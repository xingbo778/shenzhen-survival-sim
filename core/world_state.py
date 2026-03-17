import os, json, random, logging
from threading import Lock
from .constants import (LOCATIONS, JOBS, PERSONAS, FAMILY_RELATIONS, EMOTION_DIMS,
                         BOT_DESIRE_PROFILES, DEFAULT_DESIRE_PROFILE)

os.makedirs("/home/ubuntu/logs", exist_ok=True)
os.makedirs("/home/ubuntu/selfies", exist_ok=True)

log = logging.getLogger("world")
log.setLevel(logging.DEBUG)
fh = logging.FileHandler("/home/ubuntu/logs/world_engine.log", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [WORLD] %(levelname)s %(message)s"))
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s [WORLD] %(levelname)s %(message)s"))
log.addHandler(fh)
log.addHandler(sh)

lock = Lock()

world = {
    "time": {"tick": 0, "virtual_hour": 6, "virtual_day": 1, "virtual_datetime": "第1天 06:00"},
    "weather": {"current": "晴天", "desc": "阳光明媚，适合外出", "changed_at_tick": 0},
    "news_feed": [],
    "hot_topics": [],
    "bots": {},
    "locations": {},
    "events": [],
    "active_effects": [],
    "world_narrative": "这座城市刚刚苏醒，故事还没有开始。",
    "message_board": [],
    "moments": [],
    "gallery": [],
    "food_prices": {},
    "world_modifications": [],
    "urban_legends": [],
    "generation_count": 0,
    "graveyard": [],
    "reputation_board": {},
    "active_rules": [],
}


def create_bot(bot_id):
    p = PERSONAS[bot_id]
    family = FAMILY_RELATIONS.get(bot_id, {"parents": [], "children": []})
    profile = BOT_DESIRE_PROFILES.get(bot_id, DEFAULT_DESIRE_PROFILE)
    return {
        "id": bot_id,
        "name": p["name"],
        "age": p["age"],
        "gender": p["gender"],
        "origin": p["origin"],
        "edu": p["edu"],
        "home": p["home"],
        "location": p["start_loc"],
        "hp": p["hp"],
        "money": p["money"],
        "energy": 100,
        "satiety": 70,
        "status": "alive",
        "job": None,
        "skills": {"tech": random.randint(5, 30), "social": random.randint(5, 30),
                    "creative": random.randint(5, 30), "physical": random.randint(5, 30)},
        "inventory": [],
        "relationships": {},
        "family": family,
        "action_log": [],
        "is_sleeping": False,
        "current_task": None,
        "selfie_count": 0,
        # v8 新增
        "emotions": {"happiness": 50, "sadness": 10, "anger": 5, "anxiety": 20, "loneliness": 30},
        "desires": {
            "lust": random.randint(10, 30) * profile.get("lust_mult", 1.0),
            "power": random.randint(5, 20) * profile.get("power_mult", 1.0),
            "greed": random.randint(10, 30) * profile.get("greed_mult", 1.0),
            "vanity": random.randint(10, 25) * profile.get("vanity_mult", 1.0),
            "security": random.randint(5, 20) * profile.get("security_mult", 1.0),
        },
        "phone_battery": 100,  # 手机电量
        # 内心状态 (由Bot Agent同步过来)
        "values": {"original": "", "current": "", "shifts": []},
        "core_memories": [],
        "emotional_bonds": {},
        # v8.3 新增
        "long_term_goal": None,           # 长期目标
        "pending_reply_to": None,         # 待回应的对话 {"from": bot_id, "msg": "...", "tick": N}
        "recent_actions_synced": [],      # 由bot_agent同步过来的最近行动
        "current_activity": "",              # v8.4: 当前正在做的事（一句话描述，供其他bot观察）
        # v9.0: 进化引擎新字段
        "reputation": {"score": 0, "tags": [], "deeds": []},  # 公众声望
        "created_things": [],     # 这个bot创造的永久改变
        "generation": 0,          # 第几代bot
        "inherited_from": None,   # 继承自哪个死亡bot
        "known_legends": [],      # 知道的城市传说
    }


def generate_npcs(loc_name):
    npc_pool = {
        "宝安城中村": [
            {"id": "npc_landlord", "name": "房东王姐", "role": "房东", "personality": "精明但不坏"},
            {"id": "npc_vendor", "name": "早餐摊老李", "role": "小贩", "personality": "热情健谈"},
            {"id": "npc_guard", "name": "保安老张", "role": "保安", "personality": "沉默寡言"},
        ],
        "南山科技园": [
            {"id": "npc_hr", "name": "HR小陈", "role": "招聘", "personality": "职业微笑"},
            {"id": "npc_coder", "name": "秃头程序员", "role": "路人", "personality": "疲惫但友善"},
        ],
        "福田CBD": [
            {"id": "npc_banker", "name": "银行经理刘总", "role": "金融", "personality": "势利但专业"},
            {"id": "npc_intern", "name": "实习生小美", "role": "实习生", "personality": "紧张焦虑"},
        ],
        "华强北": [
            {"id": "npc_dealer", "name": "手机贩子阿强", "role": "商贩", "personality": "油嘴滑舌"},
            {"id": "npc_tourist", "name": "外国游客Tom", "role": "游客", "personality": "好奇友好"},
        ],
        "东门老街": [
            {"id": "npc_boss", "name": "包工头老陈", "role": "包工头", "personality": "粗犷直接"},
            {"id": "npc_oldlady", "name": "卖菜阿婆", "role": "小贩", "personality": "慈祥唠叨"},
        ],
        "南山公寓": [
            {"id": "npc_neighbor", "name": "隔壁室友小刘", "role": "邻居", "personality": "安静内向"},
        ],
        "深圳湾公园": [
            {"id": "npc_runner", "name": "跑步大叔", "role": "路人", "personality": "阳光积极"},
            {"id": "npc_couple", "name": "拍婚纱照的情侣", "role": "路人", "personality": "甜蜜幸福"},
        ],
    }
    return npc_pool.get(loc_name, [])


def init_world():
    # 初始化地点
    for loc_name, loc_data in LOCATIONS.items():
        world["locations"][loc_name] = {
            "desc": loc_data["desc"],
            "type": loc_data["type"],
            "bots": [],
            "npcs": generate_npcs(loc_name),
            "items": [],
            "jobs": JOBS.get(loc_name, []),
            # v9.0: 地点公共记忆
            "public_memory": [],       # 这个地点发生过的重要事件 [{event, actor, tick, impact}]
            "modifications": [],       # 这个地点的永久改造 [{name, creator, desc, tick}]
            "vibe": "普通",             # 地点氛围(由历史事件塾积而成)
        }

    # 尝试从快照恢复
    snapshot_path = "/home/ubuntu/world_state_snapshot.json"
    if os.path.exists(snapshot_path):
        try:
            with open(snapshot_path, "r") as f:
                snap = json.load(f)
            world["time"] = snap["time"]
            world["events"] = snap.get("events", [])
            world["message_board"] = snap.get("message_board", [])
            world["moments"] = snap.get("moments", [])
            world["gallery"] = snap.get("gallery", [])
            world["world_narrative"] = snap.get("world_narrative", "")
            world["news_feed"] = snap.get("news_feed", [])
            world["hot_topics"] = snap.get("hot_topics", [])
            world["weather"] = snap.get("weather", world["weather"])
            world["food_prices"] = snap.get("food_prices", {})
            # v9.0: 恢复进化引擎数据
            world["world_modifications"] = snap.get("world_modifications", [])
            world["urban_legends"] = snap.get("urban_legends", [])
            world["generation_count"] = snap.get("generation_count", 0)
            world["graveyard"] = snap.get("graveyard", [])
            world["reputation_board"] = snap.get("reputation_board", {})
            world["active_rules"] = snap.get("active_rules", [])

            for bid, bdata in snap.get("bots", {}).items():
                bot = create_bot(bid)
                # 恢复数值
                for key in ["hp", "money", "energy", "satiety", "status", "job", "location",
                            "skills", "inventory", "relationships", "action_log", "is_sleeping",
                            "current_task", "selfie_count", "desires", "emotions",
                            "phone_battery", "values", "core_memories", "emotional_bonds",
                            "long_term_goal", "pending_reply_to", "recent_actions_synced",
                            "narrative_summary", "current_activity",
                            # v9.0
                            "reputation", "created_things", "generation",
                            "inherited_from", "known_legends"]:
                    if key in bdata:
                        bot[key] = bdata[key]
                # 家庭关系：如果快照中为空则用默认值
                family = bdata.get("family", {})
                if not family or (not family.get("parents") and not family.get("children")):
                    bot["family"] = FAMILY_RELATIONS.get(bid, {"parents": [], "children": []})
                else:
                    bot["family"] = family
                # 确保v8新字段存在
                if "emotions" not in bot or not bot["emotions"]:
                    bot["emotions"] = {"happiness": 50, "sadness": 10, "anger": 5, "anxiety": 20, "loneliness": 30}
                if "phone_battery" not in bot:
                    bot["phone_battery"] = 100
                world["bots"][bid] = bot
                loc = bot["location"]
                if loc in world["locations"] and bid not in world["locations"][loc]["bots"]:
                    world["locations"][loc]["bots"].append(bid)

            # v9.0: 恢复地点的公共记忆和改造
            for loc_name in world["locations"]:
                loc_snap = snap.get("locations", {}).get(loc_name, {})
                if loc_snap:
                    world["locations"][loc_name]["public_memory"] = loc_snap.get("public_memory", [])
                    world["locations"][loc_name]["modifications"] = loc_snap.get("modifications", [])
                    world["locations"][loc_name]["vibe"] = loc_snap.get("vibe", "普通")

            log.info(f"从快照恢复成功: tick={world['time']['tick']}, {len(world['bots'])}个Bot")
            return
        except Exception as e:
            log.error(f"快照恢复失败: {e}")

    # 全新世界
    for bid in PERSONAS:
        bot = create_bot(bid)
        world["bots"][bid] = bot
        loc = bot["location"]
        world["locations"][loc]["bots"].append(bid)

    # 初始新闻
    from systems.news import inject_news
    inject_news()

    # === v10.1: 注入种子规则（打破冷启动） ===
    from rules.rules_engine import create_rule
    seed_rules = [
        create_rule(
            name="早餐摒老李的炒粉摒",
            creator_id="npc_vendor", creator_name="早餐摒老李",
            location="宝安城中村",
            trigger="every_tick",
            condition={"and": [{"time_between": [6, 22]}, {"random": 0.15}]},
            effects=[
                {"type": "modify_bot_attr", "attr": "satiety", "delta": 35, "cost_money": 12},
                {"type": "modify_bot_emotion", "emotion": "happiness", "delta": 3},
                {"type": "generate_income", "target": "creator", "amount": 0},
                {"type": "narrative", "text": "老李的炒粉摒飘来阵阵香气，有人忍不住停下脚步买了一份"},
            ],
            description="宝安城中村的早餐摒老李每天卖炒粉，香气四溢，经过的人忍不住买一份",
            durability=500, decay_rate=0.02,
        ),
        create_rule(
            name="华强北地摒经济",
            creator_id="system", creator_name="城市系统",
            location="华强北",
            trigger="every_tick",
            condition={"and": [{"time_between": [9, 21]}, {"random": 0.1}]},
            effects=[
                {"type": "modify_bot_emotion", "emotion": "vanity", "delta": 2},
                {"type": "narrative", "text": "华强北的商贩们在大声吾喝，各种电子产品的叫卖声此起彼伏"},
            ],
            description="华强北的地摒经济永远充满活力，各种商品交易和小生意在这里不断发生",
            durability=999, decay_rate=0.005,
        ),
        create_rule(
            name="深圳湾公园的宁静",
            creator_id="system", creator_name="城市系统",
            location="深圳湾公园",
            trigger="every_tick",
            condition={"random": 0.2},
            effects=[
                {"type": "modify_bot_attr", "attr": "energy", "delta": 5},
                {"type": "modify_bot_emotion", "emotion": "happiness", "delta": 5},
                {"type": "modify_bot_emotion", "emotion": "anxiety", "delta": -3},
                {"type": "attract_bot", "chance": 0.05, "location": "深圳湾公园", "message": "海风徐徐，公园里传来宁静的气息"},
            ],
            description="深圳湾公园的海风和绿地让人心旷神怡，恢复精力和快乐",
            durability=999, decay_rate=0.005,
        ),
        create_rule(
            name="福田CBD的压力",
            creator_id="system", creator_name="城市系统",
            location="福田CBD",
            trigger="every_tick",
            condition={"and": [{"time_between": [9, 18]}, {"random": 0.15}]},
            effects=[
                {"type": "modify_bot_emotion", "emotion": "anxiety", "delta": 3},
                {"type": "modify_bot_emotion", "emotion": "vanity", "delta": 2},
                {"type": "narrative", "text": "周围的白领们行色匹匹，每个人都在为生活拼命"},
            ],
            description="福田CBD的快节奏让人焦虑但也刺激野心",
            durability=999, decay_rate=0.005,
        ),
        create_rule(
            name="东门老街的日结工招募",
            creator_id="npc_boss", creator_name="包工头老陈",
            location="东门老街",
            trigger="every_tick",
            condition={"and": [{"time_between": [7, 17]}, {"random": 0.1}]},
            effects=[
                {"type": "modify_bot_attr", "attr": "money", "delta": 80, "cost_money": 0},
                {"type": "modify_bot_attr", "attr": "energy", "delta": -30},
                {"type": "narrative", "text": "包工头老陈在招日结工，干一天能拿80块"},
            ],
            description="东门老街的包工头老陈每天招日结工，辛苦但能赚钱",
            durability=800, decay_rate=0.01,
        ),
    ]
    for sr in seed_rules:
        sr["created_tick"] = 0
    world["active_rules"] = seed_rules
    log.info(f"v10.1: 注入{len(seed_rules)}条种子规则")

    log.info("全新世界初始化完成")
