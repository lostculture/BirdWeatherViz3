"""
Species API Endpoints
Endpoints for querying species data and analytics.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.api.deps import get_db_dependency, get_current_user
from app.repositories.species import SpeciesRepository
from app.schemas.species import (
    SpeciesResponse,
    SpeciesListItem,
    SpeciesDiversityTrend,
    SpeciesDiscoveryCurve,
    NewSpeciesThisWeek,
    ReturningSpecies,
    OverdueSpecies,
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


@router.post("/refresh-stats")
async def refresh_species_stats(
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Refresh cached statistics for all species.

    Updates total_detections, first_seen, and last_seen for all species
    based on actual detection data.
    """
    repo = SpeciesRepository(db)
    count = repo.update_all_cached_stats()
    return {"success": True, "species_updated": count}


@router.get("/inat-taxon/{scientific_name:path}")
async def get_inat_taxon_id(
    scientific_name: str,
    db: Session = Depends(get_db_dependency)
):
    """
    Get iNaturalist taxon ID for a species.

    Returns cached ID if available, otherwise fetches from iNaturalist API
    and caches the result.
    """
    from app.services.inaturalist import fetch_inat_taxon_id, generate_inat_url

    repo = SpeciesRepository(db)

    # Check if we have it cached in the species table
    species = repo.get_by_scientific_name(scientific_name)
    if species and species.inat_taxon_id:
        return {
            "scientific_name": scientific_name,
            "taxon_id": species.inat_taxon_id,
            "url": generate_inat_url(scientific_name, species.inat_taxon_id),
            "cached": True
        }

    # Fetch from iNaturalist API
    taxon_id = await fetch_inat_taxon_id(scientific_name)

    # Cache it if we found one and have the species in our DB
    if taxon_id and species:
        species.inat_taxon_id = taxon_id
        db.commit()

    return {
        "scientific_name": scientific_name,
        "taxon_id": taxon_id,
        "url": generate_inat_url(scientific_name, taxon_id),
        "cached": False
    }


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


@router.get("/returning", response_model=List[ReturningSpecies])
async def get_returning_species(
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    recent_days: int = Query(14, ge=1, le=90, description="How far back counts as 'just returned'"),
    min_absence_days: int = Query(90, ge=14, le=730, description="Silence required before a detection counts as a return"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get species heard again after a long absence.

    These are the returning migrants and the seasonal singers: species with an
    earlier detection history, a gap of at least ``min_absence_days``, and a
    fresh detection inside ``recent_days``. Species with no prior record are
    excluded - those are lifers and appear under /new/this-week instead.
    """
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    results = repo.get_returning_species(
        station_ids=station_id_list,
        recent_days=recent_days,
        min_absence_days=min_absence_days,
    )

    return [ReturningSpecies(**r) for r in results]


@router.get("/overdue", response_model=List[OverdueSpecies])
async def get_overdue_species(
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    absent_days: int = Query(21, ge=7, le=365, description="Silence before a species counts as missing"),
    window_days: int = Query(21, ge=7, le=60, description="Half-width of the calendar window compared to previous years"),
    min_prior_years: int = Query(1, ge=1, le=10, description="Prior years the species must have been present in this window"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get species that history says should be present now, but are not.

    The counterpart to /returning: a species detected in this same calendar
    window in previous years, with nothing heard for ``absent_days``. Needs at
    least one full year of history before it can report anything.
    """
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    results = repo.get_overdue_species(
        station_ids=station_id_list,
        absent_days=absent_days,
        window_days=window_days,
        min_prior_years=min_prior_years,
    )

    return [OverdueSpecies(**r) for r in results]


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


@router.get("/by-family/{family_name}", response_model=List[SpeciesResponse])
async def get_species_by_family(
    family_name: str,
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get all species in a given bird family.

    Returns list of species belonging to the specified family.
    """
    # Parse station_ids if provided
    station_id_list = None
    if station_ids:
        station_id_list = [int(id.strip()) for id in station_ids.split(",")]

    repo = SpeciesRepository(db)
    species = repo.get_species_by_family(family_name, station_ids=station_id_list)

    return [SpeciesResponse.from_orm(s) for s in species]


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


@router.get("/{species_id}/hourly-pattern")
async def get_species_hourly_pattern(
    species_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get hourly detection pattern for a species.

    Returns detection counts for each hour (0-23).
    """
    repo = SpeciesRepository(db)
    return repo.get_hourly_pattern(species_id)


@router.get("/{species_id}/monthly-pattern")
async def get_species_monthly_pattern(
    species_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get monthly detection pattern for a species.

    Returns detection counts for each month (1-12).
    """
    repo = SpeciesRepository(db)
    return repo.get_monthly_pattern(species_id)


@router.get("/{species_id}/timeline")
async def get_species_timeline(
    species_id: int,
    months: Optional[int] = Query(None, description="Limit to last N months"),
    db: Session = Depends(get_db_dependency)
):
    """
    Get detection timeline for a species by station.

    Returns daily detection counts over time, grouped by station.
    """
    repo = SpeciesRepository(db)
    return repo.get_detection_timeline(species_id, months=months)


@router.get("/{species_id}/station-distribution")
async def get_species_station_distribution(
    species_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get detection distribution across stations for a species.

    Returns detection counts and percentages by station.
    """
    repo = SpeciesRepository(db)
    return repo.get_station_distribution(species_id)


@router.get("/{species_id}/confidence-by-station")
async def get_species_confidence_by_station(
    species_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Get average detection confidence by station for a species.

    Returns average confidence scores per station.
    """
    repo = SpeciesRepository(db)
    return repo.get_confidence_by_station(species_id)
