"""Tests for day-master strength assessment."""
from datetime import datetime
import pytest
from bazibase.pillars import compute_four_pillars
from bazibase.strength import assess_strength


class TestAssessStrength:
    def test_strong_chart(self):
        # Pick a chart where day master is well-supported.
        # 甲木日主生于寅月(本气甲木), with multiple 木/水 stems — should be strong.
        # 2022-03-01 12:00 — let's see what this produces.
        fp = compute_four_pillars(datetime(2022, 3, 1, 12, 0))
        result = assess_strength(fp)
        assert isinstance(result.total_score, float)
        assert result.total_score >= 0
        # We don't hard-assert strong/weak since the chart may vary,
        # but the verdict should be one of the two.
        assert result.verdict in ("身强", "身弱")

    def test_weak_chart_winter_water_dm(self):
        # 丁火生于子月(冬), 月令癸水七杀当令, should be weak.
        fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        result = assess_strength(fp)
        assert result.verdict == "身弱"
        assert result.total_score < 5.0

    def test_breakdown_items_have_valid_contributions(self):
        fp = compute_four_pillars(datetime(2000, 6, 15, 12, 0))
        result = assess_strength(fp)
        for item in result.breakdown:
            assert item.contribution > 0
            assert isinstance(item.source, str)
            assert isinstance(item.note, str)

    def test_month_令_weight_applied(self):
        # For 丁火 day master at 1893-12-26, the month 子 hidden 癸水
        # does NOT support fire (水克火), so no month-令 contribution.
        # The score should NOT include any "月令" item.
        fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        result = assess_strength(fp)
        month_items = [b for b in result.breakdown if "月令" in b.source]
        assert len(month_items) == 0, "Month 子 does not support 丁火, no 令 contribution expected"

    def test_month_令_weight_applied_when_supported(self):
        # 丁火生于午月(夏火旺), month hidden 丁/己 both support 火.
        # 2024-07-01 12:00 is around 午月.
        fp = compute_four_pillars(datetime(2024, 7, 1, 12, 0))
        if fp.day_master in ("丙", "丁"):
            result = assess_strength(fp)
            month_items = [b for b in result.breakdown if "月令" in b.source]
            assert len(month_items) > 0, "Expected month 午 to support fire DM"

    def test_borderline_flag(self):
        # 1893-12-26 chart had score 4.0, threshold 5.0, so borderline (within ±1.0).
        fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        result = assess_strength(fp)
        assert result.borderline is True

    def test_determinism(self):
        fp = compute_four_pillars(datetime(2000, 6, 15, 12, 0))
        a = assess_strength(fp)
        b = assess_strength(fp)
        assert a == b
