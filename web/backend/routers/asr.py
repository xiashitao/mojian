"""语音输入：接收前端录音（base64 WAV），转发火山大模型 ASR，返回识别文本。

识别接口要求登录：ASR 按量计费，匿名开放会被刷量。
/asr/enabled 公开，前端据此决定是否渲染麦克风按钮。
"""
from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import CurrentUser, get_current_user
from ..services.asr import AsrError, asr_enabled, recognize

router = APIRouter()

# 16k 单声道 16bit WAV 约 32KB/s，5MB ≈ 2.5 分钟，语音输入绰绰有余。
_MAX_AUDIO_BYTES = 5 * 1024 * 1024


class AsrRequest(BaseModel):
    audio: str = Field(..., description="base64 编码的 WAV（16k 单声道）")


class AsrResponse(BaseModel):
    text: str


@router.get("/asr/enabled")
def enabled() -> dict[str, bool]:
    return {"enabled": asr_enabled()}


@router.post("/asr/recognize", response_model=AsrResponse)
def recognize_voice(
    payload: AsrRequest,
    user: CurrentUser = Depends(get_current_user),
) -> AsrResponse:
    if not asr_enabled():
        raise HTTPException(status_code=503, detail="语音识别未配置")
    try:
        audio = base64.b64decode(payload.audio, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="音频数据不是有效的 base64")
    if not audio:
        raise HTTPException(status_code=400, detail="音频数据为空")
    if len(audio) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="音频过大，请分段输入")
    try:
        return AsrResponse(text=recognize(audio))
    except AsrError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
