"""
BirdWeatherViz3 Version Information

Version: 1.1.1
"""

__version__ = "1.1.1"
__author__ = "BirdWeatherViz3 Contributors"
__description__ = "Next-generation bird detection visualization platform"
__license__ = "Proprietary"

# Version history
VERSION_HISTORY = {
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
