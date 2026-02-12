#!/usr/bin/env python3
import os, json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
import uvicorn, requests as req

app = FastAPI()

@app.get("/avatars/{filename}")
def get_avatar(filename: str):
    # 优先真人头像(jpg)
    base = filename.rsplit('.', 1)[0]
    for ext in ['jpg', 'jpeg', 'png']:
        for d in ['/home/ubuntu/bot_avatars_v2', '/home/ubuntu/bot_avatars']:
            path = f"{d}/{base}.{ext}"
            if os.path.exists(path):
                mt = "image/jpeg" if ext in ['jpg','jpeg'] else "image/png"
                with open(path, "rb") as f:
                    return Response(content=f.read(), media_type=mt)
    return Response(content=b"", status_code=404)

@app.get("/selfies/{filename}")
def get_selfie(filename: str):
    path = f"/home/ubuntu/selfies/{filename}"
    if os.path.exists(path):
        media = "image/jpeg" if filename.endswith(".jpg") else "image/png"
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type=media)
    return Response(content=b"", status_code=404)

@app.get("/api/logs/{log_name}")
def get_log(log_name: str):
    path = f"/home/ubuntu/logs/{log_name}.log"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": lines[-100:]}
    return {"lines": []}

@app.get("/api/world")
def get_world():
    try:
        r = req.get("http://localhost:8000/world", timeout=3)
        return r.json()
    except:
        return {"error": "World engine not available"}

@app.get("/api/bot/{bot_id}/detail")
def get_bot_detail(bot_id: str):
    try:
        r = req.get(f"http://localhost:8000/bot/{bot_id}/detail", timeout=3)
        return r.json()
    except:
        return {"error": "Cannot fetch bot detail"}

@app.get("/api/messages/{bot_id}")
def get_messages(bot_id: str):
    try:
        r = req.get(f"http://localhost:8000/messages/{bot_id}", timeout=3)
        return r.json()
    except:
        return {"messages": []}

@app.get("/api/gallery")
def get_gallery():
    try:
        r = req.get("http://localhost:8000/gallery", timeout=3)
        return r.json()
    except:
        return {"gallery": []}

@app.post("/api/add_bot")
async def add_bot(request: Request):
    data = await request.json()
    try:
        r = req.post("http://localhost:8000/admin/add_bot", json=data, timeout=5)
        return r.json()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/send_message")
async def send_message(request: Request):
    data = await request.json()
    try:
        r = req.post("http://localhost:8000/admin/send_message", json=data, timeout=5)
        return r.json()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/", response_class=HTMLResponse)
def dashboard():
    bots_info = [
        {"id": "bot_1", "name": "李浩然", "role": "程序员", "color": "#4A90D9"},
        {"id": "bot_2", "name": "王雪", "role": "金融分析师", "color": "#E8913A"},
        {"id": "bot_3", "name": "张伟", "role": "打工人", "color": "#5BB5A2"},
        {"id": "bot_4", "name": "陈静", "role": "设计师", "color": "#C9A96E"},
        {"id": "bot_5", "name": "赵磊", "role": "富二代", "color": "#00BCD4"},
        {"id": "bot_6", "name": "刘悦", "role": "创业者", "color": "#E91E63"},
        {"id": "bot_7", "name": "周建国", "role": "老商人", "color": "#FF9800"},
        {"id": "bot_8", "name": "吴秀英", "role": "餐馆老板", "color": "#8BC34A"},
        {"id": "bot_9", "name": "林枫", "role": "音乐人", "color": "#9C27B0"},
        {"id": "bot_10", "name": "苏小小", "role": "网红", "color": "#FF69B4"},
    ]
    bots_json = json.dumps(bots_info, ensure_ascii=False)
    locations_json = json.dumps({
        "宝安城中村": {"x": 12, "y": 30, "icon": "🏚️", "type": "residential"},
        "南山科技园": {"x": 32, "y": 48, "icon": "🏢", "type": "work"},
        "南山公寓":   {"x": 25, "y": 68, "icon": "🏠", "type": "residential"},
        "华强北":     {"x": 55, "y": 35, "icon": "🔌", "type": "commercial"},
        "福田CBD":    {"x": 68, "y": 55, "icon": "🏦", "type": "work"},
        "东门老街":   {"x": 78, "y": 30, "icon": "🏮", "type": "commercial"},
        "深圳湾公园": {"x": 42, "y": 82, "icon": "🌊", "type": "leisure"},
    }, ensure_ascii=False)

    html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>深圳生存模拟 - 实时监控 v5</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #080c14; color: #e0e0e0; font-family: 'Noto Sans SC', 'Segoe UI', sans-serif; overflow: hidden; height: 100vh; }

