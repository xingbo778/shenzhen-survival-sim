# ============================================================
# 常量与配置
# ============================================================

# --- 寿命系统 (HP→不可逆寿命) ---
AGING_BASE = 0.5               # 每tick基础衰老 (100寿命 / 0.5 = 200tick ≈ 加速模式约50分钟)
AGING_HUNGER_MULT = 5.0        # 饥饿时衰老加速倍率
AGING_OVERWORK_MULT = 3.0      # 过劳时衰老加速倍率
AGING_SICK_MULT = 2.0          # 生病时衰老加速倍率

# --- 固定开销 ---
DAILY_RENT = {
    "宝安城中村": 15,  # 城中村便宜
    "南山公寓": 50,    # 白领公寓贵
}
DAILY_MISC_COST = 5            # 每日杂费

# --- 数值衰减/恢复 ---
SATIETY_DECAY = 2
ENERGY_DAY_COST = 2
ENERGY_NIGHT_RECOVER = 5
ENERGY_SLEEP_RECOVER = 15
DESIRE_DECAY_ON_FULFILL = 30

# --- 天气系统 ---
WEATHER_TYPES = {
    "晴天": {"desc": "阳光明媚，适合外出", "mood_effect": {"happiness": 1, "sadness": -1}, "energy_mod": 0, "event_chance_mod": 0},
    "多云": {"desc": "天空灰蒙蒙的", "mood_effect": {"happiness": 0}, "energy_mod": 0, "event_chance_mod": 0},
    "小雨": {"desc": "淅淅沥沥的小雨", "mood_effect": {"sadness": 2, "loneliness": 2}, "energy_mod": -1, "event_chance_mod": 0.02},
    "暴雨": {"desc": "倾盆大雨，出行困难", "mood_effect": {"anxiety": 3, "sadness": 3}, "energy_mod": -3, "event_chance_mod": 0.05},
    "台风": {"desc": "台风来袭！所有人尽量待在室内", "mood_effect": {"anxiety": 8, "sadness": 2}, "energy_mod": -5, "event_chance_mod": 0.15},
    "闷热": {"desc": "又热又闷，让人烦躁", "mood_effect": {"anger": 3, "happiness": -2}, "energy_mod": -2, "event_chance_mod": 0.01},
    "凉爽": {"desc": "难得的凉爽天气", "mood_effect": {"happiness": 2, "anxiety": -2}, "energy_mod": 1, "event_chance_mod": 0},
}

WEATHER_TRANSITION = {
    "晴天": ["晴天", "晴天", "多云", "闷热", "凉爽"],
    "多云": ["多云", "晴天", "小雨", "闷热"],
    "小雨": ["小雨", "多云", "暴雨", "多云"],
    "暴雨": ["暴雨", "小雨", "多云", "台风"],
    "台风": ["台风", "暴雨", "小雨"],
    "闷热": ["闷热", "晴天", "暴雨", "多云"],
    "凉爽": ["凉爽", "晴天", "多云"],
}

# --- 情绪系统 ---
EMOTION_DIMS = ["happiness", "sadness", "anger", "anxiety", "loneliness"]
EMOTION_LABELS = {"happiness": "开心", "sadness": "难过", "anger": "愤怒", "anxiety": "焦虑", "loneliness": "孤独"}
EMOTION_DECAY = {"happiness": -0.5, "sadness": -1, "anger": -2, "anxiety": -0.5, "loneliness": 0.5}  # 每tick自然衰减/增长 (v8.3: 大幅降低happiness衰减，让快乐更持久)

# --- 食物菜单 ---
FOOD_MENU = {
    "城中村快餐": {"cost": 5, "satiety": 40, "mood": {"happiness": 1}},
    "路边摊炒粉": {"cost": 12, "satiety": 50, "mood": {"happiness": 5}},
    "便利店饭团": {"cost": 8, "satiety": 30, "mood": {"happiness": 1}},
    "麦当劳套餐": {"cost": 35, "satiety": 60, "mood": {"happiness": 8}},
    "火锅": {"cost": 80, "satiety": 90, "mood": {"happiness": 8, "loneliness": -5}},
    "泡面": {"cost": 3, "satiety": 25, "mood": {"sadness": 3}},
    "奶茶": {"cost": 15, "satiety": 10, "mood": {"happiness": 4, "anxiety": -2}},
}

