import random, logging
from core.world_state import world, log
from core.constants import RANDOM_EVENTS


PERSONAL_FATE_EVENTS = [
    # 经济类（有实质后果）
    {"name": "手机被偷了", "desc": "你发现口袋里的手机不见了！可能是刚才挤公交的时候被偷的。",
     "effect": {"money": -200, "mood": {"anxiety": 20, "anger": 15, "sadness": 10}}},
    {"name": "在路上捜到一个钱包", "desc": "路边有一个钱包，里面有200块和一张身份证。你要怎么办？",
     "effect": {"money": 200, "mood": {"happiness": 5, "anxiety": 5}},
     "moral_dilemma": True},
    {"name": "房东通知下月涨租200", "desc": "房东发来消息：“下个月开始租金涨200，不接受的话可以找别的地方。”",
     "effect": {"mood": {"anxiety": 15, "anger": 10}}},
    {"name": "收到老家汇来的1000块", "desc": "父母给你转了1000块，附言“在外面别乱花钱，注意身体”。",
     "effect": {"money": 1000, "mood": {"happiness": 10, "sadness": 5, "loneliness": -10}}},
    # 工作类
    {"name": "被老板炒了", "desc": "老板说最近生意不好，要裁员，你被辞退了。",
     "effect": {"job_lost": True, "mood": {"sadness": 20, "anxiety": 15, "anger": 10}}},
    {"name": "有人给你介绍了一份好工作", "desc": "朋友说有个地方在招人，待遇不错，问你有没有兴趣。",
     "effect": {"mood": {"happiness": 8, "anxiety": -5}}},
    # 社交类（涉及其他bot）
    {"name": "有人在背后说你坏话", "desc": "你无意中听到有人在说你的坏话，说你“不靠谱”。",
     "effect": {"mood": {"anger": 15, "sadness": 10, "anxiety": 8}},
     "social": "gossip_victim"},
    {"name": "有人向你借钱", "desc": "附近的人过来说：“兄弟，能借我100块吗？我这个月实在周转不开。”",
     "effect": {"mood": {"anxiety": 5}},
     "social": "borrow_request"},
    {"name": "有人送了你一份礼物", "desc": "一个你认识的人送了你一份小礼物，说“上次谢谢你帮忙”。",
     "effect": {"mood": {"happiness": 12, "loneliness": -8}}},
    # 道德困境
    {"name": "看到有人在偷东西", "desc": "你看到一个人在偷超市的东西，他发现你看到了，用哀求的眼神看着你。",
     "effect": {"mood": {"anxiety": 10, "sadness": 5}},
     "moral_dilemma": True},
    {"name": "老人在路边摔倒了", "desc": "一个老人在你面前摘倒了，周围的人都在观望，没人上前。",
     "effect": {"mood": {"anxiety": 8, "sadness": 5}},
     "moral_dilemma": True},
    # 意外惊喜
    {"name": "买彩票中了200块", "desc": "你买的彩票居然中了200块！虽然不多，但心情很好。",
     "effect": {"money": 200, "mood": {"happiness": 15}}},
    {"name": "被狗追着跑了三条街", "desc": "一只没拴绳的大狗突然向你冲过来，你拔腿就跑。",
     "effect": {"energy": -15, "mood": {"anxiety": 12, "anger": 5}}},
    {"name": "在公园里遇到了老乡", "desc": "竟然在深圳遇到了老家的熟人！两人聊了很久，感觉很亲切。",
     "effect": {"mood": {"happiness": 15, "loneliness": -20, "sadness": 5}}},
    {"name": "食物中毒了", "desc": "吃了路边摆的东西后肠胃特别难受，可能不干净。",
     "effect": {"energy": -20, "satiety": -30, "mood": {"sadness": 10, "anger": 8}}},
]


