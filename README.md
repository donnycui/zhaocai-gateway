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

同时，仓库里仍保留了旧版 `gateway.py` / `control_plane/` 运行时，作为 legacy 兼容层存在。

## 当前模块结构

当前后台已经拆成四个资源模块：

- `OpenClaw`
  - 管理节点同步、设备配对、模型分配和 `openclaw.json` 下发
- `Gateway`
  - 管理统一对外模型供给、上游账号、稳定别名、failover 和项目接入 key
- `Media`
  - 管理 `zhaocai-media` 使用的独立 Provider 与媒体模板
- `Universal`
  - 只做模板池，可导入到其他模块，但导入后各模块独立管理

当前 Web 资源中心已经能看到这四个模块，其中 `OpenClaw`、`Gateway`、`Media`、`Universal` 都有最小可用实现。

## 当前已完成能力

### v2.0 phase 1 scaffold

- OpenClaw Provider 管理
  - `GET /admin/providers`
  - `POST /admin/providers`
  - `POST /admin/providers/validate`

- OpenClaw Model 管理
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
  - Resource Center
  - Devices
  - Nodes

- Node agent
  - `register`
  - `sync-once`
  - `run`

### Gateway module

- Gateway Upstream Accounts
  - `GET /admin/gateway/accounts`
  - `POST /admin/gateway/accounts`
  - `POST /admin/gateway/accounts/{id}/test`
  - `POST /admin/gateway/accounts/{id}/sync-models`

- Gateway Aliases
  - `GET /admin/gateway/aliases`
  - `POST /admin/gateway/aliases`
  - `PATCH /admin/gateway/aliases/{id}`
  - `GET /admin/gateway/aliases/{id}/targets`
  - `PUT /admin/gateway/aliases/{id}/targets`

- Gateway Client Keys
  - `GET /admin/gateway/client-keys`
  - `POST /admin/gateway/client-keys`
  - `PATCH /admin/gateway/client-keys/{id}`

- Gateway Runtime
  - `POST /v1/chat/completions`
  - `POST /v1/responses`
  - alias-based upstream routing
  - timeout / network / `5xx` / `429` failover

### Media module

- Media Providers
  - `GET /admin/media/providers`
  - `POST /admin/media/providers`

- Media Templates
  - `GET /admin/media/templates`
  - `POST /admin/media/templates`
  - `POST /admin/media/templates/validate`

- Media Catalog
  - `GET /admin/media/catalog`

### Universal template pool

- Universal Templates
  - `GET /admin/universal/templates`
  - `POST /admin/universal/templates`
  - `POST /admin/universal/templates/{id}/import/openclaw`
  - `POST /admin/universal/templates/{id}/import/gateway`
  - `POST /admin/universal/templates/{id}/import/media`

### 旧版 runtime 仍可用

仓库中仍保留旧能力，包括：

- `/v1/chat/completions`
- `/v1/responses`
- 旧控制面 CRUD
- OpenRouter free model sync

这些逻辑仍主要在：

- `gateway.py`（legacy fallback）
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

### 主从关系

`node-agent` 是 `zhaocai-gateway v2` 体系中的一个**子模块**，不是完整 gateway。

可以把当前结构理解成：

```text
Raspberry Pi
  = zhaocai_gateway/ + web/
  = 主控服务 / 配置源 / 控制面

Mac / VPS / Other Nodes
  = agent/
  = 节点客户端 / 配置同步执行端
```

也就是说：

- 只有树莓派运行完整 `zhaocai_gateway.main`
- 其他机器只运行 `agent`
- `agent` 不持有控制面职责，只负责注册、拉配置、写本地 OpenClaw 配置

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

如果你想保留旧版配置驱动方式，也可以继续准备：

```bash
cp config.example.yaml config.yaml
```

### 3. 启动 v2 后端

当前推荐主入口：

```bash
.venv/bin/python -m zhaocai_gateway.main
```

默认会读取：

- `ZHAOCAI_HOST`
- `ZHAOCAI_PORT`
- `ZHAOCAI_CONTROL_DB`
- `ZHAOCAI_WEB_DIST`

说明：

