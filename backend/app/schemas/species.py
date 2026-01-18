"""
Species Pydantic Schemas
Request/response models for species endpoints.

Version: 1.0.0
"""

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class SpeciesBase(BaseModel):
    """Base species schema with common fields."""

    common_name: str = Field(..., max_length=200, description="Common name")
    scientific_name: str = Field(..., max_length=200, description="Scientific name")
    family: Optional[str] = Field(None, max_length=200, description="Bird family")
    order: Optional[str] = Field(None, max_length=200, description="Bird order")


class SpeciesCreate(SpeciesBase):
    """Schema for creating a new species."""

    species_id: int = Field(..., description="BirdWeather species ID")
    ebird_code: Optional[str] = Field(None, max_length=10, description="eBird species code")


class SpeciesUpdate(BaseModel):
    """Schema for updating species information."""

    common_name: Optional[str] = Field(None, max_length=200)
    scientific_name: Optional[str] = Field(None, max_length=200)
    family: Optional[str] = Field(None, max_length=200)
    order: Optional[str] = Field(None, max_length=200)
    ebird_code: Optional[str] = Field(None, max_length=10)


class SpeciesResponse(SpeciesBase):
    """Schema for species in API responses."""

    id: int = Field(..., description="Database ID")
    species_id: Optional[int] = Field(None, description="BirdWeather species ID (null for manual imports)")
    ebird_code: Optional[str] = Field(None, description="eBird species code")
    total_detections: int = Field(0, description="Total detections (cached)")
    first_seen: Optional[datetime] = Field(None, description="First detection time")
    last_seen: Optional[datetime] = Field(None, description="Last detection time")

    class Config:
        from_attributes = True


class SpeciesListItem(BaseModel):
    """Schema for species in list views."""

    id: int
    species_id: Optional[int] = None
    common_name: str
    scientific_name: str
    family: Optional[str] = None
    total_detections: int = 0
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None


class SpeciesDiversityTrend(BaseModel):
    """Schema for species diversity over time."""

    detection_date: date = Field(..., description="Date")
    unique_species_count: int = Field(..., description="Number of unique species")
    seven_day_avg: Optional[float] = Field(None, description="7-day moving average")


class SpeciesDiscoveryCurve(BaseModel):
    """Schema for cumulative species discovery."""

    discovery_date: date = Field(..., description="Date")
    cumulative_species_count: int = Field(..., description="Cumulative species count")


class NewSpeciesThisWeek(BaseModel):
    """Schema for new species detected this week."""

    species_id: Optional[int] = None
    common_name: str
    scientific_name: str
    ebird_code: Optional[str] = Field(None, description="eBird species code")
    first_detection_date: date = Field(..., description="First detection date this week")
    detection_count: int = Field(default=0, description="Number of detections this week")


class SpeciesTimeStats(BaseModel):
    """Schema for species temporal statistics."""

    average_time: Optional[str] = Field(None, description="Average detection time (HH:MM:SS)")
    mode_time: Optional[str] = Field(None, description="Most common detection time (HH:MM:SS)")


class FamilyStats(BaseModel):
    """Schema for bird family statistics."""

    family: str = Field(..., description="Bird family name")
    species_count: int = Field(..., description="Number of species in family")
    total_detections: int = Field(..., description="Total detections for family")


class MonthlyChampion(BaseModel):
    """Schema for monthly detection champion."""

    month: int = Field(..., ge=1, le=12, description="Month number")
    month_name: str = Field(..., description="Month name")
    species_common_name: str = Field(..., description="Most detected species")
    species_scientific_name: str = Field(..., description="Scientific name")
    detection_count: int = Field(..., description="Detection count")


class SpeciesConfidenceScatter(BaseModel):
    """Schema for species detection count vs confidence scatter plot."""

    species_common_name: str
    detection_count: int
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
