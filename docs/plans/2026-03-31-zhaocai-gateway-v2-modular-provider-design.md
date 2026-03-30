# Zhaocai Gateway v2 Modular Provider Design

**Date:** 2026-03-31
**Project:** `zhaocai-gateway-v2`

## 1. 目标

把当前 `zhaocai-gateway-v2` 从“单一 Provider / Model / Device 控制面”演进成一个分模块的模型基础设施后台，同时保持当前已经完成并验证过的 OpenClaw 节点同步主线稳定可用。

这次设计要解决四件事：

1. 保留并增强 OpenClaw 节点同步能力
2. 增加统一对外模型转发能力，给 `Content-IP-Strategy` 等项目使用
3. 增加 `zhaocai-media` 使用的独立 Provider 与模板管理能力
4. 提供一个 `Universal` 模板池，提高多模块复用效率，但不引入共享修改风险

## 2. 当前确认结论

### 2.1 OpenClaw 主线

当前仓库中已经完成并验证过的主线是：

- Provider 管理
- Model 管理
- Device 配对
- Node agent 同步
- OpenClaw 配置编译
- Web 控制台

这条线继续保留，视为 `OpenClaw` 模块。

### 2.2 Content-IP-Strategy 的定位

`Content-IP-Strategy` 不再负责维护上游 Provider、真实 API key、真实 base URL。

它未来只保留：

- 业务能力后台
- 能力到模型别名的路由配置

真实模型供给统一由 `zhaocai-gateway-v2` 提供。

项目侧接入方式收敛为：

- 一个统一 `baseUrl`
- 一个统一 `apiKey`
- 一组稳定模型别名

### 2.3 Media 的定位

`zhaocai-media` 使用的 Provider 与模板，不与 OpenClaw 的普通文本模型主线混用。

`Media` 模块需要独立的数据结构和管理界面。

### 2.4 Universal 的定位

`Universal` 只是模板池，不是共享运行时资源。

规则是：

- `Universal` 里的配置可以导入到 `OpenClaw`
- `Universal` 里的配置可以导入到 `Gateway`
- `Universal` 里的配置可以导入到 `Media`

导入之后，各模块独立管理，互不联动。

## 3. 顶层信息架构

后台拆成 4 个顶层模块：

1. `Universal`
2. `OpenClaw`
3. `Gateway`
4. `Media`

### 3.1 Universal

用途：

- 保存可复用的供应商模板
- 快速导入到具体模块

不承担：

- 运行时路由
- 真实请求转发
- 节点同步

### 3.2 OpenClaw

用途：

- 设备管理
- 模型分配
- agent 配对
- 节点同步
- OpenClaw 配置编译

它管理的是：

- 哪些设备可用哪些模型
- 节点最终收到的 `openclaw.json`

### 3.3 Gateway

用途：

- 对外统一提供模型访问入口
- 统一管理上游账号
- 管理稳定别名
- 管理 fallback / failover
- 给外部项目发放统一接入 key

它管理的是：

- 外部项目通过哪个 `url + apiKey` 调网关
- 一个稳定别名最终指向哪些真实模型和上游账号
- 上游挂掉时如何自动切换到备用 target

### 3.4 Media

用途：

- 管理 `zhaocai-media` 所需上游 Provider
- 管理复杂媒体模板
- 导出供 `zhaocai-media` 和网站消费的 media catalog

它管理的是：

- 图片、视频、TTS 等复杂媒体能力
- 这些能力背后的模板与参数结构

## 4. 模块边界

### 4.1 不允许默认跨模块混用

以下情况默认不成立：

- OpenClaw Provider 自动可用于 Gateway
- Gateway 上游账号自动可用于 Media
- Media Provider 自动可用于 OpenClaw

原因：

- 有些供应商只适合 OpenClaw
- 有些媒体供应商不适合 OpenClaw
- Gateway 有独立的接入账号与 fallback 语义

### 4.2 允许通过 Universal 导入复用

如果某个供应商模板确实可复用，应通过 `Universal` 导入到目标模块。

导入后的目标记录：

- 可以继续编辑
- 可以独立启停
- 不受原模板后续修改影响

## 5. Gateway 模块设计

## 5.1 设计目标

让 `zhaocai-gateway-v2` 成为统一模型供给层，对外暴露：

- 一个统一 `baseUrl`
- 一个统一 `apiKey`
- 一组稳定模型别名

内部负责：

- 上游账号管理
- 模型同步
- 稳定别名管理
- fallback 与 failover

## 5.2 核心对象

### 5.2.1 Gateway Upstream Account

表示一个真实上游连接，例如公益站、代理站、官方站。

建议字段：

- `id`
- `name`
- `base_url`
- `auth_type`
- `api_key_encrypted`
- `protocol`
- `enabled`
- `health_status`
- `cooldown_until`
- `last_checked_at`
- `notes`

