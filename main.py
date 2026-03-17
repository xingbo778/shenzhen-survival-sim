#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深圳生存模拟 - 启动入口
"""
import uvicorn
from api.server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
