"""
Setting Database Model
Represents application settings stored in database.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.db.base import Base


class Setting(Base):
    """
    Application setting key-value store.

    Stores configurable application settings in the database
    for persistence across restarts.
    """

    __tablename__ = "settings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Setting data
    key = Column(String(100), unique=True, nullable=False, index=True,
                comment="Setting key (unique identifier)")
    value = Column(Text,
                  comment="Setting value (stored as string)")
    data_type = Column(String(20),
                      comment="Data type hint (str, int, float, bool, json)")
    description = Column(Text,
                        comment="Human-readable description of the setting")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    def __repr__(self):
        """String representation of Setting."""
        return f"<Setting(key='{self.key}', value='{self.value}')>"

    def to_dict(self):
        """Convert setting to dictionary."""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "data_type": self.data_type,
            "description": self.description,
        }

    def get_typed_value(self):
        """
        Get value converted to appropriate type based on data_type hint.

        Returns:
            Value converted to indicated type, or original string if unknown type
        """
        if self.data_type == "int":
            return int(self.value) if self.value else None
        elif self.data_type == "float":
            return float(self.value) if self.value else None
        elif self.data_type == "bool":
            return self.value.lower() in ("true", "1", "yes") if self.value else False
        elif self.data_type == "json":
            import json
            return json.loads(self.value) if self.value else None
        else:
            return self.value
