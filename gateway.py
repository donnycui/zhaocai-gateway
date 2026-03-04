#!/usr/bin/env python3
"""
Zhaocai Gateway

Unified AI gateway + control plane for multi-provider routing and
multi-node OpenClaw configuration distribution.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import random
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from control_plane.router import create_control_plane_routers
from control_plane.store import create_store_from_env
from providers.adapters import detect_provider_type, get_provider_adapter


logging.basicConfig(
    level=getattr(logging, os.getenv("ZHAOCAI_LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    api_key: str
    models: List[str]
    provider_type: str = "openai"
    auth_scheme: str = "bearer"
    weight: float = 1.0
    priority: int = 100
    timeout: int = 60
    enabled: bool = True
    extra_headers: Dict[str, str] = Field(default_factory=dict)


@dataclass
class ProviderStatus:
    name: str
    healthy: bool = True
    last_check: float = field(default_factory=time.time)
    request_count: int = 0
    error_count: int = 0
    latency_ms: float = 0.0


@dataclass
class BucketState:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, enabled: bool, requests_per_minute: int, burst: int) -> None:
        self.enabled = enabled
        self.requests_per_minute = max(1, requests_per_minute)
        self.burst = max(1, burst)
        self.rate_per_second = self.requests_per_minute / 60.0
        self._lock = threading.Lock()
        self._buckets: Dict[str, BucketState] = {}

    def allow(self, key: str) -> bool:
        if not self.enabled:
            return True
        now = time.time()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = BucketState(tokens=float(self.burst), last_refill=now)
                self._buckets[key] = bucket

            elapsed = max(0.0, now - bucket.last_refill)
            bucket.tokens = min(float(self.burst), bucket.tokens + elapsed * self.rate_per_second)
            bucket.last_refill = now

            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True


class ProviderCallError(Exception):
    def __init__(self, provider_name: str, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.provider_name = provider_name
        self.status_code = status_code
        self.detail = detail


class ProviderManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.providers: Dict[str, ProviderConfig] = {}
        self.status: Dict[str, ProviderStatus] = {}
        self.round_robin_index: Dict[str, int] = {}
        self.config = self._load_config(config_path)
        self._init_providers()

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            logger.warning("Config file not found: %s, using defaults", path)
            return self._default_config()
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        return self._expand_env_vars(loaded)

    def _default_config(self) -> Dict[str, Any]:
        return {
            "gateway": {"host": "0.0.0.0", "port": 8000, "workers": 1},
            "providers": {},
            "routing": {
                "strategy": "round_robin",
                "fallback_enabled": True,
                "max_retries": 3,
            },
            "rate_limit": {"enabled": False, "requests_per_minute": 60, "burst": 10},
        }

    def _expand_env_vars(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            default = ""
            if ":-" in env_var:
                env_var, default = env_var.split(":-", 1)
            return os.getenv(env_var, default)
        return obj

    def _init_providers(self) -> None:
        providers_config = self.config.get("providers", {})
        for name, cfg in providers_config.items():
            if not cfg.get("enabled", True):
                logger.info("Provider %s disabled in config", name)
                continue
            provider_type = detect_provider_type(name, cfg.get("base_url", ""), cfg.get("provider_type"))
            provider = ProviderConfig(
                name=name,
                base_url=cfg["base_url"],
                api_key=cfg.get("api_key", ""),
                models=cfg.get("models", []),
                provider_type=provider_type,
                auth_scheme=cfg.get("auth_scheme", "bearer"),
                weight=float(cfg.get("weight", 1.0)),
                priority=int(cfg.get("priority", 100)),
                timeout=int(cfg.get("timeout", 60)),
                enabled=bool(cfg.get("enabled", True)),
                extra_headers=cfg.get("extra_headers", {}),
            )
            self.providers[name] = provider
            self.status[name] = ProviderStatus(name=name)
            logger.info(
                "Loaded provider=%s type=%s models=%s",
                name,
                provider.provider_type,
                provider.models,
            )

    def get_all_models(self) -> List[Dict[str, str]]:
        result: List[Dict[str, str]] = []
        for provider_name, provider in self.providers.items():
            for model in provider.models:
                result.append(
                    {
                        "id": model,
                        "object": "model",
                        "owned_by": provider_name,
                    }
                )
        return result

    def get_model_candidates(self, requested_model: str) -> List[Tuple[ProviderConfig, str]]:
        if "/" in requested_model:
            provider_name, actual_model = requested_model.split("/", 1)
            provider = self.providers.get(provider_name)
            if provider and self.status[provider_name].healthy:
                if not provider.models or actual_model in provider.models:
                    return [(provider, actual_model)]
            return []

        candidates: List[Tuple[ProviderConfig, str]] = []
        for name, provider in self.providers.items():
            if requested_model in provider.models and self.status[name].healthy:
                candidates.append((provider, requested_model))
        return candidates

    def ordered_candidates(
        self,
        requested_model: str,
        candidates: List[Tuple[ProviderConfig, str]],
    ) -> List[Tuple[ProviderConfig, str]]:
        strategy = str(self.config.get("routing", {}).get("strategy", "round_robin")).lower()
        if not candidates:
            return []

        if strategy == "priority":
            return sorted(candidates, key=lambda item: (item[0].priority, item[0].name))

        if strategy == "weighted":
            remaining = list(candidates)
            ordered: List[Tuple[ProviderConfig, str]] = []
            while remaining:
                weights = [max(item[0].weight, 0.01) for item in remaining]
                index = random.choices(range(len(remaining)), weights=weights, k=1)[0]
                ordered.append(remaining.pop(index))
            return ordered

        # round_robin default
        start = self.round_robin_index.get(requested_model, 0) % len(candidates)
        ordered = candidates[start:] + candidates[:start]
        self.round_robin_index[requested_model] = (start + 1) % len(candidates)
        return ordered

    def mark_provider_result(self, provider_name: str, healthy: bool, latency_ms: float) -> None:
        status_obj = self.status.get(provider_name)
        if not status_obj:
            return
        status_obj.healthy = healthy
        status_obj.last_check = time.time()
        status_obj.latency_ms = latency_ms
        if not healthy:
            status_obj.error_count += 1

    async def health_check(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        async with httpx.AsyncClient() as client:
            for name, provider in self.providers.items():
                adapter = get_provider_adapter(provider.provider_type)
                endpoint = adapter.health_endpoint(provider.base_url)
                headers = adapter.build_headers(provider.api_key, provider.auth_scheme, provider.extra_headers)
                started = time.time()
                try:
                    resp = await client.get(endpoint, headers=headers, timeout=min(provider.timeout, 20))
                    latency = (time.time() - started) * 1000
                    healthy = 200 <= resp.status_code < 300
                    self.mark_provider_result(name, healthy=healthy, latency_ms=latency)
                    results[name] = {
                        "healthy": healthy,
                        "latency_ms": latency,
                        "status_code": resp.status_code,
                    }
                except Exception as exc:  # noqa: BLE001
                    latency = (time.time() - started) * 1000
                    self.mark_provider_result(name, healthy=False, latency_ms=latency)
                    results[name] = {"healthy": False, "error": str(exc)}
        return results


class GatewayServer:
    def __init__(self):
        config_path = os.getenv("ZHAOCAI_CONFIG", "config.yaml")
        self.provider_manager = ProviderManager(config_path=config_path)
        routing_cfg = self.provider_manager.config.get("routing", {})
        self.fallback_enabled = bool(routing_cfg.get("fallback_enabled", True))
        self.max_retries = max(0, int(routing_cfg.get("max_retries", 3)))
        rate_limit_cfg = self.provider_manager.config.get("rate_limit", {})
        self.rate_limiter = RateLimiter(
            enabled=bool(rate_limit_cfg.get("enabled", False)),
            requests_per_minute=int(rate_limit_cfg.get("requests_per_minute", 60)),
            burst=int(rate_limit_cfg.get("burst", 10)),
        )

    def _get_attempt_plan(self, model: str) -> List[Tuple[ProviderConfig, str]]:
        candidates = self.provider_manager.get_model_candidates(model)
        ordered = self.provider_manager.ordered_candidates(model, candidates)
        if not ordered:
            return []
        if not self.fallback_enabled:
            return ordered[:1]
        max_attempts = min(len(ordered), self.max_retries + 1)
        return ordered[:max_attempts]

    async def _call_provider(
        self,
        provider: ProviderConfig,
        target_model: str,
        request: ChatCompletionRequest,
    ) -> Dict[str, Any]:
        adapter = get_provider_adapter(provider.provider_type)
        payload = request.model_dump(exclude_none=True)
        payload["model"] = target_model
        payload["stream"] = False
        prepared_payload = adapter.prepare_chat_payload(payload)
        endpoint = adapter.chat_endpoint(provider.base_url)
        headers = adapter.build_headers(provider.api_key, provider.auth_scheme, provider.extra_headers)

        started = time.time()
        async with httpx.AsyncClient(timeout=provider.timeout) as client:
            try:
                resp = await client.post(endpoint, json=prepared_payload, headers=headers)
            except httpx.TimeoutException as exc:
                latency = (time.time() - started) * 1000
                self.provider_manager.mark_provider_result(provider.name, healthy=False, latency_ms=latency)
                raise ProviderCallError(provider.name, status.HTTP_504_GATEWAY_TIMEOUT, "Upstream timeout") from exc
            except Exception as exc:  # noqa: BLE001
                latency = (time.time() - started) * 1000
                self.provider_manager.mark_provider_result(provider.name, healthy=False, latency_ms=latency)
                raise ProviderCallError(provider.name, status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

        latency = (time.time() - started) * 1000
        self.provider_manager.mark_provider_result(provider.name, healthy=True, latency_ms=latency)
        self.provider_manager.status[provider.name].request_count += 1

        if not (200 <= resp.status_code < 300):
            self.provider_manager.mark_provider_result(provider.name, healthy=False, latency_ms=latency)
            body = resp.text[:2000]
            raise ProviderCallError(provider.name, resp.status_code, body)

        try:
            parsed = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderCallError(provider.name, status.HTTP_502_BAD_GATEWAY, "Invalid upstream JSON") from exc
        return adapter.parse_chat_response(parsed, model=request.model)

    async def chat_completion(self, request: ChatCompletionRequest, client_key: str) -> Dict[str, Any]:
        if not self.rate_limiter.allow(client_key):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        attempt_plan = self._get_attempt_plan(request.model)
        if not attempt_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {request.model} is unavailable or all providers are unhealthy",
            )

        errors: List[Dict[str, Any]] = []
        for provider, target_model in attempt_plan:
            try:
                return await self._call_provider(provider, target_model, request)
            except ProviderCallError as exc:
                errors.append(
                    {
                        "provider": exc.provider_name,
                        "status_code": exc.status_code,
                        "detail": exc.detail,
                    }
                )
                logger.warning(
                    "Provider call failed provider=%s model=%s status=%s detail=%s",
                    exc.provider_name,
                    request.model,
                    exc.status_code,
                    exc.detail,
                )
                continue

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "All provider attempts failed", "attempts": errors},
        )

    async def stream_chat_completion(
        self,
        request: ChatCompletionRequest,
        client_key: str,
    ) -> StreamingResponse:
        # Compatibility stream mode:
        # execute a non-stream upstream call (with fallback/strategy/retry),
        # then re-emit as OpenAI SSE chunks.
        non_stream_request = copy.deepcopy(request)
        non_stream_request.stream = False
        response_payload = await self.chat_completion(non_stream_request, client_key=client_key)
        created = int(time.time())
        model = request.model

        assistant_text = ""
        try:
            assistant_text = response_payload["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001
            assistant_text = ""

        async def sse_generator():
            chunk_id = response_payload.get("id", f"chatcmpl-{created}")
            role_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n"

            if assistant_text:
                content_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": assistant_text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(content_chunk, ensure_ascii=False)}\n\n"

            stop_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(stop_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse_generator(), media_type="text/event-stream")


gateway = GatewayServer()
control_store = create_store_from_env()
admin_token = os.getenv("ZHAOCAI_ADMIN_TOKEN", "change-me-admin-token")
control_api_router, control_panel_router = create_control_plane_routers(
    store=control_store,
    admin_token=admin_token,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    logger.info("Starting Zhaocai Gateway...")
    health = await gateway.provider_manager.health_check()
    logger.info("Initial provider health check completed: %s", health)
    yield
    logger.info("Shutting down Zhaocai Gateway...")


app = FastAPI(
    title="Zhaocai Gateway",
    description="AI Provider Gateway + OpenClaw Control Plane",
    version="2.0.0",
    lifespan=lifespan,
)

def _load_cors_origins() -> list[str]:
    origins_str = os.getenv("ZHAOCAI_CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    # Default: same-origin only for security
    port = os.getenv("ZHAOCAI_PORT", "8000")
    return [f"http://localhost:{port}", f"http://127.0.0.1:{port}"]


_cors_origins = _load_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(control_api_router)
app.include_router(control_panel_router)


@app.get("/")
async def root():
    return {
        "name": "Zhaocai Gateway",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "control_panel": "/control",
    }


@app.get("/health")
async def health():
    providers = await gateway.provider_manager.health_check()
    return {
        "status": "healthy",
        "providers": providers,
        "timestamp": time.time(),
    }


@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": gateway.provider_manager.get_all_models()}


@app.get("/v1/providers")
async def list_providers():
    providers = []
    for name, cfg in gateway.provider_manager.providers.items():
        st = gateway.provider_manager.status[name]
        providers.append(
            {
                "name": cfg.name,
                "provider_type": cfg.provider_type,
                "base_url": cfg.base_url,
                "models": cfg.models,
                "weight": cfg.weight,
                "priority": cfg.priority,
                "enabled": cfg.enabled,
                "status": {
                    "healthy": st.healthy,
                    "request_count": st.request_count,
                    "error_count": st.error_count,
                    "latency_ms": st.latency_ms,
                },
            }
        )
    return {"providers": providers}


@app.post("/v1/chat/completions")
async def chat_completions(http_request: Request, payload: ChatCompletionRequest):
    client_ip = http_request.client.host if http_request.client else "unknown"
    if payload.stream:
        return await gateway.stream_chat_completion(payload, client_key=client_ip)
    return await gateway.chat_completion(payload, client_key=client_ip)


@app.get("/metrics")
async def metrics():
    return {
        "requests_total": sum(v.request_count for v in gateway.provider_manager.status.values()),
        "errors_total": sum(v.error_count for v in gateway.provider_manager.status.values()),
        "providers": {
            name: {
                "healthy": st.healthy,
                "requests": st.request_count,
                "errors": st.error_count,
                "latency_ms": st.latency_ms,
            }
            for name, st in gateway.provider_manager.status.items()
        },
    }


def main():
    import uvicorn

    config = gateway.provider_manager.config
    host = os.getenv("ZHAOCAI_HOST", config.get("gateway", {}).get("host", "0.0.0.0"))
    port = int(os.getenv("ZHAOCAI_PORT", config.get("gateway", {}).get("port", 8000)))
    workers = int(config.get("gateway", {}).get("workers", 1))

    logger.info("Starting on %s:%s", host, port)
    logger.info("Workers=%s", workers)
    logger.info("Providers=%s", list(gateway.provider_manager.providers.keys()))
    logger.info("Control DB=%s", os.getenv("ZHAOCAI_CONTROL_DB", "sqlite:///./data/control_plane.db"))

    uvicorn.run(
        "gateway:app",
        host=host,
        port=port,
        workers=workers if workers > 1 else 1,
        reload=False,
    )


if __name__ == "__main__":
    main()
