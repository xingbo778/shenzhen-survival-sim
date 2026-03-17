# 深圳生存模拟 - 各服务启动方式
# 
# 1. 游戏引擎 API (端口 8000):
#    python main.py
#    或: uvicorn api.server:app --host 0.0.0.0 --port 8000
#
# 2. 管理员仪表板 (端口 8080):
#    cd dashboard && uvicorn app:app --host 0.0.0.0 --port 8080

