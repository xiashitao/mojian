"""
Regression tests using publicly documented charts and boundary cases.

These tests serve two purposes:
    1. Anchor the engine to external ground truth (publicly documented Ba Zi)
    2. Catch regressions in calendar/solar-term boundary handling

If any of these break, the bug is almost certainly in:
    - The lunar_python version (check pyproject.toml pin)
    - True solar time correction (solar_time.py)
    - Boundary conventions (pillars.py docstring)
"""
from datetime import datetime
import pytest
from bazibase import cast_chart


class TestPublicCharts:
    """
    Charts whose pillar values are widely published in open sources.

    We deliberately avoid naming individuals in the assertions to keep
    the tests about engine correctness, not biographical claims.
    """

    def test_chart_a_winter_1893_chen_hour(self):
        """
        Birth: 1893-12-26, ~08:00 Beijing time (辰时), ~112.9°E.
        Expected: 癸巳 / 甲子 / 丁酉 / 甲辰
        This is one of the most widely published Ba Zi in Chinese sources.
        """
        c = cast_chart(
            birth_time=datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
        )
        assert c.year_pillar.stem_branch == "癸巳"
        assert c.month_pillar.stem_branch == "甲子"
        assert c.day_pillar.stem_branch == "丁酉"
        assert c.hour_pillar.stem_branch == "甲辰"

    def test_chart_a_is_pre_lichun_year_boundary(self):
        """
        1893-12-26 is before 立春 1894. Year pillar should be 癸巳 (1893's year),
        NOT 甲午 (1894's year). Confirms year boundary uses 立春, not Jan 1.
        """
        c = cast_chart(
            birth_time=datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
        )
        # 1893 立春 started 癸巳. 1894 立春 starts 甲午. Dec 26 is well before.
        assert c.year_pillar.stem == "癸"
        assert c.year_pillar.branch == "巳"

    def test_chart_a_luck_direction_backward(self):
        """
        Year stem 癸 is 阴. Male + 阴 year -> 逆行 (backward).
        Month is 甲子, so first 大运 should be 癸亥 (one step back in 60甲子).
        """
        c = cast_chart(
            birth_time=datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
        )
        assert c.luck.direction == -1
        assert c.luck.luck_pillars[0].pillar.stem_branch == "癸亥"
        assert c.luck.luck_pillars[1].pillar.stem_branch == "壬戌"


class TestCalendarBoundaries:
    """Tests for critical calendar boundaries that engines often get wrong."""

    def test_lichun_2024_year_transition(self):
        """
        2024 立春: 2024-02-04 16:26:58 Beijing time.

        Year/month/day pillars use clock time, so the transition happens
        at the published 立春 instant regardless of birth longitude.
        """
        before = cast_chart(
            birth_time=datetime(2024, 2, 4, 16, 25),
            longitude=116.4,
            gender="male",
        )
        after = cast_chart(
            birth_time=datetime(2024, 2, 4, 16, 28),
            longitude=116.4,
            gender="male",
        )
        assert before.year_pillar.stem_branch == "癸卯"
        assert after.year_pillar.stem_branch == "甲辰"

    def test_jie_2024_jingzhe_month_transition(self):
        """
        2024 惊蛰: 2024-03-05 10:22:44 Beijing time.
        Before: 寅月. After: 卯月.
        """
        before = cast_chart(
            birth_time=datetime(2024, 3, 5, 10, 20),
            longitude=116.4,
            gender="male",
        )
        after = cast_chart(
            birth_time=datetime(2024, 3, 5, 10, 25),
            longitude=116.4,
            gender="male",
        )
        assert before.month_pillar.branch == "寅"
        assert after.month_pillar.branch == "卯"

    def test_zi_hour_late_night(self):
        """
        23:30 is 子时 (子 spans 23:00–01:00).
        The day pillar should remain the same as 22:30 of the same calendar day
        under the "day boundary at 00:00" convention.
        """
        early = cast_chart(
            birth_time=datetime(2024, 6, 15, 22, 30),
            longitude=116.4,
            gender="male",
        )
        late = cast_chart(
            birth_time=datetime(2024, 6, 15, 23, 30),
            longitude=116.4,
            gender="male",
        )
        # Both should report hour branch = 子
        # early is 亥 at 22:30, late is 子 at 23:30
        # Wait: 21-23 is 亥, 23-01 is 子. So 22:30 = 亥, 23:30 = 子.
        assert early.hour_pillar.branch == "亥"
        assert late.hour_pillar.branch == "子"
        # Day pillars should be the same (23:30 is still day 15 under our convention).
        assert early.day_pillar == late.day_pillar

    def test_zi_hour_after_midnight(self):
        """00:30 should also be 子时, but day pillar advanced by one."""
        before_midnight = cast_chart(
            birth_time=datetime(2024, 6, 15, 23, 30),
            longitude=116.4,
            gender="male",
        )
        after_midnight = cast_chart(
            birth_time=datetime(2024, 6, 16, 0, 30),
            longitude=116.4,
            gender="male",
        )
        assert before_midnight.hour_pillar.branch == "子"
        assert after_midnight.hour_pillar.branch == "子"
        # Day pillar advances.
        assert before_midnight.day_pillar != after_midnight.day_pillar


