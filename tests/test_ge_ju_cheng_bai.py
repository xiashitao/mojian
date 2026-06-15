"""Tests for 格局成败 (pattern success/failure) assessment (v0.2.2)."""
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from bazibase import cast_chart
from bazibase.rules.yong_shen import determine_yong_shen
from bazibase.rules.ge_ju import determine_ge_ju
from bazibase.rules.xiang_shen import identify_xiang_ji, StemOccurrence
from bazibase.rules.ge_ju_cheng_bai import (
    assess_cheng_bai, ChengBaiResult,
)


def _diagnose_cb(dt, lon=116.4, gender="male"):
    """Run the full 成败 pipeline and return (chart, ys, gj, xs, cb)."""
    c = cast_chart(dt, lon, gender)
    ys = determine_yong_shen(c)
    gj = determine_ge_ju(c, ys)
    xs = identify_xiang_ji(c, ys)
    cb = assess_cheng_bai(c, ys, gj, xs)
    return c, ys, gj, xs, cb


class TestChengGeVerdict:
    """成格 = 用神已立, 无忌神破坏."""

    def test_random_2000_is_cheng_ge(self):
        # 2000-06-15 has 0 忌神 → 成格
        c, ys, gj, xs, cb = _diagnose_cb(datetime(2000, 6, 15, 12, 0))
        assert cb.verdict == "成格"
        assert cb.source_rule_id == "ZP-CHENG-001"
        assert len(cb.rescue_gods) == 0

    def test_cheng_ge_citation_explains(self):
        c, ys, gj, xs, cb = _diagnose_cb(datetime(2000, 6, 15, 12, 0))
        cite = cb.citations[0]
        assert cite.rule_id == "ZP-CHENG-001"
        assert "用神" in cite.reason
        assert "相神" in cite.reason or "忌神" in cite.reason

    def test_cheng_ge_summary(self):
        c, ys, gj, xs, cb = _diagnose_cb(datetime(2000, 6, 15, 12, 0))
        assert cb.summary() == "成格"


class TestJiuYingVerdict:
    """救应 = 忌神现, 但有相神可制."""

    def test_mao_1893_is_jiu_ying(self):
        # 1893-12-26 七杀格, 忌神(财)现 + 相神(印)现 → 救应
        c, ys, gj, xs, cb = _diagnose_cb(
            datetime(1893, 12, 26, 8, 0), 112.9
        )
        assert cb.verdict == "救应"
        assert cb.source_rule_id == "ZP-JIUYING-001"
        assert len(cb.rescue_gods) > 0

    def test_jiu_ying_rescue_gods_are_xiang_shen(self):
        c, ys, gj, xs, cb = _diagnose_cb(
            datetime(1893, 12, 26, 8, 0), 112.9
        )
        # All rescue gods should be from the 相神 list
        xiang_stems = {(o.stem, o.position, o.location) for o in xs.xiang_shen}
        for g in cb.rescue_gods:
            assert (g.stem, g.position, g.location) in xiang_stems

    def test_jiu_ying_citation_mentions_rescue(self):
        c, ys, gj, xs, cb = _diagnose_cb(
            datetime(1893, 12, 26, 8, 0), 112.9
        )
        cite = cb.citations[0]
        assert cite.rule_id == "ZP-JIUYING-001"
        assert "救神" in cite.conclusion
        assert "反败为成" in cite.conclusion

    def test_jiu_ying_summary_includes_rescue_names(self):
        c, ys, gj, xs, cb = _diagnose_cb(
            datetime(1893, 12, 26, 8, 0), 112.9
        )
        s = cb.summary()
        assert "救应" in s
        assert "救神" in s


