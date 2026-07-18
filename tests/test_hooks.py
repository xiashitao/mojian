"""hook 系统测试:核心语义 / 聚合 / 内置消费者 / 埋点集成 / 管线端到端。

分层:
1. dispatch 核心语义:顺序、matcher、block/patch、能力表白名单、错误隔离
2. summarize_run 聚合
3. CostMeter / StructuredLog 内置 hook
4. TraceWriter 埋点集成
5. planner 端到端:hook 真实影响一轮对话(block/patch/观测事件)
"""
from __future__ import annotations

import json

import pytest

from web.backend import database
from web.backend.agent import hooks, planner, repository, tracing
from web.backend.agent.hooks import (
    EVENTS,
    HookContext,
    HookError,
    HookResult,
    HookSpec,
    RunSummary,
    summarize_run,
)
from web.backend.agent.hooks_builtin import CostMeter, StructuredLog, compute_cost
from web.backend.agent.obs import Span


@pytest.fixture(autouse=True)
def clean_hooks():
    """每个测试前后清空注册表,测试之间绝不互相污染。"""
    hooks.reset()
    yield
    hooks.reset()


@pytest.fixture()
def agent_db(tmp_path, monkeypatch):
    """隔离的 DB + 强制 LLM 降级:e2e 测试必须密闭——不烧真钱、不依赖网络、
    结果确定。is_configured 被各模块直接 import,逐模块补丁。"""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "agent.db")
    database.init_db()
    from web.backend.agent import extractor, responder
    from web.backend.services import llm
    for mod in (extractor, responder, llm):
        monkeypatch.setattr(mod, "is_configured", lambda: False)


def _spec(event, fn, **kw):
    return HookSpec(event=event, fn=fn, **kw)


# ---------------------------------------------------------------------------
# 1. dispatch 核心语义
# ---------------------------------------------------------------------------

class TestDispatchBasics:
    def test_no_hooks_returns_payload_unchanged(self):
        out = hooks.dispatch("user_message", {"message": "hi"})
        assert out.payload == {"message": "hi"}
        assert not out.blocked
        assert out.applied == ()

    def test_unknown_event_dispatch_raises(self):
        with pytest.raises(ValueError, match="unknown hook event"):
            hooks.dispatch("no_such_event", {})

    def test_unknown_event_registration_raises(self):
        with pytest.raises(ValueError, match="unknown hook event"):
            hooks.register(_spec("no_such_event", lambda ctx: None))

    def test_bad_matcher_regex_raises_at_registration(self):
        with pytest.raises(Exception):  # re.error
            hooks.register(_spec("on_step", lambda ctx: None, matcher="[unclosed"))

    def test_hook_returning_none_means_continue(self):
        hooks.register(_spec("user_message", lambda ctx: None))
        out = hooks.dispatch("user_message", {"message": "hi"})
        assert out.payload == {"message": "hi"}
        assert len(out.applied) == 1

    def test_reset_clears_registry(self):
        hooks.register(_spec("on_step", lambda ctx: None))
        hooks.reset()
        assert hooks.registered() == []

    def test_registered_filters_by_event(self):
        hooks.register(_spec("on_step", lambda ctx: None, name="a"))
        hooks.register(_spec("on_span", lambda ctx: None, name="b"))
        assert [s.name for s in hooks.registered("on_step")] == ["a"]

    def test_default_name_is_function_qualname(self):
        def my_hook(ctx):
            return None
        hooks.register(_spec("on_step", my_hook))
        assert "my_hook" in hooks.registered("on_step")[0].name

    def test_caller_payload_dict_not_mutated(self):
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="patch", patch={"message": "changed"})))
        original = {"message": "hi"}
        out = hooks.dispatch("user_message", original)
        assert original == {"message": "hi"}      # 调用方的 dict 不被改
        assert out.payload["message"] == "changed"


