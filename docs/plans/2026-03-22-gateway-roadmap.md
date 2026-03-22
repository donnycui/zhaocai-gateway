# Zhaocai Gateway Roadmap

## Goal

Make `zhaocai-gateway` the real model-routing bridge for the broader system rather than only an OpenAI-compatible chat gateway and OpenClaw control plane.

The next stage is to turn the gateway into the preferred bridge for:

- broader model access into the orchestration layer
- `GPT-5.4` class routing
- `Responses API` compatibility
- OpenRouter free-model syncing and stable aliases

## Current State

Today the gateway already provides:

- OpenAI-compatible chat completions
- provider routing
- control plane CRUD for providers / models / profiles / nodes
- model compilation for OpenClaw nodes
- health and control panel surfaces

Current strength:

- central-provider and node-control design is already correct
- the control plane can manage models as aliases over upstream providers

Current gap:

- it is still centered on `/v1/chat/completions`
- it does not yet expose a first-class `/v1/responses`
- it does not yet provide curated model aliases such as a “best free” OpenRouter route

## Priority Features

### 1. Responses API compatibility

Add a new inference surface:

- `POST /v1/responses`

This should become the preferred bridge for newer model clients and future orchestration paths that are not strictly chat-completions shaped.

Minimum expectations:

- accept an OpenAI-style Responses payload
- translate it to the upstream provider format
- preserve streaming where practical
- return an OpenAI-compatible response envelope

Initial scope can be limited:

- text-only first
- no multimodal parity required in the first release
- no tool orchestration parity required in the first release

### 2. GPT-5.4 routing foundation

The gateway should become the preferred route for `GPT-5.4` access in the wider system.

Expected outcomes:

- register one or more `GPT-5.4`-class providers in the control plane
- expose stable aliases suitable for OpenClaw and other internal clients
- allow policy-driven routing and failover through the existing provider manager

Examples of future alias shapes:

- `gpt-5.4`
- `gpt-5.4-xhigh`
- `gpt-5.4-general`

### 3. OpenRouter free-model sync and stable aliases

The gateway should periodically pull OpenRouter model metadata and maintain a curated free-model registry.

Do not treat “most used” as automatically “best”.

Recommended internal model buckets:

- `openrouter/free/best`
- `openrouter/free/general`
- `openrouter/free/code`
- `openrouter/free/fast`

Recommended selection dimensions:

- stability
- capability fit
- popularity

The gateway should own the alias decision so downstream clients do not need to know raw OpenRouter model ids.

## Suggested Implementation Order

1. add `Responses API` surface
2. add provider / model registration path for `GPT-5.4`
3. add OpenRouter free-model sync job
4. add curated alias resolution over synced models
5. expose admin visibility for synced free-model candidates

## Notes For Future Workers

- do not overbuild the first `Responses API` implementation
- do not block on multimodal parity
- prefer a clear compatibility layer over speculative abstraction
- the control plane already provides the right long-term place for model aliasing