class TestBaiGeVerdict:
    """败格 = 忌神现, 无相神可救."""

    def test_mock_bai_ge(self):
        """Construct a scenario where 忌神 exists but 相神 is empty."""
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = "甲"
        mock_ys.ten_god = "正官"
        mock_gj = MagicMock()
        mock_xs = MagicMock()
        # 忌神 non-empty, 相神 empty → 败格
        mock_xs.ji_shen = (StemOccurrence(
            position="hour", location="天干",
            stem="辛", ten_god="伤官",
        ),)
        mock_xs.xiang_shen = ()

        cb = assess_cheng_bai(mock_chart, mock_ys, mock_gj, mock_xs)
        assert cb.verdict == "败格"
        assert cb.source_rule_id == "ZP-BAI-001"
        assert len(cb.rescue_gods) == 0

    def test_bai_ge_citation(self):
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = "甲"
        mock_ys.ten_god = "正官"
        mock_gj = MagicMock()
        mock_xs = MagicMock()
        mock_xs.ji_shen = (StemOccurrence(
            position="hour", location="天干",
            stem="辛", ten_god="伤官",
        ),)
        mock_xs.xiang_shen = ()

        cb = assess_cheng_bai(mock_chart, mock_ys, mock_gj, mock_xs)
        cite = cb.citations[0]
        assert cite.rule_id == "ZP-BAI-001"
        assert "忌神" in cite.reason
        assert "败格" in cite.conclusion

    def test_bai_ge_summary(self):
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = "甲"
        mock_ys.ten_god = "正官"
        mock_gj = MagicMock()
        mock_xs = MagicMock()
        mock_xs.ji_shen = (StemOccurrence(
            position="hour", location="天干",
            stem="辛", ten_god="伤官",
        ),)
        mock_xs.xiang_shen = ()

        cb = assess_cheng_bai(mock_chart, mock_ys, mock_gj, mock_xs)
        assert cb.summary() == "败格"


class TestUnresolvedVerdict:
    """未定 = 用神未定."""

    def test_yong_shen_unresolved_returns_wei_ding(self):
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = None
        mock_ys.ten_god = None
        mock_gj = MagicMock()
        mock_xs = MagicMock()

        cb = assess_cheng_bai(mock_chart, mock_ys, mock_gj, mock_xs)
        assert cb.verdict == "未定"
        assert cb.unresolved is True

    def test_unresolved_summary(self):
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = None
        mock_ys.ten_god = None
        mock_gj = MagicMock()
        mock_xs = MagicMock()

        cb = assess_cheng_bai(mock_chart, mock_ys, mock_gj, mock_xs)
        assert "未定" in cb.summary()

    def test_unusual_ten_god_returns_wei_ding(self):
        """用神十神 not in the 8 standard 格局 also returns 未定."""
        mock_chart = MagicMock()
        mock_ys = MagicMock()
        mock_ys.stem = "甲"
        mock_ys.ten_god = "比肩"  # not in standard table
        mock_gj = MagicMock()
        mock_xs = MagicMock()
        mock_xs.ji_shen = ()
        mock_xs.xiang_shen = ()

        cb = assess_cheng_bai(mock_chart, mock_ys, mock_gj, mock_xs)
        assert cb.verdict == "未定"
        assert cb.unresolved is True


class TestChengBaiCitationsExplain:
    """Citations reference the original 子平真诠 text."""

    def test_cheng_ge_citation_has_original_text(self):
        from bazibase.rules import get_rule
        c, ys, gj, xs, cb = _diagnose_cb(datetime(2000, 6, 15, 12, 0))
        rule = get_rule(cb.source_rule_id)
        assert "相神" in rule.source_text or "成格" in rule.source_text

    def test_jiu_ying_citation_has_original_text(self):
        from bazibase.rules import get_rule
        c, ys, gj, xs, cb = _diagnose_cb(
            datetime(1893, 12, 26, 8, 0), 112.9
        )
        rule = get_rule(cb.source_rule_id)
        assert "救应" in rule.source_text or "反败为成" in rule.source_text


class TestChengBaiDeterminism:
    def test_same_chart_same_verdict(self):
        a = _diagnose_cb(datetime(2000, 6, 15, 12, 0))[4]
        b = _diagnose_cb(datetime(2000, 6, 15, 12, 0))[4]
        assert a == b

    def test_same_chart_same_verdict_mao(self):
        a = _diagnose_cb(datetime(1893, 12, 26, 8, 0), 112.9)[4]
        b = _diagnose_cb(datetime(1893, 12, 26, 8, 0), 112.9)[4]
        assert a == b


class TestChengBaiResultIsFrozen:
    """ChengBaiResult is a frozen dataclass."""

    def test_result_is_frozen(self):
        c, ys, gj, xs, cb = _diagnose_cb(datetime(2000, 6, 15, 12, 0))
        with pytest.raises(Exception):
            cb.verdict = "败格"  # should raise FrozenInstanceError
