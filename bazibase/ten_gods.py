"""
bazibase.ten_gods
=================

Ten-god (十神) labeling for every position in the chart.

For each pillar (year/month/day/hour), we label:
    - The stem itself (天干十神)
    - Each hidden stem inside the branch (地支藏干十神), with role
      annotated as 本气 / 中气 / 余气

The day stem (日主) gets the label "日主" rather than "比肩" — it's the
reference point, not another god in the chart.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .constants import ten_god
from .pillars import Pillar, FourPillars


HIDDEN_ROLE = Literal["本气", "中气", "余气"]
POSITION_NAMES = ("year", "month", "day", "hour")
POSITION_CN = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}


@dataclass(frozen=True)
class StemTenGod:
    """A ten-god label attached to a stem at a given position."""
    position: str          # "year" / "month" / "day" / "hour"
    stem: str
    ten_god: str           # e.g. "正官", "偏财", or "日主" for day stem


@dataclass(frozen=True)
class HiddenStemTenGod:
    """A ten-god label attached to a hidden stem inside a branch."""
    position: str          # "year" / "month" / "day" / "hour"
    branch: str
    stem: str
    role: str              # "本气" / "中气" / "余气"
    ten_god: str


@dataclass(frozen=True)
class TenGodLabels:
    """All ten-god labels for a chart."""
    stems: tuple[StemTenGod, ...]
    hidden_stems: tuple[HiddenStemTenGod, ...]

    def at_position(self, position: str) -> tuple[StemTenGod, tuple[HiddenStemTenGod, ...]]:
        """Return (stem_label, hidden_stem_labels) for the given pillar."""
        stem = next(s for s in self.stems if s.position == position)
        hidden = tuple(h for h in self.hidden_stems if h.position == position)
        return stem, hidden


_HIDDEN_ROLE_BY_INDEX = ("本气", "中气", "余气")


def label_ten_gods(fp: FourPillars) -> TenGodLabels:
    """
    Produce ten-god labels for all stems and hidden stems in the chart.

    Args:
        fp: A FourPillars object from `pillars.compute_four_pillars`.

    Returns:
        TenGodLabels with all stem and hidden-stem labels.

    Example (excerpt for 毛泽东's chart 癸巳/甲子/丁酉/甲辰, day master 丁):
        Year stem  癸 → 七杀
        Year 巳 hidden: 丙(劫财) 庚(正财) 戊(伤官)
        Month stem 甲 → 正印
        ...
        Day stem 丁 → 日主
        ...
    """
    dm = fp.day_master
    stems: list[StemTenGod] = []
    hidden: list[HiddenStemTenGod] = []

    for pos_name in POSITION_NAMES:
        pillar: Pillar = getattr(fp, pos_name)
        if pos_name == "day":
            label = "日主"
        else:
            label = ten_god(dm, pillar.stem)
        stems.append(StemTenGod(position=pos_name, stem=pillar.stem, ten_god=label))

        for i, hs in enumerate(pillar.hidden_stems):
            role = _HIDDEN_ROLE_BY_INDEX[i] if i < len(_HIDDEN_ROLE_BY_INDEX) else f"杂气{i}"
            tg = ten_god(dm, hs)
            hidden.append(HiddenStemTenGod(
                position=pos_name,
                branch=pillar.branch,
                stem=hs,
                role=role,
                ten_god=tg,
            ))

    return TenGodLabels(stems=tuple(stems), hidden_stems=tuple(hidden))


__all__ = [
    "StemTenGod",
    "HiddenStemTenGod",
    "TenGodLabels",
    "label_ten_gods",
    "POSITION_NAMES",
    "POSITION_CN",
]
