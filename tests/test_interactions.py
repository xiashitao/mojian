"""Tests for 刑冲合化 (stem/branch interactions) detection (v0.2.3)."""
from datetime import datetime
import pytest
from bazibase import cast_chart
from bazibase.rules.interactions import (
    detect_interactions,
    Interaction,
    InteractionResult,
    GAN_HE_TABLE,
    SAN_HE_TABLE,
    SAN_HUI_TABLE,
    LIU_CHONG_TABLE,
    HAI_TABLE,
    XING_SAN_TYPES,
    XING_HU_TYPES,
    ZI_XING_BRANCHES,
)


def _chart(dt, lon=116.4, gender="male"):
    return cast_chart(dt, lon, gender)


class TestGanHe:
    """天干五合 (stem combinations)."""

    def test_table_has_five_pairs(self):
        # 5 pairs, both directions = 10 entries
        assert len(GAN_HE_TABLE) == 10

    def test_jia_ji_he_hua_tu(self):
        assert GAN_HE_TABLE[("甲", "己")] == "土"
        assert GAN_HE_TABLE[("己", "甲")] == "土"

    def test_all_five_combinations(self):
        assert GAN_HE_TABLE[("乙", "庚")] == "金"
        assert GAN_HE_TABLE[("丙", "辛")] == "水"
        assert GAN_HE_TABLE[("丁", "壬")] == "木"
        assert GAN_HE_TABLE[("戊", "癸")] == "火"

    def test_1970_chart_has_gan_he(self):
        # 1970-03-15: 庚 己 甲 己
        # 甲(月干)+己(日干) or 甲(月干)+己(时干) → 合化土
        c = _chart(datetime(1970, 3, 15, 10, 0))
        ia = detect_interactions(c)
        assert len(ia.gan_he) >= 1
        # At least one should be 甲+己→土
        he_elements = {
            (i.elements, i.resulting_element) for i in ia.gan_he
        }
        assert any(
            i.resulting_element == "土" and set(i.elements) == {"甲", "己"}
            for i in ia.gan_he
        )

    def test_gan_he_citation(self):
        c = _chart(datetime(1970, 3, 15, 10, 0))
        ia = detect_interactions(c)
        cite_ids = [cite.rule_id for cite in ia.citations]
        assert "ZP-HE-GAN" in cite_ids


class TestSanHe:
    """地支三合 (branch triple combinations)."""

    def test_table_has_four_sets(self):
        assert len(SAN_HE_TABLE) == 4
        elements = {elem for _, elem in SAN_HE_TABLE}
        assert elements == {"水", "木", "火", "金"}

    def test_shen_zi_chen_full_san_he(self):
        # 1960-08-20: branches = 子申辰申 → 申子辰 full 三合水局
        c = _chart(datetime(1960, 8, 20, 16, 0))
        ia = detect_interactions(c)
        assert len(ia.san_he) == 1
        assert ia.san_he[0].kind == "三合"
        assert ia.san_he[0].resulting_element == "水"
        assert set(ia.san_he[0].elements) == {"申", "子", "辰"}

    def test_half_san_he(self):
        # Mao 1893: branches = 巳子酉辰 → 子+辰 of 申子辰 = 半三合水
        c = _chart(datetime(1893, 12, 26, 8, 0), 112.9)
        ia = detect_interactions(c)
        # At least one 半三合 (子+辰 missing 申)
        assert len(ia.ban_he) >= 1
        ban_he_elements = [set(i.elements) for i in ia.ban_he]
        # 子+辰 should be present as a 半三合
        assert any(
            {"子", "辰"} == s for s in ban_he_elements
        )

    def test_san_he_citation(self):
        c = _chart(datetime(1960, 8, 20, 16, 0))
        ia = detect_interactions(c)
        cite_ids = [cite.rule_id for cite in ia.citations]
        assert "ZP-SAN-HE" in cite_ids


class TestSanHui:
    """地支三会 (branch seasonal combinations)."""

    def test_table_has_four_sets(self):
        assert len(SAN_HUI_TABLE) == 4
        elements = {elem for _, elem in SAN_HUI_TABLE}
        assert elements == {"木", "火", "金", "水"}


class TestLiuChong:
    """地支六冲 (branch clashes)."""

    def test_table_has_six_pairs(self):
        assert len(LIU_CHONG_TABLE) == 6

    def test_all_six_clashes_listed(self):
        expected = {
            frozenset({"子", "午"}),
            frozenset({"丑", "未"}),
            frozenset({"寅", "申"}),
            frozenset({"卯", "酉"}),
            frozenset({"辰", "戌"}),
            frozenset({"巳", "亥"}),
        }
        assert set(LIU_CHONG_TABLE) == expected

    def test_chen_xu_chong_detected(self):
        # YangRen 2024: branches = 辰卯戌午 → 辰+戌 冲
        c = _chart(datetime(2024, 3, 11, 12, 0))
        ia = detect_interactions(c)
        assert len(ia.chong) >= 1
        chong_pairs = {frozenset(i.elements) for i in ia.chong}
        assert frozenset({"辰", "戌"}) in chong_pairs

    def test_chong_citation(self):
        c = _chart(datetime(2024, 3, 11, 12, 0))
        ia = detect_interactions(c)
        cite_ids = [cite.rule_id for cite in ia.citations]
        assert "ZP-CHONG" in cite_ids


