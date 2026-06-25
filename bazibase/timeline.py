"""
bazibase.timeline
=================

Resolve the *内生之变* (endogenous change) layer for a given year: which 大运
a chart is in, the 流年 干支, and how both relate to the day master (十神).

This is the deterministic counterpart to era-context framing: the 易经 "变"
inside 命理 is modelled by 大运/流年, and it is *computed*, not searched. Given
a Chart (whose 大运 sequence is already fixed) plus a target Gregorian year,
this returns a reproducible PeriodResolution — the foundation for 运势 / 流年
features and for filling the agent's contextual `Judgment`.

Convention notes:

- 流年 干支 follows the 立春-based 干支纪年: `year` denotes the solar year that
  begins at 立春 of that year. Dates in early Jan/Feb *before* 立春 belong to
  the previous 干支 year — pass the solar year accordingly.
- Ages are 虚岁 (1 at birth), matching `luck.py`.
- 大运 spans are inclusive on both ends ([start_year, end_year]) and
  contiguous without overlap (each end_year is one less than the next
  start_year), so a year matches exactly one pillar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from lunar_python import Solar

from .constants import STEMS, BRANCHES, BRANCH_HIDDEN_STEMS, ten_god
from .pillars import Pillar
from .luck import LuckPillar

if TYPE_CHECKING:
    # Type-only import: avoids a runtime cycle with chart.py, which imports
    # resolve_period to attach a current period at cast time.
    from .chart import Chart


# Resolution status relative to the computed 大运 sequence.
STATUS_PRE_LUCK = "pre_luck"        # 运前 / 童限：still before the first 大运
STATUS_ACTIVE = "active"            # inside a computed 大运
STATUS_BEYOND_RANGE = "beyond_range"  # past the last computed 大运


@dataclass(frozen=True)
class PeriodResolution:
    """The active 大运 + 流年 for one year, with 十神 relative to the day master."""

    year: int
    status: str
    nominal_age: int                 # 虚岁 in that year

    # 流年 (always present)
    liunian: Pillar
    liunian_stem_ten_god: str
    liunian_branch_ten_god: str

    # 大运 (None when 运前 or beyond the computed range)
    luck_pillar: Optional[LuckPillar]
    luck_stem_ten_god: Optional[str]
    luck_branch_ten_god: Optional[str]

    def summary(self) -> str:
        dy = self.luck_pillar.pillar.stem_branch if self.luck_pillar else "（运前）"
        return (
            f"{self.year}年 {self.liunian.stem_branch}（流年）"
            f" | 大运 {dy}"
            f" | 虚岁{self.nominal_age}"
        )

    def to_dict(self) -> dict:
        luck = None
        if self.luck_pillar is not None:
            luck = {
                "stem_branch": self.luck_pillar.pillar.stem_branch,
                "index": self.luck_pillar.index,
                "start_year": self.luck_pillar.start_year,
                "end_year": self.luck_pillar.end_year,
                "start_age": self.luck_pillar.start_age,
                "end_age": self.luck_pillar.end_age,
                "stem_ten_god": self.luck_stem_ten_god,
                "branch_ten_god": self.luck_branch_ten_god,
            }
        return {
            "year": self.year,
            "status": self.status,
            "nominal_age": self.nominal_age,
            "liunian": {
                "stem_branch": self.liunian.stem_branch,
                "stem_ten_god": self.liunian_stem_ten_god,
                "branch_ten_god": self.liunian_branch_ten_god,
            },
            "luck_pillar": luck,
        }


def solar_ganzhi_year(dt: datetime) -> int:
    """The 立春-based 干支 year a real date belongs to.

    A calendar year and the 干支 year diverge between Jan 1 and 立春 (early
    Feb): a date in that window still belongs to the *previous* 干支 year.
    This returns the Gregorian year number `Y` such that `dt` falls in
    [立春 of Y, 立春 of Y+1) — the value to pass as `reference_year`.

    Uses `lunar_python`'s 立春-anchored year pillar (precise to the 节气
    instant) and maps it back to a year number. Since 立春 is always in early
    February, the answer is either `dt.year` or `dt.year - 1`.
    """
    year_ganzhi = (
        Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        .getLunar()
        .getEightChar()
        .getYear()
    )
    for candidate in (dt.year, dt.year - 1):
        if liunian_pillar(candidate).stem_branch == year_ganzhi:
            return candidate
    return dt.year  # unreachable in practice; calendar year as a safe fallback


def liunian_pillar(year: int) -> Pillar:
    """The 流年 干支 for a 立春-based solar year (deterministic, no calendar lookup)."""
    stem = STEMS[(year - 4) % 10]
    branch = BRANCHES[(year - 4) % 12]
    return Pillar(
        stem=stem,
        branch=branch,
        hidden_stems=BRANCH_HIDDEN_STEMS[branch],
        position="liunian",
    )


def _branch_main_ten_god(day_master: str, branch: str) -> str:
    """十神 of a branch's 本气 (primary hidden stem) relative to the day master."""
    hidden = BRANCH_HIDDEN_STEMS[branch]
    if not hidden:
        return ""
    return ten_god(day_master, hidden[0])


def _active_luck(chart: Chart, year: int) -> Optional[LuckPillar]:
    pillars = chart.luck.luck_pillars
    if not pillars:
        return None
    for lp in pillars:
        # Inclusive, contiguous, non-overlapping spans → exactly one match.
        if lp.start_year <= year <= lp.end_year:
            return lp
    return None


def resolve_period(chart: Chart, year: int) -> PeriodResolution:
    """
    Resolve the active 大运 and 流年 for `year` against a chart.

    Args:
        chart: A Chart from `cast_chart` (its 大运 sequence is already fixed).
        year: Target Gregorian/solar year (立春-based, see module docstring).

    Returns:
        PeriodResolution with 流年 always populated and 大运 populated when the
        year falls inside the computed sequence.
    """
    day_master = chart.day_master
    ln = liunian_pillar(year)
    ln_stem_tg = ten_god(day_master, ln.stem)
    ln_branch_tg = _branch_main_ten_god(day_master, ln.branch)

    nominal_age = year - chart.birth_clock_time.year + 1  # 虚岁

    active = _active_luck(chart, year)
    if active is None:
        pillars = chart.luck.luck_pillars
        if pillars and year < pillars[0].start_year:
            status = STATUS_PRE_LUCK
        else:
            status = STATUS_BEYOND_RANGE
        return PeriodResolution(
            year=year,
            status=status,
            nominal_age=nominal_age,
            liunian=ln,
            liunian_stem_ten_god=ln_stem_tg,
            liunian_branch_ten_god=ln_branch_tg,
            luck_pillar=None,
            luck_stem_ten_god=None,
            luck_branch_ten_god=None,
        )

    lp = active.pillar
    return PeriodResolution(
        year=year,
        status=STATUS_ACTIVE,
        nominal_age=nominal_age,
        liunian=ln,
        liunian_stem_ten_god=ln_stem_tg,
        liunian_branch_ten_god=ln_branch_tg,
        luck_pillar=active,
        luck_stem_ten_god=ten_god(day_master, lp.stem),
        luck_branch_ten_god=_branch_main_ten_god(day_master, lp.branch),
    )


__all__ = [
    "PeriodResolution",
    "STATUS_PRE_LUCK",
    "STATUS_ACTIVE",
    "STATUS_BEYOND_RANGE",
    "solar_ganzhi_year",
    "liunian_pillar",
    "resolve_period",
]
