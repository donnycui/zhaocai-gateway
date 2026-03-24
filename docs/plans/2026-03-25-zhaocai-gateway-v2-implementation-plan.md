# Zhaocai Gateway v2.0 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build phase 1 of `zhaocai-gateway v2.0` as a Raspberry Pi-hosted control plane with provider management, device pairing, per-device model assignment, and node-agent config sync for OpenClaw.

**Architecture:** Keep FastAPI and SQLite, but replace the current monolithic layout with a layered package structure. Add a small React/Vite admin UI and a Python `node-agent`, while preserving the current repository as the delivery vehicle for phase 1 control-plane work.

**Tech Stack:** Python, FastAPI, SQLite, Pydantic, React, Vite, pytest, httpx

---

## File Structure

### Backend

- Create: `zhaocai_gateway/__init__.py`
- Create: `zhaocai_gateway/app.py`
- Create: `zhaocai_gateway/config.py`
- Create: `zhaocai_gateway/db/__init__.py`
- Create: `zhaocai_gateway/db/schema.py`
- Create: `zhaocai_gateway/db/store.py`
- Create: `zhaocai_gateway/domain/__init__.py`
- Create: `zhaocai_gateway/domain/models.py`
- Create: `zhaocai_gateway/services/__init__.py`
- Create: `zhaocai_gateway/services/providers.py`
- Create: `zhaocai_gateway/services/models.py`
- Create: `zhaocai_gateway/services/devices.py`
- Create: `zhaocai_gateway/services/pairing.py`
- Create: `zhaocai_gateway/services/config_compiler.py`
- Create: `zhaocai_gateway/api/__init__.py`
- Create: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/api/agent.py`
- Create: `zhaocai_gateway/api/health.py`
- Modify: `gateway.py`

### Frontend

- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/lib/api.ts`
- Create: `web/src/pages/DashboardPage.tsx`
- Create: `web/src/pages/ProvidersPage.tsx`
- Create: `web/src/pages/DevicesPage.tsx`
- Create: `web/src/pages/NodesPage.tsx`

### Node Agent

- Create: `agent/__init__.py`
- Create: `agent/cli.py`
- Create: `agent/config.py`
- Create: `agent/client.py`
- Create: `agent/sync.py`
- Create: `agent/openclaw_writer.py`

### Tests

- Create: `tests/conftest.py`
- Create: `tests/test_schema.py`
- Create: `tests/test_provider_api.py`
- Create: `tests/test_device_api.py`
- Create: `tests/test_pairing_api.py`
- Create: `tests/test_config_compiler.py`
- Create: `tests/test_agent_sync.py`

### Docs

- Modify: `README.md`
- Modify: `config.example.yaml`
- Modify: `.env.example`

## Task 1: Scaffold the New Backend Package

**Files:**
- Create: `zhaocai_gateway/__init__.py`
- Create: `zhaocai_gateway/app.py`
- Create: `zhaocai_gateway/config.py`
- Modify: `gateway.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Create the package entrypoints**

Create a minimal `create_app()` path in `zhaocai_gateway/app.py` and make `gateway.py` delegate to it.

- [ ] **Step 2: Add a smoke test target**

Create `tests/test_schema.py` with a minimal app bootstrap test.

```python
def test_create_app_smoke():
    from zhaocai_gateway.app import create_app

    app = create_app()
    assert app is not None
```

- [ ] **Step 3: Run the smoke test**

Run: `pytest tests/test_schema.py -v`
Expected: fail until package files exist, then pass after scaffold is in place.

- [ ] **Step 4: Implement the minimal scaffold**

Add:

- config loading
- app factory
- health router registration
- compatibility `main()` path from `gateway.py`

- [ ] **Step 5: Re-run the smoke test**

Run: `pytest tests/test_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add gateway.py zhaocai_gateway tests/test_schema.py
git commit -m "refactor: scaffold v2 backend package"
```

## Task 2: Build the SQLite Schema and Store Layer

**Files:**
- Create: `zhaocai_gateway/db/schema.py`
- Create: `zhaocai_gateway/db/store.py`
- Create: `zhaocai_gateway/domain/models.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write failing schema tests**

Add tests covering:

- provider insert and read
- model insert and read
- device insert and read
- config snapshot version sequencing

