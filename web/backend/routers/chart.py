"""POST /api/chart — cast chart + diagnose."""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from bazibase import cast_chart, diagnose

from ..schemas import ChartRequest
from ..services.enrich import enrich_chart

router = APIRouter()


def _parse_datetime(date_str: str, time_str: str) -> datetime:
    combined = f"{date_str} {time_str}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {combined!r}")


@router.post("/chart")
def cast_and_diagnose(req: ChartRequest):
    """排盘 + 诊断。返回 chart + diagnosis + enrichment。"""
    try:
        birth_time = _parse_datetime(req.date, req.time)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        chart = cast_chart(
            birth_time=birth_time,
            longitude=req.longitude,
            gender=req.gender,
            tz_offset_hours=req.tz_offset_hours,
            apply_solar_time_correction=req.apply_solar_time_correction,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"排盘失败: {e}")

    diag = diagnose(chart)

    chart_dict = chart.to_dict()
    diag_dict = diag.to_dict()

    # Enrich with nayin, kong_wang, liuqin, element distribution
    chart_dict = enrich_chart(chart_dict)

    return {
        "chart": chart_dict,
        "diagnosis": diag_dict,
    }
