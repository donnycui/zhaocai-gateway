from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import GatewayAliasService, GatewayClientKeyService


def create_runtime_router(store: SQLiteStore) -> APIRouter:
    gateway_alias_service = GatewayAliasService(store)
    gateway_client_key_service = GatewayClientKeyService(store)
    router = APIRouter(tags=["runtime"])

    @router.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        authenticate_runtime_request(request, gateway_client_key_service)
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be a JSON object")

        alias_key = str(payload.get("model", "")).strip()
        if not alias_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model is required")

        try:
            response_status, response_payload = gateway_alias_service.invoke_chat_completions(alias_key, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        return JSONResponse(content=_ensure_json_object(response_payload), status_code=response_status)

    @router.post("/v1/responses")
    async def responses(request: Request) -> JSONResponse:
        authenticate_runtime_request(request, gateway_client_key_service)
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be a JSON object")

        alias_key = str(payload.get("model", "")).strip()
        if not alias_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model is required")

        try:
            response_status, response_payload = gateway_alias_service.invoke_responses(alias_key, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        return JSONResponse(content=_ensure_json_object(response_payload), status_code=response_status)

    return router


def authenticate_runtime_request(request: Request, client_key_service: GatewayClientKeyService) -> None:
    if not client_key_service.has_enabled_keys():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gateway client access is not configured",
        )

    raw_api_key = _extract_runtime_api_key(request)
    if not raw_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing gateway client key",
        )

    authenticated = client_key_service.authenticate(raw_api_key)
    if authenticated is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid gateway client key",
        )


def _extract_runtime_api_key(request: Request) -> str:
    x_api_key = request.headers.get("x-api-key", "").strip()
    if x_api_key:
        return x_api_key

    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _ensure_json_object(payload: dict[str, Any]) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {"data": payload}
