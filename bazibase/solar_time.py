"""
bazibase.solar_time
===================

True solar time (真太阳时) correction.

The hour pillar of a Ba Zi chart depends on the actual solar time at the
birth location, not the wall-clock time. Two corrections are required:

1. **Longitude correction (经度修正)** — convert from standard-zone clock
   time to local mean solar time. Every degree east of the zone's
   reference meridian adds 4 minutes.

2. **Equation of time (均时差)** — correct for the fact that the sun
   doesn't cross the meridian exactly at noon every day due to Earth's
   elliptical orbit and axial tilt. This oscillates between roughly
   -14 and +16 minutes across the year.

Final formula:

    true_solar_time = clock_time
                    + (longitude - reference_longitude) * 4 min/deg
                    + equation_of_time

Convention used here: input datetimes are treated as naive wall-clock
time in the zone given by `tz_offset_hours`. The reference longitude for
that zone is `15 * tz_offset_hours` (e.g. 120°E for UTC+8).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta


# Reference longitudes for common zones.
# Zone = UTC+8 (China) -> reference meridian 120°E
# Zone = UTC-5 (US Eastern) -> 75°W (i.e. -75)
# Note: some real-world zones are politically offset from their
# reference meridian (e.g. China uses 120°E for the whole country).
def reference_longitude(tz_offset_hours: float) -> float:
    return 15.0 * tz_offset_hours


def equation_of_time_minutes(dt: datetime) -> float:
    """
    Approximate the equation of time in minutes for the given date.

    Uses the Spencer/Spencer-style formula. Accuracy: within ~0.5 minute
    of high-precision ephemeris values, which is more than sufficient for
    Ba Zi purposes (hour branches are 2 hours wide).

    Returns:
        Offset in minutes to ADD to local mean solar time to get true
        solar time. Positive means the sun is "ahead" of mean noon.
    """
    # Day of year (N). Use Jan 1 as N=1.
    start_of_year = datetime(dt.year, 1, 1)
    n = (dt - start_of_year).days + 1

    # Spencer's formula angle (radians).
    b = 2.0 * math.pi * (n - 81) / 365.0

    # Standard approximation.
    eot_min = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    return eot_min


def to_true_solar_time(
    clock_time: datetime,
    longitude: float,
    tz_offset_hours: float = 8.0,
) -> datetime:
    """
    Convert a wall-clock time at a given longitude to true solar time.

    Args:
        clock_time: Naive wall-clock datetime in the zone indicated by
            `tz_offset_hours`. Should NOT carry timezone info — we treat
            it as "the time the clock on the wall showed".
        longitude: Birth location longitude, east positive, west negative.
            Beijing ≈ 116.4, Shanghai ≈ 121.5.
        tz_offset_hours: Timezone offset of the input clock_time relative
            to UTC. Default 8.0 for China standard time (北京时间).

    Returns:
        Naive datetime representing the true solar time at the birth
        location. This is the value that should be fed to the pillar
        computation engine.

    Examples:
        # 1990-05-15 08:30 Beijing clock time, Beijing longitude
        >>> from datetime import datetime
        >>> t = datetime(1990, 5, 15, 8, 30)
        >>> to_true_solar_time(t, longitude=116.4)
        datetime.datetime(1990, 5, 15, 8, 17, 42)  # approx

        # Same clock time in far-western China (Urumqi ≈ 87.6°E)
        >>> to_true_solar_time(t, longitude=87.6)
        datetime.datetime(1990, 5, 15, 6, 25)  # approx — ~2h earlier
    """
    if clock_time.tzinfo is not None:
        raise ValueError(
            "clock_time must be a naive (timezone-unaware) datetime. "
            "Pass tz_offset_hours separately instead."
        )

    ref_lon = reference_longitude(tz_offset_hours)

    # Longitude correction: every degree east of reference meridian
    # adds 4 minutes to local mean solar time.
    lon_delta_deg = longitude - ref_lon
    lon_correction = timedelta(minutes=lon_delta_deg * 4.0)

    # Equation of time correction.
    eot = equation_of_time_minutes(clock_time)
    eot_correction = timedelta(minutes=eot)

    true_solar = clock_time + lon_correction + eot_correction
    return true_solar


__all__ = [
    "reference_longitude",
    "equation_of_time_minutes",
    "to_true_solar_time",
]
