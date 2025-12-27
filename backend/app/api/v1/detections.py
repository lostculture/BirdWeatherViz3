"""
Detection API Endpoints
Endpoints for querying detection data.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.api.deps import get_db_dependency
from app.repositories.detection import DetectionRepository
from app.schemas.detection import (
    DetectionResponse,
    DailyDetectionCount,
    HourlyDetectionPattern,
    DetectionListResponse
)
from app.schemas.common import DatabaseStats

router = APIRouter()


@router.get("/daily-counts", response_model=List[DailyDetectionCount])
async def get_daily_detection_counts(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get daily detection counts grouped by station.

    Returns time series data suitable for line charts showing
    detection trends over time.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = DetectionRepository(db)
    results = repo.get_daily_detections(
        start_date=start_date,
        end_date=end_date,
        station_ids=station_id_list
    )

    return [DailyDetectionCount(**r) for r in results]


@router.get("/by-species/{species_id}", response_model=List[dict])
async def get_detections_by_species(
    species_id: int,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get detections for a specific species over time.

    Returns daily detection counts and average confidence for the species,
    grouped by station.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = DetectionRepository(db)
    results = repo.get_detections_by_species(
        species_id=species_id,
        start_date=start_date,
        end_date=end_date,
        station_ids=station_id_list
    )

    return results


@router.get("/hourly-pattern", response_model=List[HourlyDetectionPattern])
async def get_hourly_pattern(
    species_id: Optional[int] = Query(None, description="Filter by species ID"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get hourly detection pattern (24-hour distribution).

    Returns detection counts for each hour of the day (0-23),
    useful for creating rose plots and hourly bar charts.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = DetectionRepository(db)
    results = repo.get_hourly_pattern(
        species_id=species_id,
        station_ids=station_id_list
    )

    return [HourlyDetectionPattern(**r) for r in results]


@router.get("/recent", response_model=List[DetectionResponse])
async def get_recent_detections(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of detections"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get most recent detections.

    Returns the latest detections across all stations (or filtered stations),
    ordered by timestamp descending.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = DetectionRepository(db)
    detections = repo.get_recent_detections(
        limit=limit,
        station_ids=station_id_list
    )

    return [DetectionResponse.from_orm(d) for d in detections]


@router.get("/stats", response_model=DatabaseStats)
async def get_detection_stats(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get detection database statistics.

    Returns total detections, unique species count, date range,
    and nighttime detection percentage.
    """
    from app.repositories.species import SpeciesRepository

    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    detection_repo = DetectionRepository(db)
    species_repo = SpeciesRepository(db)

    # Get statistics
    total_detections = detection_repo.get_total_count(
        start_date=start_date,
        end_date=end_date,
        station_ids=station_id_list
    )

    unique_species = species_repo.get_total_unique_species(
        station_ids=station_id_list
    )

    date_range = detection_repo.get_date_range()

    nighttime_pct = detection_repo.calculate_nighttime_percentage(
        station_ids=station_id_list
    )

    from app.repositories.station import StationRepository
    station_repo = StationRepository(db)
    total_stations = len(station_repo.get_active_stations())

    return DatabaseStats(
        total_detections=total_detections,
        unique_species=unique_species,
        total_stations=total_stations,
        nighttime_percentage=nighttime_pct,
        date_range_start=date_range[0],
        date_range_end=date_range[1]
    )
