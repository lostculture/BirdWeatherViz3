"""
Background Scheduler for Automatic Station Updates
Handles periodic updates of station detection data.

Version: 1.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal
from app.repositories.station import StationRepository
from app.repositories.detection import DetectionRepository
from app.repositories.species import SpeciesRepository

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None


def get_next_station_to_update(db: Session) -> Optional[dict]:
    """
    Get the next station that should be updated.

    Rules:
    - Only active stations
    - No station updated more than once per hour
    - Prioritize stations that haven't been updated recently

    Returns station info dict or None if no station needs updating.
    """
    station_repo = StationRepository(db)

    # Get all active stations
    stations = station_repo.get_active_stations()

    if not stations:
        return None

    # Find stations eligible for update (not updated in last hour)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    eligible_stations = []
    for station in stations:
        last_update = station.last_update
        if last_update is None or last_update < one_hour_ago:
            eligible_stations.append({
                'id': station.id,
                'name': station.name,
                'station_id': station.station_id,
                'last_update': last_update,
                'api_token': station.api_token
            })

    if not eligible_stations:
        logger.debug("No stations eligible for update (all updated within last hour)")
        return None

    # Sort by last_update (oldest first, None = never updated = highest priority)
    eligible_stations.sort(
        key=lambda s: s['last_update'] or datetime.min
    )

    return eligible_stations[0]


def sync_station_job():
    """
    Background job to sync a single station.
    Called every 10 minutes by the scheduler.
    """
    from app.api.v1.stations import _sync_station_detections

    logger.info("Running scheduled station sync job")

    db = SessionLocal()
    try:
        # Get next station to update
        station_info = get_next_station_to_update(db)

        if not station_info:
            logger.info("No stations need updating at this time")
            return

        logger.info(f"Syncing station: {station_info['name']} (last update: {station_info['last_update']})")

        # Get the full station object
        station_repo = StationRepository(db)
        station = station_repo.get_by_id(station_info['id'])

        if not station:
            logger.error(f"Station {station_info['id']} not found")
            return

        # Perform the sync
        detection_repo = DetectionRepository(db)
        species_repo = SpeciesRepository(db)

        result = _sync_station_detections(
            station=station,
            detection_repo=detection_repo,
            species_repo=species_repo,
            station_repo=station_repo,
            logger=logger
        )

        logger.info(
            f"Sync complete for {station.name}: "
            f"{result['detections_added']} added, "
            f"{result['skipped_existing']} skipped"
        )

        # Update species stats if detections were added
        if result['detections_added'] > 0:
            logger.info("Updating species statistics...")
            species_repo.update_all_cached_stats()

            # Sync weather for new detection dates
            try:
                from app.api.v1.weather import _sync_weather_internal
                logger.info("Syncing weather data for new detections...")
                weather_result = _sync_weather_internal(db)
                logger.info(f"Weather sync: {weather_result.get('days_fetched', 0)} days fetched")
            except Exception as e:
                logger.warning(f"Weather sync failed (non-critical): {e}")

        db.commit()

    except Exception as e:
        logger.error(f"Error in scheduled sync job: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler for automatic updates.
    """
    global scheduler

    if not settings.AUTO_UPDATE_ENABLED:
        logger.info("Auto-update is disabled in settings")
        return

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    scheduler = BackgroundScheduler()

    # Add job to run every 10 minutes
    scheduler.add_job(
        sync_station_job,
        trigger=IntervalTrigger(minutes=10),
        id='station_sync_job',
        name='Sync station detections',
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
        coalesce=True  # Combine missed runs into one
    )

    scheduler.start()
    logger.info("Background scheduler started - station sync every 10 minutes")


def stop_scheduler():
    """
    Stop the background scheduler.
    """
    global scheduler

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("Background scheduler stopped")


def get_scheduler_status() -> dict:
    """
    Get the current status of the scheduler.
    """
    global scheduler

    if scheduler is None:
        return {
            'running': False,
            'enabled': settings.AUTO_UPDATE_ENABLED,
            'next_run': None,
            'jobs': []
        }

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return {
        'running': scheduler.running,
        'enabled': settings.AUTO_UPDATE_ENABLED,
        'jobs': jobs
    }
