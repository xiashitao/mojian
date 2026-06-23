"""DeepSeek API client — extracted from examples/deepseek_runner.py."""
import json
import urllib.request
import urllib.error
from collections.abc import Iterator
from typing import Any

from ..config import settings


class DeepSeekAPIError(Exception):
    """DeepSeek API call failed."""


def call_deepseek(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    base_url: str | None = None,
    timeout: int = 60,
) -> str:
    """Call DeepSeek chat completions API, return content string."""
    key = api_key or settings.deepseek_api_key
    url_base = (base_url or settings.deepseek_base_url).rstrip("/")
    mdl = model or settings.deepseek_model

    if not key:
        raise DeepSeekAPIError("DEEPSEEK_API_KEY not set")

    url = f"{url_base}/chat/completions"
    payload = {
        "model": mdl,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise DeepSeekAPIError(f"DeepSeek API HTTP {e.code}: {err_body[:500]}") from e
    except urllib.error.URLError as e:
        raise DeepSeekAPIError(f"Network error: {e.reason}") from e

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise DeepSeekAPIError(
            f"Response structure error: {json.dumps(body, ensure_ascii=False)[:500]}"
        ) from e


def stream_deepseek(
    system_prompt: str,
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    base_url: str | None = None,
    timeout: int = 60,
) -> Iterator[str]:
    """Call DeepSeek with stream=True, yield content chunks as they arrive."""
    key = api_key or settings.deepseek_api_key
    url_base = (base_url or settings.deepseek_base_url).rstrip("/")
    mdl = model or settings.deepseek_model

    if not key:
        raise DeepSeekAPIError("DEEPSEEK_API_KEY not set")

    url = f"{url_base}/chat/completions"
    payload: dict[str, Any] = {
        "model": mdl,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                payload_str = line[len("data:"):].strip()
                if payload_str == "[DONE]":
                    return
                try:
                    chunk = json.loads(payload_str)
                    delta = chunk["choices"][0]["delta"]
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise DeepSeekAPIError(f"DeepSeek API HTTP {e.code}: {err_body[:500]}") from e
    except urllib.error.URLError as e:
        raise DeepSeekAPIError(f"Network error: {e.reason}") from e
