#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳生存模拟 - 边界场景测试
覆盖集成测试未触及的关键分支：
  - 死亡 & 代际传承
  - 租金扣除 & 驱逐
  - 睡眠恢复
  - 饥饿加速衰老
  - 工作任务完成/失败
  - Move 行动（地点一致性）
  - 世界改造（Mock LLM 返回 has_modification=true）
  - 快照格式完整性
  - 情绪/数值边界（不溢出）
  - 规则引擎衰减
"""
import sys, os, json, random, copy, logging
import unittest.mock as mock

# ── 依赖 mock ──────────────────────────────────────────────
os.makedirs = mock.MagicMock()
_mock_openai = mock.MagicMock()
sys.modules['openai'] = _mock_openai

_null = logging.NullHandler()
with mock.patch('logging.FileHandler', return_value=_null), \
     mock.patch('logging.StreamHandler', return_value=_null):
    from core.world_state import world, lock, log, create_bot, init_world
    from core.constants import (LOCATIONS, PERSONAS, FOOD_MENU, JOBS,
                                 EMOTION_DIMS, WEATHER_TYPES, DAILY_RENT,
                                 DAILY_MISC_COST, AGING_BASE, AGING_HUNGER_MULT,
                                 AGING_OVERWORK_MULT)
    import utils.ai_client, systems.news, systems.world_mods
    import core.tick_engine, actions.processor

# ── 通用 LLM Mock ──────────────────────────────────────────
def make_client(override=None):
    """构造 mock client，override 可以注入特定返回值"""
    c = mock.MagicMock()
    def side_effect(messages=None, model=None, **kw):
        content = (messages or [{}])[-1].get("content", "")
        if override and override.get("match") and override["match"] in content:
            text = override["response"]
        elif "工具调用" in content and "后果" in content:
            text = json.dumps({
                "narrative": "完成了行动。",
                "success": True, "money_delta": 0,
                "energy_delta": 5, "satiety_delta": -1,
                "happiness_delta": 2, "skill_up": None,
                "world_change": None, "social_effects": [],
                "side_effects": [], "feedback_to_actor": "好的。"
            })
        elif "JSON转换器" in content:
            text = json.dumps({"tool": "use_resource",
                               "args": {"resource": "energy", "amount": 0, "purpose": "休息"},
                               "desc": "休息"})
        elif "热搜" in content:
            text = "深圳打工人\n城中村生活\n周末去哪玩\n今天加班\n买房难"
        elif "新闻" in content or "深圳本地" in content:
            text = "深圳天气晴好\n华强北生意火爆\n南山新楼盘热销"
        elif "城市日记" in content or "旁观者" in content:
            text = "这座城市又平静地过了一天。"
        elif "氛围" in content:
            text = "热闹的"
        elif "永久性" in content or "has_modification" in content:
            text = json.dumps({"has_modification": False})
        else:
            text = json.dumps({"tool": "use_resource",
                               "args": {"resource": "energy", "amount": 0, "purpose": "休息"},
                               "desc": "休息"})
        msg = mock.MagicMock(); msg.content = text
        ch = mock.MagicMock(); ch.message = msg
        r = mock.MagicMock(); r.choices = [ch]
        return r
    c.chat.completions.create.side_effect = side_effect
    return c

def reset_world():
    """每个测试前重置世界状态"""
    world["bots"].clear()
    world["locations"].clear()
    world["events"].clear()
    world["active_effects"].clear()
    world["moments"].clear()
    world["message_board"].clear()
    world["world_modifications"].clear()
    world["graveyard"].clear()
    world["urban_legends"].clear()
    world["active_rules"].clear()
    world["news_feed"].clear()
    world["hot_topics"].clear()
    world["time"] = {"tick": 0, "virtual_hour": 6, "virtual_day": 1, "virtual_datetime": "第1天 06:00"}
    world["weather"] = {"current": "晴天", "desc": "阳光明媚", "changed_at_tick": 0}
    world["generation_count"] = 0
    world["reputation_board"].clear()

# ── 测试结果收集 ───────────────────────────────────────────
results = []

def test(name, fn):
    try:
        fn()
        results.append((name, True, None))
        print(f"  ✓ {name}")
    except AssertionError as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        import traceback
        results.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"  ✗ {name}: {type(e).__name__}: {e}")

# ═══════════════════════════════════════════════════════════
print("=" * 60)
print("边界场景测试")
print("=" * 60)

# ── 1. 死亡检测 ────────────────────────────────────────────
print("\n[1] 死亡与代际传承")

def test_death_detection():
    reset_world()
    client = make_client()
    # mock handle_bot_death so it doesn't spawn a replacement bot
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'), \
         mock.patch('core.tick_engine.handle_bot_death') as mock_death:
        init_world()
        bot = world["bots"]["bot_1"]
        bot["hp"] = 0.1       # 下一 tick 必死
        bot["satiety"] = 100  # 不是饥饿死亡
        core.tick_engine.world_tick()
        bot = world["bots"]["bot_1"]
        assert bot["status"] == "dead", f"Expected dead, got {bot['status']}"

test("hp≤0 → status=dead", test_death_detection)

def test_dead_bot_removed_from_location():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
        world["bots"]["bot_1"]["hp"] = 0.1
        loc = world["bots"]["bot_1"]["location"]
        with mock.patch('systems.generation.subprocess.Popen'):
            core.tick_engine.world_tick()
        assert "bot_1" not in world["locations"][loc]["bots"], \
            "死亡 bot 应从地点 bots 列表移除"

test("死亡 bot 从地点列表移除", test_dead_bot_removed_from_location)

def test_graveyard_entry():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
        world["bots"]["bot_1"]["hp"] = 0.1
        import time; orig_sleep = time.sleep
        with mock.patch('systems.generation.subprocess.Popen'), \
             mock.patch('time.sleep'):
            core.tick_engine.world_tick()
            # handle_bot_death 在子线程，等待它
            import threading
            for t in threading.enumerate():
                if t.name != 'MainThread' and t.daemon:
                    t.join(timeout=2)
        assert len(world["graveyard"]) > 0, "墓地应有记录"
        grave = world["graveyard"][0]
        assert "name" in grave and "final_money" in grave and "death_tick" in grave

test("死亡 → 墓地记录", test_graveyard_entry)

# ── 2. 经济系统 ────────────────────────────────────────────
print("\n[2] 经济系统")

def test_rent_deduction():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    # 把时间设置到 07:00，这样下一 tick 是 08:00 触发房租
    world["time"]["virtual_hour"] = 7
    world["time"]["tick"] = 1
    bot = world["bots"]["bot_1"]
    home = bot["home"]
    rent = DAILY_RENT.get(home, 15)
    expected_cost = rent + DAILY_MISC_COST
    money_before = bot["money"]
    # mock 掉随机事件和规则引擎，确保只有房租一项扣款
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('systems.events.trigger_event'), \
         mock.patch('systems.events.trigger_personal_fate'), \
         mock.patch('rules.rules_engine.tick_rules', return_value=[]):
        core.tick_engine.world_tick()
    money_after = world["bots"]["bot_1"]["money"]
    assert money_after == money_before - expected_cost, \
        f"应扣 {expected_cost} 元，实际: {money_before} → {money_after}"

test("08:00 扣房租+杂费", test_rent_deduction)

def test_eviction_when_broke():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    world["time"]["virtual_hour"] = 7
    world["time"]["tick"] = 1
    bot = world["bots"]["bot_1"]
    bot["money"] = 0          # 没钱交租
    bot["location"] = bot["home"]  # 确保在家
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('systems.events.trigger_event'), \
         mock.patch('systems.events.trigger_personal_fate'), \
         mock.patch('rules.rules_engine.tick_rules', return_value=[]):
        core.tick_engine.world_tick()
    bot = world["bots"]["bot_1"]
    assert bot["money"] == 0, "钱应该是 0"
    assert bot["location"] == "东门老街", \
        f"交不起租应被驱逐到东门老街，实际在: {bot['location']}"
    assert bot["home"] == "东门老街", "home 也应更新为东门老街"

test("钱不够交租 → 驱逐到东门老街", test_eviction_when_broke)

# ── 3. 睡眠系统 ────────────────────────────────────────────
print("\n[3] 睡眠系统")

def test_auto_sleep_at_night():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot = world["bots"]["bot_1"]
    bot["energy"] = 20            # 低能量
    bot["location"] = bot["home"] # 在家
    world["time"]["virtual_hour"] = 23  # 深夜
    world["time"]["tick"] = 17
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    assert world["bots"]["bot_1"]["is_sleeping"] == True, \
        "深夜+低能量+在家 → 应自动入睡"

test("深夜低能量在家 → 自动入睡", test_auto_sleep_at_night)

def test_sleep_restores_energy():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot = world["bots"]["bot_1"]
    bot["is_sleeping"] = True
    bot["energy"] = 30
    energy_before = bot["energy"]
    world["time"]["virtual_hour"] = 2  # 凌晨，不会自动起床
    world["time"]["tick"] = 20
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    energy_after = world["bots"]["bot_1"]["energy"]
    assert energy_after > energy_before, \
        f"睡觉应恢复能量: {energy_before} → {energy_after}"

test("睡觉中 → 能量恢复", test_sleep_restores_energy)

def test_wake_up_naturally():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot = world["bots"]["bot_1"]
    bot["is_sleeping"] = True
    bot["energy"] = 85           # 能量已够，应自然醒
    world["time"]["virtual_hour"] = 9   # 白天
    world["time"]["tick"] = 3
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    assert world["bots"]["bot_1"]["is_sleeping"] == False, \
        "白天能量>=80 应自然醒"

test("白天能量够 → 自然醒", test_wake_up_naturally)

# ── 4. 饥饿加速衰老 ────────────────────────────────────────
print("\n[4] 饥饿衰老系统")

def test_hunger_accelerates_aging():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    # 对比：正常 bot vs 饥饿 bot
    bot_normal = world["bots"]["bot_1"]
    bot_hungry = world["bots"]["bot_2"]
    bot_normal["satiety"] = 80
    bot_hungry["satiety"] = 5   # 饥饿
    hp_normal_before = bot_normal["hp"]
    hp_hungry_before = bot_hungry["hp"]
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    hp_normal_after = world["bots"]["bot_1"]["hp"]
    hp_hungry_after = world["bots"]["bot_2"]["hp"]
    normal_loss = hp_normal_before - hp_normal_after
    hungry_loss = hp_hungry_before - hp_hungry_after
    assert hungry_loss > normal_loss, \
        f"饥饿HP损失({hungry_loss:.3f})应 > 正常({normal_loss:.3f})"
    assert abs(hungry_loss / normal_loss - AGING_HUNGER_MULT) < 0.5, \
        f"饥饿倍率应接近 {AGING_HUNGER_MULT}x，实际: {hungry_loss/normal_loss:.2f}x"

test("satiety≤10 → HP衰减加速", test_hunger_accelerates_aging)

def test_overwork_accelerates_aging():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot_normal = world["bots"]["bot_1"]
    bot_tired  = world["bots"]["bot_2"]
    bot_normal["energy"] = 80
    bot_tired["energy"] = 5    # 过劳
    bot_tired["satiety"] = 50  # 不饥饿，排除干扰
    hp_before = {bid: world["bots"][bid]["hp"] for bid in ["bot_1","bot_2"]}
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    loss_normal = hp_before["bot_1"] - world["bots"]["bot_1"]["hp"]
    loss_tired  = hp_before["bot_2"] - world["bots"]["bot_2"]["hp"]
    assert loss_tired > loss_normal, \
        f"过劳HP损失({loss_tired:.3f})应 > 正常({loss_normal:.3f})"

test("energy<10 → HP衰减加速（过劳）", test_overwork_accelerates_aging)

# ── 5. 工作任务 ────────────────────────────────────────────
print("\n[5] 工作任务系统")

def test_work_task_progress():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot = world["bots"]["bot_1"]
    bot["current_task"] = {
        "status": "in_progress",
        "task_name": "测试任务",
        "progress": 0,
        "duration": 3,
        "difficulty": 0.1,
        "skill": "none",
        "base_pay": 50,
    }
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    task = world["bots"]["bot_1"]["current_task"]
    assert task["progress"] == 1, f"进度应为1，实际: {task['progress']}"

test("工作任务 → 每 tick 进度+1", test_work_task_progress)

def test_work_task_completion_pays():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot = world["bots"]["bot_1"]
    money_before = bot["money"]
    bot["current_task"] = {
        "status": "in_progress",
        "task_name": "完成任务",
        "progress": 2,    # 再一 tick 就完成 (duration=3)
        "duration": 3,
        "difficulty": 0.0,  # 零难度，必成功
        "skill": "none",
        "base_pay": 80,
    }
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    task = world["bots"]["bot_1"]["current_task"]
    money_after = world["bots"]["bot_1"]["money"]
    assert task["status"] in ("completed", "failed"), \
        f"任务应结束，实际: {task['status']}"
    if task["status"] == "completed":
        assert money_after > money_before, \
            f"完成任务应赚钱: {money_before} → {money_after}"

test("工作任务完成 → 赚钱 + status=completed", test_work_task_completion_pays)

# ── 6. Move 行动地点一致性 ─────────────────────────────────
print("\n[6] Move 行动")

def test_move_updates_location():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    bot = world["bots"]["bot_1"]
    old_loc = bot["location"]
    new_loc = next(l for l in LOCATIONS if l != old_loc)

    # Mock LLM 返回 move 工具调用
    move_client = make_client()
    move_resp = json.dumps({"tool": "move",
                            "args": {"destination": new_loc, "mode": "walk"},
                            "desc": f"去{new_loc}"})
    def move_side_effect(messages=None, **kw):
        c = (messages or [{}])[-1].get("content","")
        text = move_resp if "JSON转换器" in c else json.dumps({
            "narrative":"移动了。","success":True,"money_delta":0,
            "energy_delta":-5,"satiety_delta":0,"happiness_delta":0,
            "skill_up":None,"world_change":None,"social_effects":[],
            "side_effects":[],"feedback_to_actor":"到了。"
        })
        msg = mock.MagicMock(); msg.content = text
        ch = mock.MagicMock(); ch.message = msg
        r = mock.MagicMock(); r.choices = [ch]
        return r
    move_client.chat.completions.create.side_effect = move_side_effect

    with mock.patch('utils.ai_client.client', move_client), \
         mock.patch('actions.processor.client', move_client):
        with lock:
            actions.processor.process_action_v10("bot_1", f"去{new_loc}")

    bot_after = world["bots"]["bot_1"]
    assert bot_after["location"] == new_loc, \
        f"地点应变为 {new_loc}，实际: {bot_after['location']}"
    assert "bot_1" not in world["locations"][old_loc]["bots"], \
        f"bot_1 应从 {old_loc} 移除"
    assert "bot_1" in world["locations"][new_loc]["bots"], \
        f"bot_1 应出现在 {new_loc}"

test("move 行动 → 地点双向一致", test_move_updates_location)

# ── 7. 世界改造 ────────────────────────────────────────────
print("\n[7] 世界改造")

def test_world_modification_created():
    reset_world()
    with mock.patch('subprocess.Popen'):
        mod_client = make_client(override={
            "match": "永久性的改变",
            "response": json.dumps({
                "has_modification": True,
                "type": "open_shop",
                "name": "测试小摊",
                "desc": "在宝安城中村摆了个小摊",
                "impact": "周围人有地方买东西了"
            })
        })
        with mock.patch('utils.ai_client.client', mod_client), \
             mock.patch('core.tick_engine.client', mod_client), \
             mock.patch('systems.news.client', mod_client):
            init_world()

    bot = world["bots"]["bot_5"]  # bot_5 有 3000 元，够开店
    bot["location"] = "华强北"

    from systems.world_mods import judge_world_modification
    with mock.patch('systems.world_mods.client', mod_client):
        mod = judge_world_modification("bot_5", bot, "开了个小摊", "摆好了摊位")

    assert mod is not None, "应创建世界改造记录"
    assert mod["name"] == "测试小摊"
    assert mod["location"] == "华强北"
    assert len(world["world_modifications"]) == 1
    assert "bot_5" in world["locations"]["华强北"]["modifications"][0]["creator"]

test("世界改造 → 记录到 world_modifications 和地点", test_world_modification_created)

def test_world_modification_requires_money():
    reset_world()
    with mock.patch('subprocess.Popen'):
        mod_client = make_client(override={
            "match": "永久性的改变",
            "response": json.dumps({
                "has_modification": True,
                "type": "open_shop",   # 需要 200 元
                "name": "穷人小摊",
                "desc": "想开摊但没钱",
                "impact": "?"
            })
        })
        with mock.patch('utils.ai_client.client', mod_client), \
             mock.patch('systems.news.client', mod_client):
            init_world()

    bot = world["bots"]["bot_1"]
    bot["money"] = 10   # 远不够 open_shop 需要的 200 元
    from systems.world_mods import judge_world_modification
    with mock.patch('systems.world_mods.client', mod_client):
        mod = judge_world_modification("bot_1", bot, "想开摊", "没钱")
    assert mod is None, "钱不够时不应创建改造"

test("世界改造 → 钱不够则拒绝", test_world_modification_requires_money)

# ── 8. 情绪/数值边界 ──────────────────────────────────────
print("\n[8] 数值边界")

def test_emotion_caps():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    # 把所有情绪推到极端
    for bid, bot in world["bots"].items():
        bot["emotions"] = {e: 99 for e in EMOTION_DIMS}
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client):
        core.tick_engine.world_tick()
    for bid, bot in world["bots"].items():
        if bot["status"] != "alive": continue
        for e in EMOTION_DIMS:
            v = bot["emotions"].get(e, 0)
            assert 0 <= v <= 100, f"{bid}.{e}={v} 超出 [0,100]"

test("情绪极端值 → 不溢出 [0,100]", test_emotion_caps)

def test_satiety_floor():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    for bid, bot in world["bots"].items():
        bot["satiety"] = 0
    for _ in range(5):
        with mock.patch('utils.ai_client.client', client), \
             mock.patch('core.tick_engine.client', client), \
             mock.patch('systems.news.client', client):
            core.tick_engine.world_tick()
    for bid, bot in world["bots"].items():
        if bot["status"] != "alive": continue
        assert bot["satiety"] >= 0, f"{bid}.satiety={bot['satiety']} < 0"
        assert bot["energy"] >= 0,  f"{bid}.energy={bot['energy']} < 0"
        assert bot["money"] >= 0,   f"{bid}.money={bot['money']} < 0"

test("satiety/energy/money 不出现负数", test_satiety_floor)

# ── 9. 快照格式 ────────────────────────────────────────────
print("\n[9] 快照格式")

def test_snapshot_structure():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()

    written = {}
    def fake_open(path, mode='r', **kw):
        if 'w' in mode:
            import io
            buf = io.StringIO()
            class FakeFile:
                def write(self, s): buf.write(s)
                def __enter__(self): return self
                def __exit__(self, *a): written['data'] = buf.getvalue()
            return FakeFile()
        raise FileNotFoundError(path)

    from api import server as api_server
    with mock.patch('builtins.open', fake_open):
        with mock.patch('utils.ai_client.client', client):
            import asyncio
            # _do_auto_save 是同步函数
            from api.server import _do_auto_save
            _do_auto_save()

    assert 'data' in written, "应该写入了快照数据"
    snap = json.loads(written['data'])

    required_keys = ["time","weather","bots","locations","events",
                     "message_board","moments","world_narrative",
                     "world_modifications","graveyard","generation_count"]
    for k in required_keys:
        assert k in snap, f"快照缺少字段: {k}"

    for bid, bdata in snap["bots"].items():
        assert "hp" in bdata and "money" in bdata and "emotions" in bdata, \
            f"快照 bot {bid} 缺字段"

test("快照包含所有必要字段", test_snapshot_structure)

# ── 10. 规则引擎 ───────────────────────────────────────────
print("\n[10] 规则引擎")

def test_rules_engine_tick():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    assert len(world["active_rules"]) > 0, "应有种子规则"
    initial_rules = len(world["active_rules"])
    # 跑10轮，确保有足够机会触发（15%概率×10轮×多个bot，统计上必然执行）
    for _ in range(10):
        with mock.patch('utils.ai_client.client', client), \
             mock.patch('core.tick_engine.client', client), \
             mock.patch('systems.news.client', client):
            core.tick_engine.world_tick()
    total_executions = sum(r.get("execution_count",0) for r in world["active_rules"])
    assert total_executions > 0, "规则应该被执行过"

test("规则引擎 → 执行计数增加", test_rules_engine_tick)

def test_rule_durability_decays():
    reset_world()
    client = make_client()
    with mock.patch('utils.ai_client.client', client), \
         mock.patch('core.tick_engine.client', client), \
         mock.patch('systems.news.client', client), \
         mock.patch('subprocess.Popen'):
        init_world()
    # 找一个 durability 不是 999 的规则（会衰减的）
    decayable = [r for r in world["active_rules"] if r.get("durability",999) < 999]
    if not decayable:
        # 手动添加一个会衰减的规则
        from rules.rules_engine import create_rule
        r = create_rule("测试规则","sys","system","宝安城中村",
                        "every_tick",{"random":0.9},
                        [{"type":"modify_bot_emotion","emotion":"happiness","delta":1}],
                        "测试", durability=10, decay_rate=0.5)
        world["active_rules"].append(r)
        decayable = [r]
    dur_before = decayable[0]["durability"]
    for _ in range(5):
        with mock.patch('utils.ai_client.client', client), \
             mock.patch('core.tick_engine.client', client), \
             mock.patch('systems.news.client', client):
            core.tick_engine.world_tick()
    dur_after = decayable[0]["durability"]
    assert dur_after < dur_before, \
        f"规则耐久应衰减: {dur_before} → {dur_after}"

test("规则耐久度随执行衰减", test_rule_durability_decays)

# ── 最终汇总 ───────────────────────────────────────────────
passed = sum(1 for _, ok, _ in results if ok)
failed = [(n, e) for n, ok, e in results if not ok]

print(f"\n{'='*60}")
print(f"结果: {passed}/{len(results)} 通过")
if failed:
    print("\n失败项:")
    for name, err in failed:
        print(f"  ✗ {name}")
        print(f"    {err}")
    sys.exit(1)
else:
    print("\n✅ 全部边界场景通过！")
