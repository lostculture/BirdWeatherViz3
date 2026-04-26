"""
BirdWeatherViz3 Version Information

Version: 2.1.2
"""

__version__ = "2.1.2"
__author__ = "BirdWeatherViz3 Contributors"
__description__ = "Next-generation bird detection visualization platform"
__license__ = "Proprietary"

# Version history
VERSION_HISTORY = {
    "2.1.2": "Sync hardening — force_full now auto-resumes past max_pages until BirdWeather returns empty; new detection_day_verification table tracks per-(station,date) sync history with a `verified` flag set after two consistent reads; sync uses 7-consecutive-verified-day stop in normal mode for safer catchup",
    "2.1.1": "Sync fixes — main-page Sync All now sends auth headers (was 401-ing in web mode); incremental sync no longer skips backfilled BirdWeather detections (date-cutoff replaced with consecutive-known-ID catchup window); new 'Re-sync full history' button to recover stations whose data was truncated by the old logic",
    "2.1.0": "Localized common names from eBird multilingual taxonomy (XLSX upload + per-language dropdown), database backup/restore (download + upload SQLite snapshot)",
    "2.0.0": "Native desktop app (pywebview + PyInstaller), timezone dropdown, streaming CSV upload with progress bar, shared sync state",
    "1.3.0": "Advanced Analytics page, JWT authentication, password protection, rate limiting, public deployment via Cloudflare Tunnel, iNat taxon ID lookup/caching",
    "1.2.0": "Streaming sync with progress updates, species stats fix, multi-station support improvements",
    "1.1.1": "eBird URL fix, UI improvements, filter bar enhancements",
    "1.1.0": "Weather integration, Docker deployment, performance optimizations",
    "1.0.0": "Initial release - FastAPI + React architecture with all visualizations"
}


def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_version_info() -> dict:
    """Get comprehensive version information."""
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "license": __license__
    }
