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
from app.repositories.detection import DetectionRepository
from app.repositories.species import SpeciesRepository
from app.schemas.station import (
    StationResponse,
    StationCreate,
    StationUpdate,
    StationStats
)
from app.services.birdweather import BirdWeatherAPI
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# ============================================
# Static routes must come BEFORE dynamic routes
# ============================================

class SyncResponse(BaseModel):
    """Response model for sync operation"""
    success: bool
    detections_added: int
    message: str


class SyncAllResponse(BaseModel):
    """Response model for sync all stations operation"""
    success: bool
    total_detections_added: int
    stations_synced: int
    details: List[dict]
    weather_synced: bool = False
    weather_days_fetched: int = 0


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
        StationResponse(**station.to_dict(include_token=False))
        for station in stations
    ]


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


@router.post("/sync-all", response_model=SyncAllResponse)
async def sync_all_stations(
    db: Session = Depends(get_db_dependency)
):
    """
    Sync all active stations.

    Performs intelligent sync for all active stations, fetching new detections
    from current date back to last detection in database for each station.

    Returns:
        SyncAllResponse with total detections added and per-station details
    """
    import logging
    logger = logging.getLogger(__name__)

    station_repo = StationRepository(db)
    detection_repo = DetectionRepository(db)
    species_repo = SpeciesRepository(db)

    stations = station_repo.get_active_stations()
    if not stations:
        return SyncAllResponse(
            success=True,
            total_detections_added=0,
            stations_synced=0,
            details=[]
        )

    total_added = 0
    details = []

    for station in stations:
        try:
            result = _sync_station_detections(
                station, detection_repo, species_repo, station_repo, logger
            )
            total_added += result['detections_added']

            # Determine status message
            if result.get('reached_existing'):
                status = 'success (caught up to existing data)'
            elif result.get('reached_gap'):
                status = 'success (stopped at 7+ day gap)'
            elif result.get('reached_limit'):
                status = 'partial (hit page limit - run again for more)'
            else:
                status = 'success'

            details.append({
                'station_name': station.name,
                'detections_added': result['detections_added'],
                'status': status
            })
        except Exception as e:
            logger.error(f"Error syncing station {station.name}: {str(e)}")
            details.append({
                'station_name': station.name,
                'detections_added': 0,
                'status': f'error: {str(e)}'
            })

    # Sync weather for any new detection days
    weather_synced = False
    weather_days_fetched = 0
    try:
        from app.api.v1.weather import _sync_weather_internal
        weather_result = _sync_weather_internal(db)
        weather_synced = weather_result.get('success', False)
        weather_days_fetched = weather_result.get('days_fetched', 0)
        logger.info(f"Weather sync completed: {weather_days_fetched} days fetched")
    except Exception as e:
        logger.warning(f"Weather sync failed (non-critical): {str(e)}")

    return SyncAllResponse(
        success=True,
        total_detections_added=total_added,
        stations_synced=len(stations),
        details=details,
        weather_synced=weather_synced,
        weather_days_fetched=weather_days_fetched
    )


# ============================================
# Dynamic routes with {station_id} parameter
# ============================================

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
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    try:
        repo = StationRepository(db)

        # Check if station already exists
        existing = repo.get_by_birdweather_id(station_data.station_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Station with BirdWeather ID {station_data.station_id} already exists"
            )

        # Create station
        logger.info(f"Creating station with data: {station_data.model_dump()}")
        station = repo.create(**station_data.model_dump())
        logger.info(f"Station created: {station.id}")

        result = station.to_dict(include_token=False)
        logger.info(f"Station dict: {result}")

        return StationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating station: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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


