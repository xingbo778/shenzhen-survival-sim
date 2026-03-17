import random, logging
from threading import Thread
from core.world_state import world, lock, log
from core.constants import (AGING_BASE, AGING_HUNGER_MULT, AGING_OVERWORK_MULT, AGING_SICK_MULT,
                              SATIETY_DECAY, ENERGY_DAY_COST, ENERGY_NIGHT_RECOVER, ENERGY_SLEEP_RECOVER,
                              EMOTION_DECAY, WEATHER_TYPES, DESIRE_GROWTH_PER_TICK,
                              BOT_DESIRE_PROFILES, DEFAULT_DESIRE_PROFILE, FOOD_MENU, DAILY_RENT, DAILY_MISC_COST)
from systems.weather import update_weather
from systems.news import inject_news
from systems.events import trigger_event, trigger_personal_fate
from systems.generation import spread_urban_legends, handle_bot_death
from systems.labor_market import (update_job_market, spread_job_info,
                                   compute_passive_income, update_adaptive_expectations)
from utils.ai_client import client
from rules.rules_engine import tick_rules


def _generate_world_narrative(t):
    """每天22:00生成世界叙事摘要"""
    try:
        day = t["virtual_day"]
        events_today = [e for e in world["events"] if f"第{day}天" in e.get("time", "")]
        events_text = "; ".join([e["event"] for e in events_today[-5:]]) if events_today else "平静的一天"

        bot_summaries = []
        for bid, bot in world["bots"].items():
            if bot["status"] != "alive":
                continue
            recent = bot.get("action_log", [])[-3:]
            actions = "; ".join([a.get("plan", "")[:30] for a in recent]) if recent else "无"
            bot_summaries.append(f"{bot['name']}(HP:{bot['hp']:.1f},¥{bot['money']}): {actions}")

        prompt = f"""你是深圳这座城市的观察者。今天是模拟世界的第{day}天。
天气: {world['weather']['current']}
今天发生的事件: {events_text}
居民动态:
{chr(10).join(bot_summaries[:6])}

请用2-3句话写一段"城市日记"，像一个旁观者记录这座城市今天的故事。
要求：有文学感，关注人物命运，不要列举。只输出日记内容。"""

        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8, max_tokens=150,
        )
        narrative = resp.choices[0].message.content.strip()
        world["world_narrative"] = narrative
        log.info(f"📖 世界叙事: {narrative}")
    except Exception as e:
        log.error(f"世界叙事生成失败: {e}")


