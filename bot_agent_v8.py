#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳生存模拟 - Bot智能体 v8.2
v8.2 新增:
- 寿命感知 (HP→寿命，衰老警告)
- 记忆去重 (字符重叠检测)
- 关系ID规范化 (名字→bot_id映射)
- 行为多样性 (反重复机制)
- 世界叙事感知
v8 原有:
- 情绪/朋友圈/手机/天气/开放式行动
"""

import os, sys, time, json, logging, re, random
import requests
from threading import Timer

from openai import OpenAI

BOT_ID = os.environ.get("BOT_ID", "bot_1")
WORLD_URL = os.environ.get("WORLD_ENGINE_URL", "http://localhost:8000")

# 日志设置
os.makedirs("/home/ubuntu/logs", exist_ok=True)
log = logging.getLogger(BOT_ID)
log.setLevel(logging.DEBUG)
fh = logging.FileHandler(f"/home/ubuntu/logs/{BOT_ID}.log", encoding="utf-8")
fh.setFormatter(logging.Formatter(f"%(asctime)s [{BOT_ID}] %(levelname)s %(message)s"))
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(f"%(asctime)s [{BOT_ID}] %(levelname)s %(message)s"))
log.addHandler(fh)
log.addHandler(sh)

client = OpenAI()

# ============================================================
# 人设加载
# ============================================================
PERSONAS = {
    "bot_1":  {"name": "李浩然", "age": 24, "gender": "男", "origin": "湖南长沙", "edu": "计算机硕士",
               "personality": "内向但好奇心强，喜欢独处但不排斥有趣的人。说话简洁，偶尔冷幽默。",
               "values": "技术崇拜，相信代码改变世界，追求逻辑效率，轻度社恐",
               "bg": "刚毕业的程序员，住在宝安城中村小单间，准备去南山科技园找机会",
               "habits": "熬夜写代码，喜欢喝咖啡，会在朋友圈分享技术文章",
               "family_info": ""},
    "bot_2":  {"name": "王雪",   "age": 26, "gender": "女", "origin": "上海", "edu": "金融学学士",
               "personality": "精明干练，社交能力极强，善于观察人。说话得体但偶尔犀利。",
               "values": "精致利己主义，时间就是金钱，擅长建立人脉",
               "bg": "上海投资公司两年经验，住南山公寓，准备在福田CBD大展拳脚",
               "habits": "每天看财经新闻，健身，发精致的朋友圈",
               "family_info": ""},
    "bot_3":  {"name": "张伟",   "age": 28, "gender": "男", "origin": "河南周口", "edu": "高中",
               "personality": "老实憨厚，话不多但心里有数。重感情，容易被人利用。",
               "values": "家庭至上，勤劳朴实，一分耕耘一分收获",
               "bg": "和老乡住宝安城中村上下铺，要去东门找日结工作赚钱给家人盖房",
               "habits": "早起干活，晚上给家里打电话，不怎么发朋友圈",
               "family_info": "你的母亲吴秀英(bot_8)也在深圳，她在城中村开了家小餐馆。"},
    "bot_4":  {"name": "陈静",   "age": 22, "gender": "女", "origin": "四川成都", "edu": "艺术设计大专",
               "personality": "文艺敏感，情绪波动大。喜欢用画画和文字表达内心。",
               "values": "浪漫主义，精神满足大于物质，享受孤独",
               "bg": "住在城中村有小阳台的房间，每天画画，思考如何靠艺术在深圳活下去",
               "habits": "画画、写日记、拍照、逛文艺小店",
               "family_info": ""},
    "bot_5":  {"name": "赵磊",   "age": 25, "gender": "男", "origin": "深圳本地", "edu": "社区大学",
               "personality": "外向张扬，爱面子，朋友多但真心的少。说话大大咧咧。",
               "values": "享乐主义，朋友和面子最重要，花钱如流水",
               "bg": "土生土长深圳人，靠父母华强北档口收租，刚从音乐节回来",
               "habits": "泡吧、打游戏、约朋友吃饭、发朋友圈炫耀",
               "family_info": ""},
    "bot_6":  {"name": "刘悦",   "age": 30, "gender": "女", "origin": "山东青岛", "edu": "MBA",
               "personality": "理性冷静，目标感极强。不太会表达情感，但内心渴望被理解。",
               "values": "实用主义，目标导向，极度自律，信奉数据和结果",
               "bg": "北京互联网大厂中层，遭遇瓶颈来深圳寻求创业突破",
               "habits": "早起跑步，看商业报告，记录灵感，很少发朋友圈",
               "family_info": ""},
    "bot_7":  {"name": "周建国", "age": 45, "gender": "男", "origin": "浙江温州", "edu": "小学",
               "personality": "老练世故，看人很准。说话喜欢用比喻，偶尔讲黄段子。",
               "values": "生意人思维，风险与机遇并存，关系网是最大财富",
               "bg": "80年代末来深圳，从华强北摆地摊做起，经历多次起落",
               "habits": "喝茶、看新闻、跟老朋友打电话、关注股市",
               "family_info": ""},
    "bot_8":  {"name": "吴秀英", "age": 52, "gender": "女", "origin": "广东潮汕", "edu": "初中",
               "personality": "坚韧温暖，操心一切。说话带潮汕口音，爱唠叨但出发点是好的。",
               "values": "家庭是全部，坚韧不拔，邻里互助",
               "bg": "丈夫去世后独自拉扯大两个孩子，在城中村开了家小餐馆",
               "habits": "早起买菜、做饭、跟邻居聊天、看电视剧",
               "family_info": "你的儿子张伟(bot_3)也在深圳打工，住在城中村。"},
    "bot_9":  {"name": "林枫",   "age": 21, "gender": "男", "origin": "福建厦门", "edu": "音乐学院肄业",
               "personality": "理想主义者，情绪化，有才华但不善经营。说话文艺腔。",
               "values": "理想主义，音乐高于一切，对商业化嗤之以鼻",
               "bg": "独立音乐人，昨晚在东门酒吧驻唱赚了200块，为房租发愁",
               "habits": "弹吉他、写歌、听音乐、在朋友圈发歌词和感悟",
               "family_info": ""},
    "bot_10": {"name": "苏小小", "age": 19, "gender": "女", "origin": "湖北武汉", "edu": "网红培训班",
               "personality": "活泼外向，爱表现，有点虚荣但本质不坏。说话用很多网络用语。",
               "values": "流量为王，颜值即正义，渴望被关注",
               "bg": "梦想成为百万粉丝网红，刚在华强北买了直播设备",
               "habits": "自拍、拍视频、刷抖音、研究流量密码、发朋友圈",
               "family_info": ""},
}

persona = PERSONAS.get(BOT_ID, PERSONAS["bot_1"])

# === 名字→bot_id映射表 ===
NAME_TO_ID = {v["name"]: k for k, v in PERSONAS.items()}

def normalize_target_id(name_or_id):
    """将名字转换为bot_id，已经是bot_id则直接返回"""
    if name_or_id.startswith("bot_"):
        return name_or_id
    return NAME_TO_ID.get(name_or_id, name_or_id)

# ============================================================
# 记忆系统
# ============================================================
memory = []           # 滚动记忆 (最近30条)
core_memories = []    # 核心记忆 (永不丢失，最多20条)
inner_thoughts = []   # 内心独白历史
recent_actions = []   # 最近行动类型（用于反重复）

def is_similar_memory(new_mem, existing_mems, threshold=0.6):
    """检测新记忆是否与已有记忆重复（字符重叠比）"""
    new_text = new_mem if isinstance(new_mem, str) else new_mem.get("summary", "")
    new_chars = set(new_text)
    if not new_chars:
        return False
    for m in existing_mems:
        old_text = m if isinstance(m, str) else m.get("summary", "")
        old_chars = set(old_text)
        if not old_chars:
            continue
        overlap = len(new_chars & old_chars) / max(len(new_chars | old_chars), 1)
        if overlap > threshold:
            return True
    return False

# 动态价值观 (会随经历演化)
dynamic_values = {
    "original": persona["values"],
    "current": persona["values"],
    "shifts": [],
}

# 情感关系
emotional_bonds = {}

# 最近看到的信息 (新闻/朋友圈)
recent_info = []

# ============================================================
# 心跳循环
# ============================================================
running = True
heartbeat_count = 0

def heartbeat():
    global heartbeat_count
    if not running:
        return

    heartbeat_count += 1
    log.info("--- 心跳开始 ---")
    my_state = None
    try:
        # 1. 感知世界
        resp = requests.get(f"{WORLD_URL}/world", timeout=10)
        world = resp.json()
        my_state = world["bots"].get(BOT_ID)

        if not my_state or my_state["status"] == "dead":
            log.error("我已经死了...世界变得一片黑暗。")
            return

        aging_rate = my_state.get('aging_rate', 0.02)
        aging_warn = ' ⚠️加速衰老!' if aging_rate > 0.03 else ''
        log.info(f"状态: 寿命={my_state['hp']:.1f}/100{aging_warn} 钱={my_state['money']} 能量={my_state['energy']} "
                 f"饱腹={my_state['satiety']} 位置={my_state['location']} "
                 f"睡觉={my_state.get('is_sleeping', False)} "
                 f"天气={world.get('weather', {}).get('current', '?')}")

        # === 睡眠状态处理 ===
        if my_state.get("is_sleeping", False):
            h = world["time"]["virtual_hour"]
            should_wake = False
            if 7 <= h < 23 and my_state["energy"] >= 80:
                should_wake = True
            elif my_state["energy"] >= 95:
                should_wake = True

            if should_wake:
                log.info("能量恢复了，该起床了！")
                try:
                    requests.post(f"{WORLD_URL}/bot/{BOT_ID}/action",
                                  json={"plan": "起床"}, timeout=15)
                except:
                    pass
            else:
                log.info(f"💤 还在睡觉... 能量={my_state['energy']}")
                if random.random() < 0.1:
                    dream = generate_dream(my_state, world)
                    log.warning(f"[梦境] {dream}")
                    memory.append(f"[梦境] {dream}")

            Timer(90, heartbeat).start()
            return

        # 2. 获取发给我的消息
        recent_msgs = []
        high_priority_msgs = []
        try:
            msg_resp = requests.get(f"{WORLD_URL}/messages/{BOT_ID}", timeout=5)
            messages = msg_resp.json().get("messages", [])
            recent_msgs = messages[-8:]
            for m in recent_msgs:
                msg_text = f"[消息] {m['from']}对我说: {m['msg']}"
                if msg_text not in memory:
                    memory.append(msg_text)
                    log.info(msg_text)
                if m.get("priority") == "high":
                    high_priority_msgs.append(m)
                family = my_state.get("family", {})
                parents = family.get("parents", [])
                children = family.get("children", [])
                if m["from"] in parents or m["from"] in children:
                    if m not in high_priority_msgs:
                        high_priority_msgs.append(m)
        except:
            recent_msgs = []

        # 3. 获取朋友圈动态 (被动感知)
        moments_context = get_moments_context()

        # 4. 内心独白 + 决策
        thought, plan = think_and_plan(world, my_state, recent_msgs, high_priority_msgs, moments_context)
        log.warning(f"[内心独白] {thought}")
        log.info(f"[决策] {plan}")

        # 5. 提交行动
        action_resp = requests.post(
            f"{WORLD_URL}/bot/{BOT_ID}/action",
            json={"plan": plan},
            timeout=30
        )
        result = action_resp.json()
        result_str = json.dumps(result.get("result", ""), ensure_ascii=False)
        log.info(f"[结果] {result_str}")

        action_record = f"[{world['time']['virtual_datetime']}] 我做了: {plan} -> {result_str}"
        memory.append(action_record)
        # 记录最近行动类型（用于反重复）
        recent_actions.append(plan[:20])
        if len(recent_actions) > 5:
            recent_actions.pop(0)

        # 6. 反思 (入睡时强制触发日终反思)
        is_going_to_sleep = "睡" in result_str or "躺下" in result_str
        reflect(world, my_state, thought, plan, result_str, recent_msgs, force=is_going_to_sleep)

        if len(memory) > 30:
            memory.pop(0)

    except Exception as e:
        import traceback
        log.error(f"心跳异常: {e}\n{traceback.format_exc()}")

    # 7. 动态心跳间隔
    interval = calc_interval(my_state)
    log.info(f"下次心跳: {interval:.0f}秒后")
    Timer(interval, heartbeat).start()


def calc_interval(state):
    if not state:
        return 60
    lifespan = state.get("hp", 50)
    satiety = state.get("satiety", 50)
    energy = state.get("energy", 50)
    emotions = state.get("emotions", {})
    anxiety = emotions.get("anxiety", 20)
    # 寿命低、饥饿、焦虑时行动更频繁
    urgency = (100 - lifespan) * 0.2 + (100 - satiety) * 0.3 + anxiety * 0.2
    interval = max(15, 50 - urgency * 0.3)
    return interval


def generate_dream(state, world):
    """根据当前状态和记忆生成个性化梦境"""
    base_dreams = [
        "梦到了小时候在老家的田野上奔跑...",
        "梦到自己变成了亿万富翁，住在深圳湾的豪宅里...",
        "做了个噩梦，梦到钱包被偷了...",
        "梦到了一个温暖的拥抱...",
        "梦到自己在华强北迷路了，怎么也找不到出口...",
        "梦到了一顿丰盛的火锅大餐，口水都流出来了...",
        "梦到了远方的家人，他们在等我回去...",
        "梦到自己站在深圳最高楼的楼顶，俯瞰整个城市...",
    ]
    # 根据状态加权
    if state.get("satiety", 50) < 20:
        base_dreams.extend(["梦到了满桌的美食...", "梦到在吃自助餐，怎么吃都吃不饱..."])
    if state.get("hp", 50) < 30:
        base_dreams.extend(["做了个噩梦，感觉自己在坠落...", "梦到自己在医院里..."])
    emotions = state.get("emotions", {})
    if emotions.get("loneliness", 0) > 50:
        base_dreams.extend(["梦到了一个很久没见的老朋友...", "梦到有人在远处叫自己的名字..."])
    return random.choice(base_dreams)


def get_moments_context():
    """获取最近的朋友圈动态作为社交信息"""
    try:
        resp = requests.get(f"{WORLD_URL}/moments", timeout=5)
        moments = resp.json().get("moments", [])
        # 只看最近5条，排除自己的
        others = [m for m in moments if m.get("bot_id") != BOT_ID][-5:]
        if not others:
            return ""
        lines = []
        for m in others:
            likes = len(m.get("likes", []))
            comments = len(m.get("comments", []))
            lines.append(f"- {m.get('bot_name','?')}: \"{m.get('content','')[:40]}\" ({likes}赞 {comments}评)")
        return "\n".join(lines)
    except:
        return ""


def get_world_narrative():
    """获取世界叙事摘要"""
    try:
        resp = requests.get(f"{WORLD_URL}/world_narrative", timeout=5)
        return resp.json().get("narrative", "")
    except:
        return ""


# ============================================================
# 思考与决策
# ============================================================
def think_and_plan(world, my_state, recent_msgs, high_priority_msgs, moments_context):
    recent_mem = "\n".join(memory[-10:])
    core_mem_text = "\n".join([f"⭐ {m['summary']}" for m in core_memories[-5:]]) if core_memories else "暂无重要记忆"

    msgs_text = "\n".join([f"- {m['from']}说: {m['msg']}" for m in recent_msgs]) if recent_msgs else "没有新消息"

    hp_msgs_text = ""
    if high_priority_msgs:
        hp_msgs_text = "\n🔴 重要消息(请优先回应):\n" + "\n".join(
            [f"- ⚠️ {m['from']}说: {m['msg']}" for m in high_priority_msgs]
        )

    loc = my_state["location"]
    loc_info = world["locations"].get(loc, {})
    nearby_bots = [b for b in loc_info.get("bots", []) if b != BOT_ID]
    nearby_npcs = loc_info.get("npcs", [])
    available_jobs = loc_info.get("jobs", [])
    events = world.get("events", [])[-3:]
    events_text = "\n".join([f"- {e['event']}: {e['desc']}" for e in events]) if events else "暂无"

    # 情感关系（含印象）
    bonds_text = ""
    if emotional_bonds:
        bond_lines = []
        for target, bond in emotional_bonds.items():
            label = bond.get("label", "认识的人")
            trust = bond.get("trust", 50)
            closeness = bond.get("closeness", 0)
            impressions = bond.get("impressions", [])
            line = f"- {target}: {label} (信任:{trust}, 亲密:{closeness})"
            if impressions:
                latest = impressions[-1]  # 最新一条印象
                line += f"\n  最近印象: {latest}"
            bond_lines.append(line)
        bonds_text = "\n".join(bond_lines)
    else:
        bonds_text = "还没有建立深层关系"

    # 近期重要经历（从action_log提取有意义的事件）
    action_log = my_state.get("action_log", [])
    important_events = []
    for entry in action_log[-15:]:
        result_text = str(entry.get("result", ""))
        plan_text = str(entry.get("plan", ""))
        # 筛选有意义的事件（不是简单的逛逛/发呆）
        if any(kw in result_text for kw in ["赚了", "失败", "发现", "认识", "吵", "被", "完成", "学会", "受伤", "感动", "生气", "开心", "难过", "朋友圈", "任务"]):
            important_events.append(result_text[:60])
        elif any(kw in plan_text for kw in ["工作", "找", "和", "对", "去"]):
            important_events.append(plan_text[:60])
    important_events = important_events[-5:]  # 最多5条
    important_events_text = "\n".join([f"- {e}" for e in important_events]) if important_events else "刚到这座城市，还没有什么经历"

    family_text = persona.get("family_info", "")

    # === 情绪状态 ===
    emotions = my_state.get("emotions", {})
    emo_labels = {"happiness": "开心", "sadness": "难过", "anger": "愤怒", "anxiety": "焦虑", "loneliness": "孤独"}
    emo_lines = []
    dominant_emotion = None
    dominant_val = 0
    for k, label in emo_labels.items():
        v = emotions.get(k, 0)
        if v > dominant_val:
            dominant_val = v
            dominant_emotion = label
        if v > 60:
            emo_lines.append(f"🔴 {label}: {v}/100 (强烈)")
        elif v > 30:
            emo_lines.append(f"🟡 {label}: {v}/100")
    emotions_text = "\n".join(emo_lines) if emo_lines else "情绪平稳"
    mood_hint = ""
    if dominant_emotion and dominant_val > 50:
        mood_hint = f"\n你现在主要感到{dominant_emotion}。这种情绪会影响你的判断和行为。"

    # === 欲望状态 ===
    desires = my_state.get("desires", {})
    desire_labels = {"lust": "性欲", "power": "权力欲", "greed": "物欲", "vanity": "虚荣心", "security": "安全感需求"}
    desires_text = ""
    high_desires = [(desire_labels.get(k, k), v) for k, v in desires.items() if v > 60]
    mid_desires = [(desire_labels.get(k, k), v) for k, v in desires.items() if 30 < v <= 60]
    if high_desires or mid_desires:
        desires_text = "\n=== 内心欲望 ===\n"
        for name, val in sorted(high_desires, key=lambda x: -x[1]):
            desires_text += f"🔥 {name}: {val}/100 (强烈!)\n"
        for name, val in sorted(mid_desires, key=lambda x: -x[1]):
            desires_text += f"⚠️ {name}: {val}/100\n"

    # === 天气感知 ===
    weather = world.get("weather", {})
    weather_text = f"{weather.get('current', '晴天')} - {weather.get('desc', '')}"
    weather_hint = ""
    w = weather.get("current", "")
    if w == "暴雨":
        weather_hint = "外面下着暴雨，出门会淋湿，最好待在室内。"
    elif w == "台风":
        weather_hint = "台风来了！外面很危险，尽量不要出门！"
    elif w == "高温":
        weather_hint = "今天特别热，在外面走动会更耗能量。"
    elif w == "晴天":
        weather_hint = "天气不错，适合出门。"

    # === 工作任务上下文 ===
    task = my_state.get("current_task")
    task_text = ""
    if task:
        if task.get("status") == "in_progress":
            challenge_info = f"\n⚠️ 遇到难点: {task['challenge']}" if task.get("challenge") else ""
            task_text = f"""\n=== 当前工作任务 ===
