"""
劳动力市场 - 四条基础规则
1. 稀缺性: 竞争压低工资（涌现：35岁危机、内卷）
2. 信息不对称: 机会通过社交网络传播（涌现：老乡帮带）
3. 适应性预期: 根据近期结果更新期望（涌现：躺平 / 重新奋斗）
4. 收益递增: 财富和连接带来更多机会（涌现：贫富分化）
"""
import random
from core.world_state import world, log
from core.constants import JOBS


def update_job_market():
    """
    统计每个地点、每个工种的竞争人数。
    market structure: {location: {skill_key: {"pressure": float, "workers": [bid,...]}}}
    pressure 每 tick 以 0.7 衰减（市场惯性），然后加上本 tick 的在场竞争者数。
    """
    market = world.setdefault("job_market", {})

    # 衰减
    for loc_key in market:
        for skill_key in market[loc_key]:
            market[loc_key][skill_key]["pressure"] = (
                market[loc_key][skill_key].get("pressure", 0) * 0.7
            )
            market[loc_key][skill_key]["workers"] = []

    # 统计本 tick 竞争者
    for bid, bot in world["bots"].items():
        if bot["status"] != "alive" or bot.get("is_sleeping"):
            continue
        task = bot.get("current_task")
        if task and task.get("status") == "in_progress":
            loc = bot["location"]
            skill = task.get("skill", "none")
            if loc not in market:
                market[loc] = {}
            if skill not in market[loc]:
                market[loc][skill] = {"pressure": 0.0, "workers": []}
            market[loc][skill]["pressure"] += 1
            market[loc][skill]["workers"].append(bid)


def compute_wage(job, location, bot):
    """
    竞争函数：工资由供需决定。
      wage = base_pay × competition_discount × skill_premium
    - 竞争越激烈 → 工资越低（自然产生35岁危机：老打工人高期望被竞争淘汰）
    - 技能越高 → 溢价越大
    Returns integer wage, minimum 5.
    """
    base_pay = job.get("pay", 30)
    skill_key = job.get("skill", "none")

    # 竞争折扣
    market = world.get("job_market", {})
    pressure = market.get(location, {}).get(skill_key, {}).get("pressure", 0)
    competition_discount = 1.0 / (1.0 + pressure * 0.08)

    # 技能溢价 (skill 100 → +67%)
    skill_val = bot["skills"].get(skill_key, 0) if skill_key != "none" else 10
    skill_premium = 1.0 + skill_val / 150.0

    return max(5, round(base_pay * competition_discount * skill_premium))


def check_reservation_wage(bot, offered_wage):
    """
    是否接受这个工资？
    reservation_wage = aspiration_level × 0.6（心理底线）
    - 新来深圳的人 aspiration 低 → 接受低薪
    - 经验丰富的人 aspiration 高 → 嫌低不做
    - 反复失败后 aspiration 被压低 → 被迫接受低薪（自然躺平前兆）
    Returns (accept: bool, reservation_wage: float)
    """
    aspiration = bot.get("aspiration_level", 30.0)
    reservation = aspiration * 0.6
    return offered_wage >= reservation, reservation


def update_adaptive_expectations(bot, outcome_type, amount=0):
    """
    根据近期结果更新 bot 的期望（aspiration_level）和风险偏好（risk_tolerance）。
    outcome_type: "success" | "failure" | "rejection"
    涌现效果：
    - 连续成功 → aspiration 上升 → 变得挑剔
    - 连续失败/被拒 → aspiration 下降 → 接受更差条件（自然躺平）
    - risk_tolerance 低于 0.2 → _low_motivation_ticks 累计（可视化展示用）
    """
    outcomes = bot.setdefault("recent_outcomes", [])
    outcomes.append({"type": outcome_type, "amount": amount})
    if len(outcomes) > 8:
        outcomes.pop(0)

    # 更新 aspiration（指数移动平均）
    asp = bot.get("aspiration_level", 30.0)
    if outcome_type == "success" and amount > 0:
        bot["aspiration_level"] = asp * 0.8 + amount * 0.2
    elif outcome_type in ("failure", "rejection"):
        bot["aspiration_level"] = max(8.0, asp * 0.95)

    # 更新 risk_tolerance
    recent = outcomes[-5:]
    successes = sum(1 for o in recent if o["type"] == "success")
    rejections = sum(1 for o in recent if o["type"] == "rejection")
    rt = bot.get("risk_tolerance", 0.5)
    if successes >= 3:
        bot["risk_tolerance"] = min(1.0, rt + 0.05)
    elif rejections >= 3:
        bot["risk_tolerance"] = max(0.1, rt - 0.08)

    # 低动力累计（供展示，不做硬判断）
    if bot.get("risk_tolerance", 0.5) < 0.2:
        bot["_low_motivation_ticks"] = bot.get("_low_motivation_ticks", 0) + 1
    else:
        bot["_low_motivation_ticks"] = 0


