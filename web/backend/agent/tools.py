"""Tool wrappers around deterministic bazibase APIs."""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any

from bazibase import cast_chart, diagnose, assess_pillar_fortune
from bazibase.arbitration import (
    ArbitrationParseError,
    ArbitrationResponse,
    ArbitrationResult,
    attach_response,
    parse_arbitration_response,
    prepare_arbitration,
)

from ..services.llm import LLMError, complete, is_configured
from .models import BirthInfo
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
) -> dict[str, Any]:
    """Chart casting + diagnosis + arbitration, cached by birth determinants.

    Args:
        birth_info: Complete birth information.
        reference_year: Consultation temporal anchor. When given, the chart
            resolves its active 大运 + 流年 at cast time (`current_period`), so
            those become the shared basis for all downstream judgments. The
            caller injects "now"; the engine never reads the clock.
    """
    if not birth_info.is_complete():
        raise ValueError(f"birth info incomplete: {birth_info.complete_missing_fields()}")

    key = _cache_key(birth_info, reference_year)
    cached = _TOOL_CACHE.get(key)
    if cached is not None:
        _TOOL_CACHE.move_to_end(key)
        return cached

    result = _compute_bazibase_tools(birth_info, reference_year)
    _TOOL_CACHE[key] = result
    _TOOL_CACHE.move_to_end(key)
    if len(_TOOL_CACHE) > _TOOL_CACHE_MAX:
        _TOOL_CACHE.popitem(last=False)
    return result


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
    _attach_period_fortune(chart, diagnosis, chart_dict)

    return {
        "chart": chart_dict,
        "diagnosis": diagnosis.to_dict(),
        "diagnosis_summary": diagnosis.summary(),
        "arbitration": _arbitration_to_dict(arbitration),
    }


def _attach_period_fortune(chart, diagnosis, chart_dict: dict[str, Any]) -> None:
    """Annotate the current 大运/流年 with a deterministic 喜忌 verdict.

    Derived from the chart's own 用神/格局 (子平真诠 论行运), so the responder
    has a grounded good/bad judgment instead of guessing.
    """
    cp = chart.current_period
    cp_dict = chart_dict.get("current_period")
    if cp is None or not cp_dict:
        return
    yong_tg = diagnosis.yong_shen.ten_god
    dm = chart.day_master
    cp_dict["liunian_fortune"] = assess_pillar_fortune(dm, yong_tg, cp.liunian).to_dict()
    if cp.luck_pillar is not None:
        cp_dict["luck_fortune"] = assess_pillar_fortune(
            dm, yong_tg, cp.luck_pillar.pillar
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

