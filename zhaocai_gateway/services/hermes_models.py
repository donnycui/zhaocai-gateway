from __future__ import annotations

from dataclasses import asdict
import sqlite3

from zhaocai_gateway.db.store import SQLiteStore


class HermesModelService:
    """Hermes model inventory service."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self, provider_id: int | None = None) -> list[dict]:
        return [asdict(model) for model in self.store.list_hermes_models(provider_id)]

    def get(self, model_id: int) -> dict | None:
        model = self.store.get_hermes_model(model_id)
        if model is None:
            return None
        return asdict(model)

    def create(
        self,
        *,
        provider_id: int,
        upstream_model: str,
        display_name: str,
        enabled: bool,
    ) -> dict:
        provider = self.store.get_hermes_provider(provider_id)
        if provider is None:
            raise ValueError(f"Hermes provider {provider_id} not found")
        try:
            model = self.store.create_hermes_model(
                provider_id=provider_id,
                upstream_model=upstream_model.strip(),
                display_name=display_name.strip(),
                enabled=enabled,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Hermes model already exists for this provider") from exc
        return asdict(model)

    def update(
        self,
        model_id: int,
        *,
        upstream_model: str,
        display_name: str,
        enabled: bool,
    ) -> dict:
        existing = self.store.get_hermes_model(model_id)
        if existing is None:
            raise ValueError(f"Hermes model {model_id} not found")
        try:
            model = self.store.update_hermes_model(
                model_id,
                upstream_model=upstream_model.strip(),
                display_name=display_name.strip(),
                enabled=enabled,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Hermes model already exists for this provider") from exc
        return asdict(model)

    def delete(self, model_id: int) -> None:
        existing = self.store.get_hermes_model(model_id)
        if existing is None:
            raise ValueError(f"Hermes model {model_id} not found")
        self.store.delete_hermes_model(model_id)