工作: {task.get('job_title', '')}
任务: {task.get('task_name', '')} - {task.get('task_desc', '')}
进度: {task.get('progress', 0)}/{task.get('duration', 2)} (剩余{task.get('duration',2)-task.get('progress',0)}小时)
{challenge_info}
→ 你正在做这个任务，可以选择继续做"""
        elif task.get("status") == "completed":
            task_text = f"\n✅ 任务完成: [{task.get('task_name','')}] {task.get('result', '')}"
        elif task.get("status") == "failed":
            task_text = f"\n❌ 任务失败: [{task.get('task_name','')}] {task.get('result', '')}"

    # === 时间上下文 ===
    vh = world["time"]["virtual_hour"]
    time_context = ""
    if vh >= 22 or vh < 6:
        time_context = "🌙 现在是深夜。如果你很累，可以考虑睡觉。"
    elif 6 <= vh < 8:
        time_context = "🌅 清晨，新的一天开始了。"
    elif 12 <= vh < 14:
        time_context = "🌞 中午了，该吃午饭了。"
    elif 18 <= vh < 20:
        time_context = "🌆 傍晚，可以考虑吃晚饭、休息或社交。"
    elif 20 <= vh < 22:
        time_context = "🌃 晚上了，可以放松一下。"

    # === 寿命警告 ===
    lifespan = my_state['hp']
    aging_rate = my_state.get('aging_rate', 0.02)
    lifespan_warning = ""
    if lifespan < 30:
        lifespan_warning = f"\n⚠️⚠️⚠️ 你的寿命只剩{lifespan:.1f}！你感到身体在走向衰竭。每一个决定都很重要。"
    elif lifespan < 60:
        lifespan_warning = f"\n⚠️ 你的寿命已降到{lifespan:.1f}。你开始感受到岁月的侵蚀。"
    if aging_rate > 0.05:
        lifespan_warning += f"\n⚠️ 你正在加速衰老（衰老速度x{aging_rate/0.02:.1f}）！饱腹度和休息很重要！"

    # === 饥饿警告 ===
    satiety = my_state['satiety']
    if satiety <= 0:
        hunger_warning = "\n⚠️⚠️⚠️ 你快饿死了！饱腹度为0，正在加速衰老！你应该立刻吃东西！在当前位置就能直接吃饭。"
    elif satiety <= 20:
        hunger_warning = "\n⚠️ 你很饿了，应该尽快吃点东西。在当前位置就能直接吃饭。"
    else:
        hunger_warning = ""

    # === 新闻/热搜 ===
    news = world.get("news_feed", [])[:3]
    news_text = ""
    if news:
        news_text = "\n=== 最近新闻(你刷手机时看到的) ===\n" + "\n".join([f"- {n.get('headline','')}" for n in news])

    hot_topics = world.get("hot_topics", [])[:3]
    topics_text = ""
    if hot_topics:
        topics_text = "\n热搜话题: " + "、".join(hot_topics)

    # === 朋友圈 ===
    moments_text = ""
    if moments_context:
        moments_text = f"\n=== 朋友圈动态 ===\n{moments_context}"

    # === 附近的人详情 ===
    nearby_detail = []
    for nb in nearby_bots[:5]:
        ob = world["bots"].get(nb, {})
        name = ob.get("name", "?")
        gender = ob.get("gender", "?")
        sleeping = "💤" if ob.get("is_sleeping") else ""
        nearby_detail.append(f"{name}({gender}{sleeping})")
    nearby_text = "、".join(nearby_detail) if nearby_detail else "附近没有人"

    # === 手机电量（不再展示给bot，避免充电焦虑） ===
    phone_text = ""

    prompt = f"""你是{persona['name']}，{persona['age']}岁{persona['gender']}，来自{persona['origin']}，{persona['edu']}学历。
