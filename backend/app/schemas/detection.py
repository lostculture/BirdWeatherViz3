"""
Detection Pydantic Schemas
Request/response models for detection endpoints.

Version: 1.0.0
"""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class DetectionBase(BaseModel):
    """Base detection schema with common fields."""

    detection_id: int = Field(..., description="BirdWeather detection ID")
    timestamp: datetime = Field(..., description="Detection timestamp")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence (0-1)")
    latitude: Optional[float] = Field(None, description="Detection latitude")
    longitude: Optional[float] = Field(None, description="Detection longitude")


class DetectionCreate(DetectionBase):
    """Schema for creating a new detection."""

    station_id: int = Field(..., description="Station database ID")
    species_id: int = Field(..., description="Species database ID")
    soundscape_id: Optional[int] = Field(None, description="Soundscape ID")
    soundscape_start_time: Optional[datetime] = Field(None, description="Soundscape start time")
    soundscape_url: Optional[str] = Field(None, max_length=500, description="Soundscape URL")


class DetectionResponse(DetectionBase):
    """Schema for detection in API responses."""

    id: int = Field(..., description="Database ID")
    station_id: int = Field(..., description="Station database ID")
    species_id: int = Field(..., description="Species database ID")
    detection_date: date = Field(..., description="Detection date")
    detection_hour: Optional[int] = Field(None, ge=0, le=23, description="Detection hour (0-23)")
    detection_minute: Optional[int] = Field(None, ge=0, le=59, description="Detection minute (0-59)")
    soundscape_id: Optional[int] = Field(None, description="Soundscape ID")
    soundscape_url: Optional[str] = Field(None, description="Soundscape URL")
    created_at: datetime = Field(..., description="Record creation time")

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)


class DailyDetectionCount(BaseModel):
    """Schema for daily detection counts by station."""

    detection_date: date = Field(..., description="Date")
    station_id: int = Field(..., description="Station ID")
    station_name: Optional[str] = Field(None, description="Station name")
    detection_count: int = Field(..., description="Number of detections")


class HourlyDetectionPattern(BaseModel):
    """Schema for hourly detection pattern."""

    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    detection_count: int = Field(..., description="Number of detections")


class MonthlyDetectionPattern(BaseModel):
    """Schema for monthly detection pattern."""

    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    month_name: str = Field(..., description="Month name")
    detection_count: int = Field(..., description="Number of detections")


class DetectionListResponse(BaseModel):
    """Schema for paginated detection list."""

    total: int = Field(..., description="Total number of detections")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    detections: list[DetectionResponse] = Field(..., description="List of detections")
