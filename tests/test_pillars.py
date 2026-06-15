"""Tests for four-pillar computation."""
from datetime import datetime
import pytest
from bazibase.pillars import compute_four_pillars, Pillar, FourPillars
from bazibase.constants import BRANCH_HIDDEN_STEMS


class TestPillarDataclass:
    def test_stem_branch_property(self):
        p = Pillar(stem="甲", branch="子", hidden_stems=("癸",), position="year")
        assert p.stem_branch == "甲子"

    def test_str(self):
        p = Pillar(stem="甲", branch="子", hidden_stems=("癸",), position="year")
        assert str(p) == "甲子"

    def test_frozen(self):
        p = Pillar(stem="甲", branch="子", hidden_stems=("癸",))
        with pytest.raises(Exception):
            p.stem = "乙"  # type: ignore


class TestComputeFourPillars:
    def test_known_chart_1893_12_26_chen(self):
        # 1893-12-26 08:00 (辰时) — documented as 癸巳/甲子/丁酉/甲辰
        fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        assert fp.year.stem_branch == "癸巳"
        assert fp.month.stem_branch == "甲子"
        assert fp.day.stem_branch == "丁酉"
        assert fp.hour.stem_branch == "甲辰"

    def test_day_master(self):
        fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        assert fp.day_master == "丁"

    def test_hidden_stems_filled(self):
        fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        # 巳 branch hidden: 丙庚戊
        assert fp.year.hidden_stems == ("丙", "庚", "戊")
        # 子 branch hidden: 癸
        assert fp.month.hidden_stems == ("癸",)
        # 酉 branch hidden: 辛
        assert fp.day.hidden_stems == ("辛",)
        # 辰 branch hidden: 戊乙癸
        assert fp.hour.hidden_stems == ("戊", "乙", "癸")

    def test_positions_set(self):
        fp = compute_four_pillars(datetime(2000, 1, 1, 12, 0))
        assert fp.year.position == "year"
        assert fp.month.position == "month"
        assert fp.day.position == "day"
        assert fp.hour.position == "hour"

    def test_lichun_boundary_year_pillar(self):
        # 立春 2024 was at 2024-02-04 16:26:58 Beijing time.
        # Just before: still 癸卯 year. Just after: 甲辰 year.
        before = compute_four_pillars(datetime(2024, 2, 4, 16, 0))
        after = compute_four_pillars(datetime(2024, 2, 4, 17, 0))
        assert before.year.stem == "癸"
        assert before.year.branch == "卯"
        assert after.year.stem == "甲"
        assert after.year.branch == "辰"

    def test_jie_boundary_month_pillar(self):
        # 惊蛰 2024 was at 2024-03-05 10:22:44 Beijing time.
        # Before 寅月, after 卯月.
        before = compute_four_pillars(datetime(2024, 3, 5, 10, 0))
        after = compute_four_pillars(datetime(2024, 3, 5, 11, 0))
        assert before.month.branch == "寅"
        assert after.month.branch == "卯"

    def test_hour_branch_by_time(self):
        # 12:00 noon -> 午时
        fp = compute_four_pillars(datetime(2024, 6, 15, 12, 0))
        assert fp.hour.branch == "午"
        # 00:30 -> 子时
        fp2 = compute_four_pillars(datetime(2024, 6, 15, 0, 30))
        assert fp2.hour.branch == "子"
        # 23:30 -> 子时
        fp3 = compute_four_pillars(datetime(2024, 6, 15, 23, 30))
        assert fp3.hour.branch == "子"

    def test_rejects_tz_aware_datetime(self):
        from datetime import timezone
        with pytest.raises(ValueError):
            compute_four_pillars(datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc))

    def test_determinism(self):
        a = compute_four_pillars(datetime(2024, 6, 15, 12, 0))
        b = compute_four_pillars(datetime(2024, 6, 15, 12, 0))
        assert a == b

    def test_iteration(self):
        fp = compute_four_pillars(datetime(2024, 6, 15, 12, 0))
        pillars = list(fp)
        assert len(pillars) == 4
        assert pillars[0] is fp.year
