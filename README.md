# 招财网关 (Zhaocai Gateway)

<p align="center">
  <strong>OpenAI 兼容的 AI 推理网关 + OpenClaw 多节点控制面板</strong>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> •
  <a href="#功能特性">功能特性</a> •
  <a href="#控制面板">控制面板</a> •
  <a href="#api-文档">API 文档</a>
</p>

---

## 简介

招财网关是统一的 AI 推理网关，提供：

1. **OpenAI 兼容的推理接口** (`/v1/chat/completions`)
2. **多节点配置分发控制面板** (`/control/v1/...`)

适用于拥有多个 LLM Provider 和多个 OpenClaw 节点（树莓派、VPS 等）的场景，需要为不同节点分配不同的模型集合。

---

## 功能特性

- **🚀 多 Provider 路由** - 支持轮询、权重、优先级三种策略
- **🔄 故障自动转移** - 单点失败时自动切换到备用 Provider
- **⚡ 基础限流保护** - 基于令牌桶的速率限制
- **🔌 Provider 适配层** - 支持 OpenAI 兼容和 Anthropic 格式转换
- **📦 控制面板数据模型**
  - Providers（Provider 管理）
  - Models（模型别名管理）
  - Profiles（配置集/场景）
  - Profile 模型绑定
  - Nodes（节点管理）
  - 节点配置版本追踪
- **📥 节点配置拉取协议**
  - 节点 Bearer Token 认证
  - `ETag` + `If-None-Match` 缓存
  - `304` 响应表示无变更
- **🎛️ 管理面板** - 最小化 Web 界面，支持中英双语

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备配置文件

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```

编辑 `.env` 文件，设置以下关键项：

```bash
# 可选：生成 Fernet 加密密钥（用于 API Key 静态加密存储）
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 填入 .env
# 推荐填写；留空则不启用静态加密
ZHAOCAI_ENCRYPTION_KEY="你的加密密钥"
ZHAOCAI_ADMIN_TOKEN="你的管理员Token"

# 填入至少一个 Provider API Key
SILICONFLOW_API_KEY="sk-..."
```

### 3. 启动服务

```bash
python gateway.py
```

服务启动后访问：
- 📘 API 文档: http://localhost:8000/docs
- 🎛️ 控制面板: http://localhost:8000/control
- ❤️ 健康检查 API: http://localhost:8000/health
- 📊 健康监控页面: http://localhost:8000/health-ui

---

## 控制面板

访问 http://localhost:8000/control 打开管理面板。

面板支持 **中文/English** 双语切换。

### 快速操作流程

1. **创建 Provider** - 配置上游 AI 服务（如 SiliconFlow）
2. **创建 Model** - 设置模型别名和 Provider 绑定
3. **创建 Profile** - 创建配置集（如 "默认配置"）
4. **绑定模型** - 将模型关联到配置集
5. **创建 Node** - 创建节点并关联配置集
6. **获取 Token** - 创建后获取节点的拉取 Token
7. **拉取配置** - 使用 Token 获取节点的专属配置

---

## API 文档

### 推理接口

#### 聊天补全

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role":"user","content":"你好"}]
  }'
```

#### 流式响应

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role":"user","content":"你好"}],
    "stream": true
  }'
```

#### 监控接口

- `GET /health` - 健康状态
- `GET /v1/models` - 可用模型列表
- `GET /v1/providers` - Provider 状态
- `GET /metrics` - 指标统计

### 控制面板接口

#### 认证方式

管理接口需要在请求头中携带：

```
X-Admin-Token: 你的管理员Token
```

#### Provider 管理

```bash
# 创建 Provider
curl -X POST http://localhost:8000/control/v1/providers \
  -H "X-Admin-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "siliconflow",
    "provider_type": "openai",
    "base_url": "https://api.siliconflow.cn/v1",
    "auth_scheme": "bearer",
    "api_key": "sk-xxx",
    "enabled": true
  }'

# 列出 Providers
curl http://localhost:8000/control/v1/providers \
  -H "X-Admin-Token: $TOKEN"
