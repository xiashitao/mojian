"""Compact chart payload for the front-end 命盘 card (八字 + 大运 + 流年).

Curated from the full bazibase chart so the stream stays small; the full chart
still lives in the run trace for audit.
"""
from __future__ import annotations

from typing import Any

from .models import BirthInfo

_PILLAR_KEYS = ("year", "month", "day", "hour")
_POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时"}
# 相生顺序 — 木生火生土生金生水生木，so a left-to-right read shows 气势流通.
_ELEMENT_ORDER = ("木", "火", "土", "金", "水")


def _elements(chart: dict[str, Any]) -> list[dict[str, Any]]:
    """Five-element strength distribution, ordered along the 相生 cycle."""
    dist = chart.get("element_distribution") or {}
    return [
        {
            "el": el,
            "count": (dist.get(el) or {}).get("count", 0),
            "pct": (dist.get(el) or {}).get("percentage", 0),
        }
        for el in _ELEMENT_ORDER
    ]

# diagnosis interaction categories folded into the four 合/冲/刑/害 families.
_INTERACTION_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("合", ("gan_he", "san_he", "ban_he", "san_hui", "ban_hui")),
    ("冲", ("chong",)),
    ("刑", ("xing",)),
    ("害", ("hai",)),
)


def _interactions(raw: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten the diagnosis 刑冲合化 result into a compact, display-ready list."""
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for group, keys in _INTERACTION_GROUPS:
        for key in keys:
            for i in raw.get(key, []):
                out.append({
                    "group": group,
                    "kind": i.get("kind"),
                    "chars": i.get("elements", []),
                    "positions": [_POS_CN.get(p, p) for p in i.get("participants", [])],
                    "note": i.get("note") or "",
                })
    return out


def build_chart_card(
    chart: dict[str, Any],
    birth_info: BirthInfo,
    interactions: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "elements": _elements(chart),
        "interactions": _interactions(interactions),
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
