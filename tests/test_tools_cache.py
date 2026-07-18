"""Bazibase tool-result caching by birth determinants (Cache pillar)."""
from web.backend.agent.models import BirthInfo
from web.backend.agent.tools import _TOOL_CACHE, run_bazibase_tools

BIRTH = BirthInfo(
    birth_date="1990-05-15", birth_time="08:00", longitude=116.4, gender="male"
)


def test_same_birth_served_from_cache():
    _TOOL_CACHE.clear()
    first = run_bazibase_tools(BIRTH)
    second = run_bazibase_tools(BIRTH)
    assert first is second  # computed once, reused on the follow-up turn


def test_different_birth_not_shared():
    _TOOL_CACHE.clear()
    first = run_bazibase_tools(BIRTH)
    other = BirthInfo(
        birth_date="1991-06-16", birth_time="09:30", longitude=121.5, gender="female"
    )
    assert first is not run_bazibase_tools(other)


def test_tool_span_emitted_with_cache_flag():
    """tool_call span:实算标 cached=False,缓存命中标 cached=True——
    与 llm_call 并列构成完整外部调用链。"""
    _TOOL_CACHE.clear()
    sink: list = []
    run_bazibase_tools(BIRTH, trace_sink=sink)
    run_bazibase_tools(BIRTH, trace_sink=sink)
    assert len(sink) == 2
    first, second = sink
    assert first.kind == "tool" and first.name == "tool.bazibase"
    assert first.step_type() == "tool_call"
    assert first.attributes["cached"] is False   # 第一次实算
    assert second.attributes["cached"] is True   # 第二次缓存命中


def test_no_sink_is_noop():
    _TOOL_CACHE.clear()
    run_bazibase_tools(BIRTH)  # 不传 sink 不报错(单测/eval 直调场景)
