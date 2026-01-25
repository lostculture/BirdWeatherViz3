"""
Species API Endpoints
Endpoints for querying species data and analytics.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.api.deps import get_db_dependency
from app.repositories.species import SpeciesRepository
from app.schemas.species import (
    SpeciesResponse,
    SpeciesListItem,
    SpeciesDiversityTrend,
    SpeciesDiscoveryCurve,
    NewSpeciesThisWeek,
    FamilyStats
)

router = APIRouter()


# ============================================
# Static routes must come BEFORE dynamic routes
# ============================================

@router.get("/", response_model=List[SpeciesResponse])
async def get_species_list(
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    search: Optional[str] = Query(None, description="Search in common or scientific name"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get list of all species.

    Returns all detected species with cached statistics.
    Can be filtered by stations and searched by name.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    species = repo.get_species_list(
        station_ids=station_id_list,
        search=search
    )

    return [SpeciesResponse.from_orm(s) for s in species]


@router.get("/diversity/trend", response_model=List[SpeciesDiversityTrend])
async def get_diversity_trend(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get species diversity trend over time.

    Returns daily unique species counts, suitable for creating
    diversity trend charts with 7-day moving average.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    results = repo.get_daily_unique_species(
        start_date=start_date,
        end_date=end_date,
        station_ids=station_id_list
    )

    # Calculate 7-day moving average
    diversity_data = []
    for i, r in enumerate(results):
        # Calculate 7-day average
        window_start = max(0, i - 6)
        window = results[window_start:i+1]
        avg = sum(w['unique_species_count'] for w in window) / len(window)

        diversity_data.append(SpeciesDiversityTrend(
            detection_date=r['detection_date'],
            unique_species_count=r['unique_species_count'],
            seven_day_avg=avg
        ))

    return diversity_data


@router.get("/discovery/curve", response_model=List[SpeciesDiscoveryCurve])
async def get_discovery_curve(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get cumulative species discovery curve.

    Returns cumulative count of unique species discovered over time,
    suitable for spline charts showing discovery progress.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    results = repo.get_discovery_curve(
        start_date=start_date,
        end_date=end_date,
        station_ids=station_id_list
    )

    return [SpeciesDiscoveryCurve(**r) for r in results]


@router.get("/new/this-week", response_model=List[NewSpeciesThisWeek])
async def get_species_this_week(
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get species detected since Monday of current week.

    Returns new species discovered this week with first detection date,
    suitable for "New Species This Week" displays.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    results = repo.get_species_this_week(station_ids=station_id_list)

    return [NewSpeciesThisWeek(**r) for r in results]


@router.get("/families/stats", response_model=List[FamilyStats])
async def get_family_stats(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get bird family statistics.

    Returns detection totals and species counts by bird family,
    suitable for family analysis bar charts.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    results = repo.get_family_totals(
        start_date=start_date,
        end_date=end_date,
        station_ids=station_id_list
    )

    return [FamilyStats(**r) for r in results]


@router.post("/refresh-stats")
async def refresh_species_stats(
    db: Session = Depends(get_db_dependency)
):
    """
    Refresh cached statistics for all species.

    Updates first_seen, last_seen, and total_detections from actual
    detection data. Use this after bulk imports or if stats appear incorrect.
    """
    repo = SpeciesRepository(db)
    updated_count = repo.update_all_cached_stats()

    return {
        "success": True,
        "species_updated": updated_count,
        "message": f"Updated statistics for {updated_count} species"
    }


# ============================================
# Dynamic routes with {species_id} parameter
# ============================================

@router.get("/{species_id}", response_model=SpeciesResponse)
async def get_species_by_id(
    species_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get a single species by database ID.

    Returns detailed species information including cached statistics.
    """
    repo = SpeciesRepository(db)
    species = repo.get_by_id(species_id)

    if not species:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Species not found")

    return SpeciesResponse.from_orm(species)
