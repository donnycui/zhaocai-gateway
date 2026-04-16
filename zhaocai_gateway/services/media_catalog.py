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
                    "mode": self._to_catalog_mode(template.capability),
                    "provider": provider.name,
                    "template_type": template.template_type,
                    "model_key": template.model_key,
                    "upstream_model": template.upstream_model,
                    "display_name": template.ui_label or template.name,
                    "description": template.ui_description,
                    "badge": template.ui_badge,
                    "enabled": template.enabled,
                    "ui_order": template.ui_order,
                    "ratios": self._extract_ratios(template),
                    "resolutions": self._extract_resolutions(template),
                    "requires_start_image": self._requires_start_image(template),
                    "requires_end_image": self._requires_end_image(template),
                    "is_paid": False,
                    "tags": self._build_tags(template),
                    "defaults": template.defaults_json,
                }
            )
        return catalog

    @staticmethod
    def _to_catalog_mode(capability: str) -> str:
        return "video" if capability == "image_to_video" else capability

    @staticmethod
    def _extract_enum_options(template, field_names: list[str]) -> list[str]:
        schema = template.input_schema_json if isinstance(template.input_schema_json, dict) else {}
        for field_name in field_names:
            field = schema.get(field_name)
            if isinstance(field, dict):
                options = field.get("options")
                if isinstance(options, list):
                    return [str(option) for option in options]
        return []

    @classmethod
    def _extract_resolutions(cls, template) -> list[str]:
        return cls._extract_enum_options(template, ["resolution", "resolutions"])

    @classmethod
    def _extract_ratios(cls, template) -> list[str]:
        explicit = cls._extract_enum_options(template, ["aspect_ratio", "ratio", "ratios"])
        if explicit:
            return explicit
        size_options = cls._extract_enum_options(template, ["size"])
        size_to_ratio = {
            "1024x1024": "1:1",
            "1024x1792": "9:16",
            "1792x1024": "16:9",
            "1280x720": "16:9",
            "720x1280": "9:16",
        }
        ratios: list[str] = []
        for size in size_options:
            ratio = size_to_ratio.get(size)
            if ratio and ratio not in ratios:
                ratios.append(ratio)
        return ratios

    @staticmethod
    def _requires_start_image(template) -> bool:
        schema = template.input_schema_json if isinstance(template.input_schema_json, dict) else {}
        return any(key in schema for key in ("image", "image_url", "images", "start_image_url"))

    @staticmethod
    def _requires_end_image(template) -> bool:
        schema = template.input_schema_json if isinstance(template.input_schema_json, dict) else {}
        return "end_image_url" in schema

    @staticmethod
    def _build_tags(template) -> list[str]:
        tags = [template.capability]
        if template.template_type not in tags:
            tags.append(template.template_type)
        return tags