# --- 欲望系统 ---
DESIRE_DIMS = ["lust", "power", "greed", "vanity", "security"]
DESIRE_GROWTH_PER_TICK = {"lust": 0.8, "power": 0.3, "greed": 0.5, "vanity": 0.4, "security": 0.2}

BOT_DESIRE_PROFILES = {
    "bot_1": {"lust_mult": 0.8, "power_mult": 0.5, "greed_mult": 0.6, "vanity_mult": 0.3, "security_mult": 1.2},
    "bot_2": {"lust_mult": 0.6, "power_mult": 1.5, "greed_mult": 1.8, "vanity_mult": 1.5, "security_mult": 0.8},
    "bot_3": {"lust_mult": 1.0, "power_mult": 0.3, "greed_mult": 0.8, "vanity_mult": 0.2, "security_mult": 1.5},
    "bot_4": {"lust_mult": 0.7, "power_mult": 0.2, "greed_mult": 0.3, "vanity_mult": 1.2, "security_mult": 0.9},
    "bot_5": {"lust_mult": 2.0, "power_mult": 0.8, "greed_mult": 1.5, "vanity_mult": 1.8, "security_mult": 0.3},
    "bot_6": {"lust_mult": 0.5, "power_mult": 1.8, "greed_mult": 1.2, "vanity_mult": 0.8, "security_mult": 1.0},
    "bot_7": {"lust_mult": 1.0, "power_mult": 1.5, "greed_mult": 2.0, "vanity_mult": 1.0, "security_mult": 1.3},
    "bot_8": {"lust_mult": 0.2, "power_mult": 0.3, "greed_mult": 0.5, "vanity_mult": 0.3, "security_mult": 2.0},
    "bot_9": {"lust_mult": 1.2, "power_mult": 0.2, "greed_mult": 0.3, "vanity_mult": 1.5, "security_mult": 0.7},
    "bot_10":{"lust_mult": 0.8, "power_mult": 0.5, "greed_mult": 1.0, "vanity_mult": 2.5, "security_mult": 0.5},
}
DEFAULT_DESIRE_PROFILE = {"lust_mult": 1.0, "power_mult": 1.0, "greed_mult": 1.0, "vanity_mult": 1.0, "security_mult": 1.0}

# --- 地点 ---
LOCATIONS = {
    "宝安城中村":  {"desc": "密密麻麻的握手楼，便宜但嘈杂", "type": "residential"},
    "南山科技园":  {"desc": "高新技术企业聚集地", "type": "business"},
    "福田CBD":     {"desc": "金融中心，高楼林立", "type": "business"},
    "华强北":      {"desc": "电子产品集散地，人流密集", "type": "commercial"},
    "东门老街":    {"desc": "传统商业街，日结工多", "type": "commercial"},
    "南山公寓":    {"desc": "白领合租公寓", "type": "residential"},
    "深圳湾公园":  {"desc": "海边公园，适合散步思考", "type": "leisure"},
}

