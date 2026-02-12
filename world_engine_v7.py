#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳生存模拟 - 世界引擎 v7
新增:
- 日夜节律/睡眠系统
- Selfie/拍照技能 (Grok API)
- 消息优先级 (父母=high)
- 价值观动态演化
- 深层记忆系统 (重要/普通)
- 情感化人际关系 (信任/敌意/好感度)
- Bot详情API
"""

import os, time, json, random, logging, copy, subprocess, sys
from datetime import datetime, timedelta
from threading import Lock, Thread

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI

# Grok 图像生成
sys.path.insert(0, "/home/ubuntu")
# Grok图像生成 - 直接导入脚本
import importlib.util
_spec = importlib.util.spec_from_file_location("generate_image", "/home/ubuntu/skills/grok-image-generator/scripts/generate_image.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
grok_generate = _mod.generate_image

# ============================================================
# 日志
# ============================================================
os.makedirs("/home/ubuntu/logs", exist_ok=True)
os.makedirs("/home/ubuntu/selfies", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORLD] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("/home/ubuntu/logs/world_engine.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("world")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
scheduler = BackgroundScheduler()
lock = Lock()
client = OpenAI()

# ============================================================
# 世界常量
# ============================================================
TICK_SECONDS = 75          # 1 tick = 1虚拟小时 = 75真实秒
HP_DECAY_PER_TICK = 1
SATIETY_DECAY = 3
ENERGY_NIGHT_RECOVER = 8
ENERGY_DAY_COST = 2
ENERGY_SLEEP_RECOVER = 15  # 睡觉时每tick恢复

# ============================================================
# 欲望系统
# ============================================================
# 每个欲望维度: 0-100, 越高越强烈
# lust=性欲, power=权力欲, greed=物欲, vanity=虚荣心, security=安全感需求
DESIRE_DECAY_ON_FULFILL = 40   # 满足后降低
DESIRE_GROWTH_PER_TICK = {      # 每tick自然增长率(基础值，个体有差异)
    "lust": 2.5,
    "power": 0.5,
    "greed": 1.0,
    "vanity": 0.8,
    "security": 0.6,
}

# 每个Bot的个性化欲望配置: {初始值, 增长倍率}
BOT_DESIRE_PROFILES = {
    "bot_1":  {"lust": 15, "power": 10, "greed": 20, "vanity": 5,  "security": 40, "lust_mult": 1.8, "power_mult": 0.5, "greed_mult": 0.8, "vanity_mult": 0.3, "security_mult": 1.5},  # 李浩然: 社恐程序员，安全感需求高
    "bot_2":  {"lust": 20, "power": 35, "greed": 45, "vanity": 40, "security": 30, "lust_mult": 1.0, "power_mult": 1.3, "greed_mult": 1.5, "vanity_mult": 1.3, "security_mult": 1.0},  # 王雪: 精致利己，物欲权力欲强
    "bot_3":  {"lust": 25, "power": 5,  "greed": 15, "vanity": 5,  "security": 50, "lust_mult": 2.0, "power_mult": 0.3, "greed_mult": 0.6, "vanity_mult": 0.2, "security_mult": 1.8},  # 张伟: 朴实打工人，安全感最重要
    "bot_4":  {"lust": 10, "power": 5,  "greed": 5,  "vanity": 15, "security": 20, "lust_mult": 0.6, "power_mult": 0.3, "greed_mult": 0.3, "vanity_mult": 0.8, "security_mult": 0.8},  # 陈静: 浪漫主义，欲望淡泊
    "bot_5":  {"lust": 40, "power": 20, "greed": 50, "vanity": 45, "security": 5,  "lust_mult": 2.5, "power_mult": 0.8, "greed_mult": 1.8, "vanity_mult": 1.5, "security_mult": 0.2},  # 赵磊: 享乐主义富二代
    "bot_6":  {"lust": 15, "power": 40, "greed": 35, "vanity": 20, "security": 35, "lust_mult": 0.7, "power_mult": 1.5, "greed_mult": 1.2, "vanity_mult": 0.8, "security_mult": 1.2},  # 刘悦: 目标导向创业者，权力欲强
    "bot_7":  {"lust": 20, "power": 35, "greed": 50, "vanity": 15, "security": 40, "lust_mult": 1.5, "power_mult": 1.2, "greed_mult": 1.8, "vanity_mult": 0.5, "security_mult": 1.3},  # 周建国: 老商人，物欲和安全感
    "bot_8":  {"lust": 5,  "power": 5,  "greed": 10, "vanity": 5,  "security": 60, "lust_mult": 0.3, "power_mult": 0.2, "greed_mult": 0.4, "vanity_mult": 0.2, "security_mult": 2.0},  # 吴秀英: 母亲，安全感最强
    "bot_9":  {"lust": 30, "power": 5,  "greed": 10, "vanity": 30, "security": 15, "lust_mult": 2.0, "power_mult": 0.2, "greed_mult": 0.4, "vanity_mult": 1.2, "security_mult": 0.6},  # 林枫: 理想主义音乐人
    "bot_10": {"lust": 20, "power": 15, "greed": 30, "vanity": 60, "security": 20, "lust_mult": 1.0, "power_mult": 0.6, "greed_mult": 1.0, "vanity_mult": 2.0, "security_mult": 0.8},  # 苏小小: 网红，虚荣心爆表
}

# 默认欲望配置(新Bot)
DEFAULT_DESIRE_PROFILE = {"lust": 20, "power": 15, "greed": 20, "vanity": 15, "security": 25, "lust_mult": 1.0, "power_mult": 1.0, "greed_mult": 1.0, "vanity_mult": 1.0, "security_mult": 1.0}

# 家庭关系定义
FAMILY_RELATIONS = {
    "bot_8": {"role": "parent", "children": ["bot_3"]},   # 吴秀英 是 张伟 的母亲
    "bot_3": {"role": "child", "parents": ["bot_8"]},      # 张伟 是 吴秀英 的儿子
}

LOCATIONS = {
    "宝安城中村": {"type": "residential", "rent": 20, "desc": "便宜但嘈杂的城中村，外来务工者聚集地"},
    "南山科技园": {"type": "work", "rent": 0, "desc": "腾讯、大疆等科技巨头的总部所在地"},
    "南山公寓":   {"type": "residential", "rent": 80, "desc": "白领聚集的中高档公寓区"},
    "华强北":     {"type": "commercial", "rent": 0, "desc": "全球最大的电子产品市场"},
    "福田CBD":    {"type": "work", "rent": 0, "desc": "深圳的金融中心，银行和基金公司林立"},
    "东门老街":   {"type": "commercial", "rent": 0, "desc": "热闹的商业步行街，餐饮和零售密集"},
    "深圳湾公园": {"type": "leisure", "rent": 0, "desc": "海边公园，适合休闲和社交"},
}

JOBS = {
    "南山科技园": [
        {"title": "初级程序员", "pay": 80, "skill": "programming", "min_skill": 10,
         "tasks": [
             {"name": "修复登录页面Bug", "duration": 3, "difficulty": 0.3, "desc": "用户反馈登录页面偶尔白屏"},
             {"name": "写商品列表API接口", "duration": 2, "difficulty": 0.2, "desc": "后端需要新增一个分页查询接口"},
             {"name": "做代码Review", "duration": 2, "difficulty": 0.15, "desc": "审查同事提交的PR"},
             {"name": "优化数据库查询性能", "duration": 4, "difficulty": 0.4, "desc": "首页加载太慢，需要优化SQL"},
         ],
         "challenges": ["产品经理突然改需求", "线上服务器报警了", "代码合并冲突", "测试发现新Bug", "需求文档不清楚"]},
        {"title": "高级程序员", "pay": 200, "skill": "programming", "min_skill": 30,
         "tasks": [
             {"name": "设计微服务架构方案", "duration": 4, "difficulty": 0.5, "desc": "系统需要从单体迁移到微服务"},
             {"name": "排查线上内存泄漏", "duration": 3, "difficulty": 0.6, "desc": "生产环境OOM频发"},
             {"name": "带新人做技术分享", "duration": 2, "difficulty": 0.2, "desc": "给团队做一次技术培训"},
             {"name": "重构支付模块", "duration": 5, "difficulty": 0.7, "desc": "支付系统代码年久失修"},
         ],
         "challenges": ["CTO要求提前上线", "核心依赖库有安全漏洞", "团队成员请假了", "客户投诉升级"]},
        {"title": "产品经理", "pay": 150, "skill": "social", "min_skill": 20,
         "tasks": [
             {"name": "撰写需求文档PRD", "duration": 3, "difficulty": 0.3, "desc": "新功能需要详细的需求说明"},
             {"name": "组织需求评审会", "duration": 2, "difficulty": 0.25, "desc": "拉齐各方对需求的理解"},
             {"name": "分析用户反馈数据", "duration": 2, "difficulty": 0.2, "desc": "从用户反馈中提炼改进方向"},
             {"name": "制定产品路线图", "duration": 4, "difficulty": 0.5, "desc": "规划下季度产品迭代计划"},
         ],
         "challenges": ["老板和用户需求矛盾", "开发说做不了", "竞品发布了类似功能", "数据指标下滑"]},
    ],
    "福田CBD": [
        {"title": "金融分析师", "pay": 120, "skill": "analysis", "min_skill": 15,
         "tasks": [
             {"name": "撰写行业研究报告", "duration": 3, "difficulty": 0.4, "desc": "分析新能源行业投资机会"},
             {"name": "建立财务模型", "duration": 4, "difficulty": 0.5, "desc": "为目标公司做DCF估值"},
             {"name": "准备投资路演材料", "duration": 2, "difficulty": 0.3, "desc": "给LP做季度汇报"},
             {"name": "尽职调查", "duration": 3, "difficulty": 0.45, "desc": "实地考察拟投企业"},
         ],
         "challenges": ["数据源不一致", "市场突然大跌", "客户质疑分析结论", "合规审查卡住了"]},
        {"title": "销售代表", "pay": 60, "skill": "social", "min_skill": 5,
         "tasks": [
             {"name": "电话拜访潜在客户", "duration": 2, "difficulty": 0.2, "desc": "从名单中筛选并联系客户"},
             {"name": "上门拜访客户", "duration": 3, "difficulty": 0.35, "desc": "带着方案去客户公司演示"},
             {"name": "跟进合同签署", "duration": 2, "difficulty": 0.3, "desc": "客户有意向但还在犹豫"},
             {"name": "参加行业展会", "duration": 2, "difficulty": 0.15, "desc": "在展会上收集名片拓展人脉"},
         ],
         "challenges": ["客户放鸽子", "竞争对手报价更低", "客户预算砍了一半", "被前台拦住了"]},
        {"title": "行政助理", "pay": 50, "skill": "social", "min_skill": 0,
         "tasks": [
             {"name": "整理会议纪要", "duration": 2, "difficulty": 0.1, "desc": "记录并整理上午的部门会议"},
             {"name": "安排领导出差行程", "duration": 2, "difficulty": 0.2, "desc": "订机票酒店安排接送"},
             {"name": "采购办公用品", "duration": 2, "difficulty": 0.1, "desc": "统计各部门需求并下单"},
             {"name": "组织团建活动", "duration": 3, "difficulty": 0.25, "desc": "策划下周的部门团建"},
         ],
         "challenges": ["领导临时改行程", "预算超标了", "供应商缺货", "同事投诉"]},
    ],
    "华强北": [
        {"title": "电子维修", "pay": 70, "skill": "hardware", "min_skill": 10,
         "tasks": [
             {"name": "修手机碎屏", "duration": 2, "difficulty": 0.2, "desc": "iPhone换外屏"},
             {"name": "修笔记本主板", "duration": 3, "difficulty": 0.5, "desc": "客户笔记本不开机"},
             {"name": "数据恢复", "duration": 3, "difficulty": 0.4, "desc": "硬盘摔了，客户急需恢复数据"},
             {"name": "组装台式机", "duration": 2, "difficulty": 0.15, "desc": "按客户配置单装机"},
         ],
         "challenges": ["配件缺货要等", "修完发现新问题", "客户嫌贵要砍价", "烙铁烫到手了"]},
        {"title": "档口销售", "pay": 55, "skill": "social", "min_skill": 5,
         "tasks": [
             {"name": "向游客推销手机壳", "duration": 2, "difficulty": 0.15, "desc": "门口来了一群游客"},
             {"name": "批发谈判", "duration": 3, "difficulty": 0.35, "desc": "有个客户要批发100个充电宝"},
             {"name": "盘点库存", "duration": 2, "difficulty": 0.1, "desc": "月底了要清点货物"},
             {"name": "直播带货", "duration": 3, "difficulty": 0.3, "desc": "老板让你试试直播卖货"},
         ],
         "challenges": ["遇到砍价高手", "发现有假货混入", "隔壁档口打价格战", "城管来检查了"]},
        {"title": "快递分拣", "pay": 40, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "分拣包裹到对应区域", "duration": 2, "difficulty": 0.1, "desc": "今天有500个包裹要分"},
             {"name": "装车发货", "duration": 2, "difficulty": 0.15, "desc": "下午的货车要装满"},
             {"name": "处理退货包裹", "duration": 2, "difficulty": 0.1, "desc": "退货区堆了一堆"},
             {"name": "双十一加班分拣", "duration": 3, "difficulty": 0.2, "desc": "包裹量翻了三倍"},
         ],
         "challenges": ["包裹太重闪了腰", "扫码枪没电了", "地址看不清", "传送带卡住了"]},
    ],
    "宝安城中村": [
        {"title": "外卖骑手", "pay": 40, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "午高峰送餐", "duration": 2, "difficulty": 0.15, "desc": "10单外卖要在1小时内送完"},
             {"name": "雨天加急单", "duration": 2, "difficulty": 0.3, "desc": "下雨了单量暴增"},
             {"name": "送夜宵订单", "duration": 2, "difficulty": 0.1, "desc": "深夜还有人点烧烤"},
             {"name": "跑腿代购", "duration": 2, "difficulty": 0.15, "desc": "客户让帮忙买药"},
         ],
         "challenges": ["电动车没电了", "找不到楼栋号", "客户不接电话", "被交警拦了"]},
        {"title": "保洁阿姨", "pay": 30, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "打扫出租屋", "duration": 2, "difficulty": 0.1, "desc": "租客退房了要打扫"},
             {"name": "清洗公共区域", "duration": 2, "difficulty": 0.1, "desc": "楼道和天台要清洁"},
             {"name": "洗衣收衣服务", "duration": 2, "difficulty": 0.1, "desc": "帮忙洗衣服赚外快"},
             {"name": "垃圾分类整理", "duration": 2, "difficulty": 0.05, "desc": "把可回收物分出来卖钱"},
         ],
         "challenges": ["水管堵了", "租客投诉没打扫干净", "垃圾太多搬不动", "清洁剂用完了"]},
        {"title": "城中村小卖部", "pay": 35, "skill": "social", "min_skill": 0,
         "tasks": [
             {"name": "看店收银", "duration": 2, "difficulty": 0.1, "desc": "老板出去了让你看店"},
             {"name": "进货搬货", "duration": 2, "difficulty": 0.15, "desc": "批发市场的货到了"},
             {"name": "夜间值班", "duration": 3, "difficulty": 0.1, "desc": "通宵看店"},
             {"name": "帮人代收快递", "duration": 2, "difficulty": 0.05, "desc": "邻居的快递放你这"},
         ],
         "challenges": ["收到假钞", "货物过期了", "有人赊账不还", "冰柜坏了"]},
    ],
    "南山公寓": [
        {"title": "家政服务", "pay": 45, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "做饭保洁", "duration": 2, "difficulty": 0.15, "desc": "给白领家庭做晚饭和打扫"},
             {"name": "照看小孩", "duration": 3, "difficulty": 0.2, "desc": "家长加班让你帮忙带孩子"},
             {"name": "整理收纳", "duration": 2, "difficulty": 0.1, "desc": "帮客户整理衣柜和杂物"},
             {"name": "遛狗", "duration": 2, "difficulty": 0.05, "desc": "主人出差了要帮忙遛狗"},
         ],
         "challenges": ["小孩不听话", "狗跑丢了", "客户嫌做的菜不好吃", "钥匙锁屋里了"]},
        {"title": "网约车司机", "pay": 55, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "早高峰接单", "duration": 2, "difficulty": 0.2, "desc": "7-9点单量最大"},
             {"name": "机场接送", "duration": 3, "difficulty": 0.15, "desc": "送客人去宝安机场"},
             {"name": "夜间代驾", "duration": 3, "difficulty": 0.25, "desc": "酒吧门口等代驾单"},
             {"name": "拼车单", "duration": 2, "difficulty": 0.15, "desc": "顺路拼车多赚一点"},
         ],
         "challenges": ["堵车迟到被投诉", "乘客醉酒吐车上", "导航绕路了", "油费涨了"]},
    ],
    "深圳湾公园": [
        {"title": "公园保安", "pay": 35, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "巡逻公园", "duration": 2, "difficulty": 0.1, "desc": "沿海边步道巡逻一圈"},
             {"name": "维持秩序", "duration": 2, "difficulty": 0.15, "desc": "周末人太多了"},
             {"name": "看管停车场", "duration": 3, "difficulty": 0.1, "desc": "指挥车辆停放"},
             {"name": "处理游客纠纷", "duration": 2, "difficulty": 0.2, "desc": "两拨人抢烧烤位"},
         ],
         "challenges": ["有人翻栏杆", "丢了东西来找你", "天太热中暑了", "遇到不讲理的人"]},
    ],
    "东门老街": [
        {"title": "餐厅服务员", "pay": 35, "skill": "none", "min_skill": 0,
         "tasks": [
             {"name": "午餐高峰期端菜", "duration": 2, "difficulty": 0.15, "desc": "12点了，客人排队等位"},
             {"name": "收拾桌子翻台", "duration": 2, "difficulty": 0.1, "desc": "外面还有人等位"},
             {"name": "帮厨切菜备料", "duration": 2, "difficulty": 0.1, "desc": "厨房人手不够"},
             {"name": "招待VIP包间", "duration": 3, "difficulty": 0.25, "desc": "老板的朋友来了要好好招待"},
         ],
         "challenges": ["上错菜了", "客人投诉菜太咸", "打碎了一个盘子", "被热油溅到"]},
        {"title": "街头艺人", "pay": 45, "skill": "art", "min_skill": 10,
         "tasks": [
             {"name": "街头吉他弹唱", "duration": 3, "difficulty": 0.2, "desc": "在步行街找个好位置表演"},
             {"name": "画人像速写", "duration": 2, "difficulty": 0.3, "desc": "有路人想画一幅肖像"},
             {"name": "参加街头艺术节", "duration": 4, "difficulty": 0.35, "desc": "东门组织了街头艺术活动"},
             {"name": "录制短视频", "duration": 2, "difficulty": 0.2, "desc": "把表演录下来发到网上"},
         ],
         "challenges": ["下雨了没法表演", "音响没电了", "城管让换地方", "围观的人不给钱"]},
        {"title": "小摊贩", "pay": 50, "skill": "social", "min_skill": 5,
         "tasks": [
             {"name": "摆摊卖烤红薯", "duration": 3, "difficulty": 0.15, "desc": "天冷了烤红薯好卖"},
             {"name": "进货补充库存", "duration": 2, "difficulty": 0.2, "desc": "去批发市场拿新货"},
             {"name": "夜市摆摊", "duration": 3, "difficulty": 0.2, "desc": "晚上人流量大"},
             {"name": "试卖新品种", "duration": 2, "difficulty": 0.25, "desc": "尝试卖手工饰品"},
         ],
         "challenges": ["城管来了要跑", "货卖不动", "被同行挤了位置", "找零钱不够了"]},
    ],
}

FOOD_MENU = {
    "路边摊炒粉": {"cost": 8, "satiety": 25},
    "城中村快餐": {"cost": 15, "satiety": 40},
    "便利店饭团": {"cost": 10, "satiety": 20},
    "餐厅套餐":   {"cost": 30, "satiety": 60},
    "火锅大餐":   {"cost": 80, "satiety": 90},
}

RANDOM_EVENTS = [
    {"name": "台风预警", "desc": "台风来袭，所有户外工作暂停一小时", "effect": "no_outdoor_work"},
    {"name": "科技园招聘会", "desc": "南山科技园举办大型招聘会，工资临时+50%", "effect": "bonus_nanshan"},
    {"name": "华强北大甩卖", "desc": "华强北商家清仓，物品价格减半", "effect": "discount_huaqiang"},
    {"name": "城中村停水", "desc": "宝安城中村停水，居民需要外出解决饮水问题", "effect": "no_water_baoan"},
    {"name": "深圳湾音乐节", "desc": "深圳湾公园举办免费音乐节，社交机会大增", "effect": "social_boost"},
    {"name": "神秘包裹", "desc": "一个神秘包裹出现在随机地点", "effect": "mystery_item"},
]

# ============================================================
# 世界状态
# ============================================================
world = {
    "time": {
        "real_start": 0,
        "virtual_datetime": "2026-02-13 06:00",
        "virtual_hour": 6,
        "virtual_day": 1,
        "tick": 0,
    },
    "bots": {},
    "locations": {},
    "events": [],
    "active_effects": [],
    "message_board": [],
    "gallery": [],  # 照片墙
}

SNAPSHOT_PATH = "/home/ubuntu/world_state_snapshot.json"

# ============================================================
# 初始化
# ============================================================
def init_world():
    world["time"]["real_start"] = time.time()

    # 初始化地点
    for name, info in LOCATIONS.items():
        world["locations"][name] = {
            "type": info["type"], "desc": info["desc"], "rent": info["rent"],
            "bots": [], "npcs": [], "items": [], "jobs": JOBS.get(name, []),
        }

    world["locations"]["南山科技园"]["npcs"].append({"id": "hr_zhang", "name": "张总(HR)", "desc": "腾讯的HR总监，精明务实"})
    world["locations"]["宝安城中村"]["npcs"].append({"id": "landlady_wang", "name": "王姐(房东)", "desc": "城中村包租婆，热情但市侩"})
    world["locations"]["华强北"]["npcs"].append({"id": "boss_chen", "name": "陈老板", "desc": "华强北电子档口老板，经验丰富"})
    world["locations"]["东门老街"]["npcs"].append({"id": "chef_liu", "name": "刘师傅", "desc": "东门老街小餐馆厨师，手艺好"})
    world["locations"]["福田CBD"]["npcs"].append({"id": "investor_li", "name": "李总(投资人)", "desc": "知名天使投资人，眼光独到"})

    # 尝试从快照恢复
    if os.path.exists(SNAPSHOT_PATH):
        try:
            with open(SNAPSHOT_PATH, 'r') as f:
                snapshot = json.load(f)
            log.info("=== 从快照恢复世界状态 ===")

            if 'time' in snapshot:
                for k in ['virtual_datetime', 'virtual_hour', 'virtual_day', 'tick']:
                    if k in snapshot['time']:
                        world['time'][k] = snapshot['time'][k]

            for bid, bdata in snapshot.get('bots', {}).items():
                world['bots'][bid] = {
                    'status': bdata.get('status', 'alive'),
                    'hp': bdata.get('hp', 100),
                    'money': bdata.get('money', 500),
                    'energy': bdata.get('energy', 100),
                    'satiety': bdata.get('satiety', 80),
                    'location': bdata.get('location', '宝安城中村'),
                    'home': bdata.get('home', '宝安城中村'),
                    'job': bdata.get('job', None),
                    'is_sleeping': bdata.get('is_sleeping', False),
                    'skills': bdata.get('skills', {'programming': 10, 'social': 10, 'hardware': 10, 'analysis': 10, 'art': 10}),
                    'inventory': bdata.get('inventory', []),
                    'relationships': bdata.get('relationships', {}),
                    'action_log': bdata.get('action_log', [])[-20:],
                    # v7新增字段
                    'values': bdata.get('values', {}),
                    'core_memories': bdata.get('core_memories', []),
                    'emotional_bonds': bdata.get('emotional_bonds', {}),
                    'selfie_count': bdata.get('selfie_count', 0),
                    'family': bdata.get('family', {}) or FAMILY_RELATIONS.get(bid, {}),
                    # v7.1 工作系统
                    'current_task': bdata.get('current_task', None),
                    # v7.2 欲望系统
                    'desires': bdata.get('desires') or {
                        k: BOT_DESIRE_PROFILES.get(bid, DEFAULT_DESIRE_PROFILE).get(k, 20)
                        for k in ['lust', 'power', 'greed', 'vanity', 'security']
                    },
                }
                loc = bdata.get('location', '宝安城中村')
                if loc in world['locations'] and bid not in world['locations'][loc]['bots']:
                    world['locations'][loc]['bots'].append(bid)

            world['events'] = snapshot.get('events', [])
            world['message_board'] = snapshot.get('message_board', [])
            world['gallery'] = snapshot.get('gallery', [])

            bot_count = len(world['bots'])
            tick = world['time']['tick']
            vdt = world['time']['virtual_datetime']
            log.info(f'快照恢复成功! {bot_count}个Bot, tick={tick}, 虚拟时间={vdt}')

            os.rename(SNAPSHOT_PATH, SNAPSHOT_PATH + '.used')
            return
        except Exception as e:
            log.error(f'快照恢复失败: {e}, 将从头初始化')

    # 全新初始化
    start_locations = {
        "bot_1": "宝安城中村", "bot_2": "南山公寓", "bot_3": "宝安城中村",
        "bot_4": "宝安城中村", "bot_5": "华强北", "bot_6": "南山公寓",
        "bot_7": "华强北", "bot_8": "宝安城中村", "bot_9": "东门老街",
        "bot_10": "华强北",
    }
    for i in range(1, 11):
        bid = f"bot_{i}"
        create_bot(bid, start_locations[bid])

    log.info("=== 深圳生存模拟世界 v7 初始化完成 ===")
    log.info(f'10个Bot已就位，虚拟时间从 {world["time"]["virtual_datetime"]} 开始')


def create_bot(bot_id, location):
    with lock:
        if bot_id in world["bots"]:
            return
        world["bots"][bot_id] = {
            "status": "alive",
            "hp": 100,
            "money": 500,
            "energy": 100,
            "satiety": 80,
            "location": location,
            "home": location if LOCATIONS.get(location, {}).get("type") == "residential" else "宝安城中村",
            "job": None,
            "is_sleeping": False,
            "skills": {"programming": 10, "social": 10, "hardware": 10, "analysis": 10, "art": 10},
            "inventory": [],
            "relationships": {},
            "action_log": [],
            # v7新增
            "values": {},           # 动态价值观，由Bot Agent维护
            "core_memories": [],    # 重要记忆，永不丢失
            "emotional_bonds": {},  # 情感关系 {bot_id: {trust: 0-100, hostility: 0-100, closeness: 0-100, label: "朋友/敌人/..."}}
            "selfie_count": 0,
            "family": FAMILY_RELATIONS.get(bot_id, {}),
            # v7.1 工作系统
            'current_task': None,  # {job_title, task_name, task_desc, duration, progress, difficulty, challenge, started_tick}
            # v7.2 欲望系统
            'desires': {
                k: BOT_DESIRE_PROFILES.get(bot_id, DEFAULT_DESIRE_PROFILE).get(k, 20)
                for k in ['lust', 'power', 'greed', 'vanity', 'security']
            },
        }
        if location in world["locations"]:
            world["locations"][location]["bots"].append(bot_id)
        log.info(f"新Bot {bot_id} 在 {location} 创建成功")
        # 启动Bot进程
        try:
            subprocess.Popen(
                ["python3", "/home/ubuntu/bot_agent_v7.py"],
                env=dict(os.environ, BOT_ID=bot_id)
            )
            log.info(f"Bot {bot_id} 进程已启动")
        except Exception as e:
            log.error(f"启动Bot {bot_id} 进程失败: {e}")


# ============================================================
# 世界 Tick
# ============================================================
def world_tick():
    with lock:
        t = world["time"]
        t["tick"] += 1
        t["virtual_hour"] = (6 + t["tick"]) % 24
        t["virtual_day"] = 1 + t["tick"] // 24
        vd = t['virtual_day']; vh = t['virtual_hour']
        t['virtual_datetime'] = f'第{vd}天 {vh:02d}:00'

        log.info(f'===== TICK {t["tick"]} | {t["virtual_datetime"]} =====')

        alive_count = 0
        for bid, bot in world["bots"].items():
            if bot["status"] != "alive":
                continue
            alive_count += 1

            h = t["virtual_hour"]

            # === 睡眠系统 ===
            if bot.get("is_sleeping", False):
                # 睡觉时：能量快速恢复，HP不衰减，饱腹度缓慢衰减
                bot["energy"] = min(100, bot["energy"] + ENERGY_SLEEP_RECOVER)
                bot["satiety"] = max(0, bot["satiety"] - 1)  # 睡觉时饱腹度衰减慢
                # 自动起床：到了7点且能量>80
                if 7 <= h < 23 and bot["energy"] >= 80:
                    bot["is_sleeping"] = False
                    log.info(f"{bid} 自然醒了 (能量={bot['energy']})")
                continue  # 睡觉时跳过其他处理

            # === 正常状态 ===
            bot["hp"] = max(0, bot["hp"] - HP_DECAY_PER_TICK)
            bot["satiety"] = max(0, bot["satiety"] - SATIETY_DECAY)

            # 能量：夜晚在家恢复，白天消耗
            if h >= 22 or h < 6:
                bot["energy"] = min(100, bot["energy"] + ENERGY_NIGHT_RECOVER)
            else:
                bot["energy"] = max(0, bot["energy"] - ENERGY_DAY_COST)

            # 饥饿惩罚
            if bot["satiety"] <= 0:
                bot["hp"] = max(0, bot["hp"] - 1)
                log.warning(f"{bid} 饥饿中，额外扣除1HP！")

            # === 欲望自然增长 ===
            desires = bot.get("desires", {})
            profile = BOT_DESIRE_PROFILES.get(bid, DEFAULT_DESIRE_PROFILE)
            for d_key, base_growth in DESIRE_GROWTH_PER_TICK.items():
                mult = profile.get(f"{d_key}_mult", 1.0)
                # 困境会加速某些欲望
                if d_key == "security" and (bot["hp"] < 30 or bot["money"] < 50):
                    mult *= 1.5
                if d_key == "greed" and bot["money"] < 100:
                    mult *= 1.3
                if d_key == "lust" and bot["energy"] > 60 and bot["satiety"] > 30:
                    mult *= 1.2  # 吃饱了有精力才想这些
                if d_key == "lust":
                    # 夜晚性欲增长更快
                    vh = world["time"]["virtual_hour"]
                    if vh >= 22 or vh <= 5:
                        mult *= 1.5
                    # 附近有异性时性欲增长更快
                    loc = bot["location"]
                    loc_bots = world["locations"].get(loc, {}).get("bots", [])
                    gender = bot.get("gender", "")
                    for ob in loc_bots:
                        other = world["bots"].get(ob, {})
                        if other.get("gender") and other.get("gender") != gender and other.get("status") == "alive":
                            mult *= 1.3
                            break
                desires[d_key] = min(100, desires.get(d_key, 20) + base_growth * mult)
            bot["desires"] = desires

            # 死亡检测
            if bot["hp"] <= 0:
                bot["status"] = "dead"
                log.error(f"!!! {bid} 已死亡 !!! HP归零")
                loc = bot["location"]
                if bid in world["locations"].get(loc, {}).get("bots", []):
                    world["locations"][loc]["bots"].remove(bid)

            # === 工作进度推进 ===
            task = bot.get("current_task")
            if task and task.get("status") == "in_progress":
                task["progress"] = task.get("progress", 0) + 1
                # 随机难点（每个tick 20%概率触发，且还没触发过）
                if not task.get("challenge") and random.random() < 0.2:
                    job_title = task.get("job_title", "")
                    loc = bot["location"]
                    job_def = None
                    for j in JOBS.get(loc, []):
                        if j["title"] == job_title:
                            job_def = j
                            break
                    if job_def and job_def.get("challenges"):
                        challenge = random.choice(job_def["challenges"])
                        task["challenge"] = challenge
                        task["duration"] = task["duration"] + 1  # 难点延长工期
                        log.warning(f"{bid} 工作遇到难点: {challenge} (工期+1)")
                
                # 完成判断
                if task["progress"] >= task["duration"]:
                    # 成功率基于技能和难度
                    skill_key = task.get("skill", "none")
                    skill_val = bot["skills"].get(skill_key, 0) if skill_key != "none" else 10
                    difficulty = task.get("difficulty", 0.3)
                    # 成功率: 技能越高越容易成功
                    success_rate = min(0.95, 0.5 + skill_val * 0.01 - difficulty * 0.3)
                    success = random.random() < success_rate
                    
                    base_pay = task.get("base_pay", 50)
                    had_challenge = task.get("challenge") is not None
                    
                    if success:
                        # 成功：全额发薪 + 有难点奖励
                        bonus = random.randint(10, 30) if had_challenge else 0
                        pay = base_pay + bonus
                        bot["money"] += pay
                        if skill_key != "none" and skill_key in bot["skills"]:
                            bot["skills"][skill_key] = min(100, bot["skills"][skill_key] + random.randint(2, 4))
                        task["status"] = "completed"
                        task["result"] = f"成功完成! 赚了{pay}元" + (f"(含难点奖励{bonus}元)" if bonus else "")
                        log.info(f"{bid} 完成任务[{task['task_name']}]: 赚{pay}元")
                    else:
                        # 失败：只发部分薪资
                        pay = max(10, base_pay // 3)
                        bot["money"] += pay
                        if skill_key != "none" and skill_key in bot["skills"]:
                            bot["skills"][skill_key] = min(100, bot["skills"][skill_key] + 1)
                        task["status"] = "failed"
                        task["result"] = f"任务失败了...只拿到{pay}元辛苦费"
                        log.warning(f"{bid} 任务失败[{task['task_name']}]: 只拿到{pay}元")
                else:
                    remaining = task["duration"] - task["progress"]
                    log.info(f"{bid} 工作中[{task['task_name']}]: 进度 {task['progress']}/{task['duration']} 剩余{remaining}tick")

            # 自动入睡：23:00-07:00 且能量<30 且在住所
            if (h >= 23 or h < 7) and bot["energy"] < 30 and bot["location"] == bot["home"]:
                bot["is_sleeping"] = True
                log.info(f"{bid} 太累了，在{bot['home']}睡着了")

        # 每日HP分配
        if t["virtual_hour"] == 6 and t["tick"] > 1:
            distribute_hp(alive_count)

        # 随机事件
        if random.random() < 0.08:
            trigger_event()

        log.info(f'存活Bot数: {alive_count}/{len(world["bots"])}')


def distribute_hp(alive_count):
    hp_pool = max(0, alive_count - 1)
    if hp_pool <= 0:
        return
    alive_bots = [bid for bid, b in world["bots"].items() if b["status"] == "alive"]
    recipients = random.sample(alive_bots, min(hp_pool, len(alive_bots)))
    for bid in recipients:
        world["bots"][bid]["hp"] = min(100, world["bots"][bid]["hp"] + 1)
        log.info(f'每日HP发放: {bid} +1 HP (当前: {world["bots"][bid]["hp"]})')


def trigger_event():
    event = random.choice(RANDOM_EVENTS)
    world["events"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "event": event["name"],
        "desc": event["desc"]
    })
    world["active_effects"].append({
        "effect": event["effect"],
        "expires_tick": world["time"]["tick"] + 2
    })
    log.warning(f'!!! 随机事件: {event["name"]} - {event["desc"]}')


# ============================================================
# 动作解释与执行
# ============================================================
def process_action(bot_id, plan):
    bot = world["bots"][bot_id]
    loc = bot["location"]
    loc_info = world["locations"][loc]

    context = f"""当前地点: {loc} ({LOCATIONS[loc]["desc"]})
