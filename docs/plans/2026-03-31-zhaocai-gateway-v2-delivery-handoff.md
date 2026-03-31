# Zhaocai Gateway v2 Delivery Handoff

**Date:** 2026-03-31  
**Branch:** `codex/zhaocai-gateway-v2-scaffold`

## 1. 当前做到哪里

当前 `zhaocai-gateway-v2` 已经从单一的 OpenClaw 控制面，推进成四模块结构：

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

当前已经落地并提交的能力如下：

### OpenClaw

- 现有 Provider / Model / Device / Pairing / Agent Sync 主线保留
- 当前这条线已经明确收口为 `OpenClaw` 模块
- `node-agent` 已支持保留 sidecar：
  - `~/.openclaw/zhaocai-preserve.json`
- sidecar 中声明的 provider / model 不会被同步覆盖

### Gateway

- 已支持 `Gateway Upstream Accounts`
- 已支持从上游 `/models` 同步真实模型
- 已支持 `Gateway Aliases`
- 已支持 `Gateway Alias Targets`
- 已支持按 priority 的 failover
- 已支持 `Gateway Client Keys`
- 已支持运行时：
  - `POST /v1/chat/completions`
  - `POST /v1/responses`

当前 failover 规则：

- timeout 切换
- network error 切换
- `5xx` 切换
- `429` 切换
- 明显 `4xx` 不切换

### Media

- 已支持 `Media Providers`
- 已支持 `Media Templates`
- 已支持 `POST /admin/media/templates/validate`
- 已支持 `GET /admin/media/catalog`
- 已有基础 UI，可录入 provider、template 并预览 catalog

### Universal

- 已支持 `Universal Provider Templates`
- 已支持导入到：
  - `OpenClaw`
  - `Gateway`
  - `Media`
- 导入后是独立副本，不会回写模板池

## 2. 树莓派部署状态

树莓派地址：

- `cuijunpeng@192.168.1.26`

当前部署目录：

- `/home/cuijunpeng/zhaocai-gateway-v2`

当前 systemd 服务：

- `zhaocai-gateway.service`

已经确认：

- 服务成功切回 systemd 托管
- 不再由手工 Python 进程占用 `8000`
- 当前部署已更新到本轮最新代码
- `web/dist` 已在树莓派重新构建

已做过的 smoke check：

- `GET /health`
- `GET /admin/gateway/accounts`
- `GET /admin/media/catalog`
- `GET /admin/universal/templates`

结果：

- 服务正常
- 新模块路由可访问

## 3. GitHub 状态

远程仓库：

- `https://github.com/donnycui/zhaocai-gateway`

当前工作分支已经推送：

- `origin/codex/zhaocai-gateway-v2-scaffold`

这轮主要提交顺序：

- `d33eee9` `docs: add modular provider design for v2`
- `4b4bc24` `docs: add modular provider implementation plan`
- `63513a2` `feat: preserve local openclaw config via sidecar`
- `d3113c4` `refactor: scope current provider admin to openclaw`
- `b870e2a` `feat: add modular provider center shell`
- `988da81` `feat: add gateway upstream account management`
- `ec3ffd0` `feat: add gateway aliases and target mappings`
- `fd6411c` `feat: add gateway alias failover routing`
- `5bec996` `feat: add gateway client access keys`
- `7ad6ed2` `feat: add media provider and template module`
- `92dac50` `feat: add universal provider template pool`
- `fd04a02` `docs: update v2 modular provider rollout guidance`

## 4. 已验证内容

已跑过的后端测试：

- `tests/test_agent_runtime.py`
- `tests/test_agent_sync.py`
- `tests/test_provider_api.py`
- `tests/test_device_api.py`
- `tests/test_pairing_api.py`
- `tests/test_gateway_accounts_api.py`
- `tests/test_gateway_alias_api.py`
- `tests/test_gateway_failover.py`
- `tests/test_gateway_client_keys_api.py`
- `tests/test_media_template_api.py`
- `tests/test_media_catalog.py`
- `tests/test_universal_templates_api.py`

已跑过的前端验证：

- `npm run typecheck`
- `npm run build`

已做过的功能烟测：

- 创建 Gateway upstream account
- 同步 gateway models
- 创建 alias
- 给 alias 绑定 target
- 创建 gateway client key
- 通过 `Authorization: Bearer <gateway-client-key>` 调 `/v1/chat/completions`
- alias 被正确解析到真实模型

## 5. Content-IP-Strategy 下一步

本地仓库已经准备好：

- [Content-IP-Strategy](D:/github_mintstudio/Content-IP-Strategy)

建议下一步目标：

把 `Content-IP-Strategy` 切到：

- 一个 gateway `baseUrl`
- 一个 gateway `client key`
- 业务能力绑定稳定 alias

而不是继续让它自己管理：

- 真实 provider 连接
- 真实 API key
- 真实 base URL
- 真实模型切换与 fallback

建议能力绑定方式：

- `signal_scoring -> signal/deep`
- `draft_generation -> draft/deep`
- `topic_generation -> balanced`

然后由 `zhaocai-gateway-v2` 内部决定：

- alias 当前映射到哪个真实模型
- 这个 alias 下有哪些 target
- 某个 target 出错时如何切换

## 6. 剩余事项

这轮代码已经把四模块最小闭环做出来了，但还有这些后续工作值得单开：

### 运行与发布

- 给树莓派补更正式的升级脚本，而不是手动 zip 部署
- 如果需要，增加一个简单的部署校验脚本
- 评估是否要把当前分支合并回 `main`

### Gateway

- 给 `Gateway Client Keys` 增加更细粒度的 alias allow-list
- 增加更清晰的 health / cooldown / failure event 列表页
- 如果要对外正式使用，补 usage logging 与更完整的鉴权审计

### Media

- 现在的 `Media Templates` UI 还是最小闭环
- 后面可增加更好的 JSON 编辑器、模板预览和 catalog 字段编辑

### Universal

- 现在支持最小导入流
- 后面可以继续补模板模型列表的编辑体验、导入记录、模板复制

### Content-IP-Strategy

- 现在还没有切到新的 gateway client key + alias 模式
- 这部分建议单开线程、单独实施和验证

## 7. 建议阅读顺序

如果是新接手的人，建议按这个顺序读：

1. [README.md](D:/github_mintstudio/zhaocai-gateway/README.md)
2. [2026-03-31-zhaocai-gateway-v2-modular-provider-design.md](D:/github_mintstudio/zhaocai-gateway/docs/plans/2026-03-31-zhaocai-gateway-v2-modular-provider-design.md)
3. [2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md](D:/github_mintstudio/zhaocai-gateway/docs/plans/2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md)
4. 本文件
