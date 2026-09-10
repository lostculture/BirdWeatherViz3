"""
Rollup Builder Service
Maintains the pre-aggregated analytics tables (see db/models/rollup.py).

The builder is incremental: it folds every detection with an id above the
stored watermark into the rollups, in bounded id-range chunks so a first build
over ten million rows never holds a single long transaction. Because detection
ids are autoincrementing, new rows always sort above the watermark even when
BirdWeather backfills older *timestamps*.

A full rebuild is available for the cases the watermark cannot cover: deleted
detections, a restored database snapshot, or a schema change to the rollups.

Version: 1.0.0
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models.rollup import CONFIDENCE_BUCKETS
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Detections folded in per transaction. Large enough that the per-chunk
# overhead is negligible, small enough to keep WAL growth and lock windows sane.
CHUNK_SIZE = 250_000

# Minutes either side of sunrise/sunset kept in the solar rollup. The API caps
# its window at 180, so building to 180 covers every supported request.
SOLAR_WINDOW_MINUTES = 180
SOLAR_BIN_MINUTES = 5

# Guards against two builds racing (scheduler + manual refresh).
_build_lock = threading.Lock()
_build_thread: Optional[threading.Thread] = None


def _bucket_columns() -> str:
    return ", ".join(f"cnt_{suffix}" for suffix, _ in CONFIDENCE_BUCKETS)


def _bucket_sums() -> str:
    return ", ".join(
        f"SUM(CASE WHEN d.confidence >= {threshold} THEN 1 ELSE 0 END)"
        for _, threshold in CONFIDENCE_BUCKETS
    )


def _bucket_conflict_updates() -> str:
    return ", ".join(
        f"cnt_{suffix} = detection_rollups.cnt_{suffix} + excluded.cnt_{suffix}"
        for suffix, _ in CONFIDENCE_BUCKETS
    )


def _solar_conflict_updates() -> str:
    return ", ".join(
        f"cnt_{suffix} = solar_rollups.cnt_{suffix} + excluded.cnt_{suffix}"
        for suffix, _ in CONFIDENCE_BUCKETS
    )


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def get_state(db: Session, name: str) -> dict:
    """Read a rollup's build state, seeding the row on first use."""
    row = db.execute(
        text("SELECT name, last_detection_id, status, rows_processed, "
             "total_rows, message, updated_at FROM rollup_state WHERE name = :n"),
        {"n": name},
    ).mappings().first()

    if row is None:
        db.execute(
            text("INSERT INTO rollup_state (name, last_detection_id, status, "
                 "rows_processed, total_rows) VALUES (:n, 0, 'idle', 0, 0)"),
            {"n": name},
        )
        db.commit()
        return {
            "name": name, "last_detection_id": 0, "status": "idle",
            "rows_processed": 0, "total_rows": 0, "message": None,
            "updated_at": None,
        }

    return dict(row)


def _set_state(db: Session, name: str, **fields) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(
        text(f"UPDATE rollup_state SET {assignments} WHERE name = :name"),
        {**fields, "name": name},
    )
    db.commit()


def get_status(db: Session) -> dict:
    """Combined status for both rollups, for the API and Config UI."""
    detection = get_state(db, "detection")
    solar = get_state(db, "solar")

    max_id = db.execute(
        text("SELECT COALESCE(MAX(id), 0) FROM detections")
    ).scalar() or 0

    behind = max(0, max_id - int(detection["last_detection_id"] or 0))

    return {
        "detection": detection,
        "solar": solar,
        "max_detection_id": max_id,
        "detections_pending": behind,
        # The charts stay correct while a build is catching up, they just show
        # a shrinking tail. Only a never-built rollup needs the raw fallback.
        "ready": int(detection["last_detection_id"] or 0) > 0 or max_id == 0,
        "building": detection["status"] == "building" or solar["status"] == "building",
    }


# ---------------------------------------------------------------------------
# Build passes
# ---------------------------------------------------------------------------

