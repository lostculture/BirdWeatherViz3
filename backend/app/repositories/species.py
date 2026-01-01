"""
Species Repository
Data access methods for species queries and analytics.

Version: 1.0.0
"""

from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, distinct
from sqlalchemy.orm import Session

from app.db.models.species import Species
from app.db.models.detection import Detection
from app.repositories.base import BaseRepository


class SpeciesRepository(BaseRepository[Species]):
    """Repository for species data access and analytics."""

    def __init__(self, db: Session):
        super().__init__(Species, db)

    def get_by_scientific_name(self, scientific_name: str) -> Optional[Species]:
        """Get species by scientific name."""
        return self.db.query(Species).filter(
            Species.scientific_name == scientific_name
        ).first()

    def get_by_birdweather_id(self, species_id: int) -> Optional[Species]:
        """Get species by BirdWeather species ID."""
        return self.db.query(Species).filter(
            Species.species_id == species_id
        ).first()

    def get_species_list(
        self,
        station_ids: Optional[List[int]] = None,
        search: Optional[str] = None
    ) -> List[Species]:
        """
        Get list of all species with optional filtering.

        Args:
            station_ids: Filter by stations
            search: Search in common or scientific name

        Returns:
            List of Species instances
        """
        query = self.db.query(Species)

        # Filter by stations (species detected at these stations)
        if station_ids:
            query = query.join(Detection).filter(
                Detection.station_id.in_(station_ids)
            ).distinct()

        # Search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Species.common_name.ilike(search_pattern)) |
                (Species.scientific_name.ilike(search_pattern))
            )

        return query.order_by(Species.common_name).all()

    def get_daily_unique_species(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get daily unique species counts (diversity trend).

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            station_ids: Filter by station IDs

        Returns:
            List of dicts with detection_date, unique_species_count
        """
        query = (
            self.db.query(
                Detection.detection_date,
                func.count(distinct(Detection.species_id)).label('unique_species_count')
            )
        )

        # Apply filters
        if start_date:
            query = query.filter(Detection.detection_date >= start_date)
        if end_date:
            query = query.filter(Detection.detection_date <= end_date)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        # Group and order
        query = query.group_by(Detection.detection_date).order_by(Detection.detection_date)

        results = query.all()

        return [
            {
                'detection_date': row.detection_date,
                'unique_species_count': row.unique_species_count
            }
            for row in results
        ]

    def get_discovery_curve(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get cumulative species discovery curve.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            station_ids: Filter by station IDs

        Returns:
            List of dicts with discovery_date, cumulative_species_count
        """
        # Get first detection date for each species
        subquery = (
            self.db.query(
                Detection.species_id,
                func.min(Detection.detection_date).label('first_seen')
            )
        )

        if station_ids:
            subquery = subquery.filter(Detection.station_id.in_(station_ids))

        subquery = subquery.group_by(Detection.species_id).subquery()

        # Count cumulative species by date
        query = (
            self.db.query(
                subquery.c.first_seen.label('discovery_date'),
                func.count(subquery.c.species_id).label('species_count')
            )
        )

        if start_date:
            query = query.filter(subquery.c.first_seen >= start_date)
        if end_date:
            query = query.filter(subquery.c.first_seen <= end_date)

        query = query.group_by(subquery.c.first_seen).order_by(subquery.c.first_seen)

        results = query.all()

        # Calculate cumulative count
        cumulative = []
        total = 0
        for row in results:
            total += row.species_count
            cumulative.append({
                'discovery_date': row.discovery_date,
                'cumulative_species_count': total
            })

        return cumulative

    def get_species_this_week(
        self,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get species detected since Monday of current week.

        Args:
            station_ids: Filter by station IDs

        Returns:
            List of dicts with species info, first detection date, and detection count
        """
        # Calculate Monday of this week
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        query = (
            self.db.query(
                Species.species_id,
                Species.common_name,
                Species.scientific_name,
                func.min(Detection.detection_date).label('first_detection_date'),
                func.count(Detection.id).label('detection_count')
            )
            .join(Detection, Species.id == Detection.species_id)
            .filter(Detection.detection_date >= monday)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        query = query.group_by(
            Species.species_id,
            Species.common_name,
            Species.scientific_name
        ).order_by(func.min(Detection.detection_date))

        results = query.all()

        return [
            {
                'species_id': row.species_id,
                'common_name': row.common_name,
                'scientific_name': row.scientific_name,
                'first_detection_date': row.first_detection_date,
                'detection_count': row.detection_count
            }
            for row in results
        ]

    def get_total_unique_species(
        self,
        station_ids: Optional[List[int]] = None
    ) -> int:
        """
        Get total number of unique species.

        Args:
            station_ids: Filter by station IDs

        Returns:
            Count of unique species
        """
        query = self.db.query(func.count(distinct(Detection.species_id)))

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        return query.scalar() or 0

    def get_family_totals(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get detection totals by bird family.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            station_ids: Filter by station IDs

        Returns:
            List of dicts with family, species_count, total_detections
        """
        query = (
            self.db.query(
                Species.family,
                func.count(distinct(Species.id)).label('species_count'),
                func.count(Detection.id).label('total_detections')
            )
            .join(Detection, Species.id == Detection.species_id)
            .filter(Species.family.isnot(None))
        )

        # Apply filters
        if start_date:
            query = query.filter(Detection.detection_date >= start_date)
        if end_date:
            query = query.filter(Detection.detection_date <= end_date)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        # Group and order
        query = query.group_by(Species.family).order_by(
            func.count(Detection.id).desc()
        )

        results = query.all()

        return [
            {
                'family': row.family,
                'species_count': row.species_count,
                'total_detections': row.total_detections
            }
            for row in results
        ]

    def get_species_avg_confidence(
        self,
        station_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Get average confidence score per species.

        Args:
            station_ids: Filter by station IDs

        Returns:
            List of dicts with species_common_name, detection_count, avg_confidence
        """
        query = (
            self.db.query(
                Species.common_name.label('species_common_name'),
                func.count(Detection.id).label('detection_count'),
                func.avg(Detection.confidence).label('avg_confidence')
            )
            .join(Detection, Species.id == Detection.species_id)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        query = query.group_by(Species.common_name).order_by(
            func.count(Detection.id).desc()
        )

        results = query.all()

        return [
            {
                'species_common_name': row.species_common_name,
                'detection_count': row.detection_count,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else 0.0
            }
            for row in results
        ]

    def update_cached_stats(self, species_id: int) -> None:
        """
        Update cached statistics for a species.

        Args:
            species_id: Database species ID
        """
        species = self.get_by_id(species_id)
        if not species:
            return

        # Calculate stats from detections
        stats = (
            self.db.query(
                func.count(Detection.id).label('total'),
                func.min(Detection.timestamp).label('first'),
                func.max(Detection.timestamp).label('last')
            )
            .filter(Detection.species_id == species_id)
            .first()
        )

        # Update species
        species.total_detections = stats.total or 0
        species.first_seen = stats.first
        species.last_seen = stats.last

        self.db.commit()