def trigger_event():
    event = random.choice(RANDOM_EVENTS)
    world["events"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "event": event["name"],
        "desc": event["desc"],
    })
    world["active_effects"].append({
        "effect": event["effect"],
        "expires_tick": world["time"]["tick"] + 2,
        "mood": event.get("mood", {}),
    })
    # 对所有存活Bot施加情绪影响
    mood_effect = event.get("mood", {})
    for bid, bot in world["bots"].items():
        if bot["status"] != "alive" or bot.get("is_sleeping"):
            continue
        emotions = bot.get("emotions", {})
        for emo_key, delta in mood_effect.items():
            emotions[emo_key] = max(0, min(100, emotions.get(emo_key, 0) + delta))
        bot["emotions"] = emotions
    # 特殊效果
    if event["effect"] == "found_money":
        alive = [bid for bid, b in world["bots"].items() if b["status"] == "alive" and not b.get("is_sleeping")]
        if alive:
            lucky = random.choice(alive)
            world["bots"][lucky]["money"] += 50
            log.info(f"{lucky} 捡到了50块钱！")
    elif event["effect"] == "free_food":
        alive = [bid for bid, b in world["bots"].items() if b["status"] == "alive" and not b.get("is_sleeping")]
        for bid in alive:
            if random.random() < 0.3:
                world["bots"][bid]["satiety"] = min(100, world["bots"][bid]["satiety"] + 15)
                log.info(f"{bid} 吃到了免费试吃！")

    log.warning(f'!!! 随机事件: {event["name"]} - {event["desc"]}')


def trigger_personal_fate(bot_id=None):
    """v8.4: 对单个随机bot触发个人命运事件，有实质后果"""
    alive = [bid for bid, b in world["bots"].items() if b["status"] == "alive" and not b.get("is_sleeping")]
    if not alive:
        return
    target = bot_id or random.choice(alive)
    bot = world["bots"][target]
    event = random.choice(PERSONAL_FATE_EVENTS)
    eff = event["effect"]

    # 应用金钱效果
    if "money" in eff:
        bot["money"] = max(0, bot["money"] + eff["money"])
    # 应用能量效果
    if "energy" in eff:
        bot["energy"] = max(0, min(100, bot["energy"] + eff["energy"]))
    # 应用饱腹度效果
    if "satiety" in eff:
        bot["satiety"] = max(0, min(100, bot["satiety"] + eff["satiety"]))
    # 应用情绪效果
    mood_eff = eff.get("mood", {})
    emotions = bot.get("emotions", {})
    for emo_key, delta in mood_eff.items():
        emotions[emo_key] = max(0, min(100, emotions.get(emo_key, 0) + delta))
    bot["emotions"] = emotions
    # 失去工作
    if eff.get("job_lost") and bot.get("job"):
        bot["job"] = None
        bot["current_task"] = None

    # 通过消息板发送给目标bot，让它在下一次心跳时感知到
    world["message_board"].append({
        "to": target,
        "from": "fate",
        "msg": f"【命运事件】{event['name']}: {event['desc']}",
        "tick": world["time"]["tick"],
        "priority": "high",
    })

    # 记录到世界事件
    world["events"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "event": f"{bot['name']}: {event['name']}",
        "desc": event["desc"],
    })

    # 如果涉及其他bot（借钱、八卦），随机选择一个附近的bot作为关联方
    if event.get("social"):
        loc = bot["location"]
        nearby = [b for b in world["locations"].get(loc, {}).get("bots", []) if b != target]
        if nearby:
            other = random.choice(nearby)
            other_name = world["bots"][other].get("name", "?")
            if event["social"] == "borrow_request":
                # 让目标bot知道是谁借钱
                world["message_board"][-1]["msg"] += f" (是{other_name}向你借钱)"
            elif event["social"] == "gossip_victim":
                world["message_board"][-1]["msg"] += f" (似乎是{other_name}在说)"

    log.warning(f'☄️ 命运事件: {bot["name"]}({target}) - {event["name"]}')
