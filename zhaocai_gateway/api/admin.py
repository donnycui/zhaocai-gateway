from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import ModelService, ProviderService


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


def create_admin_router(store: SQLiteStore) -> APIRouter:
    provider_service = ProviderService(store)
    model_service = ModelService(store)
    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.get("/providers")
    def list_providers() -> dict:
        return {"providers": provider_service.list()}

    @router.post("/providers")
    def create_provider(payload: ProviderCreate) -> dict:
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
    def validate_provider(payload: ProviderValidate) -> dict:
        return provider_service.validate(
            base_url=payload.base_url,
            auth_scheme=payload.auth_scheme,
        )

    @router.get("/models")
    def list_models() -> dict:
        return {"models": model_service.list()}

    @router.post("/models")
    def create_model(payload: ModelCreate) -> dict:
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

    return router
