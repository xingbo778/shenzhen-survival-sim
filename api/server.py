import os, json, logging, subprocess, time as _time
from threading import Thread
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.world_state import world, lock, log, init_world
from core.constants import AGING_BASE, PERSONAS
from actions.processor import process_action_v10

app = FastAPI(title="深圳生存模拟 v9.0 - 自我进化")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/world")
def get_world():
    with lock:
        safe = {
            "time": world["time"],
            "weather": world["weather"],
            "news_feed": world["news_feed"],
            "hot_topics": world["hot_topics"],
            "bots": {},
            "locations": {},
            "events": world["events"][-10:],
            "active_effects": world["active_effects"],
            "moments": world["moments"][-20:],
            "food_prices": world.get("food_prices", {}),
        }
        for bid, bot in world["bots"].items():
            safe["bots"][bid] = {
                "id": bid, "name": bot["name"], "age": bot["age"], "gender": bot["gender"],
                "location": bot["location"], "hp": bot["hp"], "money": bot["money"],
                "energy": bot["energy"], "satiety": bot["satiety"], "status": bot["status"],
                "job": bot["job"], "skills": bot["skills"], "inventory": bot["inventory"],
                "is_sleeping": bot.get("is_sleeping", False),
                "current_task": bot.get("current_task"),
                "emotions": bot.get("emotions", {}),
                "desires": bot.get("desires", {}),
                "phone_battery": bot.get("phone_battery", 100),
                "family": bot.get("family", {}),
                "selfie_count": bot.get("selfie_count", 0),
                "aging_rate": bot.get("aging_rate", AGING_BASE),
                "emotional_bonds_summary": {k: {"label": v.get("label", ""), "closeness": v.get("closeness", 0), "latest_impression": (v.get("impressions", []) or [""])[-1]} for k, v in bot.get("emotional_bonds", {}).items()},
                "long_term_goal": bot.get("long_term_goal"),
                "narrative_summary": bot.get("narrative_summary"),
                "pending_reply_to": bot.get("pending_reply_to"),
                "core_memories": bot.get("core_memories", []),
                "recent_actions_synced": bot.get("recent_actions_synced", []),
                "current_activity": bot.get("current_activity", ""),
                # v9.0
                "reputation": bot.get("reputation", {"score": 0, "tags": [], "deeds": []}),
                "created_things": bot.get("created_things", []),
                "generation": bot.get("generation", 0),
                "inherited_from": bot.get("inherited_from"),
                # v10.0
                "last_action_feedback": bot.get("last_action_feedback", {}),
                "action_log": bot.get("action_log", [])[-10:],
            }
        for loc_name, loc_data in world["locations"].items():
            safe["locations"][loc_name] = {
                "desc": loc_data["desc"],
                "type": loc_data["type"],
                "bots": loc_data["bots"],
                "npcs": [{"name": n["name"], "role": n["role"]} for n in loc_data["npcs"]],
                "jobs": [{"title": j["title"], "pay": j["pay"]} for j in loc_data.get("jobs", [])],
                # v9.0
                "public_memory": loc_data.get("public_memory", [])[-5:],
                "modifications": loc_data.get("modifications", []),
                "vibe": loc_data.get("vibe", "普通"),
            }
        # v9.0: 添加进化引擎数据
        safe["world_modifications"] = world.get("world_modifications", [])[-20:]
        safe["urban_legends"] = world.get("urban_legends", [])[-10:]
        safe["graveyard"] = world.get("graveyard", [])
        safe["generation_count"] = world.get("generation_count", 0)
        safe["reputation_board"] = world.get("reputation_board", {})
        # v10.1: 保存活跃规则
        rules_to_save = []
        for r in world.get("active_rules", []):
            r_copy = {k: v for k, v in r.items() if k != "_triggered_bots"}
            rules_to_save.append(r_copy)
        safe["active_rules"] = rules_to_save[-50:]
        return safe