地点内的Bot: {loc_info["bots"]}
地点内的NPC: {[n["name"] for n in loc_info["npcs"]]}
地点可用工作: {[j["title"] for j in loc_info.get("jobs", [])]}
地点物品: {loc_info["items"]}
所有地点: {list(LOCATIONS.keys())}
Bot状态: HP={bot["hp"]}, 钱={bot["money"]}, 能量={bot["energy"]}, 饱腹度={bot["satiety"]}
Bot技能: {bot["skills"]}
Bot欲望: {json.dumps(bot.get('desires', {}), ensure_ascii=False)}
当前时间: {world["time"]["virtual_datetime"]}
是否在睡觉: {bot.get("is_sleeping", False)}
当前工作任务: {json.dumps(bot.get('current_task'), ensure_ascii=False) if bot.get('current_task') else '无'}"""

    prompt = f"""你是深圳生存模拟的世界解释器。将Bot的自然语言计划转为一个JSON动作。

重要规则(必须严格遵守):
- 如果计划包含"吃""饭""食物""填饱""买吃的""补充饱腹"等吃东西的意图，必须解析为eat动作，不要解析为move！吃东西不需要移动，在当前地点就能吃。food字段填"城中村快餐"(5元)、"便利店饭团"(8元)、"路边摊炒粉"(12元)等
- 如果计划包含"工作""干活""赚钱""找工作""上班"等工作意图，必须解析为work动作，不要解析为move！工作不需要移动，在当前地点就能做。job字段从"地点可用工作"中选择
- 如果计划包含"亲密""发展关系""约会""在一起"等亲密意图，解析为intimate动作
- move动作的to字段只能填"所有地点"列表中的地点名，不要填"小卖部""餐馆""小摊"等不存在的地点
- 如果Bot已经在目标地点，不要生成move，而是解析为实际意图(work/eat/explore等)

