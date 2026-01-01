"""
Weather API Endpoints
Endpoints for fetching and managing weather data.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime, time, timedelta
import logging

from app.api.deps import get_db_dependency
from app.db.models.weather import Weather
from app.db.models.station import Station
from app.db.models.detection import Detection
from app.db.models.setting import Setting
from app.services.weather import WeatherAPI

logger = logging.getLogger(__name__)

router = APIRouter()


class WeatherResponse(BaseModel):
    """Weather response model."""
    id: int
    station_id: int
    weather_date: date
    latitude: float
    longitude: float
    temp_max: Optional[float] = None
    temp_min: Optional[float] = None
    temp_avg: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    precipitation: Optional[float] = None
    weather_description: Optional[str] = None
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    day_length: Optional[str] = None


class WeatherSyncResponse(BaseModel):
    """Response for weather sync operations."""
    success: bool
    days_fetched: int
    days_skipped: int
    days_failed: int
    message: str


class WeatherStationSetting(BaseModel):
    """Weather station setting response."""
    station_id: Optional[int] = None
    station_name: Optional[str] = None


@router.get("/", response_model=List[WeatherResponse])
async def get_weather(
    station_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    db: Session = Depends(get_db_dependency)
):
    """
    Get weather records.

    Optionally filter by station, date range, and limit results.
    """
    query = db.query(Weather)

    if station_id:
        query = query.filter(Weather.station_id == station_id)
    if start_date:
        query = query.filter(Weather.weather_date >= start_date)
    if end_date:
        query = query.filter(Weather.weather_date <= end_date)

    records = query.order_by(Weather.weather_date.desc()).limit(limit).all()

    return [
        WeatherResponse(
            id=r.id,
            station_id=r.station_id,
            weather_date=r.weather_date,
            latitude=r.latitude,
            longitude=r.longitude,
            temp_max=r.temp_max,
            temp_min=r.temp_min,
            temp_avg=r.temp_avg,
            humidity=r.humidity,
            pressure=r.pressure,
            wind_speed=r.wind_speed,
            precipitation=r.precipitation,
            weather_description=r.weather_description,
            sunrise=r.sunrise.strftime('%H:%M:%S') if r.sunrise else None,
            sunset=r.sunset.strftime('%H:%M:%S') if r.sunset else None,
            day_length=r.day_length
        )
        for r in records
    ]


@router.get("/station-setting", response_model=WeatherStationSetting)
async def get_weather_station_setting(db: Session = Depends(get_db_dependency)):
    """
    Get the currently selected weather station.
    """
    setting = db.query(Setting).filter(Setting.key == 'weather_station_id').first()

    if not setting or not setting.value:
        return WeatherStationSetting(station_id=None, station_name=None)

    try:
        station_id = int(setting.value)
        station = db.query(Station).filter(Station.id == station_id).first()
        if station:
            return WeatherStationSetting(
                station_id=station.id,
                station_name=station.name
            )
    except (ValueError, TypeError):
        pass

    return WeatherStationSetting(station_id=None, station_name=None)


@router.put("/station-setting/{station_id}", response_model=WeatherStationSetting)
async def set_weather_station(
    station_id: int,
    db: Session = Depends(get_db_dependency)
):
    """
    Set the station to use for weather data.

    Weather will be fetched using this station's GPS coordinates.
    """
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    if not station.latitude or not station.longitude:
        raise HTTPException(
            status_code=400,
            detail="Station does not have GPS coordinates. Sync detections first."
        )

    # Update or create setting
    setting = db.query(Setting).filter(Setting.key == 'weather_station_id').first()
    if setting:
        setting.value = str(station_id)
    else:
        setting = Setting(
            key='weather_station_id',
            value=str(station_id),
            data_type='int',
            description='Station ID to use for weather data location'
        )
        db.add(setting)

    db.commit()

    return WeatherStationSetting(
        station_id=station.id,
        station_name=station.name
    )


@router.get("/date/{weather_date}", response_model=Optional[WeatherResponse])
async def get_weather_for_date(
    weather_date: date,
    db: Session = Depends(get_db_dependency)
):
    """
    Get weather for a specific date using the configured weather station.
    """
    # Get weather station setting
    setting = db.query(Setting).filter(Setting.key == 'weather_station_id').first()
    if not setting or not setting.value:
        raise HTTPException(
            status_code=400,
            detail="No weather station configured. Set a weather station first."
        )

    station_id = int(setting.value)

    # Check if we have cached weather
    weather = db.query(Weather).filter(
        Weather.station_id == station_id,
        Weather.weather_date == weather_date
    ).first()

    if weather:
        return WeatherResponse(
            id=weather.id,
            station_id=weather.station_id,
            weather_date=weather.weather_date,
            latitude=weather.latitude,
            longitude=weather.longitude,
            temp_max=weather.temp_max,
            temp_min=weather.temp_min,
            temp_avg=weather.temp_avg,
            humidity=weather.humidity,
            pressure=weather.pressure,
            wind_speed=weather.wind_speed,
            precipitation=weather.precipitation,
            weather_description=weather.weather_description,
            sunrise=weather.sunrise.strftime('%H:%M:%S') if weather.sunrise else None,
            sunset=weather.sunset.strftime('%H:%M:%S') if weather.sunset else None,
            day_length=weather.day_length
        )

    return None


def _sync_weather_internal(db: Session) -> dict:
    """
    Internal function to sync weather data for all days that have detections.

    Can be called from other modules (e.g., stations sync).

    Returns:
        dict with success, days_fetched, days_skipped, days_failed, message
    """
    # Get weather station setting
    setting = db.query(Setting).filter(Setting.key == 'weather_station_id').first()
    if not setting or not setting.value:
        return {
            'success': False,
            'days_fetched': 0,
            'days_skipped': 0,
            'days_failed': 0,
            'message': 'No weather station configured'
        }

    station_id = int(setting.value)
    station = db.query(Station).filter(Station.id == station_id).first()

    if not station:
        return {
            'success': False,
            'days_fetched': 0,
            'days_skipped': 0,
            'days_failed': 0,
            'message': 'Weather station not found'
        }

    if not station.latitude or not station.longitude:
        return {
            'success': False,
            'days_fetched': 0,
            'days_skipped': 0,
            'days_failed': 0,
            'message': 'Weather station does not have GPS coordinates'
        }

    # Get all unique detection dates - normalize to date strings for comparison
    detection_dates_raw = db.query(func.distinct(Detection.detection_date)).all()
    detection_dates = []
    for d in detection_dates_raw:
        if d[0]:
            # Normalize to string for consistent comparison
            if isinstance(d[0], str):
                detection_dates.append(d[0])
            else:
                detection_dates.append(d[0].isoformat())

    if not detection_dates:
        return {
            'success': True,
            'days_fetched': 0,
            'days_skipped': 0,
            'days_failed': 0,
            'message': 'No detection dates found'
        }

    # Get existing weather dates for this station - normalize to strings
    existing_dates_raw = db.query(Weather.weather_date).filter(
        Weather.station_id == station_id
    ).all()
    existing_dates = set()
    for d in existing_dates_raw:
        if d[0]:
            if isinstance(d[0], str):
                existing_dates.add(d[0])
            else:
                existing_dates.add(d[0].isoformat())

    # Find missing dates (comparing strings now)
    missing_dates = [d for d in detection_dates if d not in existing_dates]

    logger.info(f"Weather sync: {len(detection_dates)} detection days, "
                f"{len(existing_dates)} already have weather, "
                f"{len(missing_dates)} need fetching")

    weather_api = WeatherAPI()
    days_fetched = 0
    days_failed = 0

    for weather_date in sorted(missing_dates):
        try:
            # Handle both date objects and strings from SQLite
            if isinstance(weather_date, str):
                date_str = weather_date
                weather_date = datetime.strptime(weather_date, '%Y-%m-%d').date()
            else:
                date_str = weather_date.isoformat()

            # Fetch weather data
            weather_data = weather_api.get_historical_weather(
                station.latitude,
                station.longitude,
                date_str
            )

            # Fetch sunrise/sunset
            sun_data = weather_api.get_sunrise_sunset(
                station.latitude,
                station.longitude,
                date_str
            )

            if weather_data:
                # Parse sunrise/sunset times
                sunrise_time = None
                sunset_time = None
                day_length = None

                if sun_data:
                    if sun_data.get('sunrise'):
                        try:
                            sunrise_time = datetime.strptime(
                                sun_data['sunrise'], '%H:%M:%S'
                            ).time()
                        except ValueError:
                            pass
                    if sun_data.get('sunset'):
                        try:
                            sunset_time = datetime.strptime(
                                sun_data['sunset'], '%H:%M:%S'
                            ).time()
                        except ValueError:
                            pass
                    day_length = sun_data.get('day_length')

                # Check if record already exists (race condition protection)
                existing = db.query(Weather).filter(
                    Weather.station_id == station_id,
                    Weather.weather_date == weather_date
                ).first()

                if existing:
                    # Already have data, skip
                    continue

                # Create weather record
                weather_record = Weather(
                    station_id=station_id,
                    weather_date=weather_date,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    temp_max=weather_data.get('temp_max'),
                    temp_min=weather_data.get('temp_min'),
                    temp_avg=weather_data.get('temp_avg'),
                    humidity=weather_data.get('humidity'),
                    pressure=weather_data.get('pressure'),
                    wind_speed=weather_data.get('wind_speed'),
                    precipitation=weather_data.get('precipitation'),
                    weather_description=weather_data.get('description'),
                    sunrise=sunrise_time,
                    sunset=sunset_time,
                    day_length=day_length
                )
                db.add(weather_record)
                days_fetched += 1

                # Commit each record individually to avoid losing progress
                try:
                    db.commit()
                except Exception as commit_err:
                    db.rollback()
                    days_failed += 1
                    days_fetched -= 1
                    logger.warning(f"Failed to save weather for {date_str}: {commit_err}")
                    continue

                if days_fetched % 10 == 0:
                    logger.info(f"Weather sync progress: {days_fetched} days fetched")
            else:
                days_failed += 1
                logger.warning(f"Failed to fetch weather for {date_str}")

        except Exception as e:
            db.rollback()
            days_failed += 1
            logger.error(f"Error fetching weather for {weather_date}: {e}")

    db.commit()

    return {
        'success': True,
        'days_fetched': days_fetched,
        'days_skipped': len(existing_dates),
        'days_failed': days_failed,
        'message': f"Fetched weather for {days_fetched} days. "
                   f"{len(existing_dates)} days already had data. "
                   f"{days_failed} days failed."
    }


@router.post("/sync", response_model=WeatherSyncResponse)
async def sync_weather_for_detection_days(
    db: Session = Depends(get_db_dependency)
):
    """
    Intelligently sync weather data for all days that have detections.

    This will:
    1. Find all unique detection dates
    2. Check which dates are missing weather data
    3. Fetch weather for those dates from Open-Meteo
    """
    result = _sync_weather_internal(db)

    # If not successful due to configuration issues, raise HTTP exception
    if not result['success'] and result['days_fetched'] == 0:
        raise HTTPException(status_code=400, detail=result['message'])

    return WeatherSyncResponse(
        success=result['success'],
        days_fetched=result['days_fetched'],
        days_skipped=result['days_skipped'],
        days_failed=result['days_failed'],
        message=result['message']
    )


@router.get("/stats")
async def get_weather_stats(db: Session = Depends(get_db_dependency)):
    """
    Get weather data statistics.
    """
    total_records = db.query(Weather).count()

    # Get date range
    date_range = db.query(
        func.min(Weather.weather_date),
        func.max(Weather.weather_date)
    ).first()

    # Get detection days without weather
    detection_dates = db.query(func.distinct(Detection.detection_date)).count()
    weather_dates = db.query(func.distinct(Weather.weather_date)).count()

    # Get weather station setting
    setting = db.query(Setting).filter(Setting.key == 'weather_station_id').first()
    station_name = None
    if setting and setting.value:
        station = db.query(Station).filter(Station.id == int(setting.value)).first()
        if station:
            station_name = station.name

    return {
        'total_weather_records': total_records,
        'first_date': date_range[0].isoformat() if date_range[0] else None,
        'last_date': date_range[1].isoformat() if date_range[1] else None,
        'detection_days': detection_dates,
        'weather_days': weather_dates,
        'missing_days': max(0, detection_dates - weather_dates),
        'weather_station': station_name
    }