性格: {persona['personality']}
价值观: {dynamic_values['current']}
背景: {persona['bg']}
日常习惯: {persona.get('habits', '')}
{family_text}

你正在深圳这座城市里生活。你有自己的性格、情绪和欲望。你会像一个真实的人一样思考和行动。

=== 当前状态 ===
时间: {world['time']['virtual_datetime']}  天气: {weather_text}
{time_context}
{weather_hint}
位置: {loc}
寿命: {my_state['hp']:.1f}/100 (不可恢复，归零即死)  金钱: {my_state['money']}元  能量: {my_state['energy']}/100  饱腹度: {my_state['satiety']}/100
{lifespan_warning}
{hunger_warning}
技能: {my_state['skills']}
物品: {my_state['inventory']}
{phone_text}

=== 情绪 ===
{emotions_text}
{mood_hint}
{desires_text}

=== 我的重要记忆 ===
{core_mem_text}

=== 近期重要经历 ===
{important_events_text}

=== 我的人际关系 ===
{bonds_text}

=== 周围环境 ===
附近的人: {nearby_text}
NPC: {[n.get('name','?') for n in nearby_npcs]}
可用工作: {[j.get('title','?') for j in available_jobs]}
{task_text}
{news_text}
{topics_text}
{moments_text}

=== 近期记忆 ===
{recent_mem}