def spread_job_info():
    """
    信息不对称：机会通过社交网络传播。
    1. 亲身在场 → 精确信息（confidence=1.0）
    2. 通过 emotional_bonds 听说 → 有噪声（confidence = closeness/100）
    3. 超过 20 tick 的信息置信度衰减，最终被遗忘
    涌现：老乡网络（同 origin 的 bot closeness 更高 → 信息传播更快更准）
    """
    tick_now = world["time"]["tick"]
    for bid, bot in world["bots"].items():
        if bot["status"] != "alive":
            continue
        known = bot.setdefault("known_opportunities", {})
        loc = bot["location"]

        # 1. 亲身在场 → 精确信息
        if loc in JOBS:
            for job in JOBS[loc]:
                wage = compute_wage(job, loc, bot)
                known[f"{loc}:{job['title']}"] = {
                    "location": loc,
                    "title": job["title"],
                    "wage_estimate": wage,
                    "skill": job.get("skill", "none"),
                    "confidence": 1.0,
                    "source": "direct",
                    "discovered_tick": tick_now,
                }

        # 2. 社交网络 → 有噪声的信息
        bonds = bot.get("emotional_bonds", {})
        for other_id, bond in bonds.items():
            if other_id not in world["bots"]:
                continue
            other = world["bots"][other_id]
            if other["status"] != "alive":
                continue
            closeness = bond.get("closeness", 0)
            if closeness < 15:
                continue
            if random.random() > closeness / 100:
                continue
            other_loc = other["location"]
            if other_loc in JOBS and random.random() < 0.3:
                for job in JOBS[other_loc]:
                    key = f"{other_loc}:{job['title']}"
                    if key not in known:
                        noise = (1 - closeness / 100) * 0.4
                        est = compute_wage(job, other_loc, bot)
                        noisy = int(est * (1 + random.uniform(-noise, noise)))
                        known[key] = {
                            "location": other_loc,
                            "title": job["title"],
                            "wage_estimate": noisy,
                            "skill": job.get("skill", "none"),
                            "confidence": round(closeness / 100, 2),
                            "source": other["name"],
                            "discovered_tick": tick_now,
                        }

        # 3. 信息衰减 / 遗忘
        stale = []
        for key, info in known.items():
            age = tick_now - info.get("discovered_tick", 0)
            if age > 20:
                info["confidence"] = round(max(0.05, info["confidence"] * 0.9), 3)
            if info["confidence"] < 0.05:
                stale.append(key)
        for key in stale:
            del known[key]


def compute_passive_income():
    """
    收益递增：财富产生财富。
    > 10000元：稳定被动收入（0.1%/tick）
    > 5000元：偶尔有小额收益
    涌现：贫富分化（初始差距 × 复利）
    """
    for bid, bot in world["bots"].items():
        if bot["status"] != "alive":
            continue
        money = bot.get("money", 0)
        if money > 10000:
            income = max(1, round(money * 0.001))
            bot["money"] += income
            if random.random() < 0.05:
                log.info(f"[市场] {bot['name']} 被动收入 +{income}元 (资产{money})")
        elif money > 5000:
            if random.random() < 0.1:
                income = random.randint(10, 50)
                bot["money"] += income