### 5.2.2 Gateway Model

表示从某个上游账号同步下来的真实模型。

建议字段：

- `id`
- `account_id`
- `upstream_model`
- `display_name`
- `family`
- `supports_chat`
- `supports_responses`
- `enabled`
- `created_at`
- `updated_at`

### 5.2.3 Gateway Alias

表示一个对外稳定模型名。

建议字段：

- `id`
- `alias_key`
- `display_name`
- `alias_type`
- `enabled`
- `visibility`
- `notes`

示例：

- `fast`
- `balanced`
- `deep`
- `signal/deep`
- `draft/deep`

### 5.2.4 Gateway Alias Target

表示一个别名下的候选真实 target 列表项。

建议字段：

- `id`
- `alias_id`
- `account_id`
- `model_id`
- `priority`
- `enabled`
- `fallback_on_timeout`
- `fallback_on_5xx`
- `fallback_on_429`
- `cooldown_seconds`
- `created_at`
- `updated_at`

### 5.2.5 Gateway Client Key

表示给外部项目使用的接入 key。

建议字段：

- `id`
- `name`
- `api_key_hash`
- `enabled`
- `notes`
- `created_at`
- `updated_at`

第一版可以先只支持极简模式：

- 一把 `Content-IP-Strategy` 专用 key

### 5.2.6 Gateway Target Health Event

表示上游 target 的失败记录与健康事件。

建议字段：

- `id`
- `account_id`
- `model_id`
- `alias_id`
- `status`
- `failure_type`
- `message`
- `created_at`

## 5.3 Gateway 中两类“账号”的区分

为了避免歧义，产品语义上区分为：

- 上游账号
  - 公益站、代理站、官方站的真实连接
- 接入账号
  - 外部项目访问 `zhaocai-gateway-v2` 时使用的 key

这两类账号不能混为一谈。

## 5.4 Gateway fallback 机制

### 5.4.1 目标

支持同一个稳定别名下面挂多个候选真实 target。

例如：

- `gpt-5.4 -> 公益站A/gpt-5.4`
- `gpt-5.4 -> 公益站B/gpt-5.4`
- `gpt-5.4 -> 公益站C/gpt-5.4`

当公益站 A 出现异常时，自动切到 B，再不行再切到 C。

### 5.4.2 第一版自动切换触发条件

仅在以下情况触发自动 fallback：

- 连接失败
- 请求超时
- DNS / TLS / 网络错误
- `5xx`
- `429`

### 5.4.3 第一版不自动 fallback 的情况

以下情况不自动切换：

- 明显请求参数错误
- 鉴权错误
- 模型名错误
- 明显调用方导致的大多数 `4xx`

原因是这些错误更像调用方问题，不应被自动切换掩盖。

### 5.4.4 冷却策略

当某个 target 连续失败后：

- 记录失败事件
- 设置短期冷却
- 冷却期内优先跳过该 target

## 5.5 Content-IP-Strategy 与 Gateway 的边界

`Content-IP-Strategy` 只负责：

- 业务能力到稳定别名的映射

例如：

- `signal_scoring -> signal/deep`
- `draft_generation -> draft/deep`
- `topic_generation -> balanced`

`zhaocai-gateway-v2` 负责：

- `signal/deep -> gpt-5.4 alias`
- `gpt-5.4 alias -> 公益站A/gpt-5.4 -> 公益站B/gpt-5.4`

也就是说：

- 项目不再知道真实 Provider
- 项目不再知道真实 API key
- 项目不再直接知道真实模型切换细节

## 6. OpenClaw 模块调整

## 6.1 当前问题

当前 `agent/openclaw_writer.py` 会直接替换：

- `models.providers`
- `agents.defaults.model`
- `agents.defaults.models`

这会导致本地希望保留的 provider / model 也被覆盖掉。

## 6.2 不采用在 openclaw.json 中写额外字段

不建议直接在 `openclaw.json` 的 provider / model 上加：

- `managedBy`
- `preserve`

原因：

- 无法确认 OpenClaw 运行时是否完全容忍额外字段
- 有潜在兼容性风险

## 6.3 采用 sidecar 文件方案

在 `openclaw.json` 旁边新增一个 sidecar 文件，例如：

- `~/.openclaw/zhaocai-preserve.json`

用途：

- 只给 agent 自己读
- OpenClaw 本身不读取这个文件

建议格式：

```json
{
  "preserveProviders": ["zhipu", "custom-local"],
  "preserveModels": ["zhipu/glm-4-plus", "custom-local/dev-model"]
}
```

## 6.4 新同步规则

同步时：

1. 读取当前 `openclaw.json`
2. 读取 `zhaocai-preserve.json`
3. 找出旧的网关托管内容
4. 只清理旧的网关托管内容
5. sidecar 中声明保留的 provider / model 不删除
6. 写入新下发内容

