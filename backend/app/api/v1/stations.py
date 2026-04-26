"""
Station API Endpoints
Endpoints for managing and querying station data.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Generator
import json

from app.api.deps import get_db_dependency, get_current_user
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
from app.db.models.detection import Detection as DetectionModel
from app.db.models.detection_day_verification import DetectionDayVerification
from pydantic import BaseModel
from datetime import datetime, date as date_type
from sqlalchemy import func as sa_func

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
    force_full: bool = False,
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Sync all active stations.

    Performs intelligent sync for all active stations, fetching new detections
    from current date back to last detection in database for each station.

    Args:
        force_full: When True, paginate all the way through BirdWeather's
            history for each station, ignoring the catch-up early-stop. Use
            this once to recover from past sync gaps; normal incremental
            syncs should leave it False.

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
                station, detection_repo, species_repo, station_repo, logger,
                force_full=force_full,
            )
            total_added += result['detections_added']

            # Determine status message
            if result.get('reached_existing'):
                status = 'success (caught up to existing data)'
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

    # Update species cached statistics if any detections were added
    if total_added > 0:
        try:
            species_repo.update_all_cached_stats()
            logger.info("Species cached statistics updated")
        except Exception as e:
            logger.warning(f"Species stats update failed (non-critical): {str(e)}")

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


@router.post("/sync-all-stream")
async def sync_all_stations_stream(
    force_full: bool = False,
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Sync all active stations with streaming progress updates.

    Returns newline-delimited JSON with progress updates to keep connection alive
    and show progress to the user. See `sync_all_stations` for `force_full`.
    """
    def generate_sync_progress() -> Generator[str, None, None]:
        import logging
        logger = logging.getLogger(__name__)

        station_repo = StationRepository(db)
        detection_repo = DetectionRepository(db)
        species_repo = SpeciesRepository(db)

        stations = station_repo.get_active_stations()

        # Initial status
        yield json.dumps({
            "type": "start",
            "message": f"Starting sync for {len(stations)} stations...",
            "total_stations": len(stations)
        }) + "\n"

        if not stations:
            yield json.dumps({
                "type": "complete",
                "success": True,
                "total_detections_added": 0,
                "stations_synced": 0,
                "details": []
            }) + "\n"
            return

        total_added = 0
        details = []

        for i, station in enumerate(stations):
            # Progress update before sync
            yield json.dumps({
                "type": "progress",
                "message": f"Syncing station: {station.name}",
                "station_index": i + 1,
                "total_stations": len(stations),
                "station_name": station.name
            }) + "\n"

            try:
                result = _sync_station_detections(
                    station, detection_repo, species_repo, station_repo, logger,
                    force_full=force_full,
                )
                total_added += result['detections_added']

                # Determine status message
                if result.get('reached_existing'):
                    status = 'success (caught up to existing data)'
                elif result.get('reached_limit'):
                    status = 'partial (hit page limit - run again for more)'
                else:
                    status = 'success'

                detail = {
                    'station_name': station.name,
                    'detections_added': result['detections_added'],
                    'status': status
                }
                details.append(detail)

                # Progress update after station sync
                yield json.dumps({
                    "type": "station_complete",
                    "station_name": station.name,
                    "detections_added": result['detections_added'],
                    "status": status,
                    "running_total": total_added
                }) + "\n"

            except Exception as e:
                logger.error(f"Error syncing station {station.name}: {str(e)}")
                detail = {
                    'station_name': station.name,
                    'detections_added': 0,
                    'status': f'error: {str(e)}'
                }
                details.append(detail)

                yield json.dumps({
                    "type": "station_error",
                    "station_name": station.name,
                    "error": str(e)
                }) + "\n"

        # Weather sync
        yield json.dumps({
            "type": "progress",
            "message": "Syncing weather data..."
        }) + "\n"

        weather_synced = False
        weather_days_fetched = 0
        try:
            from app.api.v1.weather import _sync_weather_internal
            weather_result = _sync_weather_internal(db)
            weather_synced = weather_result.get('success', False)
            weather_days_fetched = weather_result.get('days_fetched', 0)

            yield json.dumps({
                "type": "weather_complete",
                "success": weather_synced,
                "days_fetched": weather_days_fetched
            }) + "\n"
        except Exception as e:
            logger.warning(f"Weather sync failed (non-critical): {str(e)}")
            yield json.dumps({
                "type": "weather_error",
                "error": str(e)
            }) + "\n"

        # Refresh species stats if we added any detections
        if total_added > 0:
            yield json.dumps({
                "type": "progress",
                "message": "Updating species statistics..."
            }) + "\n"
            try:
                species_updated = species_repo.update_all_cached_stats()
                yield json.dumps({
                    "type": "stats_complete",
                    "species_updated": species_updated
                }) + "\n"
            except Exception as e:
                logger.warning(f"Species stats update failed: {str(e)}")

        # Final result
        yield json.dumps({
            "type": "complete",
            "success": True,
            "total_detections_added": total_added,
            "stations_synced": len(stations),
            "details": details,
            "weather_synced": weather_synced,
            "weather_days_fetched": weather_days_fetched
        }) + "\n"

    return StreamingResponse(
        generate_sync_progress(),
        media_type="application/x-ndjson"
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
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
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
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
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
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
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


@router.get("/species/by-station")
async def get_species_by_station(
    db: Session = Depends(get_db_dependency)
):
    """
    Get species lists for each station (for UpSet plot).

    Returns a dict with station names as keys and lists of species objects
    (with common_name and ebird_code) as values.
    """
    from app.db.models.species import Species
    from app.db.models.detection import Detection
    from sqlalchemy import distinct
    from app.services import taxonomy_translations as _tx

    station_repo = StationRepository(db)
    stations = station_repo.get_active_stations()

    lang = _tx.current_language()

    result = {}
    for station in stations:
        # Get unique species for this station
        species_query = (
            db.query(
                Species.id,
                Species.common_name,
                Species.scientific_name,
                Species.ebird_code,
                Species.inat_taxon_id,
            )
            .join(Detection, Species.id == Detection.species_id)
            .filter(Detection.station_id == station.id)
            .distinct()
            .order_by(Species.common_name)
        )
        species_list = []
        for row in species_query.all():
            localized = _tx.translate_common_name(row.id, row.common_name) if lang else row.common_name
            species_list.append({
                "common_name": localized,
                "english_name": row.common_name if lang and localized != row.common_name else None,
                "scientific_name": row.scientific_name,
                "ebird_code": row.ebird_code,
                "inat_taxon_id": row.inat_taxon_id,
            })
        result[station.name] = species_list

    return result


def _update_day_verification(
    db: Session,
    station_id: int,
    dates_added: dict,
    dates_seen: set,
    logger,
) -> int:
    """
    Upsert `detection_day_verification` rows for every date the sync touched.

    A "touched" date is one that appeared in the BirdWeather pagination this
    run (whether or not we added anything for it). For each:

    - `read_count` is incremented by one
    - `last_added` is set to the number of new rows inserted this run for that date
    - `detections_count` is refreshed from the actual `detections` table
    - `verified` is set to True iff `read_count >= 2 AND last_added == 0`
    - if `last_added > 0`, `verified` is forced back to False — a backfill
      invalidates a prior True

    Returns the number of dates updated.
    """
    from app.db.models.detection_day_verification import DetectionDayVerification

    if not dates_seen:
        return 0

    # Count detections per date in one query for the dates we touched.
    counts_rows = (
        db.query(DetectionModel.detection_date, sa_func.count(DetectionModel.id))
        .filter(DetectionModel.station_id == station_id)
        .filter(DetectionModel.detection_date.in_(list(dates_seen)))
        .group_by(DetectionModel.detection_date)
        .all()
    )
    actual_counts = {row[0]: row[1] for row in counts_rows}

    existing = (
        db.query(DetectionDayVerification)
        .filter(DetectionDayVerification.station_id == station_id)
        .filter(DetectionDayVerification.detection_date.in_(list(dates_seen)))
        .all()
    )
    by_date = {r.detection_date: r for r in existing}

    updated = 0
    now = datetime.utcnow()
    for d in dates_seen:
        added = dates_added.get(d, 0)
        count = actual_counts.get(d, 0)
        row = by_date.get(d)
        if row is None:
            row = DetectionDayVerification(
                station_id=station_id,
                detection_date=d,
                detections_count=count,
                read_count=1,
                last_added=added,
                verified=False,
                first_synced_at=now,
                last_synced_at=now,
            )
            db.add(row)
        else:
            row.read_count += 1
            row.last_added = added
            row.detections_count = count
            row.last_synced_at = now
            if added > 0:
                row.verified = False
            elif row.read_count >= 2:
                row.verified = True
        updated += 1

    db.commit()
    logger.info(
        "Updated day-verification rows: station=%s touched_dates=%d",
        station_id,
        updated,
    )
    return updated


def _sync_station_detections(
    station,
    detection_repo: DetectionRepository,
    species_repo: SpeciesRepository,
    station_repo: StationRepository,
    logger,
    max_pages: int = 5000,
    force_full: bool = False,
    catchup_window: int = 50,
    verified_window_days: int = 7,
) -> dict:
    """
    Sync detections for a single station from BirdWeather.

    Walks BirdWeather's cursor-based pagination newest-first. Each detection
    is matched to the local DB by `bw_detection_id`; existing rows are
    skipped, new rows are inserted. Stop conditions, in order:

    1. BirdWeather returned an empty/short page (nothing more upstream).
    2. Normal mode only: `verified_window_days` consecutive previously-
       verified dates yielded zero new rows in this run — those days have
       already been confirmed twice and there's nothing new in the recent
       walk, so the older history is also stable.
    3. Normal mode fallback: `catchup_window` consecutive already-known IDs
       (the per-detection equivalent of stop 2; useful for stations that
       haven't built up verification history yet).
    4. `max_pages` safety cap (normal mode only). When `force_full=True` we
       walk until BirdWeather returns an empty page, ignoring `max_pages` —
       built-in continuation, no need for the manual chained passes that
       were required pre-v2.1.2.

    The `dates_added` accumulator drives the verification table writes that
    happen at the end of the sync via `_update_day_verification`.
    """
    bw_service = BirdWeatherAPI(station.api_token or "")

    last_detection = detection_repo.get_latest_detection(station.id)
    is_initial_sync = last_detection is None

    db = species_repo.db  # piggy-back the SessionLocal session for verification rows

    # Pre-load the set of already-verified dates so the new stop condition can
    # consult it without a per-page DB hit.
    from app.db.models.detection_day_verification import DetectionDayVerification
    verified_dates = {
        row.detection_date
        for row in db.query(DetectionDayVerification.detection_date)
        .filter(DetectionDayVerification.station_id == station.id)
        .filter(DetectionDayVerification.verified.is_(True))
        .all()
    }

    logger.info(
        "Syncing station %s (BW ID %s). force_full=%s, last_detection_id=%s, "
        "verified_dates=%d",
        station.name,
        station.station_id,
        force_full,
        getattr(last_detection, "detection_id", None),
        len(verified_dates),
    )

    detections_added = 0
    skipped_existing = 0
    skipped_no_species = 0
    consecutive_existing = 0
    reached_caught_up = False
    station_gps_updated = False
    needs_gps = not station.latitude or not station.longitude

    # Per-date tracking for the verification table.
    dates_added: dict = {}
    dates_seen: set = set()
    consecutive_verified_dates = 0
    last_seen_date = None

    cursor = None
    pages_fetched = 0
    # Hard cap to prevent runaway loops if BW ever streams the same cursor
    # back forever. force_full disables the soft `max_pages` cap.
    HARD_CAP = max(max_pages * 20, 100_000)
    while pages_fetched < HARD_CAP:
        if not force_full and pages_fetched >= max_pages:
            break

        pages_fetched += 1
        result = bw_service.get_detections(station.station_id, limit=100, cursor=cursor)
        detections = result.get('detections', [])
        if not detections:
            break

        for detection_data in detections:
            bw_detection_id = detection_data.get('id')
            if not bw_detection_id:
                continue

            timestamp_str = detection_data.get('timestamp')
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = timestamp_str
            current_date = timestamp.date()
            dates_seen.add(current_date)

            # Track date transitions for the verified-window stop.
            if last_seen_date is not None and current_date != last_seen_date:
                # Just rolled over to an older date. Decide whether to count it.
                if last_seen_date in verified_dates and dates_added.get(last_seen_date, 0) == 0:
                    consecutive_verified_dates += 1
                    if not force_full and consecutive_verified_dates >= verified_window_days:
                        reached_caught_up = True
                        break
                else:
                    consecutive_verified_dates = 0
            last_seen_date = current_date

            if detection_repo.get_by_birdweather_id(bw_detection_id, station.id):
                skipped_existing += 1
                consecutive_existing += 1
                if not force_full and consecutive_existing >= catchup_window:
                    reached_caught_up = True
                    break
                continue

            # New detection — reset both catchup counters so the loop keeps
            # walking back through pages that mix new + existing IDs.
            consecutive_existing = 0
            consecutive_verified_dates = 0

            species_data = detection_data.get('species', {})
            bw_species_id = species_data.get('id')
            scientific_name = species_data.get('scientificName')
            common_name = species_data.get('commonName')

            if not bw_species_id or not scientific_name:
                skipped_no_species += 1
                continue

            species = species_repo.get_by_birdweather_id(bw_species_id)
            if not species:
                species = species_repo.get_by_scientific_name(scientific_name)
            if not species:
                species = species_repo.create(
                    species_id=bw_species_id,
                    scientific_name=scientific_name,
                    common_name=common_name,
                )

            detection_lat = detection_data.get('lat')
            detection_lon = detection_data.get('lon')
            if needs_gps and not station_gps_updated and detection_lat and detection_lon:
                station_repo.update(station.id, latitude=detection_lat, longitude=detection_lon)
                station_gps_updated = True
                logger.info(
                    "Updated station GPS from detection: %s, %s",
                    detection_lat,
                    detection_lon,
                )

            detection_repo.create(
                station_id=station.id,
                species_id=species.id,
                detection_id=bw_detection_id,
                timestamp=timestamp,
                confidence=detection_data.get('confidence', 0.0),
                latitude=detection_lat or station.latitude,
                longitude=detection_lon or station.longitude,
                detection_date=current_date,
                detection_hour=timestamp.hour,
            )
            detections_added += 1
            dates_added[current_date] = dates_added.get(current_date, 0) + 1

        if reached_caught_up:
            break
        if len(detections) < 100:
            break
        cursor = detections[-1].get('id')
        if cursor is None:
            break

    station_repo.update(station.id, last_update=datetime.utcnow())

    # Side effect: record per-date verification status for every date this run touched.
    try:
        _update_day_verification(db, station.id, dates_added, dates_seen, logger)
    except Exception as e:
        logger.warning("Day-verification update failed (non-critical): %s", e)
        try:
            db.rollback()
        except Exception:
            pass

    return {
        'station_id': station.id,
        'station_name': station.name,
        'detections_added': detections_added,
        'skipped_existing': skipped_existing,
        'skipped_no_species': skipped_no_species,
        'is_initial_sync': is_initial_sync,
        'reached_existing': reached_caught_up,
        'reached_gap': False,
        'reached_limit': not reached_caught_up and not force_full and pages_fetched >= max_pages,
        'pages_fetched': pages_fetched,
        'force_full': force_full,
        'dates_touched': len(dates_seen),
    }


@router.post("/{station_id}/sync", response_model=SyncResponse)
async def sync_station_data(
    station_id: int,
    force_full: bool = False,
    db: Session = Depends(get_db_dependency),
    current_user: dict = Depends(get_current_user)
):
    """
    Intelligent sync: fetch detections from current date back to last detection in database.

    This endpoint fetches new detections from BirdWeather starting from today
    and going back until it reaches detections already in the database.

    Args:
        station_id: Database ID of the station to sync
        force_full: When True, paginate the full BirdWeather history for the
            station. Use to recover detections missed by earlier (buggy)
            incremental syncs.

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
            station, detection_repo, species_repo, station_repo, logger,
            force_full=force_full,
        )

        # Update species cached statistics if detections were added
        if result['detections_added'] > 0:
            try:
                species_repo.update_all_cached_stats()
                logger.info("Species cached statistics updated")
            except Exception as e:
                logger.warning(f"Species stats update failed (non-critical): {str(e)}")

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
