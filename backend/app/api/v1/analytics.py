"""
Analytics API Endpoints
Endpoints for advanced analytics and visualizations.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.api.deps import get_db_dependency
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    SpeciesHourBubble,
    PhenologyCell,
    ConfidenceScatterPoint,
    ConfidenceByHour,
    TemporalDistribution,
)

router = APIRouter()


@router.get("/species-hour-bubble", response_model=List[SpeciesHourBubble])
async def get_species_hour_bubble(
    limit: int = Query(50, ge=10, le=100, description="Number of top species to include"),
    months: int = Query(3, ge=1, le=12, description="Number of months to analyze"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get species activity by hour for bubble chart visualization.

    Returns detection counts by species and hour of day for the top N species.
    Useful for visualizing activity patterns across many species simultaneously.
    """
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = AnalyticsRepository(db)
    return repo.get_species_hour_bubble_data(
        limit=limit,
        months=months,
        station_ids=station_id_list,
        min_confidence=min_confidence
    )


@router.get("/phenology", response_model=List[PhenologyCell])
async def get_phenology_data(
    year: Optional[int] = Query(None, description="Year to analyze (defaults to current)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(50, ge=10, le=100, description="Number of top species to include"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get phenology data for heatmap visualization.

    Returns detection counts by species and week number for the specified year.
    Shows seasonal presence patterns at a glance.
    """
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = AnalyticsRepository(db)
    return repo.get_phenology_data(
        year=year,
        station_ids=station_id_list,
        min_confidence=min_confidence,
        limit=limit
    )


@router.get("/confidence-scatter", response_model=List[ConfidenceScatterPoint])
async def get_confidence_scatter(
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    min_detections: int = Query(10, ge=1, description="Minimum detections to include species"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get detection count vs confidence data for scatter plot.

    Returns one data point per species showing total detections and
    average confidence. Useful for identifying reliable vs questionable species.
    """
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = AnalyticsRepository(db)
    return repo.get_confidence_scatter_data(
        station_ids=station_id_list,
        min_detections=min_detections
    )


@router.get("/confidence-by-hour", response_model=List[ConfidenceByHour])
async def get_confidence_by_hour(
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    months: int = Query(6, ge=1, le=12, description="Number of months to analyze"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get confidence distribution by hour for heatmap visualization.

    Returns detection counts binned by hour and confidence range.
    Shows when detections are most/least reliable.
    """
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = AnalyticsRepository(db)
    return repo.get_confidence_by_hour(
        station_ids=station_id_list,
        months=months
    )


@router.get("/temporal-distribution", response_model=List[TemporalDistribution])
async def get_temporal_distribution(
    species_ids: Optional[str] = Query(None, description="Comma-separated species IDs"),
    months: int = Query(6, ge=1, le=12, description="Number of months to analyze"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(20, ge=5, le=50, description="Number of top species if not specified"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get temporal distribution data for density visualization.

    Returns daily detection counts per species over time.
    Useful for KDE/density plots showing when species were active.
    """
    species_id_list = None
    if species_ids:
        species_id_list = [int(id.strip()) for id in species_ids.split(",")]

    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = AnalyticsRepository(db)
    return repo.get_temporal_distribution(
        species_ids=species_id_list,
        months=months,
        station_ids=station_id_list,
        min_confidence=min_confidence,
        limit=limit
    )