class TestOrdering:
    def test_priority_order_lower_first(self):
        calls = []
        hooks.register(_spec("on_step", lambda ctx: calls.append("late"),
                             priority=200, name="late"))
        hooks.register(_spec("on_step", lambda ctx: calls.append("early"),
                             priority=1, name="early"))
        hooks.dispatch("on_step", {})
        assert calls == ["early", "late"]

    def test_same_priority_keeps_registration_order(self):
        calls = []
        for tag in ("first", "second", "third"):
            hooks.register(_spec("on_step",
                                 lambda ctx, t=tag: calls.append(t), name=tag))
        hooks.dispatch("on_step", {})
        assert calls == ["first", "second", "third"]

    def test_patch_chains_later_hook_sees_earlier_patch(self):
        seen = {}
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="patch", patch={"message": "A"}),
            priority=1))

        def second(ctx):
            seen["msg"] = ctx.payload["message"]
            return HookResult(action="patch", patch={"message": ctx.payload["message"] + "B"})

        hooks.register(_spec("user_message", second, priority=2))
        out = hooks.dispatch("user_message", {"message": "x"})
        assert seen["msg"] == "A"          # 第二个 hook 看到第一个的 patch
        assert out.payload["message"] == "AB"


class TestMatcher:
    def test_matcher_skips_non_matching(self):
        calls = []
        hooks.register(_spec("pre_tool", lambda ctx: calls.append(1),
                             matcher="^bazibase$"))
        hooks.dispatch("pre_tool", {"args": {}}, match_value="other_tool")
        assert calls == []

    def test_matcher_runs_on_match(self):
        calls = []
        hooks.register(_spec("pre_tool", lambda ctx: calls.append(1),
                             matcher="^bazibase$"))
        hooks.dispatch("pre_tool", {"args": {}}, match_value="bazibase")
        assert calls == [1]

    def test_matcher_is_regex_search(self):
        calls = []
        hooks.register(_spec("on_span", lambda ctx: calls.append(ctx.match_value),
                             matcher=r"llm\."))
        hooks.dispatch("on_span", {}, match_value="llm.stream")
        hooks.dispatch("on_span", {}, match_value="llm.complete")
        hooks.dispatch("on_span", {}, match_value="tool.bazibase")
        assert calls == ["llm.stream", "llm.complete"]

    def test_no_matcher_runs_always(self):
        calls = []
        hooks.register(_spec("on_span", lambda ctx: calls.append(1)))
        hooks.dispatch("on_span", {}, match_value="anything")
        hooks.dispatch("on_span", {})  # match_value=None 也执行
        assert calls == [1, 1]

    def test_matcher_with_none_match_value_skips(self):
        calls = []
        hooks.register(_spec("on_span", lambda ctx: calls.append(1), matcher="x"))
        hooks.dispatch("on_span", {})  # 有 matcher 但没有 match_value → 不执行
        assert calls == []


class TestBlockSemantics:
    def test_block_short_circuits_later_hooks(self):
        calls = []
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="block", reason="nope"),
            priority=1, name="blocker"))
        hooks.register(_spec("user_message", lambda ctx: calls.append(1),
                             priority=2))
        out = hooks.dispatch("user_message", {"message": "hi"})
        assert out.blocked
        assert out.reason == "nope"
        assert out.blocked_by == "blocker"
        assert calls == []                # 后续 hook 未执行

    def test_block_ignored_on_observe_only_event(self, caplog):
        hooks.register(_spec(
            "on_step", lambda ctx: HookResult(action="block", reason="try"),
            name="bad_blocker"))
        out = hooks.dispatch("on_step", {"step_type": "x"})
        assert not out.blocked            # 观察类事件 block 无效
        assert "observe-only" in caplog.text

    def test_block_after_patch_keeps_patched_payload(self):
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="patch", patch={"message": "cleaned"}),
            priority=1))
        hooks.register(_spec(
            "user_message", lambda ctx: HookResult(action="block", reason="stop"),
            priority=2))
        out = hooks.dispatch("user_message", {"message": "raw"})
        assert out.blocked
        assert out.payload["message"] == "cleaned"  # block 前的 patch 保留


