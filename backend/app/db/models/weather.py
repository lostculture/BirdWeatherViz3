"""
Weather Database Model
Represents daily weather data for a station.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, Float, String, Date, Time, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Weather(Base):
    """
    Daily weather record.

    Stores historical and current weather data from Open-Meteo API,
    including temperature, precipitation, and sun times.
    """

    __tablename__ = "weather"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False, index=True)

    # Date
    weather_date = Column(Date, nullable=False, index=True,
                         comment="Date of weather record")

    # Location (denormalized for convenience)
    latitude = Column(Float, nullable=False, comment="Latitude")
    longitude = Column(Float, nullable=False, comment="Longitude")

    # Temperature (Fahrenheit)
    temp_max = Column(Float, comment="Maximum temperature (°F)")
    temp_min = Column(Float, comment="Minimum temperature (°F)")
    temp_avg = Column(Float, comment="Average temperature (°F)")

    # Other weather metrics
    humidity = Column(Float, comment="Relative humidity (%)")
    pressure = Column(Float, comment="Atmospheric pressure (hPa)")
    wind_speed = Column(Float, comment="Maximum wind speed (mph)")
    precipitation = Column(Float, comment="Total precipitation (inches)")
    weather_description = Column(String(100), comment="Weather condition description")

    # Sun times
    sunrise = Column(Time, comment="Sunrise time (HH:MM:SS)")
    sunset = Column(Time, comment="Sunset time (HH:MM:SS)")
    day_length = Column(String(10), comment="Day length (HH:MM:SS)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Relationships
    station = relationship("Station", back_populates="weather_records")

    # Unique constraint: one weather record per station per date
    __table_args__ = (
        UniqueConstraint('station_id', 'weather_date', name='uq_station_weather_date'),
    )

    def __repr__(self):
        """String representation of Weather."""
        return f"<Weather(id={self.id}, station_id={self.station_id}, date={self.weather_date})>"

    def to_dict(self):
        """Convert weather to dictionary."""
        return {
            "id": self.id,
            "station_id": self.station_id,
            "weather_date": self.weather_date.isoformat() if self.weather_date else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "temp_max": self.temp_max,
            "temp_min": self.temp_min,
            "temp_avg": self.temp_avg,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed": self.wind_speed,
            "precipitation": self.precipitation,
            "weather_description": self.weather_description,
            "sunrise": self.sunrise.isoformat() if self.sunrise else None,
            "sunset": self.sunset.isoformat() if self.sunset else None,
            "day_length": self.day_length,
        }
