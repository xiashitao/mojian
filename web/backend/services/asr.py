"""火山引擎大模型 ASR（录音文件识别·极速版）——语音输入的识别后端。

前端把录音转成 16k 单声道 WAV 上传，这里带鉴权同步转发给火山 flash 接口，
返回识别文本。选极速版而非流式：语音输入是「说完再发」的短音频场景，
一次 HTTP 请求最简单可靠，不需要 WebSocket 流式协议。
文档：https://www.volcengine.com/docs/6561/1631584

鉴权两种方式（填其一，新版优先）：
- 新版控制台：VOLC_ASR_API_KEY               → X-Api-Key
- 旧版控制台：VOLC_ASR_APP_ID + VOLC_ASR_ACCESS_TOKEN
                                              → X-Api-App-Key / X-Api-Access-Key
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
import uuid

from ..config import settings

_FLASH_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
_RESOURCE_ID = "volc.bigasr.auc_turbo"
_OK_STATUS = "20000000"
_TIMEOUT_SECONDS = 30


class AsrError(Exception):
    """ASR 调用失败（配置缺失 / 网络 / 服务端返回错误码）。"""


def asr_enabled() -> bool:
    return bool(
        settings.volc_asr_api_key
        or (settings.volc_asr_app_id and settings.volc_asr_access_token)
    )


def _auth_headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": _RESOURCE_ID,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "X-Api-Sequence": "-1",
    }
    if settings.volc_asr_api_key:
        headers["X-Api-Key"] = settings.volc_asr_api_key
    else:
        headers["X-Api-App-Key"] = settings.volc_asr_app_id
        headers["X-Api-Access-Key"] = settings.volc_asr_access_token
    return headers


def recognize(audio_bytes: bytes, fmt: str = "wav") -> str:
    """识别一段短音频，返回文本。fmt 须为火山支持的 wav/mp3/ogg。"""
    if not asr_enabled():
        raise AsrError("语音识别未配置（缺少火山引擎 ASR 密钥）")

    body = {
        "user": {"uid": settings.volc_asr_app_id or "kairos"},
        "audio": {"format": fmt, "data": base64.b64encode(audio_bytes).decode()},
        "request": {"model_name": "bigmodel"},
    }
    req = urllib.request.Request(
        _FLASH_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=_auth_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            status = resp.headers.get("X-Api-Status-Code", "")
            message = resp.headers.get("X-Api-Message", "")
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AsrError(f"语音识别服务返回 HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AsrError("语音识别服务连接失败") from exc
    except json.JSONDecodeError as exc:
        raise AsrError("语音识别服务返回了无法解析的内容") from exc

    if status != _OK_STATUS:
        raise AsrError(f"语音识别失败（{status} {message}）".strip())

    result = payload.get("result") or {}
    text = (result.get("text") or "").strip()
    if not text:
        raise AsrError("未识别到有效语音，请再试一次")
    return text
