# Hermes Module Design

## 目标

在当前 `zhaocai-gateway` 资源中心中新增一个独立的 `Hermes` 模块，使其具备和 `OpenClaw` 类似的中心化配置与节点同步能力，但目标产物不是 `openclaw.json`，而是：

- `~/.hermes/config.yaml`
- `~/.hermes/plugins/model-providers/<provider>/__init__.py`

同时提供一个快捷能力：

- 从 `OpenClaw` provider 一键复制 `base_url + api_key` 到 `Hermes` provider

## 为什么要独立成模块

`Hermes` 的 provider 配置语义和 `OpenClaw` 有本质差异：

- `Hermes` 的主配置是 YAML
- `Hermes` 存在用户 provider 插件
- 某些中转站只在插件 `default_headers` 下可正常工作
- 模型名格式要求是 `provider_name/model-id`

如果复用 `OpenClaw` 的 provider / device 表，会把两套运行时语义搅在一起。  
因此 `Hermes` 应作为资源中心的第五个模块，与：

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

并列存在。

## 设计原则

1. `Hermes` 与 `OpenClaw` 独立建模
- `OpenClaw` 继续只负责 OpenClaw 节点同步
- `Hermes` 自己维护 provider、模型、节点和快照

2. 允许从 `OpenClaw` 导入，但导入后独立
- 一键导入只复制基础信息
- 导入后 `Hermes` 的记录不与 `OpenClaw` 联动回写

3. 插件能力受控
- 不允许任意 Python 脚本
- 只允许生成固定模板的 provider 插件
- 当前只支持：
  - `none`
  - `default_headers`

4. 第一版优先最小闭环
- provider 管理
- 模型管理
- 设备管理
- 节点同步
- 配置预览
- 不先做复杂插件生态

## 模块范围

### 1. Hermes Providers

每个 Hermes provider 需要保存：

- `name`
- `base_url`
- `api_key`
- `enabled`
- `notes`
- `plugin_mode`
  - `none`
  - `default_headers`
- `default_headers_json`
- `source_openclaw_provider_id`（可选）

作用：
- `plugin_mode = none`
  - 只写入 `config.yaml`
- `plugin_mode = default_headers`
  - 额外生成固定模板的 provider 插件文件

### 2. Hermes Models

每个 Hermes 模型需要保存：

- `provider_id`
- `upstream_model`
- `display_name`
- `enabled`

最终编译时会生成：

```yaml
providers:
  provider_name:
    base_url: https://relay.example.com/v1
    api_key: sk-xxxx

model:
  default: provider_name/model-id
```

模型引用名采用：

- `provider_name/upstream_model`

### 3. Hermes Devices

Hermes 也做成和 OpenClaw 类似的节点同步体系：

- 创建设备
- 设备签发 pairing token
- agent 注册
- agent 拉配置
- agent 回报应用状态

与 OpenClaw 差异在于：
- 输出目录改为 `~/.hermes/`
- 重载命令改为：
  - `systemctl --user restart hermes-gateway`
  - `systemctl --user restart hermes-webui`

### 4. Hermes Config Snapshots

每次设备配置编译后，保存 Hermes 设备专属快照：

- `version`
- `etag`
- `content_hash`
- `payload_json`

这里的 `payload_json` 建议结构为：

```json
{
  "config_yaml": "...",
  "plugin_files": {
    "provider_name": "python source..."
  }
}
```

这样 agent 同步时不需要再次做模板展开。

## 数据模型

建议新增这些表：

### `hermes_providers`
- `id`
- `name`
- `base_url`
- `api_key_encrypted`
- `enabled`
- `notes`
- `plugin_mode`
- `default_headers_json`
- `source_openclaw_provider_id`
- `created_at`
- `updated_at`

### `hermes_models`
- `id`
- `provider_id`
- `upstream_model`
- `display_name`
- `enabled`
- `created_at`
- `updated_at`

### `hermes_devices`
- `id`
- `name`
- `device_type`
- `hostname`
- `platform`
- `active`
- `last_seen_at`
- `sync_token_hash`
- `current_config_version`
- `created_at`

### `hermes_device_model_bindings`
- `device_id`
- `model_id`
- `priority`

### `hermes_pairing_tokens`
- `id`
- `device_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

### `hermes_config_snapshots`
- `id`
- `device_id`
- `version`
- `etag`
- `payload_json`
- `content_hash`
- `created_at`

## 配置编译

### 1. `config.yaml`

对单台 Hermes 设备，编译后至少包含：

```yaml
providers:
  provider_name:
    base_url: https://relay.example.com/v1
    api_key: sk-xxxx

