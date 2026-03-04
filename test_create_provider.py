#!/usr/bin/env python3
"""
测试创建 Provider（自动读取 .env）
"""

import os
import httpx
from pathlib import Path

# 手动读取 .env 文件
def load_env():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

load_env()

# 从环境变量读取
ADMIN_TOKEN = os.getenv("ZHAOCAI_ADMIN_TOKEN", "")
BASE_URL = "http://localhost:8000"

print(f"使用 Admin Token: {ADMIN_TOKEN[:30]}...")
print(f"请求地址: {BASE_URL}")
print()

# 创建 SiliconFlow Provider
resp = httpx.post(
    f"{BASE_URL}/control/v1/providers",
    headers={"X-Admin-Token": ADMIN_TOKEN},
    json={
        "name": "siliconflow",
        "provider_type": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "auth_scheme": "bearer",
        "api_key": "sk-oygjolpbktfphizinffhxutkmfpcjmesxtcqmktsezkeylzk",
        "enabled": True
    }
)

print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text}")