可用动作(只能选一个):
1. {{"action":"move","to":"地点名"}} (只能移动到"所有地点"列表中的地点!)
2. {{"action":"work","job":"工作名"}}
3. {{"action":"eat","food":"食物名"}} (在当前地点直接吃，不需要移动)
4. {{"action":"talk","target":"bot_X或npc_id","message":"说的话"}}
5. {{"action":"rest"}}
6. {{"action":"explore"}}
7. {{"action":"trade","target":"bot_X","give_type":"money/hp","give_amount":数字,"want_type":"money/hp","want_amount":数字}}
8. {{"action":"post","content":"内容"}}
9. {{"action":"sleep"}}
10. {{"action":"wake_up"}}
11. {{"action":"selfie","prompt":"英文描述想拍的照片内容"}}
12. {{"action":"sell_body","want":"money或food"}} (出卖身体换取金钱或食物)
13. {{"action":"seek_pleasure"}} (花钱寻欢作乐，满足欲望)
14. {{"action":"intimate","target":"bot_X"}} (与附近的人发展亲密关系，降低双方性欲，提升亲密度)
15. {{"action":"idle"}}

{context}

Bot的计划: "{plan}"

只输出一个JSON对象，不要其他文字:"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        action = json.loads(raw)
    except Exception as e:
        log.error(f"解析 {bot_id} 动作失败: {e}")
        action = {"action": "idle"}

    result = execute(bot_id, action)
    bot["action_log"].append({
        "tick": world["time"]["tick"],
        "time": world["time"]["virtual_datetime"],
        "plan": plan,
        "action": action,
        "result": result
    })
    # 保持action_log不要太长
    if len(bot["action_log"]) > 50:
        bot["action_log"] = bot["action_log"][-30:]

    return {"action": action, "result": result}