```python
def test_snapshot_versions_increment(store):
    first = store.save_config_snapshot(device_id=1, payload={"a": 1})
    second = store.save_config_snapshot(device_id=1, payload={"a": 2})
    assert first["version"] == 1
    assert second["version"] == 2
```

- [ ] **Step 2: Run schema tests**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL because the new store and schema do not exist yet.

- [ ] **Step 3: Implement the schema**

Add tables:

- `providers`
- `models`
- `devices`
- `device_model_bindings`
- `pairing_tokens`
- `config_snapshots`

- [ ] **Step 4: Implement the store methods**

Implement repository-style methods for:

- provider CRUD
- model CRUD
- device CRUD
- token issuance and consumption
- snapshot creation and retrieval

- [ ] **Step 5: Re-run schema tests**

Run: `pytest tests/test_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway/db zhaocai_gateway/domain tests/test_schema.py
git commit -m "feat: add v2 sqlite schema and store"
```

## Task 3: Implement Provider and Model Admin APIs

**Files:**
- Create: `zhaocai_gateway/services/providers.py`
- Create: `zhaocai_gateway/services/models.py`
- Create: `zhaocai_gateway/api/admin.py`
- Test: `tests/test_provider_api.py`

- [ ] **Step 1: Write failing provider API tests**

Cover:

- create provider
- validate provider input
- create model under provider
- list providers and models

```python
def test_create_provider(client):
    response = client.post("/admin/providers", json={"name": "openrouter", "base_url": "https://openrouter.ai/api/v1", "provider_type": "openai", "auth_scheme": "bearer", "api_key": "sk-test"})
    assert response.status_code == 200
```

- [ ] **Step 2: Run provider API tests**

Run: `pytest tests/test_provider_api.py -v`
Expected: FAIL because admin routes are not implemented yet.

- [ ] **Step 3: Implement service layer**

Create clean service methods for:

- provider creation
- provider validation
- model creation
- model listing

- [ ] **Step 4: Implement admin routes**

Expose:

- `GET /admin/providers`
- `POST /admin/providers`
- `POST /admin/providers/validate`
- `GET /admin/models`
- `POST /admin/models`

- [ ] **Step 5: Re-run provider API tests**

Run: `pytest tests/test_provider_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway/services zhaocai_gateway/api tests/test_provider_api.py
git commit -m "feat: add v2 provider and model admin APIs"
```

## Task 4: Implement Device, Pairing, and Assignment APIs

**Files:**
- Create: `zhaocai_gateway/services/devices.py`
- Create: `zhaocai_gateway/services/pairing.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/api/agent.py`
- Test: `tests/test_device_api.py`
- Test: `tests/test_pairing_api.py`

- [ ] **Step 1: Write failing device API tests**

Cover:

- create device
- issue pairing token
- assign models to device
- list devices

- [ ] **Step 2: Write failing pairing API tests**

Cover:

- successful registration with token
- expired token rejection
- heartbeat updates `last_seen_at`

- [ ] **Step 3: Run device and pairing tests**

Run: `pytest tests/test_device_api.py tests/test_pairing_api.py -v`
Expected: FAIL until routes and services are added.

- [ ] **Step 4: Implement the device services**

Support:

- device creation
- pairing token issuance
- token consumption
- model binding replacement
- heartbeat persistence

- [ ] **Step 5: Implement routes**

Admin routes:

- `GET /admin/devices`
- `POST /admin/devices`
- `POST /admin/devices/{id}/pairing-token`
- `PUT /admin/devices/{id}/models`

Agent routes:

- `POST /agent/v1/register`
- `POST /agent/v1/heartbeat`

- [ ] **Step 6: Re-run device and pairing tests**

Run: `pytest tests/test_device_api.py tests/test_pairing_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add zhaocai_gateway/services zhaocai_gateway/api tests/test_device_api.py tests/test_pairing_api.py
git commit -m "feat: add v2 device pairing and assignment APIs"
```

## Task 5: Implement Config Compilation and Versioned Sync

**Files:**
- Create: `zhaocai_gateway/services/config_compiler.py`
- Modify: `zhaocai_gateway/api/agent.py`
- Test: `tests/test_config_compiler.py`
- Test: `tests/test_agent_sync.py`

- [ ] **Step 1: Write failing compiler tests**

