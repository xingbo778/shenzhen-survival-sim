import json, random, logging, re
from threading import Thread
from core.world_state import world, log, lock
from core.constants import FOOD_MENU, JOBS, LOCATIONS, PERSONAS, EMOTION_DIMS, WEATHER_TYPES, DESIRE_DECAY_ON_FULFILL
from utils.ai_client import client, grok_generate
from systems.reputation import update_reputation, reputation_interaction_modifier
from systems.world_mods import judge_world_modification, add_public_memory
from rules.rules_engine import generate_rules_from_action, get_attraction_signals
from systems.labor_market import compute_wage, check_reservation_wage, update_adaptive_expectations


def process_action(bot_id, plan):
    """涌现友好架构：LLM解析为5大类 + 保留自然语言描述，世界引擎解释后果"""
    bot = world["bots"][bot_id]

    # v8.3.2: 硬编码起床动作，不经过LLM
    if plan.strip() in ("起床", "醒来", "起来"):
        action = {"category": "survive", "type": "wake_up", "desc": plan}
        result = execute(bot_id, action)
        bot["action_log"].append({
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "plan": plan, "action": action, "result": result
        })
        bot["current_activity"] = "刚刚醒来，正在伸懒腰"
        return {"action": action, "result": result}

    loc = bot["location"]
    loc_info = world["locations"][loc]

    nearby_bots = [b for b in loc_info["bots"] if b != bot_id]
    nearby_bot_info = []
    for nb in nearby_bots[:5]:
        ob = world["bots"].get(nb, {})
        nearby_bot_info.append(f"{nb}({ob.get('name','?')},{ob.get('gender','?')})")

    food_list = ', '.join([f'{k}({v["cost"]}元)' for k, v in FOOD_MENU.items()])
    job_list = ', '.join([j['title'] for j in JOBS.get(loc, [])])
    all_locs = list(LOCATIONS.keys())

    # 检查是否有进行中的任务
    current_task = bot.get("current_task")
    task_hint = ""
    if current_task and current_task.get("status") == "in_progress":
        task_hint = f"\n⭐ 当前有进行中的工作任务[{current_task.get('task_name','')}]，如果计划提到继续做/继续工作/继续任务，必须用survive类别的work。"

    prompt = f"""你是一个JSON转换器。将用户的自然语言计划转为一个JSON动作对象。只输出JSON，不要任何其他文字。

## 上下文
- 当前地点: {loc}
- 附近的人: {nearby_bot_info if nearby_bot_info else '无'}
- 附近的NPC: {[n['name'] for n in loc_info['npcs']]}
- 所有可去地点: {all_locs}
- 当前地点可用工作: {job_list if job_list else '无'}
- 可选食物: {food_list}
{task_hint}

## 5大行动类别

### 1. survive (生存类: 吃饭/工作/睡觉/休息)
- 吃东西: {{"category":"survive","type":"eat","food":"食物名","desc":"原始描述"}}
  食物名必须是: {list(FOOD_MENU.keys())}
- 工作: {{"category":"survive","type":"work","job":"职位名","desc":"原始描述"}}
- 睡觉: {{"category":"survive","type":"sleep","desc":"原始描述"}}
- 休息: {{"category":"survive","type":"rest","desc":"原始描述"}}

### 2. social (社交类: 聊天/亲密/交易)
- 聊天: {{"category":"social","type":"talk","target":"bot_X或npc名","message":"说的话","desc":"原始描述"}}
- 亲密: {{"category":"social","type":"intimate","target":"bot_X","desc":"原始描述"}}
- 交易: {{"category":"social","type":"trade","target":"bot_X","give_type":"money","give_amount":数字,"want_type":"money","want_amount":数字,"desc":"原始描述"}}

### 3. move (移动类)
{{"category":"move","to":"目的地","desc":"原始描述"}}
目的地必须是: {all_locs}

### 4. express (表达类: 发朋友圈/拍照/刷手机)
- 发朋友圈: {{"category":"express","type":"post_moment","content":"朋友圈内容","mood":"happy/sad/neutral/angry","desc":"原始描述"}}
- 刷手机: {{"category":"express","type":"browse_phone","focus":"news/moments/hot","desc":"原始描述"}}
- 拍照: {{"category":"express","type":"selfie","prompt":"英文拍照场景描述","desc":"原始描述"}}

### 5. free (自由行动: 以上都不匹配时，保留bot的原始描述)
{{"category":"free","desc":"完整保留bot的原始描述"}}

## 规则
- 只输出一个JSON对象，不要输出多个
- 如果计划包含多个动作（如"吃热粉然后拍照"），只取第一个动作
- 如果计划明确涉及吃/喝/工作/睡觉/休息，用survive
- 如果计划明确涉及和某人互动，用social
- 如果计划明确涉及去其他地点，用move
- 如果计划明确涉及发朋友圈/拍照/刷手机，用express
- 其他一切行为（画画/弹吉他/健身/逛街/思考/写代码/喝酒/看电影/散步...）用free
- desc字段始终完整保留用户的原始计划文本

## 计划
"{plan}"

## JSON
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        # 提取第一个JSON对象（处理LLM返回多个JSON的情况）
        start = raw.find("{")
        if start >= 0:
            depth = 0
            end = start
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            raw = raw[start:end]
        action = json.loads(raw)
    except Exception as e:
        log.error(f"LLM解析 {bot_id} 动作失败: {e}")
        action = {"category": "free", "desc": plan}

    result = execute(bot_id, action)
    bot["action_log"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "plan": plan,
        "action": action,
        "result": result
    })
    if len(bot["action_log"]) > 50:
        bot["action_log"] = bot["action_log"][-30:]

    # v8.4: 更新当前活动描述（供其他bot观察）
    activity_desc = action.get("desc", "")[:40] if action.get("desc") else plan[:40]
    bot["current_activity"] = activity_desc

    # v9.0: 判断行动是否产生永久世界改变
    result_str = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
    if action.get("category") in ("free", "social") or "开" in plan or "创" in plan or "建" in plan or "摆" in plan:
        try:
            mod = judge_world_modification(bot_id, bot, plan, result_str)
            if mod:
                result_str += f" | 🌟永久改变: 创造了[{mod['name']}]"
        except Exception as e:
            log.error(f"[v9.0] 世界改造判断异常: {e}")

    # v9.0: 记录重要行动到地点公共记忆
    if action.get("category") in ("social", "free") and len(plan) > 5:
        # 只记录有意义的行动
        interesting_keywords = ["吵架", "打架", "帮助", "救", "表白", "分手", "结婚", "创业", "开店", "演出", "比赛", "教", "学"]
        if any(kw in plan for kw in interesting_keywords):
            add_public_memory(bot["location"], f"{bot.get('name', bot_id)}{plan[:30]}", bot_id, "notable")

    return {"action": action, "result": result}


def execute(bot_id, action):
    bot = world["bots"][bot_id]
    cat = action.get("category", "free")
    act = action.get("type", action.get("action", ""))  # 兼容新旧格式
    desc = action.get("desc", "")
    emotions = bot.get("emotions", {})

    # === 移动类 ===
    if cat == "move" or act == "move":
        dest = action.get("to", "")
        if dest in LOCATIONS:
            if dest == bot["location"]:
                # 目的地=当前位置，转为自由行动
                return interpret_free_action(bot_id, bot, desc or f"在{dest}随便逛逛")
        if dest in LOCATIONS and dest != bot["location"]:
            old_loc = bot["location"]
            if bot_id in world["locations"][old_loc]["bots"]:
                world["locations"][old_loc]["bots"].remove(bot_id)
            bot["location"] = dest
            world["locations"][dest]["bots"].append(bot_id)
            bot["energy"] = max(0, bot["energy"] - 5)
            # 台风天移动有风险
            if world["weather"]["current"] == "台风":
                if random.random() < 0.3:
                    bot["hp"] = max(0, bot["hp"] - 5)
                    return f"冒着台风从 {old_loc} 移动到 {dest}，被风吹得东倒西歪，受了点伤(HP-5)"
            msg = f"从 {old_loc} 移动到 {dest}"
            log.info(f"{bot_id}: {msg}")
            return msg
        return f"无法移动到 {dest}"

    elif act == "work":
        task = bot.get("current_task")
        if task and task.get("status") == "in_progress":
            remaining = task["duration"] - task.get("progress", 0)
            challenge_text = f" [难点: {task['challenge']}]" if task.get("challenge") else ""
            bot["energy"] = max(0, bot["energy"] - 8)
            msg = f'继续做[{task["task_name"]}]: {task["task_desc"]} | 进度{task.get("progress",0)}/{task["duration"]}{challenge_text}'
            log.info(f"{bot_id}: {msg}")
            return msg

        if task and task.get("status") in ["completed", "failed"]:
            bot["current_task"] = None

        job_title = action.get("job", "")
        loc = bot["location"]
        available = JOBS.get(loc, [])
        job = next((j for j in available if j["title"] == job_title), None)
        if not job:
            job = next((j for j in available if job_title in j["title"] or j["title"] in job_title), None)
        if not job and available:
            job = available[0]
        if job:
            skill_key = job["skill"]
            skill_val = bot["skills"].get(skill_key, 0) if skill_key != "none" else 10
            if skill_val >= job["min_skill"]:
                offered = compute_wage(job, loc, bot)
                accept, floor = check_reservation_wage(bot, offered)
                if not accept:
                    update_adaptive_expectations(bot, "rejection")
                    return (f"想在{loc}做{job['title']}，但出价{offered}元低于心理底线"
                            f"{floor:.0f}元，决定不做这份工作。")
                task_template = random.choice(job.get("tasks", [{"name": "工作", "duration": 2, "difficulty": 0.2, "desc": "日常工作"}]))
                new_task = {
                    "job_title": job["title"],
                    "task_name": task_template["name"],
                    "task_desc": task_template["desc"],
                    "duration": task_template["duration"],
                    "difficulty": task_template["difficulty"],
                    "skill": skill_key,
                    "base_pay": compute_wage(job, loc, bot),
                    "progress": 0,
                    "status": "in_progress",
                    "challenge": None,
                    "result": None,
                    "started_tick": world["time"]["tick"],
                }
                bot["current_task"] = new_task
                bot["energy"] = max(0, bot["energy"] - 8)
                bot["job"] = job["title"]
                msg = f'开始任务[{task_template["name"]}]: {task_template["desc"]} | 预计{task_template["duration"]}小时'
                log.info(f"{bot_id}: {msg}")
                return msg
            return f'技能不足，无法胜任 {job["title"]}'
        return f"{loc} 没有可用工作"

    elif act == "eat":
        food_name = action.get("food", "")
        food = FOOD_MENU.get(food_name)
        if not food:
            food_name = next((k for k in FOOD_MENU if food_name in k or k in food_name), None)
            food = FOOD_MENU.get(food_name) if food_name else None
        if not food:
            food_name = "城中村快餐"
            food = FOOD_MENU[food_name]
        # v8.3.2: 动态价格 - 用当前动态价格而非基础价格
        dynamic_prices = world.get("food_prices", {})
        current_cost = dynamic_prices.get(food_name, food["cost"])
        if bot["money"] >= current_cost:
            bot["money"] -= current_cost
            bot["satiety"] = min(100, bot["satiety"] + food["satiety"])
            # 食物影响情绪
            for emo_key, delta in food.get("mood", {}).items():
                emotions[emo_key] = max(0, min(100, emotions.get(emo_key, 0) + delta))
            bot["emotions"] = emotions
            # 动态经济：购买后微幅涨价
            base_cost = food["cost"]
            new_price = min(int(base_cost * 1.5), current_cost + max(1, base_cost // 10))
            dynamic_prices[food_name] = new_price
            world["food_prices"] = dynamic_prices
            msg = f'吃了{food_name}，花费{current_cost}元，饱腹度+{food["satiety"]}'
            log.info(f"{bot_id}: {msg}")
            return msg
        return f"钱不够买{food_name}(需要{current_cost}元，只有{bot['money']}元)"

    elif act == "talk":
        target = action.get("target", "")
        message = action.get("message", "你好")
        world["message_board"].append({
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "from": bot_id,
            "to": target,
            "msg": message,
            "priority": "normal"
        })
        if target.startswith("bot_"):
            bot["relationships"][target] = bot["relationships"].get(target, 0) + 1
            if target in world["bots"] and world["bots"][target]["status"] == "alive":
                target_bot = world["bots"][target]
                target_bot["relationships"][bot_id] = target_bot["relationships"].get(bot_id, 0) + 1
                # v8.3: 双向对话机制 - 设置对方的pending_reply_to
                target_bot["pending_reply_to"] = {
                    "from": bot_id,
                    "from_name": bot.get("name", bot_id),
                    "msg": message,
                    "tick": world["time"]["tick"]
                }
        bot["skills"]["social"] = min(100, bot["skills"]["social"] + 1)
        # v8.3: 社交给予更强的正面情绪反馈
        emotions["loneliness"] = max(0, emotions.get("loneliness", 30) - 8)
        emotions["happiness"] = min(100, emotions.get("happiness", 50) + 5)
        bot["emotions"] = emotions
        msg = f"对{target}说: {message}"
        log.info(f"{bot_id}: {msg}")

        # === 互动后更新双方关系记忆 ===
        def _update_bonds_after_talk():
            try:
                bot_name = bot.get("name", bot_id)
                # 确定对方信息
                if target.startswith("bot_") and target in world["bots"]:
                    target_bot = world["bots"][target]
                    target_name = target_bot.get("name", target)
                    target_personality = target_bot.get("personality", "")
                else:
                    # NPC
                    target_name = target
                    target_personality = ""
                    for loc_data in world["locations"].values():
                        for npc in loc_data.get("npcs", []):
                            if npc.get("name") == target:
                                target_personality = npc.get("personality", npc.get("desc", ""))
                                break

                # 获取双方之前的互动历史
                prev_interactions = []
                for entry in bot.get("action_log", [])[-20:]:
                    entry_str = str(entry.get("result", "")) + str(entry.get("plan", ""))
                    if target_name in entry_str or target in entry_str:
                        prev_interactions.append(entry_str[:80])
                history_text = "\n".join(prev_interactions[-5:]) if prev_interactions else "这是第一次互动"

                bond_prompt = f"""两个人刚刚进行了一次对话。请判断这次互动给双方留下了什么印象。

