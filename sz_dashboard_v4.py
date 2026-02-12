#!/usr/bin/env python3
import os, json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
import uvicorn, requests as req

app = FastAPI()

@app.get("/avatars/{filename}")
def get_avatar(filename: str):
    path = f"/home/ubuntu/bot_avatars/{filename}"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
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
        "宝安城中村": {"x": 15, "y": 35}, "南山科技园": {"x": 35, "y": 50},
        "南山公寓": {"x": 30, "y": 65}, "华强北": {"x": 55, "y": 40},
        "福田CBD": {"x": 65, "y": 55}, "东门老街": {"x": 75, "y": 35},
        "深圳湾公园": {"x": 45, "y": 80},
    }, ensure_ascii=False)

    html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>深圳生存模拟 - 实时监控 v4</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0a0e17; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; overflow: hidden; height: 100vh; }

.header { background: linear-gradient(135deg, #1a1f2e, #0d1117); padding: 8px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #2a3040; height: 50px; }
.header h1 { font-size: 18px; background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcb77, #4d96ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.header .clock { font-size: 14px; color: #ffd93d; font-family: monospace; }
.header .controls { display: flex; gap: 8px; }
.header .btn { padding: 4px 12px; font-size: 12px; border-radius: 6px; cursor: pointer; border: 1px solid #4d96ff; background: transparent; color: #4d96ff; transition: all 0.2s; }
.header .btn:hover { background: #4d96ff; color: #fff; }

.main { display: flex; height: calc(100vh - 50px); }
.left-panel { width: 45%; display: flex; flex-direction: column; border-right: 1px solid #2a3040; }
.map-container { flex: 1; position: relative; background: #0d1117; padding: 10px; min-height: 0; }
.map-bg { width: 100%; height: 100%; position: relative; background: linear-gradient(180deg, #0d1a2a 0%, #1a2a3a 100%); border-radius: 12px; border: 1px solid #2a3a4a; overflow: hidden; }
.location-dot { position: absolute; width: 10px; height: 10px; background: rgba(255,255,255,0.15); border-radius: 50%; transform: translate(-50%, -50%); }
.location-label { position: absolute; transform: translate(-50%, -50%); font-size: 11px; color: rgba(255,255,255,0.6); white-space: nowrap; pointer-events: none; text-shadow: 0 0 4px rgba(0,0,0,0.8); }
.bot-avatar-map { position: absolute; width: 36px; height: 36px; border-radius: 50%; border: 2px solid; cursor: pointer; transition: all 0.5s ease; transform: translate(-50%, -50%); box-shadow: 0 0 8px rgba(0,0,0,0.5); }
.bot-avatar-map:hover { transform: translate(-50%, -50%) scale(1.3); z-index: 100; }
.bot-avatar-map.dead { filter: grayscale(100%); opacity: 0.4; }
.bot-avatar-map.sleeping { animation: pulse-sleep 2s infinite; }
@keyframes pulse-sleep { 0%,100% { box-shadow: 0 0 8px rgba(0,0,0,0.5); } 50% { box-shadow: 0 0 16px rgba(100,100,255,0.6); } }
.sleep-zzz { position: absolute; font-size: 14px; pointer-events: none; animation: float-zzz 2s infinite; color: #aac; }
@keyframes float-zzz { 0% { opacity: 1; transform: translate(0,0); } 100% { opacity: 0; transform: translate(10px, -20px); } }

.cards-container { height: 180px; min-height: 180px; overflow-x: auto; overflow-y: hidden; display: flex; gap: 8px; padding: 8px 10px; background: #0d1117; white-space: nowrap; }
.bot-card { min-width: 120px; background: #1a1f2e; border-radius: 10px; padding: 8px; cursor: pointer; transition: all 0.2s; border: 1px solid #2a3040; display: flex; flex-direction: column; align-items: center; gap: 4px; position: relative; }
.bot-card:hover, .bot-card.active { border-color: #4d96ff; background: #1e2538; }
.bot-card img { width: 40px; height: 40px; border-radius: 50%; border: 2px solid; }
.bot-card .name { font-size: 12px; font-weight: bold; }
.bot-card .role { font-size: 10px; color: #888; }
.bot-card .stats { font-size: 10px; width: 100%; }
.bot-card .hp-bar { width: 100%; height: 4px; background: #333; border-radius: 2px; margin-top: 2px; }
.bot-card .hp-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.bot-card .stat-row { display: flex; justify-content: space-between; margin-top: 2px; }
.bot-card .sleep-badge { position: absolute; top: 4px; right: 4px; font-size: 12px; }
.bot-card .detail-btn { margin-top: 4px; padding: 2px 8px; font-size: 10px; background: #2a3550; color: #4d96ff; border: 1px solid #3a4560; border-radius: 4px; cursor: pointer; }
.bot-card .detail-btn:hover { background: #3a4570; }

.right-panel { flex: 1; display: flex; flex-direction: column; }
.log-tabs { display: flex; flex-wrap: wrap; gap: 4px; padding: 8px; background: #0d1117; border-bottom: 1px solid #2a3040; }
.log-tab { padding: 4px 10px; font-size: 11px; border-radius: 6px; cursor: pointer; background: #1a1f2e; color: #888; border: 1px solid #2a3040; transition: all 0.2s; }
.log-tab:hover { color: #fff; }
.log-tab.active { background: #2a3550; color: #fff; border-color: #4d96ff; }

.view-toggle { display: none; padding: 4px 8px; background: #0d1117; border-bottom: 1px solid #2a3040; gap: 4px; }
.view-toggle.visible { display: flex; }
.view-btn { padding: 3px 10px; font-size: 11px; border-radius: 4px; cursor: pointer; background: #1a1f2e; color: #888; border: 1px solid #2a3040; }
.view-btn.active { background: #2a3550; color: #fff; border-color: #4d96ff; }

.log-content { flex: 1; overflow-y: auto; padding: 10px; font-family: 'Fira Code', 'Consolas', monospace; font-size: 12px; line-height: 1.6; min-height: 0; }
.log-line { padding: 2px 0; word-wrap: break-word; }
.log-line.inner { color: #ffd93d; }
.log-line.action { color: #ff6b6b; }
.log-line.result { color: #6bcb77; }
.log-line.message { color: #4d96ff; }
.log-line.error { color: #ff4444; }
.log-line.death { color: #ff0000; animation: blink 0.5s infinite; }
.log-line.values { color: #e040fb; }
.log-line.memory { color: #ffab40; }
.log-line.bond { color: #40c4ff; }
@keyframes blink { 50% { opacity: 0.3; } }

.chat-content { flex: 1; overflow-y: auto; padding: 10px; display: none; min-height: 0; }
.chat-content.visible { display: block; }
.chat-bubble { max-width: 80%; padding: 8px 12px; border-radius: 12px; margin-bottom: 8px; font-size: 13px; line-height: 1.5; word-wrap: break-word; }
.chat-bubble.incoming { background: #1a2a3a; color: #e0e0e0; margin-right: auto; border-bottom-left-radius: 4px; }
.chat-bubble.outgoing { background: #2a4a6a; color: #e0e0e0; margin-left: auto; border-bottom-right-radius: 4px; }
.chat-bubble .sender { font-size: 10px; color: #888; margin-bottom: 3px; }
.chat-bubble .time { font-size: 9px; color: #555; margin-top: 3px; text-align: right; }
.chat-bubble.god { background: #3a2a5a; border: 1px solid #6a4a9a; }

.msg-bar { display: none; padding: 8px; background: #0d1117; border-top: 1px solid #2a3040; }
.msg-bar.visible { display: flex; gap: 6px; align-items: center; }
.msg-bar .sender-select { padding: 4px 8px; font-size: 11px; background: #1a1f2e; color: #e0e0e0; border: 1px solid #2a3040; border-radius: 6px; }
.msg-bar input { flex: 1; padding: 6px 10px; font-size: 12px; background: #1a1f2e; color: #e0e0e0; border: 1px solid #2a3040; border-radius: 6px; outline: none; }
.msg-bar input:focus { border-color: #4d96ff; }
.msg-bar .send-btn { padding: 6px 14px; font-size: 12px; background: #4d96ff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.msg-bar .send-btn:hover { background: #3a7bd5; }

.toast { position: fixed; bottom: 80px; right: 20px; padding: 10px 20px; border-radius: 8px; font-size: 13px; z-index: 2000; transition: all 0.3s; opacity: 0; transform: translateY(10px); pointer-events: none; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast.success { background: #1a3a2a; color: #6bcb77; border: 1px solid #2a5a3a; }
.toast.info { background: #1a2a3a; color: #4d96ff; border: 1px solid #2a3a5a; }

/* Detail Modal */
.detail-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); z-index: 1500; justify-content: center; align-items: center; }
.detail-overlay.visible { display: flex; }
.detail-panel { background: #12161f; border: 1px solid #2a3040; border-radius: 16px; width: 520px; max-width: 92vw; max-height: 85vh; overflow-y: auto; }
.detail-header { display: flex; align-items: center; gap: 16px; padding: 20px; border-bottom: 1px solid #2a3040; }
.detail-header img { width: 64px; height: 64px; border-radius: 50%; border: 3px solid; }
.detail-header .info h2 { font-size: 18px; margin-bottom: 4px; }
.detail-header .info .sub { font-size: 12px; color: #888; }
.detail-header .close-btn { margin-left: auto; font-size: 20px; cursor: pointer; color: #888; padding: 8px; }
.detail-header .close-btn:hover { color: #fff; }
.detail-section { padding: 16px 20px; border-bottom: 1px solid #1a2030; }
.detail-section h3 { font-size: 13px; color: #4d96ff; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.detail-stat { background: #1a1f2e; border-radius: 8px; padding: 10px; }
.detail-stat .label { font-size: 10px; color: #888; margin-bottom: 4px; }
.detail-stat .value { font-size: 16px; font-weight: bold; }
.detail-stat .bar { height: 4px; background: #333; border-radius: 2px; margin-top: 6px; }
.detail-stat .bar-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }
.detail-values { background: #1a1f2e; border-radius: 8px; padding: 12px; font-size: 13px; line-height: 1.6; }
.detail-values .original { color: #888; font-size: 11px; margin-top: 6px; }
.detail-memory { background: #1a1f2e; border-radius: 8px; padding: 10px; margin-bottom: 6px; font-size: 12px; }
.detail-memory .emotion { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; margin-left: 6px; }
.detail-memory .emotion.positive { background: #1a3a2a; color: #6bcb77; }
.detail-memory .emotion.negative { background: #3a1a1a; color: #ff6b6b; }
.detail-memory .emotion.neutral { background: #2a2a1a; color: #ffd93d; }
.detail-bond { display: flex; align-items: center; gap: 10px; background: #1a1f2e; border-radius: 8px; padding: 10px; margin-bottom: 6px; }
.detail-bond .bond-label { font-size: 12px; font-weight: bold; }
.detail-bond .bond-bars { flex: 1; font-size: 10px; }
.detail-bond .bond-bar { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
.detail-bond .bond-bar .bar { flex: 1; height: 3px; background: #333; border-radius: 2px; }
.detail-bond .bond-bar .bar-fill { height: 100%; border-radius: 2px; }
.detail-selfies { display: flex; gap: 8px; flex-wrap: wrap; }
.detail-selfies img { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; cursor: pointer; border: 1px solid #2a3040; }
.detail-selfies img:hover { border-color: #4d96ff; transform: scale(1.05); }

/* Gallery view */
.gallery-content { flex: 1; overflow-y: auto; padding: 10px; display: none; min-height: 0; }
.gallery-content.visible { display: flex; flex-wrap: wrap; gap: 10px; align-content: flex-start; }
.gallery-item { width: calc(50% - 5px); background: #1a1f2e; border-radius: 10px; overflow: hidden; border: 1px solid #2a3040; }
.gallery-item img { width: 100%; aspect-ratio: 1; object-fit: cover; }
.gallery-item .caption { padding: 8px; font-size: 11px; }
.gallery-item .caption .bot-name { color: #4d96ff; font-weight: bold; }
.gallery-item .caption .time { color: #666; font-size: 10px; }

/* Modal */
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; }
.modal-overlay.visible { display: flex; }
.modal { background: #1a1f2e; border: 1px solid #2a3040; border-radius: 16px; padding: 24px; width: 420px; max-width: 90vw; }
.modal h2 { font-size: 16px; margin-bottom: 16px; color: #ffd93d; }
.modal label { display: block; font-size: 12px; color: #888; margin-top: 12px; margin-bottom: 4px; }
.modal input, .modal select, .modal textarea { width: 100%; padding: 8px 12px; font-size: 13px; background: #0d1117; color: #e0e0e0; border: 1px solid #2a3040; border-radius: 8px; outline: none; }
.modal input:focus, .modal select:focus, .modal textarea:focus { border-color: #4d96ff; }
.modal textarea { height: 80px; resize: vertical; font-family: inherit; }
.modal .modal-btns { display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end; }
.modal .modal-btn { padding: 8px 20px; font-size: 13px; border-radius: 8px; cursor: pointer; border: none; }
.modal .modal-btn.cancel { background: #333; color: #aaa; }
.modal .modal-btn.confirm { background: #4d96ff; color: #fff; }
.modal .modal-btn:hover { opacity: 0.85; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0e17; }
::-webkit-scrollbar-thumb { background: #2a3040; border-radius: 3px; }
</style>
</head>
<body>

<div class="header">
    <h1>🏙️ 深圳生存模拟 SHENZHEN SURVIVAL v7</h1>
    <div class="clock" id="clock">虚拟时间: 加载中...</div>
    <div class="controls">
        <button class="btn" onclick="showAddBotModal()">+ 添加新居民</button>
        <button class="btn" onclick="switchToGallery()">📸 照片墙</button>
    </div>
</div>

<div class="main">
    <div class="left-panel">
        <div class="map-container">
            <div class="map-bg" id="map"></div>
        </div>
        <div class="cards-container" id="cards"></div>
    </div>
    <div class="right-panel">
        <div class="log-tabs" id="logTabs">
            <div class="log-tab active" data-log="world_engine" onclick="switchLog('world_engine', this)">🌍 世界引擎</div>
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
                <option value="一个路人">一个路人</option>
                <option value="隔壁邻居">隔壁邻居</option>
                <option value="一个神秘的声音">神秘声音</option>
                <option value="微信好友">微信好友</option>
                <option value="同事">同事</option>
                <option value="老同学">老同学</option>
                <option value="快递小哥">快递小哥</option>
                <option value="房东">房东</option>
                <option value="父亲">父亲</option>
                <option value="母亲">母亲</option>
                <option value="老板">老板</option>
            </select>
            <input type="text" id="msgInput" placeholder="以伪装身份给TA发消息..." onkeydown="if(event.key==='Enter')sendMsg()">
            <button class="send-btn" onclick="sendMsg()">发送</button>
        </div>
    </div>
</div>

<div class="toast" id="toast"></div>

<!-- Detail Modal -->
<div class="detail-overlay" id="detailOverlay" onclick="if(event.target===this)hideDetail()">
    <div class="detail-panel" id="detailPanel"></div>
</div>

<!-- Add Bot Modal -->
<div class="modal-overlay" id="addBotModal">
    <div class="modal">
        <h2>🚌 新居民来深圳了！</h2>
        <label>Bot ID (如 bot_11)</label>
        <input type="text" id="newBotId" placeholder="bot_11">
        <label>落脚点</label>
        <select id="newBotLocation">
            <option value="宝安城中村">宝安城中村（最便宜）</option>
            <option value="南山科技园">南山科技园</option>
            <option value="华强北">华强北</option>
            <option value="东门老街">东门老街</option>
            <option value="福田CBD">福田CBD</option>
            <option value="南山公寓">南山公寓</option>
            <option value="深圳湾公园">深圳湾公园</option>
        </select>
        <label>姓名</label>
        <input type="text" id="newBotName" placeholder="新角色的名字">
        <label>角色/职业</label>
        <input type="text" id="newBotRole" placeholder="如：外卖骑手、留学生...">
        <label>人设描述</label>
        <textarea id="newBotSoul" placeholder="描述这个角色的性格、背景、来深圳的原因..."></textarea>
        <div class="modal-btns">
            <button class="modal-btn cancel" onclick="hideAddBotModal()">取消</button>
            <button class="modal-btn confirm" onclick="addBot()">创建并投放</button>
        </div>
    </div>
</div>

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
    setTimeout(() => { t.classList.remove('show'); }, 3000);
}

function getBotName(botId) {
    const bot = BOTS.find(b => b.id === botId);
    return bot ? bot.name : botId;
}

function initMap() {
    const map = document.getElementById('map');
    for (const [name, pos] of Object.entries(LOCATIONS)) {
        const dot = document.createElement('div');
        dot.className = 'location-dot';
        dot.style.left = pos.x + '%'; dot.style.top = pos.y + '%';
        map.appendChild(dot);
        const label = document.createElement('div');
        label.className = 'location-label';
        label.textContent = name;
        label.style.left = pos.x + '%'; label.style.top = (pos.y - 5) + '%';
        map.appendChild(label);
    }
    BOTS.forEach(bot => addBotToMap(bot));
}

function addBotToMap(bot) {
    const map = document.getElementById('map');
    if (document.getElementById('map-' + bot.id)) return;
    const img = document.createElement('img');
    img.className = 'bot-avatar-map';
    img.id = 'map-' + bot.id;
    img.src = '/avatars/' + bot.id + '.png';
    img.style.borderColor = bot.color;
    img.title = bot.name;
    img.onclick = () => { showDetail(bot.id); };
    img.onerror = function() { this.style.background = bot.color; };
    const defaultPos = LOCATIONS['宝安城中村'];
    img.style.left = defaultPos.x + '%'; img.style.top = defaultPos.y + '%';
    map.appendChild(img);
}

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
    card.onclick = () => switchLog(bot.id, null);
    card.innerHTML = '<span class="sleep-badge" id="sleepbadge-' + bot.id + '"></span>' +
        '<img src="/avatars/' + bot.id + '.png" style="border-color:' + bot.color + '" onerror="this.style.background=\'' + bot.color + '\'">' +
        '<div class="name" style="color:' + bot.color + '">' + bot.name + '</div>' +
        '<div class="role">' + bot.role + '</div>' +
        '<div class="stats">' +
        '<div class="hp-bar"><div class="hp-fill" id="hp-' + bot.id + '" style="width:100%;background:' + bot.color + '"></div></div>' +
        '<div class="stat-row"><span>❤️ HP</span><span id="hpval-' + bot.id + '">100</span></div>' +
        '<div class="stat-row"><span>💰</span><span id="money-' + bot.id + '">500</span></div>' +
        '<div class="stat-row"><span>🍚</span><span id="satiety-' + bot.id + '">80</span></div>' +
        '<div class="stat-row"><span>📍</span><span id="loc-' + bot.id + '" style="font-size:9px">...</span></div>' +
        '</div>' +
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
    if (tabEl) { tabEl.classList.add('active'); }
    else { document.querySelectorAll('.log-tab').forEach(t => { if (t.dataset.log === logName) t.classList.add('active'); }); }
    document.querySelectorAll('.bot-card').forEach(c => c.classList.remove('active'));
    const card = document.getElementById('card-' + logName);
    if (card) card.classList.add('active');
    const msgBar = document.getElementById('msgBar');
    const viewToggle = document.getElementById('viewToggle');
    document.getElementById('galleryContent').style.display = 'none';
    document.getElementById('galleryContent').classList.remove('visible');
    if (currentBotId) {
        msgBar.classList.add('visible');
        viewToggle.classList.add('visible');
    } else {
        msgBar.classList.remove('visible');
        viewToggle.classList.remove('visible');
        currentView = 'log';
        document.getElementById('logContent').style.display = 'block';
        document.getElementById('chatContent').style.display = 'none';
    }
    if (currentView === 'chat' && currentBotId) fetchChat();
    else { currentView = 'log'; setView('log'); fetchLog(); }
}

function classifyLine(line) {
    if (line.includes('[内心独白]') || line.includes('THINK')) return 'inner';
    if (line.includes('[决策]') || line.includes('[行动]') || line.includes('ACTION')) return 'action';
    if (line.includes('[结果]') || line.includes('成功') || line.includes('赚了') || line.includes('恢复')) return 'result';
    if (line.includes('[消息]') || line.includes('说:') || line.includes('上帝视角')) return 'message';
    if (line.includes('死亡') || line.includes('DEAD')) return 'death';
    if (line.includes('ERROR') || line.includes('失败')) return 'error';
    if (line.includes('[价值观变化]')) return 'values';
    if (line.includes('[核心记忆]') || line.includes('⭐')) return 'memory';
    if (line.includes('[关系更新]')) return 'bond';
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
            html = '<div style="text-align:center;color:#555;padding:40px;font-size:13px;">暂无对话记录<br>在下方输入框以伪装身份给TA发消息</div>';
        } else {
            msgs.forEach(m => {
                const isGod = godMessages.some(g => g.msg === m.msg && g.to === m.to);
                const isToMe = m.to === currentBotId;
                const isFromMe = m.from === currentBotId;
                if (isFromMe) {
                    html += '<div class="chat-bubble outgoing"><div class="sender">' + getBotName(currentBotId) + ' → ' + (m.to === 'public' ? '公告板' : getBotName(m.to)) + '</div><div>' + m.msg + '</div><div class="time">tick ' + m.tick + '</div></div>';
                } else if (isToMe || m.to === 'public') {
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
            container.innerHTML = '<div style="text-align:center;color:#555;padding:40px;font-size:13px;width:100%;">📸 还没有人拍过照片<br>Bot们学会拍照后，照片会出现在这里</div>';
            return;
        }
        container.innerHTML = items.reverse().map(item => {
            return '<div class="gallery-item"><img src="/selfies/' + item.filename + '" onerror="this.src=\'/avatars/' + item.bot_id + '.png\'" onclick="window.open(\'/selfies/' + item.filename + '\')"><div class="caption"><span class="bot-name">' + getBotName(item.bot_id) + '</span> ' + (item.prompt || '').substring(0, 40) + '<br><span class="time">' + item.time + '</span></div></div>';
        }).join('');
    } catch(e) {}
}

async function fetchWorld() {
    try {
        const resp = await fetch('/api/world');
        worldState = await resp.json();
        if (worldState.error) return;
        if (worldState.time) {
            const timeStr = worldState.time.virtual_datetime;
            const h = worldState.time.virtual_hour;
            let icon = '☀️';
            if (h >= 22 || h < 6) icon = '🌙';
            else if (h >= 18) icon = '🌆';
            else if (h < 8) icon = '🌅';
            document.getElementById('clock').textContent = icon + ' ' + timeStr + ' | Day ' + worldState.time.virtual_day;
        }
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
                const avatar = document.getElementById('map-' + botId);
                if (avatar && bot.location && LOCATIONS[bot.location]) {
                    const pos = LOCATIONS[bot.location];
                    const botsAtLoc = Object.entries(worldState.bots).filter(([_, b]) => b.location === bot.location);
                    const idx = botsAtLoc.findIndex(([id, _]) => id === botId);
                    const angle = (idx / botsAtLoc.length) * Math.PI * 2;
                    const radius = botsAtLoc.length > 1 ? 3 : 0;
                    avatar.style.left = (pos.x + Math.cos(angle) * radius) + '%';
                    avatar.style.top = (pos.y + Math.sin(angle) * radius) + '%';
                    if (bot.status === 'dead') { avatar.classList.add('dead'); avatar.classList.remove('sleeping'); }
                    else if (bot.is_sleeping) { avatar.classList.add('sleeping'); avatar.classList.remove('dead'); }
                    else { avatar.classList.remove('dead', 'sleeping'); }
                    // Remove old zzz
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
                const hpBar = document.getElementById('hp-' + botId);
                const hpVal = document.getElementById('hpval-' + botId);
                const moneyVal = document.getElementById('money-' + botId);
                const satietyVal = document.getElementById('satiety-' + botId);
                const locVal = document.getElementById('loc-' + botId);
                const sleepBadge = document.getElementById('sleepbadge-' + botId);
                if (hpBar) {
                    hpBar.style.width = bot.hp + '%';
                    if (bot.hp < 30) hpBar.style.background = '#ff4444';
                    else if (bot.hp < 60) hpBar.style.background = '#ffd93d';
                }
                if (hpVal) hpVal.textContent = bot.hp;
                if (moneyVal) moneyVal.textContent = '\u00a5' + bot.money;
                if (satietyVal) satietyVal.textContent = bot.satiety;
                if (locVal) locVal.textContent = bot.location || '...';
                if (sleepBadge) sleepBadge.textContent = bot.is_sleeping ? '💤' : (bot.status === 'dead' ? '💀' : '');
            }
        }
    } catch(e) {}
}

async function showDetail(botId) {
    const panel = document.getElementById('detailPanel');
    const overlay = document.getElementById('detailOverlay');
    const bot = BOTS.find(b => b.id === botId) || { id: botId, name: botId, role: '?', color: '#888' };

    panel.innerHTML = '<div style="padding:40px;text-align:center;color:#888;">加载中...</div>';
    overlay.classList.add('visible');

    try {
        const resp = await fetch('/api/bot/' + botId + '/detail');
        const d = await resp.json();
        if (d.error) { panel.innerHTML = '<div style="padding:40px;text-align:center;color:#ff4444;">' + d.error + '</div>'; return; }

        let html = '';
        // Header
        html += '<div class="detail-header"><img src="/avatars/' + botId + '.png" style="border-color:' + bot.color + '" onerror="this.style.background=\'' + bot.color + '\'">';
        html += '<div class="info"><h2 style="color:' + bot.color + '">' + bot.name + '</h2>';
        html += '<div class="sub">' + bot.role + ' | ' + d.location + (d.is_sleeping ? ' 💤 睡觉中' : '') + (d.status === 'dead' ? ' 💀 已死亡' : '') + '</div></div>';
        html += '<span class="close-btn" onclick="hideDetail()">&times;</span></div>';

        // Stats
        html += '<div class="detail-section"><h3>📊 基础数值</h3><div class="detail-grid">';
        const stats = [
            { label: '❤️ 生命值', value: d.hp, max: 100, color: d.hp < 30 ? '#ff4444' : d.hp < 60 ? '#ffd93d' : '#6bcb77' },
            { label: '⚡ 能量', value: d.energy, max: 100, color: '#4d96ff' },
            { label: '🍚 饱腹度', value: d.satiety, max: 100, color: '#ff9800' },
            { label: '💰 金钱', value: '¥' + d.money, max: null, color: '#ffd93d' },
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
            html += '<div style="margin-top:8px;font-size:11px;color:#e040fb;">价值观已经历 ' + values.shifts.length + ' 次变化</div>';
        }
        html += '</div></div>';

        // Core Memories
        const memories = d.core_memories || [];
        html += '<div class="detail-section"><h3>⭐ 核心记忆 (' + memories.length + ')</h3>';
        if (memories.length === 0) {
            html += '<div style="color:#555;font-size:12px;">还没有形成核心记忆</div>';
        } else {
            memories.forEach(m => {
                const emotionCls = m.emotion || 'neutral';
                const emotionLabel = { positive: '😊 积极', negative: '😢 消极', neutral: '😐 中性' }[emotionCls] || emotionCls;
                html += '<div class="detail-memory">' + m.summary + '<span class="emotion ' + emotionCls + '">' + emotionLabel + '</span><div style="font-size:10px;color:#555;margin-top:4px;">' + (m.time || '') + '</div></div>';
            });
        }
        html += '</div>';

        // Emotional Bonds
        const bonds = d.emotional_bonds || {};
        const bondKeys = Object.keys(bonds);
        html += '<div class="detail-section"><h3>💕 情感关系 (' + bondKeys.length + ')</h3>';
        if (bondKeys.length === 0) {
            html += '<div style="color:#555;font-size:12px;">还没有建立深层关系</div>';
        } else {
            bondKeys.forEach(target => {
                const b = bonds[target];
                html += '<div class="detail-bond"><div class="bond-label" style="min-width:60px;">' + getBotName(target) + '<br><span style="font-size:10px;color:#888;">' + (b.label || '?') + '</span></div>';
                html += '<div class="bond-bars">';
                html += '<div class="bond-bar"><span style="min-width:30px;">信任</span><div class="bar"><div class="bar-fill" style="width:' + (b.trust || 0) + '%;background:#6bcb77"></div></div><span>' + (b.trust || 0) + '</span></div>';
                html += '<div class="bond-bar"><span style="min-width:30px;">亲密</span><div class="bar"><div class="bar-fill" style="width:' + (b.closeness || 0) + '%;background:#4d96ff"></div></div><span>' + (b.closeness || 0) + '</span></div>';
                html += '<div class="bond-bar"><span style="min-width:30px;">敌意</span><div class="bar"><div class="bar-fill" style="width:' + (b.hostility || 0) + '%;background:#ff4444"></div></div><span>' + (b.hostility || 0) + '</span></div>';
                html += '</div></div>';
            });
        }
        html += '</div>';

        // Family
        const family = d.family || {};
        if (Object.keys(family).length > 0) {
            html += '<div class="detail-section"><h3>👨‍👩‍👧 家庭关系</h3>';
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
            html += '<div class="detail-section"><h3>📸 拍照次数: ' + d.selfie_count + '</h3></div>';
        }

        panel.innerHTML = html;
    } catch(e) {
        panel.innerHTML = '<div style="padding:40px;text-align:center;color:#ff4444;">加载失败: ' + e + '</div>';
    }
}

function hideDetail() {
    document.getElementById('detailOverlay').classList.remove('visible');
}

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
        if (result.error) { showToast('发送失败: ' + result.error, 'info'); return; }
        godMessages.push({ msg: msg, to: currentBotId, alias: alias });
        const priorityNote = ['父亲','母亲','爸爸','妈妈'].includes(alias) ? ' (高优先级🔴)' : '';
        showToast('✅ 消息已发送给 ' + getBotName(currentBotId) + '（以"' + alias + '"身份）' + priorityNote, 'success');
        if (currentView === 'chat') {
            const container = document.getElementById('chatContent');
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble incoming god';
            bubble.innerHTML = '<div class="sender">' + alias + ' 👁️ (你)' + priorityNote + '</div><div>' + msg + '</div><div class="time">刚刚发送</div>';
            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
        }
        if (currentView === 'log') setView('chat');
    } catch(e) { showToast('发送失败: ' + e, 'info'); }
}

function showAddBotModal() {
    document.getElementById('addBotModal').classList.add('visible');
    const maxId = BOTS.reduce((max, b) => {
        const num = parseInt(b.id.replace('bot_', ''));
        return isNaN(num) ? max : (num > max ? num : max);
    }, 0);
    document.getElementById('newBotId').value = 'bot_' + (maxId + 1);
}

function hideAddBotModal() { document.getElementById('addBotModal').classList.remove('visible'); }

async function addBot() {
    const botId = document.getElementById('newBotId').value.trim();
    const location = document.getElementById('newBotLocation').value;
    const name = document.getElementById('newBotName').value.trim() || botId;
    const role = document.getElementById('newBotRole').value.trim() || '新居民';
    const soul = document.getElementById('newBotSoul').value.trim();
    if (!botId) { alert('请输入Bot ID'); return; }
    try {
        const resp = await fetch('/api/add_bot', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ bot_id: botId, location: location, name: name, role: role, soul: soul })
        });
        const result = await resp.json();
        if (result.error) { showToast('创建失败: ' + result.error, 'info'); return; }
        const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
        const newBot = { id: botId, name: name, role: role, color: color };
        BOTS.push(newBot);
        addBotToMap(newBot);
        addBotCard(newBot);
        addBotTab(newBot);
        hideAddBotModal();
        showToast('🎉 ' + name + ' 已抵达深圳 ' + location + '！', 'success');
    } catch(e) { showToast('创建失败: ' + e, 'info'); }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if (e.key === 'Escape') { hideDetail(); hideAddBotModal(); return; }
    const num = parseInt(e.key);
    if (num === 0) switchLog('world_engine', null);
    else if (num >= 1 && num <= 9) switchLog('bot_' + num, null);
});

// Initialize
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
</html>"""
    return HTMLResponse(content=html)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