# --- 工作 ---
JOBS = {
    "宝安城中村": [
        {"title": "外卖骑手", "skill": "none", "min_skill": 0, "pay": 35,
         "tasks": [
             {"name": "送3单外卖", "duration": 2, "difficulty": 0.2, "desc": "骑电动车穿梭在城中村小巷里送餐"},
             {"name": "送5单外卖(高峰)", "duration": 3, "difficulty": 0.4, "desc": "午高峰订单多，时间紧"},
         ]},
        {"title": "餐馆帮工", "skill": "none", "min_skill": 0, "pay": 30,
         "tasks": [
             {"name": "洗碗切菜", "duration": 2, "difficulty": 0.1, "desc": "在后厨帮忙洗碗切菜"},
             {"name": "端盘子招呼客人", "duration": 3, "difficulty": 0.2, "desc": "前厅服务，端菜收桌"},
         ]},
        {"title": "快递分拣", "skill": "none", "min_skill": 0, "pay": 28,
         "tasks": [
             {"name": "分拣100个包裹", "duration": 2, "difficulty": 0.15, "desc": "在快递站分拣包裹"},
         ]},
    ],
    "南山科技园": [
        {"title": "初级程序员", "skill": "tech", "min_skill": 20, "pay": 80,
         "tasks": [
             {"name": "修复登录页面Bug", "duration": 3, "difficulty": 0.3, "desc": "用户反馈登录页面偶尔白屏"},
             {"name": "写API接口", "duration": 4, "difficulty": 0.4, "desc": "按产品需求写一个新的REST API"},
             {"name": "做Code Review", "duration": 2, "difficulty": 0.25, "desc": "审查同事提交的代码"},
         ]},
        {"title": "产品助理", "skill": "social", "min_skill": 15, "pay": 60,
         "tasks": [
             {"name": "整理用户反馈", "duration": 2, "difficulty": 0.2, "desc": "从各渠道收集整理用户意见"},
             {"name": "画产品原型", "duration": 3, "difficulty": 0.35, "desc": "用Figma画新功能的原型图"},
         ]},
    ],
    "福田CBD": [
        {"title": "金融实习生", "skill": "social", "min_skill": 25, "pay": 70,
         "tasks": [
             {"name": "整理财报数据", "duration": 3, "difficulty": 0.3, "desc": "把上市公司财报数据录入Excel"},
             {"name": "陪客户开会", "duration": 2, "difficulty": 0.2, "desc": "跟着经理去见客户，做会议记录"},
         ]},
        {"title": "销售代表", "skill": "social", "min_skill": 20, "pay": 55,
         "tasks": [
             {"name": "打50个Cold Call", "duration": 3, "difficulty": 0.4, "desc": "给潜在客户打电话推销产品"},
             {"name": "跟进3个意向客户", "duration": 2, "difficulty": 0.3, "desc": "约客户见面谈合作"},
         ]},
    ],
    "华强北": [
        {"title": "电子产品销售", "skill": "social", "min_skill": 10, "pay": 45,
         "tasks": [
             {"name": "卖手机配件", "duration": 2, "difficulty": 0.2, "desc": "在柜台卖手机壳、充电线"},
             {"name": "组装电脑", "duration": 3, "difficulty": 0.35, "desc": "按客户需求组装一台台式机"},
         ]},
        {"title": "直播带货助手", "skill": "social", "min_skill": 15, "pay": 50,
         "tasks": [
             {"name": "准备直播间", "duration": 2, "difficulty": 0.15, "desc": "布置灯光、摆放产品、测试设备"},
             {"name": "协助主播卖货", "duration": 3, "difficulty": 0.3, "desc": "在直播间递产品、回复弹幕"},
         ]},
    ],
    "东门老街": [
        {"title": "日结搬运工", "skill": "none", "min_skill": 0, "pay": 40,
         "tasks": [
             {"name": "搬货卸车", "duration": 2, "difficulty": 0.25, "desc": "帮商家从货车上卸货搬进店里"},
             {"name": "仓库整理", "duration": 3, "difficulty": 0.15, "desc": "整理仓库货架，分类摆放"},
         ]},
        {"title": "街头传单", "skill": "none", "min_skill": 0, "pay": 25,
         "tasks": [
             {"name": "发2小时传单", "duration": 2, "difficulty": 0.1, "desc": "在人流密集处发宣传单"},
         ]},
    ],
    "南山公寓": [
        {"title": "家政保洁", "skill": "none", "min_skill": 0, "pay": 35,
         "tasks": [
             {"name": "打扫3间房", "duration": 2, "difficulty": 0.15, "desc": "帮租户打扫房间"},
         ]},
    ],
    "深圳湾公园": [
        {"title": "公园保洁", "skill": "none", "min_skill": 0, "pay": 25,
         "tasks": [
             {"name": "清扫步道", "duration": 2, "difficulty": 0.1, "desc": "清扫公园步道上的垃圾"},
         ]},
        {"title": "街头艺人", "skill": "social", "min_skill": 15, "pay": 30,
         "tasks": [
             {"name": "表演2小时", "duration": 2, "difficulty": 0.3, "desc": "在公园广场表演才艺赚打赏"},
         ]},
    ],
}