{bot_name}对{target_name}说: "{message}"

{bot_name}的性格: {bot.get('personality', '未知')}
{target_name}的性格: {target_personality or '未知'}

之前的互动历史:
{history_text}

请用JSON格式输出双方的印象变化:
{{
  "initiator_impression": "一句话描述{bot_name}对{target_name}的新印象(自然语言，像日记一样)",
  "target_impression": "一句话描述{target_name}对{bot_name}的新印象",
  "relationship_type": "朋友/同事/合作伙伴/竞争对手/暧昧/陌生人/家人/师徒/邻居",
  "warmth_delta": 0
}}

warmth_delta范围-10到+10，正数表示关系升温，负数表示关系降温。
只输出JSON。"""

                resp = client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=[{"role": "user", "content": bond_prompt}],
                    temperature=0.4, max_tokens=200,
                )
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"): raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    raw = raw[start:end]
                bond_data = json.loads(raw)

                # 更新发起者的bonds
                if "emotional_bonds" not in bot:
                    bot["emotional_bonds"] = {}
                bond_key = target if target.startswith("bot_") else target_name
                if bond_key not in bot["emotional_bonds"]:
                    bot["emotional_bonds"][bond_key] = {"trust": 50, "closeness": 0, "hostility": 0, "label": "陌生人", "impressions": []}
                b = bot["emotional_bonds"][bond_key]
                impression = bond_data.get("initiator_impression", "")
                if impression:
                    b["impressions"] = (b.get("impressions", []) + [impression])[-5:]  # 保留最近5条印象
                b["label"] = bond_data.get("relationship_type", b.get("label", "陌生人"))
                warmth = bond_data.get("warmth_delta", 0)
                b["closeness"] = max(0, min(100, b.get("closeness", 0) + max(0, warmth)))
                b["hostility"] = max(0, min(100, b.get("hostility", 0) + max(0, -warmth)))
                b["trust"] = max(0, min(100, b.get("trust", 50) + warmth // 2))
                log.info(f"[关系更新] {bot_id}->{bond_key}: {impression} (warmth={warmth}, label={b['label']})")

                # 更新对方的bonds（如果是bot）
                if target.startswith("bot_") and target in world["bots"]:
                    target_bot = world["bots"][target]
                    if "emotional_bonds" not in target_bot:
                        target_bot["emotional_bonds"] = {}
                    if bot_id not in target_bot["emotional_bonds"]:
                        target_bot["emotional_bonds"][bot_id] = {"trust": 50, "closeness": 0, "hostility": 0, "label": "陌生人", "impressions": []}
                    tb = target_bot["emotional_bonds"][bot_id]
                    t_impression = bond_data.get("target_impression", "")
                    if t_impression:
                        tb["impressions"] = (tb.get("impressions", []) + [t_impression])[-5:]
                    tb["label"] = bond_data.get("relationship_type", tb.get("label", "陌生人"))
                    tb["closeness"] = max(0, min(100, tb.get("closeness", 0) + max(0, warmth)))
                    tb["hostility"] = max(0, min(100, tb.get("hostility", 0) + max(0, -warmth)))
                    tb["trust"] = max(0, min(100, tb.get("trust", 50) + warmth // 2))
                    log.info(f"[关系更新] {target}->{bot_id}: {t_impression}")

            except Exception as e:
                log.error(f"[关系更新失败] {bot_id}->{target}: {e}")

        Thread(target=_update_bonds_after_talk, daemon=True).start()

        # === v8.4: 对话后果判定 — 让说话有重量 ===
        def _judge_talk_consequences():
            try:
                consequence_prompt = f"""两个人刚刚进行了一次对话。请判断这次对话是否产生了以下任何一种社会后果。