def execute(bot_id, action):
    bot = world["bots"][bot_id]
    act = action.get("action", "idle")

    if act == "move":
        dest = action.get("to", "")
        if dest in LOCATIONS and dest != bot["location"]:
            old_loc = bot["location"]
            if bot_id in world["locations"][old_loc]["bots"]:
                world["locations"][old_loc]["bots"].remove(bot_id)
            bot["location"] = dest
            world["locations"][dest]["bots"].append(bot_id)
            bot["energy"] = max(0, bot["energy"] - 5)
            msg = f"从 {old_loc} 移动到 {dest}"
            log.info(f"{bot_id}: {msg}")
            return msg
        return f"无法移动到 {dest}"

    elif act == "work":
        # 检查是否已有进行中的任务
        task = bot.get("current_task")
        if task and task.get("status") == "in_progress":
            remaining = task["duration"] - task.get("progress", 0)
            challenge_text = f" [难点: {task['challenge']}]" if task.get("challenge") else ""
            bot["energy"] = max(0, bot["energy"] - 8)
            msg = f'继续做[{task["task_name"]}]: {task["task_desc"]} | 进度{task.get("progress",0)}/{task["duration"]}{challenge_text}'
            log.info(f"{bot_id}: {msg}")
            return msg
        
        # 检查是否有已完成/失败的任务结果
        if task and task.get("status") in ["completed", "failed"]:
            result_msg = task.get("result", "")
            bot["current_task"] = None  # 清除已完成的任务
            # 不返回，继续往下分配新任务
        
        # 分配新任务
        job_title = action.get("job", "")
        loc = bot["location"]
        available = JOBS.get(loc, [])
        job = next((j for j in available if j["title"] == job_title), None)
        if not job:
            job = next((j for j in available if job_title in j["title"] or j["title"] in job_title), None)
        if not job and available:
            job = available[0]
        if job:
            skill_key = job["skill"]
            skill_val = bot["skills"].get(skill_key, 0) if skill_key != "none" else 10
            if skill_val >= job["min_skill"]:
                # 随机分配一个具体任务
                task_template = random.choice(job.get("tasks", [{"name": "工作", "duration": 2, "difficulty": 0.2, "desc": "日常工作"}]))
                new_task = {
                    "job_title": job["title"],
                    "task_name": task_template["name"],
                    "task_desc": task_template["desc"],
                    "duration": task_template["duration"],
                    "difficulty": task_template["difficulty"],
                    "skill": skill_key,
                    "base_pay": job["pay"] + random.randint(-10, 10),
                    "progress": 0,
                    "status": "in_progress",
                    "challenge": None,
                    "result": None,
                    "started_tick": world["time"]["tick"],
                }
                bot["current_task"] = new_task
                bot["energy"] = max(0, bot["energy"] - 8)
                bot["job"] = job["title"]
                msg = f'开始任务[{task_template["name"]}]: {task_template["desc"]} | 预计需要{task_template["duration"]}个小时 | 难度: {"⭐"*max(1,int(task_template["difficulty"]*5))}'
                log.info(f"{bot_id}: {msg}")
                return msg
            return f'技能不足，无法胜任 {job["title"]}'
        return f"{loc} 没有可用工作"

    elif act == "eat":
        food_name = action.get("food", "")
        food = FOOD_MENU.get(food_name)
        if not food:
            food_name = next((k for k in FOOD_MENU if food_name in k or k in food_name), None)
            food = FOOD_MENU.get(food_name) if food_name else None
        if not food:
            food_name = "城中村快餐"
            food = FOOD_MENU[food_name]
        if bot["money"] >= food["cost"]:
            bot["money"] -= food["cost"]
            bot["satiety"] = min(100, bot["satiety"] + food["satiety"])
            msg = f'吃了{food_name}，花费{food["cost"]}元，饱腹度+{food["satiety"]}'
            log.info(f"{bot_id}: {msg}")
            return msg
        return f"钱不够买{food_name}"

    elif act == "talk":
        target = action.get("target", "")
        message = action.get("message", "你好")
        world["message_board"].append({
            "tick": world["time"]["tick"],
            "from": bot_id,
            "to": target,
            "msg": message,
            "priority": "normal"
        })
        if target.startswith("bot_"):
            # 更新数值关系
            bot["relationships"][target] = bot["relationships"].get(target, 0) + 1
            if target in world["bots"] and world["bots"][target]["status"] == "alive":
                world["bots"][target]["relationships"][bot_id] = world["bots"][target]["relationships"].get(bot_id, 0) + 1
        bot["skills"]["social"] = min(100, bot["skills"]["social"] + 1)
        msg = f"对{target}说: {message}"
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "rest":
        recover = random.randint(10, 20)
        bot["energy"] = min(100, bot["energy"] + recover)
        msg = f"休息了一会，能量恢复{recover}"
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "explore":
        loc = bot["location"]
        if random.random() < 0.3:
            finds = ["一张优惠券", "一本旧书", "一个充电宝", "50元现金", "一张名片"]
            found = random.choice(finds)
            if found == "50元现金":
                bot["money"] += 50
            else:
                bot["inventory"].append(found)
            msg = f"在{loc}探索，发现了{found}！"
        else:
            msg = f"在{loc}四处逛了逛，熟悉了环境"
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "trade":
        target = action.get("target", "")
        give_type = action.get("give_type", "money")
        give_amt = int(action.get("give_amount", 0))
        want_type = action.get("want_type", "money")
        want_amt = int(action.get("want_amount", 0))
        if target in world["bots"] and world["bots"][target]["status"] == "alive":
            if give_type == "money" and bot["money"] >= give_amt:
                bot["money"] -= give_amt
                world["bots"][target]["money"] += give_amt
                if want_type == "hp" and world["bots"][target]["hp"] >= want_amt:
                    world["bots"][target]["hp"] -= want_amt
                    bot["hp"] = min(100, bot["hp"] + want_amt)
                msg = f"与{target}交易: 给出{give_amt}{give_type}, 获得{want_amt}{want_type}"
                log.info(f"{bot_id}: {msg}")
                return msg
            elif give_type == "hp" and bot["hp"] >= give_amt:
                bot["hp"] -= give_amt
                world["bots"][target]["hp"] = min(100, world["bots"][target]["hp"] + give_amt)
                if want_type == "money" and world["bots"][target]["money"] >= want_amt:
                    world["bots"][target]["money"] -= want_amt
                    bot["money"] += want_amt
                msg = f"与{target}交易: 给出{give_amt}HP, 获得{want_amt}元"
                log.info(f"{bot_id}: {msg}")
                return msg
        return "交易失败"

    elif act == "post":
        content = action.get("content", "")
        world["message_board"].append({
            "tick": world["time"]["tick"],
            "from": bot_id,
            "to": "public",
            "msg": content,
            "priority": "normal"
        })
        msg = f"在消息板发帖: {content}"
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "sleep":
        bot["is_sleeping"] = True
        msg = "躺下睡觉了，能量开始恢复..."
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "wake_up":
        bot["is_sleeping"] = False
        msg = "醒了！新的一天开始了"
        log.info(f"{bot_id}: {msg}")
        return msg

    elif act == "sell_body":
        # 出卖身体换取金钱/食物
        desires = bot.get("desires", {})
        want = action.get("want", "money")  # money 或 food
        # 收入取决于地点和外貌(vanity代替)
        vanity = desires.get("vanity", 20)
        base_pay = random.randint(50, 150)
        pay = int(base_pay * (0.5 + vanity / 200))  # 外貌影响价格
        # 代价: 扣HP、扣能量、心理创伤
        hp_cost = random.randint(3, 8)
        energy_cost = random.randint(15, 30)
        bot["hp"] = max(0, bot["hp"] - hp_cost)
        bot["energy"] = max(0, bot["energy"] - energy_cost)
        if want == "food":
            bot["satiety"] = min(100, bot["satiety"] + 60)
            msg = f"为了填饱肚子，出卖了自己的身体。得到了一顿饱饭。(HP-{hp_cost}, 能量-{energy_cost})"
        else:
            bot["money"] += pay
            msg = f"为了生存，出卖了自己的身体。获得{pay}元。(HP-{hp_cost}, 能量-{energy_cost})"
        # 欲望变化: 性欲降低，安全感需求升高
        desires["lust"] = max(0, desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL)
        desires["security"] = min(100, desires.get("security", 50) + 15)  # 不安全感加剧
        bot["desires"] = desires
        log.warning(f"{bot_id}: {msg}")
        return msg

    elif act == "seek_pleasure":
        # 寻求性服务(花钱满足欲望)
        desires = bot.get("desires", {})
        cost = random.randint(100, 300)
        if bot["money"] < cost:
            msg = f"想寻欢作乐，但钱不够(需要{cost}元，只有{bot['money']}元)"
            log.info(f"{bot_id}: {msg}")
            return msg
        bot["money"] -= cost
        bot["energy"] = max(0, bot["energy"] - 20)
        # 欲望变化: 性欲大幅降低
        desires["lust"] = max(0, desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL)
        desires["vanity"] = min(100, desires.get("vanity", 20) + 5)  # 微微满足虚荣
        bot["desires"] = desires
        msg = f"花了{cost}元寻欢作乐。欲望得到了暂时的满足。(能量-20)"
        log.warning(f"{bot_id}: {msg}")
        return msg

    elif act == "intimate":
        # 与附近的人发展亲密关系
        target_id = action.get("target", "")
        desires = bot.get("desires", {})
        loc = bot["location"]
        loc_bots = world["locations"][loc]["bots"]
        
        # 检查目标是否在同一地点
        if target_id not in loc_bots or target_id == bot_id:
            msg = "想找人发展亲密关系，但附近没有合适的对象"
            log.info(f"{bot_id}: {msg}")
            return msg
        
        target = world["bots"].get(target_id)
        if not target or target.get("status") == "dead" or target.get("is_sleeping"):
            msg = "对方不在或无法回应"
            log.info(f"{bot_id}: {msg}")
            return msg
        
        # 双方效果
        # 发起方
        desires["lust"] = max(0, desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL)
        bot["energy"] = max(0, bot["energy"] - 10)
        bot["desires"] = desires
        
        # 接受方也降低性欲
        t_desires = target.get("desires", {})
        t_desires["lust"] = max(0, t_desires.get("lust", 50) - DESIRE_DECAY_ON_FULFILL * 0.7)
        target["desires"] = t_desires
        
        # 双方亲密度提升
        bot_rels = bot.get("relationships", {})
        t_rels = target.get("relationships", {})
        
        if target_id not in bot_rels:
            bot_rels[target_id] = {"trust": 0, "intimacy": 0, "hostility": 0}
        bot_rels[target_id]["intimacy"] = min(100, bot_rels[target_id].get("intimacy", 0) + 25)
        bot_rels[target_id]["trust"] = min(100, bot_rels[target_id].get("trust", 0) + 10)
        bot["relationships"] = bot_rels
        
        if bot_id not in t_rels:
            t_rels[bot_id] = {"trust": 0, "intimacy": 0, "hostility": 0}
        t_rels[bot_id]["intimacy"] = min(100, t_rels[bot_id].get("intimacy", 0) + 20)
        t_rels[bot_id]["trust"] = min(100, t_rels[bot_id].get("trust", 0) + 8)
        target["relationships"] = t_rels
        
        target_name = target.get("name", target_id)
        bot_name = bot.get("name", bot_id)
        msg = f"和{target_name}发展了亲密关系。双方感情升温，欲望得到释放。(能量-10)"
        log.warning(f"{bot_id}: {msg}")
        
        # 给对方也记录一条
        target["action_log"].append({
            "tick": world["time"]["tick"],
            "action": f"{bot_name}与你发展了亲密关系",
            "result": "感情升温，欲望释放"
        })
        return msg

    elif act == "selfie":
        selfie_prompt = action.get("prompt", "")
        if not selfie_prompt:
            selfie_prompt = f"A person taking a selfie at {bot['location']} in Shenzhen, China"
        # 异步生成图片（不阻塞）
        bot["selfie_count"] = bot.get("selfie_count", 0) + 1
        tick = world["time"]["tick"]
        filename = f"{bot_id}_day{world['time']['virtual_day']}_{tick}.jpg"
        save_path = f"/home/ubuntu/selfies/{filename}"

        def _gen():
            result = grok_generate(selfie_prompt, save_path)
            if result["success"]:
                with lock:
                    world["gallery"].append({
                        "bot_id": bot_id,
                        "filename": filename,
                        "prompt": selfie_prompt,
                        "time": world["time"]["virtual_datetime"],
                        "tick": tick,
                        "url": f"/selfies/{filename}"
                    })
                log.info(f"{bot_id} 拍照成功: {filename}")
            else:
                log.error(f"{bot_id} 拍照失败: {result.get('error')}")

        Thread(target=_gen, daemon=True).start()
        msg = f"📸 正在拍照: {selfie_prompt[:60]}..."
        log.info(f"{bot_id}: {msg}")
        return msg

    else:
        msg = "静静地待着，观察周围"
        log.info(f"{bot_id}: {msg}")
        return msg


