# Zhaocai Gateway v2 Modular Provider Implementation Plan

> **For agentic workers:** REQUIRED: Use `executing-plans` or an equivalent checkpointed implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve `zhaocai-gateway-v2` from a single OpenClaw-oriented control plane into a four-module backend and admin UI with:

- a preserved and safer `OpenClaw` node-sync path
- a new `Gateway` model-supply module with alias-based routing and upstream failover
- a separate `Media` provider/template module for `zhaocai-media`
- a `Universal` template pool that can seed the other modules without creating shared mutable runtime state

**Architecture:** Keep the current FastAPI + SQLite + React/Vite stack. Preserve the existing OpenClaw implementation as the base module, then add new namespaced data models, services, APIs, and UI sections for `Gateway`, `Media`, and `Universal`. Treat `Content-IP-Strategy` as an external consumer that should only manage business capability -> stable alias routing, while `zhaocai-gateway-v2` becomes the model-supply truth source.

**Tech Stack:** Python, FastAPI, SQLite, Pydantic, React, Vite, pytest, httpx

---

## File Structure

### Backend

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Modify: `zhaocai_gateway/app.py`

- Create: `zhaocai_gateway/services/gateway_accounts.py`
- Create: `zhaocai_gateway/services/gateway_aliases.py`
- Create: `zhaocai_gateway/services/gateway_client_keys.py`
- Create: `zhaocai_gateway/services/media_providers.py`
- Create: `zhaocai_gateway/services/media_templates.py`
- Create: `zhaocai_gateway/services/media_catalog.py`
- Create: `zhaocai_gateway/services/universal_templates.py`

### Node Agent

- Modify: `agent/openclaw_writer.py`
- Modify: `agent/config.py`
- Modify: `agent/sync.py`

### Frontend

- Modify: `web/src/App.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/styles.css`
- Modify: `web/src/pages/ProvidersPage.tsx`
- Modify: `web/src/pages/ProviderEditorPage.tsx`

- Create: `web/src/pages/GatewayAccountsPage.tsx`
- Create: `web/src/pages/GatewayAliasesPage.tsx`
- Create: `web/src/pages/GatewayClientKeysPage.tsx`
- Create: `web/src/pages/GatewayHealthPage.tsx`
- Create: `web/src/pages/MediaProvidersPage.tsx`
- Create: `web/src/pages/MediaTemplatesPage.tsx`
- Create: `web/src/pages/MediaTemplateEditorPage.tsx`
- Create: `web/src/pages/UniversalTemplatesPage.tsx`

### Tests

- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_agent_sync.py`
- Modify: `tests/test_provider_api.py`

- Create: `tests/test_gateway_accounts_api.py`
- Create: `tests/test_gateway_alias_api.py`
- Create: `tests/test_gateway_failover.py`
- Create: `tests/test_media_template_api.py`
- Create: `tests/test_media_catalog.py`
- Create: `tests/test_universal_templates_api.py`

### Docs

- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/plans/2026-03-31-zhaocai-gateway-v2-modular-provider-design.md` only if implementation decisions change

---

## Task 1: Add OpenClaw preserve sidecar support

**Files:**

- Modify: `agent/openclaw_writer.py`
- Modify: `agent/config.py`
- Modify: `agent/sync.py`
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_agent_sync.py`

- [x] **Step 1: Define the preserve sidecar contract**

Choose a sidecar path near the existing OpenClaw config, such as:

```text
~/.openclaw/zhaocai-preserve.json
```

Document the first schema:

```json
{
  "preserveProviders": ["zhipu", "custom-local"],
  "preserveModels": ["zhipu/glm-4-plus", "custom-local/dev-model"]
}
```

- [x] **Step 2: Write failing tests for merge-preserve behavior**

Cover:

- preserved providers are kept
- preserved models are kept
- old gateway-managed sections are refreshed
- malformed sidecar does not corrupt the generated `openclaw.json`

- [x] **Step 3: Implement sidecar-aware merge logic**

Update the writer so it:

- reads the current `openclaw.json`
- reads the optional preserve sidecar
- removes only the previous gateway-managed sections
- keeps sidecar-declared providers and models
- writes a clean standard `openclaw.json` without extra metadata fields

- [x] **Step 4: Re-run agent tests**

Run:

```bash
pytest tests/test_agent_runtime.py tests/test_agent_sync.py -v
```

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add agent tests
git commit -m "feat: preserve local openclaw config via sidecar"
```

