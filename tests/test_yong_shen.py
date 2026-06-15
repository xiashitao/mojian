"""Tests for 用神取法 (yong-shen determination)."""
from datetime import datetime
import pytest
from bazibase import cast_chart
from bazibase.rules.yong_shen import (
    determine_yong_shen,
    _find_transparent_stems,
    YongShenResult,
)


class TestFindTransparentStems:
    def test_mao_chart_year_transparent(self):
        # 1893-12-26 8:00, 月令子藏癸，癸透年干
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        ts = _find_transparent_stems(c)
        assert len(ts) == 1
        assert ts[0].hidden_stem == "癸"
        assert ts[0].role == "本气"
        assert ts[0].transparent_at == "year"

    def test_day_master_not_counted_as_transparent(self):
        # 日主本人不算透干
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        # 日主是丁，确保我们没把丁当作"透出于日干"
        ts = _find_transparent_stems(c)
        for t in ts:
            assert t.transparent_at != "day"


class TestDetermineYongShenBenqiTou:
    """Rule ZP-YONG-001: 月令本气透干 → 用本气"""

    def test_mao_chart_benqi_tou(self):
        # 1893-12-26 辰时, 月令子，本气癸透于年干 → 用神癸(七杀)
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        ys = determine_yong_shen(c)
        assert ys.stem == "癸"
        assert ys.ten_god == "七杀"
        assert ys.source_rule_id == "ZP-YONG-001"
        assert ys.is_bi_jie is False
        assert ys.unresolved is False

    def test_cites_correct_rule_chain(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        ys = determine_yong_shen(c)
        rule_ids = [cite.rule_id for cite in ys.citations]
        assert "ZP-YONG-000" in rule_ids  # preface always cited
        assert "ZP-YONG-001" in rule_ids  # the firing rule
        # Higher-priority rules (002, 003, 004) should NOT fire.
        assert "ZP-YONG-002" not in rule_ids
        assert "ZP-YONG-003" not in rule_ids
        assert "ZP-YONG-004" not in rule_ids


class TestDetermineYongShenZhongqiTou:
    """Rule ZP-YONG-002: 本气不透、中气透 → 用中气"""

    def test_zhongqi_tou_case(self):
        # 2024-05-15 12:00, 月令巳藏丙庚戊
        # 己日：日主己，天干甲(年)己(月)庚(时)
        # 本气丙不透，中气庚透于时干 → 用神庚(伤官)
        c = cast_chart(datetime(2024, 5, 15, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert ys.stem == "庚"
        assert ys.ten_god == "伤官"
        assert ys.source_rule_id == "ZP-YONG-002"


class TestDetermineYongShenYuqiTou:
    """Rule ZP-YONG-003: 本中气均不透、余气透 → 用余气"""

    def test_yuqi_tou_case(self):
        # 2023-04-06 12:00, 癸卯年丙辰月甲午日庚午时
        # 月令辰藏戊乙癸。日主甲。天干癸(年)丙(月)庚(时)
        # 本气戊不透，中气乙不透，余气癸透于年干 → 用神癸(正印)
        c = cast_chart(datetime(2023, 4, 6, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert c.month_pillar.branch == "辰"
        assert ys.stem == "癸"
        assert ys.ten_god == "正印"
        assert ys.source_rule_id == "ZP-YONG-003"


class TestDetermineYongShenAnYong:
    """Rule ZP-YONG-004: 三气俱不透 → 暗用本气"""

    def test_an_yong_case(self):
        # 2024-03-15 12:00, 甲辰年丁卯月戊寅日戊午时
        # 月令卯藏乙。日主戊。天干甲(年)丁(月)戊(时) — 乙不透
        # → 暗用乙(正官)
        c = cast_chart(datetime(2024, 3, 15, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert c.month_pillar.branch == "卯"
        assert ys.stem == "乙"
        assert ys.ten_god == "正官"
        assert ys.source_rule_id == "ZP-YONG-004"

    def test_no_transparent_stems_recorded(self):
        c = cast_chart(datetime(2024, 3, 15, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert len(ys.transparent_stems) == 0


class TestDetermineYongShenBiJie:
    """Rule ZP-YONG-005: 月令本气为比劫 → 另寻用神

    v0.2.1: 另寻算法已实现。这些测试验证建禄/月劫/羊刃都能在
    月令之外找到合适的用神，并附带推理链。
    """

    def test_jianlu_jia_yin_month_resolves_to_qi_sha(self):
        # 2024-02-10 12:00, 寅月甲日 → 建禄
        # 月令寅本气甲 = 日主甲 (比肩)
        # 天干：甲(year, 比肩), 丙(month, 食神), 庚(hour, 七杀)
        # 优先级 正官→七杀：无正官，时干庚为七杀 → 用神庚
        c = cast_chart(datetime(2024, 2, 10, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert ys.is_bi_jie is True
        assert ys.unresolved is False
        assert ys.stem == "庚"
        assert ys.ten_god == "七杀"
        assert ys.source_rule_id == "ZP-YONG-007"
        assert ys.alternative_source == "透于hour干"

    def test_bi_jie_citations_explain_decision(self):
        c = cast_chart(datetime(2024, 2, 10, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        rule_ids = [cite.rule_id for cite in ys.citations]
        # 推理链：前置 → 比劫识别 → 另寻（七杀）
        assert "ZP-YONG-000" in rule_ids
        assert "ZP-YONG-005" in rule_ids
        assert "ZP-YONG-007" in rule_ids
        # 最后一条必须是实际找到用神的规则
        last_cite = ys.citations[-1]
        assert last_cite.rule_id == "ZP-YONG-007"
        assert "庚" in last_cite.conclusion
        assert "七杀" in last_cite.conclusion


class TestAlternativeYongShenPriority:
    """v0.2.1: 比劫当令的另寻用神算法 — 覆盖所有优先级。

    优先级：正官 → 七杀 → 财星 → 印星 → 食伤
    """

    def test_yang_ren_ge_resolves_to_zheng_guan_hidden(self):
        # 2024-03-11 12:00, 卯月甲日 → 羊刃格
        # 四柱：甲辰/丁卯/甲戌/庚午
        # 天干：甲(year, 比肩), 丁(month, 伤官), 庚(hour, 七杀)
        # 藏干：day 戌 = 戊(本气)/辛(中气)/丁(余气)
        # 优先级：正官优先于七杀，藏于日支中气的辛为正官 → 用神辛
        c = cast_chart(datetime(2024, 3, 11, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert ys.is_bi_jie is True
        assert ys.stem == "辛"
        assert ys.ten_god == "正官"
        assert ys.source_rule_id == "ZP-YONG-006"
        assert ys.alternative_source == "藏于day支中气"

    def test_yue_jie_ge_resolves_to_zheng_guan_hidden(self):
        # 2024-02-11 12:00, 寅月乙日 → 月劫格
        # 四柱：甲辰/丙寅/乙巳/壬午
        # 天干：甲(year, 劫财), 丙(month, 伤官), 壬(hour, 正印)
        # 藏干：day 巳 = 丙(本气)/庚(中气)/戊(余气)
        # 优先级：正官优先，藏于日支中气的庚为正官 → 用神庚
        c = cast_chart(datetime(2024, 2, 11, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert ys.is_bi_jie is True
        assert ys.stem == "庚"
        assert ys.ten_god == "正官"
        assert ys.source_rule_id == "ZP-YONG-006"
        assert ys.alternative_source == "藏于day支中气"

    def test_priority_search_prefers_transparent_over_hidden(self):
        # 同一优先级内，天干优先于藏干
        # 2024-02-10 12:00: 庚透于hour干，比藏干中的其他七杀优先
        c = cast_chart(datetime(2024, 2, 10, 12, 0), 116.4, "male")
        ys = determine_yong_shen(c)
        assert ys.alternative_source.startswith("透于")


class TestAlternativeYongShenUnit:
    """Direct unit tests for _find_alternative_yong_shen priority ordering."""

    def test_priority_order_guan_before_sha(self):
        """正官 must come before 七杀 in the priority table."""
        from bazibase.rules.yong_shen import _ALT_PRIORITY_TABLE
        tiers = [tgs for tgs, _ in _ALT_PRIORITY_TABLE]
        # Verify exact priority order
        assert tiers[0] == ("正官",)
        assert tiers[1] == ("七杀",)
        assert tiers[2] == ("正财", "偏财")
        assert tiers[3] == ("正印", "偏印")
        assert tiers[4] == ("食神", "伤官")

    def test_priority_rules_registered(self):
        from bazibase.rules import all_rules
        rule_ids = {r.id for r in all_rules()}
        for rid in ("ZP-YONG-006", "ZP-YONG-007", "ZP-YONG-008",
                    "ZP-YONG-009", "ZP-YONG-010", "ZP-YONG-011"):
            assert rid in rule_ids


class TestYongShenDeterminism:
    def test_same_input_same_output(self):
        kwargs = dict(birth_time=datetime(2000, 6, 15, 12, 0), longitude=116.4, gender="male")
        a = determine_yong_shen(cast_chart(**kwargs))
        b = determine_yong_shen(cast_chart(**kwargs))
        assert a == b
