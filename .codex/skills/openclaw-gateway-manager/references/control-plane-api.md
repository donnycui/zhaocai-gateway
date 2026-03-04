# Control Plane API Reference

## Auth

- Admin API: `X-Admin-Token: <token>`
- Node pull API: `Authorization: Bearer <node_pull_token>`

## Provider APIs

1. `POST /control/v1/providers`
2. `PATCH /control/v1/providers/{provider_id}`

Request fields:

- `name`
- `provider_type` (`openai` or `anthropic`)
- `base_url`
- `auth_scheme` (`bearer` or `x-api-key`)
- `api_key`
- `secret_ref`
- `enabled`
- `extra_headers`

## Model APIs

1. `POST /control/v1/models`
2. `PATCH /control/v1/models/{model_id}`

Request fields:

- `provider_id`
- `upstream_model`
- `alias`
- `enabled`
- `capabilities` (string list)

## Profile APIs

1. `POST /control/v1/profiles`
2. `POST /control/v1/profiles/{profile_id}/bindings`

Bindings replace the full model-id set for the profile.

## Node APIs

1. `POST /control/v1/nodes`
2. `PATCH /control/v1/nodes/{node_id}`
3. `POST /control/v1/nodes/{node_id}/sync-token/rotate`
4. `GET /control/v1/nodes/{node_id}/versions`

## Node Config Pull API

`GET /control/v1/nodes/{node_id}/openclaw-json`

Behavior:

- Supports `If-None-Match`.
- Returns `304` when unchanged.
- Returns `200` with JSON payload when changed.
- Returns headers:
  - `ETag`
  - `X-Config-Version`

