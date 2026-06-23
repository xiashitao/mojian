"""Tool wrappers around deterministic bazibase APIs."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from bazibase import cast_chart, diagnose
from bazibase.arbitration import prepare_arbitration

from .models import BirthInfo
from ..services.enrich import enrich_chart


def run_bazibase_tools(birth_info: BirthInfo) -> dict[str, Any]:
    """Run chart casting, diagnosis, and arbitration preparation."""
    if not birth_info.is_complete():
        raise ValueError(f"birth info incomplete: {birth_info.complete_missing_fields()}")

    birth_time = _parse_birth_datetime(birth_info.birth_date, birth_info.birth_time)
    chart = cast_chart(
        birth_time=birth_time,
        longitude=float(birth_info.longitude),
        gender=str(birth_info.gender),
        tz_offset_hours=birth_info.tz_offset_hours,
        apply_solar_time_correction=birth_info.apply_solar_time_correction,
    )
    diagnosis = diagnose(chart)
    arbitration = prepare_arbitration(diagnosis)

    return {
        "chart": enrich_chart(chart.to_dict()),
        "diagnosis": diagnosis.to_dict(),
        "diagnosis_summary": diagnosis.summary(),
        "arbitration": _arbitration_to_dict(arbitration),
    }


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


def _arbitration_to_dict(result) -> dict[str, Any]:
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
        "responses": {},
        "summary": {
            "total": len(result.cases),
            "resolved": 0,
            "unresolved": len(result.cases),
            "errors": 0,
        },
    }

