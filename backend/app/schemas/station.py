"""
Station Pydantic Schemas
Request/response models for station endpoints.

Version: 1.0.0
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class StationBase(BaseModel):
    """Base station schema with common fields."""

    name: Optional[str] = Field(None, max_length=200, description="Station name")
    latitude: Optional[float] = Field(None, description="Station latitude")
    longitude: Optional[float] = Field(None, description="Station longitude")
    timezone: Optional[str] = Field(None, max_length=50, description="Station timezone")


class StationCreate(StationBase):
    """Schema for creating a new station."""

    station_id: int = Field(..., description="BirdWeather station ID")
    api_token: str = Field(..., min_length=10, max_length=500, description="BirdWeather API token")
    active: bool = Field(True, description="Include in analysis")
    auto_update: bool = Field(True, description="Enable auto-updates")


class StationUpdate(BaseModel):
    """Schema for updating station information."""

    name: Optional[str] = Field(None, max_length=200)
    api_token: Optional[str] = Field(None, min_length=10, max_length=500)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = Field(None, max_length=50)
    active: Optional[bool] = None
    auto_update: Optional[bool] = None


class StationResponse(StationBase):
    """Schema for station in API responses."""

    id: int = Field(..., description="Database ID")
    station_id: int = Field(..., description="BirdWeather station ID")
    api_token_masked: Optional[str] = Field(None, description="Masked API token")
    active: bool = Field(..., description="Include in analysis")
    auto_update: bool = Field(..., description="Auto-update enabled")
    last_update: Optional[datetime] = Field(None, description="Last data fetch time")
    last_detection_id: Optional[int] = Field(None, description="Last detection ID fetched")
    created_at: datetime = Field(..., description="Record creation time")

    class Config:
        from_attributes = True


class StationStats(BaseModel):
    """Schema for station statistics."""

    station_id: int
    station_name: Optional[str] = None
    total_detections: int = 0
    unique_species: int = 0
    days_active: int = 0
    avg_confidence: float = 0.0
    first_detection: Optional[datetime] = None
    last_detection: Optional[datetime] = None


class StationComparison(BaseModel):
    """Schema for station comparison data."""

    stations: list[StationStats] = Field(..., description="Station statistics")
    species_overlap: dict = Field(..., description="Species overlap between stations")