# ============================================================
# API 端点
# ============================================================
@app.get("/world")
def get_world():
    with lock:
        safe = {
            "time": world["time"],
            "bots": {},
            "locations": {},
            "events": world["events"][-10:],
            "active_effects": [e for e in world["active_effects"] if e["expires_tick"] > world["time"]["tick"]],
            "message_board": world["message_board"][-30:],
            "gallery": world["gallery"][-20:],
        }
        for bid, b in world["bots"].items():
            safe["bots"][bid] = {
                "status": b["status"],
                "hp": b["hp"],
                "money": b["money"],
                "energy": b["energy"],
                "satiety": b["satiety"],
                "location": b["location"],
                "home": b["home"],
                "job": b["job"],
                "is_sleeping": b.get("is_sleeping", False),
                "skills": b["skills"],
                "inventory": b["inventory"],
                "relationships": b["relationships"],
                "family": b.get("family", {}),
                "current_task": b.get("current_task"),
                "desires": b.get("desires", {}),
            }
        for lname, ldata in world["locations"].items():
            safe["locations"][lname] = {
                "type": ldata["type"], "desc": ldata["desc"],
                "bots": ldata["bots"],
                "npcs": [n["name"] for n in ldata["npcs"]],
                "items": ldata["items"],
                "jobs": [j["title"] for j in ldata.get("jobs", [])],
            }
        return JSONResponse(content=safe)


