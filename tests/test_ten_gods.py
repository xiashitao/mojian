"""Tests for ten-god labeling."""
from datetime import datetime
import pytest
from bazibase.pillars import compute_four_pillars
from bazibase.ten_gods import label_ten_gods, TenGodLabels


class TestLabelTenGods:
    def setup_method(self):
        # 1893-12-26 辰时 -> 癸巳/甲子/丁酉/甲辰, day master 丁
        self.fp = compute_four_pillars(datetime(1893, 12, 26, 8, 0))
        self.labels = label_ten_gods(self.fp)

    def test_day_stem_is_ri_zhu(self):
        s, _ = self.labels.at_position("day")
        assert s.ten_god == "日主"
        assert s.stem == "丁"

    def test_year_stem_label(self):
        # Year 癸 vs day master 丁火. 癸水克火, 同性(都是阴? 癸阴, 丁阴) -> 七杀.
        s, _ = self.labels.at_position("year")
        assert s.stem == "癸"
        assert s.ten_god == "七杀"

    def test_month_stem_label(self):
        # Month 甲 vs 丁. 甲木生丁火, 异性 (甲阳, 丁阴) -> 正印.
        s, _ = self.labels.at_position("month")
        assert s.stem == "甲"
        assert s.ten_god == "正印"

    def test_hour_stem_label(self):
        # Hour 甲 vs 丁. Same as month 甲: 正印.
        s, _ = self.labels.at_position("hour")
        assert s.stem == "甲"
        assert s.ten_god == "正印"

    def test_year_branch_hidden_labels(self):
        # Year 巳 hidden: 丙(本气)/庚(中气)/戊(余气)
        # vs 丁: 丙=劫财, 庚=正财, 戊=伤官
        _, hidden = self.labels.at_position("year")
        assert len(hidden) == 3
        benqi = hidden[0]
        assert benqi.stem == "丙"
        assert benqi.role == "本气"
        assert benqi.ten_god == "劫财"
        zhongqi = hidden[1]
        assert zhongqi.stem == "庚"
        assert zhongqi.ten_god == "正财"
        yuqi = hidden[2]
        assert yuqi.stem == "戊"
        assert yuqi.ten_god == "伤官"

    def test_month_branch_hidden_labels(self):
        # Month 子 hidden: 癸(本气). vs 丁: 七杀.
        _, hidden = self.labels.at_position("month")
        assert len(hidden) == 1
        assert hidden[0].stem == "癸"
        assert hidden[0].ten_god == "七杀"

    def test_day_branch_hidden_labels(self):
        # Day 酉 hidden: 辛(本气). vs 丁: 偏财 (辛阴金克丁阴火, 同性 -> 偏财)
        _, hidden = self.labels.at_position("day")
        assert len(hidden) == 1
        assert hidden[0].stem == "辛"
        assert hidden[0].ten_god == "偏财"

    def test_hour_branch_hidden_labels(self):
        # Hour 辰 hidden: 戊(本气)/乙(中气)/癸(余气)
        # vs 丁: 戊=伤官, 乙=偏印, 癸=七杀
        _, hidden = self.labels.at_position("hour")
        assert len(hidden) == 3
        tg_set = {(h.stem, h.role, h.ten_god) for h in hidden}
        assert ("戊", "本气", "伤官") in tg_set
        assert ("乙", "中气", "偏印") in tg_set
        assert ("癸", "余气", "七杀") in tg_set

    def test_all_stems_labeled(self):
        assert len(self.labels.stems) == 4
        positions = {s.position for s in self.labels.stems}
        assert positions == {"year", "month", "day", "hour"}

    def test_at_position_returns_correct_pillar(self):
        for pos in ("year", "month", "day", "hour"):
            s, h = self.labels.at_position(pos)
            assert s.position == pos
            for hs in h:
                assert hs.position == pos
