# Zhaocai Gateway Handoff

## Repo Purpose

This repo is the runtime home for the actual `zhaocai-gateway` service.

It should hold:

- gateway implementation
- provider adapters
- control plane
- gateway roadmap and gateway-specific handoff notes

It should not depend on the website repo for its own future implementation notes.


## Verification Note (2026-03-22)

A worker summary claimed that Phase 2 had already been implemented, including:

- `responses/__init__.py`
- `responses/handler.py`
- `scripts/sync_openrouter_free.py`
- `docs/plans/2026-03-22-phase2-impl.md`

However, repository verification showed that these files were not present in the checked-out repo at verification time.

Current conclusion:

- the roadmap is valid
- the implementation summary is **not yet enough for acceptance**
- Phase 2 must be treated as **unlanded until the files are actually created and committed in this repo**

## Confirmed Current Capabilities

The repo already includes:

- gateway runtime in `gateway.py`
- provider adapter layer in `providers/`
- control plane router and storage in `control_plane/`
- model / profile / node management through the control plane
- OpenClaw config compilation

## Confirmed Missing Or Incomplete Areas

The repo does **not** currently expose:

- a first-class `POST /v1/responses`
- an OpenRouter free-model sync workflow
- curated free-model aliases such as `openrouter/free/best`
- explicit `GPT-5.4` routing foundation documentation inside this repo

## Why This Matters

The wider system has already decided that `zhaocai-gateway` should become the preferred bridge for:

- `GPT-5.4` access
- newer response-style inference paths
- curated OpenRouter free-model access

That means future gateway work should happen here, not only inside the website repo docs.

## Immediate Next Work

### 1. Responses API

Add:

- `POST /v1/responses`

Minimum first release:

- text requests
- non-stream or streaming if low-risk
- response envelope compatible enough for internal callers

### 2. GPT-5.4 provider route

Add clear documentation and implementation path for:

- registering `GPT-5.4` providers
- exposing stable aliases
- using the existing control-plane model registry instead of hardcoded logic

### 3. OpenRouter free sync

Add a periodic or on-demand sync that:

- fetches OpenRouter model metadata
- filters free models
- stores curated candidates
- exposes stable aliases for downstream callers

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

