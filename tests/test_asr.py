"""语音输入(ASR 代理)的 provider 切换、配置门控与接口契约。

不用 TestClient(需额外装 httpx),直接测路由函数与服务层;
登录门槛由 Depends(get_current_user) 声明,属 FastAPI 装配,不在此重复测。
"""
import base64

import pytest
from fastapi import HTTPException

from web.backend.config import settings
from web.backend.routers.asr import AsrRequest, enabled, recognize_voice
from web.backend.services.asr import AsrError, asr_enabled, recognize


@pytest.fixture(autouse=True)
def clear_asr_settings(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "volc")
    monkeypatch.setattr(settings, "volc_asr_api_key", "")
    monkeypatch.setattr(settings, "volc_asr_app_id", "")
    monkeypatch.setattr(settings, "volc_asr_access_token", "")
    monkeypatch.setattr(settings, "groq_api_key", "")


# ── 火山 provider ─────────────────────────────────────────────
def test_volc_disabled_without_keys():
    assert not asr_enabled()
    assert enabled() == {"enabled": False}


def test_volc_enabled_with_new_console_key(monkeypatch):
    monkeypatch.setattr(settings, "volc_asr_api_key", "test-key")
    assert asr_enabled()
    assert enabled() == {"enabled": True}


def test_volc_enabled_needs_both_old_console_fields(monkeypatch):
    monkeypatch.setattr(settings, "volc_asr_app_id", "appid-only")
    assert not asr_enabled()
    monkeypatch.setattr(settings, "volc_asr_access_token", "token")
    assert asr_enabled()


def test_volc_recognize_raises_when_unconfigured():
    with pytest.raises(AsrError):
        recognize(b"\x00\x01")


# ── Groq provider ─────────────────────────────────────────────
def test_groq_enabled_follows_its_own_key(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "groq")
    # 火山配了,但 provider=groq 时看的是 groq_api_key。
    monkeypatch.setattr(settings, "volc_asr_api_key", "volc-key")
    assert not asr_enabled()
    monkeypatch.setattr(settings, "groq_api_key", "groq-key")
    assert asr_enabled()


def test_groq_recognize_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "asr_provider", "groq")
    with pytest.raises(AsrError):
        recognize(b"\x00\x01")


def test_provider_switch_is_isolated(monkeypatch):
    # 只配火山:volc 下开,groq 下关。
    monkeypatch.setattr(settings, "volc_asr_api_key", "volc-key")
    monkeypatch.setattr(settings, "asr_provider", "volc")
    assert asr_enabled()
    monkeypatch.setattr(settings, "asr_provider", "groq")
    assert not asr_enabled()


# ── 路由层通用契约(与 provider 无关)──────────────────────────
def test_endpoint_503_when_unconfigured():
    audio = base64.b64encode(b"\x00\x01").decode()
    with pytest.raises(HTTPException) as exc:
        recognize_voice(AsrRequest(audio=audio), user=None)
    assert exc.value.status_code == 503


def test_endpoint_400_on_invalid_base64(monkeypatch):
    monkeypatch.setattr(settings, "volc_asr_api_key", "test-key")
    with pytest.raises(HTTPException) as exc:
        recognize_voice(AsrRequest(audio="not-base64!!"), user=None)
    assert exc.value.status_code == 400


def test_endpoint_400_on_empty_audio(monkeypatch):
    monkeypatch.setattr(settings, "volc_asr_api_key", "test-key")
    with pytest.raises(HTTPException) as exc:
        recognize_voice(AsrRequest(audio=""), user=None)
    assert exc.value.status_code == 400
