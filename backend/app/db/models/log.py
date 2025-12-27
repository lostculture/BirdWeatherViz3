"""
Log Database Model
Represents application log entries.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from app.db.base import Base


class Log(Base):
    """
    Application log entry.

    Stores application events, errors, and informational messages
    for debugging and auditing purposes.
    """

    __tablename__ = "logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Log metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True,
                      comment="Log entry timestamp")
    level = Column(String(10), nullable=False, index=True,
                  comment="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    category = Column(String(50), index=True,
                     comment="Log category (API, UPDATE, NOTIFICATION, DATABASE, etc.)")
    message = Column(Text, nullable=False,
                    comment="Log message")
    details = Column(JSON,
                    comment="Additional structured log data (JSON)")

    # Optional references
    station_id = Column(Integer, ForeignKey("stations.id"),
                       comment="Related station ID (if applicable)")

    def __repr__(self):
        """String representation of Log."""
        return f"<Log(id={self.id}, level='{self.level}', category='{self.category}', timestamp={self.timestamp})>"

    def to_dict(self):
        """Convert log to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "station_id": self.station_id,
        }
