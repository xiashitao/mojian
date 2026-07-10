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

from ..agent import obs
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


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


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
    trace_sink: obs.TraceSink | None = None,
) -> str:
    """Non-streaming chat completion; returns the content string (with retries).

    trace_sink(可选):传入则把这次调用记一个 obs.Span(模型/延迟/token/重试)。
    """
    prov = provider or active_provider()
    mdl = model or prov.model
    req = _build_request(system_prompt, user_prompt, provider=prov, model=model,
                         temperature=temperature, stream=False, json_object=json_object)
    started = time.monotonic()
    attempts = {"n": 0}
    usage: dict[str, Any] = {}

    def attempt() -> str:
        attempts["n"] += 1
        with _open(req, timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(
                f"Bad response shape: {json.dumps(body, ensure_ascii=False)[:500]}",
                retryable=False,
            ) from e
        usage.update(body.get("usage") or {})
        return content

    def _span(*, ok: bool, error: str | None, content: str) -> obs.Span:
        return obs.Span(
            kind="llm", name="llm.complete", ok=ok, error=error,
            latency_ms=_elapsed_ms(started), attempts=attempts["n"],
            attributes={
                "provider": prov.name, "model": mdl, "stream": False,
                "system_chars": len(system_prompt), "user_chars": len(user_prompt),
                "completion_chars": len(content),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "user_preview": obs.preview(user_prompt),
                "completion_preview": obs.preview(content),
            },
        )

    try:
        content = _with_retry(attempt, retries)
    except LLMError as e:
        obs.emit(trace_sink, _span(ok=False, error=str(e), content=""))
        raise
    obs.emit(trace_sink, _span(ok=True, error=None, content=content))
    return content


def stream(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.7,
    timeout: int = 60,
    retries: int = _DEFAULT_RETRIES,
    provider: Provider | None = None,
    model: str | None = None,
    trace_sink: obs.TraceSink | None = None,
) -> Iterator[str]:
    """Streaming chat completion. Retries only the connection (pre-stream).

    Once chunks flow we never retry (that would duplicate output); a mid-stream
    failure surfaces as LLMError so callers can fall back to a template.

    trace_sink(可选):流结束(正常/异常/被关闭)时在 finally 里记一个 span——
    延迟、产出字数、token(靠 stream_options.include_usage 拿最后一帧的 usage)。
    """
    prov = provider or active_provider()
    mdl = model or prov.model
    req = _build_request(system_prompt, user_prompt, provider=prov, model=model,
                         temperature=temperature, stream=True, json_object=False)
    started = time.monotonic()
    attempts = {"n": 0}
    chars = 0
    usage: dict[str, Any] = {}
    ok = True
    error: str | None = None

    def _connect():
        attempts["n"] += 1
        return _open(req, timeout)

    try:
        resp = _with_retry(_connect, retries)
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
                except json.JSONDecodeError:
                    continue
                if chunk.get("usage"):  # include_usage 的最后一帧,choices 为空
                    usage = chunk["usage"]
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                content = choices[0].get("delta", {}).get("content", "")
                if content:
                    chars += len(content)
                    yield content
    except LLMError as e:
        ok = False
        error = str(e)
        raise
    except urllib.error.URLError as e:
        ok = False
        error = f"Stream interrupted: {e.reason}"
        raise LLMError(error, retryable=False) from e
    finally:
        obs.emit(trace_sink, obs.Span(
            kind="llm", name="llm.stream", ok=ok, error=error,
            latency_ms=_elapsed_ms(started), attempts=attempts["n"],
            attributes={
                "provider": prov.name, "model": mdl, "stream": True,
                "system_chars": len(system_prompt), "user_chars": len(user_prompt),
                "completion_chars": chars,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "user_preview": obs.preview(user_prompt),
            },
        ))


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
        # 让最后一帧带 usage(token 数),供追踪记录;不影响 prompt、不破坏前缀缓存。
        # DeepSeek/OpenAI/Groq 均支持,不支持的 provider 会忽略此字段。
        payload["stream_options"] = {"include_usage": True}
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
