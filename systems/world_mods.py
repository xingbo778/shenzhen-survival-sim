import json, random
from core.world_state import world, log
from core.constants import JOBS, LOCATIONS
from utils.ai_client import client

WORLD_MOD_TYPES = {
    "open_shop": {"cost": 200, "desc": "开店/摆摊", "reputation": 5},
    "create_art": {"cost": 0, "desc": "创作艺术(涂鸦/壁画/雕塑)", "reputation": 3},
    "plant_tree": {"cost": 10, "desc": "种树/绿化", "reputation": 2},
    "build_facility": {"cost": 500, "desc": "建造设施(书屋/健身角/公告栏)", "reputation": 8},
    "organize_event": {"cost": 100, "desc": "组织活动(音乐会/市集/聚会)", "reputation": 6},
    "name_place": {"cost": 0, "desc": "给地方起名/留下标记", "reputation": 1},
    "teach_skill": {"cost": 0, "desc": "教别人技能", "reputation": 4},
    "start_business": {"cost": 1000, "desc": "创业/开公司", "reputation": 10},
}


def judge_world_modification(bot_id, bot, action_desc, result_narrative):
    """
    v9.0: 判断一个行动是否产生了永久的世界改变。
    在每次行动执行后调用，由LLM判断是否有永久改变。
    """
    try:
        loc = bot["location"]
        existing_mods = [m["name"] for m in world["locations"].get(loc, {}).get("modifications", [])]

        prompt = f"""一个角色刚刚执行了一个行动。请判断这个行动是否对世界产生了永久性的改变。

角色: {bot.get('name', bot_id)}
地点: {loc}
行动: {action_desc}
结果: {result_narrative}
这个地点已有的改造: {existing_mods if existing_mods else '无'}

可能的永久改变类型:
- open_shop: 开店/摆摊(需要资金)
- create_art: 创作艺术作品(涂鸦/壁画/雕塑)
- plant_tree: 种树/绿化环境
- build_facility: 建造公共设施
- organize_event: 组织活动
- name_place: 给地方起名/留下标记
- teach_skill: 教别人技能
- start_business: 创业

请用JSON输出:
{{"has_modification": true/false, "type": "类型名", "name": "改变的名称(如'小林的炒粉摊')", "desc": "一句话描述", "impact": "对周围人的影响"}}

规则:
- 只有真正有创造性的、能留下永久痕迹的行动才算永久改变
- 吃饭/睡觉/聊天/散步等日常行为不算永久改变
- 不要重复已有的改造
- 大多数行动不会产生永久改变，请保守判断
只输出JSON。"""

        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"): raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        data = json.loads(raw)

        if not data.get("has_modification"):
            return None

        mod_type = data.get("type", "name_place")
        mod_info = WORLD_MOD_TYPES.get(mod_type, {"cost": 0, "desc": "改变", "reputation": 1})

        # 检查资金是否足够
        if bot["money"] < mod_info["cost"]:
            log.info(f"[v9.0] {bot_id} 想{data.get('name','')}但资金不足(需{mod_info['cost']}元)")
            return None

        # 扣除资金
        if mod_info["cost"] > 0:
            bot["money"] -= mod_info["cost"]

        # 创建永久改造记录
        modification = {
            "id": f"mod_{world['time']['tick']}_{bot_id}",
            "creator": bot_id,
            "creator_name": bot.get("name", bot_id),
            "type": mod_type,
            "name": data.get("name", "未命名"),
            "desc": data.get("desc", ""),
            "impact": data.get("impact", ""),
            "location": loc,
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "active": True,
        }

        # 添加到世界改造列表
        world["world_modifications"].append(modification)
        # 添加到地点改造
        if loc in world["locations"]:
            world["locations"][loc]["modifications"].append(modification)
        # 记录到bot的创造列表
        bot["created_things"].append(modification["id"])

        # 更新声望
        from systems.reputation import update_reputation
        update_reputation(bot_id, mod_info["reputation"], f"创造了{data.get('name', '')}")

        # 记录到地点公共记忆
        add_public_memory(loc, f"{bot.get('name', bot_id)}在这里{data.get('desc', '')}", bot_id, "creation")

        # 广播给所有人
        world["events"].append({
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "event": f"🌟 {bot.get('name', bot_id)}创造了[{data.get('name', '')}]",
            "desc": data.get("desc", ""),
        })

        # 如果是开店/摆摊，添加新的工作机会
        if mod_type in ("open_shop", "start_business"):
            new_job = {
                "title": data.get("name", "新店员工"),
                "skill": "social",
                "min_skill": 5,
                "pay": 35 + random.randint(0, 20),
                "tasks": [{
                    "name": f"在{data.get('name', '店铺')}工作",
                    "duration": 2,
                    "difficulty": 0.2,
                    "desc": f"在{bot.get('name', bot_id)}开的{data.get('name', '店')}里帮忙"
                }],
            }
            if loc in JOBS:
                JOBS[loc].append(new_job)
            else:
                JOBS[loc] = [new_job]
            if loc in world["locations"]:
                world["locations"][loc]["jobs"] = JOBS.get(loc, [])

        log.warning(f"🌟 [v9.0 世界改造] {bot.get('name', bot_id)} 在{loc}创造了 [{data.get('name', '')}] (类型:{mod_type}, 花费:{mod_info['cost']}元)")
        return modification

    except Exception as e:
        log.error(f"[v9.0] 世界改造判断失败: {e}")
        return None


def add_public_memory(location, event_desc, actor_id, impact_type="neutral"):
    """向地点添加公共记忆"""
    if location not in world["locations"]:
        return
    memory_entry = {
        "event": event_desc,
        "actor": actor_id,
        "actor_name": world["bots"].get(actor_id, {}).get("name", actor_id),
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "impact": impact_type,  # positive/negative/neutral/creation/conflict/death
    }
    loc = world["locations"][location]
    loc["public_memory"].append(memory_entry)
    # 保留最近30条
    if len(loc["public_memory"]) > 30:
        loc["public_memory"] = loc["public_memory"][-25:]

    # 每10条记忆更新一次地点氛围
    if len(loc["public_memory"]) % 10 == 0:
        _update_location_vibe(location)


def _update_location_vibe(location):
    """根据公共记忆更新地点氛围"""
    try:
        loc = world["locations"][location]
        memories = loc["public_memory"][-15:]
        mem_text = "\n".join([f"- {m['event']} ({m['impact']})" for m in memories])
        mods = loc.get("modifications", [])[-5:]
        mods_text = "\n".join([f"- {m['name']}: {m['desc']}" for m in mods]) if mods else "无"

        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": f"""根据以下历史事件，用一个词或短语描述这个地点的氛围。

地点: {location}
原始描述: {loc['desc']}

最近发生的事:
{mem_text}

地点改造:
{mods_text}

请用一个词或短语描述氛围(如"温馨的"/"紧张的"/"充满创意的"/"冷漠的"/"热闹的"):
只输出氛围词，不要其他文字。"""}],
            temperature=0.5, max_tokens=20,
        )
        vibe = resp.choices[0].message.content.strip().strip('"').strip()
        loc["vibe"] = vibe[:10]  # 限制长度
        log.info(f"[v9.0] {location} 氛围更新为: {vibe}")
    except Exception as e:
        log.error(f"[v9.0] 氛围更新失败: {e}")
