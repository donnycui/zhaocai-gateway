#!/usr/bin/env python3
"""测试健康检查"""
import httpx
resp = httpx.get("http://localhost:8000/health")
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text}")
