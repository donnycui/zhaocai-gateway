# OpenClaw JSON Mapping

The control plane compiles one node-scoped payload with the shape:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-03-04T00:00:00Z",
  "node": {
    "id": 1,
    "name": "vps-1",
    "sync_mode": "pull",
    "active": true
  },
  "profile": {
    "id": 2,
    "name": "prod-cn",
    "description": "..."
  },
  "providers": [
    {
      "id": "openai-main",
      "type": "openai",
      "base_url": "https://api.openai.com/v1",
      "auth_scheme": "bearer",
      "api_key": "sk-...",
      "secret_ref": "",
      "extra_headers": {},
      "enabled": true
    }
  ],
  "models": [
    {
      "id": "gpt-4o",
      "provider": "openai-main",
      "upstream_model": "gpt-4o",
      "capabilities": ["chat"],
      "enabled": true
    }
  ],
  "model_routing": {
    "gpt-4o": "openai-main"
  }
}
```

Rules:

1. Include only enabled models bound to the node's profile.
2. Include only providers referenced by included models.
3. Keep `id` in `models` as the client-facing alias.
4. Keep `upstream_model` as the provider-native model identifier.
5. Use `model_routing[alias]` for deterministic provider dispatch.

