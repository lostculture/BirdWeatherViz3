"""
BirdWeatherViz3 FastAPI Application
Main entry point for the API server.

Version: 1.0.0
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.version import __version__, get_version_info
from app.db.session import create_tables

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
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

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
    logger.info(f"Database URL: {settings.DATABASE_URL}")

    # Create database tables if they don't exist
    try:
        create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    Performs cleanup tasks.
    """
    logger.info(f"Shutting down {settings.APP_NAME}")


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
