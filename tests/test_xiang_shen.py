"""Tests for 相神 / 忌神 identification (v0.2.2)."""
from datetime import datetime
import pytest
from bazibase import cast_chart
from bazibase.rules.yong_shen import determine_yong_shen
from bazibase.rules.xiang_shen import (
    identify_xiang_ji, XiangShenResult, StemOccurrence,
    XIANG_JI_TABLE,
)


def _diagnose(dt, lon=116.4, gender="male"):
    c = cast_chart(dt, lon, gender)
    ys = determine_yong_shen(c)
    return c, ys, identify_xiang_ji(c, ys)


class TestXiangJiTable:
    """The lookup table covers all 8 standard 十神."""

    def test_all_eight_ten_gods_covered(self):
        for tg in ("正官", "七杀", "正财", "偏财", "正印", "偏印", "食神", "伤官"):
            assert tg in XIANG_JI_TABLE
            xiang, ji = XIANG_JI_TABLE[tg]
            assert isinstance(xiang, tuple) and len(xiang) > 0
            assert isinstance(ji, tuple) and len(ji) > 0

    def test_zheng_guan_xiang_includes_cai_and_yin(self):
        xiang, _ = XIANG_JI_TABLE["正官"]
        # 正官格以财生官、印护官为相
        assert "正财" in xiang or "偏财" in xiang
        assert "正印" in xiang or "偏印" in xiang

    def test_qi_sha_ji_includes_cai(self):
        # 七杀格忌财党杀
        _, ji = XIANG_JI_TABLE["七杀"]
        assert "正财" in ji or "偏财" in ji

    def test_cai_ji_includes_bi_jie(self):
        # 财格忌比劫夺财
        for cai in ("正财", "偏财"):
            _, ji = XIANG_JI_TABLE[cai]
            assert "比肩" in ji or "劫财" in ji

    def test_yin_ji_includes_cai(self):
        # 印格忌财破印
        for yin in ("正印", "偏印"):
            _, ji = XIANG_JI_TABLE[yin]
            assert "正财" in ji or "偏财" in ji

    def test_shi_shen_ji_includes_pian_yin(self):
        # 食神格忌枭神（偏印）夺食
        _, ji = XIANG_JI_TABLE["食神"]
        assert "偏印" in ji

    def test_shang_guan_ji_includes_zheng_guan(self):
        # 伤官见官，为祸百端
        _, ji = XIANG_JI_TABLE["伤官"]
        assert "正官" in ji


class TestIdentifyXiangJi:
    """End-to-end 相神/忌神 identification on known charts."""

    def test_mao_chart_qi_sha_ge_has_yin_xiang(self):
        # 1893-12-26 辰时: 七杀格，癸杀
        # 七杀格相神 = 食神/印；月干甲(正印)、时干甲(正印) 应被识别为相神
        c, ys, xs = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        assert ys.ten_god == "七杀"
        # 相神应包含 正印 或 偏印
        xiang_tgs = {o.ten_god for o in xs.xiang_shen}
        assert "正印" in xiang_tgs or "偏印" in xiang_tgs
        # 忌神应包含 财
        ji_tgs = {o.ten_god for o in xs.ji_shen}
        assert "正财" in ji_tgs or "偏财" in ji_tgs

    def test_citations_explain_decision(self):
        c, ys, xs = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        rule_ids = [cite.rule_id for cite in xs.citations]
        assert "ZP-XIANG-001" in rule_ids
        assert "ZP-JI-001" in rule_ids

    def test_stem_occurrence_records_position(self):
        c, ys, xs = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        # All occurrences should have valid position fields
        for o in xs.xiang_shen:
            assert o.position in ("year", "month", "day", "hour")
            assert o.location in ("天干", "本气", "中气", "余气")
            assert o.stem
            assert o.ten_god


class TestSpecialNotes:
    """Special notes for problematic 忌神 configurations."""

    def test_no_special_note_for_qi_sha_with_cai(self):
        # 七杀格 + 财忌 不触发特殊 note（只有 食神格+偏印/伤官格+正官/正官格+七杀 才触发）
        c, ys, xs = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        assert ys.ten_god == "七杀"
        # 七杀格的忌神是财，不触发"官杀混杂"等特殊 note
        special_notes = [n for n in xs.notes if "混杂" in n or "夺食" in n or "见官" in n]
        assert len(special_notes) == 0


class TestUnresolvedYongShen:
    """When 用神 is unresolved, 相神/忌神 should be empty."""

    def test_no_xiang_ji_when_yong_shen_unresolved(self):
        # Construct a chart where 用神 unresolved
        # (in v0.2.1, this is nearly impossible for real charts — 用 mock)
        from unittest.mock import MagicMock
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = None
        mock_ys.ten_god = None
        xs = identify_xiang_ji(mock_chart, mock_ys)
        assert len(xs.xiang_shen) == 0
        assert len(xs.ji_shen) == 0
        assert any("未定" in n for n in xs.notes)


class TestXiangJiDeterminism:
    def test_same_input_same_output(self):
        a = _diagnose(datetime(2000, 6, 15, 12, 0))[2]
        b = _diagnose(datetime(2000, 6, 15, 12, 0))[2]
        assert a == b
