# Zhaocai Gateway

招财网关当前正在向 `v2.0 phase 1` 演进。

这一阶段的目标不是做本地 provider 切换器，而是做一个部署在树莓派上的**中心控制面**：

- 统一保存上游 provider、URL、API key、models
- 统一管理设备注册与配对
- 按设备分配模型
- 由本地 `node-agent` 拉取专属配置并写入 OpenClaw 本地配置

当前分支已经包含 `phase 1` 的最小可用骨架：

- 新的后端包：`zhaocai_gateway/`
- 最小 Web 管理台：`web/`
- 最小 node agent：`agent/`

同时，仓库里仍保留了旧版 `gateway.py` / `control_plane/` 运行时，方便兼容现有能力与逐步迁移。

## 当前已完成能力

### v2.0 phase 1 scaffold

- Provider 管理
  - `GET /admin/providers`
  - `POST /admin/providers`
  - `POST /admin/providers/validate`

- Model 管理
  - `GET /admin/models`
  - `POST /admin/models`

- Device 管理
  - `GET /admin/devices`
  - `POST /admin/devices`
  - `PUT /admin/devices/{id}/models`
  - `GET /admin/devices/{id}/config-preview`

- Pairing / Agent
  - `POST /admin/devices/{id}/pairing-token`
  - `POST /agent/v1/register`
  - `POST /agent/v1/heartbeat`
  - `GET /agent/v1/config/meta`
  - `GET /agent/v1/config`
  - `POST /agent/v1/config/applied`

- Config compiler
  - 按设备编译 provider + model payload
  - snapshot version / etag
  - 内容不变时版本不递增

- Web UI
  - Dashboard
  - Providers
  - Devices
  - Nodes

- Node agent
  - `register`
  - `sync-once`
  - `run`

### 旧版 runtime 仍可用

仓库中仍保留旧能力，包括：

- `/v1/chat/completions`
- `/v1/responses`
- 旧控制面 CRUD
- OpenRouter free model sync

这些逻辑仍主要在：

- `gateway.py`
- `control_plane/`
- `providers/`
- `responses/`

## 推荐部署形态

### phase 1

推荐使用：

- 树莓派运行 `zhaocai-gateway`
- Mac / VPS / 其他机器运行 `node-agent`
- 所有设备通过 Tailscale 或其他私网方式访问树莓派

phase 1 的重点是**控制面 + 配置同步**，不是“所有推理都必须经过树莓派”。

也就是说：

- 树莓派负责 provider / model / device 的统一管理
- 节点从树莓派拉取自己的配置
- 节点本地 OpenClaw 继续读取本地配置文件

后续如果需要，再扩展到混合模式：

- 某些模型由节点本地直连上游
- 某些模型通过树莓派中心网关转发

## 快速开始

### 1. Python 环境

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

### 2. 准备环境变量

```bash
cp .env.example .env
```

至少设置：

```bash
ZHAOCAI_ADMIN_TOKEN=replace-me
ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db
```

如果你要继续跑旧版 `gateway.py` 兼容路径，也可以保留：

```bash
cp config.example.yaml config.yaml
```

### 3. 启动后端

当前分支仍沿用：

```bash
.venv/bin/python gateway.py
```

说明：

- 旧版 `gateway.py` 仍然是当前统一入口
- `zhaocai_gateway/` 已经接入了新的 `create_app()` 骨架与 v2 API
- 后续可以再把入口彻底切换到纯 v2 结构

### 4. 启动 Web 管理台

```bash
cd web
npm install
npm run dev
```

默认开发地址通常是：

- `http://127.0.0.1:4173`

前端会访问同机后端的 `/admin` 与 `/agent` 路径。

生产构建：

```bash
cd web
npm run build
```

### 5. 使用 node-agent

注册节点：

```bash
.venv/bin/python -m agent.cli register \
  --server http://127.0.0.1:8000 \
  --token YOUR_PAIRING_TOKEN
```

单次同步：

```bash
.venv/bin/python -m agent.cli sync-once
```

持续轮询：

```bash
.venv/bin/python -m agent.cli run --interval 60
```

## Repo Layout

### v2.0 phase 1

- [zhaocai_gateway/](zhaocai_gateway/)
  - 新的后端包结构
- [web/](web/)
  - 最小 React/Vite 管理台
- [agent/](agent/)
  - 节点注册与同步客户端
- [tests/](tests/)
  - 当前 v2 后端测试

### legacy runtime

- [gateway.py](gateway.py)
- [control_plane/](control_plane/)
- [providers/](providers/)
- [responses/](responses/)

## API 摘要

### Admin

```bash
GET    /admin/providers
POST   /admin/providers
POST   /admin/providers/validate

GET    /admin/models
POST   /admin/models

GET    /admin/devices
POST   /admin/devices
PUT    /admin/devices/{id}/models
GET    /admin/devices/{id}/config-preview
POST   /admin/devices/{id}/pairing-token
```

### Agent

```bash
POST   /agent/v1/register
POST   /agent/v1/heartbeat
GET    /agent/v1/config/meta
GET    /agent/v1/config
POST   /agent/v1/config/applied
```

## 配置同步流程

1. 在 Web UI 新建设备
2. 生成一次性 pairing token
3. 在目标机器执行 `node-agent register`
4. agent 获得长期 `sync_token`
5. 通过 `config/meta -> config` 检查并拉取最新配置
6. 本地原子写入 OpenClaw 配置
7. 成功后回报 `config/applied`

## 网络建议

推荐默认使用 Tailscale：

- 不要求树莓派有公网 IP
- Mac / VPS / 树莓派都在同一 tailnet
- 更适合 phase 1 的控制面与配置同步场景

如果后面开启混合模式，再单独评估哪些模型需要走中心转发。

## 当前验证状态

当前分支已经通过：

```bash
.venv/bin/python -m pytest tests/test_schema.py \
  tests/test_provider_api.py \
  tests/test_device_api.py \
  tests/test_pairing_api.py \
  tests/test_config_compiler.py \
  tests/test_agent_sync.py \
  tests/test_agent_runtime.py -v
```

以及：

```bash
cd web
npm run build
```

## 设计与计划文档

- [v2 设计文档](docs/plans/2026-03-25-zhaocai-gateway-v2-design.md)
- [v2 实现计划](docs/plans/2026-03-25-zhaocai-gateway-v2-implementation-plan.md)
