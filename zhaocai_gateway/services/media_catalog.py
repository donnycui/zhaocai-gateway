from __future__ import annotations

from zhaocai_gateway.db.store import SQLiteStore


class MediaCatalogService:
    """Exports the simplified media catalog for downstream consumers."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def export(self) -> list[dict]:
        catalog: list[dict] = []
        for template in self.store.list_media_templates():
            if not template.enabled:
                continue
            provider = self.store.get_media_provider(template.provider_id)
            if provider is None or not provider.enabled:
                continue

            catalog.append(
                {
                    "id": template.id,
                    "template_id": template.id,
                    "mode": template.capability,
                    "provider": provider.name,
                    "template_type": template.template_type,
                    "model_key": template.model_key,
                    "upstream_model": template.upstream_model,
                    "display_name": template.ui_label or template.name,
                    "description": template.ui_description,
                    "badge": template.ui_badge,
                    "enabled": template.enabled,
                    "ui_order": template.ui_order,
                    "ratios": [],
                    "resolutions": [],
                    "requires_start_image": False,
                    "requires_end_image": False,
                    "is_paid": False,
                    "tags": [template.capability],
                    "defaults": template.defaults_json,
                }
            )
        return catalog
