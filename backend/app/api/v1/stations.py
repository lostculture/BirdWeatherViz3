"""
Station API Endpoints
Endpoints for managing and querying station data.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db_dependency
from app.repositories.station import StationRepository
from app.schemas.station import (
    StationResponse,
    StationCreate,
    StationUpdate,
    StationStats
)

router = APIRouter()


@router.get("/", response_model=List[StationResponse])
async def get_stations(
    active_only: bool = False,
    db: Session = Depends(get_db_dependency)
):
    """
    Get list of all stations.

    Returns all configured stations with masked API tokens.
    """
    repo = StationRepository(db)

    if active_only:
        stations = repo.get_active_stations()
    else:
        stations = repo.get_all()

    # Convert to response models with masked tokens
    return [
        StationResponse(
            **station.to_dict(include_token=False)
        )
        for station in stations
    ]


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(
    station_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get a single station by database ID.

    Returns station information with masked API token.
    """
    repo = StationRepository(db)
    station = repo.get_by_id(station_id)

    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    return StationResponse(**station.to_dict(include_token=False))


@router.post("/", response_model=StationResponse, status_code=201)
async def create_station(
    station_data: StationCreate,
    db: Session = Depends(get_db_dependency)
):
    """
    Create a new station.

    Registers a new BirdWeather station with API token for data fetching.
    """
    repo = StationRepository(db)

    # Check if station already exists
    existing = repo.get_by_birdweather_id(station_data.station_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Station with BirdWeather ID {station_data.station_id} already exists"
        )

    # Create station
    station = repo.create(**station_data.dict())

    return StationResponse(**station.to_dict(include_token=False))


@router.put("/{station_id}", response_model=StationResponse)
async def update_station(
    station_id: int,
    station_data: StationUpdate,
    db: Session = Depends(get_db_dependency)
):
    """
    Update an existing station.

    Updates station information. Only provided fields are updated.
    """
    repo = StationRepository(db)

    # Check if station exists
    station = repo.get_by_id(station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Update station (only non-None fields)
    update_data = station_data.dict(exclude_unset=True)
    updated_station = repo.update(station_id, **update_data)

    return StationResponse(**updated_station.to_dict(include_token=False))


@router.delete("/{station_id}", status_code=204)
async def delete_station(
    station_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Delete a station.

    Removes station and all associated detections (cascade delete).
    """
    repo = StationRepository(db)

    # Check if station exists
    if not repo.exists(station_id):
        raise HTTPException(status_code=404, detail="Station not found")

    # Delete station
    repo.delete(station_id)

    return None


@router.get("/{station_id}/stats", response_model=StationStats)
async def get_station_statistics(
    station_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get statistics for a specific station.

    Returns detection counts, unique species, activity days, and confidence metrics.
    """
    repo = StationRepository(db)

    # Check if station exists
    if not repo.exists(station_id):
        raise HTTPException(status_code=404, detail="Station not found")

    # Get station info for name
    station = repo.get_by_id(station_id)

    # Get statistics
    stats = repo.get_station_stats(station_id)
    stats['station_name'] = station.name

    return StationStats(**stats)


@router.get("/comparison/all", response_model=List[StationStats])
async def get_station_comparison(
    db: Session = Depends(get_db_dependency)
):
    """
    Get comparison statistics for all stations.

    Returns statistics for all stations for side-by-side comparison.
    """
    repo = StationRepository(db)
    stats = repo.get_all_station_stats()

    return [StationStats(**s) for s in stats]
