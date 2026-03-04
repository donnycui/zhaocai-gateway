#!/usr/bin/env python3
"""测试获取 Providers 列表"""
import httpx
ADMIN_TOKEN = "admin-74f9845b77e9b836bb567c16a649ad53"
resp = httpx.get(
    "http://localhost:8000/control/v1/providers",
    headers={"X-Admin-Token": ADMIN_TOKEN}
)
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text}")