@app.get("/bot/{bot_id}/detail")
def get_bot_detail(bot_id: str):
    with lock:
        bot = world["bots"].get(bot_id)
        if not bot:
            return JSONResponse({"error": "not found"}, 404)
        return {
            "id": bot_id,
            "name": bot["name"],
            "age": bot["age"],
            "gender": bot["gender"],
            "origin": bot.get("origin", ""),
            "edu": bot.get("edu", ""),
            "home": bot["home"],
            "location": bot["location"],
            "hp": bot["hp"],
            "money": bot["money"],
            "energy": bot["energy"],
            "satiety": bot["satiety"],
            "status": bot["status"],
            "job": bot["job"],
            "skills": bot["skills"],
            "inventory": bot["inventory"],
            "relationships": bot["relationships"],
            "family": bot.get("family", {}),
            "is_sleeping": bot.get("is_sleeping", False),
            "current_task": bot.get("current_task"),
            "selfie_count": bot.get("selfie_count", 0),
            "aging_rate": bot.get("aging_rate", AGING_BASE),
            "emotions": bot.get("emotions", {}),
            "desires": bot.get("desires", {}),
            "phone_battery": bot.get("phone_battery", 100),
            "values": bot.get("values", {}),
            "core_memories": bot.get("core_memories", []),
            "emotional_bonds": bot.get("emotional_bonds", {}),
            "action_log": bot.get("action_log", [])[-15:],
            "long_term_goal": bot.get("long_term_goal"),
            "narrative_summary": bot.get("narrative_summary"),
            "recent_actions_synced": bot.get("recent_actions_synced", []),
            "pending_reply_to": bot.get("pending_reply_to"),
            # v9.0
            "reputation": bot.get("reputation", {"score": 0, "tags": [], "deeds": []}),
            "created_things": bot.get("created_things", []),
            "generation": bot.get("generation", 0),
            "inherited_from": bot.get("inherited_from"),
            "known_legends": bot.get("known_legends", []),
        }


@app.post("/bot/{bot_id}/action")
async def bot_action(bot_id: str, request: Request):
    data = await request.json()
    plan = data.get("plan", "idle")
    with lock:
        bot = world["bots"].get(bot_id)
        if not bot or bot["status"] != "alive":
            return {"error": "bot not available"}
        result = process_action_v10(bot_id, plan)
    return result


@app.post("/bot/{bot_id}/update_inner")
async def update_inner(bot_id: str, request: Request):
    """v8.2兼容端点"""
    data = await request.json()
    with lock:
        bot = world["bots"].get(bot_id)
        if not bot:
            return {"error": "not found"}
        if "values" in data:
            bot["values"] = data["values"]
        if "new_core_memory" in data:
            bot["core_memories"].append(data["new_core_memory"])
            if len(bot["core_memories"]) > 20:
                bot["core_memories"] = bot["core_memories"][-15:]
        if "emotional_bonds" in data:
            bot["emotional_bonds"] = data["emotional_bonds"]
        if "emotions" in data:
            bot["emotions"] = data["emotions"]
    return {"ok": True}


@app.post("/bot/{bot_id}/sync_state")
async def sync_state(bot_id: str, request: Request):
    """v8.3: 统一状态同步总线 - bot_agent每次心跳后同步完整状态"""
    data = await request.json()
    with lock:
        bot = world["bots"].get(bot_id)
        if not bot:
            return {"error": "not found"}
        # 同步核心记忆
        if "core_memories" in data and data["core_memories"]:
            bot["core_memories"] = data["core_memories"][-20:]
        # 同步价值观
        if "values" in data and data["values"]:
            bot["values"] = data["values"]
        # 同步情感纽带
        if "emotional_bonds" in data and data["emotional_bonds"]:
            bot["emotional_bonds"] = data["emotional_bonds"]
        # 同步最近行动
        if "recent_actions" in data:
            bot["recent_actions_synced"] = data["recent_actions"][-10:]
        # 同步长期目标
        if "long_term_goal" in data and data["long_term_goal"]:
            bot["long_term_goal"] = data["long_term_goal"]
        # 同步内心状态叙事摘要
        if "narrative_summary" in data and data["narrative_summary"]:
            bot["narrative_summary"] = data["narrative_summary"]
        # 清除已回应的pending_reply
        if data.get("clear_pending_reply"):
            bot["pending_reply_to"] = None
    return {"ok": True}