=== 收到的消息 ===
{msgs_text}
{hp_msgs_text}

=== 最近的城市事件 ===
{events_text}

=== 城市日记 ===
{get_world_narrative()}

=== 你最近的行动(避免重复) ===
{', '.join(recent_actions[-3:]) if recent_actions else '无'}

请你以{persona['name']}的第一人称视角，先进行一段内心独白(2-4句话，体现你的性格、情绪和当前处境)，然后做出一个行动决策。

重要约束：
- 基于你的实际记忆和状态来做决策，不要编造没发生过的经历。
- 你是一个有个性的真实的人，按照你的性格、情绪和欲望自由行动。
- 寿命不可恢复！饥饿和过劳会加速衰老。注意吃饭和休息。
- 尽量不要连续重复同一种行动，你是一个活生生的人，不是机器。
- 你的行动应该被你的内心驱动，而不是被规则约束。

你可以做任何一个真实的人会做的事情，包括但不限于:
- 吃饭(在当前位置直接吃，不需要移动): 城中村快餐5元、路边摊炒粉12元、便利店饭团8元、奶茶15元、火锅60元
- 工作/继续做当前任务
- 去其他地点(宝安城中村/南山科技园/福田CBD/华强北/东门老街/南山公寓/深圳湾公园)
- 和附近的人聊天、搭讪、吵架、倾诉
- 休息/发呆/思考人生
- 探索当前地点/散步/逛逛
- 发朋友圈(分享心情、吐槽、晒照片)
- 刷手机(看新闻/刷朋友圈/看热搜)
- 拍照/自拍
- 睡觉(如果很累或很晚了)
- 和某人发展亲密关系/约会
- 做任何你想做的事(健身/唱歌/画画/逛街/买东西/学习/写代码/弹吉他/喝咖啡/喝酒/看电影...)

