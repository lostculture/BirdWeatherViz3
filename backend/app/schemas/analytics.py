"""
Analytics Pydantic Schemas
Request/response models for advanced analytics endpoints.

Version: 1.0.0
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class SpeciesHourBubble(BaseModel):
    """Data point for species activity bubble chart."""

    species_id: int
    common_name: str
    scientific_name: str
    hour: int = Field(..., ge=0, le=23)
    detection_count: int
    total_detections: int  # Total for this species (for sorting)


class PhenologyCell(BaseModel):
    """Data point for phenology heatmap."""

    species_id: int
    common_name: str
    week_number: int = Field(..., ge=1, le=53)
    year: int
    detection_count: int


class ConfidenceScatterPoint(BaseModel):
    """Data point for detection count vs confidence scatter plot."""

    species_id: int
    common_name: str
    scientific_name: str
    total_detections: int
    avg_confidence: float = Field(..., ge=0.0, le=1.0)
    detection_days: int  # Number of days with detections


class ConfidenceByHour(BaseModel):
    """Data point for confidence by hour heatmap."""

    hour: int = Field(..., ge=0, le=23)
    confidence_bin: str  # e.g., "0.5-0.6", "0.6-0.7"
    confidence_min: float
    confidence_max: float
    detection_count: int


class TemporalDistribution(BaseModel):
    """Data point for temporal distribution chart."""

    species_id: int
    common_name: str
    date: date
    detection_count: int


class WeatherImpact(BaseModel):
    """Data point for weather impact analysis."""

    temperature_bin: Optional[str] = None
    condition: Optional[str] = None
    avg_detections: float
    total_detections: int
    observation_count: int  # Number of time periods
