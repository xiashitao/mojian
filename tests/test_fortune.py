"""Tests for 大运/流年 喜忌判断 (bazibase.rules.fortune)."""
from datetime import datetime
import pytest

from bazibase import cast_chart, diagnose, assess_pillar_fortune
from bazibase.pillars import _make_pillar


def _pillar(stem: str, branch: str):
    return _make_pillar(stem, branch, "luck")


class TestAssessPillarFortune:
    def test_undetermined_when_no_yong_shen(self):
        f = assess_pillar_fortune("戊", None, _pillar("壬", "寅"))
        assert f.verdict == "未定"

    def test_ji_shen_stem_is_unfavorable(self):
        # 正财格 忌神 = 比劫. 日主甲, 大运天干甲(比肩) -> 忌 -> 凶.
        f = assess_pillar_fortune("甲", "正财", _pillar("甲", "子"))
        assert f.stem.role == "忌"
        assert f.verdict in ("凶", "参半")

    def test_xiang_shen_stem_is_favorable(self):
        # 正财格 相神 = 食伤. 日主甲, 天干丙(食神) -> 喜.
        f = assess_pillar_fortune("甲", "正财", _pillar("丙", "午"))
        assert f.stem.role == "喜"
        assert f.verdict == "吉"

    def test_mixed_stem_branch_is_canban(self):
        # 偏印格: 忌神=财, 相神=官杀. 壬寅: 天干壬(偏财/忌) + 地支甲(七杀/相) -> 参半.
        f = assess_pillar_fortune("戊", "偏印", _pillar("壬", "寅"))
        assert f.stem.role == "忌"
        assert f.branch.role == "喜"
        assert f.verdict == "参半"


class TestUserChartRegression:
    """The reported case: 1997-05-16 08:00 男 铜陵 — '偏财大运好' was wrong."""

    @pytest.fixture
    def diag(self):
        c = cast_chart(datetime(1997, 5, 16, 8, 0), longitude=117.8,
                       gender="male", reference_year=2026)
        return c, diagnose(c)

    def test_yong_shen_is_pian_yin(self, diag):
        _, d = diag
        assert d.yong_shen.ten_god == "偏印"

    def test_pianecai_luck_is_not_simply_good(self, diag):
        # 当前大运 壬寅: 天干偏财坏印(忌) — 引擎判定绝不能是单纯的「吉/好」.
        c, d = diag
        cp = c.current_period
        f = assess_pillar_fortune(c.day_master, d.yong_shen.ten_god, cp.luck_pillar.pillar)
        assert cp.luck_pillar.pillar.stem_branch == "壬寅"
        assert f.verdict != "吉"          # 关键：不能说成「好运」
        assert f.verdict == "参半"
        assert f.stem.role == "忌"        # 天干偏财是忌神(破印)
        assert "破用神" in f.stem.note

    def test_serialization_shape(self, diag):
        c, d = diag
        f = assess_pillar_fortune(c.day_master, d.yong_shen.ten_god, c.current_period.liunian)
        out = f.to_dict()
        assert set(out.keys()) == {"pillar", "verdict", "stem", "branch", "reason"}
        assert out["verdict"] in ("吉", "凶", "参半", "平", "未定")