{bot.get('name', bot_id)}对{target}说: "{message}"

请用JSON输出:
{{{{
  "has_consequence": true/false,
  "type": "gossip/promise/request/conflict/none",
  "detail": "一句话描述后果",
  "gossip_about": "如果是八卦，说的是谁",
  "promise_content": "如果是承诺，承诺了什么"
}}}}
只输出JSON。"""
                resp = client.chat.completions.create(
                    model="gpt-4.1-nano",
                    messages=[{"role": "user", "content": consequence_prompt}],
                    temperature=0.3, max_tokens=150,
                )
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"): raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    raw = raw[start:end]
                cdata = json.loads(raw)

                if not cdata.get("has_consequence"):
                    return

                ctype = cdata.get("type", "none")
                detail = cdata.get("detail", "")

                if ctype == "gossip" and cdata.get("gossip_about"):
                    # 八卦传播：将信息传递给第三方
                    gossip_target = cdata["gossip_about"]
                    # 找到被八卦的bot
                    for bid2, b2 in world["bots"].items():
                        if b2.get("name") == gossip_target and bid2 != bot_id and bid2 != target:
                            world["message_board"].append({
                                "to": bid2, "from": "rumor",
                                "msg": f"【流言】有人在背后议论你: {detail}",
                                "tick": world["time"]["tick"], "priority": "normal",
                            })
                            log.info(f"[八卦传播] {bot_id}和{target}在议论{gossip_target}: {detail}")
                            break

                elif ctype == "promise":
                    # 记录承诺，待实现
                    promise = cdata.get("promise_content", detail)
                    bot["action_log"].append({
                        "tick": world["time"]["tick"],
                        "time": world["time"]["virtual_datetime"],
                        "plan": f"承诺: {promise}",
                        "action": {"category": "social", "type": "promise"},
                        "result": f"对{target}做出了承诺: {promise}"
                    })
                    log.info(f"[承诺] {bot_id}对{target}: {promise}")

                elif ctype == "conflict":
                    # 冲突大幅影响关系
                    emotions["anger"] = min(100, emotions.get("anger", 0) + 10)
                    emotions["sadness"] = min(100, emotions.get("sadness", 0) + 5)
                    bot["emotions"] = emotions
                    if target.startswith("bot_") and target in world["bots"]:
                        tb = world["bots"][target]
                        te = tb.get("emotions", {})
                        te["anger"] = min(100, te.get("anger", 0) + 10)
                        tb["emotions"] = te
                        # 降低双方信任
                        if bot_id in tb.get("emotional_bonds", {}):
                            tb["emotional_bonds"][bot_id]["trust"] = max(0, tb["emotional_bonds"][bot_id].get("trust", 50) - 10)
                            tb["emotional_bonds"][bot_id]["hostility"] = min(100, tb["emotional_bonds"][bot_id].get("hostility", 0) + 10)
                    log.info(f"[冲突] {bot_id}和{target}发生了冲突: {detail}")

                elif ctype == "request":
                    # 请求帮助，通知对方
                    if target.startswith("bot_") and target in world["bots"]:
                        world["message_board"].append({
                            "to": target, "from": bot_id,
                            "msg": f"【请求】{bot.get('name', bot_id)}向你提出了请求: {detail}",
                            "tick": world["time"]["tick"], "priority": "high",
                        })
                    log.info(f"[请求] {bot_id}向{target}: {detail}")

            except Exception as e:
                log.error(f"[对话后果判定失败] {bot_id}->{target}: {e}")

        Thread(target=_judge_talk_consequences, daemon=True).start()

        # === NPC会“回嘴”：用LLM生成NPC的回应 ===
        # NPC互动计数（用于NPC演化）
        if not target.startswith("bot_"):
            for loc_data in world["locations"].values():
                for npc in loc_data.get("npcs", []):
                    if npc.get("name") == target:
                        npc["interaction_count"] = npc.get("interaction_count", 0) + 1
        npc_reply = ""
        if not target.startswith("bot_"):
            def _generate_npc_reply():
                try:
                    # 找到NPC信息
                    npc_info = None
                    for loc_data in world["locations"].values():
                        for npc in loc_data.get("npcs", []):
                            if npc.get("name") == target:
                                npc_info = npc
                                break
                    npc_desc = npc_info.get("desc", "") if npc_info else ""
                    npc_personality = npc_info.get("personality", npc_desc) if npc_info else target

                    # 获取之前的互动历史
                    prev = []
                    for entry in bot.get("action_log", [])[-20:]:
                        r = str(entry.get("result", ""))
                        if target in r:
                            prev.append(r[:80])
                    history = "\n".join(prev[-5:]) if prev else "这是他们第一次聊天"

                    npc_prompt = f"""你是{target}，一个深圳的NPC。