@app.get("/messages/{bot_id}")
def get_messages(bot_id: str):
    with lock:
        msgs = [m for m in world["message_board"] if m.get("to") == bot_id or m.get("to") == "public"]
        bot = world["bots"].get(bot_id, {})
        return {
            "messages": msgs[-20:],
            "pending_reply_to": bot.get("pending_reply_to"),
        }


@app.post("/admin/send_message")
async def admin_send_message(request: Request):
    data = await request.json()
    with lock:
        world["message_board"].append({
            "tick": world["time"]["tick"],
            "time": world["time"]["virtual_datetime"],
            "from": data.get("from", "系统"),
            "to": data.get("to", "public"),
            "msg": data.get("message", ""),
            "priority": data.get("priority", "normal"),
        })
    return {"ok": True}


@app.get("/moments")
def get_moments():
    with lock:
        return {"moments": world["moments"][-50:]}


@app.post("/moments/{moment_id}/like")
async def like_moment(moment_id: str, request: Request):
    data = await request.json()
    bot_id = data.get("bot_id", "")
    with lock:
        for m in world["moments"]:
            if m["id"] == moment_id:
                if bot_id not in m["likes"]:
                    m["likes"].append(bot_id)
                return {"ok": True}
    return {"error": "moment not found"}


@app.post("/moments/{moment_id}/comment")
async def comment_moment(moment_id: str, request: Request):
    data = await request.json()
    with lock:
        for m in world["moments"]:
            if m["id"] == moment_id:
                m["comments"].append({
                    "bot_id": data.get("bot_id", ""),
                    "bot_name": data.get("bot_name", ""),
                    "content": data.get("content", ""),
                    "tick": world["time"]["tick"],
                })
                return {"ok": True}
    return {"error": "moment not found"}


@app.get("/gallery")
def get_gallery():
    with lock:
        return {"photos": world["gallery"][-30:]}


@app.get("/world_narrative")
def get_world_narrative():
    with lock:
        return {"narrative": world.get("world_narrative", "这座城市刚刚苏醒，故事还没有开始。")}


# === v9.0 进化引擎专用端点 ===
@app.get("/evolution")
def get_evolution_data():
    """v9.0: 获取所有进化引擎数据"""
    with lock:
        return {
            "world_modifications": world.get("world_modifications", []),
            "urban_legends": world.get("urban_legends", []),
            "graveyard": world.get("graveyard", []),
            "generation_count": world.get("generation_count", 0),
            "reputation_board": world.get("reputation_board", {}),
            "location_vibes": {loc: data.get("vibe", "普通") for loc, data in world["locations"].items()},
            "location_memories": {loc: data.get("public_memory", [])[-10:] for loc, data in world["locations"].items()},
            "location_modifications": {loc: data.get("modifications", []) for loc, data in world["locations"].items()},
            # v10.1: 规则引擎数据
            "active_rules": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "creator_name": r.get("creator_name", "?"),
                    "location": r.get("location"),
                    "description": r.get("description", ""),
                    "durability": round(r.get("durability", 0), 1),
                    "execution_count": r.get("execution_count", 0),
                    "active": r.get("active", True),
                }
                for r in world.get("active_rules", [])
            ],
            "active_rules_count": sum(1 for r in world.get("active_rules", []) if r.get("active", True)),
        }


@app.get("/rules")
def get_rules():
    """v10.1: 获取所有世界规则"""
    with lock:
        rules = []
        for r in world.get("active_rules", []):
            rules.append({
                "id": r["id"],
                "name": r["name"],
                "creator": r.get("creator", ""),
                "creator_name": r.get("creator_name", "?"),
                "location": r.get("location"),
                "trigger": r.get("trigger", "every_tick"),
                "description": r.get("description", ""),
                "durability": round(r.get("durability", 0), 1),
                "decay_rate": r.get("decay_rate", 0.1),
                "execution_count": r.get("execution_count", 0),
                "active": r.get("active", True),
                "created_tick": r.get("created_tick", 0),
                "effects_summary": str(r.get("effects", []))[:100],
            })
        return {"rules": rules, "active_count": sum(1 for r in rules if r.get("active", True))}