def world_tick():
    with lock:
        t = world["time"]
        t["tick"] += 1
        t["virtual_hour"] = (6 + t["tick"]) % 24
        t["virtual_day"] = 1 + t["tick"] // 24
        vd = t['virtual_day']; vh = t['virtual_hour']
        t['virtual_datetime'] = f'第{vd}天 {vh:02d}:00'

        log.info(f'===== TICK {t["tick"]} | {t["virtual_datetime"]} | 天气:{world["weather"]["current"]} =====')

        # 每日6:00更新天气和新闻
        if vh == 6 and t["tick"] > 1:
            update_weather()
            inject_news()
        # 每6个tick也刷新一次新闻和热搜，保持内容新鲜
        elif t["tick"] % 6 == 0:
            inject_news()

        # 天气效果
        weather_info = WEATHER_TYPES.get(world["weather"]["current"], {})
        weather_mood = weather_info.get("mood_effect", {})

        alive_count = 0
        for bid, bot in world["bots"].items():
            if bot["status"] != "alive":
                continue
            alive_count += 1

            h = t["virtual_hour"]
            emotions = bot.get("emotions", {})

            # === 睡眠系统 ===
            if bot.get("is_sleeping", False):
                bot["energy"] = min(100, bot["energy"] + ENERGY_SLEEP_RECOVER)
                bot["satiety"] = max(0, bot["satiety"] - 1)
                # 睡觉时情绪恢复
                emotions["anxiety"] = max(0, emotions.get("anxiety", 20) - 3)
                emotions["anger"] = max(0, emotions.get("anger", 5) - 2)
                emotions["loneliness"] = max(0, emotions.get("loneliness", 30) - 1)
                bot["emotions"] = emotions
                # 手机充电
                bot["phone_battery"] = min(100, bot.get("phone_battery", 50) + 15)
                # 自动起床
                if 7 <= h < 23 and bot["energy"] >= 80:
                    bot["is_sleeping"] = False
                    log.info(f"{bid} 自然醒了 (能量={bot['energy']})")
                continue

            # === 正常状态: 寿命衰老 ===
            aging_rate = AGING_BASE
            # 饥饿加速衰老
            if bot["satiety"] <= 10:
                aging_rate *= AGING_HUNGER_MULT
                if not bot.get("_hunger_warned"):
                    log.warning(f"⚠️ {bid} 饥饿加速衰老! (x{AGING_HUNGER_MULT})")
                    bot["_hunger_warned"] = True
            else:
                bot["_hunger_warned"] = False
            # 过劳加速衰老 (能量<10且没睡觉)
            if bot["energy"] < 10 and not bot.get("is_sleeping", False):
                aging_rate *= AGING_OVERWORK_MULT
                if not bot.get("_overwork_warned"):
                    log.warning(f"⚠️ {bid} 过劳加速衰老! (x{AGING_OVERWORK_MULT})")
                    bot["_overwork_warned"] = True
            else:
                bot["_overwork_warned"] = False
            bot["hp"] = max(0, round(bot["hp"] - aging_rate, 3))
            bot["aging_rate"] = round(aging_rate, 4)
            bot["satiety"] = max(0, bot["satiety"] - SATIETY_DECAY)

            # 能量
            if h >= 22 or h < 6:
                bot["energy"] = min(100, bot["energy"] + ENERGY_NIGHT_RECOVER)
            else:
                bot["energy"] = max(0, bot["energy"] - ENERGY_DAY_COST)

            # 手机电量：自动慢充，作为背景变量不影响决策
            if bot.get("phone_battery", 100) < 80:
                bot["phone_battery"] = min(100, bot.get("phone_battery", 100) + random.randint(3, 8))
            else:
                bot["phone_battery"] = max(30, bot.get("phone_battery", 100) - random.randint(0, 2))

            # 饥饿惩罚（寿命加速衰老已在上面处理，这里只加情绪影响）
            if bot["satiety"] <= 0:
                emotions["sadness"] = min(100, emotions.get("sadness", 10) + 3)
                emotions["anxiety"] = min(100, emotions.get("anxiety", 20) + 2)
                log.warning(f"{bid} 饥饿中，加速衰老中!")

            # === 情绪自然衰减/增长 ===
            for emo_key, decay in EMOTION_DECAY.items():
                old = emotions.get(emo_key, 0)
                emotions[emo_key] = max(0, min(100, old + decay))

            # 天气影响情绪
            for emo_key, delta in weather_mood.items():
                emotions[emo_key] = max(0, min(100, emotions.get(emo_key, 0) + delta))

            # v8.3: 孤独感重新平衡 - 降低增长速度，提高社交减少量
            loc = bot["location"]
            nearby = [b for b in world["locations"].get(loc, {}).get("bots", []) if b != bid]
            if not nearby:
                emotions["loneliness"] = min(100, emotions.get("loneliness", 30) + 0.5)
            else:
                emotions["loneliness"] = max(0, emotions.get("loneliness", 30) - 5)

            # 金钱焦虑
            if bot["money"] < 50:
                emotions["anxiety"] = min(100, emotions.get("anxiety", 20) + 3)
                emotions["sadness"] = min(100, emotions.get("sadness", 10) + 2)
            elif bot["money"] < 100:
                emotions["anxiety"] = min(100, emotions.get("anxiety", 20) + 1)

            # 能量低时疲惫感
            if bot["energy"] < 20:
                emotions["sadness"] = min(100, emotions.get("sadness", 10) + 2)
                emotions["happiness"] = max(0, emotions.get("happiness", 50) - 3)

            # 无聊/无事可做时happiness自然下降
            # （已经通过EMOTION_DECAY实现）

            bot["emotions"] = emotions

            # === 欲望自然增长 ===
            desires = bot.get("desires", {})
            profile = BOT_DESIRE_PROFILES.get(bid, DEFAULT_DESIRE_PROFILE)
            for d_key, base_growth in DESIRE_GROWTH_PER_TICK.items():
                mult = profile.get(f"{d_key}_mult", 1.0)
                if d_key == "security" and (bot["hp"] < 30 or bot["money"] < 50):
                    mult *= 1.5
                if d_key == "greed" and bot["money"] < 100:
                    mult *= 1.3
                if d_key == "lust" and bot["energy"] > 60 and bot["satiety"] > 30:
                    mult *= 1.2
                if d_key == "lust":
                    if vh >= 22 or vh <= 5:
                        mult *= 1.5
                    gender = bot.get("gender", "")
                    for ob in nearby:
                        other = world["bots"].get(ob, {})
                        if other.get("gender") and other.get("gender") != gender and other.get("status") == "alive":
                            mult *= 1.3
                            break
                old_val = desires.get(d_key, 20)
                # 欲望超90自动衰减，80-90增长变慢
                if old_val >= 90:
                    desires[d_key] = max(0, old_val - random.uniform(0.5, 1.5))
                elif old_val >= 80:
                    desires[d_key] = min(100, old_val + base_growth * mult * 0.3)
                else:
                    desires[d_key] = min(100, old_val + base_growth * mult)
            bot["desires"] = desires

            # 死亡检测
            if bot["hp"] <= 0:
                bot["status"] = "dead"
                log.error(f"!!! {bid} 已死亡 !!! HP归零")
                if bid in world["locations"].get(loc, {}).get("bots", []):
                    world["locations"][loc]["bots"].remove(bid)
                # v9.0: 触发代际传承机制
                Thread(target=handle_bot_death, args=(bid,), daemon=True).start()

            # === 工作进度推进 ===
            task = bot.get("current_task")
            if task and task.get("status") == "in_progress":
                task["progress"] = task.get("progress", 0) + 1
                # 随机难点
                if not task.get("challenge") and random.random() < task.get("difficulty", 0.2) * 0.5:
                    challenges = ["客户突然改需求", "工具出故障了", "同事请假要帮忙", "材料不够用",
                                  "被老板催进度", "遇到技术难题", "天气影响了工作"]
                    task["challenge"] = random.choice(challenges)
                    log.info(f"{bid} 工作遇到难点: {task['challenge']}")
                # 完成判断
                if task["progress"] >= task["duration"]:
                    skill_key = task.get("skill", "none")
                    skill_val = bot["skills"].get(skill_key, 0) if skill_key != "none" else 10
                    success_rate = min(0.95, 0.5 + skill_val / 200)
                    had_challenge = task.get("challenge") is not None
                    if had_challenge:
                        success_rate -= 0.15
                    base_pay = task.get("base_pay", 30)
                    if random.random() < success_rate:
                        bonus = random.randint(10, 30) if had_challenge else 0
                        pay = base_pay + bonus
                        bot["money"] += pay
                        if skill_key != "none" and skill_key in bot["skills"]:
                            bot["skills"][skill_key] = min(100, bot["skills"][skill_key] + random.randint(2, 4))
                        task["status"] = "completed"
                        task["result"] = f"成功完成! 赚了{pay}元" + (f"(含难点奖励{bonus}元)" if bonus else "")
                        update_adaptive_expectations(bot, "success", pay)
                        # v8.3: 完成任务给予显著happiness奖励
                        emotions["happiness"] = min(100, emotions.get("happiness", 50) + 12)
                        emotions["anxiety"] = max(0, emotions.get("anxiety", 20) - 5)
                        emotions["sadness"] = max(0, emotions.get("sadness", 10) - 3)
                        log.info(f"{bid} 完成任务[{task['task_name']}]: 赚{pay}元")
                    else:
                        pay = max(10, base_pay // 3)
                        bot["money"] += pay
                        if skill_key != "none" and skill_key in bot["skills"]:
                            bot["skills"][skill_key] = min(100, bot["skills"][skill_key] + 1)
                        task["status"] = "failed"
                        task["result"] = f"任务失败了...只拿到{pay}元辛苦费"
                        update_adaptive_expectations(bot, "failure", pay)
                        emotions["sadness"] = min(100, emotions.get("sadness", 10) + 5)
                        emotions["anxiety"] = min(100, emotions.get("anxiety", 20) + 3)
                        log.warning(f"{bid} 任务失败[{task['task_name']}]: 只拿到{pay}元")
                else:
                    remaining = task["duration"] - task["progress"]
                    log.info(f"{bid} 工作中[{task['task_name']}]: 进度 {task['progress']}/{task['duration']}")

            # 自动入睡
            if (h >= 23 or h < 7) and bot["energy"] < 30 and bot["location"] == bot["home"]:
                bot["is_sleeping"] = True
                log.info(f"{bid} 太累了，在{bot['home']}睡着了")

        # 每日8:00扣除固定开销（房租+杂费）
        if vh == 8 and t["tick"] > 1:
            for bid2, bot2 in world["bots"].items():
                if bot2["status"] != "alive":
                    continue
                home = bot2.get("home", "宝安城中村")
                rent = DAILY_RENT.get(home, 15)
                total_cost = rent + DAILY_MISC_COST
                if bot2["money"] >= total_cost:
                    bot2["money"] -= total_cost
                    log.info(f"{bid2} 扣除固定开销: 房租{rent}+杂费{DAILY_MISC_COST}={total_cost}元")
                else:
                    # 钱不够交租，被驱逐到东门老街
                    bot2["money"] = 0
                    if bot2["location"] == home:
                        old_loc = bot2["location"]
                        if bid2 in world["locations"][old_loc]["bots"]:
                            world["locations"][old_loc]["bots"].remove(bid2)
                        bot2["location"] = "东门老街"
                        bot2["home"] = "东门老街"  # 无家可归
                        world["locations"]["东门老街"]["bots"].append(bid2)
                    log.warning(f"{bid2} 交不起房租，被驱逐到东门老街!")

            # v9.0: 年龄增长 (每虚拟1天 = 1岁)
            for bid_age, bot_age in world["bots"].items():
                if bot_age["status"] != "alive":
                    continue
                bot_age["age"] = bot_age.get("age", 25) + 1
                # 老年人衰老加速
                if bot_age["age"] >= 70:
                    bot_age["hp"] = max(0, bot_age["hp"] - 2.0)  # 老年额外扣HP
                    log.info(f"{bid_age} {bot_age['name']} 已{bot_age['age']}岁，衰老加速")
                elif bot_age["age"] >= 55:
                    bot_age["hp"] = max(0, bot_age["hp"] - 0.5)  # 中年额外扣HP
                if t["tick"] % 24 == 0:  # 每24tick(虚拟1天)记录一次
                    log.info(f"🎂 {bot_age['name']} 现在{bot_age['age']}岁 (HP:{bot_age['hp']:.1f})")

        # v8.3.2: 动态经济 - 每日6:00食物价格自然回落
        if vh == 6:
            dp = world.get("food_prices", {})
            for fname, base_food in FOOD_MENU.items():
                if fname in dp and dp[fname] > base_food["cost"]:
                    dp[fname] = max(base_food["cost"], dp[fname] - max(1, base_food["cost"] // 10))
            world["food_prices"] = dp

        # 随机事件（提高概率，让环境更活跃）
        event_chance = 0.20 + WEATHER_TYPES.get(world["weather"]["current"], {}).get("event_chance_mod", 0)
        if random.random() < event_chance:
            trigger_event()
        # 第二次事件机会（低概率，让世界更丰富）
        if random.random() < 0.08:
            trigger_event()

        # v8.4: 个人命运事件（每 tick 15% 概率对随机一个 bot 触发）
        if random.random() < 0.15:
            trigger_personal_fate()

        # === 被动朋友圈互动：每tick每个bot有概率刷朋友圈点赞 ===
        recent_moments = world.get("moments", [])[-10:]
        if recent_moments:
            for bid, bot in world["bots"].items():
                if bot["status"] != "alive" or bot.get("is_sleeping"):
                    continue
                if random.random() < 0.15:  # 15%概率刷朋友圈
                    for m in recent_moments:
                        if m["bot_id"] != bid and bid not in m.get("likes", []):
                            if random.random() < 0.4:  # 40%概率点赞
                                m["likes"].append(bid)

        # === v9.0: 每天传播城市传说 ===
        if vh == 20:
            spread_urban_legends()

        # === v9.0: 声望自然衰减 (每天向0回归一点) ===
        if vh == 6:
            for bid_r, bot_r in world["bots"].items():
                if bot_r["status"] != "alive":
                    continue
                rep = bot_r.get("reputation", {"score": 0})
                score = rep.get("score", 0)
                if score > 0:
                    rep["score"] = max(0, score - 1)
                elif score < 0:
                    rep["score"] = min(0, score + 1)

        # === 世界叙事摘要 (每天22:00生成) ===
        if vh == 22:
            _generate_world_narrative(t)

        # === NPC演化 ===
        for loc_name, loc_data in world["locations"].items():
            for npc in loc_data.get("npcs", []):
                interactions = npc.get("interaction_count", 0)
                if interactions >= 10:
                    npc["attitude"] = "跟这里的人都混熟了"
                elif interactions >= 5:
                    npc["attitude"] = "开始认识常客"

        # === v10.1: 执行世界规则引擎 ===
        try:
            rule_narratives = tick_rules(world)
            if rule_narratives:
                for rn in rule_narratives[:5]:
                    log.info(f"[RULES] {rn}")
        except Exception as e:
            log.error(f"[RULES] tick_rules失败: {e}")

        # === v11: 劳动力市场四条基础规则 ===
        update_job_market()
        spread_job_info()
        compute_passive_income()

        # 清理过期效果
        world["active_effects"] = [e for e in world["active_effects"] if e["expires_tick"] > t["tick"]]

        active_rule_count = sum(1 for r in world.get('active_rules', []) if r.get('active', True))
        log.info(f'存活Bot数: {alive_count}/{len(world["bots"])} | 活跃规则: {active_rule_count}')
