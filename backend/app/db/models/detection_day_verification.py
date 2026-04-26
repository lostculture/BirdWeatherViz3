"""
DetectionDayVerification model
Tracks per (station, date) sync history so we can mark a date as `verified`
once two or more sync passes have agreed on its detection count. The sync
algorithm uses this to skip stable regions during full re-syncs without
risking missed backfills.

Version: 1.0.0
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DetectionDayVerification(Base):
    __tablename__ = "detection_day_verification"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detection_date = Column(Date, nullable=False, index=True)

    # Local detection count for this (station, date) at last sync.
    detections_count = Column(Integer, default=0, nullable=False)
    # Number of sync passes that have visited this date.
    read_count = Column(Integer, default=0, nullable=False)
    # New rows the most recent sync added for this date. 0 means the latest
    # read agreed with what we already had.
    last_added = Column(Integer, default=0, nullable=False)
    # True iff `read_count >= 2 AND last_added == 0` — two or more reads have
    # produced the same count, so the day is considered stable.
    verified = Column(Boolean, default=False, nullable=False, index=True)

    first_synced_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    station = relationship("Station")

    __table_args__ = (
        UniqueConstraint("station_id", "detection_date", name="uq_dvv_station_date"),
    )

    def __repr__(self):
        return (
            f"<DetectionDayVerification(station_id={self.station_id}, "
            f"date={self.detection_date}, count={self.detections_count}, "
            f"reads={self.read_count}, verified={self.verified})>"
        )
