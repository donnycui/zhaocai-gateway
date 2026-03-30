from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import (
    ConfigCompilerService,
    DeviceService,
    ModelService,
    PairingService,
    ProviderService,
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


def create_admin_router(store: SQLiteStore, *, admin_token: str) -> APIRouter:
    provider_service = ProviderService(store)
    model_service = ModelService(store)
    device_service = DeviceService(store)
    pairing_service = PairingService(store)
    compiler_service = ConfigCompilerService(store)
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