# --- 人设 ---
PERSONAS = {
    "bot_1":  {"name": "李浩然", "age": 24, "gender": "男", "origin": "湖南长沙", "edu": "计算机硕士",
               "home": "宝安城中村", "start_loc": "宝安城中村", "money": 800, "hp": 100},
    "bot_2":  {"name": "王雪",   "age": 26, "gender": "女", "origin": "上海", "edu": "金融学学士",
               "home": "南山公寓", "start_loc": "南山公寓", "money": 2000, "hp": 100},
    "bot_3":  {"name": "张伟",   "age": 28, "gender": "男", "origin": "河南周口", "edu": "高中",
               "home": "宝安城中村", "start_loc": "宝安城中村", "money": 300, "hp": 100},
    "bot_4":  {"name": "陈静",   "age": 22, "gender": "女", "origin": "四川成都", "edu": "艺术设计大专",
               "home": "宝安城中村", "start_loc": "宝安城中村", "money": 500, "hp": 100},
    "bot_5":  {"name": "赵磊",   "age": 25, "gender": "男", "origin": "深圳本地", "edu": "社区大学",
               "home": "南山公寓", "start_loc": "华强北", "money": 3000, "hp": 100},
    "bot_6":  {"name": "刘悦",   "age": 30, "gender": "女", "origin": "山东青岛", "edu": "MBA",
               "home": "南山公寓", "start_loc": "福田CBD", "money": 5000, "hp": 100},
    "bot_7":  {"name": "周建国", "age": 45, "gender": "男", "origin": "浙江温州", "edu": "小学",
               "home": "宝安城中村", "start_loc": "华强北", "money": 1500, "hp": 100},
    "bot_8":  {"name": "吴秀英", "age": 52, "gender": "女", "origin": "广东潮汕", "edu": "初中",
               "home": "宝安城中村", "start_loc": "宝安城中村", "money": 600, "hp": 100},
    "bot_9":  {"name": "林枫",   "age": 21, "gender": "男", "origin": "福建厦门", "edu": "音乐学院肄业",
               "home": "宝安城中村", "start_loc": "东门老街", "money": 200, "hp": 100},
    "bot_10": {"name": "苏小小", "age": 19, "gender": "女", "origin": "湖北武汉", "edu": "网红培训班",
               "home": "宝安城中村", "start_loc": "华强北", "money": 400, "hp": 100},
}

FAMILY_RELATIONS = {
    "bot_3": {"parents": ["bot_8"], "children": []},
    "bot_8": {"parents": [], "children": ["bot_3"]},
}