class TestPatchWhitelist:
    def test_patch_key_not_in_whitelist_dropped(self, caplog):
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="patch",
                                   patch={"message": "ok", "evil_key": "x"}),
            name="sneaky"))
        out = hooks.dispatch("user_message", {"message": "hi"})
        assert out.payload["message"] == "ok"       # 白名单键生效
        assert "evil_key" not in out.payload        # 白名单外的键被丢弃
        assert "not allowed" in caplog.text

    def test_patch_entirely_ignored_on_observe_event(self):
        hooks.register(_spec(
            "run_end",
            lambda ctx: HookResult(action="patch", patch={"summary": "hacked"})))
        out = hooks.dispatch("run_end", {"summary": "real"})
        assert out.payload["summary"] == "real"

    def test_every_event_has_caps_declared(self):
        # 能力表完整性:所有事件都能 dispatch,观察类事件 patch 键为空。
        for event, caps in EVENTS.items():
            out = hooks.dispatch(event, {"k": "v"})
            assert out.payload == {"k": "v"}
            if not caps.can_block and not caps.patchable_keys:
                # 观察类:block 与 patch 都必须无效
                hooks.reset()
                hooks.register(_spec(
                    event, lambda ctx: HookResult(action="block")))
                assert not hooks.dispatch(event, {}).blocked
                hooks.reset()


class TestErrorIsolation:
    def test_noncritical_error_skipped_others_run(self, caplog):
        calls = []

        def boom(ctx):
            raise RuntimeError("boom")

        hooks.register(_spec("on_step", boom, priority=1, name="boom"))
        hooks.register(_spec("on_step", lambda ctx: calls.append(1), priority=2))
        out = hooks.dispatch("on_step", {})
        assert calls == [1]               # 后续 hook 照常执行
        assert "boom" in caplog.text
        assert len(out.applied) == 1      # 失败的不计入 applied,成功的计入

    def test_critical_error_raises_hook_error(self):
        def boom(ctx):
            raise RuntimeError("boom")

        hooks.register(_spec("user_message", boom, critical=True, name="critical_boom"))
        with pytest.raises(HookError, match="critical_boom"):
            hooks.dispatch("user_message", {"message": "hi"})

    def test_failed_hook_does_not_corrupt_payload(self):
        def boom(ctx):
            ctx.payload["message"] = "corrupted"  # 违规直接改(而非 patch)后崩溃
            raise RuntimeError("boom")

        hooks.register(_spec("user_message", boom, priority=1))
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="patch",
                                   patch={"message": ctx.payload["message"] + "!"}),
            priority=2))
        out = hooks.dispatch("user_message", {"message": "hi"})
        # 直接改 payload 是违规用法,当前实现不做深拷贝防御(文档已声明);
        # 这里锁住的行为是:dispatch 不因异常中断,后续 hook 正常执行。
        assert out.payload["message"].endswith("!")


# ---------------------------------------------------------------------------
# 2. summarize_run 聚合
# ---------------------------------------------------------------------------

def _llm_span(model="deepseek-chat", pt=100, ct=50, cost=None, name="llm.complete"):
    attrs = {"model": model, "prompt_tokens": pt, "completion_tokens": ct,
             "total_tokens": (pt or 0) + (ct or 0)}
    if cost is not None:
        attrs["cost"] = cost
    return Span(kind="llm", name=name, attributes=attrs)


class TestSummarizeRun:
    def _summary(self, spans):
        return summarize_run(run_id="r1", conversation_id="c1", status="success",
                             error=None, latency_ms=1000, spans=spans)

    def test_aggregates_llm_spans_only(self):
        spans = [
            _llm_span(pt=100, ct=50),
            _llm_span(pt=200, ct=100),
            Span(kind="tool", name="tool.bazibase",
                 attributes={"total_tokens": 99999}),  # 非 llm,必须忽略
        ]
        s = self._summary(spans)
        assert s.llm_calls == 2
        assert s.prompt_tokens == 300
        assert s.completion_tokens == 150
        assert s.total_tokens == 450

    def test_cost_none_when_no_span_has_cost(self):
        s = self._summary([_llm_span(), _llm_span()])
        assert s.cost is None             # 不知道就是 None,不冒充 0

    def test_cost_sums_present_costs(self):
        s = self._summary([_llm_span(cost=0.001), _llm_span(cost=0.002),
                           _llm_span(cost=None)])
        assert s.cost == pytest.approx(0.003)

    def test_models_bucketed_separately(self):
        s = self._summary([
            _llm_span(model="deepseek-chat", pt=100, ct=50, cost=0.001),
            _llm_span(model="deepseek-reasoner", pt=10, ct=5),
        ])
        assert set(s.models) == {"deepseek-chat", "deepseek-reasoner"}
        assert s.models["deepseek-chat"]["calls"] == 1
        assert s.models["deepseek-chat"]["cost"] == pytest.approx(0.001)
        assert s.models["deepseek-reasoner"]["cost"] is None

    def test_missing_token_fields_treated_as_zero(self):
        span = Span(kind="llm", name="llm.stream",
                    attributes={"model": "m"})   # 无任何 token 字段
        s = self._summary([span])
        assert s.llm_calls == 1
        assert s.total_tokens == 0

    def test_empty_spans(self):
        s = self._summary([])
        assert s.llm_calls == 0
        assert s.cost is None
        assert s.models == {}


