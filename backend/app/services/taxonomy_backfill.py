"""
Taxonomy Backfill Service
Fills in ``order`` and ``family`` for species the eBird taxonomy cannot cover.

The eBird taxonomy is birds only, so bats, insects and anything else arrive
with both columns NULL. That is invisible on most pages but breaks the
Nocturnal page outright, which groups species by taxonomy — a database full of
bat detections reported zero bats.

This service walks the species that are missing taxonomy and asks iNaturalist,
which covers all life. It also fills ``inat_taxon_id`` while it is there, since
that is the same lookup the species page already caches one at a time.

The run is manual: it makes outbound API calls, so it happens when the user
asks for it in Configuration rather than silently on startup. Progress is kept
in the settings table so the UI can poll it and a restart does not lose it.

Version: 1.0.0
"""

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models.setting import Setting
from app.db.models.species import Species
from app.db.session import SessionLocal
from app.services.inaturalist import TaxonomyResolver, is_resolvable

logger = logging.getLogger(__name__)

STATE_KEY = "inat_taxonomy_backfill_state"

# Names that could not be resolved, kept for the UI. Capped so the settings row
# cannot grow without bound on a database full of unresolvable placeholders.
MAX_REPORTED_FAILURES = 50

_run_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict:
    return {
        "status": "idle",          # idle | running | error
        "processed": 0,
        "total": 0,
        "updated": 0,
        "unresolved": 0,
        "skipped": 0,
        "failures": [],
        "message": None,
        "started_at": None,
        "finished_at": None,
    }


def get_state(db: Session) -> dict:
    """Read the backfill state, seeding it on first use."""
    row = db.query(Setting).filter(Setting.key == STATE_KEY).first()
    if row is None or not row.value:
        return _default_state()
    try:
        state = json.loads(row.value)
    except ValueError:
        return _default_state()
    # Merge over the defaults so a state written by an older version still
    # has every key the UI expects.
    merged = _default_state()
    merged.update(state)
    return merged


def _save_state(db: Session, state: dict) -> None:
    row = db.query(Setting).filter(Setting.key == STATE_KEY).first()
    payload = json.dumps(state)
    if row is None:
        db.add(Setting(
            key=STATE_KEY,
            value=payload,
            data_type="json",
            description="Progress of the iNaturalist taxonomy backfill",
        ))
    else:
        row.value = payload
    db.commit()


def count_missing(db: Session, detected_only: bool = True) -> int:
    """How many species are missing order or family."""
    return _missing_query(db, detected_only).count()


def _missing_query(db: Session, detected_only: bool):
    query = db.query(Species).filter(
        or_(Species.order.is_(None), Species.family.is_(None))
    )
    if detected_only:
        # Species with no detections are catalogue padding — thousands of them
        # in a full eBird import. Resolving those would be a very long run for
        # no visible benefit.
        query = query.filter(Species.total_detections > 0)
    return query.order_by(Species.total_detections.desc())


def run_backfill(
    db: Session,
    detected_only: bool = True,
    limit: Optional[int] = None,
    min_interval: Optional[float] = None,
) -> dict:
    """
    Resolve missing taxonomy from iNaturalist.

    Args:
        db: Session to use; the caller keeps ownership.
        detected_only: Only species with at least one detection (the default).
        limit: Stop after this many species. None means all of them.
        min_interval: Override the per-request delay. For tests only — the
            default respects iNaturalist's rate guidance.

    Returns the final state dict.
    """
    species = _missing_query(db, detected_only).all()
    if limit is not None:
        species = species[:limit]

    state = _default_state()
    state.update({
        "status": "running",
        "total": len(species),
        "started_at": _now(),
    })
    _save_state(db, state)

    if not species:
        state.update({"status": "idle", "finished_at": _now(),
                      "message": "Nothing to do — all species have taxonomy."})
        _save_state(db, state)
        return state

    resolver_kwargs = {} if min_interval is None else {"min_interval": min_interval}

    try:
        with TaxonomyResolver(**resolver_kwargs) as resolver:
            for index, sp in enumerate(species, start=1):
                if not is_resolvable(sp.scientific_name):
                    state["skipped"] += 1
                else:
                    taxonomy = resolver.taxonomy_for(sp.scientific_name)
                    if taxonomy is None:
                        state["unresolved"] += 1
                        if len(state["failures"]) < MAX_REPORTED_FAILURES:
                            state["failures"].append(sp.scientific_name)
                    else:
                        changed = False
                        # Never overwrite taxonomy that is already there: the
                        # eBird import is authoritative for birds.
                        if not sp.order and taxonomy["order"]:
                            sp.order = taxonomy["order"]
                            changed = True
                        if not sp.family and taxonomy["family"]:
                            sp.family = taxonomy["family"]
                            changed = True
                        if not sp.inat_taxon_id and taxonomy["taxon_id"]:
                            sp.inat_taxon_id = taxonomy["taxon_id"]
                            changed = True
                        if changed:
                            state["updated"] += 1
                        else:
                            state["unresolved"] += 1

                state["processed"] = index

                # Commit periodically so a long run is not lost to a restart,
                # and the UI's progress poll sees movement.
                if index % 10 == 0 or index == len(species):
                    db.commit()
                    _save_state(db, state)

        state.update({"status": "idle", "finished_at": _now()})
        state["message"] = (
            f"Updated {state['updated']} species; "
            f"{state['unresolved']} not found, {state['skipped']} skipped."
        )
        db.commit()
        _save_state(db, state)
        logger.info("Taxonomy backfill complete: %s", state["message"])
        return state

    except Exception as exc:  # noqa: BLE001 - the state must record any failure
        db.rollback()
        logger.error("Taxonomy backfill failed: %s", exc, exc_info=True)
        state.update({
            "status": "error",
            "message": str(exc)[:500],
            "finished_at": _now(),
        })
        _save_state(db, state)
        raise


def run_in_background(detected_only: bool = True, limit: Optional[int] = None) -> bool:
    """
    Start a backfill on a worker thread.

    Returns False if one is already running, so the UI can say so rather than
    starting a second run against the same rows.
    """
    if not _run_lock.acquire(blocking=False):
        return False

    def _run():
        db = SessionLocal()
        try:
            run_backfill(db, detected_only=detected_only, limit=limit)
        except Exception:  # noqa: BLE001 - already logged and recorded
            pass
        finally:
            db.close()
            _run_lock.release()

    threading.Thread(target=_run, name="taxonomy-backfill", daemon=True).start()
    return True