你的身份: {npc_personality}

有人对你说: "{message}"
说话的人是{bot.get('name', bot_id)}。

你们之前的互动:
{history}

请用一句话回应，符合你的身份和性格。考虑之前的互动历史，不要每次都像第一次见面。
只输出回应内容，不要加任何前缀。"""

                    resp = client.chat.completions.create(
                        model="gpt-4.1-nano",
                        messages=[{"role": "user", "content": npc_prompt}],
                        temperature=0.7, max_tokens=80,
                    )
                    reply = resp.choices[0].message.content.strip().strip('"')
                    # 把NPC回应写入消息板
                    world["message_board"].append({
                        "tick": world["time"]["tick"],
                        "time": world["time"]["virtual_datetime"],
                        "from": target,
                        "to": bot_id,
                        "msg": reply,
                        "priority": "normal"
                    })
                    log.info(f"[NPC回应] {target}对{bot_id}说: {reply}")
                except Exception as e:
                    log.error(f"[NPC回应失败] {target}: {e}")

            Thread(target=_generate_npc_reply, daemon=True).start()

        return msg

    elif act == "rest":
        recover = random.randint(10, 20)
        bot["energy"] = min(100, bot["energy"] + recover)
        emotions["anxiety"] = max(0, emotions.get("anxiety", 20) - 3)
        bot["emotions"] = emotions
        msg = f"休息了一会，能量恢复{recover}"
        log.info(f"{bot_id}: {msg}")
        return msg


    elif act == "trade":
        target = action.get("target", "")
        give_type = action.get("give_type", "money")
        give_amt = int(action.get("give_amount", 0))
        want_type = action.get("want_type", "money")
        want_amt = int(action.get("want_amount", 0))
        if target in world["bots"] and world["bots"][target]["status"] == "alive":
            if give_type == "money" and bot["money"] >= give_amt:
                bot["money"] -= give_amt
                world["bots"][target]["money"] += give_amt
                if want_type == "hp" and world["bots"][target]["hp"] >= want_amt:
                    world["bots"][target]["hp"] -= want_amt
                    bot["hp"] = min(100, bot["hp"] + want_amt)
                msg = f"与{target}交易: 给出{give_amt}{give_type}, 获得{want_amt}{want_type}"
                log.info(f"{bot_id}: {msg}")
                return msg
            elif give_type == "hp" and bot["hp"] >= give_amt:
                bot["hp"] -= give_amt
                world["bots"][target]["hp"] = min(100, world["bots"][target]["hp"] + give_amt)
                if want_type == "money" and world["bots"][target]["money"] >= want_amt:
                    world["bots"][target]["money"] -= want_amt
                    bot["money"] += want_amt
                msg = f"与{target}交易: 给出{give_amt}HP, 获得{want_amt}元"
                log.info(f"{bot_id}: {msg}")
                return msg
        return "交易失败"

    elif act == "post_moment":
        content = action.get("content", "")
        mood = action.get("mood", "neutral")
        # 基于最近的实际行动生成朋友圈内容，避免LLM幻觉
        recent_actions = bot.get("action_log", [])[-5:]
        if recent_actions:
            action_summaries = [a.get("plan", "") for a in recent_actions if a.get("plan")]
            if action_summaries:
                try:
                    gen_resp = client.chat.completions.create(
                        model="gpt-4.1-nano",
                        messages=[{"role": "user", "content": f"""你是{bot.get('name', bot_id)}，根据你最近的真实经历写一条朋友圈。
你最近做了: {'; '.join(action_summaries[-3:])}
当前位置: {bot['location']}
当前心情: {mood}