def _fold_detection_chunk(db: Session, low_id: int, high_id: int) -> None:
    """Aggregate detections in (low_id, high_id] into the hourly rollup."""
    sql = text(f"""
        INSERT INTO detection_rollups (
            station_id, species_id, detection_date, hour,
            cnt_all, {_bucket_columns()}, conf_sum, conf_max
        )
        SELECT
            d.station_id,
            d.species_id,
            d.detection_date,
            COALESCE(d.detection_hour, CAST(strftime('%H', d.timestamp) AS INTEGER)),
            COUNT(*),
            {_bucket_sums()},
            SUM(d.confidence),
            MAX(d.confidence)
        FROM detections d
        WHERE d.id > :low AND d.id <= :high
          AND d.detection_date IS NOT NULL
        GROUP BY d.station_id, d.species_id, d.detection_date,
                 COALESCE(d.detection_hour, CAST(strftime('%H', d.timestamp) AS INTEGER))
        ON CONFLICT (station_id, species_id, detection_date, hour) DO UPDATE SET
            cnt_all = detection_rollups.cnt_all + excluded.cnt_all,
            {_bucket_conflict_updates()},
            conf_sum = detection_rollups.conf_sum + excluded.conf_sum,
            conf_max = MAX(detection_rollups.conf_max, excluded.conf_max)
    """)
    db.execute(sql, {"low": low_id, "high": high_id})


def _fold_solar_chunk(db: Session, low_id: int, high_id: int) -> None:
    """
    Aggregate detections in (low_id, high_id] into the solar rollup.

    Minutes-from-event is computed entirely in SQL from the denormalised
    detection_hour/detection_minute columns and the weather table's sunrise and
    sunset times, so no detection row ever crosses into Python.

    Bins are computed with integer division on a shifted value (delta + 720 is
    always non-negative) so truncation matches floor for negative deltas too.

    Times within three hours of midnight are wrapped: a detection at 00:30 is
    treated as 30 minutes *after* a 23:50 sunset rather than 23h20m before it.
    """
    for phase in ("sunrise", "sunset"):
        sql = text(f"""
            INSERT INTO solar_rollups (
                station_id, species_id, detection_date, phase, minute_bin,
                cnt_all, {_bucket_columns()}
            )
            SELECT
                station_id, species_id, detection_date, :phase,
                (((delta + 720) / {SOLAR_BIN_MINUTES}) * {SOLAR_BIN_MINUTES}) - 720,
                COUNT(*),
                {_bucket_sums()}
            FROM (
                SELECT
                    d.station_id,
                    d.species_id,
                    d.detection_date,
                    d.confidence,
                    -- Wrap into (-720, 720] so midnight-adjacent events work.
                    (
                        ((
                            (COALESCE(d.detection_hour, CAST(strftime('%H', d.timestamp) AS INTEGER)) * 60
                             + COALESCE(d.detection_minute, CAST(strftime('%M', d.timestamp) AS INTEGER)))
                            - (CAST(strftime('%H', w.{phase}) AS INTEGER) * 60
                               + CAST(strftime('%M', w.{phase}) AS INTEGER))
                            + 1440 + 720
                        ) % 1440) - 720
                    ) AS delta
                FROM detections d
                JOIN weather w
                  ON w.station_id = d.station_id
                 AND w.weather_date = d.detection_date
                WHERE d.id > :low AND d.id <= :high
                  AND d.detection_date IS NOT NULL
                  AND w.{phase} IS NOT NULL
            ) AS d
            WHERE delta >= -{SOLAR_WINDOW_MINUTES} AND delta <= {SOLAR_WINDOW_MINUTES}
            GROUP BY station_id, species_id, detection_date,
                     (((delta + 720) / {SOLAR_BIN_MINUTES}) * {SOLAR_BIN_MINUTES}) - 720
            ON CONFLICT (station_id, species_id, detection_date, phase, minute_bin)
            DO UPDATE SET
                cnt_all = solar_rollups.cnt_all + excluded.cnt_all,
                {_solar_conflict_updates()}
        """)
        db.execute(sql, {"low": low_id, "high": high_id, "phase": phase})


