"""
统一路径管理 — 通过 SZ_DATA_DIR 环境变量覆盖，默认兼容 /home/ubuntu（Linux）
和本地 macOS 开发环境（~/.shenzhen-sim）。
"""
import os

_default = "/home/ubuntu" if os.path.exists("/home/ubuntu") else os.path.expanduser("~/.shenzhen-sim")
DATA_DIR = os.environ.get("SZ_DATA_DIR", _default)

LOGS_DIR     = os.path.join(DATA_DIR, "logs")
SELFIES_DIR  = os.path.join(DATA_DIR, "selfies")
SNAPSHOT     = os.path.join(DATA_DIR, "world_state_snapshot.json")
AVATARS_DIR  = os.path.join(DATA_DIR, "bot_avatars_v2")
AVATARS_DIR2 = os.path.join(DATA_DIR, "bot_avatars")

os.makedirs(LOGS_DIR,    exist_ok=True)
os.makedirs(SELFIES_DIR, exist_ok=True)
