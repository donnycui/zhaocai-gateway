# Zhaocai Gateway v2.0 Design

## Goal

Build `zhaocai-gateway v2.0` as a centralized control plane for managing upstream model providers and distributing per-device OpenClaw configuration from a Raspberry Pi-hosted web console.

Phase 1 focuses on:

- centralized provider and model management
- node pairing and device registration
- per-device model assignment
- agent-based config sync to each machine's local OpenClaw config
- a simple web UI that is easy to understand and operate

Phase 2 can optionally add hybrid data-plane behavior:

- some models continue to run directly from node-local provider config
- some models can be proxied through the Raspberry Pi gateway when needed

## Problem Statement

The current repository proves the core idea but is difficult to operate:

- UI is confusing and too dense
- control-plane concepts are mixed with gateway runtime concerns
- provider setup across Raspberry Pi, Mac, and multiple VPS nodes is still operationally heavy
- current mental model is not obvious: it is unclear which settings are central, which are local, and how nodes should be updated safely

The desired operating model is:

- all upstream providers, base URLs, API keys, and models are defined once on the Raspberry Pi
- each node installs a lightweight local agent
- each node pairs to the control plane
- each node receives only the models assigned to it
- nodes update their local OpenClaw config automatically

## Product Shape

`zhaocai-gateway v2.0` is a web-first control plane, not a local provider switcher like `cc-switch`.

It should be treated as:

- a central source of truth for provider definitions
- a central source of truth for model inventory
- a central source of truth for device-to-model assignments
- a config distribution service for OpenClaw nodes

It should not rely on humans manually editing local environment variables on every machine.

Instead, each machine runs a small `node-agent` that:

- registers with the control plane
- obtains a long-lived sync token
- polls for config updates
- writes node-specific OpenClaw config locally
- triggers OpenClaw reload or restart after changes

## Recommended Architecture

Recommended approach: web-first single service with strict internal layering.

The service runs on the Raspberry Pi and contains:

- `admin api`
  - used by the browser UI
- `agent api`
  - used by paired nodes for registration, heartbeat, and config sync
- `store`
  - SQLite-based system of record
- `compiler`
  - builds node-specific OpenClaw config payloads
- `web ui`
  - browser-based management console

Internal engineering should borrow from `cc-switch`:

- SQLite as the single source of truth
- explicit schema and migration handling
- repository and service boundaries
- atomic writes and config backups
- clear split between data storage, business logic, and UI

The product model should not copy `cc-switch`'s local-environment-variable switching flow.

## Scope and Non-Goals

### In Scope for Phase 1

- provider CRUD
- model CRUD
- device registration and pairing
- per-device model assignment
- config snapshot generation
- node heartbeat and sync status
- simple browser UI
- Tailscale-friendly deployment model

### Out of Scope for Phase 1

- full gateway proxy for all inference traffic
- complex routing policies exposed in UI
- profile-based assignment model
- multi-tenant RBAC
- websocket push sync
- rich observability dashboards
- unified local desktop app

### Deferred to Phase 2

- hybrid mode where selected models are routed through the Raspberry Pi gateway
- request proxying and access control tied to device identity
- advanced health and performance routing

## Data Model

Phase 1 should keep the data model minimal and operationally obvious.

### Core Entities

- `providers`
  - upstream service definition
  - fields: `name`, `provider_type`, `base_url`, `auth_scheme`, `api_key_encrypted`, `extra_headers`, `enabled`

- `models`
  - real models exposed by a provider
  - fields: `provider_id`, `upstream_model`, `display_name`, `capabilities`, `context_window`, `max_tokens`, `enabled`

- `devices`
  - a managed machine such as `mac`, `vps1`, `vps2`
  - fields: `name`, `device_type`, `hostname`, `platform`, `active`, `last_seen_at`, `sync_token_hash`, `current_config_version`

- `device_model_bindings`
  - direct mapping from a device to the models it is allowed to sync
  - this replaces the current `Profile` abstraction

