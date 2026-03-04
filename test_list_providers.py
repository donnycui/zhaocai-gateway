#!/usr/bin/env python3
"""测试列出 Providers"""
import httpx

ADMIN_TOKEN = "change-me-admin-token"
BASE_URL = "http://127.0.0.1:8000"

resp = httpx.get(
    f"{BASE_URL}/control/v1/providers",
    headers={"X-Admin-Token": ADMIN_TOKEN},
    timeout=10
)

print(f"状态码: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    providers = data.get('providers', [])
    print(f"共有 {len(providers)} 个 Providers:")
    for p in providers:
        print(f"  - ID:{p['id']} {p['name']} ({p['provider_type']}) {'启用' if p['enabled'] else '禁用'}")
else:
    print(f"响应: {resp.text}")
