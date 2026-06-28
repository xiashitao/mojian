"""Compact chart payload for the front-end 命盘 card (八字 + 大运 + 流年).

Curated from the full bazibase chart so the stream stays small; the full chart
still lives in the run trace for audit.
"""
from __future__ import annotations

from typing import Any

from bazibase import (
    ten_god as compute_ten_god,
    BRANCH_HIDDEN_STEMS,
    twelve_stage,
    liunian_pillar,
)

from .models import BirthInfo
from ..services.nayin import get_nayin
from ..services.kong_wang import get_kong_wang
from ..services.shensha import pillar_shensha

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
    anchors = _anchors(chart)
    luck_pillars = [
        {
            "stem_branch": lp.get("stem_branch"),
            "start_year": lp.get("start_year"),
            "end_year": lp.get("end_year"),
            "start_age": lp.get("start_age"),
            "end_age": lp.get("end_age"),
            "stem_ten_god": lp.get("stem_ten_god"),
            "branch_ten_god": lp.get("branch_ten_god"),
            # Full pro-grid columns for this 大运 and each of its 流年, so the
            # 专业细盘 can re-point its 流年/大运 columns on click — no round-trip.
            "column": _period_column(lp.get("stem_branch"), "大运", anchors),
            "years": _luck_year_columns(lp, anchors),
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
        # 专业细盘网格：流年 · 大运 · 年 · 月 · 日 · 时 并排成一张表。
        "columns": _pro_columns(chart, current),
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


def _anchors(chart: dict[str, Any]) -> tuple[str, str, str]:
    """(日干, 年支, 日支) — the keys 主星/星运/神煞 derive from. 桃花/将星 anchor on
    the 年支/日支."""
    four_pillars = chart.get("four_pillars", {})
    return (
        chart.get("day_master") or "",
        (four_pillars.get("year", {}).get("branch") or {}).get("char", ""),
        (four_pillars.get("day", {}).get("branch") or {}).get("char", ""),
    )


def _luck_year_columns(lp: dict[str, Any], anchors: tuple[str, str, str]) -> list[dict[str, Any]]:
    """Each 流年 in a 大运 span as {year, column}, for click-to-switch."""
    start = lp.get("start_year")
    end = lp.get("end_year")
    if start is None or end is None:
        return []
    out: list[dict[str, Any]] = []
    for y in range(int(start), int(end) + 1):
        out.append({
            "year": y,
            "column": _period_column(liunian_pillar(y).stem_branch, "流年", anchors),
        })
    return out


def _pro_columns(chart: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    """The 专业细盘 grid columns: 流年 · 大运 · 年 · 月 · 日 · 时, each a full pillar
    with 主星/天干/地支/藏干/纳音/空亡. 流年+大运 use the *current* period so the
    natal chart is read together with where the person stands now."""
    four_pillars = chart.get("four_pillars", {})
    anchors = _anchors(chart)
    columns: list[dict[str, Any]] = []

    # 流年 then 大运 (leftmost), so the present sits beside the natal four pillars.
    liunian_sb = (current.get("liunian") or {}).get("stem_branch")
    luck_sb = (current.get("luck_pillar") or {}).get("stem_branch")
    for sb, label in ((liunian_sb, "流年"), (luck_sb, "大运")):
        col = _period_column(sb, label, anchors)
        if col:
            columns.append(col)

    for key in _PILLAR_KEYS:
        if key in four_pillars:
            columns.append(_natal_column(four_pillars[key], anchors))
    return columns


def _hidden_stems(branch: str, day_master: str) -> list[dict[str, Any]]:
    return [
        {"char": h, "ten_god": compute_ten_god(day_master, h)}
        for h in BRANCH_HIDDEN_STEMS.get(branch, ())
    ]


def _period_column(
    stem_branch: str | None, label: str, anchors: tuple[str, str, str]
) -> dict[str, Any] | None:
    """Build a full column for a 大运/流年 干支 (not in the natal four pillars)."""
    if not stem_branch or len(stem_branch) < 2:
        return None
    day_master, year_branch, day_branch = anchors
    stem, branch = stem_branch[0], stem_branch[1]
    return {
        "label": label,
        "stem": stem,
        "stem_ten_god": compute_ten_god(day_master, stem),
        "branch": branch,
        "hidden": _hidden_stems(branch, day_master),
        "star_luck": twelve_stage(day_master, branch),  # 星运: 日主 on this branch
        "self_sit": twelve_stage(stem, branch),  # 自坐: this stem on its own branch
        "nayin": get_nayin(stem_branch),
        "void_branches": list(get_kong_wang(stem_branch)),
        "shensha": pillar_shensha(day_master, year_branch, day_branch, branch),
    }


def _natal_column(pillar: dict[str, Any], anchors: tuple[str, str, str]) -> dict[str, Any]:
    day_master, year_branch, day_branch = anchors
    stem = pillar.get("stem", {})
    branch = pillar.get("branch", {})
    stem_char = stem.get("char") or ""
    branch_char = branch.get("char") or ""
    return {
        "label": pillar.get("name_cn"),
        "stem": stem_char,
        "stem_ten_god": stem.get("ten_god"),
        "branch": branch_char,
        "hidden": [
            {"char": h.get("char"), "ten_god": h.get("ten_god"), "role": h.get("role")}
            for h in branch.get("hidden_stems", [])
        ],
        "star_luck": twelve_stage(day_master, branch_char),
        "self_sit": twelve_stage(stem_char, branch_char),
        "nayin": pillar.get("nayin"),
        "void_branches": pillar.get("void_branches") or [],
        "shensha": pillar_shensha(day_master, year_branch, day_branch, branch_char),
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
