"""Tests for the constants tables and ten_god computation."""
import pytest
from bazibase import constants as C


class TestStemsAndBranches:
    def test_stem_count(self):
        assert len(C.STEMS) == 10
        assert C.STEMS[0] == "甲"
        assert C.STEMS[-1] == "癸"

    def test_branch_count(self):
        assert len(C.BRANCHES) == 12
        assert C.BRANCHES[0] == "子"
        assert C.BRANCHES[-1] == "亥"

    def test_stem_index_lookup(self):
        for i, s in enumerate(C.STEMS):
            assert C.STEM_INDEX[s] == i

    def test_branch_index_lookup(self):
        for i, b in enumerate(C.BRANCHES):
            assert C.BRANCH_INDEX[b] == i

    def test_stem_polarity_alternates(self):
        # 甲(0)=阳, 乙(1)=阴, 丙(2)=阳, ...
        for i, s in enumerate(C.STEMS):
            assert C.STEM_POLARITY[s] == i % 2

    def test_branch_polarity_alternates(self):
        for i, b in enumerate(C.BRANCHES):
            assert C.BRANCH_POLARITY[b] == i % 2

    def test_stem_element_assignment(self):
        # 木火土金水, 2 stems each
        expected = {
            "甲": "木", "乙": "木",
            "丙": "火", "丁": "火",
            "戊": "土", "己": "土",
            "庚": "金", "辛": "金",
            "壬": "水", "癸": "水",
        }
        for stem, el in expected.items():
            assert C.STEM_ELEMENT[stem] == el

    def test_branch_element_assignment(self):
        expected = {
            "寅": "木", "卯": "木",
            "巳": "火", "午": "火",
            "申": "金", "酉": "金",
            "亥": "水", "子": "水",
            "辰": "土", "戌": "土", "丑": "土", "未": "土",
        }
        for b, el in expected.items():
            assert C.BRANCH_ELEMENT[b] == el


class TestHiddenStems:
    def test_all_branches_have_hidden_stems(self):
        for b in C.BRANCHES:
            assert b in C.BRANCH_HIDDEN_STEMS
            assert len(C.BRANCH_HIDDEN_STEMS[b]) >= 1

    def test_single_hidden_stems(self):
        # 子卯酉 have exactly one hidden stem (本气 only)
        assert C.BRANCH_HIDDEN_STEMS["子"] == ("癸",)
        assert C.BRANCH_HIDDEN_STEMS["卯"] == ("乙",)
        assert C.BRANCH_HIDDEN_STEMS["酉"] == ("辛",)

    def test_specific_hidden_stems(self):
        assert C.BRANCH_HIDDEN_STEMS["寅"] == ("甲", "丙", "戊")
        assert C.BRANCH_HIDDEN_STEMS["辰"] == ("戊", "乙", "癸")
        assert C.BRANCH_HIDDEN_STEMS["申"] == ("庚", "壬", "戊")
        assert C.BRANCH_HIDDEN_STEMS["亥"] == ("壬", "甲")

    def test_hidden_stem_elements_are_consistent(self):
        # The primary (本气) hidden stem element should match the branch element.
        from bazibase.constants import BRANCH_ELEMENT, STEM_ELEMENT
        for b in C.BRANCHES:
            primary = C.BRANCH_HIDDEN_STEMS[b][0]
            assert STEM_ELEMENT[primary] == BRANCH_ELEMENT[b], (
                f"Branch {b} element mismatch: branch={BRANCH_ELEMENT[b]}, "
                f"primary hidden {primary} element={STEM_ELEMENT[primary]}"
            )


class TestTenGod:
    def test_self_is_bi_jian(self):
        assert C.ten_god("甲", "甲") == "比肩"
        assert C.ten_god("丁", "丁") == "比肩"

    def test_same_element_diff_polarity_is_jie_cai(self):
        assert C.ten_god("甲", "乙") == "劫财"  # 阳木 vs 阴木
        assert C.ten_god("丁", "丙") == "劫财"  # 阴火 vs 阳火

    def test_i_produce_same_polarity_is_shi_shen(self):
        # 甲(阳木)生 丙(阳火) -> 食神
        assert C.ten_god("甲", "丙") == "食神"
        # 丁(阴火)生 己(阴土) -> 食神
        assert C.ten_god("丁", "己") == "食神"

    def test_i_produce_diff_polarity_is_shang_guan(self):
        # 甲(阳木)生 丁(阴火) -> 伤官
        assert C.ten_god("甲", "丁") == "伤官"
        # 丁(阴火)生 戊(阳土) -> 伤官
        assert C.ten_god("丁", "戊") == "伤官"

    def test_i_conquer_same_polarity_is_pian_cai(self):
        # 甲(阳木)克 戊(阳土) -> 偏财
        assert C.ten_god("甲", "戊") == "偏财"

    def test_i_conquer_diff_polarity_is_zheng_cai(self):
        # 甲(阳木)克 己(阴土) -> 正财
        assert C.ten_god("甲", "己") == "正财"

    def test_conquers_me_same_polarity_is_qi_sha(self):
        # 庚(阳金)克 甲(阳木) -> 七杀
        assert C.ten_god("甲", "庚") == "七杀"

    def test_conquers_me_diff_polarity_is_zheng_guan(self):
        # 辛(阴金)克 甲(阳木) -> 正官
        assert C.ten_god("甲", "辛") == "正官"

    def test_produces_me_same_polarity_is_pian_yin(self):
        # 壬(阳水)生 甲(阳木) -> 偏印
        assert C.ten_god("甲", "壬") == "偏印"

    def test_produces_me_diff_polarity_is_zheng_yin(self):
        # 癸(阴水)生 甲(阳木) -> 正印
        assert C.ten_god("甲", "癸") == "正印"

    def test_invalid_stem_raises(self):
        with pytest.raises(ValueError):
            C.ten_god("X", "甲")
        with pytest.raises(ValueError):
            C.ten_god("甲", "X")

    def test_all_combinations_covered(self):
        """For each pair (DM, other), ten_god must return a valid value."""
        for dm in C.STEMS:
            for other in C.STEMS:
                tg = C.ten_god(dm, other)
                assert tg in C.TEN_GODS


class TestLuckDirection:
    def test_yang_male_forward(self):
        # 甲年男 -> 顺
        assert C.luck_direction(0, "male") == 1

    def test_yang_female_backward(self):
        # 甲年女 -> 逆
        assert C.luck_direction(0, "female") == -1

    def test_yin_male_backward(self):
        # 乙年男 -> 逆
        assert C.luck_direction(1, "male") == -1

    def test_yin_female_forward(self):
        # 乙年女 -> 顺
        assert C.luck_direction(1, "female") == 1

    def test_invalid_gender_raises(self):
        with pytest.raises(ValueError):
            C.luck_direction(0, "other")
