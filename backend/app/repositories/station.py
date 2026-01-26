"""
Station Repository
Data access methods for station queries.

Version: 1.0.0
"""

from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.station import Station
from app.db.models.detection import Detection
from app.repositories.base import BaseRepository


class StationRepository(BaseRepository[Station]):
    """Repository for station data access."""

    def __init__(self, db: Session):
        super().__init__(Station, db)

    def get_by_birdweather_id(self, station_id: int) -> Optional[Station]:
        """Get station by BirdWeather station ID."""
        return self.db.query(Station).filter(
            Station.station_id == station_id
        ).first()

    def get_active_stations(self) -> List[Station]:
        """Get all active stations (included in analysis)."""
        return self.db.query(Station).filter(Station.active == True).all()

    def get_auto_update_stations(self) -> List[Station]:
        """Get all stations with auto-update enabled."""
        return self.db.query(Station).filter(
            Station.active == True,
            Station.auto_update == True
        ).all()

    def get_station_stats(
        self,
        station_id: int
    ) -> dict:
        """
        Get statistics for a specific station.

        Args:
            station_id: Database station ID

        Returns:
            Dict with station statistics
        """
        # Query detection stats
        stats = (
            self.db.query(
                func.count(Detection.id).label('total_detections'),
                func.count(func.distinct(Detection.species_id)).label('unique_species'),
                func.count(func.distinct(Detection.detection_date)).label('days_active'),
                func.avg(Detection.confidence).label('avg_confidence'),
                func.min(Detection.timestamp).label('first_detection'),
                func.max(Detection.timestamp).label('last_detection')
            )
            .filter(Detection.station_id == station_id)
            .first()
        )

        total = stats.total_detections or 0
        days = stats.days_active or 0
        return {
            'station_id': station_id,
            'total_detections': total,
            'unique_species': stats.unique_species or 0,
            'days_active': days,
            'avg_detections_per_day': round(total / days, 1) if days > 0 else 0.0,
            'avg_confidence': float(stats.avg_confidence) if stats.avg_confidence else 0.0,
            'first_detection': stats.first_detection,
            'last_detection': stats.last_detection
        }

    def get_all_station_stats(
        self,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get statistics for all stations.

        Args:
            station_ids: Optional list of station IDs to filter

        Returns:
            List of dicts with station statistics
        """
        query = (
            self.db.query(
                Station.id,
                Station.station_id,
                Station.name,
                func.count(Detection.id).label('total_detections'),
                func.count(func.distinct(Detection.species_id)).label('unique_species'),
                func.count(func.distinct(Detection.detection_date)).label('days_active'),
                func.avg(Detection.confidence).label('avg_confidence'),
                func.min(Detection.timestamp).label('first_detection'),
                func.max(Detection.timestamp).label('last_detection')
            )
            .outerjoin(Detection, Station.id == Detection.station_id)
        )

        if station_ids:
            query = query.filter(Station.id.in_(station_ids))

        query = query.group_by(Station.id, Station.station_id, Station.name)

        results = query.all()

        stats_list = []
        for row in results:
            total = row.total_detections or 0
            days = row.days_active or 0
            stats_list.append({
                'id': row.id,
                'station_id': row.station_id,
                'station_name': row.name,
                'total_detections': total,
                'unique_species': row.unique_species or 0,
                'days_active': days,
                'avg_detections_per_day': round(total / days, 1) if days > 0 else 0.0,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0,
                'first_detection': row.first_detection,
                'last_detection': row.last_detection
            })
        return stats_list