Cover:

- compiling device-specific model list
- skipping disabled models
- deterministic etag generation

- [ ] **Step 2: Write failing sync tests**

Cover:

- `GET /agent/v1/config/meta`
- `GET /agent/v1/config`
- unchanged config reuses version

- [ ] **Step 3: Run compiler and sync tests**

Run: `pytest tests/test_config_compiler.py tests/test_agent_sync.py -v`
Expected: FAIL

- [ ] **Step 4: Implement the config compiler**

Output should include:

- device metadata
- selected model list
- provider fragments required by OpenClaw
- version and etag support through snapshots

- [ ] **Step 5: Implement agent config routes**

Expose:

- `GET /agent/v1/config/meta`
- `GET /agent/v1/config`
- `POST /agent/v1/config/applied`

- [ ] **Step 6: Re-run compiler and sync tests**

Run: `pytest tests/test_config_compiler.py tests/test_agent_sync.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add zhaocai_gateway/services/config_compiler.py zhaocai_gateway/api/agent.py tests/test_config_compiler.py tests/test_agent_sync.py
git commit -m "feat: add v2 config compiler and sync APIs"
```

## Task 6: Build the Minimal Web Admin UI

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/lib/api.ts`
- Create: `web/src/pages/DashboardPage.tsx`
- Create: `web/src/pages/ProvidersPage.tsx`
- Create: `web/src/pages/DevicesPage.tsx`
- Create: `web/src/pages/NodesPage.tsx`

- [ ] **Step 1: Scaffold the web UI**

Create the Vite project structure and a basic app shell with four nav items:

- Dashboard
- Providers
- Devices
- Nodes

- [ ] **Step 2: Connect the UI to admin endpoints**

Implement minimal fetch wrappers in `web/src/lib/api.ts`.

- [ ] **Step 3: Add the provider flow**

Support:

- listing providers
- creating provider
- listing models

- [ ] **Step 4: Add the device flow**

Support:

- listing devices
- creating devices
- assigning models
- previewing config

- [ ] **Step 5: Build and smoke-test the UI**

Run: `cd web && npm install && npm run build`
Expected: successful production build.

- [ ] **Step 6: Commit**

```bash
git add web
git commit -m "feat: add v2 minimal admin web UI"
```

## Task 7: Implement the Python Node Agent

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/cli.py`
- Create: `agent/config.py`
- Create: `agent/client.py`
- Create: `agent/sync.py`
- Create: `agent/openclaw_writer.py`
- Test: `tests/test_agent_sync.py`

- [ ] **Step 1: Write failing agent tests**

Cover:

- register command stores sync token
- sync command downloads config
- writer updates local file atomically

- [ ] **Step 2: Run agent tests**

Run: `pytest tests/test_agent_sync.py -v`
Expected: FAIL until the agent package exists.

- [ ] **Step 3: Implement the agent CLI**

Support commands:

- `register`
- `sync-once`
- `run`

- [ ] **Step 4: Implement the OpenClaw writer**

Ensure:

- atomic file write
- local backup
- hook point for reload command

- [ ] **Step 5: Re-run agent tests**

Run: `pytest tests/test_agent_sync.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent tests/test_agent_sync.py
git commit -m "feat: add v2 node agent"
```

## Task 8: Documentation, Config Cleanup, and Delivery Checks

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `config.example.yaml`

- [ ] **Step 1: Update runtime documentation**

Document:

- phase 1 architecture
- Tailscale deployment assumption
- provider and device workflow
- node-agent commands

- [ ] **Step 2: Remove outdated control-plane guidance from docs**

Replace profile-oriented explanations with device-oriented assignment guidance.

- [ ] **Step 3: Run final verification**

Run:

- `pytest tests -q`
- `cd web && npm run build`

Expected:

- backend tests pass
- web build passes

- [ ] **Step 4: Commit**

```bash
git add README.md .env.example config.example.yaml
git commit -m "docs: update v2 setup and workflow docs"
```

## Notes for Execution

- Preserve existing functionality until each replacement path is ready.
- Keep Phase 2 hybrid-mode proxying out of Phase 1 implementation.
- Do not reintroduce `profiles` unless a concrete operational need emerges.
- Prefer small PR-sized commits that leave the repo runnable at every checkpoint.

