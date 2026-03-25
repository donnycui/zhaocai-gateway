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


class ModelCreate(BaseModel):
    provider_id: int
    upstream_model: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    context_window: int | None = None
    max_tokens: int | None = None
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

    @router.get("/providers")
    def list_providers(x_admin_token: str | None = Header(default=None)) -> dict:
        require_admin(x_admin_token)
        return {"providers": provider_service.list()}

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
                context_window=payload.context_window,
                max_tokens=payload.max_tokens,
                enabled=payload.enabled,
            )
        }

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