- `zhaocai_gateway.main` 是当前分支的推荐启动方式
- 如果 `web/dist` 存在，后端可以直接托管前端静态文件
- `gateway.py` 仍然保留，但现在应视为 legacy fallback

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

如果你想让后端直接托管前端静态文件，先构建：

```bash
cd web
npm run build
cd ..
.venv/bin/python -m zhaocai_gateway.main
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

推荐安装后台常驻服务：

```bash
.venv/bin/python -m agent.cli install
```

运行安装自检：

```bash
.venv/bin/python -m agent.cli doctor
```

如果需要显式指定服务管理器：

Linux `systemd` 用户服务文件：

```bash
.venv/bin/python -m agent.cli install-systemd
```

macOS `launchd` plist：

```bash
.venv/bin/python -m agent.cli install-launchd
```

`install` 会根据当前平台自动选择：

- `Linux -> systemd`
- `macOS -> launchd`

`doctor` 会检查：

- agent 配置文件是否存在
- OpenClaw 配置目录是否可写
- `openclaw gateway restart` 是否可执行
- `systemd/launchd` 服务文件是否已经生成
- `~/.zhaocai-gateway` 工作目录是否可写

### 6. 节点接入实操

下面这套流程适合：

- 树莓派运行控制面
- Mac / VPS 运行 OpenClaw
- 节点通过 `node-agent` 拉取模型相关配置

在开始之前，先在控制面里完成两件事：

1. 在 `节点接入` 页面创建目标设备
2. 为该设备签发一次性 `pairing token`

同时准备好你的控制面地址，推荐直接使用 Tailscale 地址，例如：

- `https://raspberrypi.tailnet.ts.net`

#### Mac 节点

首次准备：

```bash
git clone git@github.com:donnycui/zhaocai-gateway.git
cd zhaocai-gateway
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

注册并立即同步一次：

```bash
.venv/bin/python -m agent.cli register \
  --server https://raspberrypi.tailnet.ts.net \
  --token YOUR_PAIRING_TOKEN

.venv/bin/python -m agent.cli sync-once
```

检查本机是否具备常驻运行条件：

```bash
.venv/bin/python -m agent.cli doctor
```

安装为 macOS 后台服务：

```bash
.venv/bin/python -m agent.cli install
```

安装命令会生成：

- `~/Library/LaunchAgents/com.zhaocai.agent.plist`

然后按 CLI 输出执行：

```bash
launchctl unload ~/Library/LaunchAgents/com.zhaocai.agent.plist >/dev/null 2>&1 || true
launchctl load ~/Library/LaunchAgents/com.zhaocai.agent.plist
```

#### Linux / VPS 节点

首次准备：

```bash
git clone git@github.com:donnycui/zhaocai-gateway.git
cd zhaocai-gateway
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

注册并立即同步一次：

```bash
.venv/bin/python -m agent.cli register \
  --server https://raspberrypi.tailnet.ts.net \
  --token YOUR_PAIRING_TOKEN

.venv/bin/python -m agent.cli sync-once
```

运行自检：

```bash
.venv/bin/python -m agent.cli doctor --service-manager systemd
```

安装为 `systemd` 用户服务：

```bash
.venv/bin/python -m agent.cli install --service-manager systemd
```

安装命令会生成：

- `~/.config/systemd/user/zhaocai-agent.service`

然后按 CLI 输出执行：

```bash
systemctl --user daemon-reload
systemctl --user enable --now zhaocai-agent.service
systemctl --user status zhaocai-agent.service
```

#### 每次配置更新后会发生什么

`node-agent` 每次拿到新配置后会自动：

1. 合并写入本机 `~/.openclaw/openclaw.json`
2. 仅更新模型相关区块
3. 执行：

```bash
openclaw gateway restart
```

如果你想先手动验证，也可以直接运行：

```bash
.venv/bin/python -m agent.cli sync-once
```

成功时会看到类似输出：

```text
sync updated version=3 etag="..."
backup=/Users/yourname/.openclaw/openclaw.json.bak
```

如果你希望保留某些本地 provider / model，不想被同步覆盖，优先推荐直接在后台 `Devices` 页面编辑该设备的 preserve 配置。

