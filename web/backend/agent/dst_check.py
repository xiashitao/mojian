"""
Daylight-saving-time disambiguation for the chat agent.

Births during China's 1986–1991 DST summers carry a real *source* ambiguity
that the deterministic engine cannot resolve on its own: when a user says
"早上8点", we cannot know whether that 8 o'clock was the wall-clock reading
that was actually showing during DST (one hour ahead of standard time) or a
value someone already converted back to standard time.

The engine defaults to "assume the reported time is the DST wall clock"
(`cast_chart(apply_dst_correction=True)`). This module lets the agent layer
decide whether that assumption is worth a clarifying question — and it only
is when the ±1h would actually move the birth into a different 时辰. If both
interpretations land in the same hour branch, the answer doesn't change the
chart, so we proceed silently and keep the conversation low-friction.

This module is intentionally stateless and free of planner/router coupling:
call `analyze_dst(birth_info)`; if it returns a result with
`needs_confirmation=True`, surface `question` / `options` to the user before
casting. The user's answer maps to `apply_dst_correction` (True = "it was
the DST wall clock", False = "it was already standard time").
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from bazibase import cast_chart, is_china_dst
from .models import BirthInfo


_DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


class DstAnalysis(BaseModel):
    """Outcome of checking a birth time against China DST windows."""

    in_dst_window: bool
    # True only when the DST ±1h changes the 时辰 — i.e. worth asking.
    needs_confirmation: bool
    hour_branch_as_dst: Optional[str] = None   # 时支 if reported time is DST wall clock
    hour_branch_as_standard: Optional[str] = None  # 时支 if reported time is standard
    question: Optional[str] = None
    options: list[str] = []


# User-facing answers, mapped to the engine's `apply_dst_correction` flag.
OPTION_WAS_DST_CLOCK = "那时钟表上就是这个点"
OPTION_ALREADY_STANDARD = "已经是标准时间了"


def _parse_birth_datetime(date: str | None, time: str | None) -> datetime | None:
    if not date or not time:
        return None
    combined = f"{date} {time}"
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    return None


def _hour_branch(birth_time: datetime, birth_info: BirthInfo, *, apply_dst: bool) -> str:
    chart = cast_chart(
        birth_time=birth_time,
        longitude=float(birth_info.longitude),
        gender=str(birth_info.gender or "male"),
        tz_offset_hours=birth_info.tz_offset_hours,
        apply_solar_time_correction=birth_info.apply_solar_time_correction,
        apply_dst_correction=apply_dst,
    )
    return chart.hour_pillar.branch


def analyze_dst(birth_info: BirthInfo) -> DstAnalysis:
    """
    Decide whether a birth time needs DST disambiguation before casting.

    Returns a DstAnalysis. `needs_confirmation` is True only when the birth
    falls in a DST window AND the two interpretations (DST wall clock vs
    already-standard) produce different 时辰; otherwise the answer is moot and
    the caller should just cast with the engine default.

    Safe to call with partial birth_info — if date/time/longitude aren't
    available yet, it returns a no-op analysis (`in_dst_window=False`).
    """
    birth_time = _parse_birth_datetime(birth_info.birth_date, birth_info.birth_time)
    if birth_time is None or birth_info.longitude is None:
        return DstAnalysis(in_dst_window=False, needs_confirmation=False)

    if not is_china_dst(birth_time):
        return DstAnalysis(in_dst_window=False, needs_confirmation=False)

    branch_dst = _hour_branch(birth_time, birth_info, apply_dst=True)
    branch_std = _hour_branch(birth_time, birth_info, apply_dst=False)

    if branch_dst == branch_std:
        # The ±1h doesn't cross a 时辰 boundary — no need to bother the user.
        return DstAnalysis(
            in_dst_window=True,
            needs_confirmation=False,
            hour_branch_as_dst=branch_dst,
            hour_branch_as_standard=branch_std,
        )

    return DstAnalysis(
        in_dst_window=True,
        needs_confirmation=True,
        hour_branch_as_dst=branch_dst,
        hour_branch_as_standard=branch_std,
        question=_build_question(birth_time),
        options=[OPTION_WAS_DST_CLOCK, OPTION_ALREADY_STANDARD],
    )


def resolve_dst_choice(answer: str | None) -> bool | None:
    """
    Map a user's answer to the engine's `apply_dst_correction` flag.

    Returns True ("it was the DST wall clock" → undo the +1h), False
    ("already standard" → leave as-is), or None when the answer is unclear.
    """
    if not answer:
        return None
    text = answer.strip()
    if OPTION_WAS_DST_CLOCK in text or "钟表" in text or "当时" in text:
        return True
    if OPTION_ALREADY_STANDARD in text or "标准" in text or "换算" in text:
        return False
    return None


def _build_question(birth_time: datetime) -> str:
    clock = birth_time.strftime("%H:%M").lstrip("0") or "0:00"
    return (
        f"你出生在 {birth_time.year} 年夏天，那几年实行夏令时，钟表会比标准时间快一小时。"
        f"想跟你确认一下：你说的 {clock} 是当时钟表上显示的时间，还是已经换算成标准时间的？"
        "这一小时刚好会影响到出生时辰的判断。"
    )


__all__ = [
    "DstAnalysis",
    "analyze_dst",
    "resolve_dst_choice",
    "OPTION_WAS_DST_CLOCK",
    "OPTION_ALREADY_STANDARD",
]
