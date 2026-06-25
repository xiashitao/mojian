"""End-to-end tests for the chart engine."""
from datetime import datetime
import json
import pytest
from bazibase import cast_chart, Chart


class TestCastChart:
    def test_returns_chart_instance(self):
        c = cast_chart(
            birth_time=datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
        )
        assert isinstance(c, Chart)

    def test_known_chart_mao(self):
        c = cast_chart(
            birth_time=datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
        )
        assert c.year_pillar.stem_branch == "癸巳"
        assert c.month_pillar.stem_branch == "甲子"
        assert c.day_pillar.stem_branch == "丁酉"
        assert c.hour_pillar.stem_branch == "甲辰"
        assert c.day_master == "丁"
        # Direction: 癸阴干 + male -> 逆行
        assert c.luck.direction == -1
        assert c.luck.start_age_years == 6

    def test_summary_string_contains_all_pillars(self):
        c = cast_chart(
            birth_time=datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
        )
        s = c.summary()
        assert "癸巳" in s
        assert "甲子" in s
        assert "丁酉" in s
        assert "甲辰" in s
        assert "丁" in s

    def test_to_dict_serializable(self):
        c = cast_chart(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=116.4,
            gender="female",
        )
        d = c.to_dict()
        # Should be JSON-serializable.
        s = json.dumps(d, ensure_ascii=False)
        d2 = json.loads(s)
        assert d2["day_master"] == c.day_master
        assert "four_pillars" in d2
        assert "strength" in d2
        assert "luck" in d2

    def test_to_dict_has_expected_keys(self):
        c = cast_chart(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=116.4,
            gender="female",
        )
        d = c.to_dict()
        assert set(d.keys()) == {
            "input", "standard_clock_time", "dst_applied", "true_solar_time",
            "day_master", "day_master_element",
            "four_pillars", "strength", "luck", "current_period"
        }
        assert set(d["input"].keys()) == {
            "birth_clock_time", "longitude", "tz_offset_hours", "gender"
        }
        assert set(d["four_pillars"].keys()) == {"year", "month", "day", "hour"}

    def test_invalid_gender_raises(self):
        with pytest.raises(ValueError):
            cast_chart(datetime(2000, 1, 1, 12, 0), 116.4, "other")

    def test_tz_aware_datetime_raises(self):
        from datetime import timezone
        with pytest.raises(ValueError):
            cast_chart(
                datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
                116.4,
                "male",
            )

    def test_determinism(self):
        kwargs = dict(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=116.4,
            gender="male",
        )
        a = cast_chart(**kwargs)
        b = cast_chart(**kwargs)
        assert a.to_dict() == b.to_dict()

    def test_solar_time_correction_can_be_disabled(self):
        # When disabled, TST == input; when enabled, they differ by lon+EoT.
        c_with = cast_chart(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=116.4,
            gender="male",
            apply_solar_time_correction=True,
        )
        c_without = cast_chart(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=116.4,
            gender="male",
            apply_solar_time_correction=False,
        )
        # The hour branch should usually still match for a small correction,
        # but the TST values definitely differ.
        assert c_with.true_solar_time != c_without.true_solar_time

    def test_input_provenance_preserved(self):
        c = cast_chart(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=121.5,
            gender="female",
            tz_offset_hours=8.0,
        )
        assert c.birth_clock_time == datetime(2000, 6, 15, 12, 0)
        assert c.longitude == 121.5
        assert c.gender == "female"
        assert c.tz_offset_hours == 8.0

    def test_custom_luck_count(self):
        c = cast_chart(
            birth_time=datetime(2000, 6, 15, 12, 0),
            longitude=116.4,
            gender="male",
            luck_pillar_count=4,
        )
        assert len(c.luck.luck_pillars) == 4

    def test_no_reference_year_leaves_current_period_none(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), longitude=112.9, gender="male")
        assert c.current_period is None
        assert c.to_dict()["current_period"] is None

    def test_reference_year_attaches_current_period(self):
        c = cast_chart(
            datetime(1893, 12, 26, 8, 0),
            longitude=112.9,
            gender="male",
            reference_year=1920,
        )
        assert c.current_period is not None
        assert c.current_period.year == 1920
        assert c.current_period.liunian.stem_branch == "庚申"
        assert c.current_period.luck_pillar.pillar.stem_branch == "辛酉"
        # Serialized form carries it too.
        assert c.to_dict()["current_period"]["luck_pillar"]["stem_branch"] == "辛酉"

    def test_reference_year_is_deterministic(self):
        kwargs = dict(birth_time=datetime(1893, 12, 26, 8, 0), longitude=112.9,
                      gender="male", reference_year=1920)
        assert cast_chart(**kwargs).to_dict() == cast_chart(**kwargs).to_dict()
