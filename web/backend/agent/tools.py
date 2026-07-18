"""Tool wrappers around deterministic bazibase APIs."""
from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime
from typing import Any

from bazibase import cast_chart, diagnose, assess_pillar_facts
from bazibase.pillars import _make_pillar
from bazibase.rules.fortune import ROLE_PLAIN
from bazibase.arbitration import (
    ArbitrationParseError,
    ArbitrationResponse,
    ArbitrationResult,
    attach_response,
    parse_arbitration_response,
    prepare_arbitration,
)

from ..services.llm import LLMError, complete, is_configured
from . import obs
from .models import BirthInfo
from .topics import all_key_ages
from ..services.enrich import enrich_chart


# A birth chart (and its diagnosis/arbitration) is deterministic in its inputs,
# yet every follow-up turn would otherwise re-cast it and re-run the arbitration
# LLM calls. Cache the whole tool result by the birth determinants (Cache pillar).
_TOOL_CACHE: "OrderedDict[tuple, dict[str, Any]]" = OrderedDict()
_TOOL_CACHE_MAX = 256

# 12 大运 × 10 years covers the full traditional life span; even with an early
# 起运 age this reaches past 120, so the 专业细盘 流年 table never runs short.
_LUCK_PILLAR_COUNT = 12


def _cache_key(birth_info: BirthInfo, reference_year: int | None) -> tuple:
    return (
        birth_info.birth_date,
        birth_info.birth_time,
        birth_info.longitude,
        birth_info.gender,
        birth_info.tz_offset_hours,
        birth_info.apply_solar_time_correction,
        reference_year,  # 大运/流年 anchor — different years must not share a cache slot
    )


def run_bazibase_tools(
    birth_info: BirthInfo,
    *,
    reference_year: int | None = None,
    trace_sink: obs.TraceSink | None = None,
) -> dict[str, Any]:
    """Chart casting + diagnosis + arbitration, cached by birth determinants.

    Args:
        birth_info: Complete birth information.
        reference_year: Consultation temporal anchor. When given, the chart
            resolves its active 大运 + 流年 at cast time (`current_period`), so
            those become the shared basis for all downstream judgments. The
            caller injects "now"; the engine never reads the clock.
        trace_sink: 传入则记一个 tool_call span(耗时 + 是否缓存命中),
            与 llm_call 并列构成完整的外部调用链。
    """
    if not birth_info.is_complete():
        raise ValueError(f"birth info incomplete: {birth_info.complete_missing_fields()}")

    started = time.monotonic()
    key = _cache_key(birth_info, reference_year)
    cached = _TOOL_CACHE.get(key)
    if cached is not None:
        _TOOL_CACHE.move_to_end(key)
        _emit_tool_span(trace_sink, started, cache_hit=True,
                        reference_year=reference_year)
        return cached

    result = _compute_bazibase_tools(birth_info, reference_year)
    _TOOL_CACHE[key] = result
    _TOOL_CACHE.move_to_end(key)
    if len(_TOOL_CACHE) > _TOOL_CACHE_MAX:
        _TOOL_CACHE.popitem(last=False)
    _emit_tool_span(trace_sink, started, cache_hit=False,
                    reference_year=reference_year)
    return result


def _emit_tool_span(trace_sink: obs.TraceSink | None, started: float,
                    *, cache_hit: bool, reference_year: int | None) -> None:
    obs.emit(trace_sink, obs.Span(
        kind="tool", name="tool.bazibase",
        latency_ms=int((time.monotonic() - started) * 1000),
        attributes={"cached": cache_hit, "reference_year": reference_year},
    ))


_STEMS = "甲乙丙丁戊己庚辛壬癸"
_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
# 关键人生节点：各话题 key_ages 的并集（topics.py）。刻意话题无关——timeline 进
# 「结构化分析结果」稳定前缀，若按话题裁剪，换话题即打穿工具缓存与提示词前缀缓存。
_KEY_NODE_AGES = all_key_ages()
_FUTURE_WINDOW = 7  # 近未来若干年的流年透视（覆盖"哪年好转/这几年"类问题）。


def _liunian_gz(year: int) -> str:
    return _STEMS[(year - 4) % 10] + _BRANCHES[(year - 4) % 12]


def _timeline_facts(chart, diagnosis, reference_year: int | None) -> list[dict[str, Any]]:
    """关键年份的流年事实（vs 命局 + 当时所在大运）——关键人生节点（过去）+ 近未来
    窗口。让 LLM 能锚定具体年份（如高考那年）做时段分析，而不必自行换算或猜测。"""
    dm = chart.day_master
    yong = diagnosis.yong_shen.ten_god
    natal = tuple(p.branch for p in chart.four_pillars)
    birth_year = chart.birth_clock_time.year
    years = {birth_year + a for a in _KEY_NODE_AGES}
    if reference_year:
        years.update(range(reference_year, reference_year + _FUTURE_WINDOW))

    out: list[dict[str, Any]] = []
    for y in sorted(years):
        if not (birth_year < y <= birth_year + 120):
            continue
        gz = _liunian_gz(y)
        liunian = _make_pillar(gz[0], gz[1], "luck")
        lp = next((p for p in chart.luck if p.start_year <= y <= p.end_year), None)
        facts = assess_pillar_facts(
            dm, yong, liunian, natal_branches=natal,
            luck_branch=lp.pillar.branch if lp else None,
        ).to_dict()
        out.append({
            "年份": y,
            "虚岁": y - birth_year + 1,
            "流年": gz,
            "所在大运": lp.pillar.stem_branch if lp else "未起运",
            "天干": f"{facts['stem']['ten_god']}（{ROLE_PLAIN.get(facts['stem']['role'], facts['stem']['role'])}）",
            "地支": (f"{facts['branch']['ten_god']}（{ROLE_PLAIN.get(facts['branch']['role'], facts['branch']['role'])}）"
                     if facts.get("branch") else None),
            "关系": facts.get("relations", []),
        })
    return out


