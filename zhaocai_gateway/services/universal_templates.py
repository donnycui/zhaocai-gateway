from __future__ import annotations

from dataclasses import asdict

from zhaocai_gateway.db.store import SQLiteStore


class UniversalTemplateService:
    """Reusable provider-template pool with import flows into concrete modules."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        items: list[dict] = []
        for template in self.store.list_universal_provider_templates():
            payload = asdict(template)
            payload["models"] = [asdict(model) for model in self.store.list_universal_provider_template_models(template.id)]
            items.append(payload)
        return items

    def get(self, template_id: int) -> dict | None:
        template = self.store.get_universal_provider_template(template_id)
        if template is None:
            return None
        payload = asdict(template)
        payload["models"] = [asdict(model) for model in self.store.list_universal_provider_template_models(template.id)]
        return payload

    def create(
        self,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key: str,
        protocol: str,
        notes: str,
        models: list[dict],
    ) -> dict:
        template = self.store.create_universal_provider_template(
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            auth_type=auth_type.strip().lower(),
            api_key_encrypted=api_key,
            protocol=protocol.strip() or "openai-compatible",
            notes=notes.strip(),
        )
        created_models = []
        for model in models:
            created_models.append(
                self.store.create_universal_provider_template_model(
                    template_id=template.id,
                    upstream_model=str(model["upstream_model"]).strip(),
                    display_name=str(model["display_name"]).strip(),
                    capabilities=list(model.get("capabilities") or ["text"]),
                    reasoning=bool(model.get("reasoning", False)),
                    input_modalities=list(model.get("input_modalities") or ["text"]),
                    context_window=model.get("context_window"),
                    max_tokens=model.get("max_tokens"),
                    enabled=bool(model.get("enabled", True)),
                )
            )

        payload = asdict(template)
        payload["models"] = [asdict(model) for model in created_models]
        return payload

    def update(
        self,
        template_id: int,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key: str,
        protocol: str,
        notes: str,
        models: list[dict],
    ) -> dict:
        existing = self.store.get_universal_provider_template(template_id)
        if existing is None:
            raise ValueError(f"Universal template {template_id} not found")

        template = self.store.update_universal_provider_template(
            template_id,
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            auth_type=auth_type.strip().lower(),
            api_key_encrypted=api_key,
            protocol=protocol.strip() or "openai-compatible",
            notes=notes.strip(),
        )
        self.store.delete_universal_provider_template_models(template_id)

        created_models = []
        for model in models:
            created_models.append(
                self.store.create_universal_provider_template_model(
                    template_id=template.id,
                    upstream_model=str(model["upstream_model"]).strip(),
                    display_name=str(model["display_name"]).strip(),
                    capabilities=list(model.get("capabilities") or ["text"]),
                    reasoning=bool(model.get("reasoning", False)),
                    input_modalities=list(model.get("input_modalities") or ["text"]),
                    context_window=model.get("context_window"),
                    max_tokens=model.get("max_tokens"),
                    enabled=bool(model.get("enabled", True)),
                )
            )

        payload = asdict(template)
        payload["models"] = [asdict(model) for model in created_models]
        return payload

    def delete(self, template_id: int) -> None:
        template = self.store.get_universal_provider_template(template_id)
        if template is None:
            raise ValueError(f"Universal template {template_id} not found")
        self.store.delete_universal_provider_template_models(template_id)
        self.store.delete_universal_provider_template(template_id)

    def import_to_openclaw(self, template_id: int) -> dict:
        template, template_models = self._load_template_bundle(template_id)

        provider = self.store.create_provider(
            name=template.name,
            provider_type="openai-completions",
            base_url=template.base_url,
            auth_scheme="bearer" if template.auth_type == "bearer" else template.auth_type,
            api_key_encrypted=template.api_key_encrypted,
            extra_headers={},
            enabled=True,
        )
        created_models = []
        for item in template_models:
            created_models.append(
                self.store.create_model(
                    provider_id=provider.id,
                    upstream_model=item.upstream_model,
                    display_name=item.display_name,
                    capabilities=item.capabilities,
                    reasoning=item.reasoning,
                    input_modalities=item.input_modalities,
                    context_window=item.context_window,
                    max_tokens=item.max_tokens,
                    enabled=item.enabled,
                )
            )
        return {
            "provider": asdict(provider),
            "models": [asdict(model) for model in created_models],
        }

    def import_to_gateway(self, template_id: int) -> dict:
        template, template_models = self._load_template_bundle(template_id)

        account = self.store.create_gateway_upstream_account(
            name=template.name,
            base_url=template.base_url,
            auth_type=template.auth_type,
            api_key_encrypted=template.api_key_encrypted,
            protocol=template.protocol,
            enabled=True,
            notes=template.notes,
        )
        created_models = []
        for item in template_models:
            created_models.append(
                self.store.upsert_gateway_model(
                    account_id=account.id,
                    upstream_model=item.upstream_model,
                    display_name=item.display_name,
                    family=None,
                    supports_chat=True,
                    supports_responses=True,
                    enabled=item.enabled,
                )
            )
        return {
            "account": asdict(account),
            "models": [asdict(model) for model in created_models],
        }

    def import_to_media(self, template_id: int) -> dict:
        template, _template_models = self._load_template_bundle(template_id)

        provider = self.store.create_media_provider(
            name=template.name,
            base_url=template.base_url,
            auth_type=template.auth_type,
            api_key_encrypted=template.api_key_encrypted,
            enabled=True,
            notes=template.notes,
        )
        return {"provider": asdict(provider)}

    def _load_template_bundle(self, template_id: int):
        template = self.store.get_universal_provider_template(template_id)
        if template is None:
            raise ValueError(f"Universal template {template_id} not found")
        template_models = self.store.list_universal_provider_template_models(template_id)
        return template, template_models
