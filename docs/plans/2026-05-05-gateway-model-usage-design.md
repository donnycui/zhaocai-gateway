# Gateway Model Usage Design

## 目标

在 `Gateway` 模块里增加最小可用的模型用量视图，回答两个问题：

- 某个真实模型有没有被使用
- 最近一段时间它的成功率和失败率如何

第一版只做**真实模型 usage**，不做 alias 成本统计，也不做 token / 金额核算。

## 记录口径

每次 `Gateway` runtime 成功把请求路由到某个真实 target 模型时，都记录一条 usage event：

- `alias_key`
- `account_id`
- `account_name`
- `model_id`
- `upstream_model`
- `display_name`
- `request_kind`
  - `chat_completions`
  - `responses`
- `client_key_id`
- `status_code`
- `ok`
- `latency_ms`
- `created_at`

即使请求失败，也记录事件。

## 存储

新增表：

- `gateway_model_usage_events`

这张表不依赖外键回溯历史，而是把模型展示名、账号名等快照一起记录，避免后续账号或模型删除后 usage 丢失。

## 聚合接口

新增管理接口：

- `GET /admin/gateway/usage/models`

查询参数：

- `window`
  - `24h`
  - `7d`
- `account_id`（可选）
- `model_id`（可选）

返回聚合字段：

- `account_id`
- `account_name`
- `model_id`
- `upstream_model`
- `display_name`
- `total_calls`
- `success_calls`
- `failure_calls`
- `last_called_at`
- `avg_latency_ms`

## UI

在 `Gateway Accounts` 页面增加一个独立 `Gateway Usage` 面板：

- 时间范围筛选
- 账号筛选
- 模型 usage 列表

每条展示：

- 模型显示名
- upstream_model
- 调用次数
- 成功次数
- 失败次数
- 成功率
- 平均延迟
- 最近调用时间

## 不做的内容

第一版不做：

- token 使用量
- 金额估算
- alias 层级图表
- client key 维度报表
- 实时推送刷新
