import random
from core.world_state import world, log
from core.constants import NEWS_TEMPLATES
from utils.ai_client import client


def inject_news():
    """注入新闻到世界中"""
    # 先尝试从真实新闻API获取
    real_news = fetch_real_news()
    if real_news:
        world["news_feed"] = real_news[-5:]
    else:
        # 用模板新闻
        selected = random.sample(NEWS_TEMPLATES, min(3, len(NEWS_TEMPLATES)))
        world["news_feed"] = [
            {"headline": n, "source": "深圳晚报", "tick": world["time"]["tick"],
             "time": world["time"]["virtual_datetime"]}
            for n in selected
        ]

    # 生成热搜话题
    world["hot_topics"] = generate_hot_topics()
    log.info(f"📰 新闻注入: {len(world['news_feed'])}条新闻, {len(world['hot_topics'])}个热搜")


def fetch_real_news():
    """尝试从真实新闻源获取深圳相关新闻"""
    try:
        import requests as req
        # 使用LLM生成当日新闻（模拟真实新闻注入）
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": f"""生成3条虚构但真实感很强的深圳本地新闻标题。
要求：
- 涉及深圳的经济、生活、科技、社会等不同方面
- 有正面也有负面
- 像真实新闻标题一样简洁
- 当前虚拟时间: {world['time']['virtual_datetime']}

只输出3行新闻标题，不要编号，不要其他文字。"""}],
            temperature=0.9, max_tokens=200,
        )
        lines = [l.strip() for l in resp.choices[0].message.content.strip().split("\n") if l.strip()]
        return [
            {"headline": l, "source": "AI深圳日报", "tick": world["time"]["tick"],
             "time": world["time"]["virtual_datetime"]}
            for l in lines[:5]
        ]
    except:
        return []


def generate_hot_topics():
    """生成热搜话题"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": f"""生成5个当前深圳年轻人会讨论的热搜话题。
要求：包含社会话题、娱乐八卦、生活吐槽等。简短，像微博热搜。
当前虚拟时间: {world['time']['virtual_datetime']}
只输出5行话题，不要编号。"""}],
            temperature=0.9, max_tokens=150,
        )
        lines = [l.strip().lstrip("#").strip() for l in resp.choices[0].message.content.strip().split("\n") if l.strip()]
        return lines[:5]
    except:
        return ["深圳打工人的日常", "城中村美食推荐", "今天又加班了", "深圳租房太贵了", "周末去哪玩"]
