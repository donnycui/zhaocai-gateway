# Hermes Module Implementation Plan

> **For agentic workers:** REQUIRED: Use `executing-plans` or an equivalent checkpointed implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class `Hermes` module to `zhaocai-gateway` so operators can manage Hermes providers, Hermes models, Hermes nodes, and Hermes node config sync alongside the existing `OpenClaw / Gateway / Media / Universal` modules.

**Architecture:** Mirror the proven `OpenClaw` control-plane flow, but compile Hermes-specific artifacts instead of `openclaw.json`. Keep Hermes data and sync contracts isolated from OpenClaw. Support one-way import from OpenClaw providers into Hermes providers, and optionally render a fixed provider plugin file when a Hermes provider needs `default_headers`.

**Tech Stack:** Python, FastAPI, SQLite, Pydantic, React, Vite, pytest, httpx, PyYAML

---

## File Structure

### Backend

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Modify: `zhaocai_gateway/api/__init__.py`
- Modify: `zhaocai_gateway/app.py`

- Create: `zhaocai_gateway/services/hermes_providers.py`
- Create: `zhaocai_gateway/services/hermes_models.py`
- Create: `zhaocai_gateway/services/hermes_devices.py`
- Create: `zhaocai_gateway/services/hermes_pairing.py`
- Create: `zhaocai_gateway/services/hermes_config_compiler.py`

### Agent

- Modify: `agent/cli.py`
- Modify: `agent/config.py`
- Modify: `agent/client.py`
- Modify: `agent/sync.py`
- Modify: `agent/install.py`
- Modify: `agent/openclaw_writer.py` only if shared file helpers are reused
- Create: `agent/hermes_writer.py`

### Frontend

- Modify: `web/src/pages/ProvidersPage.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/styles.css`
- Create: `web/src/pages/HermesProvidersPage.tsx`
- Create: `web/src/pages/HermesProviderEditorPage.tsx`
- Create: `web/src/pages/HermesDevicesPage.tsx`
- Create: `web/src/pages/HermesNodesPage.tsx`

### Tests

- Create: `tests/test_hermes_provider_api.py`
- Create: `tests/test_hermes_device_api.py`
- Create: `tests/test_hermes_compiler.py`
- Create: `tests/test_hermes_agent_sync.py`

### Docs

- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/plans/2026-06-03-hermes-module-design.md` only if implementation decisions change

## Task 1: Add Hermes Schema and Store Layer

**Files:**
- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Test: `tests/test_hermes_provider_api.py`

- [ ] **Step 1: Write failing schema/store tests**

Cover:

- create Hermes provider
- create Hermes model
- create Hermes device
- bind Hermes models to device with priority
- create Hermes config snapshot

```python
def test_create_hermes_provider(store):
    provider = store.create_hermes_provider(
        name="relay_a",
        base_url="https://relay.example.com/v1",
        api_key_encrypted="sk-test",
        enabled=True,
        notes="",
        plugin_mode="none",
        default_headers_json={},
        source_openclaw_provider_id=None,
    )
    assert provider.name == "relay_a"
```

- [ ] **Step 2: Run the Hermes schema tests**

Run:

```bash
pytest tests/test_hermes_provider_api.py -v
```

Expected:
- FAIL because Hermes schema/store do not exist yet

- [ ] **Step 3: Add Hermes tables**

Add:

- `hermes_providers`
- `hermes_models`
- `hermes_devices`
- `hermes_device_model_bindings`
- `hermes_pairing_tokens`
- `hermes_config_snapshots`

- [ ] **Step 4: Add dataclasses and store methods**

Implement:

- create / get / list / update / delete Hermes provider
- create / get / list / update / delete Hermes model
- create / get / list / update / delete Hermes device
- replace Hermes device bindings with priority
- pairing token create / consume
- Hermes config snapshot create / fetch

- [ ] **Step 5: Re-run schema/store tests**

Run:

```bash
pytest tests/test_hermes_provider_api.py -v
```

Expected:
- PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway/db zhaocai_gateway/domain tests/test_hermes_provider_api.py
git commit -m "feat: add hermes schema and store"
```

## Task 2: Build Hermes Provider and Model Admin Services

