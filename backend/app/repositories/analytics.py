"""
Analytics Repository
Data access methods for advanced analytics queries.

Every method here reads the pre-aggregated rollup tables rather than the raw
``detections`` table. At Pittsburgh-region volumes (~10M detections/year) a
rolling-6-month query over raw rows scans millions of records and blows the
30-second client timeout; the same query over ``detection_rollups`` touches
tens of thousands.

Confidence filtering: the rollups store cumulative counts at 0.05 steps from
0.50 up. A requested ``min_confidence`` snaps *down* to the nearest stored step
(so 0.72 is served as 0.70 and is never under-inclusive), and anything below
0.50 uses the unfiltered count. See db/models/rollup.py.

Version: 2.0.0
"""

from typing import List, Optional, Tuple
from datetime import date, timedelta
from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session
from collections import defaultdict

from app.db.models.rollup import DetectionRollup, SolarRollup, CONFIDENCE_BUCKETS
from app.db.models.species import Species
from app.db.models.weather import Weather

# Species listed in a dawn/dusk chorus bar's hover tooltip.
CHORUS_TOP_SPECIES = 10

MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]


def _count_column(model, min_confidence: float):
    """
    Pick the cumulative-count column that satisfies ``min_confidence``.

    Snaps down to the nearest stored bucket so the result is never narrower
    than requested. Below the lowest bucket we use the unfiltered count.
    """
    chosen = None
    for suffix, threshold in CONFIDENCE_BUCKETS:
        if threshold <= min_confidence + 1e-9:
            chosen = suffix
        else:
            break

    if chosen is None:
        return model.cnt_all
    return getattr(model, f"cnt_{chosen}")


