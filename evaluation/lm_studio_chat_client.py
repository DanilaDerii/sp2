"""Direct LM Studio chat-completion calls for the model comparison harness.

SP2's runtime never calls LM Studio's chat-completions endpoint itself -
LM Studio's own chat UI owns answer generation, and SP2 only calls
/v1/embeddings for retrieval. This client exists solely for the eval
harness under evaluation/, which needs to compare candidate chat models
outside of LM Studio's UI.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.arguments import DEFAULT_HTTP_TIMEOUT, DEFAULT_LM_STUDIO_BASE_URL


class ChatCompletionError(RuntimeError):
    """Raised when an LM Studio chat-completion request fails."""


@dataclass(frozen=True)
class ChatCompletionResult:
    """One chat-completion response with timing and token metrics."""

    text: str
    latency_seconds: float
    prompt_tokens: int | None
    completion_tokens: int | None
    tokens_per_second: float | None
    raw: dict[str, Any]


def _post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            error_body = ""
        detail = f": {error_body}" if error_body else ""
        raise ChatCompletionError(
            f"LM Studio chat-completion request failed with HTTP {exc.code}{detail}"
        ) from exc
    except URLError as exc:
        raise ChatCompletionError(
            f"Could not reach LM Studio chat-completions API: {exc.reason}"
        ) from exc
    except OSError as exc:
        # Covers raw socket failures urllib doesn't wrap as URLError, e.g.
        # http.client.RemoteDisconnected when LM Studio's server drops the
        # connection mid-response (crash, OOM kill, etc.).
        raise ChatCompletionError(
            f"LM Studio chat-completions connection failed: {exc}"
        ) from exc

    try:
        decoded = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ChatCompletionError(
            "LM Studio chat-completion response was not valid JSON"
        ) from exc

    if not isinstance(decoded, dict):
        raise ChatCompletionError("LM Studio chat-completion response must be a JSON object")
    return decoded


def chat_completion(
    model: str,
    messages: list[dict[str, str]],
    *,
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    temperature: float = 0.0,
) -> ChatCompletionResult:
    """Call LM Studio's OpenAI-compatible chat-completions endpoint once."""
    normalized_base_url = base_url.strip().rstrip("/")
    if not normalized_base_url:
        raise ChatCompletionError("LM Studio base URL must not be empty")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    start = time.monotonic()
    response = _post_json(
        f"{normalized_base_url}/chat/completions",
        payload,
        timeout=timeout,
    )
    latency_seconds = time.monotonic() - start

    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ChatCompletionError("LM Studio chat-completion response had no choices")

    first_choice = choices[0]
    message = first_choice.get("message") if isinstance(first_choice, dict) else None
    text = message.get("content") if isinstance(message, dict) else None
    if not isinstance(text, str):
        raise ChatCompletionError("LM Studio chat-completion response had no message content")

    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    tokens_per_second = None
    if isinstance(completion_tokens, int) and completion_tokens > 0 and latency_seconds > 0:
        tokens_per_second = completion_tokens / latency_seconds

    return ChatCompletionResult(
        text=text,
        latency_seconds=latency_seconds,
        prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
        completion_tokens=completion_tokens if isinstance(completion_tokens, int) else None,
        tokens_per_second=tokens_per_second,
        raw=response,
    )
