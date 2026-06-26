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
