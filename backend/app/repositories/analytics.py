"""
Analytics Repository
Data access methods for advanced analytics queries.

Version: 1.0.0
"""

from typing import List, Optional
from datetime import date, datetime, timedelta, time
from sqlalchemy import func, and_, case, extract
from sqlalchemy.orm import Session
from collections import defaultdict

from app.db.models.detection import Detection
from app.db.models.species import Species
from app.db.models.station import Station
from app.db.models.weather import Weather


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
        year=0 means rolling 12 months from today.
        """
        today = date.today()
        if year is None or year == 0:
            # Rolling 12 months
            end_date = today
            start_date = date(today.year - 1, today.month, today.day)
        else:
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
        Optimized: Uses CASE statement to bin all data in a single query.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Use CASE to bin confidence in a single query
        confidence_bin = case(
            (and_(Detection.confidence >= 0.5, Detection.confidence < 0.6), '0.50-0.60'),
            (and_(Detection.confidence >= 0.6, Detection.confidence < 0.7), '0.60-0.70'),
            (and_(Detection.confidence >= 0.7, Detection.confidence < 0.8), '0.70-0.80'),
            (and_(Detection.confidence >= 0.8, Detection.confidence < 0.9), '0.80-0.90'),
            (Detection.confidence >= 0.9, '0.90-1.00'),
            else_=None
        ).label('confidence_bin')

        query = (
            self.db.query(
                extract('hour', Detection.timestamp).label('hour'),
                confidence_bin,
                func.count(Detection.id).label('detection_count')
            )
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= 0.5)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        hourly_data = (
            query
            .group_by(extract('hour', Detection.timestamp), confidence_bin)
            .all()
        )

        # Map bin labels to min/max values
        bin_ranges = {
            '0.50-0.60': (0.5, 0.6),
            '0.60-0.70': (0.6, 0.7),
            '0.70-0.80': (0.7, 0.8),
            '0.80-0.90': (0.8, 0.9),
            '0.90-1.00': (0.9, 1.0),
        }

        results = []
        for row in hourly_data:
            if row.confidence_bin and row.confidence_bin in bin_ranges:
                conf_min, conf_max = bin_ranges[row.confidence_bin]
                results.append({
                    'hour': int(row.hour),
                    'confidence_bin': row.confidence_bin,
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

    def get_dawn_chorus_data(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        window_minutes: int = 120  # 2 hours before and after sunrise
    ) -> List[dict]:
        """
        Get detection activity relative to sunrise time.

        Returns aggregated counts by minutes from sunrise.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Get detections with weather data (for sunrise times)
        query = (
            self.db.query(
                Detection.timestamp,
                Detection.detection_date,
                Detection.station_id,
                Detection.species_id,
                Weather.sunrise
            )
            .join(Weather, and_(
                Weather.station_id == Detection.station_id,
                Weather.weather_date == Detection.detection_date
            ))
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
            .filter(Weather.sunrise.isnot(None))
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        detections = query.all()

        # Calculate minutes from sunrise for each detection
        dawn_counts = defaultdict(lambda: {'detection_count': 0, 'species': set()})

        for detection in detections:
            if detection.sunrise is None or detection.timestamp is None:
                continue

            detection_time = detection.timestamp.time()
            sunrise_time = detection.sunrise

            # Convert times to minutes from midnight for calculation
            det_minutes = detection_time.hour * 60 + detection_time.minute
            sunrise_minutes = sunrise_time.hour * 60 + sunrise_time.minute

            minutes_from_sunrise = det_minutes - sunrise_minutes

            # Only include detections within the window
            if -window_minutes <= minutes_from_sunrise <= window_minutes:
                # Round to 5-minute bins
                bin_minutes = (minutes_from_sunrise // 5) * 5
                dawn_counts[bin_minutes]['detection_count'] += 1
                dawn_counts[bin_minutes]['species'].add(detection.species_id)

        results = []
        for minutes, data in sorted(dawn_counts.items()):
            results.append({
                'minutes_from_sunrise': minutes,
                'detection_count': data['detection_count'],
                'species_count': len(data['species'])
            })

        return results

    def get_weather_impact_data(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        analysis_type: str = 'temperature'  # 'temperature', 'condition', 'precipitation'
    ) -> List[dict]:
        """
        Get detection counts grouped by weather conditions.

        Returns aggregated detection data by weather bins.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Base query for detections with weather
        query = (
            self.db.query(
                Weather.weather_date,
                Weather.temp_avg,
                Weather.weather_description,
                Weather.precipitation,
                func.count(Detection.id).label('detection_count')
            )
            .join(Detection, and_(
                Weather.station_id == Detection.station_id,
                Weather.weather_date == Detection.detection_date
            ))
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        results = []

        if analysis_type == 'temperature':
            # Optimized: Use CASE statement to bin all temperature data in single query
            temp_bin = case(
                (Weather.temp_avg < 0, '< 0°F'),
                (and_(Weather.temp_avg >= 0, Weather.temp_avg < 20), '0-20°F'),
                (and_(Weather.temp_avg >= 20, Weather.temp_avg < 32), '20-32°F'),
                (and_(Weather.temp_avg >= 32, Weather.temp_avg < 50), '32-50°F'),
                (and_(Weather.temp_avg >= 50, Weather.temp_avg < 60), '50-60°F'),
                (and_(Weather.temp_avg >= 60, Weather.temp_avg < 70), '60-70°F'),
                (and_(Weather.temp_avg >= 70, Weather.temp_avg < 80), '70-80°F'),
                (and_(Weather.temp_avg >= 80, Weather.temp_avg < 90), '80-90°F'),
                (Weather.temp_avg >= 90, '> 90°F'),
                else_=None
            ).label('temp_bin')

            daily_query = (
                self.db.query(
                    temp_bin,
                    Weather.weather_date,
                    func.count(Detection.id).label('detection_count')
                )
                .join(Detection, and_(
                    Weather.station_id == Detection.station_id,
                    Weather.weather_date == Detection.detection_date
                ))
                .filter(Detection.detection_date >= cutoff_date)
                .filter(Detection.confidence >= min_confidence)
                .filter(Weather.temp_avg.isnot(None))
            )

            if station_ids:
                daily_query = daily_query.filter(Detection.station_id.in_(station_ids))

            daily_data = (
                daily_query
                .group_by(temp_bin, Weather.weather_date)
                .all()
            )

            # Aggregate by temperature bin
            bin_stats = {}
            for row in daily_data:
                if row.temp_bin is None:
                    continue
                if row.temp_bin not in bin_stats:
                    bin_stats[row.temp_bin] = {'total': 0, 'days': 0}
                bin_stats[row.temp_bin]['total'] += row.detection_count
                bin_stats[row.temp_bin]['days'] += 1

            # Output in consistent order
            bin_order = ['< 0°F', '0-20°F', '20-32°F', '32-50°F', '50-60°F', '60-70°F', '70-80°F', '80-90°F', '> 90°F']
            for label in bin_order:
                if label in bin_stats:
                    stats = bin_stats[label]
                    results.append({
                        'temperature_bin': label,
                        'condition': None,
                        'avg_detections': round(stats['total'] / stats['days'], 1),
                        'total_detections': stats['total'],
                        'observation_count': stats['days']
                    })

        elif analysis_type == 'condition':
            # Group by weather condition
            daily_data = (
                query
                .group_by(Weather.weather_date, Weather.weather_description)
                .all()
            )

            condition_stats = defaultdict(lambda: {'total': 0, 'days': 0})
            for row in daily_data:
                condition = row.weather_description or 'Unknown'
                # Simplify condition descriptions
                if 'rain' in condition.lower() or 'shower' in condition.lower():
                    condition = 'Rainy'
                elif 'cloud' in condition.lower() or 'overcast' in condition.lower():
                    condition = 'Cloudy'
                elif 'sun' in condition.lower() or 'clear' in condition.lower():
                    condition = 'Clear/Sunny'
                elif 'snow' in condition.lower():
                    condition = 'Snow'
                elif 'fog' in condition.lower() or 'mist' in condition.lower():
                    condition = 'Fog/Mist'
                else:
                    condition = 'Other'

                condition_stats[condition]['total'] += row.detection_count
                condition_stats[condition]['days'] += 1

            for condition, stats in condition_stats.items():
                results.append({
                    'temperature_bin': None,
                    'condition': condition,
                    'avg_detections': round(stats['total'] / stats['days'], 1),
                    'total_detections': stats['total'],
                    'observation_count': stats['days']
                })

        elif analysis_type == 'precipitation':
            # Group by precipitation presence including snow
            # First get all daily data
            daily_data = (
                query
                .group_by(Weather.weather_date, Weather.weather_description, Weather.precipitation)
                .all()
            )

            # Categorize each day
            categories = {
                'No Precip': {'total': 0, 'days': 0},
                'Light Rain': {'total': 0, 'days': 0},
                'Moderate Rain': {'total': 0, 'days': 0},
                'Heavy Rain': {'total': 0, 'days': 0},
                'Snow': {'total': 0, 'days': 0},
            }

            for row in daily_data:
                desc = (row.weather_description or '').lower()
                precip = row.precipitation or 0

                # Check for snow first (based on description)
                if 'snow' in desc or 'sleet' in desc or 'ice' in desc:
                    category = 'Snow'
                elif precip < 0.01:
                    category = 'No Precip'
                elif precip < 0.1:
                    category = 'Light Rain'
                elif precip < 0.5:
                    category = 'Moderate Rain'
                else:
                    category = 'Heavy Rain'

                categories[category]['total'] += row.detection_count
                categories[category]['days'] += 1

            # Build results in order
            for label in ['No Precip', 'Light Rain', 'Moderate Rain', 'Heavy Rain', 'Snow']:
                stats = categories[label]
                if stats['days'] > 0:
                    results.append({
                        'temperature_bin': label,
                        'condition': None,
                        'avg_detections': round(stats['total'] / stats['days'], 1),
                        'total_detections': stats['total'],
                        'observation_count': stats['days']
                    })

        return results

    def get_weekly_trends(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 12,
        min_confidence: float = 0.7
    ) -> List[dict]:
        """
        Get weekly detection trends over time.

        Returns aggregated weekly stats including total detections and unique species.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        query = (
            self.db.query(
                func.strftime('%Y', Detection.detection_date).label('year'),
                func.strftime('%W', Detection.detection_date).label('week'),
                func.min(Detection.detection_date).label('week_start'),
                func.count(Detection.id).label('total_detections'),
                func.count(func.distinct(Detection.species_id)).label('unique_species'),
                func.count(func.distinct(Detection.detection_date)).label('days_with_data')
            )
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        weekly_data = (
            query
            .group_by(
                func.strftime('%Y', Detection.detection_date),
                func.strftime('%W', Detection.detection_date)
            )
            .order_by(
                func.strftime('%Y', Detection.detection_date),
                func.strftime('%W', Detection.detection_date)
            )
            .all()
        )

        results = []
        for row in weekly_data:
            avg_daily = row.total_detections / max(row.days_with_data, 1)
            results.append({
                'week_start': row.week_start,
                'year': int(row.year),
                'week_number': int(row.week) + 1,
                'total_detections': row.total_detections,
                'unique_species': row.unique_species,
                'avg_daily_detections': round(avg_daily, 1)
            })

        return results

    def get_co_occurrence_matrix(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        limit: int = 20
    ) -> List[dict]:
        """
        Get species co-occurrence data for matrix visualization.

        Returns Jaccard similarity index for species pairs based on
        days they were both detected.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Get top species
        top_species_query = (
            self.db.query(
                Species.id,
                Species.common_name,
                func.count(func.distinct(Detection.detection_date)).label('total_days')
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
            .group_by(Species.id, Species.common_name)
            .order_by(func.count(func.distinct(Detection.detection_date)).desc())
            .limit(limit)
            .all()
        )

        species_info = {s.id: (s.common_name, s.total_days) for s in top_species}
        species_ids = list(species_info.keys())

        if len(species_ids) < 2:
            return []

        # Get all detection dates for all species in a single query (optimized)
        dates_query = (
            self.db.query(
                Detection.species_id,
                Detection.detection_date
            )
            .filter(Detection.species_id.in_(species_ids))
            .filter(Detection.detection_date >= cutoff_date)
            .filter(Detection.confidence >= min_confidence)
            .distinct()
        )

        if station_ids:
            dates_query = dates_query.filter(Detection.station_id.in_(station_ids))

        all_dates = dates_query.all()

        # Group dates by species
        species_dates = {sid: set() for sid in species_ids}
        for row in all_dates:
            species_dates[row.species_id].add(row.detection_date)

        # Calculate co-occurrence matrix
        results = []
        for i, sp1_id in enumerate(species_ids):
            for sp2_id in species_ids[i:]:  # Include diagonal for total days
                sp1_name, sp1_total = species_info[sp1_id]
                sp2_name, sp2_total = species_info[sp2_id]

                sp1_dates = species_dates[sp1_id]
                sp2_dates = species_dates[sp2_id]

                intersection = len(sp1_dates & sp2_dates)
                union = len(sp1_dates | sp2_dates)

                jaccard = intersection / union if union > 0 else 0

                results.append({
                    'species_1': sp1_name,
                    'species_2': sp2_name,
                    'co_occurrence_days': intersection,
                    'species_1_total_days': sp1_total,
                    'species_2_total_days': sp2_total,
                    'jaccard_index': round(jaccard, 3)
                })

                # Add reverse entry if not diagonal
                if sp1_id != sp2_id:
                    results.append({
                        'species_1': sp2_name,
                        'species_2': sp1_name,
                        'co_occurrence_days': intersection,
                        'species_1_total_days': sp2_total,
                        'species_2_total_days': sp1_total,
                        'jaccard_index': round(jaccard, 3)
                    })

        return results

    def get_species_seasonality(
        self,
        station_ids: Optional[List[int]] = None,
        min_confidence: float = 0.7,
        limit: int = 50
    ) -> List[dict]:
        """
        Get first/last sighting and peak month for each species.

        Returns seasonality data for timeline visualization.
        """
        query = (
            self.db.query(
                Species.id,
                Species.common_name,
                func.min(Detection.detection_date).label('first_seen'),
                func.max(Detection.detection_date).label('last_seen'),
                func.count(Detection.id).label('total_detections'),
                func.count(func.distinct(Detection.detection_date)).label('active_days')
            )
            .join(Detection, Detection.species_id == Species.id)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        base_results = (
            query
            .group_by(Species.id, Species.common_name)
            .order_by(func.count(Detection.id).desc())
            .limit(limit)
            .all()
        )

        species_ids = [r.id for r in base_results]
        species_data = {r.id: r for r in base_results}

        # Get peak month for all species in a single query (optimized)
        # Using subquery to find max count per species, then join to get month
        monthly_query = (
            self.db.query(
                Detection.species_id,
                func.strftime('%m', Detection.detection_date).label('month'),
                func.count(Detection.id).label('count')
            )
            .filter(Detection.species_id.in_(species_ids))
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            monthly_query = monthly_query.filter(Detection.station_id.in_(station_ids))

        monthly_counts = (
            monthly_query
            .group_by(Detection.species_id, func.strftime('%m', Detection.detection_date))
            .all()
        )

        # Find peak month for each species from the results
        species_month_counts = {}
        for row in monthly_counts:
            sid = row.species_id
            if sid not in species_month_counts or row.count > species_month_counts[sid][1]:
                species_month_counts[sid] = (int(row.month), row.count)

        peak_months = {sid: data[0] for sid, data in species_month_counts.items()}
        # Default to 1 for any species not found
        for sid in species_ids:
            if sid not in peak_months:
                peak_months[sid] = 1

        month_names = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]

        results = []
        for species_id in species_ids:
            data = species_data[species_id]
            peak_month = peak_months.get(species_id, 1)
            results.append({
                'species_id': data.id,
                'common_name': data.common_name,
                'first_seen': data.first_seen,
                'last_seen': data.last_seen,
                'peak_month': peak_month,
                'peak_month_name': month_names[peak_month],
                'total_detections': data.total_detections,
                'active_days': data.active_days
            })

        return results

    def get_monthly_champions(
        self,
        station_ids: Optional[List[int]] = None,
        year: Optional[int] = None,
        min_confidence: float = 0.7
    ) -> List[dict]:
        """
        Get the top species for each month over the rolling 12 months.

        Returns the most detected species per month with their counts.
        Optimized: Uses single query to get all monthly data, then processes in Python.
        """
        month_names = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]

        today = date.today()

        # Calculate date range for rolling 12 months
        start_date = date(today.year - 1, today.month, 1)

        # Single query to get all species counts by year-month (optimized)
        query = (
            self.db.query(
                func.strftime('%Y', Detection.detection_date).label('year'),
                func.strftime('%m', Detection.detection_date).label('month'),
                Species.id.label('species_id'),
                Species.common_name,
                func.count(Detection.id).label('detection_count')
            )
            .join(Species, Detection.species_id == Species.id)
            .filter(Detection.detection_date >= start_date)
            .filter(Detection.detection_date <= today)
            .filter(Detection.confidence >= min_confidence)
        )

        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        monthly_data = (
            query
            .group_by(
                func.strftime('%Y', Detection.detection_date),
                func.strftime('%m', Detection.detection_date),
                Species.id,
                Species.common_name
            )
            .all()
        )

        # Process results to find champion and total for each month
        month_stats = {}  # (year, month) -> {'species': {...}, 'total': int}

        for row in monthly_data:
            key = (int(row.year), int(row.month))
            if key not in month_stats:
                month_stats[key] = {'species': {}, 'total': 0}

            month_stats[key]['species'][row.species_id] = {
                'common_name': row.common_name,
                'count': row.detection_count
            }
            month_stats[key]['total'] += row.detection_count

        # Build results sorted by date
        results = []
        for (year, month), stats in sorted(month_stats.items()):
            if stats['total'] == 0:
                continue

            # Find top species for this month
            top_species_id = max(stats['species'].keys(), key=lambda sid: stats['species'][sid]['count'])
            top_species = stats['species'][top_species_id]

            percentage = (top_species['count'] / stats['total']) * 100
            month_label = f"{month_names[month]} {year}"

            results.append({
                'month': month,
                'month_name': month_label,
                'year': year,
                'species_id': top_species_id,
                'common_name': top_species['common_name'],
                'detection_count': top_species['count'],
                'percentage_of_month': round(percentage, 1)
            })

        return results