```

#### Model 管理

```bash
# 创建 Model（假设 provider_id=1）
curl -X POST http://localhost:8000/control/v1/models \
  -H "X-Admin-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": 1,
    "upstream_model": "deepseek-ai/DeepSeek-V3",
    "alias": "deepseek-v3",
    "enabled": true,
    "capabilities": ["chat"]
  }'
```

#### Profile 管理

```bash
# 创建 Profile
curl -X POST http://localhost:8000/control/v1/profiles \
  -H "X-Admin-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "默认配置", "description": "通用场景"}'

# 绑定模型到 Profile（假设 profile_id=1, model_ids=[1,2]）
curl -X POST http://localhost:8000/control/v1/profiles/1/bindings \
  -H "X-Admin-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_ids": [1, 2]}'
```

#### Node 管理

```bash
# 创建 Node
curl -X POST http://localhost:8000/control/v1/nodes \
  -H "X-Admin-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "节点-1",
    "profile_id": 1,
    "sync_mode": "pull",
    "active": true
  }'
# 返回包含 pull_token

# 拉取节点配置
curl http://localhost:8000/control/v1/nodes/1/openclaw-json \
  -H "Authorization: Bearer 节点PullToken"

# 轮换 Token
curl -X POST http://localhost:8000/control/v1/nodes/1/sync-token/rotate \
  -H "X-Admin-Token: $TOKEN"
```

---

## 节点同步代理

使用 `scripts/node_sync_agent.py` 保持节点配置自动同步：

```bash
python scripts/node_sync_agent.py \
  --base-url http://127.0.0.1:8000 \
  --node-id 1 \
  --pull-token zg_node_1_xxx \
  --output /etc/openclaw/openclaw.json \
  --interval 60 \
  --reload-cmd "systemctl restart openclaw"
```

---

## Provider 初始化助手

使用 `scripts/bootstrap_provider.py` 快速注册 Provider 和模型：

```bash
python scripts/bootstrap_provider.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token "$ZHAOCAI_ADMIN_TOKEN" \
  --name siliconflow \
  --provider-type openai \
  --provider-base-url https://api.siliconflow.cn/v1 \
  --auth-scheme bearer \
  --api-key "sk-xxx" \
  --models "deepseek-ai/DeepSeek-V3,deepseek-ai/DeepSeek-R1"
```

---

## Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f zhaocai

# 停止
docker-compose down
```

---

## 配置说明

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `ZHAOCAI_ENCRYPTION_KEY` | 推荐 | API Key 加密密钥（Fernet），留空则不启用静态加密 |
| `ZHAOCAI_ADMIN_TOKEN` | ✅ | 管理接口认证 Token |
| `ZHAOCAI_PORT` | ❌ | 服务端口（默认8000）|
| `ZHAOCAI_CORS_ORIGINS` | ❌ | CORS 允许来源 |
| `OPENAI_API_KEY` | ❌ | OpenAI API Key |
| `ANTHROPIC_API_KEY` | ❌ | Anthropic API Key |
| ... | ... | 其他 Provider API Keys |

### 配置文件

`config.yaml` 用于配置：
- 网关监听地址
- Provider 列表和路由策略
- 限流参数

---

## OpenClaw Skill

本仓库包含一个 OpenClaw Skill：

`./.codex/skills/openclaw-gateway-manager`

包含：
- SKILL.md 工作流文档
- API 和 JSON 映射参考
- 配置拉取和验证脚本

---

## 注意事项

- 控制面板数据库默认使用 SQLite: `ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db`
- PostgreSQL 后端预留但未实现
- 流式模式通过合成非流式上游响应实现 SSE 格式
- 首次启动会执行 Provider 健康检查

---

## 技术栈

- **后端**: Python 3.11+, FastAPI, Uvicorn
- **数据库**: SQLite (PostgreSQL 预留)
- **HTTP 客户端**: httpx
- **配置**: PyYAML, python-dotenv
- **安全**: cryptography (Fernet 加密)

---

## License

MIT
