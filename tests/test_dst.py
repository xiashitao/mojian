"""Tests for China daylight-saving-time correction and its effect on charts."""
from datetime import datetime
import pytest

from bazibase import cast_chart
from bazibase.dst import is_china_dst, to_standard_time


class TestIsChinaDst:
    def test_summer_1988_is_dst(self):
        assert is_china_dst(datetime(1988, 7, 1, 12, 0)) is True

    def test_winter_1988_not_dst(self):
        assert is_china_dst(datetime(1988, 1, 1, 12, 0)) is False

    def test_outside_dst_years_not_dst(self):
        # Nationwide DST ran only 1986–1991.
        assert is_china_dst(datetime(1985, 7, 1, 12, 0)) is False
        assert is_china_dst(datetime(1992, 7, 1, 12, 0)) is False
        assert is_china_dst(datetime(2024, 7, 1, 12, 0)) is False

    def test_start_date_transition_at_two(self):
        # 1988 DST began 1988-04-10 at 02:00 (clocks 02:00 -> 03:00).
        assert is_china_dst(datetime(1988, 4, 10, 1, 30)) is False
        assert is_china_dst(datetime(1988, 4, 10, 3, 30)) is True

    def test_end_date_transition_at_two(self):
        # 1988 DST ended 1988-09-11 at 02:00 (clocks 02:00 -> 01:00).
        assert is_china_dst(datetime(1988, 9, 11, 1, 30)) is True
        assert is_china_dst(datetime(1988, 9, 11, 2, 30)) is False


class TestToStandardTime:
    def test_subtracts_one_hour_in_dst(self):
        std, applied = to_standard_time(datetime(1988, 7, 1, 8, 30))
        assert applied is True
        assert std == datetime(1988, 7, 1, 7, 30)

    def test_unchanged_outside_dst(self):
        std, applied = to_standard_time(datetime(2024, 7, 1, 8, 30))
        assert applied is False
        assert std == datetime(2024, 7, 1, 8, 30)


class TestDstChartImpact:
    def test_dst_flag_surfaced_on_chart(self):
        c = cast_chart(datetime(1988, 7, 1, 8, 30), longitude=120.0, gender="male")
        assert c.dst_applied is True
        assert c.standard_clock_time == datetime(1988, 7, 1, 7, 30)
        c2 = cast_chart(datetime(2024, 7, 1, 8, 30), longitude=120.0, gender="male")
        assert c2.dst_applied is False
        assert c2.standard_clock_time == datetime(2024, 7, 1, 8, 30)

    def test_dst_shifts_hour_branch_at_boundary(self):
        # A DST summer birth reported at 09:10 is really 08:10 standard.
        # At 120°E that lands in 辰 (07–09), not 巳 (09–11).
        dst_birth = cast_chart(datetime(1988, 7, 1, 9, 10), longitude=120.0, gender="male")
        # The same wall-clock time outside DST years stays in 巳.
        no_dst = cast_chart(datetime(1992, 7, 1, 9, 10), longitude=120.0, gender="male")
        assert dst_birth.hour_pillar.branch == "辰"
        assert no_dst.hour_pillar.branch == "巳"


class TestTrueSolarDayConsistency:
    """Day pillar and hour pillar must share the true-solar-time base."""

    def test_far_west_just_after_midnight_uses_previous_solar_day(self):
        # Kashgar ~75.99°E. A 00:30 birth is ~22:34 true solar time the
        # previous evening, so 日柱 should be the previous solar day and the
        # 时柱 should be a late-evening branch (亥), not 子.
        c = cast_chart(datetime(2024, 6, 16, 0, 30), longitude=75.99, gender="male")
        # 时支 from true solar time ~22:34 -> 亥 (21–23).
        assert c.hour_pillar.branch == "亥"
        # The day pillar matches the previous calendar day's pillar.
        prev_day = cast_chart(datetime(2024, 6, 15, 12, 0), longitude=75.99, gender="male")
        assert c.day_pillar == prev_day.day_pillar

    def test_hour_stem_consistent_with_day_stem(self):
        # 五鼠遁: the hour stem must derive from the SAME day stem the chart
        # reports, regardless of how far TST shifts the time.
        from bazibase.pillars import _hour_stem_from_day_stem
        c = cast_chart(datetime(2024, 6, 16, 0, 30), longitude=75.99, gender="male")
        expected = _hour_stem_from_day_stem(c.day_pillar.stem, c.hour_pillar.branch)
        assert c.hour_pillar.stem == expected
