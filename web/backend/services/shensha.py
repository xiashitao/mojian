"""精选神煞 — presentation-only enrichment for the 专业细盘 grid.

Deliberately a WEB-LAYER service, NOT part of the `bazibase` engine: 神煞 is a
separate (神煞派) system, while the engine stays pure 子平真诠. These are shown in
the pro grid only — they never feed a judgment or the LLM.

Curated set (per product decision): 禄神 · 羊刃 · 天乙贵人 · 桃花 · 将星.
神煞 conventions vary by school/site; the anchors below are the common ones
(禄神/羊刃/天乙 by 日干; 桃花/将星 by 年支 or 日支 三合局).
"""
from __future__ import annotations

from bazibase import twelve_stage
from bazibase.constants import STEM_POLARITY

# 日干 → 天乙贵人 two 地支 (甲戊庚牛羊, 乙己鼠猴乡, 丙丁猪鸡位, 壬癸兔蛇藏, 六辛逢虎马).
_TIAN_YI = {
    "甲": "丑未", "戊": "丑未", "庚": "丑未",
    "乙": "子申", "己": "子申",
    "丙": "亥酉", "丁": "亥酉",
    "壬": "卯巳", "癸": "卯巳",
    "辛": "寅午",
}

# 三合局 → (桃花/咸池, 将星/旺神).
_TRINE_GROUPS: tuple[tuple[frozenset[str], str, str], ...] = (
    (frozenset("寅午戌"), "卯", "午"),
    (frozenset("申子辰"), "酉", "子"),
    (frozenset("巳酉丑"), "午", "酉"),
    (frozenset("亥卯未"), "子", "卯"),
)


def _peach_general(anchor_branch: str) -> tuple[str | None, str | None]:
    for group, peach, general in _TRINE_GROUPS:
        if anchor_branch in group:
            return peach, general
    return None, None


def pillar_shensha(
    day_stem: str, year_branch: str, day_branch: str, branch: str
) -> list[str]:
    """The curated 神煞 landing on `branch`, given the chart's 日干/年支/日支."""
    out: list[str] = []
    stage = twelve_stage(day_stem, branch)
    if stage == "临官":
        out.append("禄神")
    if STEM_POLARITY.get(day_stem) == 0 and stage == "帝旺":  # 阳干 only
        out.append("羊刃")
    if branch in _TIAN_YI.get(day_stem, ""):
        out.append("天乙贵人")

    peaches: set[str] = set()
    generals: set[str] = set()
    for anchor in (year_branch, day_branch):
        p, g = _peach_general(anchor)
        if p:
            peaches.add(p)
        if g:
            generals.add(g)
    if branch in peaches:
        out.append("桃花")
    if branch in generals:
        out.append("将星")
    return out