- `~/.openclaw/zhaocai-preserve.json`

控制面保存后，agent 会在下次同步时自动写入这个文件。

如果你需要在节点上应急手动处理，也可以直接编辑它。

示例：

```json
{
  "preserveProviders": ["zhipu", "custom-local"],
  "preserveModels": ["zhipu/glm-4-plus", "custom-local/dev-model"]
}
```

当前 `node-agent` 会：

- 保留 sidecar 中声明的 provider / model
- 刷新网关托管的模型区块
- 不在 `openclaw.json` 本体中写入额外自定义字段

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
  - legacy fallback runtime
- [control_plane/](control_plane/)
- [providers/](providers/)
- [responses/](responses/)

### legacy cleanup note

如果生产已经切到 `v2`：

- 旧目录建议先保留为**回滚备份**
- 不要在确认稳定前立即删除
- 推荐等 `v2` 连续稳定运行一段时间后，再压缩归档或移除旧目录

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

GET    /admin/gateway/accounts
POST   /admin/gateway/accounts
POST   /admin/gateway/accounts/{id}/test
POST   /admin/gateway/accounts/{id}/sync-models

GET    /admin/gateway/aliases
POST   /admin/gateway/aliases
PATCH  /admin/gateway/aliases/{id}
GET    /admin/gateway/aliases/{id}/targets
PUT    /admin/gateway/aliases/{id}/targets

GET    /admin/gateway/client-keys
POST   /admin/gateway/client-keys
PATCH  /admin/gateway/client-keys/{id}

GET    /admin/media/providers
POST   /admin/media/providers
GET    /admin/media/templates
POST   /admin/media/templates
POST   /admin/media/templates/validate
GET    /admin/media/catalog

GET    /admin/universal/templates
POST   /admin/universal/templates
POST   /admin/universal/templates/{id}/import/openclaw
POST   /admin/universal/templates/{id}/import/gateway
POST   /admin/universal/templates/{id}/import/media
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

## Gateway Consumer Integration

对于 `Content-IP-Strategy` 这类项目，推荐接入方式已经收敛为：

- 一个 `baseUrl`
- 一个 `Gateway client key`
- 一组稳定 alias

项目侧不再直接管理：

- 上游 provider 连接
- 真实 API key
- 真实 base URL
- 真实模型切换策略

推荐做法是让项目只保存：

- `SIGNAL_SCORING -> signal/deep`
- `DRAFT_GENERATION -> draft/deep`
- `TOPIC_GENERATION -> balanced`

然后由 `zhaocai-gateway-v2` 在内部决定：

- `signal/deep` 当前映射到哪个真实模型
- 这个别名下面挂了哪些上游 target
- 某个上游超时、`5xx` 或 `429` 时如何自动切到下一个 target

当前 Gateway runtime 支持：

- `Authorization: Bearer <gateway-client-key>`
- `x-api-key: <gateway-client-key>`

并要求先在后台创建启用中的 `Gateway client key`。

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
npm run typecheck
npm run build
```

另外，当前分支已经额外通过以下验证：

```bash
.venv/bin/python -m pytest tests/test_gateway_accounts_api.py \
  tests/test_gateway_alias_api.py \
  tests/test_gateway_failover.py \
  tests/test_gateway_client_keys_api.py \
  tests/test_media_template_api.py \
  tests/test_media_catalog.py \
  tests/test_universal_templates_api.py -v
```

并完成过一次项目接入烟测，验证了：

- 创建 Gateway Upstream Account
- 同步真实模型
- 创建 alias 与 target
- 创建 Gateway client key
- 通过 `Authorization: Bearer <gateway-client-key>` 调 `/v1/chat/completions`
- alias 最终被解析为真实上游模型

## 设计与计划文档

- [v2 设计文档](docs/plans/2026-03-25-zhaocai-gateway-v2-design.md)
- [v2 实现计划](docs/plans/2026-03-25-zhaocai-gateway-v2-implementation-plan.md)
- [模块化 Provider 设计](docs/plans/2026-03-31-zhaocai-gateway-v2-modular-provider-design.md)
- [模块化 Provider 实施计划](docs/plans/2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md)
