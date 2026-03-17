from core.world_state import world, log


def update_reputation(bot_id, delta, deed_desc):
    """更新bot的公众声望"""
    bot = world["bots"].get(bot_id)
    if not bot:
        return
    rep = bot.get("reputation", {"score": 0, "tags": [], "deeds": []})
    rep["score"] = max(-100, min(100, rep.get("score", 0) + delta))
    rep["deeds"].append({
        "desc": deed_desc,
        "delta": delta,
        "tick": world["time"]["tick"],
    })
    if len(rep["deeds"]) > 20:
        rep["deeds"] = rep["deeds"][-15:]
    bot["reputation"] = rep

    # 同步到全局声望榜
    world["reputation_board"][bot_id] = {
        "name": bot.get("name", bot_id),
        "score": rep["score"],
        "tags": rep.get("tags", []),
        "latest_deed": deed_desc,
    }

    # 声望达到阈值时自动添加标签
    score = rep["score"]
    tags = rep.get("tags", [])
    if score >= 30 and "受人尊敬" not in tags:
        tags.append("受人尊敬")
    elif score >= 15 and "有口碑" not in tags:
        tags.append("有口碑")
    elif score <= -15 and "名声不好" not in tags:
        tags.append("名声不好")
    elif score <= -30 and "臭名昭著" not in tags:
        tags.append("臭名昭著")
    rep["tags"] = tags[-5:]  # 最多5个标签


def reputation_interaction_modifier(bot_id, target_id):
    """根据声望调整社交互动的基础友好度"""
    target_rep = world["bots"].get(target_id, {}).get("reputation", {}).get("score", 0)
    if target_rep >= 20:
        return 1.3  # 声望好的人更容易被接受
    elif target_rep <= -20:
        return 0.5  # 声望差的人会被排斥
    return 1.0