def _compute_bazibase_tools(
    birth_info: BirthInfo,
    reference_year: int | None = None,
) -> dict[str, Any]:
    birth_time = _parse_birth_datetime(birth_info.birth_date, birth_info.birth_time)
    chart = cast_chart(
        birth_time=birth_time,
        longitude=float(birth_info.longitude),
        gender=str(birth_info.gender),
        tz_offset_hours=birth_info.tz_offset_hours,
        apply_solar_time_correction=birth_info.apply_solar_time_correction,
        luck_pillar_count=_LUCK_PILLAR_COUNT,
        reference_year=reference_year,
    )
    diagnosis = diagnose(chart)
    arbitration = prepare_arbitration(diagnosis)
    arbitration = _resolve_arbitration(arbitration)

    chart_dict = enrich_chart(chart.to_dict())
    _attach_period_facts(chart, diagnosis, chart_dict)

    return {
        "chart": chart_dict,
        "diagnosis": diagnosis.to_dict(),
        "diagnosis_summary": diagnosis.summary(),
        "arbitration": _arbitration_to_dict(arbitration),
        "timeline": _timeline_facts(chart, diagnosis, reference_year),
    }


def _attach_period_facts(chart, diagnosis, chart_dict: dict[str, Any]) -> None:
    """Annotate the current 大运/流年 with the engine's *deterministic facts*
    (十神 roles + 刑冲合会 relationships). No 吉凶 verdict — the responder LLM
    weighs 命局(体)+大运(路)+流年 into a 顺逆 read (确定交引擎、不确定交模型).
    The 流年 facts include its relationship to the running 大运 ("综合起来看").
    """
    cp = chart.current_period
    cp_dict = chart_dict.get("current_period")
    if cp is None or not cp_dict:
        return
    yong_tg = diagnosis.yong_shen.ten_god
    dm = chart.day_master
    natal_branches = tuple(p.branch for p in chart.four_pillars)
    luck_branch = cp.luck_pillar.pillar.branch if cp.luck_pillar is not None else None
    cp_dict["liunian_facts"] = assess_pillar_facts(
        dm, yong_tg, cp.liunian, natal_branches=natal_branches, luck_branch=luck_branch
    ).to_dict()
    if cp.luck_pillar is not None:
        cp_dict["luck_facts"] = assess_pillar_facts(
            dm, yong_tg, cp.luck_pillar.pillar, natal_branches=natal_branches
        ).to_dict()


def _resolve_arbitration(result: ArbitrationResult) -> ArbitrationResult:
    """Send each arbitration prompt to DeepSeek and parse responses."""
    if not is_configured() or not result.prompts:
        return result

    for prompt in result.prompts:
        try:
            raw = complete(
                prompt.system_prompt,
                prompt.user_prompt,
                temperature=0.0,
                timeout=120,  # flagship models (e.g. glm-5.2) can be slow
            )
            response = parse_arbitration_response(prompt.case, raw)
            result = attach_response(result, prompt.case.case_id, response)
        except (LLMError, ArbitrationParseError):
            fallback = ArbitrationResponse(
                case_id=prompt.case.case_id,
                decision="无法判定",
                reasoning="LLM 调用或解析失败",
                confidence=0.0,
                cited_rules=(),
                raw_response=None,
            )
            result = attach_response(result, prompt.case.case_id, fallback)
    return result


def _parse_birth_datetime(date: str | None, time: str | None) -> datetime:
    if not date or not time:
        raise ValueError("birth date/time missing")
    combined = f"{date} {time}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse birth datetime: {combined!r}")


def _arbitration_to_dict(result: ArbitrationResult) -> dict[str, Any]:
    resolved = 0
    unresolved = 0
    responses_dict: dict[str, Any] = {}

    for c in result.cases:
        r = result.responses.get(c.case_id)
        if r is not None:
            responses_dict[c.case_id] = {
                "decision": r.decision,
                "reasoning": r.reasoning,
                "confidence": r.confidence,
                "cited_rules": list(r.cited_rules),
                "raw_response": r.raw_response,
            }
            if r.is_unresolved():
                unresolved += 1
            else:
                resolved += 1
        else:
            unresolved += 1

    return {
        "cases": [
            {
                "case_id": c.case_id,
                "category": c.category,
                "title": c.title,
                "description": c.description,
                "evidence": c.evidence,
                "relevant_rules": list(c.relevant_rules),
                "options": list(c.options),
            }
            for c in result.cases
        ],
        "prompts": [
            {
                "case_id": p.case.case_id,
                "system_prompt": p.system_prompt,
                "user_prompt": p.user_prompt,
                "expected_schema": p.expected_schema,
            }
            for p in result.prompts
        ],
        "responses": responses_dict,
        "summary": {
            "total": len(result.cases),
            "resolved": resolved,
            "unresolved": unresolved,
            "errors": 0,
        },
    }

