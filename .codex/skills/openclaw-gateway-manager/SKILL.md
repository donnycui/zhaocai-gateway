---
name: openclaw-gateway-manager
description: Manage multi-node OpenClaw model/provider configuration through the Zhaocai control plane. Use when tasks involve creating or updating providers and models, assigning profile-specific model sets to nodes, generating node-scoped openclaw.json, rotating node sync tokens, validating rollout safety, or troubleshooting node sync and gateway routing behavior.
---

# OpenClaw Gateway Manager

Execute the control-plane workflow in this order:

1. Read and confirm control-plane contracts in `references/control-plane-api.md`.
2. Read OpenClaw payload mapping in `references/openclaw-json-mapping.md`.
3. Create or update provider records before touching models.
4. Create or update model aliases and bind them to a profile.
5. Create or update node assignments to profiles.
6. Pull node `openclaw.json` and validate shape before rollout.
7. Rotate node token only when compromise risk or key rollover requires it.

Use these scripts for deterministic operations:

- `scripts/sync_openclaw_json.py` for one-shot pull + write.
- `scripts/validate_node_config.py` for fast JSON shape validation.

Prefer API-first changes:

- Use `POST/PATCH /control/v1/providers` for provider updates.
- Use `POST/PATCH /control/v1/models` for alias and capability changes.
- Use `POST /control/v1/profiles/{profile_id}/bindings` for model set changes.
- Use `GET /control/v1/nodes/{node_id}/openclaw-json` to fetch current node payload.
- Use `GET /control/v1/nodes/{node_id}/versions` to audit config history.

When troubleshooting:

1. Check `/health`, `/v1/providers`, and `/metrics` for gateway-side failures.
2. Check node pull response code (`200` or `304`) and ETag continuity.
3. If node config changed but behavior did not, verify node reload command execution.
4. Validate that model alias exists in both profile bindings and compiled `openclaw.json`.