@app.get("/bot/{bot_id}/detail")
def get_bot_detail(bot_id: str):
    """Bot详情API - 返回完整信息包括价值观、核心记忆、情感关系"""
    with lock:
        if bot_id not in world["bots"]:
            return JSONResponse(content={"error": "Bot不存在"}, status_code=404)
        b = world["bots"][bot_id]
        detail = {
            "status": b["status"],
            "hp": b["hp"],
            "money": b["money"],
            "energy": b["energy"],
            "satiety": b["satiety"],
            "location": b["location"],
            "home": b["home"],
            "job": b["job"],
            "is_sleeping": b.get("is_sleeping", False),
            "skills": b["skills"],
            "inventory": b["inventory"],
            "relationships": b["relationships"],
            "family": b.get("family", {}),
            # v7 深层数据
            "values": b.get("values", {}),
            "core_memories": b.get("core_memories", [])[-10:],
            "emotional_bonds": b.get("emotional_bonds", {}),
            "selfie_count": b.get("selfie_count", 0),
            "action_log": b.get("action_log", [])[-10:],
            "current_task": b.get("current_task"),
            "desires": b.get("desires", {}),
        }
        return JSONResponse(content=detail)


@app.post("/bot/{bot_id}/action")
async def bot_action(bot_id: str, request: Request):
    with lock:
        if bot_id not in world["bots"]:
            return JSONResponse(content={"error": "Bot不存在"}, status_code=404)
        if world["bots"][bot_id]["status"] == "dead":
            return JSONResponse(content={"error": f"{bot_id}已死亡"}, status_code=400)
    data = await request.json()
    plan = data.get("plan", "idle")
    with lock:
        result = process_action(bot_id, plan)
    return JSONResponse(content=result)


