"""Tests for the agent-layer DST disambiguation logic."""
from web.backend.agent.dst_check import (
    analyze_dst,
    resolve_dst_choice,
    OPTION_WAS_DST_CLOCK,
    OPTION_ALREADY_STANDARD,
)
from web.backend.agent.models import BirthInfo


def _birth(date, time, longitude=120.0, gender="male"):
    return BirthInfo(birth_date=date, birth_time=time, longitude=longitude, gender=gender)


class TestAnalyzeDst:
    def test_non_dst_year_is_noop(self):
        a = analyze_dst(_birth("2024-07-01", "09:10"))
        assert a.in_dst_window is False
        assert a.needs_confirmation is False

    def test_winter_dst_year_is_noop(self):
        # 1988 but January — outside the summer DST window.
        a = analyze_dst(_birth("1988-01-01", "09:10"))
        assert a.in_dst_window is False

    def test_dst_boundary_sensitive_asks(self):
        # 1988 summer, 09:10 at 120°E: DST -> 08:10 (辰), standard -> 09:10 (巳).
        a = analyze_dst(_birth("1988-07-01", "09:10"))
        assert a.in_dst_window is True
        assert a.needs_confirmation is True
        assert a.hour_branch_as_dst == "辰"
        assert a.hour_branch_as_standard == "巳"
        assert a.question and "夏令时" in a.question
        assert a.options == [OPTION_WAS_DST_CLOCK, OPTION_ALREADY_STANDARD]

    def test_dst_mid_hour_does_not_ask(self):
        # 1988 summer, 12:30 at 120°E: DST -> 11:30 (午), standard -> 12:30 (午).
        # Same 时辰 either way, so no need to bother the user.
        a = analyze_dst(_birth("1988-07-01", "12:30"))
        assert a.in_dst_window is True
        assert a.needs_confirmation is False
        assert a.hour_branch_as_dst == a.hour_branch_as_standard == "午"
        assert a.question is None

    def test_partial_birth_info_is_noop(self):
        a = analyze_dst(BirthInfo(birth_date="1988-07-01"))  # no time / longitude
        assert a.in_dst_window is False
        assert a.needs_confirmation is False


class TestResolveDstChoice:
    def test_wall_clock_answer_means_apply_correction(self):
        assert resolve_dst_choice(OPTION_WAS_DST_CLOCK) is True
        assert resolve_dst_choice("就是当时钟表上的点") is True

    def test_standard_answer_means_no_correction(self):
        assert resolve_dst_choice(OPTION_ALREADY_STANDARD) is False
        assert resolve_dst_choice("已经是标准时间了") is False
        assert resolve_dst_choice("我换算过了") is False

    def test_unclear_answer_is_none(self):
        assert resolve_dst_choice("不知道") is None
        assert resolve_dst_choice("") is None
        assert resolve_dst_choice(None) is None