@app.get("/rules/{location}")
def get_location_rules(location: str):
    """v10.1: 获取某地点的活跃规则摘要"""
    from rules.rules_engine import get_rules_summary
    with lock:
        summaries = get_rules_summary(world, location)
        return {"location": location, "rules": summaries}


@app.get("/location/{loc_name}/history")
def get_location_history(loc_name: str):
    """v9.0: 获取地点历史"""
    with lock:
        loc = world["locations"].get(loc_name)
        if not loc:
            return JSONResponse({"error": "location not found"}, 404)
        return {
            "name": loc_name,
            "desc": loc["desc"],
            "vibe": loc.get("vibe", "普通"),
            "public_memory": loc.get("public_memory", []),
            "modifications": loc.get("modifications", []),
            "current_bots": loc["bots"],
        }


@app.get("/reputation")
def get_reputation_board():
    """v9.0: 获取声望榜"""
    with lock:
        board = []
        for bid, bot in world["bots"].items():
            rep = bot.get("reputation", {"score": 0, "tags": [], "deeds": []})
            board.append({
                "bot_id": bid,
                "name": bot.get("name", bid),
                "score": rep.get("score", 0),
                "tags": rep.get("tags", []),
                "deeds": rep.get("deeds", [])[-5:],
                "generation": bot.get("generation", 0),
                "status": bot.get("status", "alive"),
            })
        board.sort(key=lambda x: x["score"], reverse=True)
        return {"reputation_board": board}


@app.get("/graveyard")
def get_graveyard():
    """v9.0: 获取墓地记录"""
    with lock:
        return {"graveyard": world.get("graveyard", [])}


@app.get("/legends")
def get_urban_legends():
    """v9.0: 获取城市传说"""
    with lock:
        return {"urban_legends": world.get("urban_legends", [])}


@app.post("/admin/save_snapshot")
async def save_snapshot():
    with lock:
        snapshot = {
            "time": world["time"],
            "weather": world["weather"],
            "news_feed": world["news_feed"],
            "hot_topics": world["hot_topics"],
            "bots": {},
            "locations": {},
            "events": world["events"][-50:],
            "message_board": world["message_board"][-100:],
            "moments": world["moments"][-100:],
            "gallery": world["gallery"],
            "world_narrative": world.get("world_narrative", ""),
            # v9.0
            "world_modifications": world.get("world_modifications", []),
            "urban_legends": world.get("urban_legends", []),
            "generation_count": world.get("generation_count", 0),
            "graveyard": world.get("graveyard", []),
            "reputation_board": world.get("reputation_board", {}),
        }
        for bid, bot in world["bots"].items():
            snapshot["bots"][bid] = dict(bot)
            snapshot["bots"][bid]["action_log"] = bot["action_log"][-20:]
            snapshot["bots"][bid]["long_term_goal"] = bot.get("long_term_goal")
            snapshot["bots"][bid]["pending_reply_to"] = bot.get("pending_reply_to")
            snapshot["bots"][bid]["recent_actions_synced"] = bot.get("recent_actions_synced", [])
        # v9.0: 保存地点公共记忆
        for loc_name, loc_data in world["locations"].items():
            snapshot["locations"][loc_name] = {
                "public_memory": loc_data.get("public_memory", []),
                "modifications": loc_data.get("modifications", []),
                "vibe": loc_data.get("vibe", "普通"),
            }
        with open("/home/ubuntu/world_state_snapshot.json", "w") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return {"ok": True, "tick": world["time"]["tick"]}


