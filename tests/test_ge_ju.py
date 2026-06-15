"""Tests for 格局判定 (pattern determination)."""
from datetime import datetime
import pytest
from bazibase import cast_chart
from bazibase.rules.yong_shen import determine_yong_shen
from bazibase.rules.ge_ju import (
    determine_ge_ju, GeJuResult, GE_JU_NAME_BY_TEN_GOD,
)


def _diagnose(dt, lon=116.4, gender="male"):
    c = cast_chart(dt, lon, gender)
    ys = determine_yong_shen(c)
    return c, ys, determine_ge_ju(c, ys)


class TestStandardEightGeJu:
    """All 8 正格 mapping from 用神 十神."""

    def test_qi_sha_ge(self):
        # 1893-12-26 辰时 → 七杀格
        _, ys, gj = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        assert ys.ten_god == "七杀"
        assert gj.name == "七杀格"
        assert gj.alias == "偏官格"
        assert gj.category == "正格"
        assert gj.unresolved is False

    def test_shang_guan_ge(self):
        # 2024-05-15 → 伤官格
        _, ys, gj = _diagnose(datetime(2024, 5, 15, 12, 0))
        assert ys.ten_god == "伤官"
        assert gj.name == "伤官格"

    def test_zheng_yin_ge(self):
        # 2023-04-06 → 正印格
        _, ys, gj = _diagnose(datetime(2023, 4, 6, 12, 0))
        assert ys.ten_god == "正印"
        assert gj.name == "正印格"

    def test_zheng_guan_ge_an_yong(self):
        # 2024-03-15 → 正官格 (暗用)
        _, ys, gj = _diagnose(datetime(2024, 3, 15, 12, 0))
        assert ys.ten_god == "正官"
        assert gj.name == "正官格"


class TestGeJuMappingComplete:
    """The 10 十神 cover all standard patterns."""

    def test_all_eight_ten_gods_have_ge_ju(self):
        # The 8 usable 用神 十神 (excluding 比肩/劫财 which are special)
        usable = ("正官", "七杀", "正财", "偏财", "正印", "偏印", "食神", "伤官")
        for tg in usable:
            assert tg in GE_JU_NAME_BY_TEN_GOD
            name, alias = GE_JU_NAME_BY_TEN_GOD[tg]
            assert name.endswith("格")

    def test_pian_yin_has_xiao_shen_alias(self):
        assert GE_JU_NAME_BY_TEN_GOD["偏印"][1] == "枭神格"

    def test_qi_sha_has_pian_guan_alias(self):
        assert GE_JU_NAME_BY_TEN_GOD["七杀"][1] == "偏官格"


class TestBiJieGeJu:
    """比劫当令 → 建禄 / 月劫 / 羊刃.

    v0.2.1: 另寻用神算法已实现，所以 is_bi_jie=True 的格局
    现在通常能确定用神，unresolved=False。
    """

    def test_jianlu_ge(self):
        # 2024-02-10 12:00, 寅月甲日 → 建禄格
        # 月令寅本气甲 = 日主甲 (比肩)
        # 另寻用神：时干庚(七杀)
        c, ys, gj = _diagnose(datetime(2024, 2, 10, 12, 0))
        assert c.day_master == "甲"
        assert c.month_pillar.branch == "寅"
        assert ys.is_bi_jie is True
        assert gj.name == "建禄格"
        assert gj.category == "建禄月劫"
        assert gj.source_rule_id == "ZP-GE-JIANLU"
        # v0.2.1: 用神已通过另寻算法找到
        assert gj.unresolved is False
        assert ys.stem == "庚"

    def test_yang_ren_ge(self):
        # 2024-03-11 12:00, 卯月甲日 → 羊刃格
        # 四柱：甲辰/丁卯/甲戌/庚午
        # 月令卯本气乙 = 日主甲的劫财 (阳干)
        # 另寻用神：正官优先，藏于日支戌中气的辛 → 用神辛(正官)
        c, ys, gj = _diagnose(datetime(2024, 3, 11, 12, 0))
        assert c.day_master == "甲"
        assert c.month_pillar.branch == "卯"
        assert ys.is_bi_jie is True
        assert gj.name == "羊刃格"
        assert gj.category == "建禄月劫"
        assert gj.source_rule_id == "ZP-GE-YANGREN"
        assert ys.stem == "辛"
        assert ys.ten_god == "正官"

    def test_yue_jie_ge(self):
        # 2024-02-11 12:00, 寅月乙日 → 月劫格
        # 四柱：甲辰/丙寅/乙巳/壬午
        # 月令寅本气甲 = 日主乙的劫财 (阴干)
        # 另寻用神：正官优先，藏于日支巳中气的庚 → 用神庚(正官)
        c, ys, gj = _diagnose(datetime(2024, 2, 11, 12, 0))
        assert c.day_master == "乙"
        assert c.month_pillar.branch == "寅"
        assert ys.is_bi_jie is True
        assert gj.name == "月劫格"
        assert gj.category == "建禄月劫"
        assert gj.source_rule_id == "ZP-GE-YUEJIE"
        assert ys.stem == "庚"
        assert ys.ten_god == "正官"


class TestGeJuCitations:
    def test_citations_explain_decision(self):
        c, ys, gj = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        assert len(gj.citations) >= 1
        cite = gj.citations[0]
        assert cite.rule_id == "ZP-GE-MAP"
        assert "七杀" in cite.reason or "七杀" in cite.conclusion

    def test_jianlu_citation(self):
        c, ys, gj = _diagnose(datetime(2024, 2, 10, 12, 0))
        cite = gj.citations[0]
        assert cite.rule_id == "ZP-GE-JIANLU"
        assert "建禄" in cite.conclusion


class TestGeJuDeterminism:
    def test_same_input_same_output(self):
        a = _diagnose(datetime(2000, 6, 15, 12, 0))[2]
        b = _diagnose(datetime(2000, 6, 15, 12, 0))[2]
        assert a == b