---

## Task 2: Reframe current provider management as the OpenClaw module

**Files:**

- Modify: `zhaocai_gateway/api/admin.py`
- Modify: `zhaocai_gateway/services/providers.py`
- Modify: `zhaocai_gateway/services/models.py`
- Modify: `web/src/pages/ProvidersPage.tsx`
- Modify: `web/src/pages/ProviderEditorPage.tsx`
- Modify: `web/src/lib/api.ts`

- [x] **Step 1: Rename the current provider/model surface in product copy**

Make the existing provider management explicitly read as:

- `OpenClaw Providers`
- `OpenClaw Models`
- OpenClaw-only sync inventory

without changing its underlying runtime behavior yet.

- [x] **Step 2: Keep existing APIs working while clarifying scope**

Retain current `/admin/providers` and `/admin/models` behavior, but treat them as the `OpenClaw` namespace in docs and UI.

- [x] **Step 3: Update the UI labels and empty states**

Ensure current pages no longer imply that one provider list is shared by all future modules.

- [x] **Step 4: Re-run provider and device API tests**

Run:

```bash
pytest tests/test_provider_api.py tests/test_device_api.py tests/test_pairing_api.py -v
```

Expected: PASS

- [x] **Step 5: Commit**

```bash
git add zhaocai_gateway web tests
git commit -m "refactor: scope current provider admin to openclaw"
```

---

## Task 3: Build the four-module resource center shell in the admin UI

**Files:**

- Modify: `web/src/App.tsx`
- Modify: `web/src/pages/ProvidersPage.tsx`
- Modify: `web/src/styles.css`
- Create: `web/src/pages/GatewayAccountsPage.tsx`
- Create: `web/src/pages/MediaProvidersPage.tsx`
- Create: `web/src/pages/UniversalTemplatesPage.tsx`

- [x] **Step 1: Add module tabs or sub-navigation inside the current provider area**

First-phase provider center should expose:

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

- [x] **Step 2: Keep OpenClaw as the default active module**

Do not break the current workflow for already-tested OpenClaw users.

- [x] **Step 3: Add placeholder or minimal index views for Gateway, Media, and Universal**

These pages should establish the module boundary even before all CRUD behavior lands.

- [x] **Step 4: Run a frontend typecheck/build if the environment allows**

Run:

```bash
npm run typecheck
npm run build
```

Expected: PASS after dependencies are available

- [x] **Step 5: Commit**

```bash
git add web
git commit -m "feat: add modular provider center shell"
```

---

## Task 4: Add Gateway upstream account management and model sync

**Files:**

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/services/gateway_accounts.py`
- Create: `tests/test_gateway_accounts_api.py`

- [x] **Step 1: Add gateway upstream account and gateway model tables**

Introduce:

- `gateway_upstream_accounts`
- `gateway_models`

with fields for auth, health, cooldown, and model discovery.

- [x] **Step 2: Write failing tests for account CRUD, test, and sync**

Cover:

- create upstream account
- validate connection credentials
- sync `/v1/models`
- store discovered models

- [x] **Step 3: Implement service methods and admin routes**

Expose:

- `GET /admin/gateway/accounts`
- `POST /admin/gateway/accounts`
- `POST /admin/gateway/accounts/{id}/test`
- `POST /admin/gateway/accounts/{id}/sync-models`

- [x] **Step 4: Add Gateway Accounts UI**

Allow:

- account create/edit
- test connection
- sync models
- view health state

- [x] **Step 5: Re-run gateway account tests**

Run:

```bash
pytest tests/test_gateway_accounts_api.py -v
```

Expected: PASS

- [x] **Step 6: Commit**

```bash
git add zhaocai_gateway web tests
git commit -m "feat: add gateway upstream account management"
```

---

## Task 5: Add Gateway aliases and alias-target routing

**Files:**

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/services/gateway_aliases.py`
- Create: `web/src/pages/GatewayAliasesPage.tsx`
- Create: `tests/test_gateway_alias_api.py`

- [x] **Step 1: Add alias and alias-target tables**

Introduce:

- `gateway_aliases`
- `gateway_alias_targets`

with priority ordering and per-target fallback flags.