- `pairing_tokens`
  - one-time registration tokens
  - fields: `device_id`, `token_hash`, `expires_at`, `used_at`

- `config_snapshots`
  - generated config payloads per device
  - fields: `device_id`, `version`, `etag`, `payload_json`, `content_hash`, `created_at`

### Explicit Decision

Phase 1 does not use `profiles`.

The UI should let the operator assign models directly to devices because that matches the intended real-world workflow more closely.

## UI Information Architecture

The UI should remain intentionally small.

### Pages

- `Dashboard`
  - provider count
  - model count
  - device count
  - offline or sync-error devices
  - recent changes

- `Providers`
  - provider list
  - add provider
  - validate provider
  - inspect provider models

- `Devices`
  - device list with online state and sync version
  - per-device model assignment
  - config preview
  - sync status

- `Nodes`
  - create a device
  - generate registration token
  - show install/register command for `node-agent`
  - rotate sync token

### UI Principles

- keep the number of top-level pages low
- remove profile-heavy abstractions
- make "connect provider", "register device", and "assign models" the primary happy path
- default to tables and detail drawers instead of separate static pages

## Node Pairing and Sync Flow

### Pairing

1. Operator creates a device in the UI.
2. Control plane generates a one-time registration token.
3. Operator runs `node-agent register --server ... --token ...` on the target machine.
4. Agent registers machine metadata with the control plane.
5. Control plane returns a long-lived sync token.
6. Agent stores the sync token locally and becomes a managed node.

### Sync

The agent should poll in two steps:

- `GET /agent/v1/config/meta`
  - lightweight version and etag check
- `GET /agent/v1/config`
  - full payload download when version changes

After download, the agent:

- writes the local OpenClaw config atomically
- keeps a local backup
- attempts reload or restart
- reports result back to the control plane

## Network Topology

Recommended default: Tailscale.

Why:

- no public IP is required for the Raspberry Pi
- Raspberry Pi, Mac, and VPS nodes can communicate over a private tailnet
- this fits the control-plane use case well

Phase 1 only requires control-plane reachability for pairing and config sync.

Inference traffic does not need to traverse the Raspberry Pi in Phase 1.

This avoids turning the Raspberry Pi into a mandatory data-plane bottleneck too early.

## Error Handling and Recovery

Phase 1 should explicitly handle:

- invalid provider credentials
- registration token failure
- node sync failure
- local file write failure
- OpenClaw reload failure
- config generation failure caused by bad bindings or disabled upstream models

Recovery path:

- keep config snapshots in the control plane
- keep local config backups on the node
- allow reissuing sync tokens
- show last sync error directly on the device detail page

## Testing Strategy

The test strategy should prioritize control-plane correctness over UI exhaustiveness.

Minimum required coverage:

- config compiler tests
- provider and model persistence tests
- device registration and token lifecycle tests
- config version and etag tests
- simple UI happy-path tests for provider creation, device creation, and per-device assignment

## Implementation Direction

Recommended implementation stack:

- backend: Python + FastAPI
- persistence: SQLite
- web UI: React + Vite, served as static assets by the backend
- node agent: Python CLI/service

Reasoning:

- it preserves momentum from the current repository
- it keeps deployment lightweight on the Raspberry Pi
- it allows the repo to borrow `cc-switch`'s structure without forcing a Rust/Tauri rewrite

## Phased Delivery

### Phase 1

- central provider and model inventory
- device pairing
- per-device model assignment
- node-agent sync
- simple UI

### Phase 2

- hybrid mode
- selected model proxying through the Raspberry Pi
- richer routing and health policies

## Assumptions

- the Raspberry Pi can run the control plane continuously
- Tailscale or equivalent private networking is acceptable
- nodes can tolerate an automatic OpenClaw reload or restart after config changes
- raw model names are preferred over abstract aliases like `best` or `fast`

