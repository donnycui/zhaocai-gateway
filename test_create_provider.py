#!/usr/bin/env python3
"""测试创建 Provider"""
import httpx

# 服务当前使用的默认 token（因为 .env 未被加载）
ADMIN_TOKEN = "change-me-admin-token"
BASE_URL = "http://127.0.0.1:8000"

print(f"使用 Admin Token: {ADMIN_TOKEN}")
print(f"请求地址: {BASE_URL}")
print()

resp = httpx.post(
    f"{BASE_URL}/control/v1/providers",
    headers={"X-Admin-Token": ADMIN_TOKEN},
    json={
        "name": "siliconflow-v2",
        "provider_type": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "auth_scheme": "bearer",
        "api_key": "sk-oygjolpbktfphizinffhxutkmfpcjmesxtcqmktsezkeylzk",
        "enabled": True
    },
    timeout=10
)

print(f"状态码: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Provider ID: {data['provider']['id']}")
    print(f"Provider Name: {data['provider']['name']}")
    print("[OK] 创建成功!")
else:
    print(f"响应: {resp.text}")
