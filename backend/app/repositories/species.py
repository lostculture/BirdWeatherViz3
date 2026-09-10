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
from app.db.models.station import Station
from app.db.models.rollup import DetectionRollup
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
        search: Optional[str] = None,
        detected_only: bool = True
    ) -> List[Species]:
        """
        Get list of detected species with optional filtering.

        Args:
            station_ids: Filter by stations
            search: Search in common or scientific name
            detected_only: Only return species with at least one detection (default True)

        Returns:
            List of Species instances that have actual detections
        """
        # Always join with detections to only return species that have been detected
        query = self.db.query(Species).join(Detection).distinct()

        # Filter by stations (species detected at these stations)
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

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
        Get all detected species belonging to a specific family.

        Args:
            family_name: Name of the bird family
            station_ids: Optional filter by stations

        Returns:
            List of Species instances that have been detected
        """
        # Always join with Detection to only return species that have been detected
        query = (
            self.db.query(Species)
            .join(Detection)
            .filter(Species.family == family_name)
        )

        # Filter by stations if provided
        if station_ids:
            query = query.filter(Detection.station_id.in_(station_ids))

        return query.distinct().order_by(Species.common_name).all()

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
        Get species that are new since Monday of the current week.

        "New" is judged per station, not globally. A species detected for the
        first time at station B this week is new *to that station* even if
        station A has recorded it for years; with several stations selected the
        list is the union across them. Judging it globally was issue #25: with
        both stations selected the user only ever saw whichever station happened
        to hold the global first record.

        Each row carries ``is_first_ever`` so the UI can distinguish a genuine
        lifer from a first-for-this-station.

        Args:
            station_ids: Restrict to these stations. None means all stations.

        Returns:
            List of dicts with species info, first detection date, the station
            it is new to, and this week's detection count.
        """
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        # First detection per (species, station), across all history.
        per_station_first = self.db.query(
            Detection.species_id.label('species_id'),
            Detection.station_id.label('station_id'),
            func.min(Detection.detection_date).label('first_date'),
        )
        if station_ids:
            per_station_first = per_station_first.filter(
                Detection.station_id.in_(station_ids)
            )
        per_station_first = per_station_first.group_by(
            Detection.species_id, Detection.station_id
        ).subquery()

        # Species that are new to at least one of the selected stations.
        new_rows = (
            self.db.query(
                per_station_first.c.species_id,
                per_station_first.c.station_id,
                per_station_first.c.first_date,
            )
            .filter(per_station_first.c.first_date >= monday)
            .all()
        )

        if not new_rows:
            return []

        species_ids = {row.species_id for row in new_rows}

        # First-ever date across every station, so a first-for-this-station can
        # be told apart from a lifer. Deliberately unfiltered by station.
        first_ever = dict(
            self.db.query(
                Detection.species_id,
                func.min(Detection.detection_date),
            )
            .filter(Detection.species_id.in_(species_ids))
            .group_by(Detection.species_id)
            .all()
        )

        # This week's detection counts, within the selected stations.
        counts_query = (
            self.db.query(
                Detection.species_id,
                func.count(Detection.id).label('detection_count'),
            )
            .filter(Detection.species_id.in_(species_ids))
            .filter(Detection.detection_date >= monday)
        )
        if station_ids:
            counts_query = counts_query.filter(Detection.station_id.in_(station_ids))
        counts = dict(counts_query.group_by(Detection.species_id).all())

        station_names = dict(
            self.db.query(Station.id, Station.name).all()
        )

        species_rows = {
            sp.id: sp
            for sp in self.db.query(Species).filter(Species.id.in_(species_ids)).all()
        }

        # Collapse to one row per species, keeping the earliest arrival and
        # naming every station it is new to.
        by_species: dict = {}
        for row in new_rows:
            entry = by_species.get(row.species_id)
            name = station_names.get(row.station_id, f"Station {row.station_id}")
            if entry is None:
                by_species[row.species_id] = {
                    'first_detection_date': row.first_date,
                    'stations': [name],
                }
            else:
                entry['stations'].append(name)
                if row.first_date < entry['first_detection_date']:
                    entry['first_detection_date'] = row.first_date

        results = []
        for species_id, entry in by_species.items():
            species = species_rows.get(species_id)
            if species is None:
                continue
            results.append({
                'species_id': species.species_id,
                'common_name': species.common_name,
                'scientific_name': species.scientific_name,
                'ebird_code': species.ebird_code,
                'first_detection_date': entry['first_detection_date'],
                'detection_count': counts.get(species_id, 0),
                'stations': sorted(set(entry['stations'])),
                'is_first_ever': first_ever.get(species_id) == entry['first_detection_date'],
            })

        results.sort(key=lambda r: (r['first_detection_date'], r['common_name']))
        return results

    def get_returning_species(
        self,
        station_ids: Optional[List[int]] = None,
        recent_days: int = 14,
        min_absence_days: int = 90,
    ) -> List[dict]:
        """
        Species heard again after a long silence — the migrants coming back.

        A species qualifies when it was detected inside the last
        ``recent_days``, and the gap between that return and the previous
        detection was at least ``min_absence_days``. Species with no earlier
        record at all are excluded: those are lifers and belong in the new
        species list, not here.

        Reads the rollup tables, so this stays fast on multi-million-row
        databases.

        Args:
            station_ids: Restrict to these stations.
            recent_days: How far back counts as "just returned".
            min_absence_days: Silence required before a detection counts as a
                return. Three months separates a genuine seasonal return from
                a bird that simply went quiet for a fortnight.
        """
        today = date.today()
        window_start = today - timedelta(days=recent_days)

        # Earliest detection inside the recent window, per species.
        recent = self.db.query(
            DetectionRollup.species_id.label('species_id'),
            func.min(DetectionRollup.detection_date).label('returned_on'),
            func.sum(DetectionRollup.cnt_all).label('detection_count'),
        ).filter(DetectionRollup.detection_date >= window_start)
        if station_ids:
            recent = recent.filter(DetectionRollup.station_id.in_(station_ids))
        recent_rows = recent.group_by(DetectionRollup.species_id).all()

        if not recent_rows:
            return []

        species_ids = [r.species_id for r in recent_rows]
        returned_on = {r.species_id: r.returned_on for r in recent_rows}
        counts = {r.species_id: int(r.detection_count or 0) for r in recent_rows}

        # Last detection strictly before the recent window.
        previous = self.db.query(
            DetectionRollup.species_id,
            func.max(DetectionRollup.detection_date).label('previous_seen'),
        ).filter(
            DetectionRollup.species_id.in_(species_ids),
            DetectionRollup.detection_date < window_start,
        )
        if station_ids:
            previous = previous.filter(DetectionRollup.station_id.in_(station_ids))
        previous_seen = {
            r.species_id: r.previous_seen
            for r in previous.group_by(DetectionRollup.species_id).all()
        }

        species_rows = {
            sp.id: sp
            for sp in self.db.query(Species).filter(Species.id.in_(species_ids)).all()
        }

        results = []
        for species_id in species_ids:
            prior = previous_seen.get(species_id)
            if prior is None:
                continue  # No earlier record: a lifer, not a return.

            arrival = returned_on[species_id]
            absence_days = (arrival - prior).days
            if absence_days < min_absence_days:
                continue

            species = species_rows.get(species_id)
            if species is None:
                continue

            results.append({
                'species_id': species.species_id,
                'internal_id': species.id,
                'common_name': species.common_name,
                'scientific_name': species.scientific_name,
                'ebird_code': species.ebird_code,
                'returned_on': arrival,
                'previous_seen': prior,
                'absence_days': absence_days,
                'detection_count': counts.get(species_id, 0),
            })

        results.sort(key=lambda r: (r['returned_on'], -r['absence_days']), reverse=True)
        return results

    def get_overdue_species(
        self,
        station_ids: Optional[List[int]] = None,
        absent_days: int = 21,
        window_days: int = 21,
        min_prior_years: int = 1,
    ) -> List[dict]:
        """
        Species that history says should be here now, but have not been heard.

        For each species we look at the same calendar window in previous years
        (today's day-of-year plus or minus ``window_days``). A species that was
        present in that window in at least ``min_prior_years`` earlier years,
        but has no detection in the last ``absent_days``, is reported as
        overdue.

        This is the counterpart to the returning-species list: together they
        answer "who is back?" and "who should be back but isn't?".

        Args:
            station_ids: Restrict to these stations.
            absent_days: Silence required before a species counts as missing.
            window_days: Half-width of the calendar window compared against
                previous years.
            min_prior_years: How many earlier years must show the species in
                this window before its absence is considered notable.
        """
        today = date.today()
        absent_since = today - timedelta(days=absent_days)

        # Day-of-year window, as the set of %j values to match. Building the
        # set in Python keeps the year-boundary wrap trivial: late December and
        # early January simply both appear in the list.
        window_days_of_year = {
            (today + timedelta(days=offset)).strftime('%j')
            for offset in range(-window_days, window_days + 1)
        }

        day_of_year = func.strftime('%j', DetectionRollup.detection_date)
        year_of = func.strftime('%Y', DetectionRollup.detection_date)

        historical = self.db.query(
            DetectionRollup.species_id.label('species_id'),
            year_of.label('year'),
            func.min(DetectionRollup.detection_date).label('window_first'),
            func.sum(DetectionRollup.cnt_all).label('detection_count'),
        ).filter(
            day_of_year.in_(sorted(window_days_of_year)),
            DetectionRollup.detection_date < date(today.year, 1, 1),
        )
        if station_ids:
            historical = historical.filter(DetectionRollup.station_id.in_(station_ids))

        history_rows = historical.group_by(
            DetectionRollup.species_id, year_of
        ).all()

        if not history_rows:
            return []

        prior_years: dict = {}
        for row in history_rows:
            if not row.detection_count:
                continue
            entry = prior_years.setdefault(
                row.species_id, {'years': set(), 'earliest': row.window_first}
            )
            entry['years'].add(int(row.year))
            if row.window_first < entry['earliest']:
                entry['earliest'] = row.window_first

        candidates = [
            species_id for species_id, entry in prior_years.items()
            if len(entry['years']) >= min_prior_years
        ]
        if not candidates:
            return []

        # Most recent detection overall, to measure the current silence.
        last_seen_query = self.db.query(
            DetectionRollup.species_id,
            func.max(DetectionRollup.detection_date).label('last_seen'),
        ).filter(DetectionRollup.species_id.in_(candidates))
        if station_ids:
            last_seen_query = last_seen_query.filter(
                DetectionRollup.station_id.in_(station_ids)
            )
        last_seen = {
            r.species_id: r.last_seen
            for r in last_seen_query.group_by(DetectionRollup.species_id).all()
        }

        species_rows = {
            sp.id: sp
            for sp in self.db.query(Species).filter(Species.id.in_(candidates)).all()
        }

        results = []
        for species_id in candidates:
            seen = last_seen.get(species_id)
            if seen is not None and seen >= absent_since:
                continue  # Already back.

            species = species_rows.get(species_id)
            if species is None:
                continue

            entry = prior_years[species_id]
            results.append({
                'species_id': species.species_id,
                'internal_id': species.id,
                'common_name': species.common_name,
                'scientific_name': species.scientific_name,
                'ebird_code': species.ebird_code,
                'last_seen': seen,
                'days_absent': (today - seen).days if seen else None,
                'prior_years': sorted(entry['years'], reverse=True),
                'typical_arrival': entry['earliest'].strftime('%d %b'),
            })

        results.sort(
            key=lambda r: (-len(r['prior_years']), r['days_absent'] or 10**6)
        )
        return results

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
        Update cached statistics for all species that have detections.

        This calculates first_seen, last_seen, and total_detections
        from actual detection data.

        Returns:
            Number of species updated
        """
        # Get all species stats in one query
        stats_query = (
            self.db.query(
                Detection.species_id,
                func.count(Detection.id).label('total'),
                func.min(Detection.timestamp).label('first'),
                func.max(Detection.timestamp).label('last')
            )
            .group_by(Detection.species_id)
        )

        updated_count = 0
        for row in stats_query.all():
            species = self.get_by_id(row.species_id)
            if species:
                species.total_detections = row.total or 0
                species.first_seen = row.first
                species.last_seen = row.last
                updated_count += 1

        self.db.commit()
        return updated_count

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
