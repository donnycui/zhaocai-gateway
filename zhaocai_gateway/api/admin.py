from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import (
    ConfigCompilerService,
    DeviceService,
    GatewayAccountService,
    GatewayAliasService,
    GatewayClientKeyService,
    MediaCatalogService,
    MediaProviderService,
    MediaTemplateService,
    ModelService,
    PairingService,
    ProviderService,
    UniversalTemplateService,
)


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    auth_scheme: str = Field(min_length=1)
    api_key: str = ""
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ProviderValidate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    auth_scheme: str = Field(min_length=1)
    api_key: str = ""
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ProviderDiscover(BaseModel):
    base_url: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    auth_scheme: str = Field(min_length=1)
    api_key: str = ""
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    auth_scheme: str = Field(min_length=1)
    api_key: str = ""
    enabled: bool = True
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ModelCreate(BaseModel):
    provider_id: int
    upstream_model: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    reasoning: bool = False
    input_modalities: list[str] = Field(default_factory=lambda: ["text"])
    context_window: int | None = None
    max_tokens: int | None = None
    cost_input: float | None = None
    cost_output: float | None = None
    cost_cache_read: float | None = None
    cost_cache_write: float | None = None
    enabled: bool = True


class ModelUpdate(BaseModel):
    upstream_model: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    reasoning: bool = False
    input_modalities: list[str] = Field(default_factory=lambda: ["text"])
    context_window: int | None = None
    max_tokens: int | None = None
    cost_input: float | None = None
    cost_output: float | None = None
    cost_cache_read: float | None = None
    cost_cache_write: float | None = None
    enabled: bool = True


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1)
    device_type: str = Field(min_length=1)
    hostname: str = ""
    platform: str = ""
    active: bool = True


class PairingTokenCreate(BaseModel):
    expires_in_seconds: int = 600


class DeviceModelBindingUpdate(BaseModel):
    model_ids: list[int] = Field(default_factory=list)


class DevicePreserveConfigUpdate(BaseModel):
    preserve_providers: list[str] = Field(default_factory=list)
    preserve_models: list[str] = Field(default_factory=list)


class GatewayAccountCreate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    auth_type: str = Field(min_length=1)
    api_key: str = ""
    protocol: str = "openai-compatible"
    notes: str = ""


class GatewayAliasCreate(BaseModel):
    alias_key: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    alias_type: str = Field(min_length=1)
    visibility: str = "project"
    notes: str = ""


class GatewayAliasUpdate(BaseModel):
    display_name: str = Field(min_length=1)
    enabled: bool = True
    visibility: str = "project"
    notes: str = ""


class GatewayAliasTargetInput(BaseModel):
    account_id: int
    model_id: int
    priority: int
    enabled: bool = True
    fallback_on_timeout: bool = True
    fallback_on_5xx: bool = True
    fallback_on_429: bool = True
    cooldown_seconds: int = 120


class GatewayAliasTargetsUpdate(BaseModel):
    targets: list[GatewayAliasTargetInput] = Field(default_factory=list)


class GatewayClientKeyCreate(BaseModel):
    name: str = Field(min_length=1)
    api_key: str = ""
    notes: str = ""


class GatewayClientKeyUpdate(BaseModel):
    enabled: bool = True
    notes: str = ""


class MediaProviderCreate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    auth_type: str = Field(min_length=1)
    api_key: str = ""
    notes: str = ""


class MediaTemplateCreate(BaseModel):
    provider_id: int
    model_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    template_type: str = Field(min_length=1)
    upstream_model: str = Field(min_length=1)
    ui_group: str = ""
    ui_label: str = ""
    ui_description: str = ""
    ui_badge: str = ""
    ui_order: int = 0
    input_schema_json: dict = Field(default_factory=dict)
    request_template_json: dict = Field(default_factory=dict)
    response_mapping_json: dict = Field(default_factory=dict)
    defaults_json: dict = Field(default_factory=dict)
    enabled: bool = True


