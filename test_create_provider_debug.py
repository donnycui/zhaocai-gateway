#!/usr/bin/env python3
"""
测试创建 Provider - 带环境变量设置
"""

import os
import sys
from pathlib import Path

# 第一步：加载 .env 到环境变量
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').split('\n'):
        if '=' in line and not line.startswith('#') and not line.strip() == '':
            key, value = line.split('=', 1)
            os.environ[key] = value
            if key == 'ZHAOCAI_ADMIN_TOKEN':
                print(f"已加载 Admin Token: {value[:30]}...")

ADMIN_TOKEN = os.getenv("ZHAOCAI_ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    print("错误: 无法读取 ZHAOCAI_ADMIN_TOKEN")
    sys.exit(1)

print(f"最终使用的 Token: {ADMIN_TOKEN}")
print(f"Token 长度: {len(ADMIN_TOKEN)}")
print()

# 第二步：导入并测试
import httpx

BASE_URL = "http://127.0.0.1:8000"
print(f"请求地址: {BASE_URL}")
print()

# 测试创建 SiliconFlow Provider
try:
    resp = httpx.post(
        f"{BASE_URL}/control/v1/providers",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        json={
            "name": "siliconflow-test",
            "provider_type": "openai",
            "base_url": "https://api.siliconflow.cn/v1",
            "auth_scheme": "bearer",
            "api_key": "sk-oygjolpbktfphizinffhxutkmfpcjmesxtcqmktsezkeylzk",
            "enabled": True
        },
        timeout=10
    )

    print(f"状态码: {resp.status_code}")
    print(f"响应: {resp.text}")

    if resp.status_code == 200:
        print("\n✓ 创建 Provider 成功!")
    elif resp.status_code == 400 and "already exists" in resp.text.lower():
        print("\n! Provider 已存在")
    elif resp.status_code == 401:
        print("\n✗ Token 验证失败 - 请确保服务使用的是相同的 .env 文件")
        print(f"  发送的 Token: {ADMIN_TOKEN}")
except Exception as e:
    print(f"错误: {e}")
