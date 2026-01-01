"""
Detection Database Model
Represents a bird detection record from BirdWeather.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.db.base import Base


class Detection(Base):
    """
    Bird detection record.

    Stores individual detection events from BirdWeather stations,
    including metadata about the detection, location, and audio information.
    """

    __tablename__ = "detections"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign keys
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False, index=True)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False, index=True)

    # BirdWeather detection metadata
    detection_id = Column(Integer, unique=True, nullable=True, index=True,
                         comment="BirdWeather detection ID (null for manual imports)")
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True,
                      comment="Detection timestamp")
    confidence = Column(Float, nullable=False,
                       comment="Detection confidence score (0-1)")

    # Location data
    latitude = Column(Float, comment="Detection latitude")
    longitude = Column(Float, comment="Detection longitude")

    # Audio metadata
    soundscape_id = Column(Integer, comment="BirdWeather soundscape ID")
    soundscape_start_time = Column(DateTime(timezone=True),
                                  comment="Soundscape recording start time")
    soundscape_url = Column(String(500), comment="URL to soundscape recording")

    # Denormalized fields for performance
    # These are computed from timestamp and cached for faster querying
    detection_date = Column(Date, nullable=False, index=True,
                           comment="Date of detection (denormalized from timestamp)")
    detection_hour = Column(Integer, comment="Hour of detection (0-23)")
    detection_minute = Column(Integer, comment="Minute of detection (0-59)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Relationships
    station = relationship("Station", back_populates="detections")
    species = relationship("Species", back_populates="detections")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_detection_station_date', 'station_id', 'detection_date'),
        Index('ix_detection_species_date', 'species_id', 'detection_date'),
        Index('ix_detection_date_hour', 'detection_date', 'detection_hour'),
    )

    def __repr__(self):
        """String representation of Detection."""
        return f"<Detection(id={self.id}, detection_id={self.detection_id}, timestamp={self.timestamp})>"

    def to_dict(self):
        """Convert detection to dictionary."""
        return {
            "id": self.id,
            "station_id": self.station_id,
            "species_id": self.species_id,
            "detection_id": self.detection_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confidence": self.confidence,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "soundscape_id": self.soundscape_id,
            "soundscape_url": self.soundscape_url,
            "detection_date": self.detection_date.isoformat() if self.detection_date else None,
            "detection_hour": self.detection_hour,
            "detection_minute": self.detection_minute,
        }
