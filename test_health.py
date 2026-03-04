#!/usr/bin/env python3
"""测试健康检查"""
import httpx
# 禁用代理，增加超时
resp = httpx.get("http://127.0.0.1:8000/health", timeout=10, follow_redirects=True)
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text}")
