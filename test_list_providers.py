#!/usr/bin/env python3
"""测试列出 Providers"""
import os
from dotenv import load_dotenv
load_dotenv()

import httpx

ADMIN_TOKEN = os.getenv("ZHAOCAI_ADMIN_TOKEN", "change-me-admin-token")
BASE_URL = "http://127.0.0.1:8000"

resp = httpx.get(
    f"{BASE_URL}/control/v1/providers",
    headers={"X-Admin-Token": ADMIN_TOKEN},
    timeout=10
)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    providers = data.get('providers', [])
    print(f"Total {len(providers)} Providers:")
    for p in providers:
        status = "Enabled" if p['enabled'] else "Disabled"
        print(f"  - ID:{p['id']} {p['name']} ({p['provider_type']}) {status}")
else:
    print(f"Response: {resp.text}")