目标是：

- `openclaw.json` 保持标准格式
- 本地保留项不被误删
- 同步仍然可控

## 7. Media 模块设计

`Media` 模块独立于 OpenClaw 和 Gateway。

它的目标是：

- 管理 `zhaocai-media` 需要的上游 Provider
- 管理复杂媒体模板
- 导出统一 catalog

建议核心对象：

- `media_providers`
- `media_templates`

`media_templates` 采用声明式模板设计：

- `input_schema_json`
- `request_template_json`
- `response_mapping_json`
- `defaults_json`

不在数据库中存 JS / Python 执行代码。

## 8. Universal 模块设计

`Universal` 只负责模板池。

建议核心对象：

- `universal_provider_templates`
- `universal_provider_template_models`

支持：

- 导入到 OpenClaw
- 导入到 Gateway
- 导入到 Media

导入后：

- 目标模块拥有自己的独立副本
- 后续修改不联动

## 9. UI 设计

## 9.1 顶层导航

后台最终目标导航：

- `Universal`
- `OpenClaw`
- `Gateway`
- `Media`

## 9.2 第一阶段 UI 落法

为了减少对现有 v2 页面的大改，第一阶段建议：

- 保留现有 `Dashboard`
- 保留现有 `Devices`
- 保留现有 `Nodes`
- 把现有 `Providers` 页改造成四标签资源中心

标签为：

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

## 9.3 Gateway 页面

建议拆成以下子页或页内分区：

- `Gateway / Upstream Accounts`
- `Gateway / Aliases`
- `Gateway / Client Keys`
- `Gateway / Health`

## 9.4 Content-IP-Strategy 的后台表现

`Content-IP-Strategy` 后台只显示稳定别名，不显示真实 Provider 连接。

每条业务能力路由可以额外只读展示：

- 当前实际模型
- 当前主上游

这样业务侧能理解状态，但不承担基础设施管理职责。

## 10. API 设计

## 10.1 现有 OpenClaw API 保留

现有接口继续默认归属 OpenClaw：

- `/admin/providers`
- `/admin/models`
- `/admin/devices`

## 10.2 新增命名空间

### Universal

- `/admin/universal/templates`
- `/admin/universal/templates/{id}/import/openclaw`
- `/admin/universal/templates/{id}/import/gateway`
- `/admin/universal/templates/{id}/import/media`

### Gateway

- `/admin/gateway/accounts`
- `/admin/gateway/accounts/{id}/test`
- `/admin/gateway/accounts/{id}/sync-models`
- `/admin/gateway/aliases`
- `/admin/gateway/aliases/{id}/targets`
- `/admin/gateway/client-keys`
- `/admin/gateway/health`

### Media

- `/admin/media/providers`
- `/admin/media/templates`
- `/admin/media/catalog`

## 11. 数据表建议

### 11.1 OpenClaw

保留现有表：

- `providers`
- `models`
- `devices`
- `device_model_bindings`
- `pairing_tokens`
- `config_snapshots`

### 11.2 Universal

新增：

- `universal_provider_templates`
- `universal_provider_template_models`

### 11.3 Gateway

新增：

- `gateway_upstream_accounts`
- `gateway_models`
- `gateway_aliases`
- `gateway_alias_targets`
- `gateway_client_keys`
- `gateway_target_health_events`

### 11.4 Media

新增：

- `media_providers`
- `media_templates`

## 12. 最小实施顺序

### Step 1

先改 OpenClaw sidecar 保留机制：

- 不动其他模块
- 先解决当前同步会误删本地内容的问题

### Step 2

把当前 `Providers` 页面改成四模块资源中心：

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

### Step 3

把当前现有 Provider / Model 主线明确收口为 OpenClaw 资源。

### Step 4

新增 Gateway 的上游账号与模型同步能力：

- `accounts`
- `sync models`
- `health`

### Step 5

新增 Gateway 的别名与 target 链：

- `aliases`
- `alias targets`
- `fallback`

### Step 6

新增 Gateway 的对外接入 key：

- 给 `Content-IP-Strategy` 使用

### Step 7

让 `Content-IP-Strategy` 改成只保留：

- 业务能力 -> Gateway 稳定别名

### Step 8

独立推进 Media：

- `media_providers`
- `media_templates`
- `media catalog`

### Step 9

最后补 Universal 模板池导入能力。

## 13. 关键原则

1. 不破坏当前已跑通的 OpenClaw 主线
2. Gateway 统一承担模型供给、稳定别名和 fallback
3. `Content-IP-Strategy` 只保留业务能力路由，不再承担上游模型基础设施管理
4. Media 独立建模，不与普通 OpenClaw Provider / Model 语义混用
5. Universal 只做模板池，导入后各模块独立管理
