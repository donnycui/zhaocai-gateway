#!/usr/bin/env python3
"""完整功能测试脚本"""
import os
from dotenv import load_dotenv
load_dotenv()

import httpx

ADMIN_TOKEN = os.getenv("ZHAOCAI_ADMIN_TOKEN", "change-me-admin-token")
BASE_URL = "http://127.0.0.1:8000"

print("="*60)
print("招财网关功能测试")
print("="*60)

# 1. 健康检查
print("\n[1] 健康检查...")
try:
    resp = httpx.get(f"{BASE_URL}/health", timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        healthy_count = sum(1 for p in data.get('providers', {}).values() if p.get('healthy'))
        print(f"  OK - {healthy_count} 个 Provider 健康")
    else:
        print(f"  失败 - 状态码: {resp.status_code}")
except Exception as e:
    print(f"  错误: {e}")

# 2. 创建 Provider
print("\n[2] 创建 Provider...")
try:
    resp = httpx.post(
        f"{BASE_URL}/control/v1/providers",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        json={
            "name": "test-provider",
            "provider_type": "openai",
            "base_url": "https://api.siliconflow.cn/v1",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "enabled": True
        },
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"  OK - Provider ID: {data['provider']['id']}")
    elif "already exists" in resp.text.lower():
        print("  OK - Provider 已存在")
    else:
        print(f"  失败 - {resp.status_code}: {resp.text[:100]}")
except Exception as e:
    print(f"  错误: {e}")

# 3. 列出 Providers
print("\n[3] 列出 Providers...")
try:
    resp = httpx.get(
        f"{BASE_URL}/control/v1/providers",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get('providers', []))
        print(f"  OK - 共 {count} 个 Providers")
    else:
        print(f"  失败 - {resp.status_code}")
except Exception as e:
    print(f"  错误: {e}")

# 4. 列出 Models
print("\n[4] 列出 Models...")
try:
    resp = httpx.get(
        f"{BASE_URL}/control/v1/models",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get('models', []))
        print(f"  OK - 共 {count} 个 Models")
    else:
        print(f"  失败 - {resp.status_code}")
except Exception as e:
    print(f"  错误: {e}")

# 5. 列出 Profiles
print("\n[5] 列出 Profiles...")
try:
    resp = httpx.get(
        f"{BASE_URL}/control/v1/profiles",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get('profiles', []))
        print(f"  OK - 共 {count} 个 Profiles")
    else:
        print(f"  失败 - {resp.status_code}")
except Exception as e:
    print(f"  错误: {e}")

# 6. 列出 Nodes
print("\n[6] 列出 Nodes...")
try:
    resp = httpx.get(
        f"{BASE_URL}/control/v1/nodes",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10
    )
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get('nodes', []))
        print(f"  OK - 共 {count} 个 Nodes")
    else:
        print(f"  失败 - {resp.status_code}")
except Exception as e:
    print(f"  错误: {e}")

print("\n" + "="*60)
print("测试完成!")
print("="*60)
print(f"\n访问控制面板: http://localhost:8000/control")
print(f"使用 Admin Token: {ADMIN_TOKEN[:30]}...")