class UniversalTemplateModelCreate(BaseModel):
    upstream_model: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=lambda: ["text"])
    reasoning: bool = False
    input_modalities: list[str] = Field(default_factory=lambda: ["text"])
    context_window: int | None = None
    max_tokens: int | None = None
    enabled: bool = True


class UniversalTemplateCreate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    auth_type: str = Field(min_length=1)
    api_key: str = ""
    protocol: str = "openai-compatible"
    notes: str = ""
    models: list[UniversalTemplateModelCreate] = Field(default_factory=list)


def create_admin_router(store: SQLiteStore, *, admin_token: str) -> APIRouter:
    provider_service = ProviderService(store)
    model_service = ModelService(store)
    device_service = DeviceService(store)
    pairing_service = PairingService(store)
    compiler_service = ConfigCompilerService(store)
    gateway_account_service = GatewayAccountService(store)
    gateway_alias_service = GatewayAliasService(store)
    gateway_client_key_service = GatewayClientKeyService(store)
    media_provider_service = MediaProviderService(store)
    media_template_service = MediaTemplateService(store)
    media_catalog_service = MediaCatalogService(store)
    universal_template_service = UniversalTemplateService(store)
    router = APIRouter(prefix="/admin", tags=["admin"])

    def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
        if not admin_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ZHAOCAI_ADMIN_TOKEN is not configured",
            )
        if x_admin_token != admin_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin token",
            )

    # OpenClaw module: the current provider/model/device routes remain the
    # stable v2 surface while Gateway, Media, and Universal are introduced in
    # separate namespaces.
    @router.get("/providers")
    def list_providers(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"providers": provider_service.list()}

    @router.get("/providers/{provider_id}")
    def get_provider(provider_id: int, x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        provider = provider_service.get(provider_id)
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        return {"provider": provider, "models": model_service.list_for_provider(provider_id)}

    @router.post("/providers")
    def create_provider(
        payload: ProviderCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "provider": provider_service.create(
                name=payload.name,
                base_url=payload.base_url,
                provider_type=payload.provider_type,
                auth_scheme=payload.auth_scheme,
                api_key=payload.api_key,
                extra_headers=payload.extra_headers,
            )
        }

    @router.patch("/providers/{provider_id}")
    def update_provider(
        provider_id: int,
        payload: ProviderUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "provider": provider_service.update(
                provider_id,
                name=payload.name,
                base_url=payload.base_url,
                provider_type=payload.provider_type,
                auth_scheme=payload.auth_scheme,
                api_key=payload.api_key,
                extra_headers=payload.extra_headers,
                enabled=payload.enabled,
            )
        }

    @router.delete("/providers/{provider_id}")
    def delete_provider(
        provider_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        provider_service.delete(provider_id)
        return {"ok": True, "provider_id": provider_id}

    @router.post("/providers/validate")
    def validate_provider(
        payload: ProviderValidate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return provider_service.validate(
            base_url=payload.base_url,
            auth_scheme=payload.auth_scheme,
        )

    @router.post("/providers/discover-models")
    def discover_provider_models(
        payload: ProviderDiscover,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return provider_service.discover_models(
                base_url=payload.base_url,
                provider_type=payload.provider_type,
                auth_scheme=payload.auth_scheme,
                api_key=payload.api_key,
                extra_headers=payload.extra_headers,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    @router.post("/providers/{provider_id}/test")
    def test_provider(
        provider_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return provider_service.test_connectivity(provider_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.get("/models")
    def list_models(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"models": model_service.list()}

    @router.post("/models")
    def create_model(
        payload: ModelCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "model": model_service.create(
                provider_id=payload.provider_id,
                upstream_model=payload.upstream_model,
                display_name=payload.display_name,
                capabilities=payload.capabilities,
                reasoning=payload.reasoning,
                input_modalities=payload.input_modalities,
                context_window=payload.context_window,
                max_tokens=payload.max_tokens,
                cost_input=payload.cost_input,
                cost_output=payload.cost_output,
                cost_cache_read=payload.cost_cache_read,
                cost_cache_write=payload.cost_cache_write,
                enabled=payload.enabled,
            )
        }

    @router.patch("/models/{model_id}")
    def update_model(
        model_id: int,
        payload: ModelUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "model": model_service.update(
                model_id,
                upstream_model=payload.upstream_model,
                display_name=payload.display_name,
                capabilities=payload.capabilities,
                reasoning=payload.reasoning,
                input_modalities=payload.input_modalities,
                context_window=payload.context_window,
                max_tokens=payload.max_tokens,
                cost_input=payload.cost_input,
                cost_output=payload.cost_output,
                cost_cache_read=payload.cost_cache_read,
                cost_cache_write=payload.cost_cache_write,
                enabled=payload.enabled,
            )
        }

    @router.delete("/models/{model_id}")
    def delete_model(
        model_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        model_service.delete(model_id)
        return {"ok": True, "model_id": model_id}

    @router.post("/sync/openrouter-free")
    def sync_openrouter_free(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return model_service.sync_openrouter_free()

    @router.get("/gateway/accounts")
    def list_gateway_accounts(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"accounts": gateway_account_service.list()}

    @router.get("/gateway/models")
    def list_gateway_models(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"models": gateway_alias_service.list_models()}

    @router.post("/gateway/accounts")
    def create_gateway_account(
        payload: GatewayAccountCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "account": gateway_account_service.create(
                name=payload.name,
                base_url=payload.base_url,
                auth_type=payload.auth_type,
                api_key=payload.api_key,
                protocol=payload.protocol,
                notes=payload.notes,
            )
        }

    @router.post("/gateway/accounts/{account_id}/test")
    def test_gateway_account(
        account_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return gateway_account_service.test_connection(account_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    @router.post("/gateway/accounts/{account_id}/sync-models")
    def sync_gateway_account_models(
        account_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return gateway_account_service.sync_models(account_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    @router.get("/gateway/aliases")
    def list_gateway_aliases(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"aliases": gateway_alias_service.list_aliases()}

    @router.post("/gateway/aliases")
    def create_gateway_alias(
        payload: GatewayAliasCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "alias": gateway_alias_service.create_alias(
                alias_key=payload.alias_key,
                display_name=payload.display_name,
                alias_type=payload.alias_type,
                visibility=payload.visibility,
                notes=payload.notes,
            )
        }

    @router.patch("/gateway/aliases/{alias_id}")
    def update_gateway_alias(
        alias_id: int,
        payload: GatewayAliasUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return {
                "alias": gateway_alias_service.update_alias(
                    alias_id,
                    display_name=payload.display_name,
                    enabled=payload.enabled,
                    visibility=payload.visibility,
                    notes=payload.notes,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.get("/gateway/aliases/{alias_id}/targets")
    def list_gateway_alias_targets(
        alias_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return {"targets": gateway_alias_service.list_targets(alias_id)}
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.put("/gateway/aliases/{alias_id}/targets")
    def replace_gateway_alias_targets(
        alias_id: int,
        payload: GatewayAliasTargetsUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return {
                "targets": gateway_alias_service.replace_targets(
                    alias_id,
                    targets=[item.model_dump() for item in payload.targets],
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.get("/gateway/client-keys")
    def list_gateway_client_keys(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"client_keys": gateway_client_key_service.list()}

    @router.post("/gateway/client-keys")
    def create_gateway_client_key(
        payload: GatewayClientKeyCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "client_key": gateway_client_key_service.create(
                name=payload.name,
                api_key=payload.api_key,
                notes=payload.notes,
            )
        }

    @router.patch("/gateway/client-keys/{client_key_id}")
    def update_gateway_client_key(
        client_key_id: int,
        payload: GatewayClientKeyUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return {
                "client_key": gateway_client_key_service.update(
                    client_key_id,
                    enabled=payload.enabled,
                    notes=payload.notes,
                )
            }
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.get("/media/providers")
    def list_media_providers(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"providers": media_provider_service.list()}

    @router.post("/media/providers")
    def create_media_provider(
        payload: MediaProviderCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "provider": media_provider_service.create(
                name=payload.name,
                base_url=payload.base_url,
                auth_type=payload.auth_type,
                api_key=payload.api_key,
                notes=payload.notes,
            )
        }

    @router.get("/media/templates")
    def list_media_templates(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"templates": media_template_service.list()}

    @router.post("/media/templates")
    def create_media_template(
        payload: MediaTemplateCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return {
                "template": media_template_service.create(
                    provider_id=payload.provider_id,
                    model_key=payload.model_key,
                    name=payload.name,
                    capability=payload.capability,
                    template_type=payload.template_type,
                    upstream_model=payload.upstream_model,
                    ui_group=payload.ui_group,
                    ui_label=payload.ui_label,
                    ui_description=payload.ui_description,
                    ui_badge=payload.ui_badge,
                    ui_order=payload.ui_order,
                    input_schema_json=payload.input_schema_json,
                    request_template_json=payload.request_template_json,
                    response_mapping_json=payload.response_mapping_json,
                    defaults_json=payload.defaults_json,
                    enabled=payload.enabled,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/media/templates/validate")
    def validate_media_template(
        payload: MediaTemplateCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return media_template_service.validate_payload(payload.model_dump())

    @router.get("/media/catalog")
    def get_media_catalog(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"catalog": media_catalog_service.export()}

    @router.get("/universal/templates")
    def list_universal_templates(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"templates": universal_template_service.list()}

    @router.post("/universal/templates")
    def create_universal_template(
        payload: UniversalTemplateCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "template": universal_template_service.create(
                name=payload.name,
                base_url=payload.base_url,
                auth_type=payload.auth_type,
                api_key=payload.api_key,
                protocol=payload.protocol,
                notes=payload.notes,
                models=[item.model_dump() for item in payload.models],
            )
        }

    @router.post("/universal/templates/{template_id}/import/openclaw")
    def import_universal_template_to_openclaw(
        template_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return universal_template_service.import_to_openclaw(template_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/universal/templates/{template_id}/import/gateway")
    def import_universal_template_to_gateway(
        template_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return universal_template_service.import_to_gateway(template_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.post("/universal/templates/{template_id}/import/media")
    def import_universal_template_to_media(
        template_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        try:
            return universal_template_service.import_to_media(template_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @router.get("/devices")
    def list_devices(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"devices": device_service.list()}

    @router.post("/devices")
    def create_device(
        payload: DeviceCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "device": device_service.create(
                name=payload.name,
                device_type=payload.device_type,
                hostname=payload.hostname,
                platform=payload.platform,
                active=payload.active,
            )
        }

    @router.delete("/devices/{device_id}")
    def delete_device(device_id: int, x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        device_service.delete(device_id)
        return {"ok": True, "device_id": device_id}

    @router.post("/devices/{device_id}/pairing-token")
    def create_pairing_token(
        device_id: int,
        payload: PairingTokenCreate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return pairing_service.issue_pairing_token(
            device_id=device_id,
            expires_in_seconds=payload.expires_in_seconds,
        )

    @router.put("/devices/{device_id}/models")
    def assign_device_models(
        device_id: int,
        payload: DeviceModelBindingUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "device": device_service.assign_models(
                device_id=device_id,
                model_ids=payload.model_ids,
            )
        }

    @router.put("/devices/{device_id}/preserve-config")
    def update_device_preserve_config(
        device_id: int,
        payload: DevicePreserveConfigUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        return {
            "device": device_service.update_preserve_config(
                device_id=device_id,
                preserve_providers=payload.preserve_providers,
                preserve_models=payload.preserve_models,
            )
        }

    @router.get("/devices/{device_id}/config-preview")
    def get_device_config_preview(
        device_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> dict:
        require_admin(x_admin_token)
        device = device_service.get(device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found",
            )
        return compiler_service.compile_device_config(device_id)

    return router
