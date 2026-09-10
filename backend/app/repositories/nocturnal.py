"""
Nocturnal Repository
Queries backing the Nocturnal page (bats, owls, nightjars and allies).

Like the analytics repository, everything here reads the rollup tables so the
page stays responsive at multi-million-detection scale. Species membership is
decided by taxonomy — see services/taxonomy_groups.py.

Version: 1.0.0
"""

from typing import List, Optional
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.rollup import DetectionRollup, SolarRollup
from app.db.models.species import Species
from app.repositories.analytics import _count_column
from app.services import taxonomy_groups


class NocturnalRepository:
    """Data access for nocturnal species analytics."""

    def __init__(self, db: Session):
        self.db = db

    def _group_species_ids(self, groups: Optional[List[str]] = None) -> dict:
        """Map species id -> group key for every species in the given groups."""
        rows = (
            self.db.query(Species.id, Species.common_name, Species.scientific_name,
                          Species.order, Species.family)
            .filter(taxonomy_groups.nocturnal_filter(groups))
            .all()
        )
        return {
            r.id: {
                'group': taxonomy_groups.classify(r.order, r.family),
                'common_name': r.common_name,
                'scientific_name': r.scientific_name,
                'family': r.family,
            }
            for r in rows
        }

    def get_summary(
        self,
        groups: Optional[List[str]] = None,
        station_ids: Optional[List[int]] = None,
        months: int = 12,
        min_confidence: float = 0.7,
    ) -> dict:
        """
        Per-group totals plus a per-species breakdown.

        Returns ``taxonomy_available`` so the UI can tell "no bats detected"
        apart from "taxonomy never loaded".
        """
        species_map = self._group_species_ids(groups)
        available = taxonomy_groups.taxonomy_available(self.db)

        if not species_map:
            return {
                'taxonomy_available': available,
                'groups': [],
                'species': [],
            }

        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        query = (
            self.db.query(
                DetectionRollup.species_id,
                func.sum(cnt).label('detection_count'),
                func.count(func.distinct(DetectionRollup.detection_date)).label('active_nights'),
                func.min(DetectionRollup.detection_date).label('first_seen'),
                func.max(DetectionRollup.detection_date).label('last_seen'),
            )
            .filter(DetectionRollup.species_id.in_(list(species_map)))
            .filter(DetectionRollup.detection_date >= cutoff_date)
            .filter(cnt > 0)
        )
        if station_ids:
            query = query.filter(DetectionRollup.station_id.in_(station_ids))

        rows = query.group_by(DetectionRollup.species_id).all()

        species = []
        group_totals = {}
        for row in rows:
            count = int(row.detection_count or 0)
            if count == 0:
                continue
            meta = species_map[row.species_id]
            group = meta['group']

            species.append({
                'species_id': row.species_id,
                'common_name': meta['common_name'],
                'scientific_name': meta['scientific_name'],
                'family': meta['family'],
                'group': group,
                'group_label': taxonomy_groups.GROUPS[group]['label'] if group else 'Other',
                'detection_count': count,
                'active_nights': int(row.active_nights or 0),
                'first_seen': row.first_seen,
                'last_seen': row.last_seen,
            })

            totals = group_totals.setdefault(
                group, {'detection_count': 0, 'species_count': 0, 'active_nights': set()}
            )
            totals['detection_count'] += count
            totals['species_count'] += 1

        species.sort(key=lambda s: s['detection_count'], reverse=True)

        groups_out = []
        for key in taxonomy_groups.NOCTURNAL_GROUPS:
            if groups and key not in groups:
                continue
            spec = taxonomy_groups.GROUPS[key]
            totals = group_totals.get(key, {'detection_count': 0, 'species_count': 0})
            groups_out.append({
                'group': key,
                'label': spec['label'],
                'description': spec['description'],
                'species_count': totals['species_count'],
                'detection_count': totals['detection_count'],
            })

        return {
            'taxonomy_available': available,
            'groups': groups_out,
            'species': species,
        }

    def get_hourly_activity(
        self,
        groups: Optional[List[str]] = None,
        station_ids: Optional[List[int]] = None,
        months: int = 12,
        min_confidence: float = 0.7,
    ) -> List[dict]:
        """Detections by hour of day for each nocturnal species."""
        species_map = self._group_species_ids(groups)
        if not species_map:
            return []

        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        query = (
            self.db.query(
                DetectionRollup.species_id,
                DetectionRollup.hour,
                func.sum(cnt).label('detection_count'),
            )
            .filter(DetectionRollup.species_id.in_(list(species_map)))
            .filter(DetectionRollup.detection_date >= cutoff_date)
        )
        if station_ids:
            query = query.filter(DetectionRollup.station_id.in_(station_ids))

        rows = query.group_by(DetectionRollup.species_id, DetectionRollup.hour).all()

        return [
            {
                'species_id': row.species_id,
                'common_name': species_map[row.species_id]['common_name'],
                'group': species_map[row.species_id]['group'],
                'hour': int(row.hour),
                'detection_count': int(row.detection_count),
            }
            for row in rows
            if row.detection_count
        ]

    def get_nightly_totals(
        self,
        groups: Optional[List[str]] = None,
        station_ids: Optional[List[int]] = None,
        months: int = 12,
        min_confidence: float = 0.7,
    ) -> List[dict]:
        """Detections per night per group, for the seasonal activity chart."""
        species_map = self._group_species_ids(groups)
        if not species_map:
            return []

        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(DetectionRollup, min_confidence)

        query = (
            self.db.query(
                DetectionRollup.species_id,
                DetectionRollup.detection_date,
                func.sum(cnt).label('detection_count'),
            )
            .filter(DetectionRollup.species_id.in_(list(species_map)))
            .filter(DetectionRollup.detection_date >= cutoff_date)
        )
        if station_ids:
            query = query.filter(DetectionRollup.station_id.in_(station_ids))

        rows = (
            query.group_by(DetectionRollup.species_id, DetectionRollup.detection_date)
            .order_by(DetectionRollup.detection_date)
            .all()
        )

        # Collapse to one row per (date, group).
        totals = {}
        for row in rows:
            count = int(row.detection_count or 0)
            if count == 0:
                continue
            group = species_map[row.species_id]['group'] or 'other'
            key = (row.detection_date, group)
            entry = totals.setdefault(
                key, {'date': row.detection_date, 'group': group,
                      'detection_count': 0, 'species_count': 0}
            )
            entry['detection_count'] += count
            entry['species_count'] += 1

        return sorted(totals.values(), key=lambda e: (e['date'], e['group']))

    def get_chorus(
        self,
        phase: str = 'sunset',
        groups: Optional[List[str]] = None,
        station_ids: Optional[List[int]] = None,
        months: int = 12,
        min_confidence: float = 0.7,
        window_minutes: int = 180,
    ) -> List[dict]:
        """
        Sunset- (or sunrise-) relative activity for nocturnal species only.

        This is the Nocturnal page's version of the Dusk Chorus chart: same
        shape as the Analytics one, restricted to bats, owls and nightjars so
        the evening emergence peak is not swamped by songbirds.
        """
        if phase not in ('sunrise', 'sunset'):
            raise ValueError(f"phase must be 'sunrise' or 'sunset', got {phase!r}")

        species_map = self._group_species_ids(groups)
        if not species_map:
            return []

        cutoff_date = date.today() - timedelta(days=months * 30)
        cnt = _count_column(SolarRollup, min_confidence)

        query = (
            self.db.query(
                SolarRollup.minute_bin,
                func.sum(cnt).label('detection_count'),
                func.count(func.distinct(SolarRollup.species_id)).label('species_count'),
            )
            .filter(SolarRollup.species_id.in_(list(species_map)))
            .filter(SolarRollup.phase == phase)
            .filter(SolarRollup.detection_date >= cutoff_date)
            .filter(SolarRollup.minute_bin >= -window_minutes)
            .filter(SolarRollup.minute_bin <= window_minutes)
            .filter(cnt > 0)
        )
        if station_ids:
            query = query.filter(SolarRollup.station_id.in_(station_ids))

        rows = (
            query.group_by(SolarRollup.minute_bin)
            .order_by(SolarRollup.minute_bin)
            .all()
        )

        key = 'minutes_from_sunrise' if phase == 'sunrise' else 'minutes_from_sunset'
        return [
            {
                key: int(row.minute_bin),
                'detection_count': int(row.detection_count or 0),
                'species_count': int(row.species_count or 0),
            }
            for row in rows
            if row.detection_count
        ]