# --- 生活琐事 / 随机事件 ---
RANDOM_EVENTS = [
    # 天气/环境类
    {"name": "突然下雨", "desc": "天空突然下起大雨，没带伞的人都在找地方躲雨", "effect": "mood_sadness_up",
     "mood": {"sadness": 5, "anxiety": 3}},
    {"name": "看到美丽的晚霞", "desc": "天边出现了绝美的晚霞，很多人停下来拍照", "effect": "mood_happy",
     "mood": {"happiness": 8, "loneliness": -3}},
    {"name": "被蚊子咬了", "desc": "胳膊上被蚊子咬了好几个包", "effect": "mosquito",
     "mood": {"anger": 3}},
    {"name": "电梯坏了", "desc": "住的楼电梯又坏了，只能爬楼梯", "effect": "elevator_broken",
     "mood": {"anger": 4, "anxiety": 2}},
    # 人际互动类
    {"name": "路边有人吵架", "desc": "两个人因为停车问题在路边大吵，引来一圈围观的人", "effect": "mood_anxiety_up",
     "mood": {"anxiety": 3, "anger": 2}},
    {"name": "附近有免费试吃", "desc": "新开的店在搞免费试吃活动，排了好长的队", "effect": "free_food",
     "mood": {"happiness": 5}},
    {"name": "收到诈骗电话", "desc": "接到一个自称是公安局的电话，要求转账", "effect": "scam_call",
     "mood": {"anxiety": 8, "anger": 5}},
    {"name": "路上捡到50块钱", "desc": "在地上发现一张50元纸币", "effect": "found_money",
     "mood": {"happiness": 10}},
    {"name": "看到流浪猫", "desc": "路边有一只可怜的流浪猫在喵喵叫，看起来很饿", "effect": "stray_cat",
     "mood": {"sadness": 3, "loneliness": -2}},
    {"name": "听到好听的街头音乐", "desc": "有人在路边弹吉他唱歌，周围聚了一圈人", "effect": "street_music",
     "mood": {"happiness": 6, "loneliness": -4}},
    {"name": "收到家人的微信红包", "desc": "家人发了一个小红包过来，附带一句“注意身体”", "effect": "family_gift",
     "mood": {"happiness": 10, "loneliness": -8}},
    {"name": "看到有人在直播", "desc": "路边有网红在直播，围了一圈人，很热闹", "effect": "live_stream",
     "mood": {"happiness": 2}},
    {"name": "物价又涨了", "desc": "常去的快餐店涨价了2块钱，老板说是因为房租涨了", "effect": "price_up",
     "mood": {"anxiety": 4, "anger": 3}},
    # NPC主动互动类（新增）
    {"name": "房东来收租", "desc": "房东王姐来敲门收租了，还唠叨了几句“下个月要涨租”", "effect": "rent_due",
     "mood": {"anxiety": 8, "anger": 3}},
    {"name": "早餐摊老李多给了一个鸡蛋", "desc": "早餐摊老李今天心情好，多给了一个煎蛋，说“小伙子多吃点”", "effect": "npc_kind",
     "mood": {"happiness": 6, "loneliness": -3}},
    {"name": "保安查居住证", "desc": "保安老张来查居住证，没有的话要被赶出去", "effect": "id_check",
     "mood": {"anxiety": 10, "anger": 5}},
    {"name": "HR小陈主动联系你", "desc": "HR小陈发来消息：“我们公司在招人，你有兴趣吗？”", "effect": "job_offer",
     "mood": {"happiness": 5, "anxiety": -3}},
    {"name": "隔壁室友小刘邀请你吃饭", "desc": "室友小刘说今晚他做饭，问你要不要一起吃", "effect": "dinner_invite",
     "mood": {"happiness": 8, "loneliness": -10}},
    {"name": "手机贩子阿强发来一条货源信息", "desc": "阿强发来消息：“兄弟，新到一批货，价格美丽，要不要看看？”", "effect": "biz_opportunity",
     "mood": {"happiness": 3}},
    # 社会事件类（新增）
    {"name": "街头有人卖艺", "desc": "一个年轻人在街头表演魔术，引来一大群人围观", "effect": "street_show",
     "mood": {"happiness": 5, "loneliness": -3}},
    {"name": "附近开了一家新店", "desc": "街角新开了一家奶茶店，打折促销中，排队的人很多", "effect": "new_shop",
     "mood": {"happiness": 3}},
    {"name": "城管来了", "desc": "城管来清理路边摊贩，小贩们慢慢散去，气氛紧张", "effect": "chengguan",
     "mood": {"anxiety": 5, "anger": 3}},
    {"name": "有人在发传单", "desc": "一个大姐在发传单，上面写着“高薪招聘，日结200”", "effect": "flyer",
     "mood": {"happiness": 2}},
    {"name": "深夜有人在楼下吵架", "desc": "半夜被楼下的吵架声吵醒，一对情侣在大声争君", "effect": "night_fight",
     "mood": {"anger": 3, "anxiety": 4, "sadness": 2}},
    {"name": "快递到了", "desc": "之前网上买的东西到了，拆快递的快乐无与伦比", "effect": "package",
     "mood": {"happiness": 8}},
    {"name": "看到以前的同学发的朋友圈", "desc": "以前的同学在朋友圈晒了买车照，而你还在城中村挤公交", "effect": "social_compare",
     "mood": {"sadness": 8, "anxiety": 5, "happiness": -5}},
]

# --- 新闻模板（会被真实新闻替换） ---
NEWS_TEMPLATES = [
    "深圳今日新增3个地铁站开通，南山到宝安通勤时间缩短15分钟",
    "华强北商户反映今年电子产品出口订单增长20%",
    "深圳发布人才补贴新政：本科毕业生可领1.5万元",
    "福田CBD写字楼空置率创新高，租金下降10%",
    "深圳湾公园周末游客量突破5万人次",
    "城中村改造计划公布：宝安3个城中村将拆迁重建",
    "深圳最低工资标准调整为2460元/月",
    "南山科技园某公司裁员30%，员工在楼下拉横幅",
    "深圳地铁11号线早高峰故障，大量乘客滞留",
    "东门老街夜市回归，日均客流量超10万",
    "深圳房价连续3个月下跌，二手房成交量回暖",
    "华强北出现新型AI硬件创业潮，多家初创公司入驻",
    "深圳暑期气温破40度，多人中暑送医",
    "外卖骑手权益保障新规出台，平台需为骑手购买保险",
    "深圳某网红奶茶店被曝使用过期原料",
]