def refresh(db: Session, full: bool = False, progress_cb=None) -> dict:
    """
    Bring both rollups up to date with the detections table.

    Args:
        db: Session to use. The caller keeps ownership of it.
        full: Drop and rebuild from scratch rather than resuming from the
              watermark. Needed after detections are deleted or restored.
        progress_cb: Optional callable(processed, total) for streaming UIs.

    Returns a summary dict.
    """
    started = datetime.now(timezone.utc)

    if full:
        db.execute(text("DELETE FROM detection_rollups"))
        db.execute(text("DELETE FROM solar_rollups"))
        _set_state(db, "detection", last_detection_id=0)
        _set_state(db, "solar", last_detection_id=0)
        db.commit()

    detection_state = get_state(db, "detection")
    solar_state = get_state(db, "solar")

    max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM detections")).scalar() or 0
    start_id = min(
        int(detection_state["last_detection_id"] or 0),
        int(solar_state["last_detection_id"] or 0),
    )

    if max_id <= start_id:
        _set_state(db, "detection", status="idle", message=None,
                   updated_at=started.isoformat())
        _set_state(db, "solar", status="idle", message=None,
                   updated_at=started.isoformat())
        return {"built": 0, "skipped": True, "max_detection_id": max_id}

    total = max_id - start_id
    _set_state(db, "detection", status="building", total_rows=total,
               rows_processed=0, message=None)
    _set_state(db, "solar", status="building", total_rows=total,
               rows_processed=0, message=None)

    processed = 0
    low = start_id

    try:
        while low < max_id:
            high = min(low + CHUNK_SIZE, max_id)

            # The two rollups share a watermark floor but track independently so
            # a solar failure (e.g. weather not yet synced) cannot silently roll
            # the hourly rollup backwards on the next pass.
            if high > int(detection_state["last_detection_id"] or 0):
                _fold_detection_chunk(db, low, high)
            if high > int(solar_state["last_detection_id"] or 0):
                _fold_solar_chunk(db, low, high)

            db.commit()

            processed += high - low
            low = high

            _set_state(db, "detection", last_detection_id=high,
                       rows_processed=processed)
            _set_state(db, "solar", last_detection_id=high,
                       rows_processed=processed)

            if progress_cb:
                progress_cb(processed, total)

            logger.info("Rollup build: %s/%s detections folded", processed, total)

        finished = datetime.now(timezone.utc)
        _set_state(db, "detection", status="idle", message=None,
                   updated_at=finished.isoformat())
        _set_state(db, "solar", status="idle", message=None,
                   updated_at=finished.isoformat())

        elapsed = (finished - started).total_seconds()
        logger.info("Rollup build complete: %s detections in %.1fs", processed, elapsed)

        return {
            "built": processed,
            "skipped": False,
            "max_detection_id": max_id,
            "elapsed_seconds": elapsed,
        }

    except Exception as exc:  # noqa: BLE001 - state must record any failure
        db.rollback()
        logger.error("Rollup build failed: %s", exc, exc_info=True)
        _set_state(db, "detection", status="error", message=str(exc)[:500])
        _set_state(db, "solar", status="error", message=str(exc)[:500])
        raise


def refresh_in_background(full: bool = False) -> bool:
    """
    Kick off a refresh on a worker thread.

    Returns False if a build is already running, so callers (sync completion,
    the scheduler, the manual Config button) can all fire freely.
    """
    global _build_thread

    if not _build_lock.acquire(blocking=False):
        return False

    def _run():
        db = SessionLocal()
        try:
            refresh(db, full=full)
        except Exception:  # noqa: BLE001 - already logged and recorded in state
            pass
        finally:
            db.close()
            _build_lock.release()

    _build_thread = threading.Thread(
        target=_run, name="rollup-builder", daemon=True
    )
    _build_thread.start()
    return True


def ensure_built_on_startup() -> None:
    """
    Start a background build if the rollups have never been populated.

    Called from application startup. Existing installs get their first build
    here; the app stays usable throughout because the analytics endpoints fall
    back to raw queries while ``ready`` is false.
    """
    db = SessionLocal()
    try:
        status = get_status(db)
        if status["detections_pending"] > 0 and not status["building"]:
            logger.info(
                "Rollups are %s detections behind - starting background build",
                status["detections_pending"],
            )
            refresh_in_background()
    except Exception as exc:  # noqa: BLE001 - startup must never hard-fail here
        logger.warning("Could not evaluate rollup state on startup: %s", exc)
    finally:
        db.close()
