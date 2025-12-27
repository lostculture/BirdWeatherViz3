"""
Notification Database Model
Represents Apprise notification configuration.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.db.base import Base


class Notification(Base):
    """
    Notification configuration using Apprise.

    Stores notification service URLs and trigger settings for
    various events (new species, summaries, errors).
    """

    __tablename__ = "notifications"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Notification config
    name = Column(String(200), nullable=False,
                 comment="Notification service name")
    apprise_url = Column(String(500), nullable=False,
                        comment="Apprise URL (encrypted, e.g., mailto://user:pass@domain)")

    # Trigger settings
    notify_new_species = Column(Boolean, default=True,
                               comment="Send notification when new species detected")
    notify_daily_summary = Column(Boolean, default=False,
                                 comment="Send daily detection summary")
    notify_weekly_summary = Column(Boolean, default=False,
                                  comment="Send weekly detection summary")
    notify_errors = Column(Boolean, default=True,
                          comment="Send notification on errors/failures")

    # Filters
    station_ids = Column(JSON,
                        comment="List of station IDs to monitor (null = all stations)")

    # Status
    active = Column(Boolean, default=True,
                   comment="Enable/disable this notification")
    last_sent = Column(DateTime(timezone=True),
                      comment="Last notification sent timestamp")
    send_count = Column(Integer, default=0,
                       comment="Total number of notifications sent")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    def __repr__(self):
        """String representation of Notification."""
        return f"<Notification(id={self.id}, name='{self.name}', active={self.active})>"

    def to_dict(self, include_url=False):
        """
        Convert notification to dictionary.

        Args:
            include_url: Whether to include the Apprise URL (default: False for security)
        """
        data = {
            "id": self.id,
            "name": self.name,
            "notify_new_species": self.notify_new_species,
            "notify_daily_summary": self.notify_daily_summary,
            "notify_weekly_summary": self.notify_weekly_summary,
            "notify_errors": self.notify_errors,
            "station_ids": self.station_ids,
            "active": self.active,
            "last_sent": self.last_sent.isoformat() if self.last_sent else None,
            "send_count": self.send_count,
        }

        if include_url:
            data["apprise_url"] = self.apprise_url
        else:
            # Mask URL for display
            if self.apprise_url:
                data["apprise_url_masked"] = f"{self.apprise_url[:10]}...{self.apprise_url[-4:]}"

        return data
