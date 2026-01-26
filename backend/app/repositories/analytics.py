"""
Analytics Repository
Data access methods for advanced analytics queries.

Version: 1.0.0
"""

from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy import func, and_, case, extract
from sqlalchemy.orm import Session

from app.db.models.detection import Detection
from app.db.models.species import Species
from app.db.models.station import Station


class AnalyticsRepository:
    """Repository for advanced analytics data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_species_hour_bubble_data(
        self,
        limit: int = 50,
        months: int = 3,
        station_ids: Optional[List[int]] = None,
        min_confidence: float = 0.7
    ) -> List[dict]:
        """
        Get species activity by hour for bubble chart.

        Returns top N species with their hourly detection counts.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # First, get top species by total detections
        top_species_query = (
            self.db.query(
                Species.id,
                Species.common_name,
                Species.scientific_name,
                func.count(Detection.id).label('total_detections')
            )
            .join(Detection, Detection.species_id == Species.id)
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            top_species_query = top_species_query.filter(
                Detection.station_id.in_(station_ids)
            )

        top_species = (
            top_species_query
            .group_by(Species.id, Species.common_name, Species.scientific_name)
            .order_by(func.count(Detection.id).desc())
            .limit(limit)
            .all()
        )

        species_ids = [s.id for s in top_species]
        species_totals = {s.id: s.total_detections for s in top_species}
        species_info = {s.id: (s.common_name, s.scientific_name) for s in top_species}

        if not species_ids:
            return []

        # Get hourly breakdown for these species
        hourly_query = (
            self.db.query(
                Detection.species_id,
                extract('hour', Detection.timestamp).label('hour'),
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.species_id.in_(species_ids))
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            hourly_query = hourly_query.filter(
                Detection.station_id.in_(station_ids)
            )

        hourly_data = (
            hourly_query
            .group_by(Detection.species_id, extract('hour', Detection.timestamp))
            .all()
        )

        results = []
        for row in hourly_data:
            common_name, scientific_name = species_info[row.species_id]
            results.append({
                'species_id': row.species_id,
                'common_name': common_name,
                'scientific_name': scientific_name,
                'hour': int(row.hour),
                'detection_count': row.detection_count,
                'total_detections': species_totals[row.species_id]
            })

        return results

    def get_phenology_data(
        self,
        year: Optional[int] = None,
        station_ids: Optional[List[int]] = None,
        min_confidence: float = 0.7,
        limit: int = 50
    ) -> List[dict]:
        """
        Get phenology data for heatmap (species x week).

        Returns detection counts by species and week number.
        """
        if year is None:
            year = date.today().year

        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # Get top species first
        top_species_query = (
            self.db.query(
                Species.id,
                Species.common_name,
                func.count(Detection.id).label('total')
            )
            .join(Detection, Detection.species_id == Species.id)
            .filter(Detection.detection_date >= start_date)
            .filter(Detection.detection_date <= end_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            top_species_query = top_species_query.filter(
                Detection.station_id.in_(station_ids)
            )

        top_species = (
            top_species_query
            .group_by(Species.id, Species.common_name)
            .order_by(func.count(Detection.id).desc())
            .limit(limit)
            .all()
        )

        species_ids = [s.id for s in top_species]
        species_names = {s.id: s.common_name for s in top_species}

        if not species_ids:
            return []

        # Get weekly data - use strftime for SQLite compatibility
        weekly_query = (
            self.db.query(
                Detection.species_id,
                func.strftime('%W', Detection.detection_date).label('week'),
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.species_id.in_(species_ids))
            .filter(Detection.detection_date >= start_date)
            .filter(Detection.detection_date <= end_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            weekly_query = weekly_query.filter(
                Detection.station_id.in_(station_ids)
            )

        weekly_data = (
            weekly_query
            .group_by(
                Detection.species_id,
                func.strftime('%W', Detection.detection_date)
            )
            .all()
        )

        results = []
        for row in weekly_data:
            results.append({
                'species_id': row.species_id,
                'common_name': species_names[row.species_id],
                'week_number': int(row.week) + 1,  # Convert 0-indexed to 1-indexed
                'year': year,
                'detection_count': row.detection_count
            })

        return results

    def get_confidence_scatter_data(
        self,
        station_ids: Optional[List[int]] = None,
        min_detections: int = 10
    ) -> List[dict]:
        """
        Get detection count vs confidence data for scatter plot.

        Returns one point per species with total detections and avg confidence.
        """
        query = (
            self.db.query(
                Species.id,
                Species.common_name,
                Species.scientific_name,
                func.count(Detection.id).label('total_detections'),
                func.avg(Detection.confidence).label('avg_confidence'),
                func.count(func.distinct(Detection.detection_date)).label('detection_days')
            )
            .join(Detection, Detection.species_id == Species.id)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        results = (
            query
            .group_by(Species.id, Species.common_name, Species.scientific_name)
            .having(func.count(Detection.id) >= min_detections)
            .order_by(func.count(Detection.id).desc())
            .all()
        )

        return [
            {
                'species_id': row.id,
                'common_name': row.common_name,
                'scientific_name': row.scientific_name,
                'total_detections': row.total_detections,
                'avg_confidence': round(float(row.avg_confidence), 3),
                'detection_days': row.detection_days
            }
            for row in results
        ]

    def get_confidence_by_hour(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6
    ) -> List[dict]:
        """
        Get confidence distribution by hour for heatmap.

        Returns counts binned by hour and confidence range.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Define confidence bins
        bins = [
            (0.5, 0.6, "0.50-0.60"),
            (0.6, 0.7, "0.60-0.70"),
            (0.7, 0.8, "0.70-0.80"),
            (0.8, 0.9, "0.80-0.90"),
            (0.9, 1.0, "0.90-1.00"),
        ]

        results = []

        for conf_min, conf_max, bin_label in bins:
            query = (
                self.db.query(
                    extract('hour', Detection.timestamp).label('hour'),
                    func.count(Detection.id).label('detection_count')
                )
                .filter(Detection.detection_date >= cutoff_date)
                .filter(Detection.confidence >= conf_min)
                .filter(Detection.confidence < conf_max if conf_max < 1.0 else Detection.confidence <= conf_max)
            )

            if station_ids:
                query = query.filter(Detection.station_id.in_(station_ids))

            hourly_data = (
                query
                .group_by(extract('hour', Detection.timestamp))
                .all()
            )

            for row in hourly_data:
                results.append({
                    'hour': int(row.hour),
                    'confidence_bin': bin_label,
                    'confidence_min': conf_min,
                    'confidence_max': conf_max,
                    'detection_count': row.detection_count
                })

        return results

    def get_temporal_distribution(
        self,
        species_ids: Optional[List[int]] = None,
        months: int = 6,
        station_ids: Optional[List[int]] = None,
        min_confidence: float = 0.7,
        limit: int = 20
    ) -> List[dict]:
        """
        Get temporal distribution data for density/KDE visualization.

        Returns daily detection counts per species over time.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # If no species specified, get top species
        if not species_ids:
            top_species_query = (
                self.db.query(Species.id)
                .join(Detection, Detection.species_id == Species.id)
                .filter(Detection.detection_date >= cutoff_date)
                .filter(Detection.confidence >= min_confidence)
            )

            if station_ids:
                top_species_query = top_species_query.filter(
                    Detection.station_id.in_(station_ids)
                )

            top_species = (
                top_species_query
                .group_by(Species.id)
                .order_by(func.count(Detection.id).desc())
                .limit(limit)
                .all()
            )
            species_ids = [s.id for s in top_species]

        if not species_ids:
            return []

        # Get species names
        species_info = {
            s.id: s.common_name
            for s in self.db.query(Species).filter(Species.id.in_(species_ids)).all()
        }

        # Get daily data
        query = (
            self.db.query(
                Detection.species_id,
                Detection.detection_date,
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.species_id.in_(species_ids))
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        daily_data = (
            query
            .group_by(Detection.species_id, Detection.detection_date)
            .order_by(Detection.detection_date)
            .all()
        )

        return [
            {
                'species_id': row.species_id,
                'common_name': species_info.get(row.species_id, 'Unknown'),
                'date': row.detection_date,
                'detection_count': row.detection_count
            }
            for row in daily_data
        ]