@app.post("/bot/{bot_id}/update_inner")
async def update_inner_state(bot_id: str, request: Request):
    """Bot Agent调用此API更新价值观、核心记忆、情感关系"""
    data = await request.json()
    with lock:
        if bot_id not in world["bots"]:
            return JSONResponse(content={"error": "Bot不存在"}, status_code=404)
        bot = world["bots"][bot_id]

        # 更新价值观
        if "values" in data:
            bot["values"] = data["values"]

        # 添加核心记忆
        if "new_core_memory" in data:
            mem = data["new_core_memory"]
            bot["core_memories"].append(mem)
            if len(bot["core_memories"]) > 20:
                bot["core_memories"] = bot["core_memories"][-20:]
            log.info(f"{bot_id} 新核心记忆: {mem.get('summary', '')[:60]}")

        # 更新情感关系
        if "emotional_bonds" in data:
            for target, bond in data["emotional_bonds"].items():
                if target not in bot["emotional_bonds"]:
                    bot["emotional_bonds"][target] = {"trust": 50, "hostility": 0, "closeness": 0, "label": "陌生人"}
                bot["emotional_bonds"][target].update(bond)

    return JSONResponse(content={"status": "ok"})


@app.get("/messages/{bot_id}")
def get_messages(bot_id: str):
    with lock:
        msgs = [m for m in world["message_board"] if m["to"] == bot_id or m["to"] == "public"]
        # 按优先级排序：high > normal > low
        priority_order = {"high": 0, "normal": 1, "low": 2}
        msgs.sort(key=lambda m: (priority_order.get(m.get("priority", "normal"), 1), -m.get("tick", 0)))
        return JSONResponse(content={"messages": msgs[-20:]})


