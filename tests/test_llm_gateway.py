"""Provider-agnostic LLM gateway: retry policy + provider resolution."""
import pytest

from web.backend.config import settings
from web.backend.services import llm
from web.backend.services.llm import LLMError, _with_retry, active_provider


def test_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF_BASE_SECONDS", 0)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMError("transient", retryable=True)
        return "ok"

    assert _with_retry(fn, retries=2) == "ok"
    assert calls["n"] == 3


def test_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(llm, "_BACKOFF_BASE_SECONDS", 0)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise LLMError("transient", retryable=True)

    with pytest.raises(LLMError):
        _with_retry(fn, retries=2)
    assert calls["n"] == 3  # initial + 2 retries


def test_does_not_retry_non_retryable():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise LLMError("bad request", retryable=False)

    with pytest.raises(LLMError):
        _with_retry(fn, retries=2)
    assert calls["n"] == 1


def test_provider_defaults_to_deepseek(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    assert active_provider().base_url == settings.deepseek_base_url
    assert active_provider().model == settings.deepseek_model


def test_provider_override_switches_service(monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", "https://api.openai.com/v1")
    monkeypatch.setattr(settings, "llm_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_model", "gpt-4o-mini")
    provider = active_provider()
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.api_key == "sk-test"
    assert provider.model == "gpt-4o-mini"