**Files:**
- Create: `zhaocai_gateway/services/hermes_providers.py`
- Create: `zhaocai_gateway/services/hermes_models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Test: `tests/test_hermes_provider_api.py`

- [ ] **Step 1: Write failing service/API tests**

Cover:

- create Hermes provider
- update Hermes provider
- delete Hermes provider
- create Hermes model
- update Hermes model
- delete Hermes model

```python
def test_create_hermes_model(client, hermes_provider_id):
    response = client.post(
        "/admin/hermes/models",
        headers=admin_headers(),
        json={
            "provider_id": hermes_provider_id,
            "upstream_model": "gpt-5.5",
            "display_name": "GPT-5.5",
            "enabled": True,
        },
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Implement Hermes provider service**

Include:

- provider CRUD
- plugin mode normalization
- `default_headers_json` validation
- `import_openclaw_provider(openclaw_provider_id)` helper

- [ ] **Step 3: Implement Hermes model service**

Keep it minimal:

- model CRUD
- provider existence validation

- [ ] **Step 4: Re-run provider/model tests**

Run:

```bash
pytest tests/test_hermes_provider_api.py -v
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add zhaocai_gateway/services tests/test_hermes_provider_api.py
git commit -m "feat: add hermes provider and model services"
```

## Task 3: Expose Hermes Admin API

**Files:**
- Modify: `zhaocai_gateway/api/admin.py`
- Modify: `zhaocai_gateway/api/__init__.py`
- Test: `tests/test_hermes_provider_api.py`
- Test: `tests/test_hermes_device_api.py`

- [ ] **Step 1: Add Hermes provider endpoints**

Add:

- `GET /admin/hermes/providers`
- `POST /admin/hermes/providers`
- `GET /admin/hermes/providers/{id}`
- `PATCH /admin/hermes/providers/{id}`
- `DELETE /admin/hermes/providers/{id}`
- `POST /admin/hermes/providers/import-openclaw`

- [ ] **Step 2: Add Hermes model endpoints**

Add:

- `GET /admin/hermes/models`
- `POST /admin/hermes/models`
- `PATCH /admin/hermes/models/{id}`
- `DELETE /admin/hermes/models/{id}`

- [ ] **Step 3: Add Hermes device endpoints**

Add:

- `GET /admin/hermes/devices`
- `POST /admin/hermes/devices`
- `PATCH /admin/hermes/devices/{id}`
- `DELETE /admin/hermes/devices/{id}`
- `PUT /admin/hermes/devices/{id}/models`
- `GET /admin/hermes/devices/{id}/config-preview`
- `POST /admin/hermes/devices/{id}/pairing-token`

- [ ] **Step 4: Add failing device tests**

Cover:

- device create
- issue pairing token
- save ordered model bindings
- config preview contains YAML and plugin file map

- [ ] **Step 5: Run Hermes API tests**

Run:

```bash
pytest tests/test_hermes_provider_api.py tests/test_hermes_device_api.py -v
```

Expected:
- PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway/api tests/test_hermes_provider_api.py tests/test_hermes_device_api.py
git commit -m "feat: add hermes admin api"
```

## Task 4: Implement Hermes Config Compiler

**Files:**
- Create: `zhaocai_gateway/services/hermes_config_compiler.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Test: `tests/test_hermes_compiler.py`

- [ ] **Step 1: Write failing compiler tests**

Cover:

- provider-only config
- ordered model selection
- default model uses priority `0`
- plugin file generation when `plugin_mode = default_headers`

```python
def test_compile_hermes_config_with_plugin(store):
    compiled = HermesConfigCompilerService(store).compile(device_id=1)
    assert "config_yaml" in compiled
    assert "plugin_files" in compiled
    assert "relay_a" in compiled["plugin_files"]
```

- [ ] **Step 2: Implement YAML config rendering**

Render:

- `providers.<provider_name>.base_url`
- `providers.<provider_name>.api_key`
- `model.default`
- optionally `model.fallbacks` if Hermes supports it

- [ ] **Step 3: Implement plugin file rendering**

For `plugin_mode = default_headers`, generate exactly:

- `~/.hermes/plugins/model-providers/<provider>/__init__.py`

using fixed Python template and sanitized header values.

- [ ] **Step 4: Re-run compiler tests**

Run:

```bash
pytest tests/test_hermes_compiler.py -v
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add zhaocai_gateway/services/hermes_config_compiler.py tests/test_hermes_compiler.py
git commit -m "feat: add hermes config compiler"
```

## Task 5: Extend Agent for Hermes Sync

**Files:**
- Modify: `agent/cli.py`
- Modify: `agent/config.py`
- Modify: `agent/client.py`
- Modify: `agent/sync.py`
- Modify: `agent/install.py`
- Create: `agent/hermes_writer.py`
- Test: `tests/test_hermes_agent_sync.py`

- [ ] **Step 1: Write failing Hermes agent tests**

Cover:

- register Hermes node
- sync Hermes payload
- write `config.yaml`
- write plugin files
- run Hermes reload commands

- [ ] **Step 2: Add Hermes agent target mode**

Support:

- `--target hermes`
- Hermes config path defaults
- Hermes output paths

- [ ] **Step 3: Implement Hermes writer**

Write:

- `~/.hermes/config.yaml`
- plugin files into `~/.hermes/plugins/model-providers/...`

Use atomic write semantics similar to OpenClaw writer.

- [ ] **Step 4: Add Hermes reload command support**

Default sequence:

```bash
systemctl --user restart hermes-gateway
systemctl --user restart hermes-webui
```

- [ ] **Step 5: Re-run Hermes agent tests**

Run:

```bash
pytest tests/test_hermes_agent_sync.py -v
```

Expected:
- PASS

- [ ] **Step 6: Commit**

```bash
git add agent tests/test_hermes_agent_sync.py
git commit -m "feat: add hermes agent sync"
```

## Task 6: Add Hermes Resource Center UI

**Files:**
- Modify: `web/src/pages/ProvidersPage.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/styles.css`
- Create: `web/src/pages/HermesProvidersPage.tsx`
- Create: `web/src/pages/HermesProviderEditorPage.tsx`
- Create: `web/src/pages/HermesDevicesPage.tsx`
- Create: `web/src/pages/HermesNodesPage.tsx`

- [ ] **Step 1: Add Hermes module tab**

Extend resource center modules:

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`
- `Hermes`

- [ ] **Step 2: Implement Hermes Providers page**

Support:

- list providers
- create / edit / delete
- choose plugin mode
- edit `default_headers_json`
- import from OpenClaw

- [ ] **Step 3: Implement Hermes Models + Devices UI**

At minimum:

- Hermes models list / CRUD
- Hermes devices list / CRUD
- bind models to devices in priority order
- preview compiled config

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd web
npm run build
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: add hermes admin ui"
```

## Task 7: Add OpenClaw-to-Hermes Import Flow

**Files:**
- Modify: `zhaocai_gateway/services/hermes_providers.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Modify: `web/src/pages/HermesProvidersPage.tsx`
- Test: `tests/test_hermes_provider_api.py`

- [ ] **Step 1: Add provider import endpoint**

Input:

- OpenClaw provider id

Behavior:

- copy `name`
- copy `base_url`
- copy `api_key`
- store `source_openclaw_provider_id`
- default `plugin_mode = none`

- [ ] **Step 2: Add UI action**

In Hermes provider page:

- `从 OpenClaw 导入`

This can be:

- a dropdown
- or a modal chooser

but keep it minimal.

- [ ] **Step 3: Re-run provider tests**

Run:

```bash
pytest tests/test_hermes_provider_api.py -v
```

Expected:
- PASS

- [ ] **Step 4: Commit**

```bash
git add zhaocai_gateway web tests/test_hermes_provider_api.py
git commit -m "feat: import hermes providers from openclaw"
```

## Task 8: Docs and Delivery Validation

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/plans/2026-06-03-hermes-module-design.md` only if necessary

- [ ] **Step 1: Document Hermes env vars**

At minimum:

- Hermes agent server URL
- Hermes reload command
- any plugin-related defaults

- [ ] **Step 2: Document Hermes operator workflow**

Explain:

- create provider
- import from OpenClaw
- add models
- create Hermes node
- issue token
- run Hermes agent

- [ ] **Step 3: Validate the end-to-end loop**

Minimum operator smoke:

1. create Hermes provider
2. import one provider from OpenClaw
3. create Hermes model
4. bind to Hermes node
5. register Hermes node
6. sync once
7. confirm `~/.hermes/config.yaml` updated
8. confirm Hermes services restarted

- [ ] **Step 4: Commit**

```bash
git add README.md .env.example docs/plans/2026-06-03-hermes-module-design.md docs/plans/2026-06-03-hermes-module-implementation-plan.md
git commit -m "docs: add hermes module rollout guide"
```
