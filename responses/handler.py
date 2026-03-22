"""
Responses API handler.

Converts OpenAI Responses API format to/from chat completions,
reusing the existing GatewayServer routing and retry logic.

Scope (v1):
- Text input only (string or message array)
- instructions mapped to system message
- Non-streaming fully supported
- Streaming supported via synthetic SSE (full upstream call, then SSE emit)
- No tool use, no multimodal, no file_search / code_interpreter
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


class ResponsesRequest(BaseModel):
    model: str
    input: Union[str, List[dict]] = Field(...)
    instructions: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_output_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None


def _convert_input_to_messages(request: ResponsesRequest) -> List[Dict[str, str]]:
    """Convert Responses API ``input`` + ``instructions`` to chat messages."""
    messages: List[Dict[str, str]] = []

    # instructions -> system message
    if request.instructions:
        messages.append({"role": "system", "content": request.instructions})

    if isinstance(request.input, str):
        messages.append({"role": "user", "content": request.input})
    elif isinstance(request.input, list):
        for item in request.input:
            role = item.get("role", "user")
            content = item.get("content", "")
            # content can itself be a list of typed blocks
            if isinstance(content, list):
                text_parts: List[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") in ("input_text", "text"):
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block.get("text"), str):
                            text_parts.append(block["text"])
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts) if text_parts else ""
            messages.append({"role": role, "content": str(content)})

    return messages


def _convert_to_responses_format(
    chat_result: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    """Convert a chat completion result dict into the Responses API envelope."""
    assistant_text = ""
    try:
        assistant_text = chat_result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        pass

    response_id = f"resp_{uuid.uuid4().hex[:24]}"
    created_at = int(time.time())

    usage_in = chat_result.get("usage")
    usage_out: Dict[str, Any] = {}
    if usage_in:
        usage_out = {
            "input_tokens": usage_in.get("prompt_tokens", 0),
            "output_tokens": usage_in.get("completion_tokens", 0),
            "total_tokens": usage_in.get("total_tokens", 0),
        }

    return {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "model": model,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": assistant_text}],
            }
        ],
        "usage": usage_out,
    }


async def handle_responses(
    request: ResponsesRequest,
    gateway_server: Any,
    client_key: str,
) -> Dict[str, Any]:
    """Handle a non-streaming Responses API request."""
    # Delay import to avoid circular dependency at module load time.
    from gateway import ChatCompletionRequest

    messages = _convert_input_to_messages(request)
    chat_request = ChatCompletionRequest(
        model=request.model,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        temperature=request.temperature,
        max_tokens=request.max_output_tokens,
        stream=False,
        top_p=request.top_p,
    )
    chat_result = await gateway_server.chat_completion(chat_request, client_key=client_key)
    return _convert_to_responses_format(chat_result, model=request.model)


async def handle_responses_stream(
    request: ResponsesRequest,
    gateway_server: Any,
    client_key: str,
) -> StreamingResponse:
    """Handle a streaming Responses API request.

    Synthetic SSE mode: performs a full non-stream upstream call via the
    existing routing/retry logic, then emits the result as Responses-style
    SSE events.
    """
    from gateway import ChatCompletionRequest

    messages = _convert_input_to_messages(request)
    chat_request = ChatCompletionRequest(
        model=request.model,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        temperature=request.temperature,
        max_tokens=request.max_output_tokens,
        stream=False,
        top_p=request.top_p,
    )
    chat_result = await gateway_server.chat_completion(chat_request, client_key=client_key)
    response_data = _convert_to_responses_format(chat_result, model=request.model)

    assistant_text = ""
    try:
        assistant_text = response_data["output"][0]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        pass

    async def sse_generator():
        # 1. response.created
        created_event = {
            "id": response_data["id"],
            "object": "response",
            "created_at": response_data["created_at"],
            "model": response_data["model"],
            "output": [],
            "usage": None,
        }
        yield f"event: response.created\ndata: {json.dumps(created_event, ensure_ascii=False)}\n\n"

        # 2. response.output_text.delta
        if assistant_text:
            delta_event = {
                "type": "response.output_text.delta",
                "delta": assistant_text,
            }
            yield f"event: response.output_text.delta\ndata: {json.dumps(delta_event, ensure_ascii=False)}\n\n"

        # 3. response.completed
        yield f"event: response.completed\ndata: {json.dumps(response_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
