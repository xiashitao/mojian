"""
bazibase.chart
==============

The Chart dataclass and the top-level `cast_chart` entry point.

A Chart ties together:
    - The original input parameters (for reproducibility)
    - The four pillars
    - The ten-god labels
    - The day-master strength assessment
    - The luck pillars (大运)

The Chart is a *fact layer*: every field is deterministic and
traceable. No interpretation, no 用神, no prediction. Those belong to
Layer 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from typing import Optional

from .solar_time import to_true_solar_time
from .dst import to_standard_time
from .pillars import FourPillars, compute_four_pillars, Pillar
from .luck import LuckInfo, compute_luck, LuckPillar
from .ten_gods import TenGodLabels, label_ten_gods, POSITION_CN, StemTenGod, HiddenStemTenGod
from .strength import StrengthAssessment, assess_strength
from .timeline import PeriodResolution, resolve_period


@dataclass(frozen=True)
class Chart:
    """A complete Ba Zi chart (Layer 1 — facts only)."""

    # --- Input provenance ---
    birth_clock_time: datetime          # the original wall-clock input
    longitude: float
    tz_offset_hours: float
    gender: str

    # --- Derived fields ---
    standard_clock_time: datetime       # birth_clock_time with DST undone
    dst_applied: bool                   # whether a DST hour was subtracted
    true_solar_time: datetime
    four_pillars: FourPillars
    ten_gods: TenGodLabels
    strength: StrengthAssessment
    luck: LuckInfo

    # --- Temporal anchor (resolved at cast time when a reference_year is given) ---
    # The canonical "current" 大运 + 流年 that all downstream period-specific
    # judgments share. None when the chart was cast without a reference_year
    # (a purely structural natal chart).
    current_period: Optional[PeriodResolution] = None

    # --- Convenience accessors ---
    @property
    def day_master(self) -> str:
        return self.four_pillars.day_master

    @property
    def year_pillar(self) -> Pillar:
        return self.four_pillars.year

    @property
    def month_pillar(self) -> Pillar:
        return self.four_pillars.month

    @property
    def day_pillar(self) -> Pillar:
        return self.four_pillars.day

    @property
    def hour_pillar(self) -> Pillar:
        return self.four_pillars.hour

    # --- Serialization ---
    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "input": {
                "birth_clock_time": self.birth_clock_time.isoformat(),
                "longitude": self.longitude,
                "tz_offset_hours": self.tz_offset_hours,
                "gender": self.gender,
            },
            "standard_clock_time": self.standard_clock_time.isoformat(),
            "dst_applied": self.dst_applied,
            "true_solar_time": self.true_solar_time.isoformat(),
            "day_master": self.day_master,
            "day_master_element": _stem_element(self.day_master),
            "four_pillars": _four_pillars_to_dict(self.four_pillars, self.ten_gods),
            "strength": {
                "total_score": self.strength.total_score,
                "verdict": self.strength.verdict,
                "borderline": self.strength.borderline,
                "breakdown": [
                    {"source": b.source, "contribution": b.contribution, "note": b.note}
                    for b in self.strength.breakdown
                ],
            },
            "luck": _luck_to_dict(self.luck),
            "current_period": (
                self.current_period.to_dict() if self.current_period else None
            ),
        }

    def summary(self) -> str:
        """One-line summary string."""
        fp = self.four_pillars
        return (
            f"{fp.year.stem_branch}年 "
            f"{fp.month.stem_branch}月 "
            f"{fp.day.stem_branch}日 "
            f"{fp.hour.stem_branch}时 "
            f"| 日主{self.day_master}({self.strength.verdict}) "
            f"| {'顺' if self.luck.direction > 0 else '逆'}运 "
            f"{self.luck.start_age_years}岁起运"
        )


def _stem_element(stem: str) -> str:
    from .constants import STEM_ELEMENT
    return STEM_ELEMENT[stem]


def _four_pillars_to_dict(fp: FourPillars, labels: TenGodLabels) -> dict:
    out = {}
    for pos in ("year", "month", "day", "hour"):
        p: Pillar = getattr(fp, pos)
        stem_label, hidden_labels = labels.at_position(pos)
        out[pos] = {
            "name_cn": POSITION_CN[pos],
            "stem_branch": p.stem_branch,
            "stem": {
                "char": p.stem,
                "ten_god": stem_label.ten_god,
            },
            "branch": {
                "char": p.branch,
                "hidden_stems": [
                    {
                        "char": h.stem,
                        "role": h.role,
                        "ten_god": h.ten_god,
                    }
                    for h in hidden_labels
                ],
            },
        }
    return out


def _luck_to_dict(luck: LuckInfo) -> dict:
    return {
        "direction": "顺" if luck.direction > 0 else "逆",
        "start_age": {
            "years": luck.start_age_years,
            "months": luck.start_age_months,
            "days": luck.start_age_days,
        },
        "start_solar": luck.start_solar.isoformat(),
        "pillars": [
            {
                "index": lp.index,
                "stem_branch": lp.pillar.stem_branch,
                "start_age": lp.start_age,
                "end_age": lp.end_age,
                "start_year": lp.start_year,
                "end_year": lp.end_year,
            }
            for lp in luck.luck_pillars
        ],
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def cast_chart(
    birth_time: datetime,
    longitude: float,
    gender: str,
    tz_offset_hours: float = 8.0,
    apply_solar_time_correction: bool = True,
    apply_dst_correction: bool = True,
    luck_pillar_count: int = 8,
    reference_year: int | None = None,
) -> Chart:
    """
    Cast a Ba Zi chart from a wall-clock birth time.

    Args:
        birth_time: Naive wall-clock datetime (timezone-unaware). This
            is the time as it would have appeared on a clock at the
            birth location in the zone given by `tz_offset_hours`.
        longitude: Birth location longitude in degrees (east positive).
            Used for true solar time correction. Beijing ≈ 116.4,
            Shanghai ≈ 121.5.
        gender: "male" or "female".
        tz_offset_hours: Timezone offset of `birth_time` from UTC.
            Default 8.0 for 中国标准时间 (北京时间).
        apply_solar_time_correction: If True (default), correct the
            clock time to true solar time before computing pillars.
            Set to False only if `birth_time` is already a true-solar-
            time datetime (rare).
        apply_dst_correction: If True (default), automatically undo China
            daylight-saving-time (1986–1991 summers) when `birth_time`
            falls inside a DST window — i.e. assume the reported time is
            the wall-clock reading that was actually showing (+1h). Set to
            False when the caller knows `birth_time` is already standard
            time (e.g. the user confirmed it). See `Chart.dst_applied`.
        luck_pillar_count: Number of 大运 to compute (default 8 ≈ 80yr).
        reference_year: Optional temporal anchor (a Gregorian/solar year). When
            given, the chart's active 大运 and that year's 流年 are resolved at
            cast time and attached as `Chart.current_period`, becoming the
            shared basis for all period-specific judgments. The engine never
            reads the system clock — the caller injects "now" explicitly, so
            the chart stays deterministic given its inputs.

    Returns:
        A Chart dataclass containing all derived fields.

    Example:
        >>> from datetime import datetime
        >>> from bazibase import cast_chart
        >>> c = cast_chart(
        ...     birth_time=datetime(1893, 12, 26, 8, 0),
        ...     longitude=112.9,        # 湖南湘潭
        ...     gender="male",
        ... )
        >>> c.summary()
        '癸巳年 甲子月 丁酉日 甲辰时 | 日主丁(身弱) | 逆运 6岁起运'
    """
    if gender not in ("male", "female"):
        raise ValueError(f"gender must be 'male' or 'female', got {gender!r}")
    if birth_time.tzinfo is not None:
        raise ValueError(
            "birth_time must be naive. Pass tz_offset_hours separately."
        )

    # Undo daylight saving time first: a wall clock inside a DST window reads
    # +1h, but 节气 tables and the true-solar-time correction both assume the
    # clock represents standard-zone time. Everything downstream works on the
    # DST-corrected standard time; the original input is preserved separately.
    if apply_dst_correction:
        standard_time, dst_applied = to_standard_time(birth_time)
    else:
        standard_time, dst_applied = birth_time, False

    if apply_solar_time_correction:
        tst = to_true_solar_time(standard_time, longitude, tz_offset_hours)
        tst_for_hour = tst
    else:
        tst = standard_time  # stored as-is; no solar correction applied
        tst_for_hour = None  # signal "use clock_time for day/hour too"

    fp = compute_four_pillars(clock_time=standard_time, true_solar_time=tst_for_hour)
    labels = label_ten_gods(fp)
    strength = assess_strength(fp)
    luck = compute_luck(
        standard_time,  # 起运 distance is measured against 节气 in standard time
        year_stem=fp.year.stem,
        gender=gender,
        count=luck_pillar_count,
    )

    chart = Chart(
        birth_clock_time=birth_time,
        longitude=longitude,
        tz_offset_hours=tz_offset_hours,
        gender=gender,
        standard_clock_time=standard_time,
        dst_applied=dst_applied,
        true_solar_time=tst,
        four_pillars=fp,
        ten_gods=labels,
        strength=strength,
        luck=luck,
    )

    # Resolve the temporal anchor (大运 + 流年) once, at cast time, so every
    # downstream judgment shares one consistent "current period".
    if reference_year is not None:
        chart = replace(chart, current_period=resolve_period(chart, reference_year))

    return chart


__all__ = ["Chart", "cast_chart"]
