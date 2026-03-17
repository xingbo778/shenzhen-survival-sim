#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳生存模拟 - 全流程集成测试
Mock LLM 返回，跑 10 轮 world_tick + bot 行动，验证世界状态一致性
"""
import sys, os, json, random, logging
import unittest.mock as mock

# ============================================================
# 1. 先 mock 掉所有外部依赖（在 import 之前）
# ============================================================
os.makedirs = mock.MagicMock()  # /home/ubuntu 路径

# Stub openai 模块（未安装）
_mock_openai = mock.MagicMock()
sys.modules['openai'] = _mock_openai

# Mock logging FileHandler
_null_handler = logging.NullHandler()
with mock.patch('logging.FileHandler', return_value=_null_handler), \
     mock.patch('logging.StreamHandler', return_value=_null_handler):
    from core.world_state import world, lock, log, create_bot, init_world, generate_npcs
    from core.constants import (LOCATIONS, PERSONAS, FOOD_MENU, JOBS,
                                 EMOTION_DIMS, WEATHER_TYPES)
    import utils.ai_client
    import systems.news
    import systems.world_mods
    import core.tick_engine
    import actions.processor


# ============================================================
# 2. 构建智能 Mock LLM：根据 prompt 内容返回对应格式
# ============================================================
MOCK_EXECUTE_GENERIC_RESULT = json.dumps({
    "narrative": "他在原地休息了一会儿，感觉放松了些。",
    "success": True,
    "money_delta": 0,
    "energy_delta": 8,
    "satiety_delta": -2,
    "happiness_delta": 3,
    "skill_up": None,
    "world_change": None,
    "social_effects": [],
    "side_effects": ["旁边的人看了一眼，继续忙自己的事"],
    "feedback_to_actor": "你靠在墙边休息，感觉好多了。"
})

MOCK_TOOL_CALL_REST = json.dumps({
    "tool": "use_resource",
    "args": {"resource": "energy", "amount": 0, "purpose": "休息放松"},
    "desc": "休息一下"
})

MOCK_NEWS = "深圳今日天气晴好，适合外出活动\n华强北电子产品销量创新高\n南山科技园新增多家AI创业公司"
MOCK_TOPICS = "深圳打工人的日常\n城中村美食推荐\n今天又加班了\n深圳租房太贵了\n周末去哪玩"
MOCK_NARRATIVE = "城市在喧嚣中静静运转，每个人都在为自己的生活拼命。"
MOCK_VIBE = "热闹的"
MOCK_NO_MODIFICATION = json.dumps({"has_modification": False})


def smart_llm_mock(messages=None, model=None, temperature=None, max_tokens=None, **kwargs):
    """根据 prompt 内容返回对应的 mock 响应"""
    content = messages[-1]["content"] if messages else ""

    # 判断是哪种调用
    if "工具调用" in content and "后果" in content:
        # execute_generic - 判断行动后果
        text = MOCK_EXECUTE_GENERIC_RESULT
    elif "JSON转换器" in content and "工具" in content:
        # process_action_v10 - 解析行动为工具调用
        text = MOCK_TOOL_CALL_REST
    elif "JSON转换器" in content and "5大行动类别" in content:
        # process_action - 旧版行动解析
        text = json.dumps({"category": "survive", "type": "rest", "desc": "休息"})
    elif "生成3条虚构" in content or "深圳本地新闻" in content:
        # fetch_real_news
        text = MOCK_NEWS
    elif "热搜话题" in content:
        # generate_hot_topics
        text = MOCK_TOPICS
    elif "城市日记" in content or "旁观者" in content:
        # _generate_world_narrative
        text = MOCK_NARRATIVE
    elif "氛围词" in content or "氛围" in content:
        # _update_location_vibe
        text = MOCK_VIBE
    elif "永久性的改变" in content or "has_modification" in content:
        # judge_world_modification
        text = MOCK_NO_MODIFICATION
    else:
        # fallback
        text = json.dumps({"tool": "use_resource", "args": {"resource": "energy", "amount": 0, "purpose": "休息"}, "desc": "休息"})

    # 构造 OpenAI response 结构
    msg = mock.MagicMock()
    msg.content = text
    choice = mock.MagicMock()
    choice.message = msg
    resp = mock.MagicMock()
    resp.choices = [choice]
    return resp


# ============================================================
# 3. 初始化世界（mock 掉 subprocess 和 rules import）
# ============================================================
print("=" * 60)
print("深圳生存模拟 - 全流程集成测试")
print("=" * 60)

mock_client = mock.MagicMock()
mock_client.chat.completions.create.side_effect = smart_llm_mock

# Patch client in all modules
patches = [
    mock.patch('utils.ai_client.client', mock_client),
    mock.patch('systems.news.client', mock_client),
    mock.patch('systems.world_mods.client', mock_client),
    mock.patch('core.tick_engine.client', mock_client),
    mock.patch('actions.processor.client', mock_client),
    mock.patch('subprocess.Popen'),  # 不启动 bot 子进程
]
for p in patches:
    p.start()

# 初始化世界
print("\n[初始化] 创建世界...")
init_world()
print(f"  地点数: {len(world['locations'])}")
print(f"  Bot 数: {len(world['bots'])}")
print(f"  活跃规则: {len(world.get('active_rules', []))}")

from core.tick_engine import world_tick
from actions.processor import process_action_v10

# ============================================================
# 4. 记录初始状态
# ============================================================
initial_state = {}
for bid, bot in world['bots'].items():
    initial_state[bid] = {
        'hp': bot['hp'],
        'money': bot['money'],
        'location': bot['location'],
    }

# ============================================================
# 5. 主循环：10 轮 tick + 每轮每个 bot 行动一次
# ============================================================
print("\n[主循环] 开始 10 轮模拟...\n")

BOT_PLANS = [
    "休息一下",
    "在附近走走",
    "想想今天的事",
    "找个地方坐坐",
    "刷一会儿手机",
]

errors = []
tick_summaries = []

for tick_num in range(1, 11):
    try:
        world_tick()
    except Exception as e:
        errors.append(f"Tick {tick_num} world_tick 异常: {e}")
        import traceback; traceback.print_exc()
        continue

    t = world['time']
    alive = [bid for bid, b in world['bots'].items() if b['status'] == 'alive']

    # 每个存活 bot 执行一次行动
    action_results = []
    for bid in alive:
        bot = world['bots'][bid]
        if bot.get('is_sleeping'):
            continue
        plan = random.choice(BOT_PLANS)
        try:
            with lock:
                result = process_action_v10(bid, plan)
            action_results.append((bid, plan, True))
        except Exception as e:
            errors.append(f"Tick {tick_num} bot {bid} action 异常: {e}")
            action_results.append((bid, plan, False))

    ok_count = sum(1 for _, _, ok in action_results if ok)
    summary = (f"  Tick {tick_num:2d} | {t['virtual_datetime']:12s} | "
               f"天气:{world['weather']['current']:4s} | "
               f"存活:{len(alive)}/10 | "
               f"行动:{ok_count}/{len(action_results)} OK")
    tick_summaries.append(summary)
    print(summary)

# ============================================================
# 6. 验证世界状态一致性
# ============================================================
print("\n[验证] 检查世界状态一致性...")
checks_passed = 0
checks_failed = 0

def check(condition, msg):
    global checks_passed, checks_failed
    if condition:
        print(f"  ✓ {msg}")
        checks_passed += 1
    else:
        print(f"  ✗ {msg}")
        checks_failed += 1

# --- 时间 ---
check(world['time']['tick'] == 10, f"Tick 计数器 = 10 (got {world['time']['tick']})")
check(0 <= world['time']['virtual_hour'] <= 23, f"virtual_hour 在 [0,23] 范围内")

# --- 天气 ---
check(world['weather']['current'] in WEATHER_TYPES, f"天气合법: {world['weather']['current']}")

# --- 新闻 ---
check(len(world['news_feed']) > 0, f"news_feed 有内容 ({len(world['news_feed'])} 条)")
check(len(world['hot_topics']) > 0, f"hot_topics 有内容 ({len(world['hot_topics'])} 条)")

# --- 事件 ---
check(len(world['events']) > 0, f"世界事件被记录 ({len(world['events'])} 个)")

# --- Bot 状态 ---
alive_bots = {bid: b for bid, b in world['bots'].items() if b['status'] == 'alive'}
check(len(alive_bots) > 0, f"至少有 1 个存活 bot ({len(alive_bots)} 个)")

for bid, bot in world['bots'].items():
    # HP 只减不增（除非是死亡）
    if bot['status'] == 'alive':
        check(0 <= bot['hp'] <= 100, f"{bid} HP 在 [0,100]: {bot['hp']:.1f}")
        check(0 <= bot['energy'] <= 100, f"{bid} energy 在 [0,100]: {bot['energy']}")
        check(0 <= bot['satiety'] <= 100, f"{bid} satiety 在 [0,100]: {bot['satiety']}")
        check(bot['money'] >= 0, f"{bid} money >= 0: {bot['money']}")
        check(bot['location'] in LOCATIONS, f"{bid} 在合법地点: {bot['location']}")
        for emo in EMOTION_DIMS:
            check(0 <= bot['emotions'].get(emo, 0) <= 100,
                  f"{bid} emotion[{emo}] 在 [0,100]: {bot['emotions'].get(emo,0):.1f}")

# --- 地点一관性: bot 在地点 bots 列表里 ---
for bid, bot in alive_bots.items():
    loc = bot['location']
    in_loc = bid in world['locations'].get(loc, {}).get('bots', [])
    check(in_loc, f"{bid}({bot['name']}) 在 {loc} 的 bots 列表里")

# --- action_log 被记录 ---
logged = sum(len(b.get('action_log', [])) for b in world['bots'].values())
check(logged > 0, f"action_log 有记录 (共 {logged} 条)")

# --- HP 经过 10 tick 确实有衰减 ---
for bid, bot in alive_bots.items():
    orig_hp = initial_state[bid]['hp']
    # HP 应该比初始低（基础衰老 0.5/tick × 10 = 5）
    check(bot['hp'] < orig_hp,
          f"{bid} HP 有衰减: {orig_hp} → {bot['hp']:.1f}")

# ============================================================
# 7. LLM Mock 调用统计
# ============================================================
call_count = mock_client.chat.completions.create.call_count
print(f"\n[LLM Mock 统计]")
print(f"  总调用次数: {call_count}")

# ============================================================
# 8. 最终报告
# ============================================================
print(f"\n{'='*60}")
print(f"[结果] 通过: {checks_passed}  失败: {checks_failed}  错误: {len(errors)}")

if errors:
    print("\n[错误列表]")
    for e in errors:
        print(f"  ✗ {e}")

if checks_failed == 0 and len(errors) == 0:
    print("\n✅ 全部通过！10 轮全流程模拟正常运行。")
else:
    print("\n❌ 有失败项，需要排查。")
    sys.exit(1)
