"""
Common Pydantic Schemas
Shared request/response models used across multiple endpoints.

Version: 1.0.0
"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Any


class DateRangeFilter(BaseModel):
    """Schema for date range filtering."""

    start_date: Optional[date] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="End date (YYYY-MM-DD)")


class StationFilter(BaseModel):
    """Schema for station filtering."""

    station_ids: Optional[list[int]] = Field(None, description="List of station IDs to include")


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(100, ge=1, le=1000, description="Items per page")


class HealthCheck(BaseModel):
    """Schema for health check response."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    version: str = Field(..., description="Application version")
    database: str = Field(..., description="Database connection status")
    auto_update_enabled: bool = Field(..., description="Auto-update status")


class VersionInfo(BaseModel):
    """Schema for version information response."""

    version: str = Field(..., description="Application version")
    author: str = Field(..., description="Application author")
    description: str = Field(..., description="Application description")
    license: str = Field(..., description="Application license")


class DatabaseStats(BaseModel):
    """Schema for database statistics."""

    total_detections: int = Field(0, description="Total number of detections")
    unique_species: int = Field(0, description="Number of unique species")
    total_stations: int = Field(0, description="Number of stations")
    nighttime_percentage: float = Field(0.0, description="Percentage of nighttime detections")
    date_range_start: Optional[date] = Field(None, description="Earliest detection date")
    date_range_end: Optional[date] = Field(None, description="Latest detection date")


class PlotlyData(BaseModel):
    """Schema for Plotly-compatible chart data."""

    data: list[dict[str, Any]] = Field(..., description="Plotly data traces")
    layout: dict[str, Any] = Field(..., description="Plotly layout configuration")
    config: Optional[dict[str, Any]] = Field(None, description="Plotly config options")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")


class SuccessResponse(BaseModel):
    """Schema for success responses."""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Optional response data")
