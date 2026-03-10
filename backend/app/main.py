"""
BirdWeatherViz3 FastAPI Application
Main entry point for the API server.

Version: 1.0.0
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.config import settings
from app.version import __version__, get_version_info
from app.db.session import create_tables
from app.core.rate_limit import limiter
from app.scheduler import start_scheduler, stop_scheduler, get_scheduler_status

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description="Next-generation bird detection visualization platform",
    docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    Initializes database tables and performs setup tasks.
    """
    logger.info(f"Starting {settings.APP_NAME} v{__version__}")
    # Log database type only, not the full URL (may contain credentials)
    db_type = settings.DATABASE_URL.split("://")[0] if "://" in settings.DATABASE_URL else "unknown"
    logger.info(f"Database type: {db_type}")

    # Create database tables if they don't exist
    try:
        create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

    # Start background scheduler for automatic station updates
    try:
        start_scheduler()
        logger.info("Background scheduler initialized")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        # Don't raise - app can run without scheduler

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    Performs cleanup tasks.
    """
    logger.info(f"Shutting down {settings.APP_NAME}")
    stop_scheduler()


@app.get("/")
async def root():
    """
    Root endpoint.
    Returns basic application information.
    """
    return {
        "name": settings.APP_NAME,
        "version": __version__,
        "status": "running",
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }


@app.get(f"{settings.API_V1_PREFIX}/health")
async def health_check():
    """
    Health check endpoint.
    Returns application health status and version information.
    """
    from app.db.session import engine
    from sqlalchemy import text

    # Check database connection
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"Database health check failed: {e}")

    return JSONResponse(
        status_code=200 if db_status == "connected" else 503,
        content={
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "version": __version__,
            "database": db_status,
            "auto_update_enabled": settings.AUTO_UPDATE_ENABLED,
            "scheduler": get_scheduler_status(),
        }
    )


@app.get(f"{settings.API_V1_PREFIX}/version")
async def version():
    """
    Version information endpoint.
    Returns detailed version information.
    """
    return get_version_info()


# Import and include API routers
from app.api.v1 import router as api_v1_router

app.include_router(api_v1_router.router, prefix=settings.API_V1_PREFIX)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
