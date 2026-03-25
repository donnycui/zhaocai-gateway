from __future__ import annotations

from dataclasses import asdict

import httpx

from zhaocai_gateway.db.store import SQLiteStore


class ModelService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(model) for model in self.store.list_models()]

    def create(
        self,
        *,
        provider_id: int,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        context_window: int | None,
        max_tokens: int | None,
        enabled: bool,
    ) -> dict:
        model = self.store.create_model(
            provider_id=provider_id,
            upstream_model=upstream_model,
            display_name=display_name,
            capabilities=capabilities,
            context_window=context_window,
            max_tokens=max_tokens,
            enabled=enabled,
        )
        return asdict(model)

    def sync_openrouter_free(self) -> dict:
        response = httpx.get("https://openrouter.ai/api/v1/models", timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("data", [])
        if not isinstance(items, list):
            items = []

        free_models = []
        for item in items:
            if not isinstance(item, dict):
                continue
            pricing = item.get("pricing", {})
            if not isinstance(pricing, dict):
                continue
            try:
                if float(pricing.get("prompt", "1")) == 0 and float(pricing.get("completion", "1")) == 0:
                    free_models.append(item)
            except (TypeError, ValueError):
                continue

        provider = self.store.get_provider_by_name("openrouter")
        if provider is None:
            provider = self.store.create_provider(
                name="openrouter",
                provider_type="openai",
                base_url="https://openrouter.ai/api/v1",
                auth_scheme="bearer",
                api_key_encrypted="",
                extra_headers={},
                enabled=True,
            )

        created = 0
        updated = 0
        for item in free_models:
            upstream_model = str(item.get("id", "")).strip()
            if not upstream_model:
                continue
            display_name = str(item.get("name") or upstream_model).strip()
            capabilities = ["text"]
            lowered = upstream_model.lower()
            if ("code" in lowered or "coder" in lowered) and "coding" not in capabilities:
                capabilities.append("coding")
            if ("reason" in lowered or lowered.endswith("r1")) and "reasoning" not in capabilities:
                capabilities.append("reasoning")
            context_window = None
            try:
                context_window = int(item.get("context_length") or 0) or None
            except (TypeError, ValueError):
                context_window = None

            existing = self.store.get_model_by_provider_and_upstream(provider.id, upstream_model)
            self.store.upsert_model(
                provider_id=provider.id,
                upstream_model=upstream_model,
                display_name=display_name,
                capabilities=capabilities,
                context_window=context_window,
                max_tokens=None,
                enabled=True,
            )
            if existing is None:
                created += 1
            else:
                updated += 1

        return {
            "provider_id": provider.id,
            "free_models_found": len(free_models),
            "created": created,
            "updated": updated,
        }