class TestTrueSolarTimeImpact:
    """Tests confirming that true solar time correction actually matters."""

    def test_beijing_vs_urumqi_same_clock_time_different_hour(self):
        """
        Same Beijing clock time (12:00) at Beijing (116.4°E) vs Urumqi (87.6°E).
        The ~29° longitude difference (~2 hours) can shift the hour branch.
        """
        beijing = cast_chart(
            birth_time=datetime(2024, 6, 15, 12, 0),
            longitude=116.4,
            gender="male",
        )
        urumqi = cast_chart(
            birth_time=datetime(2024, 6, 15, 12, 0),
            longitude=87.6,
            gender="male",
        )
        # 12:00 Beijing clock at 116.4°E -> ~11:57 TST -> 午时 (11-13)
        # 12:00 Beijing clock at 87.6°E  -> ~09:50 TST -> 巳时 (9-11)
        assert beijing.hour_pillar.branch == "午"
        assert urumqi.hour_pillar.branch == "巳"

    def test_tst_stored_on_chart(self):
        c = cast_chart(
            birth_time=datetime(2024, 6, 15, 12, 0),
            longitude=116.4,
            gender="male",
        )
        assert c.true_solar_time != c.birth_clock_time
        # At 116.4°E vs 120°E ref, longitude delta = -3.6°, so TST should
        # be ~14.4 minutes earlier than clock, plus EoT (~0 near June 13).
        delta_min = (c.true_solar_time - c.birth_clock_time).total_seconds() / 60
        assert -16 < delta_min < -12  # roughly -14.4 plus small EoT


class TestSixtyJiaziCycle:
    """Sanity tests around the 60-甲子 cycle that should always hold."""

    def test_consecutive_days_advance_by_one(self):
        """Two consecutive calendar days at the same hour should have
        day pillars that advance by exactly one position in 60甲子."""
        from bazibase.constants import STEMS, BRANCHES
        from bazibase.pillars import compute_four_pillars

        a = compute_four_pillars(datetime(2024, 6, 15, 12, 0))
        b = compute_four_pillars(datetime(2024, 6, 16, 12, 0))

        def idx(s: str) -> int:
            si = STEMS.index(s[0])
            bi = BRANCHES.index(s[1])
            for n in range(60):
                if n % 10 == si and n % 12 == bi:
                    return n
            raise ValueError(s)

        i_a = idx(a.day.stem_branch)
        i_b = idx(b.day.stem_branch)
        assert (i_b - i_a) % 60 == 1
