#!/bin/bash
# 深圳生存模拟 v7 启动脚本

echo "=== 启动深圳生存模拟 v7 ==="
echo "新功能: 睡眠系统, Selfie(Grok), 消息优先级, 价值观演化, 深层记忆, 情感关系"

# 清理旧日志
> /home/ubuntu/logs/world_engine.log

# 1. 启动世界引擎 v7
echo "[1/3] 启动世界引擎 v7..."
cd /home/ubuntu
nohup python3 world_engine_v7.py > logs/world_stdout_v7.log 2>&1 &
echo "世界引擎 PID: $!"

# 等待世界引擎就绪
sleep 5
for i in {1..10}; do
    if curl -s http://localhost:8000/world > /dev/null 2>&1; then
        echo "世界引擎已就绪!"
        break
    fi
    echo "等待世界引擎... ($i/10)"
    sleep 2
done

# 2. 启动 Dashboard v4
echo "[2/3] 启动 Dashboard v4..."
nohup python3 sz_dashboard_v4.py > logs/dashboard_stdout_v4.log 2>&1 &
echo "Dashboard PID: $!"

echo ""
echo "[3/3] Bot agents 将由世界引擎自动启动"
echo ""
echo "=== 深圳生存模拟 v7 启动完成 ==="
echo "Dashboard: http://localhost:9000"
echo "世界引擎: http://localhost:8000"
