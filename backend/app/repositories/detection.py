"""
Detection Repository
Data access methods for detection queries.

Version: 1.0.0
"""

from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.db.models.detection import Detection
from app.db.models.species import Species
from app.db.models.station import Station
from app.repositories.base import BaseRepository


class DetectionRepository(BaseRepository[Detection]):
    """Repository for detection data access."""

    def __init__(self, db: Session):
        super().__init__(Detection, db)

    def get_by_birdweather_id(self, birdweather_detection_id: int, station_id: int) -> Optional[Detection]:
        """
        Get detection by BirdWeather detection ID and station ID.

        Args:
            birdweather_detection_id: BirdWeather API detection ID
            station_id: Database station ID

        Returns:
            Detection instance or None if not found
        """
        return self.db.query(Detection).filter(
            Detection.detection_id == birdweather_detection_id,
            Detection.station_id == station_id
        ).first()

    def get_latest_detection(self, station_id: int) -> Optional[Detection]:
        """
        Get the most recent detection for a station.

        Args:
            station_id: Database station ID

        Returns:
            Most recent Detection instance or None
        """
        return self.db.query(Detection).filter(
            Detection.station_id == station_id
        ).order_by(Detection.timestamp.desc()).first()

    def get_daily_detections(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get daily detection counts grouped by station.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            station_ids: Filter by station IDs

        Returns:
            List of dicts with detection_date, station_id, station_name, detection_count
        """
        query = (
            self.db.query(
                Detection.detection_date,
                Detection.station_id,
                Station.name.label('station_name'),
                func.count(Detection.id).label('detection_count')
            )
            .join(Station, Detection.station_id == Station.id)
        )

        # Apply filters
        if start_date:
            query = query.filter(Detection.detection_date >= start_date)
        if end_date:
            query = query.filter(Detection.detection_date <= end_date)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        # Group and order
        query = query.group_by(
            Detection.detection_date,
            Detection.station_id,
            Station.name
        ).order_by(Detection.detection_date)

        results = query.all()

        return [
            {
                'detection_date': row.detection_date,
                'station_id': row.station_id,
                'station_name': row.station_name,
                'detection_count': row.detection_count
            }
            for row in results
        ]

    def get_detections_by_species(
        self,
        species_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get detections for a specific species over time.

        Args:
            species_id: Database species ID
            start_date: Filter by start date
            end_date: Filter by end date
            station_ids: Filter by station IDs

        Returns:
            List of dicts with detection_date, station_id, detection_count, avg_confidence
        """
        query = (
            self.db.query(
                Detection.detection_date,
                Detection.station_id,
                Station.name.label('station_name'),
                func.count(Detection.id).label('detection_count'),
                func.avg(Detection.confidence).label('avg_confidence')
            )
            .join(Station, Detection.station_id == Station.id)
            .filter(Detection.species_id == species_id)
        )

        # Apply filters
        if start_date:
            query = query.filter(Detection.detection_date >= start_date)
        if end_date:
            query = query.filter(Detection.detection_date <= end_date)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        # Group and order
        query = query.group_by(
            Detection.detection_date,
            Detection.station_id,
            Station.name
        ).order_by(Detection.detection_date)

        results = query.all()

        return [
            {
                'detection_date': row.detection_date,
                'station_id': row.station_id,
                'station_name': row.station_name,
                'detection_count': row.detection_count,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0
            }
            for row in results
        ]

    def get_hourly_pattern(
        self,
        species_id: Optional[int] = None,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get hourly detection pattern (24-hour distribution).

        Args:
            species_id: Optional species ID to filter
            station_ids: Optional station IDs to filter

        Returns:
            List of dicts with hour, detection_count
        """
        query = (
            self.db.query(
                Detection.detection_hour.label('hour'),
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.detection_hour.isnot(None))
        )

        # Apply filters
        if species_id:
            query = query.filter(Detection.species_id == species_id)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        # Group and order
        query = query.group_by(Detection.detection_hour).order_by(Detection.detection_hour)

        results = query.all()

        return [
            {
                'hour': row.hour,
                'detection_count': row.detection_count
            }
            for row in results
        ]

    def get_recent_detections(
        self,
        limit: int = 100,
        station_ids: Optional[List[int]] = None
    ) -> List[Detection]:
        """
        Get most recent detections.

        Args:
            limit: Maximum number of detections to return
            station_ids: Optional station IDs to filter

        Returns:
            List of Detection instances
        """
        query = self.db.query(Detection).options(
            joinedload(Detection.species),
            joinedload(Detection.station)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        return query.order_by(Detection.timestamp.desc()).limit(limit).all()

    def get_total_count(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        station_ids: Optional[List[int]] = None
    ) -> int:
        """
        Get total detection count with optional filters.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            station_ids: Filter by station IDs

        Returns:
            Total number of detections
        """
        query = self.db.query(func.count(Detection.id))

        if start_date:
            query = query.filter(Detection.detection_date >= start_date)
        if end_date:
            query = query.filter(Detection.detection_date <= end_date)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        return query.scalar() or 0

    def get_date_range(self) -> tuple[Optional[date], Optional[date]]:
        """
        Get the date range of all detections.

        Returns:
            Tuple of (min_date, max_date) or (None, None) if no detections
        """
        result = self.db.query(
            func.min(Detection.detection_date),
            func.max(Detection.detection_date)
        ).first()

        return (result[0], result[1]) if result else (None, None)

    def calculate_nighttime_percentage(
        self,
        station_ids: Optional[List[int]] = None
    ) -> float:
        """
        Calculate percentage of detections that occurred at night.
        Night is defined as hour < 6 OR hour >= 20.

        Args:
            station_ids: Optional station IDs to filter

        Returns:
            Percentage of nighttime detections (0-100)
        """
        total_query = self.db.query(func.count(Detection.id)).filter(
            Detection.detection_hour.isnot(None)
        )

        night_query = self.db.query(func.count(Detection.id)).filter(
            Detection.detection_hour.isnot(None),
            or_(
                Detection.detection_hour < 6,
                Detection.detection_hour >= 20
            )
        )

        if station_ids:
            total_query = total_query.filter(Detection.station_id.in_(station_ids))
            night_query = night_query.filter(Detection.station_id.in_(station_ids))

        total = total_query.scalar() or 0
        night = night_query.scalar() or 0

        return (night / total * 100) if total > 0 else 0.0

    def get_detections_for_date(
        self,
        target_date: date,
        station_ids: Optional[List[int]] = None
    ) -> List[Detection]:
        """
        Get all detections for a specific date.

        Args:
            target_date: Date to query
            station_ids: Optional station IDs to filter

        Returns:
            List of Detection instances
        """
        query = self.db.query(Detection).filter(
            Detection.detection_date == target_date
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        return query.all()