/* Header */
.header { background: linear-gradient(135deg, #0f1520, #0a0e17); padding: 6px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(77,150,255,0.15); height: 48px; backdrop-filter: blur(10px); }
.header h1 { font-size: 16px; font-weight: 700; letter-spacing: 2px; }
.header h1 .city { background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcb77, #4d96ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.header h1 .ver { font-size: 10px; color: #555; font-weight: 300; vertical-align: super; }
.header .clock { font-size: 13px; color: #ffd93d; font-family: 'Courier New', monospace; letter-spacing: 1px; }
.header .controls { display: flex; gap: 6px; }
.header .btn { padding: 4px 12px; font-size: 11px; border-radius: 20px; cursor: pointer; border: 1px solid rgba(77,150,255,0.3); background: rgba(77,150,255,0.08); color: #4d96ff; transition: all 0.3s; font-family: inherit; }
.header .btn:hover { background: rgba(77,150,255,0.2); border-color: #4d96ff; }

/* Layout */
.main { display: flex; height: calc(100vh - 48px); }
.left-panel { width: 46%; display: flex; flex-direction: column; border-right: 1px solid rgba(255,255,255,0.05); }

/* Map */
.map-container { flex: 1; position: relative; padding: 8px; min-height: 0; }
.map-bg { width: 100%; height: 100%; position: relative; border-radius: 12px; overflow: hidden; transition: background 2s; }
.map-bg.day { background: linear-gradient(180deg, #1a3a5a 0%, #1a2a3a 30%, #152030 100%); }
.map-bg.sunset { background: linear-gradient(180deg, #3a2a1a 0%, #2a1a2a 30%, #1a1a2a 100%); }
.map-bg.night { background: linear-gradient(180deg, #0a0e17 0%, #0d1220 30%, #0a0e17 100%); }
.map-bg.dawn { background: linear-gradient(180deg, #1a2a4a 0%, #2a2a3a 30%, #1a2030 100%); }

/* Map roads */
.map-road { position: absolute; background: rgba(255,255,255,0.04); border-radius: 2px; }
.map-road.h { height: 2px; }
.map-road.v { width: 2px; }

/* Map locations */
.loc-zone { position: absolute; transform: translate(-50%, -50%); border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; cursor: default; transition: all 0.3s; }
.loc-zone:hover { border-color: rgba(255,255,255,0.15); }
.loc-zone.residential { background: rgba(100,200,100,0.06); }
.loc-zone.work { background: rgba(100,150,255,0.06); }
.loc-zone.commercial { background: rgba(255,180,50,0.06); }
.loc-zone.leisure { background: rgba(100,200,255,0.06); }
.loc-icon { font-size: 20px; filter: drop-shadow(0 0 4px rgba(0,0,0,0.5)); }
.loc-name { font-size: 10px; color: rgba(255,255,255,0.5); white-space: nowrap; text-shadow: 0 1px 3px rgba(0,0,0,0.8); font-weight: 500; letter-spacing: 0.5px; }
.loc-count { font-size: 9px; color: rgba(255,255,255,0.3); }

/* Map stars (night) */
.star { position: absolute; width: 2px; height: 2px; background: rgba(255,255,255,0.3); border-radius: 50%; animation: twinkle 3s infinite; }
@keyframes twinkle { 0%,100% { opacity: 0.3; } 50% { opacity: 0.8; } }

/* Bot avatars on map */
.bot-avatar-map { position: absolute; width: 34px; height: 34px; border-radius: 50%; border: 2px solid; cursor: pointer; transition: all 0.8s cubic-bezier(0.4,0,0.2,1); transform: translate(-50%, -50%); box-shadow: 0 2px 8px rgba(0,0,0,0.4); object-fit: cover; }
.bot-avatar-map:hover { transform: translate(-50%, -50%) scale(1.3); z-index: 100; box-shadow: 0 0 20px rgba(77,150,255,0.4); }
.bot-avatar-map.dead { filter: grayscale(100%) brightness(0.5); opacity: 0.4; }
.bot-avatar-map.sleeping { animation: pulse-sleep 2.5s ease-in-out infinite; }
@keyframes pulse-sleep { 0%,100% { box-shadow: 0 2px 8px rgba(0,0,0,0.4); } 50% { box-shadow: 0 0 16px rgba(100,100,255,0.5); } }
.bot-avatar-map.working { box-shadow: 0 0 12px rgba(255,200,50,0.4); }
.sleep-zzz { position: absolute; font-size: 12px; pointer-events: none; animation: float-zzz 2.5s infinite; }
@keyframes float-zzz { 0% { opacity: 1; transform: translate(0,0) scale(1); } 100% { opacity: 0; transform: translate(8px, -18px) scale(0.6); } }

/* Bot cards */
.cards-container { height: 175px; min-height: 175px; overflow-x: auto; overflow-y: hidden; display: flex; gap: 6px; padding: 6px 8px; background: rgba(10,14,23,0.95); white-space: nowrap; border-top: 1px solid rgba(255,255,255,0.05); }
.bot-card { min-width: 130px; background: linear-gradient(180deg, rgba(26,31,46,0.9), rgba(18,22,31,0.9)); border-radius: 10px; padding: 8px; cursor: pointer; transition: all 0.3s; border: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; align-items: center; gap: 3px; position: relative; backdrop-filter: blur(5px); }
.bot-card:hover, .bot-card.active { border-color: rgba(77,150,255,0.4); background: linear-gradient(180deg, rgba(30,37,56,0.95), rgba(20,25,38,0.95)); transform: translateY(-2px); }
.bot-card img { width: 38px; height: 38px; border-radius: 50%; border: 2px solid; object-fit: cover; }
.bot-card .name { font-size: 12px; font-weight: 600; }
.bot-card .role { font-size: 10px; color: #666; }
.bot-card .stats { font-size: 10px; width: 100%; }
.bot-card .hp-bar { width: 100%; height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; margin-top: 2px; overflow: hidden; }
.bot-card .hp-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease; }
.bot-card .stat-row { display: flex; justify-content: space-between; margin-top: 1px; font-size: 9px; color: #888; }
.bot-card .sleep-badge { position: absolute; top: 3px; right: 3px; font-size: 11px; }
.bot-card .task-badge { font-size: 9px; color: #ffd93d; margin-top: 2px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: center; }
.bot-card .detail-btn { margin-top: 2px; padding: 2px 10px; font-size: 9px; background: rgba(77,150,255,0.1); color: #4d96ff; border: 1px solid rgba(77,150,255,0.2); border-radius: 12px; cursor: pointer; transition: all 0.2s; }
.bot-card .detail-btn:hover { background: rgba(77,150,255,0.25); }

/* Right panel */
.right-panel { flex: 1; display: flex; flex-direction: column; }
.log-tabs { display: flex; flex-wrap: wrap; gap: 3px; padding: 6px 8px; background: rgba(10,14,23,0.95); border-bottom: 1px solid rgba(255,255,255,0.05); }
.log-tab { padding: 3px 10px; font-size: 11px; border-radius: 12px; cursor: pointer; background: rgba(26,31,46,0.6); color: #666; border: 1px solid transparent; transition: all 0.2s; }
.log-tab:hover { color: #aaa; }
.log-tab.active { background: rgba(77,150,255,0.12); color: #fff; border-color: rgba(77,150,255,0.3); }

.view-toggle { display: none; padding: 4px 8px; background: rgba(10,14,23,0.95); border-bottom: 1px solid rgba(255,255,255,0.05); gap: 4px; }
.view-toggle.visible { display: flex; }
.view-btn { padding: 3px 10px; font-size: 10px; border-radius: 12px; cursor: pointer; background: rgba(26,31,46,0.6); color: #666; border: 1px solid transparent; transition: all 0.2s; font-family: inherit; }
.view-btn.active { background: rgba(77,150,255,0.12); color: #fff; border-color: rgba(77,150,255,0.3); }

.log-content { flex: 1; overflow-y: auto; padding: 8px; font-family: 'Fira Code', 'Consolas', monospace; font-size: 11px; line-height: 1.7; min-height: 0; }
.log-line { padding: 1px 4px; border-radius: 3px; word-wrap: break-word; }
.log-line:hover { background: rgba(255,255,255,0.03); }
.log-line.inner { color: #ffd93d; }
.log-line.action { color: #ff6b6b; }
.log-line.result { color: #6bcb77; }
.log-line.message { color: #4d96ff; }
.log-line.error { color: #ff4444; }
.log-line.death { color: #ff0000; animation: blink 0.5s infinite; }
.log-line.values { color: #e040fb; }
.log-line.memory { color: #ffab40; }
.log-line.bond { color: #40c4ff; }
.log-line.task { color: #ffd93d; background: rgba(255,217,61,0.05); }
@keyframes blink { 50% { opacity: 0.3; } }

.chat-content { flex: 1; overflow-y: auto; padding: 10px; display: none; min-height: 0; }
.chat-content.visible { display: block; }
.chat-bubble { max-width: 80%; padding: 8px 12px; border-radius: 14px; margin-bottom: 8px; font-size: 12px; line-height: 1.5; word-wrap: break-word; }
.chat-bubble.incoming { background: rgba(26,42,58,0.8); color: #e0e0e0; margin-right: auto; border-bottom-left-radius: 4px; }
.chat-bubble.outgoing { background: rgba(42,74,106,0.8); color: #e0e0e0; margin-left: auto; border-bottom-right-radius: 4px; }
.chat-bubble .sender { font-size: 10px; color: #888; margin-bottom: 3px; }
.chat-bubble .time { font-size: 9px; color: #444; margin-top: 3px; text-align: right; }
.chat-bubble.god { background: rgba(58,42,90,0.8); border: 1px solid rgba(106,74,154,0.3); }

.msg-bar { display: none; padding: 6px 8px; background: rgba(10,14,23,0.95); border-top: 1px solid rgba(255,255,255,0.05); }
.msg-bar.visible { display: flex; gap: 6px; align-items: center; }
.msg-bar .sender-select { padding: 4px 8px; font-size: 10px; background: rgba(26,31,46,0.8); color: #e0e0e0; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; font-family: inherit; }
.msg-bar input { flex: 1; padding: 6px 10px; font-size: 11px; background: rgba(26,31,46,0.8); color: #e0e0e0; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; outline: none; font-family: inherit; }
.msg-bar input:focus { border-color: rgba(77,150,255,0.4); }
.msg-bar .send-btn { padding: 6px 14px; font-size: 11px; background: linear-gradient(135deg, #4d96ff, #3a7bd5); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-family: inherit; transition: all 0.2s; }
.msg-bar .send-btn:hover { transform: scale(1.05); }

/* Toast */
.toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(20px); padding: 10px 20px; border-radius: 10px; font-size: 12px; opacity: 0; transition: all 0.3s; z-index: 2000; backdrop-filter: blur(10px); }
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.toast.success { background: rgba(26,58,42,0.9); color: #6bcb77; border: 1px solid rgba(42,90,58,0.5); }
.toast.info { background: rgba(26,42,58,0.9); color: #4d96ff; border: 1px solid rgba(42,58,90,0.5); }

/* Detail Modal */
.detail-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1500; justify-content: center; align-items: center; backdrop-filter: blur(4px); }
.detail-overlay.visible { display: flex; }
.detail-panel { background: linear-gradient(180deg, #12161f, #0d1117); border: 1px solid rgba(77,150,255,0.15); border-radius: 16px; width: 540px; max-width: 92vw; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
.detail-header { display: flex; align-items: center; gap: 16px; padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.detail-header img { width: 64px; height: 64px; border-radius: 50%; border: 3px solid; object-fit: cover; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
.detail-header .info h2 { font-size: 18px; margin-bottom: 4px; font-weight: 700; }
.detail-header .info .sub { font-size: 12px; color: #888; }
.detail-header .close-btn { margin-left: auto; font-size: 20px; cursor: pointer; color: #555; padding: 8px; transition: color 0.2s; }
.detail-header .close-btn:hover { color: #fff; }
.detail-section { padding: 14px 20px; border-bottom: 1px solid rgba(255,255,255,0.03); }
.detail-section h3 { font-size: 12px; color: rgba(77,150,255,0.8); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 500; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.detail-stat { background: rgba(26,31,46,0.5); border-radius: 8px; padding: 10px; border: 1px solid rgba(255,255,255,0.03); }
.detail-stat .label { font-size: 10px; color: #666; margin-bottom: 4px; }
.detail-stat .value { font-size: 16px; font-weight: 700; }
.detail-stat .bar { height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; margin-top: 6px; overflow: hidden; }
.detail-stat .bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }

/* Task progress in detail */
.detail-task { background: rgba(255,217,61,0.05); border: 1px solid rgba(255,217,61,0.15); border-radius: 10px; padding: 12px; }
.detail-task .task-title { font-size: 13px; font-weight: 600; color: #ffd93d; }
.detail-task .task-desc { font-size: 11px; color: #999; margin-top: 4px; }
.detail-task .task-progress { margin-top: 8px; }
.detail-task .task-progress .bar { height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
.detail-task .task-progress .bar-fill { height: 100%; background: linear-gradient(90deg, #ffd93d, #ff9800); border-radius: 3px; transition: width 0.5s; }
.detail-task .task-meta { display: flex; justify-content: space-between; margin-top: 6px; font-size: 10px; color: #888; }
.detail-task .challenge { margin-top: 6px; padding: 6px 10px; background: rgba(255,68,68,0.08); border: 1px solid rgba(255,68,68,0.15); border-radius: 6px; font-size: 11px; color: #ff6b6b; }

.detail-values { background: rgba(26,31,46,0.5); border-radius: 8px; padding: 12px; font-size: 13px; line-height: 1.6; border: 1px solid rgba(255,255,255,0.03); }
.detail-values .original { color: #555; font-size: 11px; margin-top: 6px; font-style: italic; }
.detail-memory { background: rgba(26,31,46,0.5); border-radius: 8px; padding: 10px; margin-bottom: 6px; font-size: 12px; border: 1px solid rgba(255,255,255,0.03); }
.detail-memory .emotion { display: inline-block; padding: 1px 6px; border-radius: 10px; font-size: 10px; margin-left: 6px; }
.detail-memory .emotion.positive { background: rgba(107,203,119,0.15); color: #6bcb77; }
.detail-memory .emotion.negative { background: rgba(255,107,107,0.15); color: #ff6b6b; }
.detail-memory .emotion.neutral { background: rgba(255,217,61,0.15); color: #ffd93d; }
.detail-bond { display: flex; align-items: center; gap: 10px; background: rgba(26,31,46,0.5); border-radius: 8px; padding: 10px; margin-bottom: 6px; border: 1px solid rgba(255,255,255,0.03); }
.detail-bond .bond-label { font-size: 12px; font-weight: 600; }
.detail-bond .bond-bars { flex: 1; font-size: 10px; }
.detail-bond .bond-bar { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
.detail-bond .bond-bar .bar { flex: 1; height: 3px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; }
.detail-bond .bond-bar .bar-fill { height: 100%; border-radius: 2px; }

/* Gallery */
.gallery-content { flex: 1; overflow-y: auto; padding: 10px; display: none; min-height: 0; }
.gallery-content.visible { display: flex; flex-wrap: wrap; gap: 10px; align-content: flex-start; }
.gallery-item { width: calc(50% - 5px); background: rgba(26,31,46,0.5); border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.05); transition: all 0.3s; }
.gallery-item:hover { border-color: rgba(77,150,255,0.3); transform: translateY(-2px); }
.gallery-item img { width: 100%; aspect-ratio: 1; object-fit: cover; }
.gallery-item .caption { padding: 8px; font-size: 11px; }
.gallery-item .caption .bot-name { color: #4d96ff; font-weight: 600; }
.gallery-item .caption .time { color: #555; font-size: 10px; }

/* Modal */
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; backdrop-filter: blur(4px); }
.modal-overlay.visible { display: flex; }
.modal { background: linear-gradient(180deg, #12161f, #0d1117); border: 1px solid rgba(77,150,255,0.15); border-radius: 16px; padding: 24px; width: 420px; max-width: 90vw; }
.modal h2 { font-size: 16px; margin-bottom: 16px; color: #ffd93d; }
.modal label { display: block; font-size: 11px; color: #666; margin-top: 12px; margin-bottom: 4px; }
.modal input, .modal select, .modal textarea { width: 100%; padding: 8px 12px; font-size: 12px; background: rgba(13,17,23,0.8); color: #e0e0e0; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; outline: none; font-family: inherit; }
.modal input:focus, .modal select:focus, .modal textarea:focus { border-color: rgba(77,150,255,0.4); }
.modal textarea { height: 80px; resize: vertical; }
.modal .modal-btns { display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end; }
.modal .modal-btn { padding: 8px 20px; font-size: 12px; border-radius: 8px; cursor: pointer; border: none; font-family: inherit; transition: all 0.2s; }
.modal .modal-btn.cancel { background: rgba(51,51,51,0.5); color: #aaa; }
.modal .modal-btn.confirm { background: linear-gradient(135deg, #4d96ff, #3a7bd5); color: #fff; }
.modal .modal-btn:hover { transform: scale(1.05); }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
</head>
<body>

<div class="header">
    <h1><span class="city">SHENZHEN SURVIVAL</span> <span class="ver">v7</span></h1>
    <div class="clock" id="clock">Loading...</div>
    <div class="controls">
        <button class="btn" onclick="showAddBotModal()">+ 新居民</button>
        <button class="btn" onclick="switchToGallery()">📸 照片墙</button>
    </div>
</div>

<div class="main">
    <div class="left-panel">
        <div class="map-container">
            <div class="map-bg night" id="map"></div>
        </div>
        <div class="cards-container" id="cards"></div>
    </div>
    <div class="right-panel">
        <div class="log-tabs" id="logTabs">
            <div class="log-tab active" data-log="world_engine" onclick="switchLog('world_engine', this)">🌍 世界</div>
        </div>
        <div class="view-toggle" id="viewToggle">
            <button class="view-btn active" id="btnLogView" onclick="setView('log')">📋 日志</button>
            <button class="view-btn" id="btnChatView" onclick="setView('chat')">💬 对话</button>
        </div>
        <div class="log-content" id="logContent"></div>
        <div class="chat-content" id="chatContent"></div>
        <div class="gallery-content" id="galleryContent"></div>
        <div class="msg-bar" id="msgBar">
            <select class="sender-select" id="senderAlias">
                <option value="一个路人">路人</option>
                <option value="隔壁邻居">邻居</option>
                <option value="一个神秘的声音">神秘声音</option>
                <option value="微信好友">微信好友</option>
                <option value="同事">同事</option>
                <option value="老同学">老同学</option>
                <option value="快递小哥">快递</option>
                <option value="房东">房东</option>
                <option value="父亲">父亲 🔴</option>
                <option value="母亲">母亲 🔴</option>
                <option value="老板">老板</option>
            </select>
            <input type="text" id="msgInput" placeholder="以伪装身份给TA发消息..." onkeydown="if(event.key==='Enter')sendMsg()">
            <button class="send-btn" onclick="sendMsg()">发送</button>
        </div>
    </div>
</div>

<div class="toast" id="toast"></div>

<div class="detail-overlay" id="detailOverlay" onclick="if(event.target===this)hideDetail()">
    <div class="detail-panel" id="detailPanel"></div>
</div>

<div class="modal-overlay" id="addBotModal">
    <div class="modal">
        <h2>🚌 新居民来深圳了！</h2>
        <label>Bot ID</label>
        <input type="text" id="newBotId" placeholder="bot_11">
        <label>落脚点</label>
        <select id="newBotLocation">
            <option value="宝安城中村">宝安城中村</option>
            <option value="南山科技园">南山科技园</option>
            <option value="华强北">华强北</option>
            <option value="东门老街">东门老街</option>
            <option value="福田CBD">福田CBD</option>
            <option value="南山公寓">南山公寓</option>
            <option value="深圳湾公园">深圳湾公园</option>
        </select>
        <label>姓名</label>
        <input type="text" id="newBotName" placeholder="角色名字">
        <label>角色</label>
        <input type="text" id="newBotRole" placeholder="如：外卖骑手">
        <label>人设</label>
        <textarea id="newBotSoul" placeholder="性格、背景、来深圳的原因..."></textarea>
        <div class="modal-btns">
            <button class="modal-btn cancel" onclick="hideAddBotModal()">取消</button>
            <button class="modal-btn confirm" onclick="addBot()">创建</button>
        </div>
    </div>
</div>
"""
    return HTMLResponse(content=html + r"""
<script>
const BOTS_INIT = """ + bots_json + r""";
const LOCATIONS = """ + locations_json + r""";
let BOTS = [...BOTS_INIT];
let currentLog = 'world_engine';
let currentBotId = null;
let currentView = 'log';
let worldState = null;
let godMessages = [];

function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + (type || 'success') + ' show';
    setTimeout(() => t.classList.remove('show'), 3000);
}

function getBotName(botId) {
    const bot = BOTS.find(b => b.id === botId);
    return bot ? bot.name : botId;
}

function getAvatarUrl(botId) {
    return '/avatars/' + botId + '.jpg';
}

// ===== MAP =====
function initMap() {
    const map = document.getElementById('map');

    // Add decorative roads
    const roads = [
        {x: 10, y: 40, w: 80, h: 2, cls: 'h'},
        {x: 30, y: 20, w: 2, h: 60, cls: 'v'},
        {x: 55, y: 15, w: 2, h: 70, cls: 'v'},
        {x: 10, y: 60, w: 70, h: 2, cls: 'h'},
        {x: 70, y: 20, w: 2, h: 50, cls: 'v'},
    ];
    roads.forEach(r => {
        const el = document.createElement('div');
        el.className = 'map-road ' + r.cls;
        el.style.left = r.x + '%'; el.style.top = r.y + '%';
        if (r.cls === 'h') { el.style.width = r.w + '%'; }
        else { el.style.height = r.h + '%'; }
        map.appendChild(el);
    });

    // Add stars (for night)
    for (let i = 0; i < 30; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 40 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        star.style.width = (1 + Math.random() * 2) + 'px';
        star.style.height = star.style.width;
        map.appendChild(star);
    }

    // Add location zones
    for (const [name, pos] of Object.entries(LOCATIONS)) {
        const zone = document.createElement('div');
        zone.className = 'loc-zone ' + pos.type;
        zone.style.left = pos.x + '%'; zone.style.top = pos.y + '%';
        zone.style.width = '70px'; zone.style.height = '50px';
        zone.innerHTML = '<span class="loc-icon">' + pos.icon + '</span>' +
            '<span class="loc-name">' + name + '</span>' +
            '<span class="loc-count" id="loccount-' + name + '"></span>';
        map.appendChild(zone);
    }

    BOTS.forEach(bot => addBotToMap(bot));
}

function addBotToMap(bot) {
    const map = document.getElementById('map');
    if (document.getElementById('map-' + bot.id)) return;
    const img = document.createElement('img');
    img.className = 'bot-avatar-map';
    img.id = 'map-' + bot.id;
    img.src = getAvatarUrl(bot.id);
    img.style.borderColor = bot.color;
    img.title = bot.name;
    img.onclick = () => showDetail(bot.id);
    img.onerror = function() { this.style.background = bot.color; this.src = ''; };
    const defaultPos = LOCATIONS['宝安城中村'];
    img.style.left = defaultPos.x + '%'; img.style.top = defaultPos.y + '%';
    map.appendChild(img);
}

function updateMapTime(hour) {
    const map = document.getElementById('map');
    map.classList.remove('day', 'night', 'sunset', 'dawn');
    if (hour >= 7 && hour < 17) map.classList.add('day');
    else if (hour >= 17 && hour < 20) map.classList.add('sunset');
    else if (hour >= 20 || hour < 5) map.classList.add('night');
    else map.classList.add('dawn');

    // Toggle star visibility
    const stars = map.querySelectorAll('.star');
    const showStars = (hour >= 20 || hour < 5);
    stars.forEach(s => s.style.display = showStars ? 'block' : 'none');
}

// ===== CARDS =====
function initCards() {
    const container = document.getElementById('cards');
    container.innerHTML = '';
    BOTS.forEach(bot => addBotCard(bot));
}

function addBotCard(bot) {
    const container = document.getElementById('cards');
    if (document.getElementById('card-' + bot.id)) return;
    const card = document.createElement('div');
    card.className = 'bot-card';
    card.id = 'card-' + bot.id;
    card.onclick = () => showDetail(bot.id);
    card.innerHTML = '<span class="sleep-badge" id="sleepbadge-' + bot.id + '"></span>' +
        '<img src="' + getAvatarUrl(bot.id) + '" style="border-color:' + bot.color + '" onerror="this.style.background=\'' + bot.color + '\';this.src=\'\';">' +
        '<div class="name" style="color:' + bot.color + '">' + bot.name + '</div>' +
        '<div class="role">' + bot.role + '</div>' +
        '<div class="stats">' +
        '<div class="hp-bar"><div class="hp-fill" id="hp-' + bot.id + '" style="width:100%;background:' + bot.color + '"></div></div>' +
        '<div class="stat-row"><span>❤️</span><span id="hpval-' + bot.id + '">100</span></div>' +
        '<div class="stat-row"><span>💰</span><span id="money-' + bot.id + '">500</span></div>' +
        '<div class="stat-row"><span>📍</span><span id="loc-' + bot.id + '" style="font-size:9px">...</span></div>' +
        '</div>' +
        '<div class="task-badge" id="task-' + bot.id + '"></div>' +
        '<div class="detail-btn" onclick="event.stopPropagation();showDetail(\'' + bot.id + '\')">详情</div>';
    container.appendChild(card);
}

function addBotTab(bot) {
    const tabs = document.getElementById('logTabs');
    if (tabs.querySelector('[data-log="' + bot.id + '"]')) return;
    const tab = document.createElement('div');
    tab.className = 'log-tab';
    tab.dataset.log = bot.id;
    tab.textContent = bot.name;
    tab.style.color = bot.color;
    tab.onclick = function() { switchLog(bot.id, this); };
    tabs.appendChild(tab);
}

function initTabs() { BOTS.forEach(bot => addBotTab(bot)); }

// ===== VIEW SWITCHING =====
function setView(view) {
    currentView = view;
    document.getElementById('btnLogView').classList.toggle('active', view === 'log');
    document.getElementById('btnChatView').classList.toggle('active', view === 'chat');
    document.getElementById('logContent').style.display = view === 'log' ? 'block' : 'none';
    document.getElementById('chatContent').style.display = view === 'chat' ? 'block' : 'none';
    document.getElementById('galleryContent').style.display = 'none';
    document.getElementById('galleryContent').classList.remove('visible');
    if (view === 'chat') fetchChat();
    else fetchLog();
}

function switchToGallery() {
    currentView = 'gallery';
    document.getElementById('logContent').style.display = 'none';
    document.getElementById('chatContent').style.display = 'none';
    document.getElementById('galleryContent').style.display = 'flex';
    document.getElementById('galleryContent').classList.add('visible');
    document.getElementById('msgBar').classList.remove('visible');
    document.getElementById('viewToggle').classList.remove('visible');
    document.querySelectorAll('.log-tab').forEach(t => t.classList.remove('active'));
    fetchGallery();
}

function switchLog(logName, tabEl) {
    currentLog = logName;
    currentBotId = logName.startsWith('bot_') ? logName : null;
    document.querySelectorAll('.log-tab').forEach(t => t.classList.remove('active'));
    if (tabEl) tabEl.classList.add('active');
    else document.querySelectorAll('.log-tab').forEach(t => { if (t.dataset.log === logName) t.classList.add('active'); });
    document.querySelectorAll('.bot-card').forEach(c => c.classList.remove('active'));
    const card = document.getElementById('card-' + logName);
    if (card) card.classList.add('active');
    document.getElementById('galleryContent').style.display = 'none';
    document.getElementById('galleryContent').classList.remove('visible');
    if (currentBotId) {
        document.getElementById('msgBar').classList.add('visible');
        document.getElementById('viewToggle').classList.add('visible');
    } else {
        document.getElementById('msgBar').classList.remove('visible');
        document.getElementById('viewToggle').classList.remove('visible');
        currentView = 'log';
        document.getElementById('logContent').style.display = 'block';
        document.getElementById('chatContent').style.display = 'none';
    }
    if (currentView === 'chat' && currentBotId) fetchChat();
    else { currentView = 'log'; setView('log'); fetchLog(); }
}

// ===== DATA FETCHING =====
function classifyLine(line) {
    if (line.includes('[内心独白]') || line.includes('THINK')) return 'inner';
    if (line.includes('[决策]') || line.includes('[行动]')) return 'action';
    if (line.includes('[结果]') || line.includes('成功') || line.includes('赚了')) return 'result';
    if (line.includes('[消息]') || line.includes('说:') || line.includes('上帝视角')) return 'message';
    if (line.includes('死亡') || line.includes('DEAD')) return 'death';
    if (line.includes('ERROR') || line.includes('失败')) return 'error';
    if (line.includes('[价值观变化]')) return 'values';
    if (line.includes('[核心记忆]') || line.includes('⭐')) return 'memory';
    if (line.includes('[关系更新]')) return 'bond';
    if (line.includes('任务') || line.includes('工作中') || line.includes('难点')) return 'task';
    return '';
}

async function fetchLog() {
    if (currentView !== 'log') return;
    try {
        const resp = await fetch('/api/logs/' + currentLog);
        const data = await resp.json();
        const container = document.getElementById('logContent');
        container.innerHTML = data.lines.map(line => {
            const cls = classifyLine(line);
            return '<div class="log-line ' + cls + '">' + line.replace(/</g, '&lt;').trim() + '</div>';
        }).join('');
        container.scrollTop = container.scrollHeight;
    } catch(e) {}
}

async function fetchChat() {
    if (!currentBotId || currentView !== 'chat') return;
    try {
        const resp = await fetch('/api/messages/' + currentBotId);
        const data = await resp.json();
        const container = document.getElementById('chatContent');
        const msgs = data.messages || [];
        let html = '';
        if (msgs.length === 0) {
            html = '<div style="text-align:center;color:#444;padding:40px;font-size:12px;">暂无对话记录</div>';
        } else {
            msgs.forEach(m => {
                const isGod = godMessages.some(g => g.msg === m.msg && g.to === m.to);
                const isFromMe = m.from === currentBotId;
                if (isFromMe) {
                    html += '<div class="chat-bubble outgoing"><div class="sender">' + getBotName(currentBotId) + ' → ' + (m.to === 'public' ? '公告板' : getBotName(m.to)) + '</div><div>' + m.msg + '</div><div class="time">tick ' + m.tick + '</div></div>';
                } else if (m.to === currentBotId || m.to === 'public') {
                    const cls = isGod ? 'incoming god' : 'incoming';
                    const priority = m.priority === 'high' ? ' 🔴' : '';
                    html += '<div class="chat-bubble ' + cls + '"><div class="sender">' + m.from + (isGod ? ' 👁️' : '') + priority + '</div><div>' + m.msg + '</div><div class="time">tick ' + m.tick + '</div></div>';
                }
            });
        }
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
    } catch(e) {}
}

async function fetchGallery() {
    try {
        const resp = await fetch('/api/gallery');
        const data = await resp.json();
        const container = document.getElementById('galleryContent');
        const items = data.gallery || [];
        if (items.length === 0) {
            container.innerHTML = '<div style="text-align:center;color:#444;padding:40px;font-size:12px;width:100%;">📸 还没有人拍过照片</div>';
            return;
        }
        container.innerHTML = items.reverse().map(item => {
            return '<div class="gallery-item"><img src="/selfies/' + item.filename + '" onerror="this.src=\'' + getAvatarUrl(item.bot_id) + '\'" onclick="window.open(\'/selfies/' + item.filename + '\')"><div class="caption"><span class="bot-name">' + getBotName(item.bot_id) + '</span> ' + (item.prompt || '').substring(0, 40) + '<br><span class="time">' + item.time + '</span></div></div>';
        }).join('');
    } catch(e) {}
}

async function fetchWorld() {
    try {
        const resp = await fetch('/api/world');
        worldState = await resp.json();
        if (worldState.error) return;

        // Update time & map
        if (worldState.time) {
            const h = worldState.time.virtual_hour;
            let icon = '☀️';
            if (h >= 22 || h < 6) icon = '🌙';
            else if (h >= 18) icon = '🌆';
            else if (h < 8) icon = '🌅';
            document.getElementById('clock').textContent = icon + ' ' + worldState.time.virtual_datetime + ' | Day ' + worldState.time.virtual_day + ' | Tick ' + worldState.time.tick;
            updateMapTime(h);
        }

        // Update location counts
        if (worldState.locations) {
            for (const [name, loc] of Object.entries(worldState.locations)) {
                const countEl = document.getElementById('loccount-' + name);
                if (countEl) {
                    const n = (loc.bots || []).length;
                    countEl.textContent = n > 0 ? n + '人' : '';
                }
            }
        }

        // Update bots
        if (worldState.bots) {
            for (const botId of Object.keys(worldState.bots)) {
                if (!BOTS.find(b => b.id === botId)) {
                    const newBot = { id: botId, name: botId, role: '新居民', color: '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0') };
                    BOTS.push(newBot);
                    addBotToMap(newBot);
                    addBotCard(newBot);
                    addBotTab(newBot);
                }
            }
            for (const [botId, bot] of Object.entries(worldState.bots)) {
                // Map avatar position
                const avatar = document.getElementById('map-' + botId);
                if (avatar && bot.location && LOCATIONS[bot.location]) {
                    const pos = LOCATIONS[bot.location];
                    const botsAtLoc = Object.entries(worldState.bots).filter(([_, b]) => b.location === bot.location);
                    const idx = botsAtLoc.findIndex(([id]) => id === botId);
                    const angle = (idx / Math.max(botsAtLoc.length, 1)) * Math.PI * 2;
                    const radius = botsAtLoc.length > 1 ? 3.5 : 0;
                    avatar.style.left = (pos.x + Math.cos(angle) * radius) + '%';
                    avatar.style.top = (pos.y + 6 + Math.sin(angle) * radius) + '%';

                    avatar.classList.remove('dead', 'sleeping', 'working');
                    if (bot.status === 'dead') avatar.classList.add('dead');
                    else if (bot.is_sleeping) avatar.classList.add('sleeping');
                    else if (bot.current_task && bot.current_task.status === 'in_progress') avatar.classList.add('working');

                    // Zzz
                    const oldZzz = document.getElementById('zzz-' + botId);
                    if (oldZzz) oldZzz.remove();
                    if (bot.is_sleeping && bot.status === 'alive') {
                        const zzz = document.createElement('span');
                        zzz.className = 'sleep-zzz';
                        zzz.id = 'zzz-' + botId;
                        zzz.textContent = '💤';
                        zzz.style.left = avatar.style.left;
                        zzz.style.top = (parseFloat(avatar.style.top) - 4) + '%';
                        document.getElementById('map').appendChild(zzz);
                    }
                }

                // Card stats
                const hpBar = document.getElementById('hp-' + botId);
                const hpVal = document.getElementById('hpval-' + botId);
                const moneyVal = document.getElementById('money-' + botId);
                const locVal = document.getElementById('loc-' + botId);
                const sleepBadge = document.getElementById('sleepbadge-' + botId);
                const taskBadge = document.getElementById('task-' + botId);

                if (hpBar) {
                    hpBar.style.width = bot.hp + '%';
                    if (bot.hp < 30) hpBar.style.background = '#ff4444';
                    else if (bot.hp < 60) hpBar.style.background = '#ffd93d';
                }
                if (hpVal) hpVal.textContent = bot.hp;
                if (moneyVal) moneyVal.textContent = '¥' + bot.money;
                if (locVal) locVal.textContent = bot.location || '...';
                if (sleepBadge) sleepBadge.textContent = bot.is_sleeping ? '💤' : (bot.status === 'dead' ? '💀' : '');

                // Task badge
                if (taskBadge) {
                    const task = bot.current_task;
                    if (task && task.status === 'in_progress') {
                        const pct = Math.round((task.progress || 0) / task.duration * 100);
                        taskBadge.textContent = '🔨 ' + task.task_name + ' ' + pct + '%';
                        taskBadge.style.color = task.challenge ? '#ff6b6b' : '#ffd93d';
                    } else if (task && task.status === 'completed') {
                        taskBadge.textContent = '✅ ' + (task.task_name || '');
                        taskBadge.style.color = '#6bcb77';
                    } else if (task && task.status === 'failed') {
                        taskBadge.textContent = '❌ ' + (task.task_name || '');
                        taskBadge.style.color = '#ff6b6b';
                    } else {
                        taskBadge.textContent = '';
                    }
                }
            }
        }
    } catch(e) {}
}

// ===== DETAIL PANEL =====
async function showDetail(botId) {
    const panel = document.getElementById('detailPanel');
    const overlay = document.getElementById('detailOverlay');
    const bot = BOTS.find(b => b.id === botId) || { id: botId, name: botId, role: '?', color: '#888' };

    panel.innerHTML = '<div style="padding:40px;text-align:center;color:#555;">加载中...</div>';
    overlay.classList.add('visible');

    try {
        const resp = await fetch('/api/bot/' + botId + '/detail');
        const d = await resp.json();
        if (d.error) { panel.innerHTML = '<div style="padding:40px;text-align:center;color:#ff4444;">' + d.error + '</div>'; return; }

        let html = '';
        // Header
        html += '<div class="detail-header"><img src="' + getAvatarUrl(botId) + '" style="border-color:' + bot.color + '" onerror="this.style.background=\'' + bot.color + '\'">';
        html += '<div class="info"><h2 style="color:' + bot.color + '">' + bot.name + '</h2>';
        html += '<div class="sub">' + bot.role + ' | ' + d.location + (d.is_sleeping ? ' 💤' : '') + (d.status === 'dead' ? ' 💀' : '') + '</div></div>';
        html += '<span class="close-btn" onclick="hideDetail()">&times;</span></div>';

        // Current Task
        const task = d.current_task;
        if (task && task.status === 'in_progress') {
            const pct = Math.round((task.progress || 0) / task.duration * 100);
            html += '<div class="detail-section"><h3>🔨 当前任务</h3>';
            html += '<div class="detail-task">';
            html += '<div class="task-title">' + task.job_title + ' → ' + task.task_name + '</div>';
            html += '<div class="task-desc">' + task.task_desc + '</div>';
            html += '<div class="task-progress"><div class="bar"><div class="bar-fill" style="width:' + pct + '%"></div></div></div>';
            html += '<div class="task-meta"><span>进度: ' + (task.progress||0) + '/' + task.duration + ' (' + pct + '%)</span><span>难度: ' + '⭐'.repeat(Math.max(1, Math.round(task.difficulty * 5))) + '</span></div>';
            if (task.challenge) {
                html += '<div class="challenge">⚠️ 遇到难点: ' + task.challenge + '</div>';
            }
            html += '</div></div>';
        } else if (task && task.status === 'completed') {
            html += '<div class="detail-section"><h3>✅ 上一个任务</h3>';
            html += '<div class="detail-task" style="border-color:rgba(107,203,119,0.3);background:rgba(107,203,119,0.05);">';
            html += '<div class="task-title" style="color:#6bcb77;">' + task.task_name + '</div>';
            html += '<div class="task-desc">' + (task.result || '') + '</div>';
            html += '</div></div>';
        } else if (task && task.status === 'failed') {
            html += '<div class="detail-section"><h3>❌ 上一个任务</h3>';
            html += '<div class="detail-task" style="border-color:rgba(255,107,107,0.3);background:rgba(255,107,107,0.05);">';
            html += '<div class="task-title" style="color:#ff6b6b;">' + task.task_name + '</div>';
            html += '<div class="task-desc">' + (task.result || '') + '</div>';
            html += '</div></div>';
        }

        // Stats
        html += '<div class="detail-section"><h3>📊 基础数值</h3><div class="detail-grid">';
        const stats = [
            { label: '❤️ 生命值', value: d.hp, max: 100, color: d.hp < 30 ? '#ff4444' : d.hp < 60 ? '#ffd93d' : '#6bcb77' },
            { label: '⚡ 能量', value: d.energy, max: 100, color: '#4d96ff' },
            { label: '🍚 饱腹度', value: d.satiety, max: 100, color: '#ff9800' },
            { label: '💰 金钱', value: '¥' + d.money, color: '#ffd93d' },
        ];
        stats.forEach(s => {
            html += '<div class="detail-stat"><div class="label">' + s.label + '</div><div class="value" style="color:' + s.color + '">' + s.value + (s.max ? '/' + s.max : '') + '</div>';
            if (s.max) html += '<div class="bar"><div class="bar-fill" style="width:' + (typeof s.value === 'number' ? s.value : 0) + '%;background:' + s.color + '"></div></div>';
            html += '</div>';
        });
        html += '</div></div>';

        // Skills
        html += '<div class="detail-section"><h3>🎯 技能</h3><div class="detail-grid">';
        const skillNames = { programming: '💻 编程', social: '🤝 社交', hardware: '🔧 硬件', analysis: '📈 分析', art: '🎨 艺术' };
        for (const [k, v] of Object.entries(d.skills || {})) {
            html += '<div class="detail-stat"><div class="label">' + (skillNames[k] || k) + '</div><div class="value">' + v + '</div><div class="bar"><div class="bar-fill" style="width:' + v + '%;background:#4d96ff"></div></div></div>';
        }
        html += '</div></div>';

        // Desires
        const desires = d.desires || {};
        const desireNames = { lust: '🔥 性欲', power: '👑 权力欲', greed: '💰 物欲', vanity: '🪞 虚荣心', security: '🛡️ 安全感' };
        const desireColors = { lust: '#ff4d6d', power: '#9b59b6', greed: '#f39c12', vanity: '#e91e63', security: '#3498db' };
        html += '<div class="detail-section"><h3>🔥 内心欲望</h3><div class="detail-grid">';
        for (const [k, v] of Object.entries(desires)) {
            const val = Math.round(v);
            const color = desireColors[k] || '#888';
            const level = val > 70 ? ' (强烈!)' : val > 40 ? ' (中等)' : ' (微弱)';
            html += '<div class="detail-stat"><div class="label">' + (desireNames[k] || k) + level + '</div><div class="value">' + val + '</div><div class="bar"><div class="bar-fill" style="width:' + val + '%;background:' + color + '"></div></div></div>';
        }
        html += '</div></div>';

        // Values
        const values = d.values || {};
        const currentValues = values.current || '(尚未形成)';
        const originalValues = values.original || '';
        html += '<div class="detail-section"><h3>💭 价值观</h3>';
        html += '<div class="detail-values">' + currentValues;
        if (originalValues && originalValues !== currentValues) {
            html += '<div class="original">初始: ' + originalValues + '</div>';
        }
        if (values.shifts && values.shifts.length > 0) {
            html += '<div style="margin-top:8px;font-size:11px;color:#e040fb;">已经历 ' + values.shifts.length + ' 次价值观变化</div>';
        }
        html += '</div></div>';

        // Core Memories
        const memories = d.core_memories || [];
        html += '<div class="detail-section"><h3>⭐ 核心记忆 (' + memories.length + ')</h3>';
        if (memories.length === 0) {
            html += '<div style="color:#444;font-size:11px;">还没有形成核心记忆</div>';
        } else {
            memories.forEach(m => {
                const emotionCls = m.emotion || 'neutral';
                const emotionLabel = { positive: '😊 积极', negative: '😢 消极', neutral: '😐 中性' }[emotionCls] || emotionCls;
                html += '<div class="detail-memory">' + m.summary + '<span class="emotion ' + emotionCls + '">' + emotionLabel + '</span><div style="font-size:10px;color:#444;margin-top:4px;">' + (m.time || '') + '</div></div>';
            });
        }
        html += '</div>';

        // Emotional Bonds
        const bonds = d.emotional_bonds || {};
        const bondKeys = Object.keys(bonds);
        html += '<div class="detail-section"><h3>💕 情感关系 (' + bondKeys.length + ')</h3>';
        if (bondKeys.length === 0) {
            html += '<div style="color:#444;font-size:11px;">还没有建立深层关系</div>';
        } else {
            bondKeys.forEach(target => {
                const b = bonds[target];
                html += '<div class="detail-bond"><div class="bond-label" style="min-width:60px;">' + getBotName(target) + '<br><span style="font-size:10px;color:#666;">' + (b.label || '?') + '</span></div>';
                html += '<div class="bond-bars">';
                html += '<div class="bond-bar"><span style="min-width:30px;color:#6bcb77;">信任</span><div class="bar"><div class="bar-fill" style="width:' + (b.trust || 0) + '%;background:#6bcb77"></div></div><span>' + (b.trust || 0) + '</span></div>';
                html += '<div class="bond-bar"><span style="min-width:30px;color:#4d96ff;">亲密</span><div class="bar"><div class="bar-fill" style="width:' + (b.closeness || 0) + '%;background:#4d96ff"></div></div><span>' + (b.closeness || 0) + '</span></div>';
                html += '<div class="bond-bar"><span style="min-width:30px;color:#ff4444;">敌意</span><div class="bar"><div class="bar-fill" style="width:' + (b.hostility || 0) + '%;background:#ff4444"></div></div><span>' + (b.hostility || 0) + '</span></div>';
                html += '</div></div>';
            });
        }
        html += '</div>';

        // Family
        const family = d.family || {};
        if (Object.keys(family).length > 0) {
            html += '<div class="detail-section"><h3>👨‍👩‍👧 家庭</h3>';
            html += '<div class="detail-values">';
            if (family.role) html += '角色: ' + family.role + '<br>';
            if (family.parents) html += '父母: ' + family.parents.map(p => getBotName(p)).join(', ') + '<br>';
            if (family.children) html += '子女: ' + family.children.map(c => getBotName(c)).join(', ') + '<br>';
            html += '</div></div>';
        }

        // Inventory
        if (d.inventory && d.inventory.length > 0) {
            html += '<div class="detail-section"><h3>🎒 物品</h3>';
            html += '<div class="detail-values">' + d.inventory.join(', ') + '</div></div>';
        }

        // Selfie count
        if (d.selfie_count > 0) {
            html += '<div class="detail-section"><h3>📸 拍照: ' + d.selfie_count + ' 次</h3></div>';
        }

        panel.innerHTML = html;
    } catch(e) {
        panel.innerHTML = '<div style="padding:40px;text-align:center;color:#ff4444;">加载失败</div>';
    }
}

function hideDetail() {
    document.getElementById('detailOverlay').classList.remove('visible');
}

// ===== MESSAGING =====
async function sendMsg() {
    if (!currentBotId) return;
    const input = document.getElementById('msgInput');
    const alias = document.getElementById('senderAlias').value;
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    try {
        const resp = await fetch('/api/send_message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ target_id: currentBotId, message: msg, sender_alias: alias })
        });
        const result = await resp.json();
        if (result.error) { showToast('发送失败', 'info'); return; }
        godMessages.push({ msg, to: currentBotId, alias });
        const priorityNote = ['父亲','母亲','爸爸','妈妈'].includes(alias) ? ' (高优先级🔴)' : '';
        showToast('✅ 已发送给 ' + getBotName(currentBotId) + '（' + alias + '）' + priorityNote, 'success');
        if (currentView === 'chat') {
            const container = document.getElementById('chatContent');
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble incoming god';
            bubble.innerHTML = '<div class="sender">' + alias + ' 👁️' + priorityNote + '</div><div>' + msg + '</div><div class="time">刚刚</div>';
            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
        }
        if (currentView === 'log') setView('chat');
    } catch(e) { showToast('发送失败', 'info'); }
}

// ===== ADD BOT =====
function showAddBotModal() {
    document.getElementById('addBotModal').classList.add('visible');
    const maxId = BOTS.reduce((max, b) => { const n = parseInt(b.id.replace('bot_', '')); return isNaN(n) ? max : Math.max(max, n); }, 0);
    document.getElementById('newBotId').value = 'bot_' + (maxId + 1);
}
function hideAddBotModal() { document.getElementById('addBotModal').classList.remove('visible'); }

async function addBot() {
    const botId = document.getElementById('newBotId').value.trim();
    const location = document.getElementById('newBotLocation').value;
    const name = document.getElementById('newBotName').value.trim() || botId;
    const role = document.getElementById('newBotRole').value.trim() || '新居民';
    if (!botId) { alert('请输入Bot ID'); return; }
    try {
        const resp = await fetch('/api/add_bot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ bot_id: botId, location })
        });
        const result = await resp.json();
        if (result.error) { showToast('创建失败', 'info'); return; }
        const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
        const newBot = { id: botId, name, role, color };
        BOTS.push(newBot);
        addBotToMap(newBot);
        addBotCard(newBot);
        addBotTab(newBot);
        hideAddBotModal();
        showToast('🎉 ' + name + ' 已抵达 ' + location, 'success');
    } catch(e) { showToast('创建失败', 'info'); }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
    if (e.key === 'Escape') { hideDetail(); hideAddBotModal(); return; }
    const num = parseInt(e.key);
    if (num === 0) switchLog('world_engine', null);
    else if (num >= 1 && num <= 9) switchLog('bot_' + num, null);
});

// Init
initMap();
initCards();
initTabs();

setInterval(() => {
    if (currentView === 'log') fetchLog();
    else if (currentView === 'chat') fetchChat();
    else if (currentView === 'gallery') fetchGallery();
}, 3000);
setInterval(fetchWorld, 3000);
fetchLog();
fetchWorld();
</script>
</body>
</html>""")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
