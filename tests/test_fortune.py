"""Tests for 大运/流年 行运事实 (bazibase.rules.fortune).

The engine reports **deterministic facts** (十神 roles + 刑冲合会), not a 吉凶
verdict — weighing 顺逆 is the model's job (确定交引擎、不确定交模型).
"""
from datetime import datetime
import pytest

from bazibase import cast_chart, diagnose, assess_pillar_facts
from bazibase.pillars import _make_pillar


def _pillar(stem: str, branch: str):
    return _make_pillar(stem, branch, "luck")


class TestAssessPillarFacts:
    def test_yong_unknown_when_no_yong_shen(self):
        f = assess_pillar_facts("戊", None, _pillar("壬", "寅"))
        assert f.yong_unknown is True

    def test_ji_shen_stem_role(self):
        # 正财格 忌神 = 比劫. 日主甲, 大运天干甲(比肩) -> 忌.
        f = assess_pillar_facts("甲", "正财", _pillar("甲", "子"))
        assert f.stem.role == "忌"
        assert "破用神" in f.stem.note

    def test_xiang_shen_stem_role(self):
        # 正财格 相神 = 食伤. 日主甲, 天干丙(食神) -> 喜.
        f = assess_pillar_facts("甲", "正财", _pillar("丙", "午"))
        assert f.stem.role == "喜"

    def test_mixed_stem_branch_roles(self):
        # 偏印格: 忌神=财, 相神=官杀. 壬寅: 天干壬(偏财/忌) + 地支甲(七杀/喜).
        f = assess_pillar_facts("戊", "偏印", _pillar("壬", "寅"))
        assert f.stem.role == "忌"
        assert f.branch is not None and f.branch.role == "喜"


class TestUserChartRegression:
    """1997-05-16 08:00 男 铜陵 — '偏财大运好' was wrong. The engine must expose
    the FACT that 偏财 is the 忌神 (破印), so the model won't call it simply good."""

    @pytest.fixture
    def diag(self):
        c = cast_chart(datetime(1997, 5, 16, 8, 0), longitude=117.8,
                       gender="male", reference_year=2026)
        return c, diagnose(c)

    def test_yong_shen_is_pian_yin(self, diag):
        _, d = diag
        assert d.yong_shen.ten_god == "偏印"

    def test_pianecai_luck_stem_is_jishen(self, diag):
        # 当前大运 壬寅: 天干偏财坏印 — 引擎须暴露"天干偏财是忌神(破印)"这个事实.
        c, d = diag
        cp = c.current_period
        f = assess_pillar_facts(
            c.day_master, d.yong_shen.ten_god, cp.luck_pillar.pillar,
            natal_branches=tuple(p.branch for p in c.four_pillars),
        )
        assert cp.luck_pillar.pillar.stem_branch == "壬寅"
        assert f.stem.role == "忌"          # 天干偏财是忌神(破印)
        assert "破用神" in f.stem.note

    def test_no_verdict_anymore(self, diag):
        c, d = diag
        f = assess_pillar_facts(c.day_master, d.yong_shen.ten_god, c.current_period.liunian)
        assert not hasattr(f, "verdict")    # 吉凶判断已交给模型

    def test_serialization_shape(self, diag):
        c, d = diag
        f = assess_pillar_facts(c.day_master, d.yong_shen.ten_god, c.current_period.liunian)
        out = f.to_dict()
        assert set(out.keys()) == {"pillar", "stem", "branch", "relations", "yong_unknown"}
        assert "verdict" not in out
        assert set(out["stem"].keys()) == {"char", "ten_god", "role", "note"}


class TestLiunianAcrossDayun:
    """流年×大运 relationships appear only when luck_branch is supplied (综合看)."""

    def test_liunian_relations_are_factual_strings(self):
        c = cast_chart(datetime(1990, 6, 15, 14, 30), longitude=121.0,
                       gender="male", reference_year=2026)
        d = diagnose(c)
        cp = c.current_period
        f = assess_pillar_facts(
            c.day_master, d.yong_shen.ten_god, cp.liunian,
            natal_branches=tuple(p.branch for p in c.four_pillars),
            luck_branch=cp.luck_pillar.pillar.branch,
        )
        assert isinstance(f.relations, tuple)
        assert all(isinstance(r, str) for r in f.relations)


class TestRelationPolarity:
    """论行运·关系方向标（子平真诠）：冲去忌神/成用神局为利，冲去喜用/成克用局为不利。
    只对极性单一确定的两类表态；六合/刑/害与『用神未定』一律不表态。"""

    def _rels(self, dm, yong, stem, branch, natal):
        f = assess_pillar_facts(dm, yong, _pillar(stem, branch), natal_branches=natal)
        return f.relations

    def test_chong_jishen_is_favorable(self):
        # 偏印格(戊)：偏财=忌神(亥本气壬=偏财)。巳冲命局亥 → 冲去忌神，利。
        rels = self._rels("戊", "偏印", "丁", "巳", ("亥",))
        assert any("冲去忌神，对你有利" in r for r in rels), rels

    def test_chong_xiyong_is_unfavorable(self):
        # 偏印格(戊)：七杀=相神/喜用(寅本气甲=七杀)。申冲命局寅 → 冲去喜用，不利。
        rels = self._rels("戊", "偏印", "庚", "申", ("寅",))
        assert any("冲去喜用，对你不利" in r for r in rels), rels

    def test_yong_ju_is_favorable(self):
        # 真盘回归：偏印格用神五行=火，大运壬寅与命局午半合火局 → 成用神局，利。
        c = cast_chart(datetime(1997, 5, 16, 8, 0), longitude=117.8,
                       gender="male", reference_year=2026)
        d = diagnose(c)
        f = assess_pillar_facts(
            c.day_master, d.yong_shen.ten_god, c.current_period.luck_pillar.pillar,
            natal_branches=tuple(p.branch for p in c.four_pillars),
        )
        assert any("用神五行），对你有利" in r for r in f.relations), f.relations

    def test_ke_yong_ju_is_unfavorable(self):
        # 偏印格用神五行=火；子与命局申、辰成三合水局，水克火 → 成克用局，不利。
        rels = self._rels("戊", "偏印", "甲", "子", ("申", "辰"))
        assert any("克用神五行），对你不利" in r for r in rels), rels

    def test_no_polarity_when_yong_unknown(self):
        # 用神未定：关系仍记事实，但一律不表态利/不利（喜忌待判）。
        rels = self._rels("戊", None, "庚", "申", ("寅",))
        assert rels  # 冲命局寅 仍在
        assert not any("对你有利" in r or "对你不利" in r for r in rels), rels

    def test_liuhe_and_xing_stay_untagged(self):
        # 六合/刑方向不单一，只记事实、不表态（留给模型权衡）。
        rels = self._rels("戊", "偏印", "丁", "巳", ("申",))  # 巳申六合(+相刑)
        assert any("六合" in r for r in rels), rels
        assert not any("六合" in r and ("对你有利" in r or "对你不利" in r) for r in rels), rels