# ---------------------------------------------------------------------------
# 3. 内置 hook:CostMeter / StructuredLog
# ---------------------------------------------------------------------------

class TestComputeCost:
    def test_known_model_exact_math(self):
        # deepseek-chat: 输入 ¥2/M,输出 ¥8/M
        # 1000 输入 + 500 输出 = 2*1000/1e6 + 8*500/1e6 = 0.002 + 0.004
        assert compute_cost("deepseek-chat", 1000, 500) == pytest.approx(0.006)

    def test_unknown_model_returns_none(self):
        assert compute_cost("gpt-99", 1000, 500) is None

    def test_missing_tokens_returns_none(self):
        assert compute_cost("deepseek-chat", None, 500) is None
        assert compute_cost("deepseek-chat", 1000, None) is None

    def test_none_model_returns_none(self):
        assert compute_cost(None, 1000, 500) is None

    def test_zero_tokens_costs_zero(self):
        assert compute_cost("deepseek-chat", 0, 0) == 0.0


class TestCostMeter:
    def test_on_span_writes_cost_to_llm_span(self):
        span = _llm_span(pt=1000, ct=500)
        CostMeter().on_span(HookContext(event="on_span", run_id="r",
                                        payload={"span": span}))
        assert span.attributes["cost"] == pytest.approx(0.006)

    def test_on_span_ignores_non_llm_span(self):
        span = Span(kind="tool", name="tool.x",
                    attributes={"model": "deepseek-chat",
                                "prompt_tokens": 1, "completion_tokens": 1})
        CostMeter().on_span(HookContext(event="on_span", run_id="r",
                                        payload={"span": span}))
        assert "cost" not in span.attributes

    def test_on_span_unknown_model_leaves_no_cost(self):
        span = _llm_span(model="mystery")
        CostMeter().on_span(HookContext(event="on_span", run_id="r",
                                        payload={"span": span}))
        assert "cost" not in span.attributes

    def test_on_run_end_persists_to_run_costs(self, monkeypatch):
        written = {}

        def fake_add(run_id, conversation_id, **kw):
            written.update(run_id=run_id, conversation_id=conversation_id, **kw)

        monkeypatch.setattr(repository, "add_run_cost", fake_add)
        summary = RunSummary(run_id="r1", conversation_id="c1", status="success",
                             error=None, latency_ms=1, llm_calls=2,
                             prompt_tokens=300, completion_tokens=150,
                             total_tokens=450, cost=0.006,
                             models={"deepseek-chat": {"calls": 2}})
        CostMeter().on_run_end(HookContext(event="run_end", run_id="r1",
                                           payload={"summary": summary}))
        assert written["run_id"] == "r1"
        assert written["cost"] == pytest.approx(0.006)
        assert written["total_tokens"] == 450

    def test_on_run_end_skips_zero_llm_calls(self, monkeypatch):
        called = []
        monkeypatch.setattr(repository, "add_run_cost",
                            lambda *a, **k: called.append(1))
        summary = RunSummary(run_id="r1", conversation_id="c1", status="success",
                             error=None, latency_ms=1, llm_calls=0,
                             prompt_tokens=0, completion_tokens=0,
                             total_tokens=0, cost=None)
        CostMeter().on_run_end(HookContext(event="run_end", run_id="r1",
                                           payload={"summary": summary}))
        assert called == []


