"""
bazibase.strength
=================

Day-master strength assessment (日主旺衰).

This module implements a transparent, score-based heuristic for
classifying the day master as 身强 (strong) or 身弱 (weak). It is NOT
the final word — real 弱强 analysis in 子平派 requires looking at
用神选取、相神配合、刑冲合化 etc. But this heuristic captures the
three classical channels:

    1. 得令 (seasonal):   Is the day master supported by 月令?
    2. 得地 (rooted):     Does it have roots in any branch hidden stem?
    3. 得势 (assisted):   Do the other 天干 produce or match it?

Score weights (tunable but documented):
    月令本气 = 4       月令中气 = 2       月令余气 = 1
    通根本气 = 2       通根中气 = 1       通根余气 = 0.5
    天干同/印 = 1 each

Threshold: total >= 5 → 身强 (strong); else 身弱 (weak).
This threshold is calibrated so a chart with 得令 alone is borderline.

Caveat: borderline cases (score 4–6) are genuinely ambiguous; the
caller should treat the verdict as provisional.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .constants import (
    STEM_ELEMENT,
    ELEMENT_PRODUCTION,
    BRANCH_HIDDEN_STEMS,
)
from .pillars import FourPillars
from .ten_gods import TenGodLabels


MONTH_WEIGHT = (4.0, 2.0, 1.0)   # 本气 / 中气 / 余气
ROOT_WEIGHT = (2.0, 1.0, 0.5)
STEM_SUPPORT_WEIGHT = 1.0
STRONG_THRESHOLD = 5.0


@dataclass(frozen=True)
class StrengthBreakdown:
    """Itemised strength contributions for transparency."""
    source: str        # e.g. "月令本气 丙"
    contribution: float
    note: str          # human-readable explanation


@dataclass(frozen=True)
class StrengthAssessment:
    """Full strength assessment result."""
    total_score: float
    is_strong: bool
    verdict: str                  # "身强" / "身弱"
    breakdown: tuple[StrengthBreakdown, ...]
    borderline: bool              # True if within ±1.0 of threshold


def _element_supports(supporter_el: str, dm_el: str) -> bool:
    """True if supporter_el produces or matches dm_el."""
    if supporter_el == dm_el:
        return True
    if ELEMENT_PRODUCTION.get(supporter_el) == dm_el:
        return True
    return False


def assess_strength(fp: FourPillars) -> StrengthAssessment:
    """
    Assess day-master strength by scoring 得令 / 得地 / 得势.

    Args:
        fp: FourPillars object.

    Returns:
        StrengthAssessment with total score, verdict, and a detailed
        breakdown so the user can audit each contribution.
    """
    dm = fp.day_master
    dm_el = STEM_ELEMENT[dm]
    breakdown: list[StrengthBreakdown] = []
    total = 0.0

    # ----- 1. 得令: month branch hidden stems -----
    # 月令 has the heaviest weight because it's the dominant qi of the season.
    month_hidden = fp.month.hidden_stems
    for i, hs in enumerate(month_hidden):
        hs_el = STEM_ELEMENT[hs]
        if _element_supports(hs_el, dm_el):
            weight = MONTH_WEIGHT[i] if i < len(MONTH_WEIGHT) else 0.0
            rel = "同我" if hs_el == dm_el else "生我"
            breakdown.append(StrengthBreakdown(
                source=f"月令{'本中余'[i] if i < 3 else '?'}气 {hs}",
                contribution=weight,
                note=f"月令{rel} ({hs_el} → {dm_el})",
            ))
            total += weight

    # ----- 2. 得地: roots in any branch (excluding month counted above) -----
    # We do count roots in the month branch too, but with the smaller
    # 通根 weight to avoid double-counting. Since the month contribution
    # above already used 月令 weight, we skip the month branch here.
    for pos in ("year", "day", "hour"):
        pillar = getattr(fp, pos)
        for i, hs in enumerate(pillar.hidden_stems):
            if STEM_ELEMENT[hs] == dm_el:
                weight = ROOT_WEIGHT[i] if i < len(ROOT_WEIGHT) else 0.0
                breakdown.append(StrengthBreakdown(
                    source=f"{pos}柱{pillar.branch}藏 {hs}",
                    contribution=weight,
                    note=f"通根 ({hs}与日主同属{dm_el})",
                ))
                total += weight

    # ----- 3. 得势: 天干 same element or producer (excluding day stem itself) -----
    for pos in ("year", "month", "hour"):
        pillar = getattr(fp, pos)
        stem = pillar.stem
        stem_el = STEM_ELEMENT[stem]
        if _element_supports(stem_el, dm_el):
            rel = "同我" if stem_el == dm_el else "生我"
            breakdown.append(StrengthBreakdown(
                source=f"{pos}干 {stem}",
                contribution=STEM_SUPPORT_WEIGHT,
                note=f"透干{rel} ({stem_el} → {dm_el})",
            ))
            total += STEM_SUPPORT_WEIGHT

    is_strong = total >= STRONG_THRESHOLD
    verdict = "身强" if is_strong else "身弱"
    borderline = abs(total - STRONG_THRESHOLD) <= 1.0

    return StrengthAssessment(
        total_score=total,
        is_strong=is_strong,
        verdict=verdict,
        breakdown=tuple(breakdown),
        borderline=borderline,
    )


__all__ = [
    "StrengthBreakdown",
    "StrengthAssessment",
    "assess_strength",
    "MONTH_WEIGHT",
    "ROOT_WEIGHT",
    "STEM_SUPPORT_WEIGHT",
    "STRONG_THRESHOLD",
]
