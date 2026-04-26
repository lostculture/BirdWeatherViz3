"""
System info + update-check endpoints.

`/system/info` is the single source the frontend reads to learn the running
backend version, schema version, and deployment mode. Public — the layout
needs it before login.

`/system/update-info` polls GitHub releases for the latest tag, caches the
answer in-process for 6 hours so we stay well under GitHub's anonymous
60-req/hr limit, and reports whether an update is available compared to
the running `__version__`. Public, opt-out via the `update_check_enabled`
setting.
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db_dependency
from app.config import settings as app_settings
from app.db.models.setting import Setting
from app.version import __version__

logger = logging.getLogger(__name__)
router = APIRouter()

# Settings keys
SCHEMA_VERSION_KEY = "schema_version"
UPDATE_CHECK_ENABLED_KEY = "update_check_enabled"

# Schema version starts at 1. Increment when a non-additive schema change
# ships (e.g. column rename, drop, type change). Pure new-table additions
# do not require a bump because `create_all()` handles them transparently.
CURRENT_SCHEMA_VERSION = "1"

# GitHub releases — anonymous 60 req/hr per IP. Cache aggressively.
GITHUB_LATEST_URL = "https://api.github.com/repos/lostculture/BirdWeatherViz3/releases/latest"
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours

_cache_lock = threading.Lock()
_cache: dict[str, object] = {}  # {fetched_at: float, payload: dict}


class SystemInfoResponse(BaseModel):
    version: str
    schema_version: str
    mode: str  # "web" or "desktop"
    platform: str  # "linux", "darwin", "windows"
    python_version: str


class UpdateInfoResponse(BaseModel):
    current: str
    latest: Optional[str]
    update_available: bool
    release_url: Optional[str]
    published_at: Optional[str]
    body: Optional[str]
    enabled: bool
    error: Optional[str] = None  # populated when GitHub fetch failed


def _read_schema_version(db: Session) -> str:
    setting = db.query(Setting).filter(Setting.key == SCHEMA_VERSION_KEY).first()
    return setting.value if setting and setting.value else CURRENT_SCHEMA_VERSION


def _update_check_enabled(db: Session) -> bool:
    setting = db.query(Setting).filter(Setting.key == UPDATE_CHECK_ENABLED_KEY).first()
    if not setting or not setting.value:
        return True
    return setting.value.strip().lower() in ("true", "1", "yes")


def _normalise_tag(tag: Optional[str]) -> Optional[str]:
    if not tag:
        return None
    return tag.lstrip("v")


def _is_newer(latest: Optional[str], current: str) -> bool:
    """Strict semver-ish compare. Returns True iff `latest` > `current`."""
    if not latest:
        return False

    def parts(v: str) -> tuple:
        # Drop pre-release suffix for ordering simplicity
        head = v.split("-", 1)[0]
        try:
            return tuple(int(x) for x in head.split("."))
        except ValueError:
            return ()

    a, b = parts(latest), parts(current)
    return bool(a and b and a > b)


def _fetch_latest_release(timeout_seconds: float = 4.0) -> dict:
    """Hit GitHub for the latest release. Raises on network/HTTP error."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"BirdWeatherViz3/{__version__} (update-check)",
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.get(GITHUB_LATEST_URL, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _cached_release(force_refresh: bool = False) -> tuple[Optional[dict], Optional[str]]:
    """Return (payload, error). At most one entry, refreshed every 6 hours."""
    now = time.time()
    with _cache_lock:
        if not force_refresh:
            fetched_at = _cache.get("fetched_at", 0)
            if isinstance(fetched_at, (int, float)) and (now - fetched_at) < CACHE_TTL_SECONDS:
                payload = _cache.get("payload")
                error = _cache.get("error")
                if isinstance(payload, dict) or isinstance(error, str):
                    return (payload if isinstance(payload, dict) else None,
                            error if isinstance(error, str) else None)

        try:
            payload = _fetch_latest_release()
            _cache.update({"fetched_at": now, "payload": payload, "error": None})
            return payload, None
        except Exception as e:  # noqa: BLE001 — broad catch is intentional, we surface the message
            err = f"{type(e).__name__}: {e}"
            logger.warning("Update check failed: %s", err)
            # Cache the failure too, but with a shorter TTL feel by leaving fetched_at
            # at the current time so we don't hammer GitHub on errors.
            _cache.update({"fetched_at": now, "payload": None, "error": err})
            return None, err


def ensure_schema_version_seeded(db: Session) -> None:
    """Idempotent on-startup hook: seed schema_version row if missing."""
    setting = db.query(Setting).filter(Setting.key == SCHEMA_VERSION_KEY).first()
    if setting is None:
        db.add(Setting(
            key=SCHEMA_VERSION_KEY,
            value=CURRENT_SCHEMA_VERSION,
            data_type="str",
            description="Database schema version. Incremented when a non-additive "
                        "schema change ships (column rename, drop, type change).",
        ))
        db.commit()
        logger.info("Seeded %s=%s", SCHEMA_VERSION_KEY, CURRENT_SCHEMA_VERSION)


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(db: Session = Depends(get_db_dependency)):
    """Public — used by the frontend for the running version + mode."""
    return SystemInfoResponse(
        version=__version__,
        schema_version=_read_schema_version(db),
        mode=app_settings.BWV_MODE,
        platform=platform.system().lower(),
        python_version=platform.python_version(),
    )


@router.get("/update-info", response_model=UpdateInfoResponse)
async def get_update_info(
    refresh: bool = False,
    db: Session = Depends(get_db_dependency),
):
    """
    Compare the running version to the latest GitHub release.

    `refresh=true` bypasses the in-process cache (debug / "check now" button).
    Returns `enabled: false` and skips the network call if the user has
    opted out via the `update_check_enabled` setting.
    """
    enabled = _update_check_enabled(db)
    if not enabled:
        return UpdateInfoResponse(
            current=__version__, latest=None, update_available=False,
            release_url=None, published_at=None, body=None,
            enabled=False, error=None,
        )

    payload, error = _cached_release(force_refresh=refresh)
    if payload is None:
        return UpdateInfoResponse(
            current=__version__, latest=None, update_available=False,
            release_url=None, published_at=None, body=None,
            enabled=True, error=error,
        )

    latest_tag = payload.get("tag_name") if isinstance(payload, dict) else None
    latest = _normalise_tag(latest_tag if isinstance(latest_tag, str) else None)
    return UpdateInfoResponse(
        current=__version__,
        latest=latest,
        update_available=_is_newer(latest, __version__),
        release_url=payload.get("html_url") if isinstance(payload.get("html_url"), str) else None,
        published_at=payload.get("published_at") if isinstance(payload.get("published_at"), str) else None,
        body=payload.get("body") if isinstance(payload.get("body"), str) else None,
        enabled=True,
        error=None,
    )
