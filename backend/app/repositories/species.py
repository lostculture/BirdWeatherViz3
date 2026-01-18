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

    def get_species_by_family(
        self,
        family_name: str,
        station_ids: Optional[List[int]] = None
    ) -> List[Species]:
        """
        Get all species belonging to a specific family.

        Args:
            family_name: Name of the bird family
            station_ids: Optional filter by stations

        Returns:
            List of Species instances
        """
        query = self.db.query(Species).filter(Species.family == family_name)

        # Filter by stations (species detected at these stations)
        if station_ids:
            query = query.join(Detection).filter(
                Detection.station_id.in_(station_ids)
            ).distinct()

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
        Get species whose FIRST EVER detection was this week.

        Only returns truly new species discovered since Monday of current week,
        not all species that happened to be detected this week.

        Args:
            station_ids: Filter by station IDs

        Returns:
            List of dicts with species info, first detection date, and detection count
        """
        # Calculate Monday of this week
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        # Subquery to get the first detection date for each species (ever)
        first_detection_subq = (
            self.db.query(
                Detection.species_id,
                func.min(Detection.detection_date).label('first_ever_date')
            )
        )
        if station_ids:
            first_detection_subq = first_detection_subq.filter(Detection.station_id.in_(station_ids))
        first_detection_subq = first_detection_subq.group_by(Detection.species_id).subquery()

        # Main query: only species whose first_ever_date is this week
        query = (
            self.db.query(
                Species.species_id,
                Species.common_name,
                Species.scientific_name,
                Species.ebird_code,
                first_detection_subq.c.first_ever_date.label('first_detection_date'),
                func.count(Detection.id).label('detection_count')
            )
            .join(Detection, Species.id == Detection.species_id)
            .join(first_detection_subq, Detection.species_id == first_detection_subq.c.species_id)
            .filter(first_detection_subq.c.first_ever_date >= monday)
            .filter(Detection.detection_date >= monday)  # Count only this week's detections
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        query = query.group_by(
            Species.species_id,
            Species.common_name,
            Species.scientific_name,
            Species.ebird_code,
            first_detection_subq.c.first_ever_date
        ).order_by(first_detection_subq.c.first_ever_date)

        results = query.all()

        return [
            {
                'species_id': row.species_id,
                'common_name': row.common_name,
                'scientific_name': row.scientific_name,
                'ebird_code': row.ebird_code,
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

    def update_all_cached_stats(self) -> int:
        """
        Update cached statistics for all species.

        Returns:
            Number of species updated
        """
        # Get all species with their computed stats in one query
        stats_query = (
            self.db.query(
                Detection.species_id,
                func.count(Detection.id).label('total'),
                func.min(Detection.timestamp).label('first'),
                func.max(Detection.timestamp).label('last')
            )
            .group_by(Detection.species_id)
        )

        stats_dict = {
            row.species_id: {
                'total': row.total,
                'first': row.first,
                'last': row.last
            }
            for row in stats_query.all()
        }

        # Update all species
        species_list = self.get_all()
        for species in species_list:
            stats = stats_dict.get(species.id, {'total': 0, 'first': None, 'last': None})
            species.total_detections = stats['total']
            species.first_seen = stats['first']
            species.last_seen = stats['last']

        self.db.commit()
        return len(species_list)

    def get_hourly_pattern(self, species_id: int) -> List[dict]:
        """
        Get hourly detection pattern for a species.

        Args:
            species_id: Database species ID

        Returns:
            List of dicts with hour (0-23) and detection_count
        """
        from sqlalchemy import extract

        query = (
            self.db.query(
                extract('hour', Detection.timestamp).label('hour'),
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.species_id == species_id)
            .group_by(extract('hour', Detection.timestamp))
            .order_by(extract('hour', Detection.timestamp))
        )

        results = query.all()

        # Fill in all 24 hours
        hour_counts = {int(row.hour): row.detection_count for row in results}
        return [
            {'hour': h, 'detection_count': hour_counts.get(h, 0)}
            for h in range(24)
        ]

    def get_monthly_pattern(self, species_id: int) -> List[dict]:
        """
        Get monthly detection pattern for a species.

        Args:
            species_id: Database species ID

        Returns:
            List of dicts with month (1-12), month_name, and detection_count
        """
        from sqlalchemy import extract

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        query = (
            self.db.query(
                extract('month', Detection.timestamp).label('month'),
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.species_id == species_id)
            .group_by(extract('month', Detection.timestamp))
            .order_by(extract('month', Detection.timestamp))
        )

        results = query.all()

        # Fill in all 12 months
        month_counts = {int(row.month): row.detection_count for row in results}
        return [
            {
                'month': m,
                'month_name': month_names[m - 1],
                'detection_count': month_counts.get(m, 0)
            }
            for m in range(1, 13)
        ]

    def get_detection_timeline(
        self,
        species_id: int,
        months: Optional[int] = None
    ) -> List[dict]:
        """
        Get detection timeline by station for a species.

        Args:
            species_id: Database species ID
            months: Limit to last N months (optional)

        Returns:
            List of dicts with date, station_name, detection_count
        """
        from app.db.models.station import Station

        query = (
            self.db.query(
                Detection.detection_date,
                Station.name.label('station_name'),
                func.count(Detection.id).label('detection_count')
            )
            .join(Station, Detection.station_id == Station.id)
            .filter(Detection.species_id == species_id)
        )

        if months:
            cutoff = date.today() - timedelta(days=months * 30)
            query = query.filter(Detection.detection_date >= cutoff)

        query = query.group_by(
            Detection.detection_date,
            Station.name
        ).order_by(Detection.detection_date)

        results = query.all()

        return [
            {
                'date': row.detection_date.isoformat() if hasattr(row.detection_date, 'isoformat') else str(row.detection_date),
                'station_name': row.station_name,
                'detection_count': row.detection_count
            }
            for row in results
        ]

    def get_station_distribution(self, species_id: int) -> List[dict]:
        """
        Get detection distribution across stations for a species.

        Args:
            species_id: Database species ID

        Returns:
            List of dicts with station_name, detection_count, percentage
        """
        from app.db.models.station import Station

        query = (
            self.db.query(
                Station.name.label('station_name'),
                func.count(Detection.id).label('detection_count')
            )
            .join(Station, Detection.station_id == Station.id)
            .filter(Detection.species_id == species_id)
            .group_by(Station.name)
            .order_by(func.count(Detection.id).desc())
        )

        results = query.all()

        # Calculate percentages
        total = sum(row.detection_count for row in results)
        return [
            {
                'station_name': row.station_name,
                'detection_count': row.detection_count,
                'percentage': round(row.detection_count / total * 100, 2) if total > 0 else 0
            }
            for row in results
        ]

    def get_confidence_by_station(self, species_id: int) -> List[dict]:
        """
        Get average confidence by station for a species.

        Args:
            species_id: Database species ID

        Returns:
            List of dicts with station_name, avg_confidence, detection_count
        """
        from app.db.models.station import Station

        query = (
            self.db.query(
                Station.name.label('station_name'),
                func.avg(Detection.confidence).label('avg_confidence'),
                func.count(Detection.id).label('detection_count')
            )
            .join(Station, Detection.station_id == Station.id)
            .filter(Detection.species_id == species_id)
            .group_by(Station.name)
            .order_by(func.avg(Detection.confidence).desc())
        )

        results = query.all()

        return [
            {
                'station_name': row.station_name,
                'avg_confidence': round(float(row.avg_confidence), 3) if row.avg_confidence else 0,
                'detection_count': row.detection_count
            }
            for row in results
        ]
