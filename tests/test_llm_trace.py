"""LLM 网关的调用级追踪:complete()/stream() 是否把 span 记进 trace_sink。

用假的 _open 顶替真实 HTTP(与 test_llm_gateway 同风格),不联网。
"""
import json

import pytest

from web.backend.agent import obs
from web.backend.config import settings
from web.backend.services import llm
from web.backend.services.llm import LLMError


class _FakeResp:
    """既能当 complete 的 `with _open() as r: r.read()`,也能当 stream 的可迭代行。"""

    def __init__(self, payload: bytes = b"", lines=None):
        self._payload = payload
        self._lines = lines or []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._payload

    def __iter__(self):
        return iter(self._lines)


@pytest.fixture(autouse=True)
def _provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_base_url", "https://x/v1")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(llm, "_BACKOFF_BASE_SECONDS", 0)


# ── obs.Span 契约 ─────────────────────────────────────────────
def test_span_trace_views_drop_none_values():
    sp = obs.Span(kind="llm", name="llm.complete",
                  attributes={"model": "m", "prompt_tokens": None, "total_tokens": 12})
    out = sp.trace_output()
    assert sp.step_type() == "llm_call"
    assert out["ok"] is True and out["total_tokens"] == 12
    assert "prompt_tokens" not in out  # None 被丢掉


def test_emit_noop_on_none_sink():
    obs.emit(None, obs.Span(kind="llm", name="x"))  # 不在 run 内:静默无操作


# ── complete() ────────────────────────────────────────────────
def test_complete_emits_span_with_tokens(monkeypatch):
    body = {
        "choices": [{"message": {"content": "你好"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    }
    monkeypatch.setattr(llm, "_open", lambda req, t: _FakeResp(json.dumps(body).encode()))
    sink: list = []
    assert llm.complete("sys", "hi", trace_sink=sink) == "你好"
    assert len(sink) == 1
    sp = sink[0]
    assert sp.kind == "llm" and sp.name == "llm.complete" and sp.ok
    assert sp.attributes["model"] == "test-model"
    assert sp.attributes["total_tokens"] == 12
    assert sp.attributes["stream"] is False


def test_complete_without_sink_is_noop(monkeypatch):
    body = {"choices": [{"message": {"content": "x"}}]}
    monkeypatch.setattr(llm, "_open", lambda req, t: _FakeResp(json.dumps(body).encode()))
    assert llm.complete("s", "u") == "x"  # 不传 sink 也正常返回


def test_complete_failure_emits_failed_span(monkeypatch):
    def boom(req, t):
        raise LLMError("LLM HTTP 401: bad key", retryable=False)

    monkeypatch.setattr(llm, "_open", boom)
    sink: list = []
    with pytest.raises(LLMError):
        llm.complete("s", "u", trace_sink=sink)
    assert len(sink) == 1
    assert sink[0].ok is False and "401" in sink[0].error


# ── stream() ──────────────────────────────────────────────────
def test_stream_emits_span_with_chars_and_usage(monkeypatch):
    lines = [
        b'data: {"choices":[{"delta":{"content":"\xe7\x94\xb2"}}]}',   # 甲
        b'data: {"choices":[{"delta":{"content":"\xe6\x9c\xa8"}}]}',   # 木
        b'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
        b"data: [DONE]",
    ]
    monkeypatch.setattr(llm, "_open", lambda req, t: _FakeResp(lines=lines))
    sink: list = []
    chunks = list(llm.stream("s", "u", trace_sink=sink))
    assert "".join(chunks) == "甲木"
    assert len(sink) == 1
    sp = sink[0]
    assert sp.name == "llm.stream" and sp.ok and sp.attributes["stream"] is True
    assert sp.attributes["completion_chars"] == 2
    assert sp.attributes["total_tokens"] == 7


# ── 端到端:span 一路串到 trace 表 ─────────────────────────────
def test_stream_chat_persists_llm_call_into_trace(monkeypatch, tmp_path):
    """驱动整条 stream_chat,证明 sink 从 planner→route→extract→complete 串到底,
    并在收尾时排入 run_traces(step_type=llm_call)。"""
    from web.backend import database
    from web.backend.agent import planner, repository

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "trace.db")
    database.init_db()

    # 让抽取把「你好」判为 smalltalk:只触发一次 complete,链路最短。
    extraction = json.dumps({"intent": "smalltalk", "topic": None})
    body = {
        "choices": [{"message": {"content": extraction}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
    }
    monkeypatch.setattr(llm, "_open", lambda req, t: _FakeResp(json.dumps(body).encode()))

    chunks = [json.loads(c) for c in planner.stream_chat("你好")]
    package = repository.get_analysis_package(chunks[-1]["analysis_id"])
    llm_calls = [t for t in package["run_traces"] if t["step_type"] == "llm_call"]
    assert len(llm_calls) >= 1
    out = llm_calls[0]["output_json"]
    # model 由 extractor 用的 fast_provider 决定(环境相关),只断言非空;
    # 关键是 span 里的调用元数据真的落进了 trace。
    assert out["model"]
    assert out["stream"] is False
    assert out["total_tokens"] == 11
    assert out["ok"] is True


def test_conversation_runs_aggregate(monkeypatch, tmp_path):
    """跨轮追踪:一段会话里每轮 run 的概要 + LLM 聚合,按时间正序。"""
    from web.backend import database
    from web.backend.agent import planner, repository

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "conv.db")
    database.init_db()
    body = {
        "choices": [{"message": {"content": json.dumps({"intent": "smalltalk"})}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
    }
    monkeypatch.setattr(llm, "_open", lambda req, t: _FakeResp(json.dumps(body).encode()))

    first = [json.loads(c) for c in planner.stream_chat("你好")]
    conv_id = first[-1]["conversation_id"]
    list(planner.stream_chat("在吗", conversation_id=conv_id))  # 同一会话第二轮

    runs = repository.get_conversation_runs(conv_id)
    assert [r["user_message"] for r in runs] == ["你好", "在吗"]  # 严格时间正序
    assert all(r["llm_calls"] >= 1 for r in runs)
    assert all(r["total_tokens"] == 11 for r in runs)