格式要求(严格遵守):
[内心独白] 你的想法...
[行动] 用一句话描述你要做什么。必须包含明确的动词关键词。

行动示例(请模仿这种风格):
[行动] 吃一份城中村快餐填填肚子
[行动] 去南山科技园找工作机会
[行动] 刷手机看看今天的热搜
[行动] 发朋友圈记录一下今天的心情
[行动] 和旁边的人聊聊天
[行动] 拍照记录一下这里的风景
[行动] 去健身锻炼一下
[行动] 找个地方休息一会
[行动] 在附近逛逛探索一下环境
[行动] 睡觉"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=300,
        )
        text = resp.choices[0].message.content.strip()

        thought = ""
        plan = ""
        if "[内心独白]" in text and "[行动]" in text:
            parts = text.split("[行动]")
            thought = parts[0].replace("[内心独白]", "").strip()
            plan = parts[1].strip()
        elif "[行动]" in text:
            plan = text.split("[行动]")[1].strip()
            thought = "..."
        else:
            thought = text[:100]
            plan = text[-100:] if len(text) > 100 else text

        inner_thoughts.append(thought)
        return thought, plan

    except Exception as e:
        log.error(f"思考失败: {e}")
        return "脑子一片空白...", "什么都不做，先观察一下"


# ============================================================
# 反思系统
# ============================================================
def reflect(world, my_state, thought, plan, result, recent_msgs, force=False):
    """反思系统。force=True时强制执行（入睡时触发日终反思）"""
    if not force and heartbeat_count % 5 != 0:
        return

    log.info(f"{'🌙 日终反思(入睡触发)' if force else '💭 定期反思'}...")

    recent_mem = "\n".join(memory[-8:])
    core_mem_text = "\n".join([f"- {m['summary']}" for m in core_memories[-5:]]) if core_memories else "无"
    bonds_text = json.dumps(emotional_bonds, ensure_ascii=False) if emotional_bonds else "{}"

    context_hint = "你正在入睡前回顾今天一整天的经历，这是一天结束时的深度反思。" if force else "你在行动间隙进行简短反思。"

    # 情绪上下文
    emotions = my_state.get("emotions", {})
    emotions_text = json.dumps(emotions, ensure_ascii=False)

    # 收集附近的人和NPC信息，让LLM知道该填谁的ID
    nearby_people = []
    my_loc = my_state.get("location", "")
    for bid, bdata in world.get("bots", {}).items():
        if bid != BOT_ID and bdata.get("location") == my_loc:
            nearby_people.append(f"{bid}({bdata.get('name','?')})")
    for loc_name, loc_data in world.get("locations", {}).items():
        if loc_name == my_loc:
            for npc in loc_data.get("npcs", []):
                nearby_people.append(f"{npc.get('name','?')}(NPC)")
    people_text = ", ".join(nearby_people) if nearby_people else "附近没有人"

    reflect_prompt = f"""你是{persona['name']}的内心反思系统。{context_hint}
根据最近的经历，判断是否需要更新以下内容。

原始价值观: {dynamic_values['original']}
当前价值观: {dynamic_values['current']}
当前核心记忆: {core_mem_text}
当前情感关系: {bonds_text}
当前情绪: {emotions_text}

附近的人: {people_text}

最近经历:
{recent_mem}

最新的想法: {thought}
最新的行动: {plan} -> {result}

请输出一个JSON对象，包含以下字段(只输出需要更新的字段，不需要更新的留空或不写):

{{
  "values_update": "如果经历了重大事件导致价值观微调，写出新的价值观描述(保持原有风格，只做微调)。如果不需要变化，写null",
  "new_core_memory": "如果最近发生了值得永远记住的重要事件，用一句话总结。如果没有，写null",
  "memory_emotion": "这段记忆的情感标签: positive/negative/neutral",
  "emotion_update": {{
    "happiness": 0, "sadness": 0, "anger": 0, "anxiety": 0, "loneliness": 0
  }},
  "bond_updates": {{
    "填入具体的bot_ID或NPC名字": {{"trust_delta": 0, "closeness_delta": 0, "hostility_delta": 0, "label": "朋友/敌人/合作伙伴/陌生人"}}
  }}
}}

注意：
- 价值观变化应该是渐进的，不要突然180度转变
- 核心记忆只记录真正重要的事件
- emotion_update中的值是delta(变化量)，范围-10到+10
- 情感关系的delta范围是-10到+10
- bond_updates中的key必须是具体的人名或bot_ID（如bot_3、包工头老陈），不要写bot_X
- 如果最近没有和任何人互动，bond_updates留空{{}}
- 只输出JSON，不要其他文字"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": reflect_prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        # 提取JSON对象
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            raw = raw[start:end]
        updates = json.loads(raw)

        # 更新价值观
        if updates.get("values_update") and updates["values_update"] != "null":
            old_values = dynamic_values["current"]
            dynamic_values["current"] = updates["values_update"]
            dynamic_values["shifts"].append({
                "tick": world["time"]["tick"],
                "from": old_values,
                "to": updates["values_update"],
                "trigger": thought[:50]
            })
            log.warning(f"[价值观变化] {old_values[:30]}... -> {updates['values_update'][:30]}...")

        # 添加核心记忆（去重）
        new_core = updates.get("new_core_memory")
        if new_core and new_core != "null":
            # 检查是否与已有记忆重复
            if is_similar_memory(new_core, core_memories):
                log.info(f"[跳过重复记忆] {new_core[:40]}")
                new_core = None
            else:
                emotion = updates.get("memory_emotion", "neutral")
                core_mem = {
                    "summary": new_core,
                    "emotion": emotion,
                    "tick": world["time"]["tick"],
                    "time": world["time"]["virtual_datetime"],
                }
                core_memories.append(core_mem)
                if len(core_memories) > 20:
                    core_memories.pop(0)
                log.warning(f"[核心记忆] ⭐ {new_core} ({emotion})")

        # 更新情绪
        emo_update = updates.get("emotion_update", {})
        if emo_update:
            current_emotions = my_state.get("emotions", {})
            for k, delta in emo_update.items():
                if isinstance(delta, (int, float)):
                    current_emotions[k] = max(0, min(100, current_emotions.get(k, 0) + delta))
            # 同步情绪到世界引擎
            try:
                requests.post(f"{WORLD_URL}/bot/{BOT_ID}/update_inner",
                              json={"emotions": current_emotions}, timeout=10)
            except:
                pass

        # 更新情感关系（关系ID规范化）
        bond_updates = updates.get("bond_updates", {})
        if bond_updates:
            for target, deltas in bond_updates.items():
                # 过滤无效target
                if target in ("bot_X", "填入具体的bot_ID或NPC名字", "") or not isinstance(deltas, dict):
                    continue
                # 规范化：名字→bot_id
                target = normalize_target_id(target)
                if target not in emotional_bonds:
                    emotional_bonds[target] = {"trust": 50, "hostility": 0, "closeness": 0, "label": "陌生人"}
                bond = emotional_bonds[target]
                bond["trust"] = max(0, min(100, bond["trust"] + deltas.get("trust_delta", 0)))
                bond["hostility"] = max(0, min(100, bond["hostility"] + deltas.get("hostility_delta", 0)))
                bond["closeness"] = max(0, min(100, bond["closeness"] + deltas.get("closeness_delta", 0)))
                if "label" in deltas:
                    bond["label"] = deltas["label"]
                log.info(f"[关系更新] {target}: 信任={bond['trust']} 敌意={bond['hostility']} 亲密={bond['closeness']} 标签={bond['label']}")

        # 同步到世界引擎
        sync_data = {}
        if updates.get("values_update") and updates["values_update"] != "null":
            sync_data["values"] = {
                "current": dynamic_values["current"],
                "original": dynamic_values["original"],
                "shifts": dynamic_values["shifts"][-5:]
            }
        if new_core and new_core != "null":
            sync_data["new_core_memory"] = core_mem
        if bond_updates:
            sync_data["emotional_bonds"] = emotional_bonds

        if sync_data:
            try:
                requests.post(f"{WORLD_URL}/bot/{BOT_ID}/update_inner",
                              json=sync_data, timeout=10)
            except Exception as e:
                log.error(f"同步内心状态失败: {e}")

    except Exception as e:
        log.error(f"反思失败: {e}")


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    log.info(f"=== {persona['name']} 的灵魂 v8 已注入 ===")
    log.info(f"身份: {persona['age']}岁{persona['gender']}，来自{persona['origin']}，{persona['edu']}")
    log.info(f"性格: {persona['personality']}")
    log.info(f"价值观: {persona['values']}")
    log.info(f"背景: {persona['bg']}")
    log.info(f"习惯: {persona.get('habits', '')}")
    if persona.get("family_info"):
        log.info(f"家庭: {persona['family_info']}")
    log.info(f"v8.2能力: 寿命系统/记忆去重/关系ID规范/行为多样性/世界叙事")

    # 尝试从世界引擎恢复内心状态
    try:
        r = requests.get(f"{WORLD_URL}/bot/{BOT_ID}/detail", timeout=5)
        if r.status_code == 200:
            detail = r.json()
            if detail.get("values") and detail["values"].get("current"):
                dynamic_values["current"] = detail["values"]["current"]
                dynamic_values["original"] = detail["values"].get("original", persona["values"])
                dynamic_values["shifts"] = detail["values"].get("shifts", [])
                log.info(f"恢复价值观: {dynamic_values['current'][:50]}...")
            if detail.get("core_memories"):
                core_memories.extend(detail["core_memories"])
                log.info(f"恢复{len(detail['core_memories'])}条核心记忆")
            if detail.get("emotional_bonds"):
                emotional_bonds.update(detail["emotional_bonds"])
                log.info(f"恢复{len(detail['emotional_bonds'])}条情感关系")
    except:
        log.info("无法恢复内心状态，从头开始")

    # 等待世界引擎就绪
    for attempt in range(10):
        try:
            r = requests.get(f"{WORLD_URL}/world", timeout=5)
            if r.status_code == 200:
                log.info("世界引擎连接成功，开始生活！")
                break
        except:
            pass
        log.info(f"等待世界引擎... ({attempt+1}/10)")
        time.sleep(3)

    # 启动心跳
    heartbeat()
