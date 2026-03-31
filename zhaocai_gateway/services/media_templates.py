from __future__ import annotations

from dataclasses import asdict

from zhaocai_gateway.db.store import SQLiteStore

ALLOWED_MEDIA_CAPABILITIES = {"image", "image_edit", "image_to_video", "tts"}
ALLOWED_TEMPLATE_TYPES = {
    "openai_images",
    "gemini_generate_content",
    "bizyair_webapp",
    "siliconflow_tts",
}


class MediaTemplateService:
    """Template registry for the Media module."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(template) for template in self.store.list_media_templates()]

    def create(
        self,
        *,
        provider_id: int,
        model_key: str,
        name: str,
        capability: str,
        template_type: str,
        upstream_model: str,
        ui_group: str,
        ui_label: str,
        ui_description: str,
        ui_badge: str,
        ui_order: int,
        input_schema_json: dict,
        request_template_json: dict,
        response_mapping_json: dict,
        defaults_json: dict,
        enabled: bool,
    ) -> dict:
        provider = self.store.get_media_provider(provider_id)
        if provider is None:
            raise ValueError(f"Media provider {provider_id} not found")

        template = self.store.create_media_template(
            provider_id=provider_id,
            model_key=model_key.strip(),
            name=name.strip(),
            capability=capability.strip(),
            template_type=template_type.strip(),
            upstream_model=upstream_model.strip(),
            ui_group=ui_group.strip(),
            ui_label=ui_label.strip(),
            ui_description=ui_description.strip(),
            ui_badge=ui_badge.strip(),
            ui_order=int(ui_order),
            input_schema_json=input_schema_json,
            request_template_json=request_template_json,
            response_mapping_json=response_mapping_json,
            defaults_json=defaults_json,
            enabled=enabled,
        )
        return asdict(template)

    def validate_payload(self, payload: dict) -> dict:
        errors: list[str] = []
        warnings: list[str] = []

        provider_id = int(payload.get("provider_id") or 0)
        if self.store.get_media_provider(provider_id) is None:
            errors.append("provider_id does not exist")

        capability = str(payload.get("capability") or "").strip()
        if capability not in ALLOWED_MEDIA_CAPABILITIES:
            errors.append("capability is invalid")

        template_type = str(payload.get("template_type") or "").strip()
        if template_type not in ALLOWED_TEMPLATE_TYPES:
            errors.append("template_type is invalid")

        for field in (
            "input_schema_json",
            "request_template_json",
            "response_mapping_json",
            "defaults_json",
        ):
            value = payload.get(field)
            if not isinstance(value, dict):
                errors.append(f"{field} must be an object")

        model_key = str(payload.get("model_key") or "").strip()
        if not model_key:
            errors.append("model_key is required")

        name = str(payload.get("name") or "").strip()
        if not name:
            errors.append("name is required")

        return {
            "ok": len(errors) == 0,
            "message": "Media template payload is valid" if not errors else "Media template payload is invalid",
            "errors": errors,
            "warnings": warnings,
        }
