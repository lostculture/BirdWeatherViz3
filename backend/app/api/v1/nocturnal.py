"""
Nocturnal API Endpoints
Endpoints backing the Nocturnal page: bats, owls, nightjars and allies.

Species membership comes from the eBird taxonomy (order/family) already stored
on the species table. Where a database has no taxonomy loaded, the summary
endpoint reports ``taxonomy_available: false`` rather than silently returning
nothing, so the UI can point the user at the taxonomy upload in Configuration.

Version: 1.0.0
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db_dependency
from app.repositories.nocturnal import NocturnalRepository
from app.schemas.analytics import (
    DuskChorusPoint,
    DawnChorusPoint,
    NocturnalSummary,
    NocturnalHourPoint,
    NocturnalNightPoint,
)
from app.services import taxonomy_groups

router = APIRouter()


def _parse_ids(raw: Optional[str]) -> Optional[List[int]]:
    if not raw:
        return None
    return [int(value.strip()) for value in raw.split(",") if value.strip()]


def _parse_groups(raw: Optional[str]) -> Optional[List[str]]:
    """Validate a comma-separated group list, ignoring unknown names."""
    if not raw:
        return None
    requested = [value.strip().lower() for value in raw.split(",") if value.strip()]
    valid = [g for g in requested if g in taxonomy_groups.GROUPS]
    return valid or None


@router.get("/groups")
async def get_groups(db: Session = Depends(get_db_dependency)):
    """
    List the nocturnal groups and how many species fall into each.

    Counts are of catalogued species, not detections, so the page can show
    "Bats (0 species)" and explain why before any chart loads.
    """
    counts = taxonomy_groups.group_counts(db)
    return {
        "taxonomy_available": taxonomy_groups.taxonomy_available(db),
        "groups": [
            {
                "group": key,
                "label": spec["label"],
                "description": spec["description"],
                "species_count": counts.get(key, 0),
            }
            for key, spec in taxonomy_groups.GROUPS.items()
        ],
    }


@router.get("/summary", response_model=NocturnalSummary)
async def get_nocturnal_summary(
    groups: Optional[str] = Query(None, description="Comma-separated group keys: bats, owls, nightjars"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db_dependency)
):
    """Per-group totals plus the species table for the Nocturnal page."""
    repo = NocturnalRepository(db)
    return repo.get_summary(
        groups=_parse_groups(groups),
        station_ids=_parse_ids(station_ids),
        months=months,
        min_confidence=min_confidence,
    )


@router.get("/hourly", response_model=List[NocturnalHourPoint])
async def get_nocturnal_hourly(
    groups: Optional[str] = Query(None, description="Comma-separated group keys"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db_dependency)
):
    """Hour-of-day activity per nocturnal species."""
    repo = NocturnalRepository(db)
    return repo.get_hourly_activity(
        groups=_parse_groups(groups),
        station_ids=_parse_ids(station_ids),
        months=months,
        min_confidence=min_confidence,
    )


@router.get("/nightly", response_model=List[NocturnalNightPoint])
async def get_nocturnal_nightly(
    groups: Optional[str] = Query(None, description="Comma-separated group keys"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db_dependency)
):
    """Detections per night per group, for the seasonal activity chart."""
    repo = NocturnalRepository(db)
    return repo.get_nightly_totals(
        groups=_parse_groups(groups),
        station_ids=_parse_ids(station_ids),
        months=months,
        min_confidence=min_confidence,
    )


@router.get("/dusk-chorus", response_model=List[DuskChorusPoint])
async def get_nocturnal_dusk_chorus(
    groups: Optional[str] = Query(None, description="Comma-separated group keys"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    window_minutes: int = Query(360, ge=30, le=360, description="Minutes before/after sunset"),
    db: Session = Depends(get_db_dependency)
):
    """
    Sunset-relative activity for nocturnal species only.

    Same shape as /analytics/dusk-chorus but restricted to bats, owls and
    nightjars, so the emergence peak is not buried under songbird counts.
    """
    repo = NocturnalRepository(db)
    return repo.get_chorus(
        phase="sunset",
        groups=_parse_groups(groups),
        station_ids=_parse_ids(station_ids),
        months=months,
        min_confidence=min_confidence,
        window_minutes=window_minutes,
    )


@router.get("/dawn-chorus", response_model=List[DawnChorusPoint])
async def get_nocturnal_dawn_chorus(
    groups: Optional[str] = Query(None, description="Comma-separated group keys"),
    station_ids: Optional[str] = Query(None, description="Comma-separated station IDs"),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    window_minutes: int = Query(360, ge=30, le=360, description="Minutes before/after sunrise"),
    db: Session = Depends(get_db_dependency)
):
    """
    Sunrise-relative activity for nocturnal species.

    The return leg: bats heading back to roost and owls falling quiet show as a
    mirror of the dusk emergence.
    """
    repo = NocturnalRepository(db)
    return repo.get_chorus(
        phase="sunrise",
        groups=_parse_groups(groups),
        station_ids=_parse_ids(station_ids),
        months=months,
        min_confidence=min_confidence,
        window_minutes=window_minutes,
    )