@app.post("/admin/add_bot")
async def add_bot(request: Request):
    data = await request.json()
    bot_id = data.get("bot_id")
    location = data.get("location", "宝安城中村")
    if not bot_id:
        return JSONResponse(content={"error": "需要bot_id"}, status_code=400)
    create_bot(bot_id, location)
    return JSONResponse(content={"message": f"Bot {bot_id} 已创建并启动"})


@app.post("/admin/send_message")
async def send_message(request: Request):
    data = await request.json()
    target_id = data.get("target_id")
    message = data.get("message")
    sender_alias = data.get("sender_alias", "一个神秘的声音")
    priority = data.get("priority", "normal")

    # 父母身份自动设为高优先级
    if sender_alias in ["父亲", "母亲", "爸爸", "妈妈", "爸", "妈", "父母"]:
        priority = "high"

    if not target_id or not message:
        return JSONResponse(content={"error": "需要target_id和message"}, status_code=400)
    with lock:
        world["message_board"].append({
            "tick": world["time"]["tick"],
            "from": sender_alias,
            "to": target_id,
            "msg": message,
            "priority": priority
        })
    log.info(f"[上帝视角] 对 {target_id} 说: {message} (来自: {sender_alias}, 优先级: {priority})")
    return JSONResponse(content={"message": "消息已发送"})


@app.post("/admin/save_snapshot")
async def save_snapshot():
    """手动保存快照"""
    with lock:
        snapshot = {
            "time": world["time"],
            "bots": world["bots"],
            "events": world["events"][-50:],
            "message_board": world["message_board"][-100:],
            "gallery": world["gallery"],
        }
        with open(SNAPSHOT_PATH, 'w') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)
    log.info("快照已保存")
    return JSONResponse(content={"message": "快照已保存"})


# 静态文件：selfies
@app.get("/selfies/{filename}")
def get_selfie(filename: str):
    path = f"/home/ubuntu/selfies/{filename}"
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(content={"error": "图片不存在"}, status_code=404)


# 静态文件：头像
@app.get("/avatars/{filename}")
def get_avatar(filename: str):
    # 优先查找真人头像
    path_v2 = f"/home/ubuntu/bot_avatars_v2/{filename}"
    if os.path.exists(path_v2):
        return FileResponse(path_v2)
    # 回退到旧头像
    path_v1 = f"/home/ubuntu/bot_avatars/{filename}"
    if os.path.exists(path_v1):
        return FileResponse(path_v1)
    return JSONResponse(content={"error": "头像不存在"}, status_code=404)


@app.get("/gallery")
def get_gallery():
    """获取照片墙"""
    with lock:
        return JSONResponse(content={"gallery": world["gallery"][-50:]})


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    init_world()
    scheduler.add_job(world_tick, "interval", seconds=TICK_SECONDS, id="tick")
    scheduler.start()
    log.info(f"世界引擎 v7 启动! 每{TICK_SECONDS}秒一个虚拟小时")
    log.info(f"现实30分钟 = 虚拟1天 (24 ticks)")
    log.info(f"新功能: 睡眠系统, Selfie(Grok), 消息优先级, 价值观演化, 深层记忆, 情感关系")
    uvicorn.run(app, host="0.0.0.0", port=8000)
