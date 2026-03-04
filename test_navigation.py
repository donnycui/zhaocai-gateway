#!/usr/bin/env python3
"""测试导航功能"""
import httpx

BASE_URL = "http://127.0.0.1:8000"

print("="*60)
print("导航功能测试")
print("="*60)

pages = [
    ("/health", "健康监控页面"),
    ("/control", "控制面板"),
    ("/docs", "API 文档"),
]

for path, name in pages:
    try:
        resp = httpx.get(f"{BASE_URL}{path}", follow_redirects=True, timeout=10)
        status = "OK" if resp.status_code == 200 else f"FAIL({resp.status_code})"
        print(f"\n[{status}] {name}")
        print(f"  URL: {BASE_URL}{path}")

        # 检查是否包含导航栏
        has_nav = 'navbar' in resp.text or 'nav-brand' in resp.text
        print(f"  导航栏: {'有' if has_nav else '无'}")

        # 检查是否包含链接
        has_health_link = '/health' in resp.text
        has_control_link = '/control' in resp.text
        has_docs_link = '/docs' in resp.text
        print(f"  链接完整性: health={has_health_link}, control={has_control_link}, docs={has_docs_link}")

    except Exception as e:
        print(f"\n[ERROR] {name}: {e}")

print("\n" + "="*60)
print("测试完成!")
print("="*60)
print("\n访问地址:")
print(f"  健康监控: {BASE_URL}/health")
print(f"  控制面板: {BASE_URL}/control")
print(f"  API 文档: {BASE_URL}/docs")