- [x] **Step 2: Write failing alias CRUD and mapping tests**

Cover:

- create alias
- assign multiple ordered targets
- disable alias
- reorder targets

- [x] **Step 3: Implement alias services and routes**

Expose:

- `GET /admin/gateway/aliases`
- `POST /admin/gateway/aliases`
- `PATCH /admin/gateway/aliases/{id}`
- `GET /admin/gateway/aliases/{id}/targets`
- `PUT /admin/gateway/aliases/{id}/targets`

- [x] **Step 4: Add Gateway Aliases UI**

Make it possible to:

- define stable alias keys such as `deep`, `signal/deep`, `draft/deep`
- attach multiple real targets
- inspect ordering and failover policy

- [x] **Step 5: Re-run alias tests**

Run:

```bash
pytest tests/test_gateway_alias_api.py -v
```

Expected: PASS

- [x] **Step 6: Commit**

```bash
git add zhaocai_gateway web tests
git commit -m "feat: add gateway aliases and target mappings"
```

---

## Task 6: Implement Gateway failover behavior in the request path

**Files:**

- Modify: `gateway.py` if legacy runtime reuse is required
- Modify: `zhaocai_gateway/app.py`
- Modify: `zhaocai_gateway/api/admin.py` if health inspection endpoints are needed
- Modify: `zhaocai_gateway/services/gateway_aliases.py`
- Create: `tests/test_gateway_failover.py`

- [ ] **Step 1: Define the first failover policy**

Fallback should occur for:

- timeouts
- connection failures
- DNS / TLS / network errors
- `5xx`
- `429`

Do not automatically fail over for obvious caller-caused `4xx`.

- [ ] **Step 2: Write failing runtime tests**

Cover:

- primary target timeout -> secondary target succeeds
- primary target `5xx` -> secondary target succeeds
- primary target `429` -> secondary target succeeds
- primary target `400` -> error returned, no failover

- [ ] **Step 3: Implement ordered target selection and cooldown**

For each alias:

- try highest-priority healthy target first
- record failure events
- cool down temporarily unhealthy targets
- continue to the next eligible target

- [ ] **Step 4: Add health inspection UI or admin diagnostics**

Make current alias target status visible enough for debugging:

- active target
- recent failures
- cooldown state

- [ ] **Step 5: Re-run failover tests**

Run:

```bash
pytest tests/test_gateway_failover.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway web tests gateway.py
git commit -m "feat: add gateway alias failover routing"
```

---

## Task 7: Add Gateway client keys and unified project access

**Files:**

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/services/gateway_client_keys.py`
- Create: `web/src/pages/GatewayClientKeysPage.tsx`

- [ ] **Step 1: Add client-key storage**

Introduce:

- `gateway_client_keys`

with hashed key storage and enabled/disabled state.

- [ ] **Step 2: Decide the first access policy**

The minimal first release can support:

- one dedicated key for `Content-IP-Strategy`
- optional alias allow-listing later

- [ ] **Step 3: Implement admin APIs and UI**

Expose:

- `GET /admin/gateway/client-keys`
- `POST /admin/gateway/client-keys`
- `PATCH /admin/gateway/client-keys/{id}`

- [ ] **Step 4: Wire the public request path to require a client key**

Requests to the Gateway runtime path should authenticate against this module instead of raw upstream account credentials.

- [ ] **Step 5: Manual smoke test**

Confirm a consumer can use:

- one gateway `baseUrl`
- one gateway `apiKey`
- one stable alias

without needing upstream-specific secrets.

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway web
git commit -m "feat: add gateway client access keys"
```

---

## Task 8: Add Media provider and template management

