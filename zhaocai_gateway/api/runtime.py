from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import GatewayAliasService


def create_runtime_router(store: SQLiteStore) -> APIRouter:
    gateway_alias_service = GatewayAliasService(store)
    router = APIRouter(tags=["runtime"])

    @router.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
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


def _ensure_json_object(payload: dict[str, Any]) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {"data": payload}
