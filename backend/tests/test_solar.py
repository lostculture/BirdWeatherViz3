"""
Tests for the local sunrise/sunset calculation.

These times drive the dawn and dusk chorus charts. They used to come from the
weather API, which only ever covers one nominated station — so the reference
values below are that API's own output for the station it did cover, and the
tolerance is what matters: the solar rollup bins to 5 minutes, so anything
inside a couple of minutes is indistinguishable in the charts.
"""

from datetime import date

import pytest

from app.services.solar import sun_times_local, sun_times_utc

# Pittsburgh, station 1 of the live database.
PGH_LAT, PGH_LON, PGH_TZ = 40.4691, -80.0874, "America/New_York"

# (date, sunrise, sunset) as reported by the weather API for that station.
PGH_REFERENCE = [
    (date(2026, 9, 10), "06:56", "19:37"),
    (date(2026, 9, 9), "06:55", "19:39"),
    (date(2026, 9, 8), "06:54", "19:40"),
    (date(2026, 9, 6), "06:52", "19:44"),
    (date(2026, 9, 4), "06:50", "19:47"),
]

TOLERANCE_MINUTES = 3


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


class TestAgainstWeatherApiValues:
    @pytest.mark.parametrize("on_date,sunrise,sunset", PGH_REFERENCE)
    def test_within_tolerance(self, on_date, sunrise, sunset):
        computed = sun_times_local(PGH_LAT, PGH_LON, on_date, PGH_TZ)
        assert computed is not None

        got_rise = computed[0].hour * 60 + computed[0].minute
        got_set = computed[1].hour * 60 + computed[1].minute

        assert abs(got_rise - _minutes(sunrise)) <= TOLERANCE_MINUTES
        assert abs(got_set - _minutes(sunset)) <= TOLERANCE_MINUTES


class TestSeasonalBehaviour:
    def test_summer_days_are_longer_than_winter_days(self):
        summer = sun_times_local(PGH_LAT, PGH_LON, date(2026, 6, 21), PGH_TZ)
        winter = sun_times_local(PGH_LAT, PGH_LON, date(2026, 12, 21), PGH_TZ)

        def length(times):
            rise = times[0].hour * 60 + times[0].minute
            set_ = times[1].hour * 60 + times[1].minute
            return set_ - rise

        # Pittsburgh: ~15h675m at the solstice against ~9h15m at midwinter.
        assert length(summer) > length(winter) + 300

    def test_sunrise_precedes_sunset(self):
        for month in range(1, 13):
            times = sun_times_local(PGH_LAT, PGH_LON, date(2026, month, 15), PGH_TZ)
            assert times[0] < times[1], month

    def test_daylight_saving_shift_is_applied(self):
        # The Sunday the clocks go forward in 2026 is 8 March. Sunrise jumps an
        # hour later in wall-clock terms across that boundary.
        before = sun_times_local(PGH_LAT, PGH_LON, date(2026, 3, 7), PGH_TZ)
        after = sun_times_local(PGH_LAT, PGH_LON, date(2026, 3, 9), PGH_TZ)
        jump = (after[0].hour * 60 + after[0].minute) - (
            before[0].hour * 60 + before[0].minute
        )
        assert 50 <= jump <= 70


class TestExtremeLatitudes:
    def test_polar_night_has_no_sunrise(self):
        # Longyearbyen in December: the sun never rises.
        assert sun_times_utc(78.22, 15.65, date(2026, 12, 21)) is None

    def test_midnight_sun_has_no_sunset(self):
        assert sun_times_utc(78.22, 15.65, date(2026, 6, 21)) is None

    def test_equator_is_close_to_twelve_hours_year_round(self):
        for month in (3, 6, 9, 12):
            rise, set_ = sun_times_utc(0.0, 0.0, date(2026, month, 21))
            assert 700 <= (set_ - rise) <= 740  # minutes


class TestTimezoneHandling:
    def test_unknown_timezone_falls_back_to_longitude(self):
        # Must not raise; the longitude offset is a reasonable approximation.
        times = sun_times_local(PGH_LAT, PGH_LON, date(2026, 6, 21), "Not/AZone")
        assert times is not None
        assert times[0] < times[1]

    def test_missing_timezone_falls_back_to_longitude(self):
        times = sun_times_local(PGH_LAT, PGH_LON, date(2026, 6, 21), None)
        assert times is not None
        assert times[0] < times[1]

    def test_southern_hemisphere(self):
        # Sydney in January is high summer, so the day is long.
        times = sun_times_local(-33.87, 151.21, date(2026, 1, 15), "Australia/Sydney")
        assert times is not None
        length = (times[1].hour * 60 + times[1].minute) - (
            times[0].hour * 60 + times[0].minute
        )
        assert length > 13 * 60