要求：只基于以上真实经历写，不要编造没发生的事。像真人发朋友圈一样，简短自然，1-2句话。
只输出朋友圈内容，不要其他文字。"""}],
                        temperature=0.8, max_tokens=100,
                    )
                    content = gen_resp.choices[0].message.content.strip().strip('"')
                except:
                    pass  # 失败时用原始 content
        moment = {
            "id": f"m_{world['time']['tick']}_{bot_id}",
            "bot_id": bot_id,
            "bot_name": bot.get("name", bot_id),
            "content": content,
            "mood": mood,
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "weather": world["weather"]["current"],
            "location": bot["location"],
            "likes": [],
            "comments": [],
        }
        world["moments"].append(moment)
        if len(world["moments"]) > 200:
            world["moments"] = world["moments"][-150:]
        # 发朋友圈满足虚荣心，降低孤独感
        desires = bot.get("desires", {})
        desires["vanity"] = max(0, desires.get("vanity", 20) - 5)
        bot["desires"] = desires
        emotions["loneliness"] = max(0, emotions.get("loneliness", 30) - 3)
        bot["emotions"] = emotions
        bot["phone_battery"] = max(0, bot.get("phone_battery", 100) - 3)
        msg = f"发了条朋友圈: {content[:50]}..."
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "browse_phone":
        focus = action.get("focus", "moments")
        bot["phone_battery"] = max(0, bot.get("phone_battery", 100) - 5)
        if bot.get("phone_battery", 0) <= 0:
            return "手机没电了，无法刷手机"

        info_gathered = []
        if focus == "news":
            news = world.get("news_feed", [])[:3]
            info_gathered = [n["headline"] for n in news]
            msg = f"刷了会新闻: {'; '.join(info_gathered[:2])}"
        elif focus == "moments":
            recent_moments = world.get("moments", [])[-5:]
            info_gathered = [f"{m['bot_name']}: {m['content'][:30]}" for m in recent_moments if m["bot_id"] != bot_id]
            msg = f"刷了会朋友圈，看到{len(info_gathered)}条动态"
            # 可能点赞
            for m in recent_moments:
                if m["bot_id"] != bot_id and bot_id not in m.get("likes", []) and random.random() < 0.3:
                    m["likes"].append(bot_id)
        else:
            topics = world.get("hot_topics", [])[:3]
            info_gathered = topics
            msg = f"刷了会热搜: {'; '.join(topics[:2])}"

        emotions["loneliness"] = max(0, emotions.get("loneliness", 30) - 2)
        if random.random() < 0.3:
            emotions["anxiety"] = min(100, emotions.get("anxiety", 20) + 2)  # 信息焦虑
        bot["emotions"] = emotions
        bot["energy"] = max(0, bot["energy"] - 2)
        log.info(f"{bot_id}: {msg}")
        return json.dumps({"msg": msg, "info": info_gathered}, ensure_ascii=False)

    elif act == "sleep":
        bot["is_sleeping"] = True
        emotions["anxiety"] = max(0, emotions.get("anxiety", 20) - 5)
        bot["emotions"] = emotions
        msg = "躺下睡觉了，能量开始恢复..."
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "wake_up":
        bot["is_sleeping"] = False
        msg = "醒了！新的一天开始了"
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "sell_body":
        desires = bot.get("desires", {})
        want = action.get("want", "money")
        vanity = desires.get("vanity", 20)
        base_pay = random.randint(50, 150)
        pay = int(base_pay * (0.5 + vanity / 200))
        hp_cost = random.randint(3, 8)
        energy_cost = random.randint(15, 30)
        bot["hp"] = max(0, bot["hp"] - hp_cost)
        bot["energy"] = max(0, bot["energy"] - energy_cost)
        if want == "food":
            bot["satiety"] = min(100, bot["satiety"] + 60)
            msg = f"为了填饱肚子，出卖了自己的身体。得到了一顿饱饭。(HP-{hp_cost}, 能量-{energy_cost})"
        else:
            bot["money"] += pay
            msg = f"为了生存，出卖了自己的身体。获得{pay}元。(HP-{hp_cost}, 能量-{energy_cost})"
        desires["lust"] = max(0, desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL)
        desires["security"] = min(100, desires.get("security", 50) + 15)
        bot["desires"] = desires
        emotions["sadness"] = min(100, emotions.get("sadness", 10) + 15)
        emotions["anxiety"] = min(100, emotions.get("anxiety", 20) + 10)
        bot["emotions"] = emotions
        log.warning(f"{bot_id}: {msg}")
        return msg

    elif act == "seek_pleasure":
        desires = bot.get("desires", {})
        cost = random.randint(100, 300)
        if bot["money"] < cost:
            return f"想寻欢作乐，但钱不够(需要{cost}元，只有{bot['money']}元)"
        bot["money"] -= cost
        bot["energy"] = max(0, bot["energy"] - 20)
        desires["lust"] = max(0, desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL)
        desires["vanity"] = min(100, desires.get("vanity", 20) + 5)
        bot["desires"] = desires
        emotions["happiness"] = min(100, emotions.get("happiness", 50) + 5)
        bot["emotions"] = emotions
        msg = f"花了{cost}元寻欢作乐。欲望得到了暂时的满足。(能量-20)"
        log.warning(f"{bot_id}: {msg}")
        return msg

    elif act == "intimate":
        target_id = action.get("target", "")
        desires = bot.get("desires", {})
        loc = bot["location"]
        loc_bots = world["locations"][loc]["bots"]

        if target_id not in loc_bots or target_id == bot_id:
            return "想找人发展亲密关系，但附近没有合适的对象"

        target = world["bots"].get(target_id)
        if not target or target.get("status") == "dead" or target.get("is_sleeping"):
            return "对方不在或无法回应"

        desires["lust"] = max(0, desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL)
        bot["energy"] = max(0, bot["energy"] - 10)
        emotions["happiness"] = min(100, emotions.get("happiness", 50) + 5)
        emotions["loneliness"] = max(0, emotions.get("loneliness", 30) - 15)
        bot["desires"] = desires
        bot["emotions"] = emotions

        t_desires = target.get("desires", {})
        t_desires["lust"] = max(0, t_desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL * 0.7)
        target["desires"] = t_desires
        t_emotions = target.get("emotions", {})
        t_emotions["happiness"] = min(100, t_emotions.get("happiness", 50) + 4)
        t_emotions["loneliness"] = max(0, t_emotions.get("loneliness", 30) - 10)
        target["emotions"] = t_emotions

        # 双方亲密度提升
        for a, b in [(bot_id, target_id), (target_id, bot_id)]:
            src = world["bots"][a]
            rels = src.get("relationships", {})
            if b not in rels or not isinstance(rels[b], dict):
                rels[b] = {"trust": 0, "intimacy": 0, "hostility": 0}
            rels[b]["intimacy"] = min(100, rels[b].get("intimacy", 0) + 25)
            rels[b]["trust"] = min(100, rels[b].get("trust", 0) + 10)
            src["relationships"] = rels

        target_name = target.get("name", target_id)
        msg = f"和{target_name}发展了亲密关系。双方感情升温，欲望得到释放。(能量-10)"
        log.warning(f"{bot_id}: {msg}")
        target["action_log"].append({
            "tick": world["time"]["tick"],
            "action": f"{bot.get('name', bot_id)}与你发展了亲密关系",
            "result": "感情升温，欲望释放"
        })
        return msg

    elif act == "selfie":
        selfie_prompt = action.get("prompt", "")
        if not selfie_prompt:
            selfie_prompt = f"A person taking a selfie at {bot['location']} in Shenzhen, China"
        bot["selfie_count"] = bot.get("selfie_count", 0) + 1
        tick = world["time"]["tick"]
        filename = f"{bot_id}_day{world['time']['virtual_day']}_{tick}.jpg"
        save_path = f"/home/ubuntu/selfies/{filename}"
        bot["phone_battery"] = max(0, bot.get("phone_battery", 100) - 5)
        emotions["happiness"] = min(100, emotions.get("happiness", 50) + 2)
        desires = bot.get("desires", {})
        desires["vanity"] = max(0, desires.get("vanity", 20) - 8)
        bot["desires"] = desires
        bot["emotions"] = emotions

        def _gen():
            result = grok_generate(selfie_prompt, save_path)
            if result["success"]:
                with lock:
                    world["gallery"].append({
                        "bot_id": bot_id,
                        "bot_name": bot.get("name", bot_id),
                        "filename": filename,
                        "prompt": selfie_prompt,
                        "time": world["time"]["virtual_datetime"],
                        "tick": tick,
                        "url": f"/selfies/{filename}"
                    })
                log.info(f"{bot_id} 拍照成功: {filename}")
            else:
                err = result.get('error', '未知错误')
                log.error(f"{bot_id} 拍照失败: {err}")
                # v8.3.2: 优雅降级 - 记录失败体验而不是静默失败
                with lock:
                    world["events"].append({
                        "tick": tick,
                        "time": world["time"]["virtual_datetime"],
                        "desc": f"{bot.get('name', bot_id)}想拍照但手机信号不好，没拍成"
                    })

        Thread(target=_gen, daemon=True).start()
        msg = f"📸 正在拍照: {selfie_prompt[:60]}..."
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "free_action" or cat == "free":
        desc = action.get("desc", "做了点事情")
        # 用LLM解释自由行动的后果，让世界更加丰富
        consequence = interpret_free_action(bot_id, bot, desc)
        log.info(f"{bot_id}: [自由行动] {desc} -> {consequence}")
        return consequence

    else:
        # 其他未识别的行动也走自由解释
        desc = action.get("desc", str(action))
        consequence = interpret_free_action(bot_id, bot, desc)
        log.info(f"{bot_id}: [未分类行动] {desc} -> {consequence}")
        return consequence


def interpret_free_action(bot_id, bot, desc):
    """LLM解释自由行动的后果，返回叙事性结果并应用数值变化"""
    emotions = bot.get("emotions", {})
    loc = bot["location"]

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": f"""你是深圳生存模拟的世界引擎。一个角色正在执行以下行动，请解释后果。

角色: {bot.get('name', bot_id)}
地点: {loc}
行动: {desc}
当前钱: {bot['money']}元
当前能量: {bot['energy']}

请输出一个JSON：
{{
  "narrative": "一句话描述发生了什么（第三人称，生动具体）",
  "money_delta": 0,
  "energy_delta": -3,
  "happiness_delta": 0,
  "skill_up": null,
  "found_item": null
}}

