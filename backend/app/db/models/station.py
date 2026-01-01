"""
Station Database Model
Represents a BirdWeather monitoring station.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Station(Base):
    """
    BirdWeather monitoring station.

    Stores station information, API credentials, location data,
    and auto-update status tracking.
    """

    __tablename__ = "stations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # BirdWeather station info
    station_id = Column(Integer, unique=True, nullable=False, index=True,
                       comment="BirdWeather station ID")
    name = Column(String(200), comment="Station name/label")

    # API credentials (should be encrypted in production)
    api_token = Column(String(500), nullable=True,
                      comment="BirdWeather API token (encrypted, optional for public stations)")

    # Location
    latitude = Column(Float, comment="Station latitude")
    longitude = Column(Float, comment="Station longitude")
    timezone = Column(String(50), comment="Station timezone (e.g., 'America/New_York')")

    # Settings
    active = Column(Boolean, default=True,
                   comment="Include station in analysis and auto-updates")
    auto_update = Column(Boolean, default=True,
                        comment="Enable automatic data fetching for this station")

    # Auto-update status
    last_update = Column(DateTime(timezone=True),
                        comment="Last successful data fetch timestamp")
    last_detection_id = Column(Integer,
                              comment="Last detection ID fetched (cursor for pagination)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Relationships
    detections = relationship("Detection", back_populates="station", cascade="all, delete-orphan")
    weather_records = relationship("Weather", back_populates="station", cascade="all, delete-orphan")

    def __repr__(self):
        """String representation of Station."""
        return f"<Station(id={self.id}, station_id={self.station_id}, name='{self.name}', active={self.active})>"

    def to_dict(self, include_token=False):
        """
        Convert station to dictionary.

        Args:
            include_token: Whether to include the API token (default: False for security)
        """
        data = {
            "id": self.id,
            "station_id": self.station_id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "active": self.active,
            "auto_update": self.auto_update,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_detection_id": self.last_detection_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_token:
            data["api_token"] = self.api_token
        else:
            # Mask token for display
            if self.api_token:
                data["api_token_masked"] = f"{self.api_token[:8]}...{self.api_token[-4:]}"

        return data
