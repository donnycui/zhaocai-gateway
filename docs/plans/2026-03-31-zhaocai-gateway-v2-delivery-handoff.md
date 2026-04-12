# Zhaocai Gateway v2 Delivery Handoff

**Date:** 2026-04-13  
**Branch:** `main`

## 1. Current State

`zhaocai-gateway-v2` has been expanded from a single OpenClaw-oriented control plane into four modules:

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

The current code is already on GitHub `main`, deployed to the Raspberry Pi, and running in service-managed mode.

### OpenClaw

- Existing `Provider / Model / Device / Pairing / Agent Sync` flows remain in place.
- The existing provider/model surface is now explicitly treated as the `OpenClaw` module.
- The OpenClaw provider editor now supports upstream model discovery:
  - operators can click a fetch-model-list action in the provider editor
  - the control plane calls the upstream `/models` endpoint using the current form values
  - models are shown in a selection modal and imported into the local editor only after confirmation
  - duplicate `upstream_model` entries are skipped rather than overwritten
- `node-agent` supports the preserve sidecar:
  - `~/.openclaw/zhaocai-preserve.json`
- Preserve entries declared in that sidecar are not deleted during sync.
- Operators can now edit device-level preserve config directly in the `Devices` page:
  - `preserve_providers`
  - `preserve_models`
- The control plane sends those values to the node on the next sync and the agent writes the sidecar file.
- `openclaw.json` itself remains standard and does not keep custom metadata.
- Device model assignment has been changed to batch-save mode:
  - checking models no longer triggers an API request per click
  - operators now explicitly confirm with a save action
- Provider editor model discovery has been reworked:
  - the discovery modal now uses upstream-owner grouping where available
  - groups default to collapsed
  - imported models are not preselected automatically
  - the modal uses a fixed header + scrollable middle list + fixed footer layout
- The `reasoning` toggle in the provider editor now correctly maps to compiled `openclaw.json`.
- Duplicate provider creation now returns a readable `409` conflict instead of an unhandled `500`.

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
- The resource-center OpenClaw cards now use rotating accent colors for provider avatars
- The provider model-discovery modal uses the same avatar palette so adjacent model rows are easier to scan
- The `Nodes` page onboarding command now defaults to the public gateway URL:
  - `https://zhaocai.mintstudio.cn`
- The generated Linux onboarding command now includes:
  - `python3-venv` prerequisite
  - explicit `register`
  - `sync-once`
  - `doctor`
  - `install --service-manager systemd`
  - `systemctl --user` enable/start steps
- The generated command no longer includes the stray `+` prefixes that briefly appeared in multiline output.

## 2. Raspberry Pi Deployment

Host:

- `cuijunpeng@192.168.1.26`

Deploy directory:

- `/home/cuijunpeng/zhaocai-gateway-v2`

systemd service:

- `zhaocai-gateway.service`

As of **2026-04-13**, the following has been confirmed:

- the service is managed by `systemd`
- the previous hand-started Python process conflict on port `8000` has been removed
- the Raspberry Pi is running the latest code from `main`
- `web/dist` has been rebuilt on the Raspberry Pi
- the latest frontend assets are in place
- the provider model-discovery UI has been deployed to the Raspberry Pi
- the Raspberry Pi itself has been registered as an OpenClaw node:
  - device id `4`
  - `zhaocai-agent.service` enabled via `systemd --user`
  - local agent config at `/home/cuijunpeng/.zhaocai-gateway/agent.json`
  - local OpenClaw config target at `/home/cuijunpeng/.openclaw/openclaw.json`
- a remote AWS Ubuntu node has also been validated:
  - device id `6`
  - `register` and first `sync-once` both succeeded against `https://zhaocai.mintstudio.cn`
  - the generated `systemd` service required a follow-up fix:
    - `WorkingDirectory` had to point at the cloned repo
    - `reload_command` had to use the absolute `openclaw` path
  - after correction, `zhaocai-agent.service` is running normally on that node

Smoke checks already performed:

- `GET /health`
- `GET /admin/gateway/accounts`
- `GET /admin/media/catalog`
- `GET /admin/universal/templates`
- `GET /admin/devices`
- `GET /admin/providers`

