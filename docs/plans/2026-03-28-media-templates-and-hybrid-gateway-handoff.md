# Zhaocai Gateway Media Templates And Hybrid Gateway Handoff

## 目的

在当前 `zhaocai-gateway` 仓库基础上，规划两条后续主线，并明确它们与现有 `v2.0 phase 1` 控制面的关系：

1. 为 `zhaocai-media / laicai.tech` 增加 `Media Templates` 模块
2. 逐步把 `zhaocai-gateway` 演进成混合模式，给 `content-ip-research-workbench` 做统一中转

本文件只做设计、边界和粗规划，不代表当前已经完成实现。

---

## 当前仓库状态

`zhaocai-gateway v2` 当前已经具备：

- Provider 管理
- Model 管理
- Device 配对
- Node agent 同步
- OpenClaw 配置编译
- Web 控制台

现有主线关注点是：

- 中心控制面
- 按设备下发模型配置
- Node 侧本地 OpenClaw 配置同步

所以后续扩展必须遵守两个前提：

1. 不破坏现有普通 `Provider / Model / Device` 主线
2. 新增模块应尽量通过新增表、服务和页面实现，而不是挤进现有对象语义里

---

## 主线 A: Media Templates For zhaocai-media

### 背景

`zhaocai-media` 当前有大量图片、视频、TTS 模型硬编码在代码中。

这带来两个问题：

- 新增或下线媒体模型必须改 `zhaocai-media` 源码
- 媒体模型往往不是“一个 model_id 就够”，而是复杂模板

典型场景包括：

- `BizyAir` 的 `web_app_id + input_values`
- `Gemini image` 的多 part 请求
- `SiliconFlow TTS` 的专用响应解析

### 目标

在 `zhaocai-gateway` 中新增一层 `Media Templates`，让：

- `zhaocai-gateway`
  - 管模板
  - 管 catalog
- `zhaocai-media`
  - 做执行
- `laicai.tech`
  - 渲染模型列表和参数面板

### 核心设计

新增表：

- `media_templates`

建议字段：

- `id`
- `model_key`
- `name`
- `provider_id`
- `capability`
- `template_type`
- `upstream_model`
- `enabled`
- `ui_group`
- `ui_label`
- `ui_description`
- `ui_badge`
- `ui_order`
- `input_schema_json`
- `request_template_json`
- `response_mapping_json`
- `defaults_json`
- `created_at`
- `updated_at`

说明：

- `model_key`
  - 必须新增，作为网站和 `zhaocai-media` 使用的稳定标识
- `provider_id`
  - 继续复用现有 provider 体系，不单独建媒体 provider 表

### 支持能力

`capability` 第一版：

- `image`
- `image_edit`
- `image_to_video`
- `tts`

`template_type` 第一版：

- `openai_images`
- `gemini_generate_content`
- `bizyair_webapp`
- `siliconflow_tts`

### 模板表达方式

原则：

- 不存 JS/Python 执行代码
- 只存声明式模板

模板由四部分构成：

- `input_schema_json`
  - 前端参数定义
- `request_template_json`
  - 声明式请求模板
- `response_mapping_json`
  - 声明式响应提取
- `defaults_json`
  - 默认参数

### 验证规则

`POST /admin/media-templates/{id}/validate` 至少做：

- `provider_id` 是否存在
- `capability` 是否合法
- `template_type` 是否合法
- 4 个 JSON 字段是否合法
- `{{variable}}` 是否都能从 `input_schema_json + defaults_json` 推导出来
- 必填字段是否完整

返回：

- `ok`
- `message`
- `errors`
- `warnings`

### 导出 catalog

新增接口：

- `GET /admin/media/catalog`

每条至少包含：

- `id`
- `template_id`
- `mode`
- `provider`
- `template_type`
- `model_key`
- `upstream_model`
- `display_name`
- `description`
- `badge`
- `enabled`
- `ui_order`
- `ratios`
- `resolutions`
- `requires_start_image`
- `requires_end_image`
- `is_paid`
- `tags`
- `defaults`

### 推荐后端文件

新增：

- `zhaocai_gateway/services/media_templates.py`
- `zhaocai_gateway/services/media_catalog.py`
- `tests/test_media_template_api.py`
- `tests/test_media_catalog.py`

修改：

- `zhaocai_gateway/db/schema.py`
- `zhaocai_gateway/db/store.py`
- `zhaocai_gateway/domain/models.py`
- `zhaocai_gateway/api/admin.py`

前端新增：

- `web/src/pages/MediaTemplatesPage.tsx`
- `web/src/pages/MediaTemplateEditorPage.tsx`

修改：

- `web/src/App.tsx`
- `web/src/lib/api.ts`
- `web/src/styles.css`

### 为什么不会破坏现有系统

因为它是新增一条媒体模板主线，而不是替换现有普通模型主线：

- 普通 `Provider / Model`
  - 继续服务 OpenClaw 与普通文本模型
- `Media Templates`
  - 只服务复杂媒体工作流

两者共享 `provider_id`，但语义不混用。

---

## 主线 B: Hybrid Gateway For content-ip-research-workbench

### 背景

`content-ip-research-workbench` 当前已经有一套自己的：

- `gateway connections`
- `managed models`
- `capability routes`
- `gateway sync`

相关代码已经存在：

- `lib/services/gateway-admin-service.ts`
- `lib/services/gateway-sync-service.ts`
- `lib/services/model-routing-service.ts`
- `lib/models/gateway-client.ts`

当前模式是：

- 工作台自己维护 provider 连接
- 工作台自己管理能力路由
- 工作台直接打各类网关或兼容接口

### 目标

