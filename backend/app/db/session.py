"""
Database Session Management
Handles database connections and session lifecycle.

Version: 1.0.0
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings


# Create database engine
# For SQLite: check_same_thread=False allows usage across threads
# For PostgreSQL: pool settings for connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG  # Log SQL statements in debug mode
)


# SQLite performance optimizations
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # WAL mode for better concurrent read/write
        cursor.execute("PRAGMA journal_mode=WAL")
        # Increase cache size (negative = KB, so -64000 = 64MB)
        cursor.execute("PRAGMA cache_size=-64000")
        # Memory-mapped I/O for faster reads
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
        # Synchronous NORMAL is safe with WAL and faster
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Store temp tables in memory
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.

    Usage in FastAPI:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    Should be called on application startup.
    """
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.
    Use with caution - only for development/testing.
    """
    from app.db.base import Base
    Base.metadata.drop_all(bind=engine)
