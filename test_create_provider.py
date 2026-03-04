#!/usr/bin/env python3
"""测试创建 Provider"""
import os
from dotenv import load_dotenv
load_dotenv()

import httpx

ADMIN_TOKEN = os.getenv("ZHAOCAI_ADMIN_TOKEN", "change-me-admin-token")
BASE_URL = "http://127.0.0.1:8000"

print(f"Using Admin Token: {ADMIN_TOKEN[:30]}...")
print(f"URL: {BASE_URL}")
print()

resp = httpx.post(
    f"{BASE_URL}/control/v1/providers",
    headers={"X-Admin-Token": ADMIN_TOKEN},
    json={
        "name": "siliconflow-v3",
        "provider_type": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "auth_scheme": "bearer",
        "api_key": "sk-oygjolpbktfphizinffhxutkmfpcjmesxtcqmktsezkeylzk",
        "enabled": True
    },
    timeout=10
)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Provider ID: {data['provider']['id']}")
    print(f"Provider Name: {data['provider']['name']}")
    print("[OK] Created successfully!")
else:
    print(f"Response: {resp.text}")
