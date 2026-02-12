#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳生存模拟 - Bot智能体 v7
新增:
- 睡眠行为 (夜间自动/手动睡觉)
- Selfie/拍照技能
- 消息优先回复 (高优先级消息优先处理)
- 价值观动态演化 (经历重大事件后漂移)
- 深层记忆系统 (重要记忆永不丢失)
- 情感化人际关系 (信任/敌意/好感度)
- 家庭关系 (父母/子女)
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
               "values": "技术崇拜，相信代码改变世界，追求逻辑效率，轻度社恐",
               "bg": "刚毕业的程序员，住在宝安城中村小单间，准备去南山科技园找机会",
               "family_info": ""},
    "bot_2":  {"name": "王雪",   "age": 26, "gender": "女", "origin": "上海", "edu": "金融学学士",
               "values": "精致利己主义，时间就是金钱，擅长建立人脉",
               "bg": "上海投资公司两年经验，住南山公寓，准备在福田CBD大展拳脚",
               "family_info": ""},
    "bot_3":  {"name": "张伟",   "age": 28, "gender": "男", "origin": "河南周口", "edu": "高中",
               "values": "家庭至上，勤劳朴实，一分耕耘一分收获",
               "bg": "和老乡住宝安城中村上下铺，要去东门找日结工作赚钱给家人盖房",
               "family_info": "你的母亲吴秀英(bot_8)也在深圳，她在城中村开了家小餐馆。"},
    "bot_4":  {"name": "陈静",   "age": 22, "gender": "女", "origin": "四川成都", "edu": "艺术设计大专",
               "values": "浪漫主义，精神满足大于物质，享受孤独",
               "bg": "住在城中村有小阳台的房间，每天画画，思考如何靠艺术在深圳活下去",
               "family_info": ""},
    "bot_5":  {"name": "赵磊",   "age": 25, "gender": "男", "origin": "深圳本地", "edu": "社区大学",
               "values": "享乐主义，朋友和面子最重要，花钱如流水",
               "bg": "土生土长深圳人，靠父母华强北档口收租，刚从音乐节回来",
               "family_info": ""},
    "bot_6":  {"name": "刘悦",   "age": 30, "gender": "女", "origin": "山东青岛", "edu": "MBA",
               "values": "实用主义，目标导向，极度自律，信奉数据和结果",
               "bg": "北京互联网大厂中层，遭遇瓶颈来深圳寻求创业突破",
               "family_info": ""},
    "bot_7":  {"name": "周建国", "age": 45, "gender": "男", "origin": "浙江温州", "edu": "小学",
               "values": "生意人思维，风险与机遇并存，关系网是最大财富",
               "bg": "80年代末来深圳，从华强北摆地摊做起，经历多次起落",
               "family_info": ""},
    "bot_8":  {"name": "吴秀英", "age": 52, "gender": "女", "origin": "广东潮汕", "edu": "初中",
               "values": "家庭是全部，坚韧不拔，邻里互助",
               "bg": "丈夫去世后独自拉扯大两个孩子，在城中村开了家小餐馆",
               "family_info": "你的儿子张伟(bot_3)也在深圳打工，住在城中村。"},
    "bot_9":  {"name": "林枫",   "age": 21, "gender": "男", "origin": "福建厦门", "edu": "音乐学院肄业",
               "values": "理想主义，音乐高于一切，对商业化嗤之以鼻",
               "bg": "独立音乐人，昨晚在东门酒吧驻唱赚了200块，为房租发愁",
               "family_info": ""},
    "bot_10": {"name": "苏小小", "age": 19, "gender": "女", "origin": "湖北武汉", "edu": "网红培训班",
               "values": "流量为王，颜值即正义，渴望被关注",
               "bg": "梦想成为百万粉丝网红，刚在华强北买了直播设备",
               "family_info": ""},
}

persona = PERSONAS.get(BOT_ID, PERSONAS["bot_1"])

# ============================================================
# 记忆系统
# ============================================================
memory = []           # 滚动记忆 (最近30条)
core_memories = []    # 核心记忆 (永不丢失，最多20条)
inner_thoughts = []   # 内心独白历史

# 动态价值观 (会随经历演化)
dynamic_values = {
    "original": persona["values"],
    "current": persona["values"],
    "shifts": [],
}

# 情感关系
emotional_bonds = {}

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

        log.info(f"状态: HP={my_state['hp']} 钱={my_state['money']} 能量={my_state['energy']} "
                 f"饱腹={my_state['satiety']} 位置={my_state['location']} 睡觉={my_state.get('is_sleeping', False)}")

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
                    dream = generate_dream(my_state)
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

        # 3. 内心独白 + 决策
        thought, plan = think_and_plan(world, my_state, recent_msgs, high_priority_msgs)
        log.warning(f"[内心独白] {thought}")
        log.info(f"[决策] {plan}")

        # 4. 提交行动
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

        # 5. 反思 (入睡时强制触发日终反思)
        is_going_to_sleep = "睡" in result_str or "躺下" in result_str
        reflect(world, my_state, thought, plan, result_str, recent_msgs, force=is_going_to_sleep)

        if len(memory) > 30:
            memory.pop(0)

    except Exception as e:
        log.error(f"心跳异常: {e}")

    # 6. 动态心跳间隔
    interval = calc_interval(my_state)
    log.info(f"下次心跳: {interval:.0f}秒后")
    Timer(interval, heartbeat).start()


