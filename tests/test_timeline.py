"""Tests for 大运/流年 resolution (bazibase.timeline)."""
from datetime import datetime
import pytest

from bazibase import (
    cast_chart,
    resolve_period,
    liunian_pillar,
    solar_ganzhi_year,
    STATUS_PRE_LUCK,
    STATUS_ACTIVE,
    STATUS_BEYOND_RANGE,
)


@pytest.fixture
def chart_1893():
    # 癸巳 / 甲子 / 丁酉 / 甲辰 — 日主丁, 逆运, first 大运 癸亥 (1900–1909).
    return cast_chart(datetime(1893, 12, 26, 8, 0), longitude=112.9, gender="male")


class TestLiunianPillar:
    def test_known_years(self):
        # 立春-based 干支纪年.
        assert liunian_pillar(1984).stem_branch == "甲子"
        assert liunian_pillar(1990).stem_branch == "庚午"
        assert liunian_pillar(2024).stem_branch == "甲辰"
        assert liunian_pillar(2026).stem_branch == "丙午"

    def test_hidden_stems_filled(self):
        # 午 hidden: 丁己.
        assert liunian_pillar(1990).hidden_stems == ("丁", "己")


class TestSolarGanzhiYear:
    def test_after_lichun_is_calendar_year(self):
        # 立春 2026 ≈ 2026-02-04. March is well after.
        assert solar_ganzhi_year(datetime(2026, 3, 1, 12, 0)) == 2026
        assert liunian_pillar(2026).stem_branch == "丙午"

    def test_before_lichun_is_previous_ganzhi_year(self):
        # Mid-January is before 立春 → still the previous 干支 year.
        assert solar_ganzhi_year(datetime(2026, 1, 15, 12, 0)) == 2025
        assert solar_ganzhi_year(datetime(2025, 1, 1, 0, 0)) == 2024

    def test_around_lichun_boundary(self):
        # On/after the 立春 instant the 干支 year flips to the calendar year.
        assert solar_ganzhi_year(datetime(2026, 2, 4, 20, 0)) == 2026

    def test_matches_year_pillar_of_a_cast_chart(self):
        # Cross-check against the engine's 立春-based year pillar.
        dt = datetime(2026, 1, 15, 12, 0)
        c = cast_chart(dt, longitude=120.0, gender="male")
        assert liunian_pillar(solar_ganzhi_year(dt)).stem_branch == c.year_pillar.stem_branch


class TestResolvePeriod:
    def test_pre_luck_before_first_pillar(self, chart_1893):
        r = resolve_period(chart_1893, 1895)  # before 起运 (1900)
        assert r.status == STATUS_PRE_LUCK
        assert r.luck_pillar is None
        assert r.luck_stem_ten_god is None
        # 流年 is still resolved.
        assert r.liunian.stem_branch == "乙未"
        assert r.nominal_age == 3  # 虚岁: 1895 - 1893 + 1

    def test_active_luck_and_ten_gods(self, chart_1893):
        r = resolve_period(chart_1893, 1920)
        assert r.status == STATUS_ACTIVE
        assert r.luck_pillar.pillar.stem_branch == "辛酉"
        # 日主丁: 辛 -> 偏财.
        assert r.luck_stem_ten_god == "偏财"
        assert r.liunian.stem_branch == "庚申"
        assert r.liunian_stem_ten_god == "正财"   # 丁 vs 庚
        assert r.nominal_age == 28

    def test_beyond_range_after_last_pillar(self, chart_1893):
        r = resolve_period(chart_1893, 2000)  # only 8 pillars computed (~to 1979)
        assert r.status == STATUS_BEYOND_RANGE
        assert r.luck_pillar is None
        assert r.liunian.stem_branch == "庚辰"

    def test_inclusive_span_boundaries(self, chart_1893):
        # Regression: 癸亥 spans 1900–1909 inclusive; 壬戌 starts 1910.
        # The end_year (1909) must still resolve to 癸亥, not fall through.
        assert resolve_period(chart_1893, 1900).luck_pillar.pillar.stem_branch == "癸亥"
        assert resolve_period(chart_1893, 1909).luck_pillar.pillar.stem_branch == "癸亥"
        assert resolve_period(chart_1893, 1910).luck_pillar.pillar.stem_branch == "壬戌"

    def test_determinism(self, chart_1893):
        a = resolve_period(chart_1893, 1950).to_dict()
        b = resolve_period(chart_1893, 1950).to_dict()
        assert a == b

    def test_to_dict_shape(self, chart_1893):
        d = resolve_period(chart_1893, 1920).to_dict()
        assert set(d.keys()) == {"year", "status", "nominal_age", "liunian", "luck_pillar"}
        assert set(d["liunian"].keys()) == {"stem_branch", "stem_ten_god", "branch_ten_god"}
        assert d["luck_pillar"]["stem_branch"] == "辛酉"

    def test_summary_string(self, chart_1893):
        s = resolve_period(chart_1893, 1920).summary()
        assert "1920" in s and "庚申" in s and "辛酉" in s
