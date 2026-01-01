"""
Species Database Model
Represents a bird species with taxonomy and cached statistics.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Species(Base):
    """
    Bird species catalog.

    Stores bird species information including taxonomy,
    identification codes, and cached detection statistics.
    """

    __tablename__ = "species"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # BirdWeather data
    species_id = Column(Integer, unique=True, nullable=True, index=True,
                       comment="BirdWeather species ID (null for manual imports)")
    common_name = Column(String(200), nullable=False, index=True,
                        comment="Common name of the species")
    scientific_name = Column(String(200), nullable=False, unique=True, index=True,
                            comment="Scientific (Latin) name of the species")

    # Taxonomy
    family = Column(String(200), index=True,
                   comment="Bird family (e.g., Turdidae)")
    order = Column(String(200),
                  comment="Bird order (e.g., Passeriformes)")

    # External integrations
    ebird_code = Column(String(10), index=True,
                       comment="eBird species code (4-6 characters)")

    # Cached statistics (updated periodically)
    total_detections = Column(Integer, default=0,
                             comment="Total number of detections (cached)")
    first_seen = Column(DateTime(timezone=True),
                       comment="First detection timestamp (cached)")
    last_seen = Column(DateTime(timezone=True),
                      comment="Last detection timestamp (cached)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Relationships
    detections = relationship("Detection", back_populates="species", cascade="all, delete-orphan")
    image_cache = relationship("ImageCache", back_populates="species", uselist=False,
                              cascade="all, delete-orphan")

    def __repr__(self):
        """String representation of Species."""
        return f"<Species(id={self.id}, common_name='{self.common_name}', scientific_name='{self.scientific_name}')>"

    def to_dict(self):
        """Convert species to dictionary."""
        return {
            "id": self.id,
            "species_id": self.species_id,
            "common_name": self.common_name,
            "scientific_name": self.scientific_name,
            "family": self.family,
            "order": self.order,
            "ebird_code": self.ebird_code,
            "total_detections": self.total_detections,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
