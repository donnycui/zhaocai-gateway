from __future__ import annotations

from dataclasses import asdict

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
