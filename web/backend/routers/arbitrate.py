"""POST /api/arbitrate — DeepSeek LLM 仲裁."""
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from bazibase import cast_chart, diagnose
from bazibase.arbitration import (
    prepare_arbitration,
    parse_arbitration_response,
    attach_response,
    ArbitrationParseError,
    DEFAULT_CONFIDENCE_THRESHOLD,
)

from ..schemas import ArbitrateRequest
from ..services.enrich import enrich_chart
from ..services.deepseek import call_deepseek, DeepSeekAPIError

router = APIRouter()


def _parse_datetime(date_str: str, time_str: str) -> datetime:
    combined = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {combined!r}")


@router.post("/arbitrate")
def run_arbitration(req: ArbitrateRequest):
    """排盘 + 诊断 + LLM 仲裁。"""
    try:
        birth_time = _parse_datetime(req.date, req.time)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chart = cast_chart(
        birth_time=birth_time,
        longitude=req.longitude,
        gender=req.gender,
        tz_offset_hours=req.tz_offset_hours,
        apply_solar_time_correction=req.apply_solar_time_correction,
    )
    diag = diagnose(chart)
    result = prepare_arbitration(diag)

    if not result.has_cases():
        return {
            "chart": enrich_chart(chart.to_dict()),
            "diagnosis": diag.to_dict(),
            "arbitration": {
                "cases": [],
                "responses": {},
                "errors": {},
                "summary": {"total": 0, "resolved": 0, "unresolved": 0, "errors": 0},
            },
        }

    errors: dict[str, str] = {}

    for prompt in result.prompts:
        case = prompt.case
        try:
            raw = call_deepseek(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            )
        except DeepSeekAPIError as e:
            errors[case.case_id] = str(e)
            continue

        try:
            response = parse_arbitration_response(case, raw)
        except ArbitrationParseError as e:
            # Retry once with correction hint
            try:
                retry_prompt = (
                    f"你上次的回复无法解析为合法 JSON，请修正。\n"
                    f"上次回复片段: {raw[:200]}\n\n"
                    f"请重新回答以下问题，必须输出严格 JSON：\n\n{prompt.user_prompt}"
                )
                raw2 = call_deepseek(
                    system_prompt=prompt.system_prompt,
                    user_prompt=retry_prompt,
                )
                response = parse_arbitration_response(case, raw2)
            except (ArbitrationParseError, DeepSeekAPIError) as e2:
                errors[case.case_id] = f"Parse failed: {e2}"
                continue

        result = attach_response(result, case.case_id, response)

    # Build summary
    threshold = req.threshold or DEFAULT_CONFIDENCE_THRESHOLD
    resolved = sum(
        1 for r in result.responses.values()
        if not r.is_unresolved(threshold)
    )
    unresolved = sum(
        1 for r in result.responses.values()
        if r.is_unresolved(threshold)
    )

    return {
        "chart": enrich_chart(chart.to_dict()),
        "diagnosis": diag.to_dict(),
        "arbitration": {
            "cases": [
                {
                    "case_id": c.case_id,
                    "category": c.category,
                    "title": c.title,
                    "description": c.description,
                    "evidence": c.evidence,
                    "options": list(c.options),
                    "relevant_rules": list(c.relevant_rules),
                }
                for c in result.cases
            ],
            "responses": {
                cid: {
                    "decision": r.decision,
                    "reasoning": r.reasoning,
                    "confidence": r.confidence,
                    "cited_rules": list(r.cited_rules),
                    "raw_response": r.raw_response or "",
                    "is_unresolved": r.is_unresolved(threshold),
                }
                for cid, r in result.responses.items()
            },
            "errors": errors,
            "summary": {
                "total": len(result.cases),
                "resolved": resolved,
                "unresolved": unresolved,
                "errors": len(errors),
            },
        },
    }
