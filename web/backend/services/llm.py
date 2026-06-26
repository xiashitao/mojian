"""Provider-agnostic LLM gateway: timeouts, bounded retries, graceful errors.

Speaks the OpenAI chat-completions wire format, which DeepSeek, OpenAI, Kimi,
Qwen, Together, Groq, etc. all implement — so switching provider is just config
(`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`), no code change. A genuinely
different API (Anthropic, Gemini) would add a small adapter behind the same
`complete()` / `stream()` surface.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, TypeVar

from ..config import settings

_DEFAULT_RETRIES = 2
_BACKOFF_BASE_SECONDS = 0.6  # 0.6, 1.2, 2.4 ... between attempts
_RETRYABLE_HTTP = {429, 500, 502, 503, 504}

T = TypeVar("T")


class LLMError(Exception):
    """An LLM call failed. `retryable` marks transient (worth-retrying) failures."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key: str
    model: str


def active_provider() -> Provider:
    """The main/deep provider — consultation reply & arbitration.
    Defaults to DeepSeek when llm_* are unset."""
    return Provider(
        name="llm",
        base_url=settings.llm_base_url or settings.deepseek_base_url,
        api_key=settings.llm_api_key or settings.deepseek_api_key,
        model=settings.llm_model or settings.deepseek_model,
    )


def fast_provider() -> Provider:
    """The cheap/fast provider — mechanical tasks (routing extraction, follow-up
    questions). Uses FAST_LLM_* if set, else DeepSeek (so a Gemini main + a
    DeepSeek key in env yields a cheap tier for free), else the main provider."""
    key = settings.fast_llm_api_key or settings.deepseek_api_key
    if key:
        return Provider(
            name="fast",
            base_url=settings.fast_llm_base_url or settings.deepseek_base_url,
            api_key=key,
            model=settings.fast_llm_model or settings.deepseek_model,
        )
    return active_provider()


def is_configured() -> bool:
    """Whether an LLM provider has credentials (else callers degrade)."""
    return bool(active_provider().api_key)


def active_model() -> str:
    return active_provider().model


def complete(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.0,
    json_object: bool = True,
    timeout: int = 60,
    retries: int = _DEFAULT_RETRIES,
    provider: Provider | None = None,
    model: str | None = None,
) -> str:
    """Non-streaming chat completion; returns the content string (with retries)."""
    prov = provider or active_provider()
    req = _build_request(system_prompt, user_prompt, provider=prov, model=model,
                         temperature=temperature, stream=False, json_object=json_object)

    def attempt() -> str:
        with _open(req, timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(
                f"Bad response shape: {json.dumps(body, ensure_ascii=False)[:500]}",
                retryable=False,
            ) from e

    return _with_retry(attempt, retries)


def stream(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.7,
    timeout: int = 60,
    retries: int = _DEFAULT_RETRIES,
    provider: Provider | None = None,
    model: str | None = None,
) -> Iterator[str]:
    """Streaming chat completion. Retries only the connection (pre-stream).

    Once chunks flow we never retry (that would duplicate output); a mid-stream
    failure surfaces as LLMError so callers can fall back to a template.
    """
    prov = provider or active_provider()
    req = _build_request(system_prompt, user_prompt, provider=prov, model=model,
                         temperature=temperature, stream=True, json_object=False)

    resp = _with_retry(lambda: _open(req, timeout), retries)
    try:
        with resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                payload_str = line[len("data:"):].strip()
                if payload_str == "[DONE]":
                    return
                try:
                    chunk = json.loads(payload_str)
                    content = chunk["choices"][0]["delta"].get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
    except urllib.error.URLError as e:
        raise LLMError(f"Stream interrupted: {e.reason}", retryable=False) from e


def _build_request(
    system_prompt: str,
    user_prompt: str,
    *,
    provider: Provider,
    model: str | None,
    temperature: float,
    stream: bool,
    json_object: bool,
) -> urllib.request.Request:
    if not provider.api_key:
        raise LLMError("LLM api key not set", retryable=False)
    payload: dict[str, Any] = {
        "model": model or provider.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if stream:
        payload["stream"] = True
    if json_object:
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return urllib.request.Request(
        f"{provider.base_url.rstrip('/')}/chat/completions",
        data=data,
        headers=headers,
        method="POST",
    )


def _open(req: urllib.request.Request, timeout: int):
    """Open the request, mapping transport failures to LLMError."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise LLMError(
            f"LLM HTTP {e.code}: {body[:500]}",
            retryable=e.code in _RETRYABLE_HTTP,
        ) from e
    except urllib.error.URLError as e:
        raise LLMError(f"Network error: {e.reason}", retryable=True) from e


def _with_retry(fn: Callable[[], T], retries: int) -> T:
    last: LLMError | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except LLMError as e:
            last = e
            if not e.retryable or attempt == retries:
                raise
            time.sleep(_BACKOFF_BASE_SECONDS * (2 ** attempt))
    assert last is not None  # pragma: no cover
    raise last
