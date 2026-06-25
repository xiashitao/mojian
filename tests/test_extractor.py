"""Regex-fallback extraction (LLM-free path) for the chat agent."""
from web.backend.agent import extractor


def test_extract_time_ignores_branch_hours():
    # Product decision: only concrete clock times are accepted; 地支时辰
    # (子时/辰时/…) are NOT converted — the agent must ask for the exact time.
    assert extractor._extract_time("辰时") is None
    assert extractor._extract_time("子时出生") is None
    assert extractor._extract_time("午时") is None
    assert extractor._extract_time("亥时") is None


def test_extract_time_digits_and_rough():
    assert extractor._extract_time("8:30") == "08:30"
    assert extractor._extract_time("8点半") == "08:30"
    assert extractor._extract_time("晚上9点") == "21:00"
    assert extractor._extract_time("早上") == "08:00"


def test_extract_time_absent():
    assert extractor._extract_time("我想问事业") is None


def test_extract_date_variants():
    assert extractor._extract_date("1990-05-15") == "1990-05-15"
    assert extractor._extract_date("1990年5月15日") == "1990-05-15"
    assert extractor._extract_date("没有日期") is None


def test_extract_place_and_gender():
    place, lon = extractor._extract_place("北京出生")
    assert place == "北京"
    assert lon == 116.4
    assert extractor._extract_gender("男") == "male"
    assert extractor._extract_gender("女生") == "female"
    assert extractor._extract_gender("没说性别") is None
