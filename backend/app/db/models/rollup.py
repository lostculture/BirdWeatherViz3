"""
Analytics Rollup Models
Pre-aggregated detection summaries that keep the Analytics page responsive
once a station's history grows past a few million detections.

Two grains are stored:

* ``detection_rollups``  — (station, species, date, hour). Serves every chart
  that only needs hour-of-day resolution: bubble, phenology, temporal density,
  weekly trends, co-occurrence, seasonality, champions, confidence heatmaps.
* ``solar_rollups``      — (station, species, date, phase, minute bin). Serves
  the dawn/dusk chorus charts, which need minute resolution relative to
  sunrise/sunset and so cannot be answered from the hourly grain.

Confidence handling: callers filter with a ``min_confidence`` threshold, so the
rollups carry *cumulative* counts at 0.05 steps from 0.50 upwards. A query for
``min_confidence=0.7`` reads ``cnt_70`` directly. Thresholds that fall between
steps snap down to the nearest stored bucket (documented in the repository), and
anything below 0.50 falls back to ``cnt_all``.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, Float, String, Date, Time, Index

from app.db.base import Base


# Cumulative confidence buckets, as (column suffix, threshold) in ascending
# order. Kept as a module constant so the builder and the repositories agree.
CONFIDENCE_BUCKETS = [
    ("50", 0.50),
    ("55", 0.55),
    ("60", 0.60),
    ("65", 0.65),
    ("70", 0.70),
    ("75", 0.75),
    ("80", 0.80),
    ("85", 0.85),
    ("90", 0.90),
    ("95", 0.95),
]


class DetectionRollup(Base):
    """
    Hourly detection counts per station/species/date.

    One row replaces every raw detection sharing that key, which for a busy
    station is a 20-50x reduction. Counts are cumulative by confidence so a
    single row answers any supported ``min_confidence``.
    """

    __tablename__ = "detection_rollups"

    station_id = Column(Integer, primary_key=True, nullable=False)
    species_id = Column(Integer, primary_key=True, nullable=False)
    detection_date = Column(Date, primary_key=True, nullable=False)
    hour = Column(Integer, primary_key=True, nullable=False,
                  comment="Hour of day, 0-23")

    cnt_all = Column(Integer, nullable=False, default=0,
                     comment="Detections at any confidence")
    cnt_50 = Column(Integer, nullable=False, default=0)
    cnt_55 = Column(Integer, nullable=False, default=0)
    cnt_60 = Column(Integer, nullable=False, default=0)
    cnt_65 = Column(Integer, nullable=False, default=0)
    cnt_70 = Column(Integer, nullable=False, default=0)
    cnt_75 = Column(Integer, nullable=False, default=0)
    cnt_80 = Column(Integer, nullable=False, default=0)
    cnt_85 = Column(Integer, nullable=False, default=0)
    cnt_90 = Column(Integer, nullable=False, default=0)
    cnt_95 = Column(Integer, nullable=False, default=0)

    conf_sum = Column(Float, nullable=False, default=0.0,
                      comment="Sum of confidence over cnt_all, for averages")
    conf_max = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        # Date-leading: nearly every analytics query is a rolling window.
        Index("ix_rollup_date_species", "detection_date", "species_id"),
        Index("ix_rollup_species_date", "species_id", "detection_date"),
        Index("ix_rollup_station_date", "station_id", "detection_date"),
    )


class SolarRollup(Base):
    """
    Detection counts binned by minutes from sunrise or sunset.

    ``phase`` is 'sunrise' or 'sunset'; ``minute_bin`` is the 5-minute bucket
    (negative = before the event). Only detections inside the configured window
    around each event are stored, which keeps this table far smaller than the
    hourly rollup despite the finer grain.
    """

    __tablename__ = "solar_rollups"

    station_id = Column(Integer, primary_key=True, nullable=False)
    species_id = Column(Integer, primary_key=True, nullable=False)
    detection_date = Column(Date, primary_key=True, nullable=False)
    phase = Column(String(8), primary_key=True, nullable=False,
                   comment="'sunrise' or 'sunset'")
    minute_bin = Column(Integer, primary_key=True, nullable=False,
                        comment="5-minute bin; negative = before the event")

    cnt_all = Column(Integer, nullable=False, default=0)
    cnt_50 = Column(Integer, nullable=False, default=0)
    cnt_55 = Column(Integer, nullable=False, default=0)
    cnt_60 = Column(Integer, nullable=False, default=0)
    cnt_65 = Column(Integer, nullable=False, default=0)
    cnt_70 = Column(Integer, nullable=False, default=0)
    cnt_75 = Column(Integer, nullable=False, default=0)
    cnt_80 = Column(Integer, nullable=False, default=0)
    cnt_85 = Column(Integer, nullable=False, default=0)
    cnt_90 = Column(Integer, nullable=False, default=0)
    cnt_95 = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_solar_phase_date", "phase", "detection_date"),
        Index("ix_solar_date_station", "detection_date", "station_id"),
    )


class SolarTime(Base):
    """
    Sunrise and sunset for one station on one date.

    Computed from the station's coordinates (see services/solar.py) rather than
    fetched, because weather is only collected for a single nominated station
    and every other station would otherwise have no sun times — which silently
    kept their detections out of the dawn and dusk chorus charts entirely.
    """

    __tablename__ = "solar_times"

    station_id = Column(Integer, primary_key=True, nullable=False)
    solar_date = Column(Date, primary_key=True, nullable=False)

    # Local wall-clock times, matching how detection_hour/minute are stored.
    sunrise = Column(Time, nullable=True)
    sunset = Column(Time, nullable=True,
                    comment="NULL inside a polar day or night")

    __table_args__ = (
        Index("ix_solar_times_date", "solar_date"),
    )


class RollupState(Base):
    """
    Bookkeeping for the rollup builder.

    A single row per rollup table tracks how far the incremental build has got
    (``last_detection_id``) plus enough status for the UI to show progress and
    for the API to decide whether a chart can be served from rollups yet.
    """

    __tablename__ = "rollup_state"

    name = Column(String(32), primary_key=True,
                  comment="'detection' or 'solar'")
    last_detection_id = Column(Integer, nullable=False, default=0,
                               comment="Highest detection id folded in so far")
    status = Column(String(16), nullable=False, default="idle",
                    comment="idle | building | error")
    rows_processed = Column(Integer, nullable=False, default=0)
    total_rows = Column(Integer, nullable=False, default=0)
    message = Column(String(500), nullable=True)
    updated_at = Column(String(32), nullable=True,
                        comment="ISO timestamp of the last successful pass")