class AnalyticsRepository:
    """Repository for advanced analytics data access."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Shared query helpers
    # ------------------------------------------------------------------

    def _scoped(self, query, station_ids: Optional[List[int]], model=DetectionRollup):
        """Apply the station filter shared by every analytics query."""
        if station_ids:
            return query.filter(model.station_id.in_(station_ids))
        return query

    def _top_species_ids(
        self,
        cnt,
        start_date: date,
        end_date: Optional[date],
        station_ids: Optional[List[int]],
        limit: int,
        order_by_days: bool = False,
    ) -> List[Tuple[int, int]]:
        """
        Rank species by detections (or by active days) within a window.

        Returns (species_id, metric) pairs, most active first.
        """
        metric = (
            func.count(func.distinct(DetectionRollup.detection_date))
            if order_by_days
            else func.sum(cnt)
        )

        query = (
            self.db.query(DetectionRollup.species_id, metric.label('metric'))
            .filter(DetectionRollup.detection_date >= start_date)
            .filter(cnt > 0)
        )
        if end_date is not None:
            query = query.filter(DetectionRollup.detection_date <= end_date)
        query = self._scoped(query, station_ids)

        rows = (
            query.group_by(DetectionRollup.species_id)
            .order_by(metric.desc())
            .limit(limit)
            .all()
        )
        return [(r.species_id, int(r.metric or 0)) for r in rows]

    def _species_lookup(self, species_ids: List[int]) -> dict:
        """Map species id -> (common_name, scientific_name)."""
        if not species_ids:
            return {}
        rows = (
            self.db.query(Species.id, Species.common_name, Species.scientific_name)
            .filter(Species.id.in_(species_ids))
            .all()
        )
        return {r.id: (r.common_name, r.scientific_name) for r in rows}

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------

    def get_species_hour_bubble_data(
        self,
        limit: int = 50,
        months: int = 3,
        station_ids: Optional[List[int]] = None,
        min_confidence: float = 0.7
    ) -> List[dict]:
        """Species activity by hour of day, for the bubble/heatmap chart."""
        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        top = self._top_species_ids(cnt, cutoff_date, None, station_ids, limit)
        if not top:
            return []

        species_ids = [sid for sid, _ in top]
        species_totals = dict(top)
        info = self._species_lookup(species_ids)

        query = (
            self.db.query(
                DetectionRollup.species_id,
                DetectionRollup.hour,
                func.sum(cnt).label('detection_count'),
            )
            .filter(DetectionRollup.species_id.in_(species_ids))
            .filter(DetectionRollup.detection_date >= cutoff_date)
        )
        query = self._scoped(query, station_ids)

        rows = query.group_by(DetectionRollup.species_id, DetectionRollup.hour).all()

        results = []
        for row in rows:
            if not row.detection_count:
                continue
            common_name, scientific_name = info.get(row.species_id, ('Unknown', 'Unknown'))
            results.append({
                'species_id': row.species_id,
                'common_name': common_name,
                'scientific_name': scientific_name,
                'hour': int(row.hour),
                'detection_count': int(row.detection_count),
                'total_detections': species_totals[row.species_id],
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
        Phenology heatmap data (species x week).

        ``year=None`` or ``0`` means a rolling 12 months from today.
        """
        today = date.today()
        if year is None or year == 0:
            end_date = today
            start_date = date(today.year - 1, today.month, today.day)
        else:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

        cnt = _count_column(DetectionRollup, min_confidence)

        top = self._top_species_ids(cnt, start_date, end_date, station_ids, limit)
        if not top:
            return []

        species_ids = [sid for sid, _ in top]
        info = self._species_lookup(species_ids)

        week = func.strftime('%W', DetectionRollup.detection_date).label('week')
        # Group by calendar year as well as week: a rolling 12-month window
        # spans two years, and reporting the requested `year` verbatim gave a
        # null when the caller asked for the rolling window.
        week_year = func.strftime('%Y', DetectionRollup.detection_date).label('week_year')

        query = (
            self.db.query(
                DetectionRollup.species_id,
                week_year,
                week,
                func.sum(cnt).label('detection_count'),
            )
            .filter(DetectionRollup.species_id.in_(species_ids))
            .filter(DetectionRollup.detection_date >= start_date)
            .filter(DetectionRollup.detection_date <= end_date)
        )
        query = self._scoped(query, station_ids)

        rows = query.group_by(DetectionRollup.species_id, week_year, week).all()

        # The heatmap plots one cell per (species, week), so fold the two
        # calendar years of a rolling window onto the same week number.
        cells: dict = {}
        for row in rows:
            if not row.detection_count:
                continue
            key = (row.species_id, int(row.week) + 1)  # strftime %W is 0-indexed
            cell = cells.get(key)
            if cell is None:
                cells[key] = {
                    'species_id': row.species_id,
                    'common_name': info.get(row.species_id, ('Unknown', ''))[0],
                    'week_number': key[1],
                    'year': int(row.week_year),
                    'detection_count': int(row.detection_count),
                }
            else:
                cell['detection_count'] += int(row.detection_count)
                cell['year'] = max(cell['year'], int(row.week_year))

        return list(cells.values())

    def get_confidence_scatter_data(
        self,
        station_ids: Optional[List[int]] = None,
        min_detections: int = 10
    ) -> List[dict]:
        """Detections vs. mean confidence, one point per species."""
        total = func.sum(DetectionRollup.cnt_all)
        query = self.db.query(
            DetectionRollup.species_id,
            total.label('total_detections'),
            func.sum(DetectionRollup.conf_sum).label('conf_sum'),
            func.count(func.distinct(DetectionRollup.detection_date)).label('detection_days'),
        )
        query = self._scoped(query, station_ids)

        rows = (
            query.group_by(DetectionRollup.species_id)
            .having(total >= min_detections)
            .order_by(total.desc())
            .all()
        )

        info = self._species_lookup([r.species_id for r in rows])

        results = []
        for row in rows:
            count = int(row.total_detections or 0)
            if count == 0:
                continue
            common_name, scientific_name = info.get(row.species_id, ('Unknown', 'Unknown'))
            results.append({
                'species_id': row.species_id,
                'common_name': common_name,
                'scientific_name': scientific_name,
                'total_detections': count,
                'avg_confidence': round(float(row.conf_sum or 0.0) / count, 3),
                'detection_days': int(row.detection_days or 0),
            })

        return results

    def get_confidence_by_hour(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6
    ) -> List[dict]:
        """
        Confidence distribution by hour, for the reliability heatmap.

        Each bin is the difference between two cumulative rollup columns, so
        the whole heatmap comes from a single grouped scan.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        bins = [
            ('0.50-0.60', 0.5, 0.6, DetectionRollup.cnt_50, DetectionRollup.cnt_60),
            ('0.60-0.70', 0.6, 0.7, DetectionRollup.cnt_60, DetectionRollup.cnt_70),
            ('0.70-0.80', 0.7, 0.8, DetectionRollup.cnt_70, DetectionRollup.cnt_80),
            ('0.80-0.90', 0.8, 0.9, DetectionRollup.cnt_80, DetectionRollup.cnt_90),
            ('0.90-1.00', 0.9, 1.0, DetectionRollup.cnt_90, None),
        ]

        selects = [DetectionRollup.hour]
        for _, _, _, lower, upper in bins:
            expr = func.sum(lower - upper) if upper is not None else func.sum(lower)
            selects.append(expr)

        query = self.db.query(*selects).filter(
            DetectionRollup.detection_date >= cutoff_date
        )
        query = self._scoped(query, station_ids)

        rows = query.group_by(DetectionRollup.hour).all()

        results = []
        for row in rows:
            hour = int(row[0])
            for idx, (label, conf_min, conf_max, _, _) in enumerate(bins, start=1):
                count = int(row[idx] or 0)
                if count <= 0:
                    continue
                results.append({
                    'hour': hour,
                    'confidence_bin': label,
                    'confidence_min': conf_min,
                    'confidence_max': conf_max,
                    'detection_count': count,
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
        """Daily detection counts per species, for the density/KDE plot."""
        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        if not species_ids:
            species_ids = [
                sid for sid, _ in
                self._top_species_ids(cnt, cutoff_date, None, station_ids, limit)
            ]

        if not species_ids:
            return []

        info = self._species_lookup(species_ids)

        query = (
            self.db.query(
                DetectionRollup.species_id,
                DetectionRollup.detection_date,
                func.sum(cnt).label('detection_count'),
            )
            .filter(DetectionRollup.species_id.in_(species_ids))
            .filter(DetectionRollup.detection_date >= cutoff_date)
        )
        query = self._scoped(query, station_ids)

        rows = (
            query.group_by(DetectionRollup.species_id, DetectionRollup.detection_date)
            .order_by(DetectionRollup.detection_date)
            .all()
        )

        return [
            {
                'species_id': row.species_id,
                'common_name': info.get(row.species_id, ('Unknown', ''))[0],
                'date': row.detection_date,
                'detection_count': int(row.detection_count),
            }
            for row in rows
            if row.detection_count
        ]

    def get_chorus_data(
        self,
        phase: str = 'sunrise',
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        window_minutes: int = 120,
    ) -> List[dict]:
        """
        Detection activity relative to sunrise or sunset.

        ``phase='sunrise'`` gives the dawn chorus; ``phase='sunset'`` gives the
        dusk chorus, which is where bat and owl activity shows up. Both read
        the solar rollup, which already stores 5-minute bins out to +/-180
        minutes with the midnight wrap handled at build time.
        """
        if phase not in ('sunrise', 'sunset'):
            raise ValueError(f"phase must be 'sunrise' or 'sunset', got {phase!r}")

        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(SolarRollup, min_confidence)

        query = (
            self.db.query(
                SolarRollup.minute_bin,
                func.sum(cnt).label('detection_count'),
                func.count(func.distinct(SolarRollup.species_id)).label('species_count'),
            )
            .filter(SolarRollup.phase == phase)
            .filter(SolarRollup.detection_date >= cutoff_date)
            .filter(SolarRollup.minute_bin >= -window_minutes)
            .filter(SolarRollup.minute_bin <= window_minutes)
            .filter(cnt > 0)
        )
        query = self._scoped(query, station_ids, model=SolarRollup)

        rows = (
            query.group_by(SolarRollup.minute_bin)
            .order_by(SolarRollup.minute_bin)
            .all()
        )

        top_by_bin = self._chorus_top_species(
            phase, cutoff_date, station_ids, window_minutes, cnt
        )

        key = 'minutes_from_sunrise' if phase == 'sunrise' else 'minutes_from_sunset'
        return [
            {
                key: int(row.minute_bin),
                'detection_count': int(row.detection_count or 0),
                'species_count': int(row.species_count or 0),
                'top_species': top_by_bin.get(int(row.minute_bin), []),
            }
            for row in rows
            if row.detection_count
        ]

    def _chorus_top_species(
        self,
        phase: str,
        cutoff_date: date,
        station_ids: Optional[List[int]],
        window_minutes: int,
        cnt,
        limit: int = CHORUS_TOP_SPECIES,
        species_ids: Optional[List[int]] = None,
    ) -> dict:
        """
        The most-detected species in each minute bin, for hover tooltips.

        One grouped scan of the solar rollup, ranked per bin in Python. The
        rollup already stores counts per species per bin, so this costs about
        the same as the totals query beside it.
        """
        query = (
            self.db.query(
                SolarRollup.minute_bin,
                SolarRollup.species_id,
                func.sum(cnt).label('detection_count'),
            )
            .filter(SolarRollup.phase == phase)
            .filter(SolarRollup.detection_date >= cutoff_date)
            .filter(SolarRollup.minute_bin >= -window_minutes)
            .filter(SolarRollup.minute_bin <= window_minutes)
            .filter(cnt > 0)
        )
        if species_ids:
            query = query.filter(SolarRollup.species_id.in_(species_ids))
        query = self._scoped(query, station_ids, model=SolarRollup)

        rows = query.group_by(SolarRollup.minute_bin, SolarRollup.species_id).all()
        if not rows:
            return {}

        by_bin: dict = defaultdict(list)
        for row in rows:
            count = int(row.detection_count or 0)
            if count:
                by_bin[int(row.minute_bin)].append((row.species_id, count))

        # Only the species that actually make a tooltip need names looking up.
        wanted = set()
        for entries in by_bin.values():
            entries.sort(key=lambda e: e[1], reverse=True)
            del entries[limit:]
            wanted.update(sid for sid, _ in entries)

        info = self._species_lookup(list(wanted))

        return {
            minute_bin: [
                {
                    'species_id': sid,
                    'common_name': info.get(sid, ('Unknown', ''))[0],
                    'detection_count': count,
                }
                for sid, count in entries
            ]
            for minute_bin, entries in by_bin.items()
        }

    def get_dawn_chorus_data(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        window_minutes: int = 120
    ) -> List[dict]:
        """Dawn chorus: activity relative to sunrise."""
        return self.get_chorus_data(
            phase='sunrise',
            station_ids=station_ids,
            months=months,
            min_confidence=min_confidence,
            window_minutes=window_minutes,
        )

    def get_dusk_chorus_data(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        window_minutes: int = 120
    ) -> List[dict]:
        """Dusk chorus: activity relative to sunset."""
        return self.get_chorus_data(
            phase='sunset',
            station_ids=station_ids,
            months=months,
            min_confidence=min_confidence,
            window_minutes=window_minutes,
        )

    def get_weather_impact_data(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        analysis_type: str = 'temperature'
    ) -> List[dict]:
        """Detection counts grouped by weather conditions."""
        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        def daily_query(*extra_columns):
            query = (
                self.db.query(
                    Weather.weather_date,
                    *extra_columns,
                    func.sum(cnt).label('detection_count'),
                )
                .join(DetectionRollup, and_(
                    Weather.station_id == DetectionRollup.station_id,
                    Weather.weather_date == DetectionRollup.detection_date,
                ))
                .filter(DetectionRollup.detection_date >= cutoff_date)
            )
            return self._scoped(query, station_ids)

        results: List[dict] = []

        if analysis_type == 'temperature':
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

            rows = (
                daily_query(temp_bin)
                .filter(Weather.temp_avg.isnot(None))
                .group_by(temp_bin, Weather.weather_date)
                .all()
            )

            bin_stats = defaultdict(lambda: {'total': 0, 'days': 0})
            for row in rows:
                if row.temp_bin is None or not row.detection_count:
                    continue
                bin_stats[row.temp_bin]['total'] += int(row.detection_count)
                bin_stats[row.temp_bin]['days'] += 1

            bin_order = ['< 0°F', '0-20°F', '20-32°F', '32-50°F', '50-60°F',
                         '60-70°F', '70-80°F', '80-90°F', '> 90°F']
            for label in bin_order:
                if label in bin_stats:
                    stats = bin_stats[label]
                    results.append({
                        'temperature_bin': label,
                        'condition': None,
                        'avg_detections': round(stats['total'] / stats['days'], 1),
                        'total_detections': stats['total'],
                        'observation_count': stats['days'],
                    })

        elif analysis_type == 'condition':
            rows = (
                daily_query(Weather.weather_description)
                .group_by(Weather.weather_date, Weather.weather_description)
                .all()
            )

            condition_stats = defaultdict(lambda: {'total': 0, 'days': 0})
            for row in rows:
                if not row.detection_count:
                    continue
                raw = (row.weather_description or '').lower()
                if 'rain' in raw or 'shower' in raw:
                    condition = 'Rainy'
                elif 'cloud' in raw or 'overcast' in raw:
                    condition = 'Cloudy'
                elif 'sun' in raw or 'clear' in raw:
                    condition = 'Clear/Sunny'
                elif 'snow' in raw:
                    condition = 'Snow'
                elif 'fog' in raw or 'mist' in raw:
                    condition = 'Fog/Mist'
                else:
                    condition = 'Other'

                condition_stats[condition]['total'] += int(row.detection_count)
                condition_stats[condition]['days'] += 1

            for condition, stats in condition_stats.items():
                results.append({
                    'temperature_bin': None,
                    'condition': condition,
                    'avg_detections': round(stats['total'] / stats['days'], 1),
                    'total_detections': stats['total'],
                    'observation_count': stats['days'],
                })

        elif analysis_type == 'precipitation':
            rows = (
                daily_query(Weather.weather_description, Weather.precipitation)
                .group_by(Weather.weather_date, Weather.weather_description,
                          Weather.precipitation)
                .all()
            )

            categories = {
                'No Precip': {'total': 0, 'days': 0},
                'Light Rain': {'total': 0, 'days': 0},
                'Moderate Rain': {'total': 0, 'days': 0},
                'Heavy Rain': {'total': 0, 'days': 0},
                'Snow': {'total': 0, 'days': 0},
            }

            for row in rows:
                if not row.detection_count:
                    continue
                desc = (row.weather_description or '').lower()
                precip = row.precipitation or 0

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

                categories[category]['total'] += int(row.detection_count)
                categories[category]['days'] += 1

            for label in ['No Precip', 'Light Rain', 'Moderate Rain', 'Heavy Rain', 'Snow']:
                stats = categories[label]
                if stats['days'] > 0:
                    results.append({
                        'temperature_bin': label,
                        'condition': None,
                        'avg_detections': round(stats['total'] / stats['days'], 1),
                        'total_detections': stats['total'],
                        'observation_count': stats['days'],
                    })

        return results

    def get_weekly_trends(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 12,
        min_confidence: float = 0.7
    ) -> List[dict]:
        """Weekly totals, unique species and daily averages."""
        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        year = func.strftime('%Y', DetectionRollup.detection_date).label('year')
        week = func.strftime('%W', DetectionRollup.detection_date).label('week')

        query = (
            self.db.query(
                year,
                week,
                func.min(DetectionRollup.detection_date).label('week_start'),
                func.sum(cnt).label('total_detections'),
                func.count(func.distinct(DetectionRollup.species_id)).label('unique_species'),
                func.count(func.distinct(DetectionRollup.detection_date)).label('days_with_data'),
            )
            .filter(DetectionRollup.detection_date >= cutoff_date)
            .filter(cnt > 0)
        )
        query = self._scoped(query, station_ids)

        rows = query.group_by(year, week).order_by(year, week).all()

        results = []
        for row in rows:
            total = int(row.total_detections or 0)
            if total == 0:
                continue
            avg_daily = total / max(int(row.days_with_data or 1), 1)
            results.append({
                'week_start': row.week_start,
                'year': int(row.year),
                'week_number': int(row.week) + 1,
                'total_detections': total,
                'unique_species': int(row.unique_species or 0),
                'avg_daily_detections': round(avg_daily, 1),
            })

        return results

    def get_co_occurrence_matrix(
        self,
        station_ids: Optional[List[int]] = None,
        months: int = 6,
        min_confidence: float = 0.7,
        limit: int = 20
    ) -> List[dict]:
        """Jaccard similarity between species, by days co-detected."""
        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        top = self._top_species_ids(
            cnt, cutoff_date, None, station_ids, limit, order_by_days=True
        )
        if len(top) < 2:
            return []

        species_ids = [sid for sid, _ in top]
        total_days = dict(top)
        info = self._species_lookup(species_ids)

        dates_query = (
            self.db.query(DetectionRollup.species_id, DetectionRollup.detection_date)
            .filter(DetectionRollup.species_id.in_(species_ids))
            .filter(DetectionRollup.detection_date >= cutoff_date)
            .filter(cnt > 0)
            .distinct()
        )
        dates_query = self._scoped(dates_query, station_ids)

        species_dates = {sid: set() for sid in species_ids}
        for row in dates_query.all():
            species_dates[row.species_id].add(row.detection_date)

        results = []
        for i, sp1_id in enumerate(species_ids):
            for sp2_id in species_ids[i:]:
                sp1_name = info.get(sp1_id, ('Unknown', ''))[0]
                sp2_name = info.get(sp2_id, ('Unknown', ''))[0]

                sp1_dates = species_dates[sp1_id]
                sp2_dates = species_dates[sp2_id]

                intersection = len(sp1_dates & sp2_dates)
                union = len(sp1_dates | sp2_dates)
                jaccard = intersection / union if union > 0 else 0

                results.append({
                    'species_1': sp1_name,
                    'species_2': sp2_name,
                    'co_occurrence_days': intersection,
                    'species_1_total_days': total_days[sp1_id],
                    'species_2_total_days': total_days[sp2_id],
                    'jaccard_index': round(jaccard, 3),
                })

                if sp1_id != sp2_id:
                    results.append({
                        'species_1': sp2_name,
                        'species_2': sp1_name,
                        'co_occurrence_days': intersection,
                        'species_1_total_days': total_days[sp2_id],
                        'species_2_total_days': total_days[sp1_id],
                        'jaccard_index': round(jaccard, 3),
                    })

        return results

    def get_species_seasonality(
        self,
        station_ids: Optional[List[int]] = None,
        min_confidence: float = 0.7,
        limit: int = 50
    ) -> List[dict]:
        """First/last sighting, peak month and active days per species."""
        cnt = _count_column(DetectionRollup, min_confidence)
        total = func.sum(cnt)

        query = (
            self.db.query(
                DetectionRollup.species_id,
                func.min(DetectionRollup.detection_date).label('first_seen'),
                func.max(DetectionRollup.detection_date).label('last_seen'),
                total.label('total_detections'),
                func.count(func.distinct(DetectionRollup.detection_date)).label('active_days'),
            )
            .filter(cnt > 0)
        )
        query = self._scoped(query, station_ids)

        base_results = (
            query.group_by(DetectionRollup.species_id)
            .order_by(total.desc())
            .limit(limit)
            .all()
        )

        species_ids = [r.species_id for r in base_results]
        if not species_ids:
            return []

        species_data = {r.species_id: r for r in base_results}
        info = self._species_lookup(species_ids)

        month = func.strftime('%m', DetectionRollup.detection_date).label('month')
        monthly_query = (
            self.db.query(
                DetectionRollup.species_id,
                month,
                func.sum(cnt).label('count'),
            )
            .filter(DetectionRollup.species_id.in_(species_ids))
            .filter(cnt > 0)
        )
        monthly_query = self._scoped(monthly_query, station_ids)

        peak_months = {}
        best_counts = {}
        for row in monthly_query.group_by(DetectionRollup.species_id, month).all():
            count = int(row.count or 0)
            if count > best_counts.get(row.species_id, -1):
                best_counts[row.species_id] = count
                peak_months[row.species_id] = int(row.month)

        results = []
        for species_id in species_ids:
            data = species_data[species_id]
            peak_month = peak_months.get(species_id, 1)
            results.append({
                'species_id': species_id,
                'common_name': info.get(species_id, ('Unknown', ''))[0],
                'first_seen': data.first_seen,
                'last_seen': data.last_seen,
                'peak_month': peak_month,
                'peak_month_name': MONTH_NAMES[peak_month],
                'total_detections': int(data.total_detections or 0),
                'active_days': int(data.active_days or 0),
            })

        return results

    def get_monthly_champions(
        self,
        station_ids: Optional[List[int]] = None,
        year: Optional[int] = None,
        min_confidence: float = 0.7
    ) -> List[dict]:
        """The most-detected species for each of the rolling 12 months."""
        today = date.today()
        start_date = date(today.year - 1, today.month, 1)
        cnt = _count_column(DetectionRollup, min_confidence)

        year_col = func.strftime('%Y', DetectionRollup.detection_date).label('year')
        month_col = func.strftime('%m', DetectionRollup.detection_date).label('month')

        query = (
            self.db.query(
                year_col,
                month_col,
                DetectionRollup.species_id,
                func.sum(cnt).label('detection_count'),
            )
            .filter(DetectionRollup.detection_date >= start_date)
            .filter(DetectionRollup.detection_date <= today)
            .filter(cnt > 0)
        )
        query = self._scoped(query, station_ids)

        rows = query.group_by(year_col, month_col, DetectionRollup.species_id).all()

        month_stats = defaultdict(lambda: {'species': {}, 'total': 0})
        for row in rows:
            count = int(row.detection_count or 0)
            if count == 0:
                continue
            key = (int(row.year), int(row.month))
            month_stats[key]['species'][row.species_id] = count
            month_stats[key]['total'] += count

        all_species = {sid for stats in month_stats.values() for sid in stats['species']}
        info = self._species_lookup(list(all_species))

        results = []
        for (yr, month), stats in sorted(month_stats.items()):
            if stats['total'] == 0:
                continue

            top_species_id = max(stats['species'], key=stats['species'].get)
            count = stats['species'][top_species_id]
            percentage = (count / stats['total']) * 100

            results.append({
                'month': month,
                'month_name': f"{MONTH_NAMES[month]} {yr}",
                'year': yr,
                'species_id': top_species_id,
                'common_name': info.get(top_species_id, ('Unknown', ''))[0],
                'detection_count': count,
                'percentage_of_month': round(percentage, 1),
            })

        return results
