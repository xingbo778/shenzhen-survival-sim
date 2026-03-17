import json, random, subprocess, os
from core.world_state import world, log, create_bot
from core.constants import LOCATIONS, PERSONAS

NEW_BOT_TEMPLATES = [
    {"name": "孙明达", "age": 23, "gender": "男", "origin": "广东潮汕", "edu": "中专",
     "personality": "踏实肯干，话不多但很靠谱。喜欢研究各种小生意。",
     "values": "勤劳致富，实在做人，赚钱养家",
     "bg": "刚来深圳打拼的年轻人，听说这里机会多",
     "habits": "早起晚睡，爱吃路边摆，爱看财经新闻"},
    {"name": "林婷婷", "age": 20, "gender": "女", "origin": "江西南昌", "edu": "大专在读",
     "personality": "开朗乐观，爱笑爱闹。有点大大咧咧但很真诚。",
     "values": "快乐最重要，人生苦短要及时行乐",
     "bg": "来深圳实习的大学生，对一切都充满好奇",
     "habits": "拍照、发朋友圈、吃吃吃、交朋友"},
    {"name": "陈志强", "age": 35, "gender": "男", "origin": "湖南衡阳", "edu": "初中",
     "personality": "沉默対言，经历过很多事。外表冷漠但内心柔软。",
     "values": "生存第一，信任要经过考验，不轻易相信人",
     "bg": "在深圳漂泊多年的老打工人，见过太多世态炎凉",
     "habits": "独处、喝酒、看新闻、早起干活"},
    {"name": "周雨晴", "age": 27, "gender": "女", "origin": "浙江温州", "edu": "本科",
     "personality": "精明能干，有商业头脑。说话直接，不喜欢绕弯子。",
     "values": "效率为王，时间就是金钱，要做就做最好的",
     "bg": "温州商人家庭出身，来深圳寻找创业机会",
     "habits": "看财报、建人脉、健身、发精致朋友圈"},
    {"name": "刘小海", "age": 18, "gender": "男", "origin": "贵州遵义", "edu": "高中辍学",
     "personality": "叛逆但善良，有街头智慧。嘴硬心软。",
     "values": "自由最重要，不想被束缚，要活出自己的样子",
     "bg": "辍学后独自来深圳闯荡，什么都不怕",
     "habits": "游荡、听音乐、交朋友、吃路边摆"},
]


