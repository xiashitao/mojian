"""
bazibase.dst
============

China daylight saving time (夏令时) correction.

Wall-clock birth times that fall inside China's nationwide DST windows read
one hour **ahead** of 北京标准时 (UTC+8 standard). Ba Zi computation needs
standard time — 节气 boundaries are published in standard time, and the
true-solar-time correction assumes the clock represents standard-zone time.
So we undo the DST offset *before* any pillar / solar-time work.

History (nationwide, 国务院):

    1986–1991, clocks advanced +1h from a Sunday in April (1986: May) to a
    Sunday in September. The transition happened at 02:00 local time:
    spring-forward 02:00 → 03:00, autumn fall-back 02:00 → 01:00.

Earlier scattered DST (1935–1951, regional, Republic / early-PRC) is not
encoded here — those records are inconsistent and the affected population in
this product is negligible. Add periods to `CHINA_DST_PERIODS` if needed.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta


# Each entry: (start_date, end_date). DST is active from `start_date` 02:00
# wall-time up to (but not including) `end_date` 02:00 wall-time. During an
# active window the wall clock reads +1h relative to 北京标准时.
# Source: 国务院 1986–1991 全国夏令时实施日期.
CHINA_DST_PERIODS: tuple[tuple[date, date], ...] = (
    (date(1986, 5, 4), date(1986, 9, 14)),
    (date(1987, 4, 12), date(1987, 9, 13)),
    (date(1988, 4, 10), date(1988, 9, 11)),
    (date(1989, 4, 16), date(1989, 9, 17)),
    (date(1990, 4, 15), date(1990, 9, 16)),
    (date(1991, 4, 14), date(1991, 9, 15)),
)

# Clocks shift at 02:00 wall-time on the boundary dates.
DST_TRANSITION_HOUR = 2


def is_china_dst(
    clock_time: datetime,
    periods: tuple[tuple[date, date], ...] = CHINA_DST_PERIODS,
) -> bool:
    """
    Whether a naive wall-clock datetime falls inside a China DST window.

    On the start date DST begins at 02:00 (the 02:00–02:59 hour does not
    exist); on the end date DST ends at 02:00 (the 01:00–01:59 hour repeats,
    and we treat the wall reading before 02:00 as still being DST).
    """
    d = clock_time.date()
    h = clock_time.hour
    for start, end in periods:
        if d == start:
            return h >= DST_TRANSITION_HOUR
        if d == end:
            return h < DST_TRANSITION_HOUR
        if start < d < end:
            return True
    return False


def to_standard_time(
    clock_time: datetime,
    periods: tuple[tuple[date, date], ...] = CHINA_DST_PERIODS,
) -> tuple[datetime, bool]:
    """
    Convert a wall-clock datetime to 北京标准时, undoing DST when active.

    Args:
        clock_time: Naive wall-clock datetime (the time shown on the wall).
        periods: DST windows to apply. Defaults to China 1986–1991.

    Returns:
        (standard_time, dst_applied). When no DST window matches,
        `standard_time` is `clock_time` unchanged and `dst_applied` is False.
    """
    if is_china_dst(clock_time, periods):
        return clock_time - timedelta(hours=1), True
    return clock_time, False


__all__ = [
    "CHINA_DST_PERIODS",
    "DST_TRANSITION_HOUR",
    "is_china_dst",
    "to_standard_time",
]
