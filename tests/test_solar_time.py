"""Tests for the true solar time correction."""
from datetime import datetime
import math
import pytest
from bazibase.solar_time import (
    to_true_solar_time,
    equation_of_time_minutes,
    reference_longitude,
)


class TestReferenceLongitude:
    def test_utc8_is_120(self):
        assert reference_longitude(8.0) == 120.0

    def test_utc0_is_0(self):
        assert reference_longitude(0.0) == 0.0

    def test_utc_minus5_is_minus75(self):
        assert reference_longitude(-5.0) == -75.0


class TestEquationOfTime:
    def test_within_reasonable_range(self):
        # EoT oscillates between roughly -14 and +16 minutes.
        for day in range(1, 366):
            dt = datetime(2024, 1, 1)
            dt = dt.replace(month=1, day=1)
            from datetime import timedelta
            dt = datetime(2024, 1, 1) + timedelta(days=day - 1)
            eot = equation_of_time_minutes(dt)
            assert -20 < eot < 20, f"EoT out of range at day {day}: {eot}"

    def test_known_value_november(self):
        # Around Nov 3, EoT is at its maximum positive (~+16 min).
        dt = datetime(2024, 11, 3, 12, 0)
        eot = equation_of_time_minutes(dt)
        assert eot > 10, f"Expected EoT > 10 near Nov 3, got {eot}"

    def test_known_value_february(self):
        # Around Feb 11, EoT is at its maximum negative (~-14 min).
        dt = datetime(2024, 2, 11, 12, 0)
        eot = equation_of_time_minutes(dt)
        assert eot < -10, f"Expected EoT < -10 near Feb 11, got {eot}"


class TestToTrueSolarTime:
    def test_beijing_no_correction_at_120(self):
        # At 120°E (the reference meridian for UTC+8), longitude correction is 0.
        # Only EoT remains.
        t = datetime(2024, 6, 15, 12, 0)
        tst = to_true_solar_time(t, longitude=120.0, tz_offset_hours=8.0)
        eot = equation_of_time_minutes(t)
        expected_delta_minutes = eot
        delta = (tst - t).total_seconds() / 60
        assert abs(delta - expected_delta_minutes) < 0.01

    def test_longitude_correction_west_of_reference(self):
        # At 116.4°E (Beijing), 3.6° west of 120°E.
        # Mean solar time should be 3.6 * 4 = 14.4 minutes earlier.
        t = datetime(2024, 6, 15, 12, 0)
        # Pick a date with negligible EoT to isolate longitude effect.
        # Around June 13, EoT is near 0.
        t = datetime(2024, 6, 13, 12, 0)
        tst = to_true_solar_time(t, longitude=116.4, tz_offset_hours=8.0)
        eot = equation_of_time_minutes(t)
        # Expected delta = (116.4 - 120) * 4 + eot
        expected_delta = (116.4 - 120.0) * 4.0 + eot
        actual_delta = (tst - t).total_seconds() / 60
        assert abs(actual_delta - expected_delta) < 0.01

    def test_shanghai_east_of_reference(self):
        # Shanghai at 121.5°E is 1.5° east of 120°E -> +6 minutes mean.
        t = datetime(2024, 6, 13, 12, 0)
        tst = to_true_solar_time(t, longitude=121.5, tz_offset_hours=8.0)
        eot = equation_of_time_minutes(t)
        expected_delta = (121.5 - 120.0) * 4.0 + eot
        actual_delta = (tst - t).total_seconds() / 60
        assert abs(actual_delta - expected_delta) < 0.01

    def test_naive_datetime_required(self):
        from datetime import timezone
        t = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            to_true_solar_time(t, longitude=120.0)

    def test_returns_naive(self):
        t = datetime(2024, 6, 15, 12, 0)
        tst = to_true_solar_time(t, longitude=120.0)
        assert tst.tzinfo is None

    def test_does_not_mutate_input(self):
        t = datetime(2024, 6, 15, 12, 0)
        original = t
        _ = to_true_solar_time(t, longitude=120.0)
        # datetime is immutable so this is mostly a sanity check.
        assert t == original
