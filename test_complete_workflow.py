#!/usr/bin/env python3
"""
完整工作流程测试
1. 创建 Provider (如果未创建)
2. 创建 Model
3. 创建 Profile
4. 绑定 Model 到 Profile
5. 创建 Node
6. 拉取 Node 配置
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

import httpx

ADMIN_TOKEN = os.getenv("ZHAOCAI_ADMIN_TOKEN", "change-me-admin-token")
BASE_URL = "http://127.0.0.1:8000"

print("="*70)
print("招财网关 - 完整工作流程测试")
print("="*70)
print(f"\n管理员 Token: {ADMIN_TOKEN[:30]}...")
print(f"服务地址: {BASE_URL}\n")

def api_call(method, path, body=None, use_admin=True):
    """调用 API"""
    headers = {"Content-Type": "application/json"}
    if use_admin:
        headers["X-Admin-Token"] = ADMIN_TOKEN

    try:
        resp = httpx.request(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            json=body,
            timeout=15
        )
        if resp.status_code >= 400:
            return None, f"HTTP {resp.status_code}: {resp.text}"
        return resp.json(), None
    except Exception as e:
        return None, str(e)

# 步骤 1: 创建 Provider
print("\n" + "-"*70)
print("[步骤 1] 创建 Provider")
print("-"*70)

# 先列出已有 Providers
result, err = api_call("GET", "/control/v1/providers")
if err:
    print(f"  [FAIL] 获取 Providers 失败: {err}")
    sys.exit(1)

existing_providers = result.get('providers', [])
print(f"  现有 Providers: {len(existing_providers)} 个")
for p in existing_providers:
    print(f"    - ID:{p['id']} {p['name']}")

# 创建新的测试 Provider
provider_data = {
    "name": "workflow-test-siliconflow",
    "provider_type": "openai",
    "base_url": "https://api.siliconflow.cn/v1",
    "auth_scheme": "bearer",
    "api_key": os.getenv("SILICONFLOW_API_KEY", "sk-test"),
    "enabled": True
}

result, err = api_call("POST", "/control/v1/providers", provider_data)
if err:
    if "already exists" in err.lower() or "UNIQUE constraint" in err:
        print(f"  [WARN] Provider 已存在，使用现有 Provider")
        # 查找已存在的 Provider
        for p in existing_providers:
            if p['name'] == provider_data['name']:
                provider_id = p['id']
                break
        else:
            # 如果找不到刚创建的，使用最后一个
            provider_id = existing_providers[-1]['id'] if existing_providers else None
    else:
        print(f"  [FAIL] 创建 Provider 失败: {err}")
        sys.exit(1)
else:
    provider_id = result['provider']['id']
    print(f"  [OK] Provider 创建成功 - ID: {provider_id}")

if not provider_id:
    print("  [FAIL] 没有可用的 Provider")
    sys.exit(1)

# 步骤 2: 创建 Model
print("\n" + "-"*70)
print("[步骤 2] 创建 Model")
print("-"*70)

model_data = {
    "provider_id": provider_id,
    "upstream_model": "deepseek-ai/DeepSeek-V3",
    "alias": "deepseek-v3-workflow",
    "enabled": True,
    "capabilities": ["chat", "reasoning"]
}

result, err = api_call("POST", "/control/v1/models", model_data)
if err:
    if "already exists" in err.lower():
        print(f"  [WARN] Model 已存在")
        # 获取 Model 列表
        result, _ = api_call("GET", "/control/v1/models")
        for m in result.get('models', []):
            if m['alias'] == model_data['alias']:
                model_id = m['id']
                break
        else:
            model_id = result['models'][0]['id'] if result.get('models') else None
    else:
        print(f"  [FAIL] 创建 Model 失败: {err}")
        sys.exit(1)
else:
    model_id = result['model']['id']
    print(f"  [OK] Model 创建成功 - ID: {model_id}")
    print(f"    别名: {result['model']['alias']}")
    print(f"    上游模型: {result['model']['upstream_model']}")

if not model_id:
    print("  [FAIL] 没有可用的 Model")
    sys.exit(1)

# 步骤 3: 创建 Profile
print("\n" + "-"*70)
print("[步骤 3] 创建 Profile (配置集)")
print("-"*70)

profile_data = {
    "name": "工作流测试配置集",
    "description": "用于测试工作流的配置集"
}

result, err = api_call("POST", "/control/v1/profiles", profile_data)
if err:
    if "already exists" in err.lower():
        print(f"  [WARN] Profile 已存在")
        # 获取 Profile 列表
        result, _ = api_call("GET", "/control/v1/profiles")
        for p in result.get('profiles', []):
            if p['name'] == profile_data['name']:
                profile_id = p['id']
                break
        else:
            profile_id = result['profiles'][0]['id'] if result.get('profiles') else None
    else:
        print(f"  [FAIL] 创建 Profile 失败: {err}")
        sys.exit(1)
else:
    profile_id = result['profile']['id']
    print(f"  [OK] Profile 创建成功 - ID: {profile_id}")
    print(f"    名称: {result['profile']['name']}")
    print(f"    描述: {result['profile']['description']}")

if not profile_id:
    print("  [FAIL] 没有可用的 Profile")
    sys.exit(1)

# 步骤 4: 绑定 Model 到 Profile
print("\n" + "-"*70)
print("[步骤 4] 绑定 Model 到 Profile")
print("-"*70)

binding_data = {
    "model_ids": [model_id]
}

result, err = api_call("POST", f"/control/v1/profiles/{profile_id}/bindings", binding_data)
if err:
    print(f"  [FAIL] 绑定失败: {err}")
    sys.exit(1)
else:
    print(f"  [OK] 绑定成功")
    print(f"    Profile ID: {profile_id}")
    print(f"    绑定的 Model IDs: {result['profile']['model_ids']}")

# 步骤 5: 创建 Node
print("\n" + "-"*70)
print("[步骤 5] 创建 Node (节点)")
print("-"*70)

node_data = {
    "name": "测试节点-01",
    "profile_id": profile_id,
    "sync_mode": "pull",
    "active": True
}

result, err = api_call("POST", "/control/v1/nodes", node_data)
if err:
    if "already exists" in err.lower():
        print(f"  [WARN] Node 已存在")
        # 获取 Node 列表
        result, _ = api_call("GET", "/control/v1/nodes")
        for n in result.get('nodes', []):
            if n['name'] == node_data['name']:
                node_id = n['id']
                pull_token = "请使用管理员 Token 或查看 Node 详情"
                break
        else:
            node_id = result['nodes'][0]['id'] if result.get('nodes') else None
            pull_token = None
    else:
        print(f"  [FAIL] 创建 Node 失败: {err}")
        sys.exit(1)
else:
    node_id = result['node']['id']
    pull_token = result['node'].get('pull_token', 'N/A')
    print(f"  [OK] Node 创建成功 - ID: {node_id}")
    print(f"    名称: {result['node']['name']}")
    print(f"    Profile ID: {result['node']['profile_id']}")
    print(f"    拉取 Token: {pull_token[:40]}..." if len(str(pull_token)) > 40 else f"    拉取 Token: {pull_token}")

if not node_id:
    print("  [FAIL] 没有可用的 Node")
    sys.exit(1)

# 步骤 6: 拉取 Node 配置
print("\n" + "-"*70)
print("[步骤 6] 拉取 Node 配置 (openclaw.json)")
print("-"*70)

# 使用 Admin Token 拉取配置
result, err = api_call("GET", f"/control/v1/nodes/{node_id}/openclaw-json")
if err:
    print(f"  [FAIL] 拉取配置失败: {err}")
else:
    print(f"  [OK] 配置拉取成功")
    config = result
    print(f"    版本: {config.get('schema_version')}")
    print(f"    生成时间: {config.get('generated_at')}")
    print(f"    节点名称: {config.get('node', {}).get('name')}")
    print(f"    Profile: {config.get('profile', {}).get('name')}")
    print(f"    Providers: {len(config.get('providers', []))} 个")
    print(f"    Models: {len(config.get('models', []))} 个")

    # 保存配置到文件
    import json
    config_file = f"openclaw_node_{node_id}.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"\n  配置已保存到: {config_file}")

# 汇总
print("\n" + "="*70)
print("工作流程测试完成[WARN]")
print("="*70)
print(f"\n创建的资源汇总:")
print(f"  Provider ID: {provider_id}")
print(f"  Model ID: {model_id}")
print(f"  Profile ID: {profile_id}")
print(f"  Node ID: {node_id}")
print(f"\n控制面板: http://localhost:8000/control")
print(f"API 文档: http://localhost:8000/docs")
