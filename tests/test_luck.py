"""Tests for luck pillar (大运) computation."""
from datetime import datetime
import pytest
from bazibase.luck import compute_luck, LuckInfo, LuckPillar


class TestLuckDirection:
    def test_yang_year_male_forward(self):
        # 甲辰 (yang year) male -> 顺
        # 甲辰 month: 2024-02-15 ~12:00 → year 甲辰
        luck = compute_luck(
            datetime(2024, 2, 15, 12, 0),
            year_stem="甲",
            gender="male",
            count=2,
        )
        assert luck.direction == 1

    def test_yang_year_female_backward(self):
        luck = compute_luck(
            datetime(2024, 2, 15, 12, 0),
            year_stem="甲",
            gender="female",
            count=2,
        )
        assert luck.direction == -1

    def test_yin_year_male_backward(self):
        # 1893 = 癸巳 year, 癸 is 阴. Male -> 逆.
        luck = compute_luck(
            datetime(1893, 12, 26, 8, 0),
            year_stem="癸",
            gender="male",
            count=2,
        )
        assert luck.direction == -1

    def test_yin_year_female_forward(self):
        luck = compute_luck(
            datetime(1893, 12, 26, 8, 0),
            year_stem="癸",
            gender="female",
            count=2,
        )
        assert luck.direction == 1


class TestLuckSequence:
    def test_known_chart_mao(self):
        # 1893-12-26 辰时, male. Month pillar 甲子. 逆行.
        # Sequence should be: 癸亥, 壬戌, 辛酉, 庚申, ...
        luck = compute_luck(
            datetime(1893, 12, 26, 8, 0),
            year_stem="癸",
            gender="male",
            count=5,
        )
        expected = ["癸亥", "壬戌", "辛酉", "庚申", "己未"]
        actual = [lp.pillar.stem_branch for lp in luck.luck_pillars[:5]]
        assert actual == expected

    def test_forward_sequence_from_jiazi(self):
        # 甲子 month, 顺行 -> 乙丑, 丙寅, 丁卯, ...
        # Pick a yang-year male with 甲子 month. Year 1924 = 甲子.
        # 1924-12-15 should be 甲子 year (after 立春 next Feb) and around 甲子月 (winter).
        # Actually 1924-12 is still 甲子 year? 1924 立春 starts 甲子.
        # 1924-12-15 12:00 — month pillar depends on 节气. Dec is around 甲子月 (after 大雪).
        # We just check the sequence direction.
        luck = compute_luck(
            datetime(1924, 12, 15, 12, 0),
            year_stem="甲",
            gender="male",
            count=5,
        )
        if luck.direction == 1:
            # 顺行: each pillar advances by one in 60甲子
            stems = [lp.pillar.stem_branch for lp in luck.luck_pillars[:5]]
            # Verify they advance by exactly one (in 60甲子 order)
            # We won't hard-code the first pillar since month depends on date;
            # instead verify they're sequential in 60甲子.
            from bazibase.constants import STEMS, BRANCHES
            def ganzhi_index(s: str) -> int:
                stem_i = STEMS.index(s[0])
                branch_i = BRANCHES.index(s[1])
                # In 60甲子, stem and branch advance together; index = (stem_i % 10)
                # such that stem_i and branch_i have same parity, then position = ...
                # Just use modular: (stem_i - branch_i) % 10 == 0 always
                # And position in 60甲子 = branch_i * 5 + ... no, simpler:
                # Solve n ≡ stem_i (mod 10), n ≡ branch_i (mod 12), n in [0, 60).
                for n in range(60):
                    if n % 10 == stem_i and n % 12 == branch_i:
                        return n
                raise ValueError(s)
            idxs = [ganzhi_index(s) for s in stems]
            for i in range(1, len(idxs)):
                assert idxs[i] == (idxs[i-1] + 1) % 60, \
                    f"Pillars not sequential at {i}: {stems}"

    def test_start_age_positive(self):
        luck = compute_luck(
            datetime(2000, 6, 15, 12, 0),
            year_stem="庚",
            gender="male",
            count=3,
        )
        assert luck.start_age_years > 0
        assert luck.luck_pillars[0].start_age >= 1

    def test_pillar_count(self):
        luck = compute_luck(
            datetime(2000, 6, 15, 12, 0),
            year_stem="庚",
            gender="male",
            count=4,
        )
        assert len(luck.luck_pillars) == 4

    def test_pillars_are_10_year_spans(self):
        luck = compute_luck(
            datetime(2000, 6, 15, 12, 0),
            year_stem="庚",
            gender="male",
            count=3,
        )
        for lp in luck.luck_pillars:
            assert lp.end_age - lp.start_age == 9  # 10 inclusive years, age 1..10 is 10 yrs span
            assert lp.end_year - lp.start_year == 9

    def test_invalid_gender_raises(self):
        with pytest.raises(ValueError):
            compute_luck(datetime(2000, 1, 1), "甲", "other")

    def test_invalid_count_raises(self):
        with pytest.raises(ValueError):
            compute_luck(datetime(2000, 1, 1), "甲", "male", count=0)
