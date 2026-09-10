"""
Solar Times Service
Computes sunrise and sunset for a station and date, from its coordinates.

The dawn and dusk chorus charts need sunrise/sunset for the station a detection
came from. Those times used to come from the weather table, but weather is
fetched for a single nominated station (``weather_station_id``) — so on a
multi-station setup every other station had no sun times, and its detections
never reached the chorus charts at all. On the Pittsburgh instance that meant
every bat detection was invisible: all of them are at a station with no weather.

Sunrise and sunset depend only on latitude, longitude and date, so there is no
reason to involve a weather API. This computes them locally with the standard
NOAA solar position algorithm — pure Python, no dependency, works offline.

Accuracy is around a minute, which is far finer than the 5-minute bins the
solar rollup stores.

Version: 1.0.0
"""

import logging
from datetime import date as date_type, datetime, time, timedelta, timezone
from math import acos, cos, degrees, pi, radians, sin, tan
from typing import Optional, Tuple

try:  # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - the app requires 3.11+
    ZoneInfo = None  # type: ignore

logger = logging.getLogger(__name__)

# Solar zenith for sunrise/sunset, in degrees. The extra 0.833 accounts for
# atmospheric refraction and the sun's apparent radius — this is the standard
# "official" sunrise definition, and matches what weather APIs report.
ZENITH = 90.833


def _equation_of_time_and_declination(gamma: float) -> Tuple[float, float]:
    """NOAA equation of time (minutes) and solar declination (radians)."""
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma)
        - 0.040849 * sin(2 * gamma)
    )
    declination = (
        0.006918
        - 0.399912 * cos(gamma)
        + 0.070257 * sin(gamma)
        - 0.006758 * cos(2 * gamma)
        + 0.000907 * sin(2 * gamma)
        - 0.002697 * cos(3 * gamma)
        + 0.001480 * sin(3 * gamma)
    )
    return eqtime, declination


def sun_times_utc(
    latitude: float, longitude: float, on_date: date_type
) -> Optional[Tuple[float, float]]:
    """
    Sunrise and sunset as minutes from UTC midnight.

    Returns None inside a polar day or night, where the sun does not cross the
    horizon and no sunrise or sunset exists.
    """
    day_of_year = on_date.timetuple().tm_yday
    # Evaluated at solar noon, which is accurate enough for a one-minute result.
    gamma = (2 * pi / 365.0) * (day_of_year - 1 + 0.5)

    eqtime, declination = _equation_of_time_and_declination(gamma)

    lat_rad = radians(latitude)
    try:
        cos_hour_angle = (
            cos(radians(ZENITH)) / (cos(lat_rad) * cos(declination))
            - tan(lat_rad) * tan(declination)
        )
    except ZeroDivisionError:  # pragma: no cover - lat = +/-90 exactly
        return None

    if cos_hour_angle > 1 or cos_hour_angle < -1:
        # Polar night (sun never rises) or midnight sun (never sets).
        return None

    hour_angle = degrees(acos(cos_hour_angle))

    sunrise = 720 - 4 * (longitude + hour_angle) - eqtime
    sunset = 720 - 4 * (longitude - hour_angle) - eqtime
    return sunrise, sunset


def sun_times_local(
    latitude: float,
    longitude: float,
    on_date: date_type,
    tz_name: Optional[str] = None,
) -> Optional[Tuple[time, time]]:
    """
    Sunrise and sunset as local wall-clock times for the station.

    Detections are stored with local hour and minute, so the comparison the
    rollup makes is local-to-local. ``tz_name`` is the station's IANA zone; when
    it is missing or unknown the times are offset by longitude instead, which
    is correct to within the difference between solar and civil time.
    """
    utc = sun_times_utc(latitude, longitude, on_date)
    if utc is None:
        return None

    results = []
    for minutes in utc:
        moment = datetime.combine(on_date, time(0, 0), tzinfo=timezone.utc) + timedelta(
            minutes=minutes
        )
        if tz_name and ZoneInfo is not None:
            try:
                local = moment.astimezone(ZoneInfo(tz_name))
            except Exception:  # noqa: BLE001 - unknown zone, or no tzdata on Windows
                logger.debug("Unknown timezone %r; falling back to longitude", tz_name)
                local = moment + timedelta(hours=longitude / 15.0)
        else:
            local = moment + timedelta(hours=longitude / 15.0)
        results.append(local.time().replace(second=0, microsecond=0))

    return results[0], results[1]


def populate_solar_times(db, only_missing: bool = True) -> int:
    """
    Ensure a ``solar_times`` row exists for every station-day with detections.

    Driven from the detection rollup, which already holds one row per
    (station, date) group and so is far cheaper to scan than the detections
    table. Returns the number of rows written.

    Stations without coordinates are skipped: nothing can be computed for them,
    and their detections simply stay out of the chorus charts.
    """
    from sqlalchemy import text as _text

    stations = {
        row[0]: (row[1], row[2], row[3])
        for row in db.execute(
            _text("SELECT id, latitude, longitude, timezone FROM stations")
        ).all()
        if row[1] is not None and row[2] is not None
    }
    if not stations:
        return 0

    sql = """
        SELECT DISTINCT r.station_id, r.detection_date
        FROM detection_rollups r
    """
    if only_missing:
        sql += """
        WHERE NOT EXISTS (
            SELECT 1 FROM solar_times s
            WHERE s.station_id = r.station_id AND s.solar_date = r.detection_date
        )
        """

    pending = db.execute(_text(sql)).all()
    if not pending:
        return 0

    written = 0
    for station_id, on_date in pending:
        coords = stations.get(station_id)
        if coords is None:
            continue
        latitude, longitude, tz_name = coords

        if isinstance(on_date, str):
            on_date = date_type.fromisoformat(on_date)

        times = sun_times_local(latitude, longitude, on_date, tz_name)
        # Bound as ISO strings: raw SQL gives SQLite no column type to adapt a
        # datetime.time through, and 'HH:MM:SS' is what strftime() reads back.
        sunrise, sunset = (
            (times[0].isoformat(), times[1].isoformat()) if times else (None, None)
        )

        db.execute(
            _text(
                "INSERT INTO solar_times (station_id, solar_date, sunrise, sunset) "
                "VALUES (:sid, :d, :sr, :ss) "
                "ON CONFLICT (station_id, solar_date) DO UPDATE SET "
                "sunrise = excluded.sunrise, sunset = excluded.sunset"
            ),
            {"sid": station_id, "d": on_date, "sr": sunrise, "ss": sunset},
        )
        written += 1

        # Commit in batches: a first run over years of history across many
        # stations is tens of thousands of rows.
        if written % 2000 == 0:
            db.commit()

    db.commit()
    logger.info("Computed sun times for %s station-days", written)
    return written
