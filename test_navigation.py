#!/usr/bin/env python3
"""测试导航功能 - 验证所有页面"""
import httpx

BASE_URL = "http://127.0.0.1:8000"

print("="*70)
print("导航功能测试")
print("="*70)

pages = [
    ("/guide", "使用指南", True),
    ("/health", "健康监控", True),
    ("/control", "控制面板", True),
    ("/docs", "API 文档", False),  # Swagger UI 没有自定义导航
]

all_ok = True
for path, name, has_nav in pages:
    try:
        resp = httpx.get(f"{BASE_URL}{path}", follow_redirects=True, timeout=10)
        status = "OK" if resp.status_code == 200 else f"FAIL({resp.status_code})"
        print(f"\n[{status}] {name}")
        print(f"  URL: {BASE_URL}{path}")

        if has_nav:
            # 检查导航栏链接
            has_guide = '/guide' in resp.text
            has_health = '/health' in resp.text
            has_control = '/control' in resp.text
            has_docs = '/docs' in resp.text
            nav_complete = has_guide and has_health and has_control and has_docs

            print(f"  导航链接: guide={has_guide}, health={has_health}, control={has_control}, docs={has_docs}")

            if not nav_complete:
                print(f"  ⚠ 导航可能不完整")
                all_ok = False

    except Exception as e:
        print(f"\n[ERROR] {name}: {e}")
        all_ok = False

print("\n" + "="*70)
if all_ok:
    print("[OK] All pages passed!")
else:
    print("[WARN] Some pages have issues")
print("="*70)

print("\n访问地址:")
print(f"  📖 使用指南 : {BASE_URL}/guide")
print(f"  📊 健康监控 : {BASE_URL}/health")
print(f"  🎛️ 控制面板 : {BASE_URL}/control")
print(f"  📚 API 文档 : {BASE_URL}/docs")
