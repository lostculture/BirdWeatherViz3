"""
BirdWeatherViz3 Version Information

Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "BirdWeatherViz3 Contributors"
__description__ = "Next-generation bird detection visualization platform"
__license__ = "Proprietary"

# Version history
VERSION_HISTORY = {
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