def handle_bot_death(bot_id):
    """
    v9.0: 处理bot死亡 - 触发代际传承机制
    1. 财富转移给最亲密的人
    2. 核心记忆变成城市传说
    3. 生成新bot继承关系网
    """
    bot = world["bots"].get(bot_id)
    if not bot:
        return

    bot_name = bot.get("name", bot_id)
    loc = bot["location"]

    log.warning(f"💀 [v9.0 代际传承] {bot_name}({bot_id}) 已死亡，触发传承机制...")

    # === 1. 财富转移 ===
    inheritance = bot.get("money", 0)
    closest_contact = None
    max_closeness = 0

    # 先查家人
    family = bot.get("family", {})
    family_members = family.get("parents", []) + family.get("children", [])
    for fm in family_members:
        if fm in world["bots"] and world["bots"][fm]["status"] == "alive":
            closest_contact = fm
            max_closeness = 999  # 家人优先
            break

    # 再查情感纽带
    if not closest_contact:
        bonds = bot.get("emotional_bonds", {})
        for target, bond in bonds.items():
            if target.startswith("bot_") and target in world["bots"]:
                if world["bots"][target]["status"] == "alive":
                    closeness = bond.get("closeness", 0)
                    if closeness > max_closeness:
                        max_closeness = closeness
                        closest_contact = target

    if closest_contact and inheritance > 0:
        world["bots"][closest_contact]["money"] += inheritance
        heir_name = world["bots"][closest_contact].get("name", closest_contact)
        world["message_board"].append({
            "to": closest_contact, "from": "system",
            "msg": f"【遗产】{bot_name}已经离开了这个世界。作为最亲近的人，你继承了{inheritance}元遗产。",
            "tick": world["time"]["tick"], "priority": "high",
        })
        log.info(f"  财富转移: {inheritance}元 -> {heir_name}({closest_contact})")

    # === 2. 核心记忆变城市传说 ===
    core_memories = bot.get("core_memories", [])
    if core_memories:
        # 选取最重要的记忆转化为传说
        best_memories = core_memories[-3:]  # 最近3条
        for mem in best_memories:
            summary = mem.get("summary", "") if isinstance(mem, dict) else str(mem)
            legend = {
                "id": f"legend_{world['time']['tick']}_{bot_id}",
                "original_bot": bot_id,
                "original_name": bot_name,
                "content": summary,
                "origin_tick": world["time"]["tick"],
                "origin_time": world["time"]["virtual_datetime"],
                "location": loc,
                "spread_count": 0,  # 传播次数
            }
            world["urban_legends"].append(legend)
        log.info(f"  {len(best_memories)}条核心记忆转化为城市传说")

    # === 3. 记录到墓地 ===
    grave = {
        "bot_id": bot_id,
        "name": bot_name,
        "age": bot.get("age", 0),
        "origin": bot.get("origin", ""),
        "death_tick": world["time"]["tick"],
        "death_time": world["time"]["virtual_datetime"],
        "death_location": loc,
        "final_money": bot.get("money", 0),
        "reputation_score": bot.get("reputation", {}).get("score", 0),
        "reputation_tags": bot.get("reputation", {}).get("tags", []),
        "created_things": bot.get("created_things", []),
        "long_term_goal": bot.get("long_term_goal", ""),
        "narrative_summary": bot.get("narrative_summary", ""),
    }
    world["graveyard"].append(grave)

    # === 4. 地点公共记忆 ===
    from systems.world_mods import add_public_memory
    add_public_memory(loc, f"{bot_name}在这里离开了世界", bot_id, "death")

    # === 5. 通知所有认识的人 ===
    bonds = bot.get("emotional_bonds", {})
    for target_id in bonds:
        if target_id.startswith("bot_") and target_id in world["bots"]:
            if world["bots"][target_id]["status"] == "alive":
                world["message_board"].append({
                    "to": target_id, "from": "system",
                    "msg": f"【讣告】{bot_name}已经离开了这个世界。",
                    "tick": world["time"]["tick"], "priority": "high",
                })

    # === 6. 生成新bot替代死亡的bot ===
    _spawn_new_generation_bot(bot_id, bot)

    # 世界事件
    world["events"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "event": f"💀 {bot_name}离开了这个世界",
        "desc": f"{bot_name}的一生结束了。{bot.get('narrative_summary', '')}",
    })


