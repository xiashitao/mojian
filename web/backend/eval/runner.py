"""Run a case through the REAL consultation pipeline and capture what we score.

Mirrors what `planner.stream_chat` does for a consult turn — minus persistence,
memory and history — so the reply is exactly what a fresh first-turn user gets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bazibase import solar_ganzhi_year

from web.backend.agent.models import ConversationState
from web.backend.agent.responder import stream_consultation_reply, _summarize_current_period
from web.backend.agent.tools import run_bazibase_tools
from web.backend.eval.cases import EvalCase

# The default 子平真诠 source basis the planner threads into the responder.
_SOURCE_BASIS = ConversationState().source_basis


@dataclass
class RunResult:
    case: EvalCase
    reply: str
    facts: dict[str, Any]              # the engine's authoritative facts (ground truth)
    grounding_violations: list[str]    # from the deterministic check_grounding
    reference_year: int


def engine_facts(tool_result: dict[str, Any]) -> dict[str, Any]:
    """The authoritative facts the judge scores fidelity against — including the
    explicit 相神/忌神 十神 (which the responder prompt only implies via 用神)."""
    chart = tool_result.get("chart") or {}
    diag = tool_result.get("diagnosis") or {}
    xs = diag.get("xiang_shen") or {}
    return {
        "日主": diag.get("day_master"),
        "日主五行": chart.get("day_master_element"),
        "身强弱": (chart.get("strength") or {}).get("verdict"),
        "格局": (diag.get("ge_ju") or {}).get("name"),
        "用神十神": (diag.get("yong_shen") or {}).get("ten_god"),
        "相神": [o.get("ten_god") for o in xs.get("xiang_shen", [])],
        "忌神": [o.get("ten_god") for o in xs.get("ji_shen", [])],
        "成败": (diag.get("cheng_bai") or {}).get("verdict"),
        # 当前大运/流年的事实(含 喜/忌/助用/增凶/平 角色标签) — 判忠诚度的关键。
        "当前大运流年": _summarize_current_period(chart.get("current_period")),
    }


def run_case(case: EvalCase, *, reference_year: int | None = None) -> RunResult:
    ref = reference_year if reference_year is not None else solar_ganzhi_year(datetime.now())
    tool_result = run_bazibase_tools(case.birth, reference_year=ref)

    parts: list[str] = []
    trace: dict[str, Any] | None = None
    for chunk, _state, gen_trace in stream_consultation_reply(
        case.topic, tool_result,
        source_basis=_SOURCE_BASIS,
        user_message=case.question,
        history=None,
        memory_notes=None,
        tone=None,
    ):
        if chunk:
            parts.append(chunk)
        if gen_trace is not None:
            trace = gen_trace

    return RunResult(
        case=case,
        reply="".join(parts),
        facts=engine_facts(tool_result),
        grounding_violations=list((trace or {}).get("grounding_violations", [])),
        reference_year=ref,
    )