def _sync_station_detections(
    station,
    detection_repo: DetectionRepository,
    species_repo: SpeciesRepository,
    station_repo: StationRepository,
    logger,
    max_pages: int = 500,
    max_gap_days: int = 7
) -> dict:
    """
    Internal function to sync detections for a single station.
    Uses intelligent sync: fetches from current date back until:
    - Finding existing data in the database, OR
    - Encountering a gap of max_gap_days with no detections

    Args:
        station: Station model instance
        detection_repo: DetectionRepository instance
        species_repo: SpeciesRepository instance
        station_repo: StationRepository instance
        logger: Logger instance
        max_pages: Maximum pages to fetch (safety limit)
        max_gap_days: Stop if no detections for this many days

    Returns dict with sync stats.
    """
    from datetime import date, timedelta

    # Initialize BirdWeather service
    bw_service = BirdWeatherAPI(station.api_token or "")

    # Get the last detection date from database for this station
    last_detection = detection_repo.get_latest_detection(station.id)
    last_date = last_detection.detection_date if last_detection else None
    is_initial_sync = last_date is None

    logger.info(f"Syncing station {station.name} (ID: {station.station_id}). Last detection in DB: {last_date}")

    detections_added = 0
    skipped_existing = 0
    skipped_no_species = 0
    reached_existing = False
    reached_gap = False
    station_gps_updated = False

    # Check if station needs GPS coordinates
    needs_gps = not station.latitude or not station.longitude

    # Track date of last detection seen to detect gaps
    prev_detection_date = None

    # Fetch detections page by page until we reach existing data or hit a gap
    cursor = None
    for page in range(max_pages):
        result = bw_service.get_detections(station.station_id, limit=100, cursor=cursor)
        detections = result.get('detections', [])

        if not detections:
            break

        for detection_data in detections:
            bw_detection_id = detection_data.get('id')

            # Check if detection already exists
            existing = detection_repo.get_by_birdweather_id(bw_detection_id, station.id)
            if existing:
                skipped_existing += 1
                # If we've found 10 consecutive existing records, assume we've caught up
                if skipped_existing > 10 and detections_added == 0:
                    reached_existing = True
                    break
                continue

            # Parse timestamp first to check date
            timestamp_str = detection_data.get('timestamp')
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = timestamp_str

            current_date = timestamp.date()

            # Check for gap in detections (7+ days with no data)
            if prev_detection_date and (prev_detection_date - current_date).days >= max_gap_days:
                logger.info(f"Detected gap of {(prev_detection_date - current_date).days} days - stopping sync")
                reached_gap = True
                break

            prev_detection_date = current_date

            # If we have a last_date and this detection is older or equal, we've caught up
            if last_date and current_date <= last_date:
                reached_existing = True
                break

            # Get or create species
            species_data = detection_data.get('species', {})
            bw_species_id = species_data.get('id')
            scientific_name = species_data.get('scientificName')
            common_name = species_data.get('commonName')

            if not bw_species_id or not scientific_name:
                skipped_no_species += 1
                continue

            species = species_repo.get_by_birdweather_id(bw_species_id)
            if not species:
                species = species_repo.create(
                    species_id=bw_species_id,
                    scientific_name=scientific_name,
                    common_name=common_name
                )

            # Capture GPS from detection data if station needs it
            detection_lat = detection_data.get('lat')
            detection_lon = detection_data.get('lon')

            if needs_gps and not station_gps_updated and detection_lat and detection_lon:
                # Update station with GPS from first detection
                station_repo.update(station.id, latitude=detection_lat, longitude=detection_lon)
                station_gps_updated = True
                logger.info(f"Updated station GPS from detection: {detection_lat}, {detection_lon}")

            # Create detection
            detection_repo.create(
                station_id=station.id,
                species_id=species.id,
                detection_id=bw_detection_id,
                timestamp=timestamp,
                confidence=detection_data.get('confidence', 0.0),
                latitude=detection_lat or station.latitude,
                longitude=detection_lon or station.longitude,
                detection_date=timestamp.date(),
                detection_hour=timestamp.hour
            )
            detections_added += 1

        if reached_existing or reached_gap:
            break

        # Set cursor for next page
        if len(detections) < 100:
            break
        cursor = detections[-1].get('id')
        if cursor is None:
            break

    # Update station last_update timestamp
    station_repo.update(station.id, last_update=datetime.utcnow())

    return {
        'station_id': station.id,
        'station_name': station.name,
        'detections_added': detections_added,
        'skipped_existing': skipped_existing,
        'skipped_no_species': skipped_no_species,
        'is_initial_sync': is_initial_sync,
        'reached_existing': reached_existing,
        'reached_gap': reached_gap,
        'reached_limit': not reached_existing and not reached_gap and page >= max_pages - 1
    }


@router.post("/{station_id}/sync", response_model=SyncResponse)
async def sync_station_data(
    station_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Intelligent sync: fetch detections from current date back to last detection in database.

    This endpoint fetches new detections from BirdWeather starting from today
    and going back until it reaches detections already in the database.

    Args:
        station_id: Database ID of the station to sync

    Returns:
        SyncResponse with count of detections added
    """
    import logging
    logger = logging.getLogger(__name__)

    station_repo = StationRepository(db)
    detection_repo = DetectionRepository(db)
    species_repo = SpeciesRepository(db)

    station = station_repo.get_by_id(station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    try:
        result = _sync_station_detections(
            station, detection_repo, species_repo, station_repo, logger
        )

        return SyncResponse(
            success=True,
            detections_added=result['detections_added'],
            message=f"Synced {result['detections_added']} new detections for {station.name}"
        )

    except Exception as e:
        logger.error(f"Sync error for station {station_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync: {str(e)}"
        )