def _spawn_new_generation_bot(dead_bot_id, dead_bot):
    """生成新一代bot替代死亡的bot"""
    # 选择一个新人设
    template = random.choice(NEW_BOT_TEMPLATES)

    world["generation_count"] = world.get("generation_count", 0) + 1
    gen = world["generation_count"]

    # 复用死亡bot的ID
    new_bot = create_bot(dead_bot_id)
    new_bot["name"] = template["name"]
    new_bot["age"] = template["age"]
    new_bot["gender"] = template["gender"]
    new_bot["origin"] = template["origin"]
    new_bot["edu"] = template["edu"]
    new_bot["hp"] = 100
    new_bot["money"] = random.randint(100, 500)
    new_bot["energy"] = 100
    new_bot["satiety"] = 70
    new_bot["status"] = "alive"
    new_bot["generation"] = gen
    new_bot["inherited_from"] = dead_bot.get("name", dead_bot_id)
    new_bot["location"] = random.choice(list(LOCATIONS.keys()))
    new_bot["home"] = random.choice(["宝安城中村", "南山公寓"])

    # 继承死亡bot的部分关系网络(作为"听说过")
    dead_bonds = dead_bot.get("emotional_bonds", {})
    inherited_bonds = {}
    for target, bond in dead_bonds.items():
        if target.startswith("bot_") and target in world["bots"]:
            if world["bots"][target]["status"] == "alive" and bond.get("closeness", 0) > 30:
                inherited_bonds[target] = {
                    "trust": 20,
                    "closeness": 5,
                    "hostility": 0,
                    "label": "听说过",
                    "impressions": [f"听说{dead_bot.get('name', '')}和这个人关系不错"]
                }
    new_bot["emotional_bonds"] = inherited_bonds

    # 继承城市传说作为初始记忆
    recent_legends = world.get("urban_legends", [])[-3:]
    new_bot["known_legends"] = [l["id"] for l in recent_legends]
    for legend in recent_legends:
        new_bot["core_memories"].append({
            "summary": f"[城市传说] 听说{legend['original_name']}的故事: {legend['content'][:50]}",
            "emotion": "neutral",
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "tag": "urban_legend",
        })

    # 更新PERSONAS以便 bot_agent能读取新人设
    PERSONAS[dead_bot_id] = {
        "name": template["name"],
        "age": template["age"],
        "gender": template["gender"],
        "origin": template["origin"],
        "edu": template["edu"],
        "home": new_bot["home"],
        "start_loc": new_bot["location"],
        "money": new_bot["money"],
        "hp": 100,
    }

    # 放入世界
    world["bots"][dead_bot_id] = new_bot
    loc = new_bot["location"]
    if loc in world["locations"] and dead_bot_id not in world["locations"][loc]["bots"]:
        world["locations"][loc]["bots"].append(dead_bot_id)

    # 启动新的bot_agent进程
    try:
        # 写入新人设到临时文件，供bot_agent读取
        persona_override = {
            "name": template["name"],
            "age": template["age"],
            "gender": template["gender"],
            "origin": template["origin"],
            "edu": template["edu"],
            "personality": template["personality"],
            "values": template["values"],
            "bg": template["bg"] + f" (第{gen}代新居民，继承了{dead_bot.get('name', '')}的一些关系)",
            "habits": template["habits"],
            "family_info": "",
        }
        with open(f"/home/ubuntu/persona_override_{dead_bot_id}.json", "w") as f:
            json.dump(persona_override, f, ensure_ascii=False)

        subprocess.Popen(
            ["python3", "/home/ubuntu/shenzhen-survival-sim/bot_agent_v8.py"],
            env=dict(os.environ, BOT_ID=dead_bot_id)
        )
        log.info(f"  新bot {template['name']}({dead_bot_id}) 已生成并启动 (第{gen}代)")
    except Exception as e:
        log.error(f"  启动新bot失败: {e}")

    # 全局事件
    world["events"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "event": f"🌟 新居民{template['name']}来到了深圳",
        "desc": f"来自{template['origin']}的{template['name']}，{template['bg'][:30]}",
    })


def spread_urban_legends():
    """每天传播城市传说 - 让活着的bot随机听到传说"""
    legends = world.get("urban_legends", [])
    if not legends:
        return
    alive_bots = [bid for bid, b in world["bots"].items() if b["status"] == "alive"]
    for bot_id in alive_bots:
        if random.random() < 0.15:  # 15%概率听到传说
            legend = random.choice(legends)
            bot = world["bots"][bot_id]
            known = bot.get("known_legends", [])
            if legend["id"] not in known:
                known.append(legend["id"])
                bot["known_legends"] = known[-10:]  # 最多记住10个
                legend["spread_count"] = legend.get("spread_count", 0) + 1
                world["message_board"].append({
                    "to": bot_id, "from": "rumor",
                    "msg": f"【城市传说】听说{legend['original_name']}曾经: {legend['content'][:60]}",
                    "tick": world["time"]["tick"], "priority": "normal",
                })
