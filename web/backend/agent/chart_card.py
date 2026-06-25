"""Compact chart payload for the front-end 命盘 card (八字 + 大运 + 流年).

Curated from the full bazibase chart so the stream stays small; the full chart
still lives in the run trace for audit.
"""
from __future__ import annotations

from typing import Any

from .models import BirthInfo

_PILLAR_KEYS = ("year", "month", "day", "hour")


def build_chart_card(chart: dict[str, Any], birth_info: BirthInfo) -> dict[str, Any]:
    four_pillars = chart.get("four_pillars", {})
    pillars = [
        _pillar(four_pillars[key])
        for key in _PILLAR_KEYS
        if key in four_pillars
    ]

    luck = chart.get("luck") or {}
    luck_pillars = [
        {
            "stem_branch": lp.get("stem_branch"),
            "start_year": lp.get("start_year"),
            "end_year": lp.get("end_year"),
            "start_age": lp.get("start_age"),
            "end_age": lp.get("end_age"),
            "stem_ten_god": lp.get("stem_ten_god"),
            "branch_ten_god": lp.get("branch_ten_god"),
        }
        for lp in luck.get("pillars", [])
    ]

    current = chart.get("current_period") or {}
    current_card = None
    if current:
        liunian = current.get("liunian") or {}
        luck_pillar = current.get("luck_pillar") or {}
        current_card = {
            "year": current.get("year"),
            "nominal_age": current.get("nominal_age"),
            "liunian": liunian.get("stem_branch"),
            "liunian_stem_ten_god": liunian.get("stem_ten_god"),
            "liunian_branch_ten_god": liunian.get("branch_ten_god"),
            "luck_index": luck_pillar.get("index"),
            "luck_stem_branch": luck_pillar.get("stem_branch"),
        }

    return {
        "day_master": chart.get("day_master"),
        "day_master_element": chart.get("day_master_element"),
        "pillars": pillars,
        "luck": {"direction": luck.get("direction"), "pillars": luck_pillars},
        "current": current_card,
        "birth": {
            "date": birth_info.birth_date,
            "time": birth_info.birth_time,
            "place": birth_info.birth_place,
            "gender": birth_info.gender,
        },
    }


def _pillar(pillar: dict[str, Any]) -> dict[str, Any]:
    stem = pillar.get("stem", {})
    branch = pillar.get("branch", {})
    return {
        "label": pillar.get("name_cn"),
        "stem": stem.get("char"),
        "stem_ten_god": stem.get("ten_god"),
        "branch": branch.get("char"),
        "branch_ten_god": branch.get("ten_god"),
        "hidden": [
            {"char": h.get("char"), "ten_god": h.get("ten_god"), "role": h.get("role")}
            for h in branch.get("hidden_stems", [])
        ],
        "nayin": pillar.get("nayin"),
    }