规则：
- narrative要生动具体，像小说叙述
- money_delta通常为0或负数（花钱），不要随便给钱
- energy_delta通常为-2到-5（做事消耗能量）
- happiness_delta范围-5到+5
- skill_up可以是"creative"/"tech"/"social"/"physical"或null
- found_item可以是一个物品名或null（小概率发现东西）
- 只输出JSON"""}],
            temperature=0.7, max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        # v8.3: 更强力的JSON提取
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        # 用正则贪婪匹配第一个完整JSON对象
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        else:
            # fallback: 用旧方法
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                raw = raw[start:end]
        # v8.3.2: 增强JSON清洗 - 处理LLM常见的非法字符
        raw = re.sub(r':\s*(-?\d+)\s*[+\-]', r': \1', raw)  # 数值后的+/-
        raw = re.sub(r',\s*}', '}', raw)  # 尾部多余逗号
        raw = re.sub(r',\s*]', ']', raw)  # 数组尾部多余逗号
        raw = raw.replace('\n', ' ')  # 去掉字符串中的换行
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # 再次尝试：去掉所有控制字符
            cleaned = re.sub(r'[\x00-\x1f]', ' ', raw)
            result = json.loads(cleaned)

        # 应用数值变化
        narrative = result.get("narrative", desc)
        bot["money"] = max(0, bot["money"] + int(result.get("money_delta", 0)))
        bot["energy"] = max(0, min(100, bot["energy"] + int(result.get("energy_delta", -3))))
        h_delta = int(result.get("happiness_delta", 0))
        emotions["happiness"] = max(0, min(100, emotions.get("happiness", 50) + h_delta))
        bot["emotions"] = emotions

        skill = result.get("skill_up")
        if skill and skill in bot["skills"]:
            bot["skills"][skill] = min(100, bot["skills"][skill] + 1)

        item = result.get("found_item")
        if item:
            bot["inventory"].append(item)
            narrative += f"（发现了{item}）"

        return narrative

    except Exception as e:
        log.error(f"interpret_free_action失败: {e} | raw={raw[:200] if 'raw' in dir() else 'N/A'}")
        # fallback: 简单处理
        bot["energy"] = max(0, bot["energy"] - 3)
        return desc


def execute_generic(bot_id, tool_call):
    """v10.0 核心：执行 generic 工具调用，返回丰富的后果反馈。
    5个工具: use_resource / interact / move / create / express
    所有后果由 LLM 判断，不再硬编码。"""
    bot = world["bots"][bot_id]
    tool = tool_call.get("tool", "")
    args = tool_call.get("args", {})
    desc = tool_call.get("desc", "")
    loc = bot["location"]
    loc_info = world["locations"].get(loc, {})

    # 构建世界上下文给 LLM
    nearby_bots_info = []
    for nb in loc_info.get("bots", []):
        if nb != bot_id:
            ob = world["bots"].get(nb, {})
            nearby_bots_info.append(f"{ob.get('name','?')}({nb}): {ob.get('current_activity','闲着')}")

    existing_creations = [m for m in world.get("world_modifications", []) if m.get("location") == loc]
    creations_text = ", ".join([f"{c['name']}(by {c.get('creator_name','?')})" for c in existing_creations[:5]]) if existing_creations else "无"

    npcs_text = ", ".join([n.get("name","?") for n in loc_info.get("npcs", [])]) if loc_info.get("npcs") else "无"

    context = f"""角色: {bot.get('name', bot_id)} ({bot.get('age','?')}岁{bot.get('gender','?')})
性格: {bot.get('personality','')[:60]}
地点: {loc}
金钱: {bot['money']}元 | 能量: {bot['energy']}/100 | 饱腹: {bot['satiety']}/100 | HP: {bot['hp']:.0f}/100
技能: {json.dumps(bot.get('skills',{}), ensure_ascii=False)}
物品: {bot.get('inventory', [])}
附近的人: {chr(10).join(nearby_bots_info) if nearby_bots_info else '无'}
NPC: {npcs_text}
这里已有的创造物: {creations_text}
天气: {world['weather'].get('condition','晴天')}
时间: {world['time']['virtual_datetime']}"""

    consequence_prompt = f"""你是深圳生存模拟的世界引擎。一个角色使用了工具，请判断后果。

{context}

== 工具调用 ==
工具: {tool}
参数: {json.dumps(args, ensure_ascii=False)}
描述: {desc}

请输出一个JSON，判断这个行动在真实世界中会产生什么后果：

{{
  "narrative": "2-3句生动的第三人称叙述，描述发生了什么，要具体、有画面感",
  "success": true或false,
  "money_delta": 金钱变化(整数，花钱为负，赚钱为正，要合理),
  "energy_delta": 能量变化(通常-2到-10，休息为正),
  "satiety_delta": 饱腹变化(吃东西为正，否则0),
  "happiness_delta": 快乐变化(-10到+10),
  "skill_up": "提升的技能名(creative/tech/social/physical)或null",
  "world_change": {{
    "type": "new_entity/modify_entity/destroy_entity/reputation/information/null",
    "name": "创造物/变化的名称",
    "description": "这个变化的描述",
    "permanent": true或false,
    "cost_money": 创建花费(0如果不花钱),
    "cost_energy": 创建消耗能量
  }} 或 null,
  "social_effects": [
    {{
      "target": "受影响的人的bot_id或名字",
      "effect": "对这个人产生了什么影响",
      "warmth_delta": 关系温度变化(-5到+5)
    }}
  ],
  "side_effects": ["附近的人能观察到的现象(1-2条)"],
  "feedback_to_actor": "给行动者的直接反馈(他能看到/听到/感受到什么)"
}}

