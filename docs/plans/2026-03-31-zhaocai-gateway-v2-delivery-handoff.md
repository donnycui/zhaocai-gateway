# Zhaocai Gateway v2 Delivery Handoff

**Date:** 2026-04-02  
**Branch:** `codex/zhaocai-gateway-v2-scaffold`

## 1. Current State

`zhaocai-gateway-v2` has been expanded from a single OpenClaw-oriented control plane into four modules:

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

The branch is already pushed to GitHub, deployed to the Raspberry Pi, and running in service-managed mode.

### OpenClaw

- Existing `Provider / Model / Device / Pairing / Agent Sync` flows remain in place.
- The existing provider/model surface is now explicitly treated as the `OpenClaw` module.
- `node-agent` supports the preserve sidecar:
  - `~/.openclaw/zhaocai-preserve.json`
- Preserve entries declared in that sidecar are not deleted during sync.
- Operators can now edit device-level preserve config directly in the `Devices` page:
  - `preserve_providers`
  - `preserve_models`
- The control plane sends those values to the node on the next sync and the agent writes the sidecar file.
- `openclaw.json` itself remains standard and does not keep custom metadata.

### Gateway

- Supports `Gateway Upstream Accounts`
- Syncs real upstream models from `/v1/models`
- Supports `Gateway Aliases`
- Supports `Gateway Alias Targets`
- Supports priority-based failover
- Supports `Gateway Client Keys`
- Exposes runtime endpoints:
  - `POST /v1/chat/completions`
  - `POST /v1/responses`

Current failover policy:

- fail over on timeout
- fail over on network error
- fail over on `5xx`
- fail over on `429`
- do not fail over on obvious caller-caused `4xx`

### Media

- Supports `Media Providers`
- Supports `Media Templates`
- Supports `POST /admin/media/templates/validate`
- Supports `GET /admin/media/catalog`
- Has a minimal working admin UI for provider entry, template editing, and catalog preview

### Universal

- Supports `Universal Provider Templates`
- Can import templates into:
  - `OpenClaw`
  - `Gateway`
  - `Media`
- Imported records are independent copies and do not write back into the template pool

### Frontend UX Follow-Up

- A follow-up performance pass has already been applied to the admin UI
- Heavy `backdrop-filter`, large shadows, and expensive hover motion were reduced
- Goal: smoother scrolling on Raspberry Pi and lower-powered clients

## 2. Raspberry Pi Deployment

Host:

- `cuijunpeng@192.168.1.26`

Deploy directory:

- `/home/cuijunpeng/zhaocai-gateway-v2`

systemd service:

- `zhaocai-gateway.service`

As of **2026-04-02**, the following has been confirmed:

- the service is managed by `systemd`
- the previous hand-started Python process conflict on port `8000` has been removed
- the Raspberry Pi is running the latest code from this branch
- `web/dist` has been rebuilt on the Raspberry Pi
- the latest frontend assets are in place

Smoke checks already performed:

- `GET /health`
- `GET /admin/gateway/accounts`
- `GET /admin/media/catalog`
- `GET /admin/universal/templates`
- `GET /admin/devices`

Observed result:

- service healthy
- module routes reachable
- device payloads now include:
  - `preserve_providers`
  - `preserve_models`

## 3. GitHub Status

Remote repository:

- `https://github.com/donnycui/zhaocai-gateway`

Pushed branch:

- `origin/codex/zhaocai-gateway-v2-scaffold`

Key commits in delivery order:

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
- `e6c0998` `docs: add v2 delivery handoff summary`
- `bb9c15c` `perf: reduce expensive frontend visual effects`
- `42bae5a` `feat: manage device preserve config from ui`

## 4. Verification Completed

Backend tests that have been run:

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

Frontend verification that has been run:

- `npm run typecheck`
- `npm run build`

Functional smoke checks already performed:

- create a Gateway upstream account
- sync gateway models
- create an alias
- bind targets to an alias
- create a gateway client key
- call `/v1/chat/completions` with `Authorization: Bearer <gateway-client-key>`
- verify alias resolution to the expected real model
- save preserve config in the `Devices` UI
- verify agent sync writes `~/.openclaw/zhaocai-preserve.json`

## 5. Content-IP-Strategy Next Step

Local repository is already prepared at:

- `D:\github_mintstudio\Content-IP-Strategy`

Recommended migration target:

- one gateway `baseUrl`
- one gateway `client key`
- business capability routing to stable aliases

The project should stop being the source of truth for:

- real provider connections
- real upstream API keys
- real upstream base URLs
- real-model switching and fallback

Suggested first alias mapping style:

- `signal_scoring -> signal/deep`
- `draft_generation -> draft/deep`
- `topic_generation -> balanced`

`zhaocai-gateway-v2` should remain responsible for:

- which real model an alias currently points to
- which targets are available under that alias
- how failover proceeds when a target fails

## 6. Remaining Work

The four-module minimum loop is in place, but these areas remain good follow-up candidates.

### Operations and Release

- add a more formal upgrade script for the Raspberry Pi instead of manual zip deployment
- optionally add a lightweight deployment verification script
- evaluate whether and when to merge this branch back into `main`

### Gateway

- add finer-grained alias allow-lists to `Gateway Client Keys`
- add a clearer health / cooldown / failure-event page
- add usage logging and stronger auth auditing if the gateway is exposed more broadly

### Media

- the current `Media Templates` UI is still the minimum working loop
- later work can add a better JSON editor, richer template preview, and catalog field editing

### Universal

- the minimum import flow is in place
- later work can improve template-model editing, import history, and template duplication

### Content-IP-Strategy

- it has not yet been cut over to the new gateway client key + alias mode
- that work should happen in a separate thread with focused implementation and verification

## 7. Recommended Reading Order

For a new maintainer, read in this order:

1. [README.md](../../README.md)
2. [2026-03-31-zhaocai-gateway-v2-modular-provider-design.md](./2026-03-31-zhaocai-gateway-v2-modular-provider-design.md)
3. [2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md](./2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md)
4. this handoff file