Observed result:

- service healthy
- module routes reachable
- device payloads now include:
  - `preserve_providers`
  - `preserve_models`
- public agent routes are reachable through Cloudflare:
  - `https://zhaocai.mintstudio.cn/agent/v1/register`
  - `https://zhaocai.mintstudio.cn/agent/v1/config/meta`
- `/control` remains protected by Cloudflare Access, but `/agent/v1/*` is reachable for node traffic

## 3. GitHub Status

Remote repository:

- `https://github.com/donnycui/zhaocai-gateway`

Primary branch:

- `origin/main`

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
- `5f9fd80` `docs: refresh v2 handoff status`
- `7e60bb9` `feat: add provider model discovery picker`
- `05e2e70` `fix: clean zhaocai marker and batch device assignment`
- `ab1e5a0` `fix: restore provider discovery modal layout`
- `cea2d2e` `fix: stabilize provider discovery modal chrome`
- `081cd7a` `fix: handle duplicate providers gracefully`
- `d7fb486` `fix: improve provider discovery failures`
- `620ce83` `fix: remove stray plus signs from node commands`
- `0903b2e` `fix: expand node onboarding prerequisites`
- `eeac789` `fix: default node onboarding to public gateway url`
- `14e1b83` `fix: make linux node setup copy-pastable`

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
- open an OpenClaw provider in the editor and fetch the upstream model list
- verify the selection modal imports only newly selected models into the local edit form
- verify Raspberry Pi local node registration, first sync, and `systemd --user` service startup
- verify Mac `launchd` agent recovery after runtime code drift
- verify AWS Ubuntu registration through public Cloudflare URL and persistent `systemd --user` service after service-file correction

## 5. Current Known Issues

These are active caveats worth carrying forward.

### Node Onboarding

- The UI-generated Linux/VPS onboarding command is now much closer to copy-paste ready, but real-world nodes may still need environment-specific correction:
  - missing `python3-venv` on fresh Ubuntu hosts
  - missing `openclaw` binary in `PATH`
  - `systemd --user` environment not matching interactive shells
- The public gateway URL is now the default onboarding target because it is more broadly reachable than the Tailscale-only address.

### Upstream Model Discovery

- `ice` model discovery is currently confirmed working.
- `anyrouter` remains problematic specifically from the Raspberry Pi host:
  - direct requests from the Raspberry Pi to `https://anyrouter.top/v1/models` are reset by the upstream
  - the same endpoint is reachable from the Mac host with `Authorization: Bearer ...`
  - this looks like an upstream/network-path issue, not a control-plane UI bug
- `yunduan` discovery is also unstable from the Raspberry Pi host:
  - macOS can reach `https://cloudapi.wdyu.eu.cc/v1/models`
  - Raspberry Pi has shown certificate-chain errors and inconsistent `404/503` upstream responses
  - a narrow TLS-cert fallback has been added for discovery/test requests, but the upstream itself is still not consistently healthy from the Raspberry Pi path

### Runtime Compatibility

- Local test execution on the development Mac is partially blocked by a repository-wide Python compatibility issue unrelated to the latest OpenClaw work:
  - another service imports `datetime.UTC`
  - the local Python 3.9 environment fails before some test modules can run
- When validating recent changes, real endpoint checks on the Raspberry Pi and browser-level verification have been used as the authoritative signal where local pytest was blocked

## 6. Content-IP-Strategy Next Step

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

## 7. Remaining Work

The four-module minimum loop is in place, but these areas remain good follow-up candidates.

### Operations and Release

- add a more formal upgrade script for the Raspberry Pi instead of manual zip deployment
- optionally add a lightweight deployment verification script
- keep deployment reproducible; the Raspberry Pi runtime directory is still a manual sync target rather than a Git working tree

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

## 8. Recommended Reading Order

For a new maintainer, read in this order:

1. [README.md](../../README.md)
2. [2026-03-31-zhaocai-gateway-v2-modular-provider-design.md](./2026-03-31-zhaocai-gateway-v2-modular-provider-design.md)
3. [2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md](./2026-03-31-zhaocai-gateway-v2-modular-provider-implementation-plan.md)
4. this handoff file
