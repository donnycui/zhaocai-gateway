from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


@dataclass
class ProviderAdapter:
    provider_type: str

    def chat_endpoint(self, base_url: str) -> str:
        raise NotImplementedError

    def health_endpoint(self, base_url: str) -> str:
        raise NotImplementedError

    def prepare_chat_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return payload

    def parse_chat_response(self, result: Dict[str, Any], model: str) -> Dict[str, Any]:
        return result

    def build_headers(
        self,
        api_key: str,
        auth_scheme: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            if auth_scheme.lower() == "bearer":
                headers["Authorization"] = f"Bearer {api_key}"
            elif auth_scheme.lower() == "x-api-key":
                headers["x-api-key"] = api_key
            else:
                headers["Authorization"] = f"{auth_scheme} {api_key}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def convert_stream_line_to_openai_chunk(
        self,
        line: str,
        model: str,
        created: int,
    ) -> Optional[str]:
        del line, model, created
        return None


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(provider_type="openai")

    def chat_endpoint(self, base_url: str) -> str:
        return f"{_normalize_base_url(base_url)}/chat/completions"

    def health_endpoint(self, base_url: str) -> str:
        return f"{_normalize_base_url(base_url)}/models"


class AnthropicAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(provider_type="anthropic")

    def chat_endpoint(self, base_url: str) -> str:
        return f"{_normalize_base_url(base_url)}/v1/messages"

    def health_endpoint(self, base_url: str) -> str:
        return f"{_normalize_base_url(base_url)}/v1/models"

    def build_headers(
        self,
        api_key: str,
        auth_scheme: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        # Anthropic should use x-api-key by default even if config omitted.
        if api_key:
            if auth_scheme.lower() == "x-api-key":
                headers["x-api-key"] = api_key
            elif auth_scheme.lower() == "bearer":
                headers["x-api-key"] = api_key
            else:
                headers["Authorization"] = f"{auth_scheme} {api_key}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def prepare_chat_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        messages = payload.get("messages", [])
        system_msg = None
        clean_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg.get("content")
            else:
                clean_messages.append(msg)

        anthropic_payload: Dict[str, Any] = {
            "model": payload.get("model"),
            "messages": clean_messages,
            "max_tokens": payload.get("max_tokens") or 4096,
        }
        if system_msg:
            anthropic_payload["system"] = system_msg
        if payload.get("temperature") is not None:
            anthropic_payload["temperature"] = payload.get("temperature")
        if payload.get("top_p") is not None:
            anthropic_payload["top_p"] = payload.get("top_p")
        if payload.get("stream"):
            anthropic_payload["stream"] = True
        return anthropic_payload

    def parse_chat_response(self, result: Dict[str, Any], model: str) -> Dict[str, Any]:
        text_content = ""
        content = result.get("content", [])
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                text_content = first.get("text", "")

        return {
            "id": result.get("id", f"chatcmpl-{int(time.time())}"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": text_content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": result.get("usage", {}),
        }

    def convert_stream_line_to_openai_chunk(
        self,
        line: str,
        model: str,
        created: int,
    ) -> Optional[str]:
        if not line.startswith("data: "):
            return None
        data = line[6:].strip()
        if not data:
            return None
        if data == "[DONE]":
            return "data: [DONE]\n\n"

        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return None

        event_type = payload.get("type")
        if event_type == "content_block_delta":
            text = payload.get("delta", {}).get("text", "")
            if not text:
                return None
            chunk = {
                "id": payload.get("message", {}).get("id", f"chatcmpl-{created}"),
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": text},
                        "finish_reason": None,
                    }
                ],
            }
            return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        if event_type == "message_stop":
            stop_chunk = {
                "id": f"chatcmpl-{created}",
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            return (
                f"data: {json.dumps(stop_chunk, ensure_ascii=False)}\n\n"
                "data: [DONE]\n\n"
            )
        return None


def detect_provider_type(provider_name: str, base_url: str, configured_type: Optional[str]) -> str:
    if configured_type:
        return configured_type.lower()
    normalized = f"{provider_name} {base_url}".lower()
    if "anthropic" in normalized:
        return "anthropic"
    return "openai"


def get_provider_adapter(provider_type: str) -> ProviderAdapter:
    normalized = (provider_type or "openai").lower()
    if normalized == "anthropic":
        return AnthropicAdapter()
    return OpenAICompatibleAdapter()