**Files:**

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/services/media_providers.py`
- Create: `zhaocai_gateway/services/media_templates.py`
- Create: `zhaocai_gateway/services/media_catalog.py`
- Create: `web/src/pages/MediaProvidersPage.tsx`
- Create: `web/src/pages/MediaTemplatesPage.tsx`
- Create: `web/src/pages/MediaTemplateEditorPage.tsx`
- Create: `tests/test_media_template_api.py`
- Create: `tests/test_media_catalog.py`

- [ ] **Step 1: Add media-specific tables**

Introduce:

- `media_providers`
- `media_templates`

Keep these independent from OpenClaw provider/model tables.

- [ ] **Step 2: Write failing media API tests**

Cover:

- media provider CRUD
- media template CRUD
- validation endpoint
- catalog export endpoint

- [ ] **Step 3: Implement admin services and APIs**

Expose:

- `GET /admin/media/providers`
- `POST /admin/media/providers`
- `GET /admin/media/templates`
- `POST /admin/media/templates`
- `POST /admin/media-templates/{id}/validate`
- `GET /admin/media/catalog`

- [ ] **Step 4: Add Media UI**

Allow:

- media provider management
- template editing
- template validation
- catalog preview

- [ ] **Step 5: Re-run media tests**

Run:

```bash
pytest tests/test_media_template_api.py tests/test_media_catalog.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway web tests
git commit -m "feat: add media provider and template module"
```

---

## Task 9: Add Universal template pool and import workflows

**Files:**

- Modify: `zhaocai_gateway/db/schema.py`
- Modify: `zhaocai_gateway/db/store.py`
- Modify: `zhaocai_gateway/domain/models.py`
- Modify: `zhaocai_gateway/services/__init__.py`
- Modify: `zhaocai_gateway/api/admin.py`
- Create: `zhaocai_gateway/services/universal_templates.py`
- Create: `web/src/pages/UniversalTemplatesPage.tsx`
- Create: `tests/test_universal_templates_api.py`

- [ ] **Step 1: Add Universal template tables**

Introduce:

- `universal_provider_templates`
- `universal_provider_template_models`

- [ ] **Step 2: Write failing import tests**

Cover:

- import Universal template into OpenClaw
- import Universal template into Gateway
- import Universal template into Media
- imported records become independent copies

- [ ] **Step 3: Implement import services and endpoints**

Expose:

- `GET /admin/universal/templates`
- `POST /admin/universal/templates`
- `POST /admin/universal/templates/{id}/import/openclaw`
- `POST /admin/universal/templates/{id}/import/gateway`
- `POST /admin/universal/templates/{id}/import/media`

- [ ] **Step 4: Add Universal UI**

Allow operators to:

- maintain reusable templates
- import them into a chosen module
- see where they have been imported

- [ ] **Step 5: Re-run Universal tests**

Run:

```bash
pytest tests/test_universal_templates_api.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add zhaocai_gateway web tests
git commit -m "feat: add universal provider template pool"
```

---

## Task 10: Documentation and consumer handoff

**Files:**

- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/plans/2026-03-31-zhaocai-gateway-v2-modular-provider-design.md` only if needed

- [ ] **Step 1: Update README module overview**

Clarify the four-module architecture:

- `OpenClaw`
- `Gateway`
- `Media`
- `Universal`

- [ ] **Step 2: Document OpenClaw preserve-sidecar behavior**

Explain where the sidecar lives and how operators use it.

- [ ] **Step 3: Document Gateway consumer integration**

Explain how a project such as `Content-IP-Strategy` should connect using:

- one gateway `baseUrl`
- one gateway `apiKey`
- stable aliases instead of raw upstream models

- [ ] **Step 4: Record verification status**

At minimum, note:

- what was tested locally
- what needs Raspberry Pi or real upstream validation
- what still needs manual Cloudflare/public entry verification

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example docs
git commit -m "docs: update v2 modular provider rollout guidance"
```

---

## Recommended Execution Order

1. Task 1: OpenClaw preserve sidecar
2. Task 2: Scope current provider admin to OpenClaw
3. Task 3: Modular provider center shell
4. Task 4: Gateway upstream accounts
5. Task 5: Gateway aliases and mappings
6. Task 6: Gateway failover
7. Task 7: Gateway client keys
8. Task 8: Media module
9. Task 9: Universal templates
10. Task 10: Final docs and handoff

## Checkpoints

- After Task 1, the current OpenClaw workflow should still be deployable without touching Gateway or Media.
- After Task 4, the Gateway module should already be able to connect to upstream accounts and sync model inventory.
- After Task 6, `zhaocai-gateway-v2` should be able to provide stable alias-based failover for external consumers.
- After Task 7, `Content-IP-Strategy` can start migrating to a single gateway `baseUrl + apiKey`.
- After Task 8, `zhaocai-media` can begin moving toward template-driven provider control.
- After Task 9, operators gain efficiency via reusable templates without reintroducing shared mutable runtime state.