逐步把 `zhaocai-gateway` 演进成工作台的统一中转层，但不是一步变成“所有流量强制走树莓派”。

这里的“混合模式”指：

- 一部分能力继续直连原上游或现有 gateway
- 一部分能力逐步接到 `zhaocai-gateway`
- 最终由 `zhaocai-gateway` 成为能力路由与上游管理中心

### 与现有 v2 主线的关系

现有 `v2` 主要处理：

- 设备配置同步
- OpenClaw 节点

工作台混合模式新增的是另一条数据面能力：

- 为工作台提供稳定的统一模型入口
- 为不同能力路由到不同上游
- 支持 `chat completions / responses`

所以建议不要把这两件事混成一个“大路由类”，而是保持分层：

- `admin/device sync`
- `media templates`
- `hybrid model gateway`

### 工作台当前已暴露的契机

从代码看，工作台已经把调用抽象成：

- `ModelGatewayTarget`
- `invokeOpenAiChatCompletions`
- `invokeOpenAiResponses`
- `resolveCapabilityRoute`

这意味着工作台本身已经具备“网关目标可替换”的结构。

所以演进路径不应该是重写工作台，而是：

1. 让工作台新增一种 `gateway target`
   - 指向 `zhaocai-gateway`
2. 逐步把部分 capability route 指向 `zhaocai-gateway`
3. 再让 `zhaocai-gateway` 内部负责二次路由

### 推荐混合模式阶段划分

#### Phase 1: Gateway As Stable Upstream

`content-ip-research-workbench` 先把 `zhaocai-gateway` 当作一个稳定上游。

目标：

- 工作台某些 capability route 不再直连外部 provider
- 改成统一打 `zhaocai-gateway`

这一阶段 `zhaocai-gateway` 需要：

- 稳定的 `/v1/chat/completions`
- 稳定的 `/v1/responses`
- provider/model 路由能力

这一阶段不要求工作台放弃自己现有所有 gateway connection。

#### Phase 2: Capability-Aware Central Routing

在 `zhaocai-gateway` 中新增一层面向工作台的“能力路由”：

- `signal_scoring`
- `direction_generation`
- `topic_generation`
- `draft_generation`
- 等等

工作台调用时，不再只传普通 model，而是可以传：

- capability key
- optional model override
- optional tier hint

`zhaocai-gateway` 负责把 capability 映射到实际 provider/model。

#### Phase 3: Unified Control Plane

把工作台现有这些概念逐步收拢进 `zhaocai-gateway`：

- gateway connections
- managed models
- capability routes
- syncable routing config

工作台最终只保留：

- UI
- domain service
- 调 `zhaocai-gateway`

### 为什么叫混合模式

因为过渡期必须允许并存：

- 旧的工作台本地 gateway 仍可用
- 新的 `zhaocai-gateway` 路由逐步接管

这样能做到：

- 小步迁移
- 可回滚
- 不阻断当前工作台业务

### 推荐在 zhaocai-gateway 新增的后端模块

先不实现全量替代，只做为未来混合模式铺路：

- `zhaocai_gateway/services/hybrid_routes.py`
- `zhaocai_gateway/services/gateway_targets.py`
- `zhaocai_gateway/services/workbench_catalog.py`

未来可能新增的表：

- `capability_routes`
- `gateway_targets`
- `managed_models`

但这部分建议作为后续单独迭代，不和 `Media Templates` 同轮落地。

### 与 workbench 的最小集成建议

工作台侧先新增一种“统一中转模式”：

- 在 `resolveCapabilityRoute()` 里允许 route 指向 `zhaocai-gateway`
- 在 `gateway-client.ts` 里继续复用现有 `chat completions / responses`
- 只替换 `baseUrl + auth`

这样 Phase 1 基本不需要大规模改工作台业务代码。

---

## 两条主线如何排序

推荐顺序：

### 第一优先级

- `Media Templates`

原因：

- 它和现有 `v2` 控制面耦合更自然
- 对 `zhaocai-media / laicai.tech` 的收益更直接
- 不需要先改另一个仓库的执行链路

### 第二优先级

- `content-ip-research-workbench` 混合模式 Phase 1

原因：

- 工作台已经有一套模型管理和网关逻辑
- 直接做统一中转需要考虑迁移边界
- 更适合在 `Media Templates` 之后单独推进

---

## 推荐实现顺序

### Step 1

为 `zhaocai-gateway` 增加：

- `media_templates` 表
- CRUD API
- validate API
- catalog API
- 最小 UI

### Step 2

让 `zhaocai-media` 消费：

- `GET /admin/media/catalog`

替代硬编码模型列表。

### Step 3

为 `content-ip-research-workbench` 设计：

- `gateway target = zhaocai-gateway`
- 小范围 capability route 接入

### Step 4

逐步把工作台的：

- gateway connections
- model routing

迁到 `zhaocai-gateway` 统一控制。

---

## 风险与注意点

### Media Templates 风险

- `BizyAir` 的节点 ID 和 `web_app_id` 可能变化
- `Gemini` 响应结构可能不止 `inlineData`
- `catalog` 字段设计要稳定，不然网站消费端会频繁改

### Hybrid Gateway 风险

- 工作台现有模型路由体系已经成型，不能粗暴替换
- 统一中转会引入新的数据面耦合
- 必须允许回退到工作台原有 gateway connection

---

## 交接建议

后续实现时，建议拆成两份独立计划：

1. `Media Templates implementation plan`
2. `Hybrid Gateway for content-ip-research-workbench implementation plan`

不要把两条主线混在同一轮实现里。

建议先完成：

- `Media Templates` 的完整最小闭环

再开始：

- `Hybrid Gateway Phase 1`