class TestStructuredLog:
    def test_on_step_writes_valid_json_line(self, tmp_path):
        slog = StructuredLog(path=tmp_path / "agent.jsonl")
        slog.on_step(HookContext(event="on_step", run_id="run-1", payload={
            "step_type": "extract_input", "step_index": 1, "summary": "routed"}))
        lines = (tmp_path / "agent.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["event"] == "step"
        assert rec["run_id"] == "run-1"
        assert rec["step_type"] == "extract_input"
        assert rec["summary"] == "routed"
        assert "ts" in rec

    def test_on_run_end_writes_summary_line(self, tmp_path):
        slog = StructuredLog(path=tmp_path / "agent.jsonl")
        summary = RunSummary(run_id="r1", conversation_id="c1", status="failed",
                             error="LLM down", latency_ms=42, llm_calls=1,
                             prompt_tokens=10, completion_tokens=5,
                             total_tokens=15, cost=0.001)
        slog.on_run_end(HookContext(event="run_end", run_id="r1",
                                    payload={"summary": summary}))
        rec = json.loads((tmp_path / "agent.jsonl").read_text().strip())
        assert rec["event"] == "run_end"
        assert rec["status"] == "failed"
        assert rec["error"] == "LLM down"
        assert rec["cost"] == pytest.approx(0.001)

    def test_appends_multiple_lines(self, tmp_path):
        slog = StructuredLog(path=tmp_path / "agent.jsonl")
        for i in range(3):
            slog.on_step(HookContext(event="on_step", run_id="r", payload={
                "step_type": "s", "step_index": i, "summary": None}))
        lines = (tmp_path / "agent.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3
        assert [json.loads(l)["step_index"] for l in lines] == [0, 1, 2]

    def test_creates_parent_directory(self, tmp_path):
        slog = StructuredLog(path=tmp_path / "deep" / "nested" / "agent.jsonl")
        assert slog.path.parent.is_dir()


# ---------------------------------------------------------------------------
# 4. TraceWriter 埋点集成
# ---------------------------------------------------------------------------

class TestTraceWriterIntegration:
    def test_add_dispatches_on_step_with_incrementing_index(self, monkeypatch):
        monkeypatch.setattr(repository, "add_trace", lambda *a, **k: None)
        seen = []
        hooks.register(_spec(
            "on_step",
            lambda ctx: seen.append((ctx.run_id, ctx.payload["step_type"],
                                     ctx.payload["step_index"]))))
        writer = tracing.TraceWriter("run-9")
        writer.add("extract_input", summary="a")
        writer.add("generate_reply", summary="b")
        assert seen == [("run-9", "extract_input", 1),
                        ("run-9", "generate_reply", 2)]

    def test_on_step_matcher_filters_by_step_type(self, monkeypatch):
        monkeypatch.setattr(repository, "add_trace", lambda *a, **k: None)
        seen = []
        hooks.register(_spec("on_step",
                             lambda ctx: seen.append(ctx.payload["step_type"]),
                             matcher="^llm_call$"))
        writer = tracing.TraceWriter("r")
        writer.add("extract_input")
        writer.add("llm_call")
        assert seen == ["llm_call"]

    def test_hook_failure_does_not_break_trace_write(self, monkeypatch):
        writes = []
        monkeypatch.setattr(repository, "add_trace",
                            lambda *a, **k: writes.append(a))

        def boom(ctx):
            raise RuntimeError("observer bug")

        hooks.register(_spec("on_step", boom))
        tracing.TraceWriter("r").add("extract_input")  # 不应抛异常
        assert len(writes) == 1


# ---------------------------------------------------------------------------
# 5. planner 端到端:hook 真实影响一轮对话
# ---------------------------------------------------------------------------

def _stream(message: str, **kw) -> tuple[str, dict]:
    chunks = [json.loads(c) for c in planner.stream_chat(message, **kw)]
    text = "".join(c.get("text", "") for c in chunks if c.get("type") == "token")
    return text, chunks[-1]


class TestPlannerEndToEnd:
    def test_zero_hooks_behaves_as_before(self, agent_db):
        text, done = _stream("你好")
        assert "结合命理看" in text        # 与 test_agent_conversations 同断言
        assert done["type"] == "done"

    def test_user_message_block_yields_out_of_scope_reply(self, agent_db):
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="block", reason="policy"),
            name="policy_gate"))
        text, done = _stream("你好")
        assert "超出" in text              # 走了 out_of_scope 模板
        assert done["type"] == "done"

        # block 记入 trace,可排查
        package = repository.get_analysis_package(done["analysis_id"])
        step_types = [t["step_type"] for t in package["run_traces"]]
        assert "hook_block" in step_types

    def test_user_message_patch_rewrites_routing_input(self, agent_db):
        # 把消息改写成越界话题 → 路由应按改写后的文本走 out_of_scope。
        hooks.register(_spec(
            "user_message",
            lambda ctx: HookResult(action="patch",
                                   patch={"message": "帮我选只股票"})))
        text, _ = _stream("你好")
        assert "超出" in text

    def test_post_route_block_forces_out_of_scope(self, agent_db):
        hooks.register(_spec(
            "post_route", lambda ctx: HookResult(action="block", reason="gate")))
        text, _ = _stream("你好")
        assert "超出" in text

    def test_post_route_matcher_only_hits_matching_action(self, agent_db):
        # matcher 限定只拦 smalltalk;越界消息(out_of_scope)不受影响。
        hooks.register(_spec(
            "post_route", lambda ctx: HookResult(action="block", reason="gate"),
            matcher="^smalltalk$"))
        text_smalltalk, _ = _stream("你好")
        assert "超出" in text_smalltalk    # smalltalk 被拦成越界
        text_oos, _ = _stream("帮我选只股票")
        assert "超出" in text_oos          # 本来就是越界,正常走(未被 hook 影响)

    def test_run_end_fired_with_summary(self, agent_db):
        seen = []
        hooks.register(_spec("run_end",
                             lambda ctx: seen.append(ctx.payload["summary"])))
        _, done = _stream("你好")
        assert len(seen) == 1
        summary = seen[0]
        assert summary.status == "success"
        assert summary.conversation_id == done["conversation_id"]
        assert summary.llm_calls == 0      # 无 LLM key,确定性降级,零 LLM 调用

    def test_on_step_fired_for_each_trace_step(self, agent_db):
        steps = []
        hooks.register(_spec("on_step",
                             lambda ctx: steps.append(ctx.payload["step_type"])))
        _stream("你好")
        assert "extract_input" in steps
        assert "persist_state" in steps

    def test_post_response_sees_full_reply(self, agent_db):
        seen = []
        hooks.register(_spec("post_response",
                             lambda ctx: seen.append(ctx.payload["reply"])))
        text, _ = _stream("你好")
        assert seen == [text]              # hook 看到的 = 用户收到的全文

    def test_critical_hook_failure_fails_run_gracefully(self, agent_db):
        def boom(ctx):
            raise RuntimeError("boom")

        hooks.register(_spec("user_message", boom, critical=True))
        chunks = [json.loads(c) for c in planner.stream_chat("你好")]
        types = [c["type"] for c in chunks]
        assert "error" in types            # 走 error 分支
        assert types[-1] == "done"         # 但流正常收尾,不裸崩

    def test_noncritical_hook_failure_run_succeeds(self, agent_db):
        def boom(ctx):
            raise RuntimeError("boom")

        hooks.register(_spec("user_message", boom, critical=False))
        text, done = _stream("你好")
        assert "结合命理看" in text        # 完全不受影响
        assert done["type"] == "done"

    def test_blocked_message_preserves_session_birth_info(self, agent_db):
        # 先正常建立生辰,再 block 一条消息 → 会话生辰不能被冲掉。
        key = "hook-block-user"
        list(planner.stream_chat("1990年5月15日早上8点北京男，看事业",
                                 memory_key=key))
        hooks.register(_spec(
            "user_message", lambda ctx: HookResult(action="block", reason="x")))
        _, done = _stream("看看财运", memory_key=key)
        hooks.reset()
        # block 解除后,记忆里的生辰仍在,能直接咨询
        text, done2 = _stream("看看我的财运", memory_key=key)
        assert done2["state"]["needs_more_info"] is False
