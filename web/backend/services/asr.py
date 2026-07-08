"""语音输入的识别后端——支持火山引擎与 Groq 两个 provider,按配置切换。

对外只暴露 asr_enabled() / recognize(),路由层不感知具体 provider。
选哪个由 ASR_PROVIDER 决定(volc | groq),默认 volc。两个 provider 都可
单独配置,随时改一个环境变量切换,互不影响。

── 火山引擎大模型 ASR(录音文件识别·极速版)──────────────────
前端把录音转成 16k 单声道 WAV 上传,带鉴权同步转发给火山 flash 接口。
选极速版而非流式:语音输入是「说完再发」的短音频,一次 HTTP 最简单可靠。
文档:https://www.volcengine.com/docs/6561/1631584
鉴权二选一(新版优先):
- 新版控制台:VOLC_ASR_API_KEY               → X-Api-Key
- 旧版控制台:VOLC_ASR_APP_ID + VOLC_ASR_ACCESS_TOKEN
                                             → X-Api-App-Key / X-Api-Access-Key

── Groq(Whisper)────────────────────────────────────────────
OpenAI 兼容的转录接口,multipart 上传音频文件,返回 {"text": ...}。
海外节点、速度快;国内访问延迟/连通性不如火山,作为备选或海外通道。
文档:https://console.groq.com/docs/speech-to-text
鉴权:GROQ_API_KEY → Authorization: Bearer
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
import uuid

from ..config import settings

_TIMEOUT_SECONDS = 30


class AsrError(Exception):
    """ASR 调用失败（配置缺失 / 网络 / 服务端返回错误码）。"""


def _provider() -> str:
    return (settings.asr_provider or "volc").strip().lower()


# ── 对外接口:按 provider 分发 ──────────────────────────────────
def asr_enabled() -> bool:
    """当前选定的 provider 是否已配置(决定前端是否显示麦克风)。"""
    if _provider() == "groq":
        return _groq_enabled()
    return _volc_enabled()


def recognize(audio_bytes: bytes, fmt: str = "wav") -> str:
    """识别一段短音频,返回文本。fmt 为 wav/mp3/ogg。"""
    if _provider() == "groq":
        return _groq_recognize(audio_bytes, fmt)
    return _volc_recognize(audio_bytes, fmt)


# ── 火山引擎 ───────────────────────────────────────────────────
_VOLC_FLASH_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
_VOLC_RESOURCE_ID = "volc.bigasr.auc_turbo"
_VOLC_OK_STATUS = "20000000"


def _volc_enabled() -> bool:
    return bool(
        settings.volc_asr_api_key
        or (settings.volc_asr_app_id and settings.volc_asr_access_token)
    )


def _volc_auth_headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": _VOLC_RESOURCE_ID,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "X-Api-Sequence": "-1",
    }
    if settings.volc_asr_api_key:
        headers["X-Api-Key"] = settings.volc_asr_api_key
    else:
        headers["X-Api-App-Key"] = settings.volc_asr_app_id
        headers["X-Api-Access-Key"] = settings.volc_asr_access_token
    return headers


def _volc_recognize(audio_bytes: bytes, fmt: str) -> str:
    if not _volc_enabled():
        raise AsrError("语音识别未配置（缺少火山引擎 ASR 密钥）")

    body = {
        "user": {"uid": settings.volc_asr_app_id or "kairos"},
        "audio": {"format": fmt, "data": base64.b64encode(audio_bytes).decode()},
        "request": {"model_name": "bigmodel"},
    }
    req = urllib.request.Request(
        _VOLC_FLASH_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=_volc_auth_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            status = resp.headers.get("X-Api-Status-Code", "")
            message = resp.headers.get("X-Api-Message", "")
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 火山把具体错误放在响应头里(如鉴权失败/资源未开通),透传出来便于排障。
        code = exc.headers.get("X-Api-Status-Code", "") if exc.headers else ""
        message = exc.headers.get("X-Api-Message", "") if exc.headers else ""
        detail = f"{code} {message}".strip() or f"HTTP {exc.code}"
        raise AsrError(f"语音识别失败（{detail}）") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AsrError("语音识别服务连接失败") from exc
    except json.JSONDecodeError as exc:
        raise AsrError("语音识别服务返回了无法解析的内容") from exc

    if status != _VOLC_OK_STATUS:
        raise AsrError(f"语音识别失败（{status} {message}）".strip())

    result = payload.get("result") or {}
    text = (result.get("text") or "").strip()
    if not text:
        raise AsrError("未识别到有效语音，请再试一次")
    return text


# ── Groq (Whisper) ────────────────────────────────────────────
def _groq_enabled() -> bool:
    return bool(settings.groq_api_key)


def _multipart(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    file_bytes: bytes,
    file_content_type: str,
) -> tuple[str, bytes]:
    """手工拼 multipart/form-data(不引入 requests/httpx,与项目其余 urllib 一致)。"""
    boundary = "----kairos" + uuid.uuid4().hex
    sep = f"--{boundary}\r\n".encode()
    body = b""
    for name, value in fields.items():
        body += sep
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    body += sep
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\n'
    ).encode()
    body += f"Content-Type: {file_content_type}\r\n\r\n".encode()
    body += file_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return boundary, body


def _groq_recognize(audio_bytes: bytes, fmt: str) -> str:
    if not _groq_enabled():
        raise AsrError("语音识别未配置（缺少 Groq API Key）")

    fields = {"model": settings.groq_asr_model, "response_format": "json"}
    # 指定语言可略微提速并稳定中文识别;留空则 Whisper 自动检测。
    if settings.groq_asr_language:
        fields["language"] = settings.groq_asr_language
    boundary, body = _multipart(
        fields, "file", f"audio.{fmt}", audio_bytes, f"audio/{fmt}"
    )
    req = urllib.request.Request(
        f"{settings.groq_base_url.rstrip('/')}/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            err = json.loads(exc.read().decode("utf-8"))
            detail = (err.get("error") or {}).get("message", "")
        except Exception:  # noqa: BLE001 - 错误体解析失败不该盖过原始 HTTP 码
            detail = ""
        raise AsrError(f"语音识别失败（{detail or f'HTTP {exc.code}'}）") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AsrError("语音识别服务连接失败") from exc
    except json.JSONDecodeError as exc:
        raise AsrError("语音识别服务返回了无法解析的内容") from exc

    text = (payload.get("text") or "").strip()
    if not text:
        raise AsrError("未识别到有效语音，请再试一次")
    return text
