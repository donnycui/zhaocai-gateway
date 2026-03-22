from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx
from fastapi import APIRouter, Header, HTTPException, Response, status
from fastapi.responses import HTMLResponse, JSONResponse

from control_plane.compiler import compile_openclaw_config
from control_plane.models import (
    ModelCreate,
    ModelUpdate,
    NodeCreate,
    NodeUpdate,
    ProfileBindingUpdate,
    ProfileCreate,
    ProviderCreate,
    ProviderCreateWithModels,
    ProviderUpdate,
    ProviderValidate,
)
from control_plane.store import SQLiteControlPlaneStore
from providers.adapters import get_provider_adapter


CHAT_INCLUDE_KEYWORDS = (
    "gpt",
    "gpt-5",
    "claude",
    "qwen",
    "deepseek",
    "glm",
    "kimi",
    "coder",
    "instruct",
    "chat",
    "sonnet",
    "opus",
    "haiku",
    "r1",
    "v3",
)

CHAT_EXCLUDE_KEYWORDS = (
    "embedding",
    "rerank",
    "moderation",
    "whisper",
    "tts",
    "asr",
    "speech",
    "transcription",
)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix) :].strip()
    return ""


def _provider_validation_message(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "Connection succeeded"
    if status_code in {401, 403}:
        return "Authentication failed"
    if status_code == 404:
        return "Endpoint not found; base_url may be incorrect for this provider"
    if 400 <= status_code < 500:
        return "Provider rejected the request"
    if status_code >= 500:
        return "Upstream provider returned a server error"
    return "Connection test failed"


def _handle_data_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, sqlite3.IntegrityError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _extract_model_items(payload: Any) -> List[Any]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        models = payload.get("models")
        if isinstance(models, list):
            return models
        items = payload.get("items")
        if isinstance(items, list):
            return items
        return []
    if isinstance(payload, list):
        return payload
    return []


def _extract_int(item: Dict[str, Any], keys: List[str]) -> int | None:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except Exception:
            continue
    return None


def _normalize_input_modalities(item: Dict[str, Any], model_id: str) -> List[str]:
    raw = item.get("input")
    if isinstance(raw, list):
        vals = [str(v).lower() for v in raw if str(v).lower() in {"text", "image"}]
        return vals or ["text"]
    if isinstance(raw, str):
        vals = [v.strip().lower() for v in raw.split(",") if v.strip().lower() in {"text", "image"}]
        return vals or ["text"]
    lowered = model_id.lower()
    if "image" in lowered and "qwen-image" not in lowered:
        return ["image"]
    return ["text"]


def _infer_capabilities(model_id: str, item: Dict[str, Any]) -> List[str]:
    caps: List[str] = []
    raw = item.get("capabilities")
    if isinstance(raw, list):
        caps.extend(str(v) for v in raw)
    lowered = model_id.lower()
    if "reason" in lowered or lowered.endswith("r1"):
        caps.append("reasoning")
    if "coder" in lowered or "code" in lowered:
        caps.append("coding")
    if not caps:
        caps.append("chat")
    if "chat" not in caps:
        caps.insert(0, "chat")
    seen: List[str] = []
    for cap in caps:
        if cap not in seen:
            seen.append(cap)
    return seen


def _is_chat_selectable(model_id: str, provider_type: str) -> tuple[bool, str]:
    lowered = model_id.lower()
    if provider_type == "anthropic":
        return True, ""
    for keyword in CHAT_EXCLUDE_KEYWORDS:
        if keyword in lowered:
            return False, f"filtered: {keyword} model"
    if any(keyword in lowered for keyword in CHAT_INCLUDE_KEYWORDS):
        return True, ""
    return False, "filtered: not a chat-oriented model"


def _build_model_candidates(provider_type: str, payload: Any) -> List[Dict[str, Any]]:
    items = _extract_model_items(payload)
    result: List[Dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            model_id = item
            item_dict: Dict[str, Any] = {}
        elif isinstance(item, dict):
            model_id = str(item.get("id") or item.get("name") or "").strip()
            item_dict = item
        else:
            continue
        if not model_id:
            continue
        selectable, reason = _is_chat_selectable(model_id, provider_type)
        result.append(
            {
                "id": model_id,
                "name": str(item_dict.get("name") or model_id),
                "selectable": selectable,
                "reason": reason,
                "capabilities": _infer_capabilities(model_id, item_dict),
                "contextWindow": _extract_int(item_dict, ["contextWindow", "context_window", "contextLength", "context_length"]),
                "maxTokens": _extract_int(item_dict, ["maxTokens", "max_tokens", "maxOutputTokens", "max_output_tokens"]),
                "input": _normalize_input_modalities(item_dict, model_id),
            }
        )
    return result


_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenRouter free-model sync helpers
# ---------------------------------------------------------------------------

_KNOWN_VENDORS = {"google", "meta", "deepseek", "qwen", "microsoft", "mistral", "nvidia"}


def _score_free_model(model_id: str, item: Dict[str, Any]) -> float:
    """Compute a quality score for a free OpenRouter model.

    Considers context window size, vendor reputation, reasoning
    capability, and parameter count.
    """
    score = 0.0

    # --- context window ---
    ctx = 0
    try:
        ctx = int(item.get("context_length") or 0)
    except (ValueError, TypeError):
        pass
    if ctx >= 128_000:
        score += 30
    elif ctx >= 32_000:
        score += 20
    elif ctx >= 8_000:
        score += 10

    # --- vendor reputation (stability proxy) ---
    lowered = model_id.lower()
    for vendor in _KNOWN_VENDORS:
        if vendor in lowered:
            score += 20
            break

    # --- reasoning capability ---
    # OpenRouter IDs often end with ":free", so check for r1 as a segment
    base_id = lowered.split(":")[0]  # strip :free suffix
    if "reason" in lowered or base_id.endswith("r1") or "-r1-" in lowered:
        score += 15

    # --- model size (popularity/quality proxy) ---
    arch = item.get("architecture", {})
    if isinstance(arch, dict):
        params = arch.get("num_parameters")
        if params:
            try:
                p = float(params)
                if p >= 100e9:
                    score += 10
                elif p >= 30e9:
                    score += 5
            except (ValueError, TypeError):
                pass

    return score


def _classify_free_model(model_id: str, item: Dict[str, Any]) -> List[str]:
    """Return category tags for a free model (general, code, fast, ...)."""
    tags: List[str] = ["general"]
    lowered = model_id.lower()

    if "code" in lowered or "coder" in lowered:
        tags.append("code")
    base_id = lowered.split(":")[0]
    if "reason" in lowered or base_id.endswith("r1") or "-r1-" in lowered:
        tags.append("reasoning")

    ctx = 0
    try:
        ctx = int(item.get("context_length") or 0)
    except (ValueError, TypeError):
        pass

    params = None
    arch = item.get("architecture", {})
    if isinstance(arch, dict):
        try:
            params = float(arch.get("num_parameters") or 0)
        except (ValueError, TypeError):
            pass

    if (params and params < 15e9) or (ctx > 0 and ctx <= 32_000 and params is None):
        tags.append("fast")

    return tags


def _run_openrouter_free_sync(store: "SQLiteControlPlaneStore") -> Dict[str, Any]:
    """Fetch free models from OpenRouter and upsert stable aliases."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get("https://openrouter.ai/api/v1/models")
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch OpenRouter models: {exc}",
        ) from exc

    items = payload.get("data", [])
    if not isinstance(items, list):
        items = []

    # ---- filter free models ----
    free_models: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pricing = item.get("pricing", {})
        if not isinstance(pricing, dict):
            continue
        try:
            if float(pricing.get("prompt", "1")) == 0 and float(pricing.get("completion", "1")) == 0:
                free_models.append(item)
        except (ValueError, TypeError):
            continue

    if not free_models:
        return {"synced": 0, "message": "No free models found on OpenRouter"}

    # ---- ensure openrouter provider exists ----
    providers = store.list_providers(include_secrets=False)
    or_provider = next((p for p in providers if p["name"] == "openrouter"), None)
    if or_provider is None:
        or_provider = store.create_provider({
            "name": "openrouter",
            "provider_type": "openai",
            "base_url": "https://openrouter.ai/api/v1",
            "auth_scheme": "bearer",
            "api_key": "",
            "enabled": True,
        })
    provider_id = or_provider["id"]

    # ---- score & sort ----
    scored: List[tuple] = []
    for item in free_models:
        mid = str(item.get("id", "")).strip()
        if not mid:
            continue
        s = _score_free_model(mid, item)
        tags = _classify_free_model(mid, item)
        scored.append((s, mid, item, tags))
    scored.sort(key=lambda x: x[0], reverse=True)

    # ---- pick best model for each alias slot ----
    alias_map: Dict[str, str] = {}
    best_set = False
    code_set = False
    fast_set = False
    general_set = False

    for _s, mid, _item, tags in scored:
        if not best_set:
            alias_map["openrouter/free/best"] = mid
            best_set = True
        if "code" in tags and not code_set:
            alias_map["openrouter/free/code"] = mid
            code_set = True
        if "fast" in tags and not fast_set:
            alias_map["openrouter/free/fast"] = mid
            fast_set = True
        if "general" in tags and not general_set and mid != alias_map.get("openrouter/free/best"):
            alias_map["openrouter/free/general"] = mid
            general_set = True
        if len(alias_map) >= 4:
            break

    # fallbacks when a category wasn't found
    if "openrouter/free/general" not in alias_map and len(scored) > 1:
        alias_map["openrouter/free/general"] = scored[1][1]
    if "openrouter/free/code" not in alias_map and len(scored) > 2:
        alias_map["openrouter/free/code"] = scored[2][1]
    if "openrouter/free/fast" not in alias_map and len(scored) > 0:
        alias_map["openrouter/free/fast"] = scored[-1][1]

    # ---- upsert models ----
    item_by_id: Dict[str, Dict[str, Any]] = {
        str(it.get("id", "")).strip(): it for it in free_models if isinstance(it, dict)
    }

    created = 0
    updated = 0
    for alias, upstream_model in alias_map.items():
        item = item_by_id.get(upstream_model, {})
        ctx_window = None
        try:
            ctx_window = int(item.get("context_length") or 0) or None
        except (ValueError, TypeError):
            pass
        caps = _infer_capabilities(upstream_model, item)
        model_data: Dict[str, Any] = {
            "provider_id": provider_id,
            "upstream_model": upstream_model,
            "enabled": True,
            "capabilities": caps,
            "context_window": ctx_window,
            "input": ["text"],
        }
        existing = store.conn.execute(
            "SELECT id FROM models WHERE alias = ?", (alias,)
        ).fetchone()
        store.upsert_model_by_alias(alias, model_data)
        if existing:
            updated += 1
        else:
            created += 1

    _logger.info(
        "OpenRouter free sync: %d free models found, %d aliases created, %d updated",
        len(free_models), created, updated,
    )

    return {
        "synced": created + updated,
        "created": created,
        "updated": updated,
        "free_models_found": len(free_models),
        "aliases": alias_map,
    }


def create_control_plane_routers(
    store: SQLiteControlPlaneStore,
    admin_token: str,
) -> Tuple[APIRouter, APIRouter]:
    api_router = APIRouter(prefix="/control/v1", tags=["control-plane"])
    panel_router = APIRouter(tags=["control-panel"])

    def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
        if not admin_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ZHAOCAI_ADMIN_TOKEN is not configured",
            )
        if x_admin_token != admin_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")

    def require_node_or_admin(
        node_id: int,
        authorization: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> None:
        if admin_token and x_admin_token == admin_token:
            return
        pull_token = _extract_bearer_token(authorization)
        if not pull_token or not store.verify_node_token(node_id, pull_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid node token")

    @api_router.get("/providers")
    def list_providers(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"providers": store.list_providers(include_secrets=False)}

    @api_router.post("/providers")
    def create_provider(payload: ProviderCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            provider = store.create_provider(payload.model_dump())
            return {"provider": provider}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.post("/providers/validate")
    def validate_provider(
        payload: ProviderValidate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        adapter = get_provider_adapter(payload.provider_type)
        endpoint = adapter.health_endpoint(payload.base_url)
        headers = adapter.build_headers(payload.api_key, payload.auth_scheme, payload.extra_headers)
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(endpoint, headers=headers)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            response_payload = None
            try:
                response_payload = response.json()
            except Exception:
                response_payload = None
            return {
                "ok": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "endpoint": endpoint,
                "message": _provider_validation_message(response.status_code),
                "detail": response.text[:500] if response.status_code >= 400 else "",
                "models": _build_model_candidates(payload.provider_type, response_payload) if 200 <= response.status_code < 300 else [],
            }
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "ok": False,
                "status_code": 504,
                "latency_ms": latency_ms,
                "endpoint": endpoint,
                "message": "Connection timed out",
                "detail": "The provider endpoint did not respond within 30 seconds.",
                "models": [],
            }
        except httpx.RequestError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "ok": False,
                "status_code": 502,
                "latency_ms": latency_ms,
                "endpoint": endpoint,
                "message": "Provider endpoint is unreachable",
                "detail": str(exc),
                "models": [],
            }

    @api_router.post("/providers/create-with-models")
    def create_provider_with_models(
        payload: ProviderCreateWithModels,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            provider = store.create_provider(payload.provider.model_dump())
            created_models: List[Dict[str, Any]] = []
            for model in payload.models:
                model_payload = model.model_dump()
                model_payload["provider_id"] = provider["id"]
                created_models.append(store.create_model(model_payload))
            return {"provider": provider, "models": created_models}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.patch("/providers/{provider_id}")
    def patch_provider(
        provider_id: int,
        payload: ProviderUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            provider = store.update_provider(provider_id, payload.model_dump(exclude_none=True))
            return {"provider": provider}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/models")
    def list_models(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"models": store.list_models()}

    @api_router.post("/models")
    def create_model(payload: ModelCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            model = store.create_model(payload.model_dump())
            return {"model": model}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.patch("/models/{model_id}")
    def patch_model(
        model_id: int,
        payload: ModelUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            model = store.update_model(model_id, payload.model_dump(exclude_none=True))
            return {"model": model}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/profiles")
    def list_profiles(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"profiles": store.list_profiles()}

    @api_router.post("/profiles")
    def create_profile(payload: ProfileCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            profile = store.create_profile(payload.model_dump())
            return {"profile": profile}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.post("/profiles/{profile_id}/bindings")
    def set_profile_bindings(
        profile_id: int,
        payload: ProfileBindingUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            profile = store.set_profile_bindings(profile_id, payload.model_ids)
            return {"profile": profile}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/nodes")
    def list_nodes(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"nodes": store.list_nodes()}

    @api_router.post("/nodes")
    def create_node(payload: NodeCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            node = store.create_node(payload.model_dump())
            return {"node": node}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.patch("/nodes/{node_id}")
    def patch_node(
        node_id: int,
        payload: NodeUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            node = store.update_node(node_id, payload.model_dump(exclude_none=True))
            return {"node": node}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/nodes/{node_id}/openclaw-json")
    def get_node_openclaw_json(
        node_id: int,
        if_none_match: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> Response:
        require_node_or_admin(node_id=node_id, authorization=authorization, x_admin_token=x_admin_token)
        try:
            payload = compile_openclaw_config(store, node_id)
            version_row, _ = store.save_node_config_version(node_id, payload)
            etag = version_row["etag"]
            headers = {
                "ETag": etag,
                "X-Config-Version": str(version_row["version"]),
            }
            if if_none_match and if_none_match.strip() == etag:
                return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
            return JSONResponse(content=version_row["payload"], headers=headers)
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.post("/nodes/{node_id}/sync-token/rotate")
    def rotate_node_sync_token(
        node_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            pull_token = store.rotate_node_token(node_id)
            return {"node_id": node_id, "pull_token": pull_token}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/nodes/{node_id}/versions")
    def list_node_versions(
        node_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            store.get_node(node_id, include_token_hash=False)
            versions = store.list_node_versions(node_id)
            return {"node_id": node_id, "versions": versions}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.post("/sync/openrouter-free")
    def sync_openrouter_free(
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        """Pull free models from OpenRouter, score them, and upsert stable aliases."""
        require_admin(x_admin_token)
        return _run_openrouter_free_sync(store)

    @panel_router.get("/guide", response_class=HTMLResponse)
    def guide_panel() -> HTMLResponse:
        guide_path = Path(__file__).parent / "static" / "guide.html"
        if not guide_path.exists():
            raise HTTPException(status_code=404, detail="Guide panel UI is missing")
        return HTMLResponse(guide_path.read_text(encoding="utf-8"))

    @panel_router.get("/control", response_class=HTMLResponse)
    def control_panel() -> HTMLResponse:
        panel_path = Path(__file__).parent / "static" / "control_panel.html"
        if not panel_path.exists():
            raise HTTPException(status_code=404, detail="Control panel UI is missing")
        return HTMLResponse(panel_path.read_text(encoding="utf-8"))

    @panel_router.get("/health-ui", response_class=HTMLResponse)
    def health_panel() -> HTMLResponse:
        health_path = Path(__file__).parent / "static" / "health.html"
        if not health_path.exists():
            raise HTTPException(status_code=404, detail="Health panel UI is missing")
        return HTMLResponse(health_path.read_text(encoding="utf-8"))

    return api_router, panel_router