# 静态文件服务
if os.path.exists("/home/ubuntu/selfies"):
    app.mount("/selfies", StaticFiles(directory="/home/ubuntu/selfies"), name="selfies")

avatar_dir = "/home/ubuntu/bot_avatars_v2"
if not os.path.exists(avatar_dir):
    avatar_dir = "/home/ubuntu/bot_avatars"
if os.path.exists(avatar_dir):
    app.mount("/avatars", StaticFiles(directory=avatar_dir), name="avatars")


def _do_auto_save():
    """自动保存快照（非async版本，供tick循环调用）"""
    try:
        with lock:
            snapshot = {
                "time": world["time"],
                "weather": world["weather"],
                "news_feed": world["news_feed"],
                "hot_topics": world["hot_topics"],
                "bots": {},
                "locations": {},
                "events": world["events"][-50:],
                "message_board": world["message_board"][-100:],
                "moments": world["moments"][-100:],
                "gallery": world["gallery"],
                "world_narrative": world.get("world_narrative", ""),
                "food_prices": world.get("food_prices", {}),
                # v9.0
                "world_modifications": world.get("world_modifications", []),
                "urban_legends": world.get("urban_legends", []),
                "generation_count": world.get("generation_count", 0),
                "graveyard": world.get("graveyard", []),
                "reputation_board": world.get("reputation_board", {}),
            }
            for bid, bot in world["bots"].items():
                snapshot["bots"][bid] = dict(bot)
                snapshot["bots"][bid]["action_log"] = bot["action_log"][-20:]
                snapshot["bots"][bid]["long_term_goal"] = bot.get("long_term_goal")
                snapshot["bots"][bid]["pending_reply_to"] = bot.get("pending_reply_to")
                snapshot["bots"][bid]["recent_actions_synced"] = bot.get("recent_actions_synced", [])
                snapshot["bots"][bid]["narrative_summary"] = bot.get("narrative_summary")
            # v9.0: 保存地点公共记忆
            for loc_name, loc_data in world["locations"].items():
                snapshot["locations"][loc_name] = {
                    "public_memory": loc_data.get("public_memory", []),
                    "modifications": loc_data.get("modifications", []),
                    "vibe": loc_data.get("vibe", "普通"),
                }
            with open("/home/ubuntu/world_state_snapshot.json", "w") as f:
                json.dump(snapshot, f, ensure_ascii=False)
        log.info(f"自动快照已保存 (tick={world['time']['tick']})")
        log.info(f"  v9.0: {len(world.get('world_modifications',[]))}个世界改造, {len(world.get('urban_legends',[]))}个城市传说, {len(world.get('graveyard',[]))}个墓地记录")
    except Exception as e:
        log.error(f"自动快照保存失败: {e}")


def start_tick_loop():
    """用简单的线程循环代替APScheduler"""
    from core.tick_engine import world_tick
    def _loop():
        while True:
            try:
                world_tick()
                # 每10个tick自动保存一次快照
                if world["time"]["tick"] % 10 == 0:
                    _do_auto_save()
            except Exception as e:
                log.error(f"Tick异常: {e}")
            _time.sleep(15)  # 每15秒一个tick (加速模式)
    t = Thread(target=_loop, daemon=True)
    t.start()
    log.info("Tick循环已启动 (15秒/tick 加速模式, 每10tick自动保存快照)")


@app.on_event("startup")
def on_startup():
    init_world()
    start_tick_loop()
    log.info("=== 深圳生存模拟 v9.0 世界引擎启动 (自我进化: 世界改造/地点记忆+声望/代际传承) ===")
    # 启动Bot进程
    for bot_id in PERSONAS:
        bot = world["bots"].get(bot_id)
        if bot and bot["status"] == "alive":
            try:
                subprocess.Popen(
                    ["python3", "/home/ubuntu/shenzhen-survival-sim/bot_agent_v8.py"],
                    env=dict(os.environ, BOT_ID=bot_id)
                )
                log.info(f"Bot {bot_id} 进程已启动")
            except Exception as e:
                log.error(f"启动Bot {bot_id} 进程失败: {e}")