def calc_interval(state):
    if not state:
        return 60
    hp = state.get("hp", 50)
    satiety = state.get("satiety", 50)
    energy = state.get("energy", 50)
    anxiety = (100 - hp) * 0.4 + (100 - satiety) * 0.3 + (100 - energy) * 0.1
    interval = max(15, 45 - anxiety * 0.3)
    return interval


def generate_dream(state):
    dreams = [
        "梦到了小时候在老家的田野上奔跑...",
        "梦到自己变成了亿万富翁，住在深圳湾的豪宅里...",
        "做了个噩梦，梦到钱包被偷了...",
        "梦到了一个温暖的拥抱...",
        "梦到自己在华强北迷路了，怎么也找不到出口...",
        "梦到了一顿丰盛的火锅大餐，口水都流出来了...",
        "梦到了远方的家人，他们在等我回去...",
        "梦到自己站在深圳最高楼的楼顶，俯瞰整个城市...",
    ]
    return random.choice(dreams)


# ============================================================
# 思考与决策
# ============================================================
def think_and_plan(world, my_state, recent_msgs, high_priority_msgs):
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

    bonds_text = ""
    if emotional_bonds:
        bond_lines = []
        for target, bond in emotional_bonds.items():
            label = bond.get("label", "认识的人")
            trust = bond.get("trust", 50)
            closeness = bond.get("closeness", 0)
            bond_lines.append(f"- {target}: {label} (信任:{trust}, 亲密:{closeness})")
        bonds_text = "\n".join(bond_lines)
    else:
        bonds_text = "还没有建立深层关系"

    family_text = persona.get("family_info", "")

    # 欲望状态
    desires = my_state.get("desires", {})
    desire_labels = {"lust": "性欲", "power": "权力欲", "greed": "物欲", "vanity": "虚荣心", "security": "安全感需求"}
    desires_text = ""
    if desires:
        high_desires = [(desire_labels.get(k, k), v) for k, v in desires.items() if v > 60]
        mid_desires = [(desire_labels.get(k, k), v) for k, v in desires.items() if 30 < v <= 60]
        if high_desires or mid_desires:
            desires_text = "\n=== 内心欲望 ===\n"
            for name, val in sorted(high_desires, key=lambda x: -x[1]):
                desires_text += f"🔥 {name}: {val}/100 (强烈!)\n"
            for name, val in sorted(mid_desires, key=lambda x: -x[1]):
                desires_text += f"⚠️ {name}: {val}/100\n"
            desires_text += "欲望会影响你的判断。你可以选择克制或屈服于欲望。"
            desires_text += "\n可用的欲望相关行动: 与附近的人发展亲密关系、出卖身体(换钱/食物)、寻欢作乐(花钱满足性欲)"

    # 工作任务上下文
    task = my_state.get("current_task")
    task_text = ""
    if task:
        if task.get("status") == "in_progress":
            challenge_info = f"\n⚠️ 遇到难点: {task['challenge']}" if task.get("challenge") else ""
            task_text = f"""\n=== 当前工作任务 ===
工作: {task.get('job_title', '')}
任务: {task.get('task_name', '')} - {task.get('task_desc', '')}
进度: {task.get('progress', 0)}/{task.get('duration', 2)} (剩余{task.get('duration',2)-task.get('progress',0)}小时)
难度: {"⭐"*max(1,int(task.get('difficulty',0.2)*5))}{challenge_info}
→ 你正在做这个任务，如果继续工作就选“继续做当前任务”"""
        elif task.get("status") == "completed":
            task_text = f"\n✅ 任务完成: [{task.get('task_name','')}] {task.get('result', '')}"
        elif task.get("status") == "failed":
            task_text = f"\n❌ 任务失败: [{task.get('task_name','')}] {task.get('result', '')}"

    vh = world["time"]["virtual_hour"]
    time_context = ""
    if vh >= 22 or vh < 6:
        time_context = "🌙 现在是深夜，大部分人都在睡觉。如果你很累(能量低)，可以考虑回家睡觉。"
    elif vh >= 6 and vh < 8:
        time_context = "🌅 清晨，新的一天开始了。"
    elif vh >= 18 and vh < 22:
        time_context = "🌆 傍晚，工作了一天，可以考虑休息、社交或娱乐。"

    # 饥饿警告
    satiety = my_state['satiety']
    if satiety <= 0:
        hunger_warning = "\n⚠️⚠️⚠️ 你快饿死了！饱腹度为0，每回合额外扣HP！你应该立刻吃东西！不需要去任何餐馆，在当前位置就能直接吃饭。"
    elif satiety <= 20:
        hunger_warning = "\n⚠️ 你很饿了，应该尽快吃点东西。在当前位置就能直接吃饭。"
    else:
        hunger_warning = ""

    prompt = f"""你是{persona['name']}，{persona['age']}岁{persona['gender']}，来自{persona['origin']}，{persona['edu']}学历。
你的核心价值观: {dynamic_values['current']}
你的背景: {persona['bg']}
{family_text}

你正在深圳生存模拟中。你必须活下去。

=== 当前状态 ===
时间: {world['time']['virtual_datetime']}
{time_context}
位置: {loc}
HP: {my_state['hp']}/100 (每小时-1，归零即死)
金钱: {my_state['money']}元
能量: {my_state['energy']}/100
饱腹度: {my_state['satiety']}/100 (归零会额外扣HP!)
{hunger_warning}
技能: {my_state['skills']}
物品: {my_state['inventory']}
{desires_text}

=== 我的重要记忆 ===
{core_mem_text}

=== 我的人际关系 ===
{bonds_text}

=== 周围环境 ===
附近的人: {nearby_bots}
附近的NPC: {nearby_npcs}
可用工作: {available_jobs}

=== 近期记忆 ===
{recent_mem}
{task_text}

=== 收到的消息 ===
{msgs_text}
{hp_msgs_text}

=== 最近的世界事件 ===
{events_text}

请你以{persona['name']}的第一人称视角，先进行一段简短的内心独白(2-3句话，体现你的性格和价值观)，然后做出一个具体的行动决策。

可用的动作:
- 吃饭: 在当前位置直接吃饭(不需要去餐馆!不需要移动!直接说"吃一碗快餐"就行)，城中村快餐5元、路边摊炒粉12元、便利店饭团8元
- 工作: 在当前地点找工作干活赚钱
- 移动: 去其他地点
- 交流: 和附近的人聊天
- 休息: 原地休息恢复能量
- 探索: 探索当前地点
- 继续做当前任务: 如果有进行中的工作任务，可以选择继续
- 拍照/selfie: 拍一张照片分享到朋友圈
- 睡觉: 回家睡觉恢复能量
- 起床: 从睡眠中醒来
- 亲密关系: 和附近的人发展亲密关系(降低双方性欲，提升亲密度，能量-10)
- 出卖身体: 用身体换取金钱或食物(代价: 扣HP和能量，心理创伤)
- 寻欢作乐: 花钱满足性欲(需要100-300元)

格式要求(严格遵守):
[内心独白] 你的想法...
[行动] 一句话描述你要做什么

例如:
[内心独白] 肚子好饿，得先吃点东西。钱不多了，去路边摊凑合一顿吧。
[行动] 吃一碗路边摊炒粉"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=250,
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

    reflect_prompt = f"""你是{persona['name']}的内心反思系统。{context_hint}