规则：
- 要符合现实逻辑，不要魔法
- 花钱的事情必须检查够不够钱(当前{bot['money']}元)，不够就失败
- 能量不够(当前{bot['energy']})也会影响结果
- 创业/开店至少需要100-500元，不能空手套白狼
- 和人互动时，对方的反应要符合对方的性格和当前状态
- world_change只在真正产生持久影响时才填(画画、开店、种树、建东西等)，普通聊天/吃饭不算
- social_effects只在有社交互动时才填
- 只输出JSON"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": consequence_prompt}],
            temperature=0.7, max_tokens=600,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            raw = json_match.group(0)
        raw = re.sub(r',\s*}', '}', raw)
        raw = re.sub(r',\s*]', ']', raw)
        result = json.loads(raw)
    except Exception as e:
        log.error(f"[v10] execute_generic LLM失败: {e}")
        result = {
            "narrative": f"{bot.get('name', bot_id)}尝试{desc}，但没什么特别的事发生。",
            "success": True, "money_delta": 0, "energy_delta": -3,
            "satiety_delta": 0, "happiness_delta": 0,
            "world_change": None, "social_effects": [], "side_effects": [],
            "feedback_to_actor": "一切如常。"
        }

    # === 应用后果 ===
    narrative = result.get("narrative", desc)

    # 资源变化
    money_d = int(result.get("money_delta", 0))
    energy_d = int(result.get("energy_delta", -3))
    satiety_d = int(result.get("satiety_delta", 0))
    happiness_d = int(result.get("happiness_delta", 0))

    bot["money"] = max(0, bot["money"] + money_d)
    bot["energy"] = max(0, min(100, bot["energy"] + energy_d))
    bot["satiety"] = max(0, min(100, bot["satiety"] + satiety_d))
    emotions = bot.get("emotions", {})
    emotions["happiness"] = max(0, min(100, emotions.get("happiness", 50) + happiness_d))
    bot["emotions"] = emotions

    # 技能提升
    skill = result.get("skill_up")
    if skill and skill in bot.get("skills", {}):
        bot["skills"][skill] = min(100, bot["skills"][skill] + 1)

    # === 世界改变 ===
    wc = result.get("world_change")
    if wc and wc.get("type") and wc["type"] != "null":
        cost_m = int(wc.get("cost_money", 0))
        cost_e = int(wc.get("cost_energy", 0))

        # 检查资源是否足够
        if bot["money"] >= cost_m and bot["energy"] >= cost_e:
            bot["money"] -= cost_m
            bot["energy"] = max(0, bot["energy"] - cost_e)

            if wc.get("permanent", False):
                mod = {
                    "name": wc.get("name", "未知创造"),
                    "description": wc.get("description", ""),
                    "type": wc["type"],
                    "creator": bot_id,
                    "creator_name": bot.get("name", bot_id),
                    "location": loc,
                    "tick": world["time"]["tick"],
                    "time": world["time"]["virtual_datetime"],
                }
                world["world_modifications"].append(mod)
                log.warning(f"[v10 WORLD_CHANGE] {bot.get('name',bot_id)} 创造了 [{wc['name']}] @ {loc}")

                # 声望奖励
                rep = bot.get("reputation", {"score": 0, "tags": []})
                rep["score"] = rep.get("score", 0) + 3
                bot["reputation"] = rep

                # 地点公共记忆
                add_public_memory(loc, f"{bot.get('name',bot_id)}创造了{wc['name']}: {wc.get('description','')[:40]}", bot_id, "creation")

            elif wc["type"] == "reputation":
                rep = bot.get("reputation", {"score": 0, "tags": []})
                rep["score"] = rep.get("score", 0) + 1
                bot["reputation"] = rep

            elif wc["type"] == "information":
                # 信息传播——添加到地点记忆
                add_public_memory(loc, f"{bot.get('name',bot_id)}: {wc.get('description','')[:50]}", bot_id, "information")

            narrative += f" [世界变化: {wc.get('name','')}]"
        else:
            narrative += f" (想创造{wc.get('name','')}, 但资源不够)"

    # === 社交效果 ===
    social_fx = result.get("social_effects", [])
    for fx in social_fx:
        target_id = fx.get("target", "")
        warmth_d = int(fx.get("warmth_delta", 0))
        effect_desc = fx.get("effect", "")

        # 尝试匹配 target 到 bot_id
        resolved_target = None
        for bid, bdata in world["bots"].items():
            if bid == target_id or bdata.get("name") == target_id:
                resolved_target = bid
                break

        if resolved_target and resolved_target != bot_id:
            # 更新关系
            rels = bot.get("relationships", {})
            if resolved_target not in rels:
                rels[resolved_target] = {"label": "认识的人", "warmth": 0}
            rels[resolved_target]["warmth"] = max(-10, min(10, rels[resolved_target].get("warmth", 0) + warmth_d))
            bot["relationships"] = rels

            # 对方也感知到
            target_bot = world["bots"].get(resolved_target, {})
            target_rels = target_bot.get("relationships", {})
            if bot_id not in target_rels:
                target_rels[bot_id] = {"label": "认识的人", "warmth": 0}
            # 对方的感受是行动者的一半
            target_rels[bot_id]["warmth"] = max(-10, min(10, target_rels[bot_id].get("warmth", 0) + warmth_d // 2))
            target_bot["relationships"] = target_rels

            log.info(f"[v10 SOCIAL] {bot.get('name',bot_id)}->{world['bots'].get(resolved_target,{}).get('name','?')}: {effect_desc} (warmth {warmth_d:+d})")

            # 记录到地点记忆（如果是显著互动）
            if abs(warmth_d) >= 3:
                add_public_memory(loc, f"{bot.get('name',bot_id)}和{target_bot.get('name','?')}: {effect_desc[:30]}", bot_id, "social")

    # === 侧面效果（供其他bot感知） ===
    side_effects = result.get("side_effects", [])
    if side_effects:
        # 存储为地点的临时事件，其他bot下次heartbeat时能看到
        if "recent_events" not in loc_info:
            loc_info["recent_events"] = []
        for se in side_effects[:3]:
            loc_info["recent_events"].append({
                "event": se,
                "source": bot_id,
                "tick": world["time"]["tick"]
            })
        # 只保留最近10条
        loc_info["recent_events"] = loc_info["recent_events"][-10:]

    # === 构建反馈结果 ===
    feedback = {
        "narrative": narrative,
        "success": result.get("success", True),
        "feedback": result.get("feedback_to_actor", ""),
        "resource_changes": {
            "money": money_d - int(wc.get("cost_money", 0) if wc and wc.get("type") != "null" else 0),
            "energy": energy_d - int(wc.get("cost_energy", 0) if wc and wc.get("type") != "null" else 0),
            "satiety": satiety_d,
            "happiness": happiness_d,
        },
        "world_change": wc.get("name") if wc and wc.get("type") != "null" else None,
        "social_effects": [f"{fx.get('target','?')}: {fx.get('effect','')}" for fx in social_fx],
    }

    log.info(f"[v10] {bot.get('name',bot_id)} | {tool}({json.dumps(args, ensure_ascii=False)[:60]}) -> {narrative[:80]}")

    return feedback


def process_action_v10(bot_id, plan):
    """v10.0: 新的行动处理入口。
    接受 bot 的自然语言计划，用 LLM 转换为 generic 工具调用，然后执行。
    如果无法解析为工具调用，fallback 到旧的 process_action。"""
    bot = world["bots"][bot_id]
    loc = bot["location"]
    loc_info = world["locations"].get(loc, {})

    # 硬编码起床
    if plan.strip() in ("起床", "醒来", "起来"):
        action = {"category": "survive", "type": "wake_up", "desc": plan}
        result = execute(bot_id, action)
        bot["action_log"].append({
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "plan": plan, "action": action, "result": result
        })
        bot["current_activity"] = "刚刚醒来"
        return {"action": action, "result": result}

    # 硬编码睡觉
    if any(kw in plan for kw in ["睡觉", "睡了", "入睡", "躺下睡"]):
        action = {"category": "survive", "type": "sleep", "desc": plan}
        result = execute(bot_id, action)
        bot["action_log"].append({
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "plan": plan, "action": action, "result": result
        })
        bot["current_activity"] = "睡觉中"
        return {"action": action, "result": result}

    # 用 LLM 将自然语言转为 generic 工具调用
    nearby_bots = [b for b in loc_info.get("bots",[]) if b != bot_id]
    nearby_info = []
    for nb in nearby_bots[:5]:
        ob = world["bots"].get(nb, {})
        nearby_info.append(f"{nb}({ob.get('name','?')})")

    all_locs = list(LOCATIONS.keys())
    existing_things = [m["name"] for m in world.get("world_modifications", []) if m.get("location") == loc]

    tool_prompt = f"""你是一个JSON转换器。将用户的自然语言计划转为一个工具调用JSON。只输出JSON。

## 上下文
- 角色: {bot.get('name', bot_id)} (钱:{bot['money']}元, 能量:{bot['energy']}, 饱腹:{bot['satiety']})
- 地点: {loc}
- 附近的人: {nearby_info if nearby_info else '无'}
- NPC: {[n['name'] for n in loc_info.get('npcs',[])]}
- 所有地点: {all_locs}
- 这里已有的东西: {existing_things if existing_things else '无'}

## 5个工具

### use_resource - 消耗资源做任何事
用途: 吃饭、买东西、工作赚钱、学习、锻炼、休息、娱乐...
{{"tool":"use_resource", "args":{{"resource":"money/energy/item", "amount":数字, "purpose":"做什么"}}, "desc":"原始描述"}}

### interact - 与人/NPC/物品/设施交互
用途: 聊天、交易、合作、争吵、求助、使用设施...
{{"tool":"interact", "args":{{"target":"对象名或bot_id", "manner":"friendly/hostile/business/romantic/casual", "content":"具体内容"}}, "desc":"原始描述"}}

### move - 移动到其他地点
{{"tool":"move", "args":{{"destination":"地点名", "mode":"walk/bus/taxi"}}, "desc":"原始描述"}}
目的地必须是: {all_locs}

### create - 创造/建造/改变世界中的东西
用途: 开店、摆摊、画画、种树、写歌、组织活动、传播消息...
{{"tool":"create", "args":{{"what":"创造什么", "where":"{loc}", "using":"需要的资源描述"}}, "desc":"原始描述"}}

### express - 表达/输出信息
用途: 发朋友圈、自言自语、大声呼喊、唱歌、演讲...
{{"tool":"express", "args":{{"channel":"朋友圈/自言自语/大声说/唱歌/表演", "content":"内容"}}, "desc":"原始描述"}}

## 规则
- 只输出一个JSON
- 如果计划包含多个动作，只取最主要的一个
- 吃饭/买东西/工作/休息/学习/锻炼 -> use_resource
- 和人说话/交易/合作 -> interact
- 去其他地方 -> move
- 创造新东西/永久改变环境 -> create
- 发朋友圈/唱歌/喊话 -> express
- desc字段完整保留原始计划

## 计划
"{plan}"

## JSON"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": tool_prompt}],
            temperature=0.0, max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        start = raw.find("{")
        if start >= 0:
            depth = 0
            end = start
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            raw = raw[start:end]
        tool_call = json.loads(raw)
    except Exception as e:
        log.error(f"[v10] LLM工具解析失败: {e}, fallback到旧逻辑")
        return process_action(bot_id, plan)

    tool_name = tool_call.get("tool", "")

    # move 特殊处理（直接执行，不需要LLM判断后果）
    if tool_name == "move":
        dest = tool_call.get("args", {}).get("destination", "")
        mode = tool_call.get("args", {}).get("mode", "walk")
        if dest == bot["location"]:
            # 同地移动 = 就地探索，转为 generic 执行
            tool_call["tool"] = "use_resource"
            tool_call["args"] = {"resource": "energy", "amount": 3, "purpose": f"在{loc}附近闲逛探索"}
            tool_call["desc"] = f"在{loc}附近闲逛探索"
            feedback = execute_generic(bot_id, tool_call)
        elif dest in LOCATIONS:
            old_loc = bot["location"]
            if old_loc in world["locations"] and bot_id in world["locations"][old_loc]["bots"]:
                world["locations"][old_loc]["bots"].remove(bot_id)
            bot["location"] = dest
            if bot_id not in world["locations"][dest]["bots"]:
                world["locations"][dest]["bots"].append(bot_id)
            cost = {"walk": 0, "bus": 3, "taxi": 15}.get(mode, 0)
            bot["money"] = max(0, bot["money"] - cost)
            bot["energy"] = max(0, bot["energy"] - 5)
            narrative = f"{bot.get('name',bot_id)}从{old_loc}{'走路' if mode=='walk' else '坐'+mode}到了{dest}"
            if cost > 0:
                narrative += f"(花了{cost}元)"
            log.info(f"[v10] {bot.get('name',bot_id)} 移动: {old_loc} -> {dest} ({mode})")
            feedback = {"narrative": narrative, "success": True, "feedback": f"你到了{dest}"}
        else:
            feedback = {"narrative": f"找不到{dest}这个地方", "success": False, "feedback": "目的地不存在"}

    # express 中的朋友圈特殊处理
    elif tool_name == "express" and tool_call.get("args", {}).get("channel") == "朋友圈":
        content = tool_call.get("args", {}).get("content", "")
        moment = {
            "author": bot_id,
            "author_name": bot.get("name", bot_id),
            "content": content,
            "time": world["time"]["virtual_datetime"],
            "tick": world["time"]["tick"],
            "likes": [],
            "comments": [],
        }
        world["moments"].append(moment)
        if len(world["moments"]) > 100:
            world["moments"] = world["moments"][-80:]
        log.info(f"[v10] {bot.get('name',bot_id)} 发朋友圈: {content[:40]}")
        feedback = {"narrative": f"{bot.get('name',bot_id)}发了一条朋友圈: {content[:30]}...", "success": True, "feedback": "朋友圈发送成功"}

    else:
        # 所有其他工具调用走 generic 执行引擎
        feedback = execute_generic(bot_id, tool_call)

    # 记录行动日志
    bot["action_log"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "plan": plan,
        "tool_call": tool_call,
        "result": feedback,
    })
    if len(bot["action_log"]) > 50:
        bot["action_log"] = bot["action_log"][-30:]

    # 更新当前活动
    bot["current_activity"] = (tool_call.get("desc", "") or plan)[:40]

    # 存储反馈供 bot 下次感知
    bot["last_action_feedback"] = {
        "plan": plan,
        "narrative": feedback.get("narrative", ""),
        "feedback": feedback.get("feedback", ""),
        "success": feedback.get("success", True),
        "world_change": feedback.get("world_change"),
        "social_effects": feedback.get("social_effects", []),
    }

    # === v10.1: 判断是否应该产生新的世界运行规则 ===
    log.info(f"[RULES-DEBUG] 准备判断规则: {bot.get('name',bot_id)} @ {loc}, success={feedback.get('success', True)}, plan={plan[:50]}")
    if feedback.get("success", True):
        try:
            new_rules = generate_rules_from_action(
                world, bot_id, bot.get("name", bot_id), loc,
                plan, feedback.get("narrative", ""), client
            )
            log.info(f"[RULES-DEBUG] 规则判断结果: {len(new_rules) if new_rules else 0}条")
            if new_rules:
                for nr in new_rules:
                    world["active_rules"].append(nr)
                    log.warning(f"[RULES] 新规则注入! [{nr['name']}] by {bot.get('name',bot_id)} @ {loc}: {nr['description'][:60]}")
                    # 同时记录到反馈中，让bot知道自己改变了世界
                    bot["last_action_feedback"]["rules_created"] = [
                        {"name": nr["name"], "desc": nr["description"]} for nr in new_rules
                    ]
                    # 声望奖励
                    rep = bot.get("reputation", {"score": 0, "tags": [], "deeds": []})
                    rep["score"] = rep.get("score", 0) + 5
                    rep["deeds"].append(f"创建规则[{nr['name']}]")
                    bot["reputation"] = rep
        except Exception as e:
            log.error(f"[RULES] generate_rules_from_action失败: {e}")

    return {"action": tool_call, "result": feedback}
