# Zhaocai Gateway

Zhaocai Gateway is now both:

1. An OpenAI-compatible inference gateway (`/v1/chat/completions`).
2. A control plane for multi-node OpenClaw configuration distribution (`/control/v1/...`).

It is designed for the scenario where you have many providers/models and multiple OpenClaw nodes
(Raspberry Pi, VPS, etc.) that need different subsets of those models.

## Core capabilities

- Multi-provider request routing (`round_robin`, `weighted`, `priority`).
- Fallback retries across providers.
- Basic per-client rate limiting.
- Provider adapter layer for auth/endpoint differences (OpenAI-compatible + Anthropic).
- Control plane data model:
  - Providers
  - Models
  - Profiles
  - Profile model bindings
  - Nodes
  - Node config versions
- Node-scoped `openclaw.json` generation + pull protocol:
  - Node bearer token auth
  - `ETag` + `If-None-Match`
  - `304` for no changes
- Minimal web control panel at `/control`.

## Quick start

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Prepare config and env

```bash
cp .env.example .env
cp config.example.yaml config.yaml
```

Set at least:

- `ZHAOCAI_ADMIN_TOKEN`
- provider API keys in `.env`

## 3) Run

```bash
python gateway.py
```

Gateway will be available at:

- API docs: `http://localhost:8000/docs`
- Control panel: `http://localhost:8000/control`

## Inference API

## Chat completions

`POST /v1/chat/completions`

Example:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role":"user","content":"hello"}]
  }'
```

## Gateway control/observability

- `GET /health`
- `GET /v1/models`
- `GET /v1/providers`
- `GET /metrics`

## Control plane API

Admin header:

```text
X-Admin-Token: <ZHAOCAI_ADMIN_TOKEN>
```

### Providers

- `POST /control/v1/providers`
- `PATCH /control/v1/providers/{provider_id}`
- `GET /control/v1/providers`

### Models

- `POST /control/v1/models`
- `PATCH /control/v1/models/{model_id}`
- `GET /control/v1/models`

### Profiles

- `POST /control/v1/profiles`
- `POST /control/v1/profiles/{profile_id}/bindings`
- `GET /control/v1/profiles`

### Nodes

- `POST /control/v1/nodes`
- `PATCH /control/v1/nodes/{node_id}`
- `POST /control/v1/nodes/{node_id}/sync-token/rotate`
- `GET /control/v1/nodes/{node_id}/versions`
- `GET /control/v1/nodes`

### Node config pull

`GET /control/v1/nodes/{node_id}/openclaw-json`

Auth for node pull:

```text
Authorization: Bearer <node_pull_token>
```

Conditional pull:

- Request header: `If-None-Match: "<etag>"`
- Response: `304` if unchanged, or `200` with payload + `ETag`

## Node sync agent

Use `scripts/node_sync_agent.py` to keep a node in sync:

```bash
python scripts/node_sync_agent.py \
  --base-url http://127.0.0.1:8000 \
  --node-id 1 \
  --pull-token zg_node_1_xxx \
  --output /etc/openclaw/openclaw.json \
  --interval 60 \
  --reload-cmd "systemctl restart openclaw"
```

## Provider bootstrap helper

Use `scripts/bootstrap_provider.py` to register one provider and models quickly:

```bash
python scripts/bootstrap_provider.py \
  --base-url http://127.0.0.1:8000 \
  --admin-token "$ZHAOCAI_ADMIN_TOKEN" \
  --name openai-main \
  --provider-type openai \
  --provider-base-url https://api.openai.com/v1 \
  --auth-scheme bearer \
  --api-key sk-xxx \
  --models gpt-4o,gpt-4o-mini
```

## OpenClaw Skill

This repo ships a skill in:

`./.codex/skills/openclaw-gateway-manager`

It includes:

- `SKILL.md` workflow
- API and JSON mapping references
- scripts for pull and validation
- `agents/openai.yaml`

## Notes

- Control plane DB defaults to SQLite:
  - `ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db`
- PostgreSQL backend is intentionally reserved but not implemented in this revision.
- Stream mode is exposed as OpenAI SSE format and currently synthesized from non-stream upstream responses.

