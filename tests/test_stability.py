"""稳定性测试:模型中断 / 客户端断开 / 持久化失败时的降级行为。

对应三个已修复的缝隙:
1. reflect_on_reply 收紧超时不重试(锦上添花不拖流的收尾)
2. 客户端断开(GeneratorExit)→ run 照常收尾(状态/成本/trace 不丢)
3. 回复送达后的持久化失败 → 降级为 partial,绝不再给用户发 error 事件
外加:记忆写入失败的旁路保护。
"""
from __future__ import annotations

import json

import pytest

from web.backend import database
from web.backend.agent import hooks, memory, planner, repository, responder
from web.backend.agent.hooks import HookSpec
from web.backend.agent.models import ChatState


@pytest.fixture(autouse=True)
def clean_hooks():
    hooks.reset()
    yield
    hooks.reset()


@pytest.fixture()
def agent_db(tmp_path, monkeypatch):
    """隔离 DB + 强制 LLM 降级(密闭:不烧真 key、不依赖网络)。"""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "agent.db")
    database.init_db()
    from web.backend.agent import extractor
    from web.backend.services import llm
    for mod in (extractor, responder, llm):
        monkeypatch.setattr(mod, "is_configured", lambda: False)


def _chunks(message: str, **kw) -> list[dict]:
    return [json.loads(c) for c in planner.stream_chat(message, **kw)]


def _latest_run() -> dict:
    runs = repository.recent_runs(limit=1)
    assert runs, "expected at least one run"
    return runs[0]


# ---------------------------------------------------------------------------
# 1. reflect_on_reply:收紧超时、不重试
# ---------------------------------------------------------------------------

class TestReflectTimeoutBudget:
    def test_reflect_uses_tight_timeout_and_no_retries(self, monkeypatch):
        captured = {}

        def fake_complete(system_prompt, user_prompt, **kw):
            captured.update(kw)
            return json.dumps({"followups": [], "conclusion": "", "memory": ""})

        monkeypatch.setattr(responder, "is_configured", lambda: True)
        monkeypatch.setattr(responder, "complete", fake_complete)
        responder.reflect_on_reply("career", [], "回复")
        assert captured["timeout"] == 15   # 不用网关默认 60s
        assert captured["retries"] == 0    # 失败即放弃,不拖流的收尾

    def test_reflect_timeout_degrades_to_fallbacks(self, monkeypatch):
        """超时 = LLMError → followups 回退规则池,conclusion/memory 空。"""
        def timeout_complete(*a, **kw):
            raise responder.LLMError("timed out", retryable=True)

        monkeypatch.setattr(responder, "is_configured", lambda: True)
        monkeypatch.setattr(responder, "complete", timeout_complete)
        out = responder.reflect_on_reply("career", [], "回复")
        assert out["followups"]            # 规则池兜底,非空
        assert out["conclusion"] == ""
        assert out["memory"] == ""


# ---------------------------------------------------------------------------
# 2. 客户端断开:run 照常收尾
# ---------------------------------------------------------------------------

class TestClientDisconnect:
    def test_disconnect_finalizes_run_as_disconnected(self, agent_db):
        gen = planner.stream_chat("你好", memory_key="dc-user")
        next(gen)          # 消费第一个 chunk(run 已创建、回复已开始)
        gen.close()        # 客户端断开 → GeneratorExit

        run = _latest_run()
        assert run["status"] == "disconnected"
        assert run["latency_ms"] is not None          # finish_agent_run 跑到了
        assert "disconnected" in (run["error"] or "")

    def test_disconnect_still_fires_run_end_hook(self, agent_db):
        """断开也要有成本记录/聚合——run_end 在 finally 里派发。"""
        seen = []
        hooks.register(HookSpec(event="run_end",
                                fn=lambda ctx: seen.append(ctx.payload["summary"])))
        gen = planner.stream_chat("你好", memory_key="dc-user2")
        next(gen)
        gen.close()
        assert len(seen) == 1
        assert seen[0].status == "disconnected"

    def test_disconnect_drains_spans_to_trace(self, agent_db):
        """断开时已收集的 span 照常落 trace(排查"断在哪"要靠它)。"""
        gen = planner.stream_chat("你好", memory_key="dc-user3")
        next(gen)
        gen.close()
        run = _latest_run()
        data = repository.get_run_with_traces(run["run_id"])
        assert data is not None            # trace 可查,run 不是黑洞

    def test_normal_completion_still_success(self, agent_db):
        """回归:正常走完的轮次不受收尾重构影响。"""
        chunks = _chunks("你好")
        assert chunks[-1]["type"] == "done"
        assert _latest_run()["status"] == "success"


# ---------------------------------------------------------------------------
# 3. 回复送达后的持久化失败:降级,不冤枉好回复
# ---------------------------------------------------------------------------