model:
  default: provider_name/model-a
  fallbacks:
    - provider_name/model-b
    - another_provider/model-c
```

如果 Hermes 不支持 `fallbacks` 的正式键，则第一版只输出：

- `model.default`

并把优先级高的第一个模型作为默认模型。

### 2. provider 插件文件

当 provider 配置了：

- `plugin_mode = default_headers`

时，额外生成：

- `~/.hermes/plugins/model-providers/<provider_name>/__init__.py`

模板固定为：

```python
from providers import ProviderProfile, register_provider

register_provider(
    ProviderProfile(
        name="your_provider",
        display_name="Your Provider",
        base_url="https://your-relay.example.com/v1",
        hostname="your-relay.example.com",
        default_headers={
            "User-Agent": "claude-code/0.1.0",
            "HTTP-Referer": "https://hermes-agent.nousresearch.com",
            "X-Title": "Hermes",
        },
    )
)
```

其中：
- `default_headers` 从 `default_headers_json` 渲染
- `hostname` 从 `base_url` 自动提取

## 一键从 OpenClaw 导入

在 Hermes provider 列表里增加：

- `从 OpenClaw 导入`

行为：

1. 选择一个现有 `OpenClaw provider`
2. 自动复制：
   - `name`
   - `base_url`
   - `api_key`
3. Hermes provider 默认：
   - `plugin_mode = none`
   - `default_headers_json = {}`
4. 记录：
   - `source_openclaw_provider_id`

这一步的目的不是共享 provider，而是减少重复录入。

## API 设计

### Hermes Providers
- `GET /admin/hermes/providers`
- `POST /admin/hermes/providers`
- `GET /admin/hermes/providers/{id}`
- `PATCH /admin/hermes/providers/{id}`
- `DELETE /admin/hermes/providers/{id}`
- `POST /admin/hermes/providers/import-openclaw`

### Hermes Models
- `GET /admin/hermes/models`
- `POST /admin/hermes/models`
- `PATCH /admin/hermes/models/{id}`
- `DELETE /admin/hermes/models/{id}`

### Hermes Devices
- `GET /admin/hermes/devices`
- `POST /admin/hermes/devices`
- `PATCH /admin/hermes/devices/{id}`
- `DELETE /admin/hermes/devices/{id}`
- `PUT /admin/hermes/devices/{id}/models`
- `GET /admin/hermes/devices/{id}/config-preview`
- `POST /admin/hermes/devices/{id}/pairing-token`

### Hermes Agent
- `POST /hermes-agent/v1/register`
- `POST /hermes-agent/v1/heartbeat`
- `GET /hermes-agent/v1/config/meta`
- `GET /hermes-agent/v1/config`
- `POST /hermes-agent/v1/config/applied`

## Web UI 设计

资源中心新增 `Hermes` 页签，包含三块：

### 1. Hermes Providers
- 新增 / 编辑 / 删除
- 配置 `plugin_mode`
- 配置 `default_headers_json`
- 从 OpenClaw 导入

### 2. Hermes Models
- 新增 / 编辑 / 删除
- 选择 provider
- 指定 `upstream_model`
- 指定 `display_name`

### 3. Hermes Nodes
- 创建设备
- 签发 token
- 绑定模型
- 预览编译结果

## Agent 设计

推荐扩展当前 Python `agent`，增加 Hermes 目标模式：

- `register --target hermes`
- `sync-once --target hermes`
- `run --target hermes`

同步行为：

1. 拉 Hermes 设备配置
2. 写入：
   - `~/.hermes/config.yaml`
   - `~/.hermes/plugins/model-providers/...`
3. 触发重载：
   - `systemctl --user restart hermes-gateway`
   - `systemctl --user restart hermes-webui`

## 风险与边界

### 1. Hermes 本身配置格式可能继续演进
需要尽量把生成逻辑限制在：
- 当前确认稳定的 provider 配置
- 当前确认稳定的 provider plugin 形式

### 2. 不做任意 Python 插件
第一版不允许用户随意写 Python，是为了避免：
- 安全问题
- 不可验证脚本
- 无法稳定同步

### 3. 不复用 OpenClaw 的设备表
避免：
- 一个设备同时承担 OpenClaw/Hermes 两种节点语义时状态混乱

## 第一版交付标准

完成后应满足：

1. 资源中心能看到独立 `Hermes` 板块
2. 能新增 Hermes provider
3. 能从 OpenClaw 一键导入 provider
4. 能配置是否生成 `default_headers` 插件
5. 能为 Hermes 节点下发 `config.yaml`
6. 能为需要的 provider 下发插件文件
7. Hermes 节点能自动重启并应用配置
