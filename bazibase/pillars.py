"""
bazibase.pillars
================

Four-pillar (四柱) computation: year, month, day, hour.

This module wraps `lunar_python` for the astronomical hard parts (节气
timing, lunar conversion, 60-甲子 day cycle) and exposes a clean
dataclass-based API. The library handles:

- 立春 boundary for year pillars
- 节 (not 中气) boundary for month pillars
- 60-甲子 cycle for day pillars

The hour pillar is computed in two steps:
    1. Hour BRANCH is derived from the true solar time (so that births
       at longitudes far from the standard meridian get the right
       sun-position-based hour branch).
    2. Hour STEM is derived from the day stem via 五鼠遁
       (甲己起甲子, 乙庚起丙子, ...).

Convention for the 子时 boundary (23:00–01:00):

    We follow the "day-boundary at 00:00" school. A birth at 23:30 on
    day X keeps day X's pillar; its hour is 子, with the stem derived
    from day X's stem. This is `lunar_python`'s default behaviour and
    matches the most common modern convention.

True solar time scope:

    - Year & month pillars use the standard-zone clock time, because 节气
      boundaries are absolute astronomical instants whose published times
      are in standard zone time (北京时间 for China).
    - Day & hour pillars use the true solar time, because which 干支 day a
      birth belongs to (including the 子时 midnight rollover) and which
      时辰 it falls in are both *solar-position* questions about the birth
      longitude. Deriving them from the same true-solar base keeps 日柱 and
      时柱 internally consistent: a far-western birth just after midnight
      whose true solar time is still the previous evening gets the previous
      solar day's 日柱 *and* a matching 时柱, instead of a desynced pair.

    If no true solar time is supplied, day & hour fall back to the clock
    time (i.e. no correction).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from lunar_python import Solar

from .constants import (
    BRANCH_HIDDEN_STEMS,
    STEMS,
    STEM_INDEX,
    STEM_POLARITY,
    STEM_ELEMENT,
    BRANCH_INDEX,
    BRANCH_HOUR_RANGE,
    WU_SHU_DUN,
)


@dataclass(frozen=True)
class Pillar:
    """
    A single 柱 (pillar): one stem + one branch.

    Examples: 甲子, 丙寅, 癸亥.

    Attributes:
        stem: Single-char heavenly stem (e.g. "甲").
        branch: Single-char earthly branch (e.g. "子").
        hidden_stems: Tuple of hidden stems in this branch, in order
            本气 → 中气 → 余气. Length 1–3 depending on the branch.
        position: Which pillar position — "year", "month", "day", or
            "hour". Purely informational.
    """
    stem: str
    branch: str
    hidden_stems: tuple[str, ...] = ()
    position: str = ""

    @property
    def stem_branch(self) -> str:
        """Combined representation like '甲子'."""
        return f"{self.stem}{self.branch}"

    @property
    def stem_element(self) -> str:
        return STEM_ELEMENT[self.stem]

    @property
    def branch_element(self) -> str:
        from .constants import BRANCH_ELEMENT
        return BRANCH_ELEMENT[self.branch]

    @property
    def stem_polarity(self) -> int:
        return STEM_POLARITY[self.stem]

    def __str__(self) -> str:
        return self.stem_branch


@dataclass(frozen=True)
class FourPillars:
    """The complete four-pillar chart."""
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar

    @property
    def day_master(self) -> str:
        """The day stem (日主) — the central reference for the whole chart."""
        return self.day.stem

    def as_list(self) -> list[Pillar]:
        return [self.year, self.month, self.day, self.hour]

    def __iter__(self):
        return iter(self.as_list())


def _make_pillar(stem: str, branch: str, position: str) -> Pillar:
    """Build a Pillar with hidden stems filled in from the branch."""
    if branch not in BRANCH_HIDDEN_STEMS:
        raise KeyError(f"No hidden-stem table for branch {branch!r}")
    return Pillar(
        stem=stem,
        branch=branch,
        hidden_stems=BRANCH_HIDDEN_STEMS[branch],
        position=position,
    )


def _hour_branch_from_time(t: datetime) -> str:
    """
    Determine the hour branch (时支) from a given datetime.

    The 子 branch spans 23:00–01:00 across midnight; all others span
    a contiguous 2-hour block. See BRANCH_HOUR_RANGE for the table.

    Args:
        t: Naive datetime (typically the true solar time).

    Returns:
        Single-char branch name like "子", "丑", etc.
    """
    h = t.hour
    # 子时 is special: it spans 23:00–01:00.
    if h == 23 or h == 0:
        return "子"
    # All others: find the branch whose range contains h.
    for branch, (start, end) in BRANCH_HOUR_RANGE.items():
        if branch == "子":
            continue
        if start <= h < end:
            return branch
    # Should be unreachable.
    raise RuntimeError(f"Could not determine hour branch for hour={h}")


def _hour_stem_from_day_stem(day_stem: str, hour_branch: str) -> str:
    """
    Derive the hour stem (时干) from the day stem via 五鼠遁.

    Rule:
        甲己日 → 子时起甲
        乙庚日 → 子时起丙
        丙辛日 → 子时起戊
        丁壬日 → 子时起庚
        戊癸日 → 子时起壬

    Then advance one stem per branch, following the branch order.

    Args:
        day_stem: Single-char day stem.
        hour_branch: Single-char hour branch.

    Returns:
        Single-char hour stem.
    """
    if day_stem not in WU_SHU_DUN:
        raise ValueError(f"Invalid day stem for 五鼠遁: {day_stem!r}")
    if hour_branch not in BRANCH_INDEX:
        raise ValueError(f"Invalid hour branch: {hour_branch!r}")

    start_stem_idx = WU_SHU_DUN[day_stem]
    # Branch advancement: 子=0, 丑=1, ..., 亥=11.
    branch_offset = BRANCH_INDEX[hour_branch]
    hour_stem_idx = (start_stem_idx + branch_offset) % 10
    return STEMS[hour_stem_idx]


def compute_four_pillars(
    clock_time: datetime,
    true_solar_time: Optional[datetime] = None,
) -> FourPillars:
    """
    Compute the four pillars.

    Args:
        clock_time: Naive wall-clock datetime (timezone-unaware). Used
            for year/month/day pillar computation against 节气 instants.
        true_solar_time: Optional naive datetime representing the local
            true solar time at the birth location. If provided, the
            hour BRANCH is derived from this (sun-position-based). If
            None, the hour branch falls back to `clock_time`.

    Returns:
        FourPillars dataclass.

    Design note:
        We deliberately split time into two inputs because year/month/day
        boundaries are absolute astronomical events (crossing 节气) that
        should be compared to the standard-zone clock time, while the
        hour branch is a local sun-position question that requires
        true solar time at the birth longitude.
    """
    if clock_time.tzinfo is not None:
        raise ValueError(
            "clock_time must be naive. Pass tz_offset_hours separately."
        )
    if true_solar_time is not None and true_solar_time.tzinfo is not None:
        raise ValueError(
            "true_solar_time must be naive. Apply timezone offset before "
            "calling to_true_solar_time, not via tzinfo."
        )

    # Year & month from the standard-zone clock time (节气 boundaries are
    # absolute astronomical instants published in 北京时间).
    solar_clock = Solar.fromYmdHms(
        clock_time.year,
        clock_time.month,
        clock_time.day,
        clock_time.hour,
        clock_time.minute,
        clock_time.second,
    )
    ec_clock = solar_clock.getLunar().getEightChar()
    year_p = _make_pillar(ec_clock.getYearGan(), ec_clock.getYearZhi(), "year")
    month_p = _make_pillar(ec_clock.getMonthGan(), ec_clock.getMonthZhi(), "month")

    # Day & hour from the true solar time (or clock time as fallback): the
    # 干支 day and the 时辰 are both solar-position questions, so they share
    # one time base to stay internally consistent across the midnight 子时.
    solar_src = true_solar_time if true_solar_time is not None else clock_time
    solar_day = Solar.fromYmdHms(
        solar_src.year,
        solar_src.month,
        solar_src.day,
        solar_src.hour,
        solar_src.minute,
        solar_src.second,
    )
    ec_day = solar_day.getLunar().getEightChar()
    day_p = _make_pillar(ec_day.getDayGan(), ec_day.getDayZhi(), "day")

    # Hour: branch from the solar time, stem via 五鼠遁 from the (matching) day stem.
    hour_branch = _hour_branch_from_time(solar_src)
    hour_stem = _hour_stem_from_day_stem(day_p.stem, hour_branch)
    hour_p = _make_pillar(hour_stem, hour_branch, "hour")

    return FourPillars(year=year_p, month=month_p, day=day_p, hour=hour_p)


__all__ = [
    "Pillar",
    "FourPillars",
    "compute_four_pillars",
    "_hour_branch_from_time",
    "_hour_stem_from_day_stem",
]