class TestXing:
    """地支相刑 (branch punishments)."""

    def test_zi_xing_self_punishment(self):
        # 2000-06-15: branches = 辰午辰午 → 辰+辰自刑 + 午+午自刑
        c = _chart(datetime(2000, 6, 15, 12, 0))
        ia = detect_interactions(c)
        # Should have 2 自刑 (辰+辰 and 午+午)
        zi_xing = [i for i in ia.xing if i.kind == "自刑"]
        assert len(zi_xing) >= 2
        xing_chars = {i.elements for i in zi_xing}
        assert ("辰", "辰") in xing_chars or ("辰", "辰") in {tuple(reversed(e)) for e in xing_chars}
        assert ("午", "午") in xing_chars or ("午", "午") in {tuple(reversed(e)) for e in xing_chars}

    def test_san_xing_full(self):
        # 1990-10-15: branches = 午戌丑未 → 丑戌未 full 三刑
        c = _chart(datetime(1990, 10, 15, 14, 0))
        ia = detect_interactions(c)
        san_xing = [i for i in ia.xing if i.kind == "三刑"]
        assert len(san_xing) >= 1
        # The 三刑 should involve 丑戌未
        all_elements = set()
        for i in san_xing:
            all_elements.update(i.elements)
        assert {"丑", "戌", "未"} <= all_elements

    def test_xing_citation(self):
        c = _chart(datetime(2000, 6, 15, 12, 0))
        ia = detect_interactions(c)
        cite_ids = [cite.rule_id for cite in ia.citations]
        assert "ZP-XING" in cite_ids


class TestHai:
    """地支相害 (branch harms)."""

    def test_table_has_six_pairs(self):
        assert len(HAI_TABLE) == 6

    def test_mao_chen_hai_detected(self):
        # YangRen 2024: branches = 辰卯戌午 → 卯+辰 害
        c = _chart(datetime(2024, 3, 11, 12, 0))
        ia = detect_interactions(c)
        assert len(ia.hai) >= 1
        hai_pairs = {frozenset(i.elements) for i in ia.hai}
        assert frozenset({"辰", "卯"}) in hai_pairs

    def test_hai_citation(self):
        c = _chart(datetime(2024, 3, 11, 12, 0))
        ia = detect_interactions(c)
        cite_ids = [cite.rule_id for cite in ia.citations]
        assert "ZP-HAI" in cite_ids


class TestInteractionResult:
    """InteractionResult data structure methods."""

    def test_has_any_true_when_interactions_exist(self):
        c = _chart(datetime(2000, 6, 15, 12, 0))
        ia = detect_interactions(c)
        assert ia.has_any() is True

    def test_summary_returns_string(self):
        c = _chart(datetime(2000, 6, 15, 12, 0))
        ia = detect_interactions(c)
        s = ia.summary()
        assert isinstance(s, str)
        assert "刑" in s

    def test_all_interactions_flattens(self):
        c = _chart(datetime(2000, 6, 15, 12, 0))
        ia = detect_interactions(c)
        flat = ia.all_interactions()
        assert isinstance(flat, tuple)
        assert len(flat) > 0


class TestInteractionDataclass:
    """Interaction frozen dataclass."""

    def test_interaction_is_frozen(self):
        c = _chart(datetime(2000, 6, 15, 12, 0))
        ia = detect_interactions(c)
        if ia.xing:
            with pytest.raises(Exception):
                ia.xing[0].kind = "test"


class TestDeterminism:
    """Same chart → same interactions."""

    def test_same_chart_same_interactions(self):
        a = detect_interactions(_chart(datetime(1893, 12, 26, 8, 0), 112.9))
        b = detect_interactions(_chart(datetime(1893, 12, 26, 8, 0), 112.9))
        assert a == b

    def test_same_chart_same_interactions_2000(self):
        a = detect_interactions(_chart(datetime(2000, 6, 15, 12, 0)))
        b = detect_interactions(_chart(datetime(2000, 6, 15, 12, 0)))
        assert a == b


class TestEngineIntegration:
    """The diagnose() pipeline includes interactions."""

    def test_diagnosis_has_interactions_field(self):
        from bazibase import diagnose
        c = _chart(datetime(2000, 6, 15, 12, 0))
        d = diagnose(c)
        assert d.interactions is not None
        assert isinstance(d.interactions, InteractionResult)

    def test_explain_contains_interactions_section(self):
        from bazibase import diagnose
        c = _chart(datetime(2000, 6, 15, 12, 0))
        text = diagnose(c).explain()
        assert "刑冲合化" in text

    def test_to_dict_includes_interactions(self):
        from bazibase import diagnose
        c = _chart(datetime(2000, 6, 15, 12, 0))
        d_dict = diagnose(c).to_dict()
        assert "interactions" in d_dict
        ia = d_dict["interactions"]
        # Check all 8 sub-keys exist
        for key in ("gan_he", "san_he", "ban_he", "san_hui",
                    "ban_hui", "chong", "xing", "hai"):
            assert key in ia