class TestPostReplyPersistFailure:
    @pytest.fixture()
    def flaky_assistant_write(self, monkeypatch):
        """user 消息正常写,assistant 消息写入时 DB 抖动。"""
        orig = repository.add_message

        def flaky(conv_id, role, content, **kw):
            if role == "assistant":
                raise RuntimeError("db hiccup")
            return orig(conv_id, role, content, **kw)

        monkeypatch.setattr(repository, "add_message", flaky)

    def test_no_error_event_after_delivered_reply(self, agent_db,
                                                  flaky_assistant_write):
        chunks = _chunks("你好")
        types = [c["type"] for c in chunks]
        assert "error" not in types        # 用户拿到了完整回复,不再吓他
        assert types[-1] == "done"         # 流正常收尾

    def test_reply_text_fully_delivered(self, agent_db, flaky_assistant_write):
        chunks = _chunks("你好")
        text = "".join(c.get("text", "") for c in chunks if c["type"] == "token")
        assert "结合命理看" in text        # 回复内容完整送达

    def test_run_marked_partial_with_error_recorded(self, agent_db,
                                                    flaky_assistant_write):
        _chunks("你好")
        run = _latest_run()
        assert run["status"] == "partial"
        assert "persistence failed" in run["error"]

    def test_persist_error_traced_for_debugging(self, agent_db,
                                                flaky_assistant_write):
        _chunks("你好")
        run = _latest_run()
        data = repository.get_run_with_traces(run["run_id"])
        step_types = [t["step_type"] for t in data["traces"]]
        assert "persist_error" in step_types

    def test_pre_reply_failure_still_uses_error_branch(self, agent_db,
                                                       monkeypatch):
        """对照:回复产出**之前**的失败仍走 error 分支(行为不变)。"""
        def boom(*a, **kw):
            raise RuntimeError("router exploded")

        monkeypatch.setattr(planner, "route", boom)
        chunks = _chunks("你好")
        assert "error" in [c["type"] for c in chunks]
        assert _latest_run()["status"] == "failed"


# ---------------------------------------------------------------------------
# 4. 记忆写入失败:旁路保护
# ---------------------------------------------------------------------------

def _fake_stream(conclusion="结论", memory_note="记忆"):
    def fake(topic, tool_result, **kw):
        state = ChatState(topic=topic, needs_more_info=False,
                          missing_fields=[], suggested_followups=[])
        yield "模拟回复", None, None
        yield "", state, {"mode": "fake", "conclusion": conclusion,
                          "memory": memory_note}
    return fake


class TestToolCallSpan:
    """咨询轮的 trace 里必须有 tool_call 步骤(排盘调用链,含耗时/缓存标记)。"""

    def test_consult_turn_traces_tool_call(self, agent_db):
        from web.backend.agent.tools import _TOOL_CACHE
        _TOOL_CACHE.clear()
        chunks = _chunks("1990年5月15日早上8点北京男，看事业", memory_key="ts-user")
        done = chunks[-1]
        package = repository.get_analysis_package(done["analysis_id"])
        tool_steps = [t for t in package["run_traces"]
                      if t["step_type"] == "tool_call"]
        assert len(tool_steps) == 1
        out = tool_steps[0]["output_json"]
        assert out["cached"] is False        # 新盘第一轮是实算
        assert "latency_ms" in out

    def test_smalltalk_turn_has_no_tool_call(self, agent_db):
        chunks = _chunks("你好")
        done = chunks[-1]
        package = repository.get_analysis_package(done["analysis_id"])
        assert all(t["step_type"] != "tool_call" for t in package["run_traces"])


class TestMemoryWriteFailure:
    BIRTH_MSG = "1990年5月15日早上8点北京男，看事业"

    def test_add_note_failure_does_not_break_reply(self, agent_db, monkeypatch):
        monkeypatch.setattr(planner, "stream_consultation_reply", _fake_stream())
        monkeypatch.setattr(memory, "add_note",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
        chunks = _chunks(self.BIRTH_MSG, memory_key="mw-user")
        types = [c["type"] for c in chunks]
        assert "error" not in types
        assert types[-1] == "done"
        assert _latest_run()["status"] == "success"   # 记忆是增强,失败不降级状态

    def test_add_note_failure_traced(self, agent_db, monkeypatch):
        monkeypatch.setattr(planner, "stream_consultation_reply", _fake_stream())
        monkeypatch.setattr(memory, "add_note",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
        chunks = _chunks(self.BIRTH_MSG, memory_key="mw-user2")
        run = _latest_run()
        data = repository.get_run_with_traces(run["run_id"])
        step_types = [t["step_type"] for t in data["traces"]]
        assert "update_memory_error" in step_types
