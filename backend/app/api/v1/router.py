"""
API V1 Router
Main router that aggregates all v1 endpoint routers.

Version: 1.0.0
"""

from fastapi import APIRouter

# Import endpoint routers as they are created
from app.api.v1 import detections, species, stations

# Create main v1 router
router = APIRouter()

# Include endpoint routers
router.include_router(
    detections.router,
    prefix="/detections",
    tags=["detections"]
)

router.include_router(
    species.router,
    prefix="/species",
    tags=["species"]
)

router.include_router(
    stations.router,
    prefix="/stations",
    tags=["stations"]
)

# Health check at v1 level (in addition to root level)
@router.get("/status")
async def api_status():
    """API v1 status check."""
    return {
        "api_version": "v1",
        "status": "operational"
    }
