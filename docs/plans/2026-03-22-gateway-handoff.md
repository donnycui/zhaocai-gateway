# Zhaocai Gateway Handoff

## Repo Purpose

This repo is the runtime home for the actual `zhaocai-gateway` service.

It should hold:

- gateway implementation
- provider adapters
- control plane
- gateway roadmap and gateway-specific handoff notes

It should not depend on the website repo for its own future implementation notes.

## Confirmed Current Capabilities

The repo already includes:

- gateway runtime in `gateway.py`
- provider adapter layer in `providers/`
- control plane router and storage in `control_plane/`
- model / profile / node management through the control plane
- OpenClaw config compilation
- **Responses API** — `POST /v1/responses` (text-first, streaming via synthetic SSE) in `responses/handler.py`
- **OpenRouter free-model sync** — `POST /control/v1/sync/openrouter-free` endpoint + `scripts/sync_openrouter_free.py` CLI
- **Stable free-model aliases** — `openrouter/free/best`, `openrouter/free/general`, `openrouter/free/code`, `openrouter/free/fast`
- **GPT-5.4 routing foundation** — `gpt-5` added to `CHAT_INCLUDE_KEYWORDS`; aliases configured through existing control-plane model registry

## Phase 2 Boundaries (v1)

The following are intentionally **not covered** in the first release:

- Multimodal input (image, file) for Responses API
- Tool use (function calling, code_interpreter, file_search)
- Automatic/cron-based OpenRouter sync (currently manual trigger only)
- Parameter-level differentiation for GPT-5.4 variants (e.g. different temperature for xhigh vs general)

## Completed Phase 2 Work

All items from the Phase 2 plan have been implemented and merged to `main`:

- `responses/__init__.py` + `responses/handler.py` — Responses API handler
- `scripts/sync_openrouter_free.py` — CLI sync script
- `docs/plans/2026-03-22-phase2-impl.md` — implementation record
- `gateway.py` — `/v1/responses` endpoint registered
- `control_plane/router.py` — sync endpoint + `gpt-5` keyword + scoring/classification logic
- `control_plane/store.py` — `upsert_model_by_alias()` method
- `README.md` — updated with Responses API, OpenRouter sync, and GPT-5.4 alias documentation

## Why This Matters

The wider system has already decided that `zhaocai-gateway` should become the preferred bridge for:

- `GPT-5.4` access
- newer response-style inference paths
- curated OpenRouter free-model access

That means future gateway work should happen here, not only inside the website repo docs.

## Immediate Next Work

### 1. Responses API — extend coverage

- Add multimodal input support (images)
- Add tool use / function calling passthrough
- Move from synthetic SSE to true token-level streaming if upstream supports it

### 2. GPT-5.4 provider route — operationalize

- Register real GPT-5.4 providers via control plane once access is available
- Test failover across multiple providers for the same alias
- Consider parameter-level differentiation (xhigh vs general)

### 3. OpenRouter free sync — automate

- Add optional cron/interval-based auto-sync
- Add model offline detection (remove aliases for models that disappear)
- Expose admin visibility into sync candidates and scoring

## Recommended Design Constraint

Keep the gateway as:

- the secret-holding model bridge
- the alias and routing owner
- the control-plane source of truth for upstream providers and downstream model visibility

Do not push model-selection complexity into every downstream node.

## Cross-Repo Context

The website repo now reads real runtime-layer data from:

- `agent_presence`
- `worklogs`
- `missions`

The next architecture step there is to connect real agents.  
The next architecture step here is to make this gateway the model bridge those agents can reliably call.

