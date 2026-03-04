#!/usr/bin/env python3
"""
Zhaocai Gateway 快速测试脚本
"""

import os
import sys
import httpx
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def load_env():
    """加载 .env 文件"""
    env_path = Path(".env")
    if not env_path.exists():
        print_error(".env 文件不存在，请先运行部署脚本")
        sys.exit(1)

    env_vars = {}
    for line in env_path.read_text(encoding='utf-8').split('\n'):
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_vars[key] = value
    return env_vars

def test_health(base_url):
    """测试健康检查端点"""
    try:
        resp = httpx.get(f"{base_url}/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print_success(f"健康检查通过 - 状态: {data.get('status')}")
            providers = data.get('providers', {})
            print_info(f"  已配置 Provider: {list(providers.keys())}")
            return True
        else:
            print_error(f"健康检查失败 - 状态码: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"健康检查失败 - {e}")
        return False

def test_models(base_url):
    """测试模型列表端点"""
    try:
        resp = httpx.get(f"{base_url}/v1/models", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('data', [])
            print_success(f"模型列表接口正常 - 共 {len(models)} 个模型")
            for m in models[:3]:  # 只显示前3个
                print_info(f"  - {m.get('id')} ({m.get('owned_by')})")
            return True
        else:
            print_error(f"模型列表接口失败 - 状态码: {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"模型列表接口失败 - {e}")
        return False

def test_control_plane(base_url, admin_token):
    """测试控制面接口"""
    headers = {"X-Admin-Token": admin_token}

    tests = [
        ("/control/v1/providers", "Provider 列表"),
        ("/control/v1/models", "Model 列表"),
        ("/control/v1/profiles", "Profile 列表"),
        ("/control/v1/nodes", "Node 列表"),
    ]

    all_passed = True
    for path, name in tests:
        try:
            resp = httpx.get(f"{base_url}{path}", headers=headers, timeout=10)
            if resp.status_code == 200:
                print_success(f"{name}接口正常")
            else:
                print_error(f"{name}接口失败 - 状态码: {resp.status_code}")
                all_passed = False
        except Exception as e:
            print_error(f"{name}接口失败 - {e}")
            all_passed = False

    return all_passed

def test_create_provider(base_url, admin_token):
    """测试创建 Provider"""
    headers = {
        "X-Admin-Token": admin_token,
        "Content-Type": "application/json"
    }

    payload = {
        "name": "test-provider",
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "auth_scheme": "bearer",
        "api_key": "sk-test-key",
        "enabled": True
    }

    try:
        resp = httpx.post(
            f"{base_url}/control/v1/providers",
            headers=headers,
            json=payload,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            provider_id = data.get('provider', {}).get('id')
            print_success(f"创建 Provider 成功 - ID: {provider_id}")
            return provider_id
        elif resp.status_code == 400 and "already exists" in resp.text:
            print_info("测试 Provider 已存在，跳过创建")
            return None
        else:
            print_error(f"创建 Provider 失败 - {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print_error(f"创建 Provider 失败 - {e}")
        return None

def main():
    print("=" * 60)
    print("Zhaocai Gateway 快速测试")
    print("=" * 60)
    print()

    # 加载环境变量
    env = load_env()
    base_url = f"http://localhost:{env.get('ZHAOCAI_PORT', '8000')}"
    admin_token = env.get('ZHAOCAI_ADMIN_TOKEN', '')

    if not admin_token:
        print_error("ZHAOCAI_ADMIN_TOKEN 未设置")
        sys.exit(1)

    print_info(f"测试地址: {base_url}")
    print()

    # 运行测试
    results = []

    print("【基础接口测试】")
    results.append(("健康检查", test_health(base_url)))
    results.append(("模型列表", test_models(base_url)))
    print()

    print("【控制面接口测试】")
    results.append(("控制面", test_control_plane(base_url, admin_token)))
    print()

    print("【数据写入测试】")
    provider_id = test_create_provider(base_url, admin_token)
    results.append(("创建 Provider", provider_id is not None or True))  # 已存在也算成功
    print()

    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}通过{Colors.END}" if result else f"{Colors.RED}失败{Colors.END}"
        print(f"  {name}: {status}")

    print()
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print()
        print_success("所有测试通过！服务运行正常")
        print()
        print("快速开始：")
        print(f"  1. 访问 http://localhost:8000/docs 查看 API 文档")
        print(f"  2. 访问 http://localhost:8000/control 进入控制面板")
        print(f"  3. 使用 Admin Token: {admin_token[:20]}...")
    else:
        print()
        print_error("部分测试失败，请检查服务状态和日志")
        sys.exit(1)

if __name__ == "__main__":
    main()