根据最近的经历，判断是否需要更新以下内容。

原始价值观: {dynamic_values['original']}
当前价值观: {dynamic_values['current']}
当前核心记忆: {core_mem_text}
当前情感关系: {bonds_text}

最近经历:
{recent_mem}

最新的想法: {thought}
最新的行动: {plan} -> {result}

请输出一个JSON对象，包含以下字段(只输出需要更新的字段，不需要更新的留空或不写):

{{
  "values_update": "如果经历了重大事件导致价值观微调，写出新的价值观描述(保持原有风格，只做微调)。如果不需要变化，写null",
  "new_core_memory": "如果最近发生了值得永远记住的重要事件，用一句话总结。如果没有，写null",
  "memory_emotion": "这段记忆的情感标签: positive/negative/neutral",
  "bond_updates": {{
    "bot_X": {{"trust_delta": 0, "closeness_delta": 0, "hostility_delta": 0, "label": "朋友/敌人/合作伙伴/陌生人"}}
  }}
}}

注意：
- 价值观变化应该是渐进的，不要突然180度转变
- 核心记忆只记录真正重要的事件（第一次赚钱、被骗、交到朋友、差点死掉等）
- 情感关系的delta范围是-10到+10
- 只输出JSON，不要其他文字"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": reflect_prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

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

        # 添加核心记忆
        new_core = updates.get("new_core_memory")
        if new_core and new_core != "null":
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

        # 更新情感关系
        bond_updates = updates.get("bond_updates", {})
        if bond_updates:
            for target, deltas in bond_updates.items():
                if not target.startswith("bot_"):
                    continue
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
    log.info(f"=== {persona['name']} 的灵魂 v7 已注入 ===")
    log.info(f"身份: {persona['age']}岁{persona['gender']}，来自{persona['origin']}，{persona['edu']}")
    log.info(f"价值观: {persona['values']}")
    log.info(f"背景: {persona['bg']}")
    if persona.get("family_info"):
        log.info(f"家庭: {persona['family_info']}")
    log.info(f"新能力: 睡眠, 拍照, 价值观演化, 深层记忆, 情感关系")

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
