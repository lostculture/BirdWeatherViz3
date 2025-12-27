"""
ImageCache Database Model
Represents cached Wikimedia bird images.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ImageCache(Base):
    """
    Cached bird species image from Wikimedia Commons.

    Stores downloaded bird images to reduce API calls to Wikimedia
    and improve performance.
    """

    __tablename__ = "image_cache"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key
    species_id = Column(Integer, ForeignKey("species.id"), unique=True, nullable=False,
                       comment="Species ID (one image per species)")

    # Wikimedia data
    page_url = Column(String(500),
                     comment="Wikipedia page URL")
    thumbnail_url = Column(String(500),
                          comment="Wikimedia thumbnail URL")
    image_data = Column(LargeBinary,
                       comment="Actual image bytes (for offline access)")

    # Image metadata
    attribution = Column(String(500),
                        comment="Image attribution/credit")
    license = Column(String(100),
                    comment="Image license (e.g., CC BY-SA 4.0)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                       comment="Record last update timestamp")

    # Relationships
    species = relationship("Species", back_populates="image_cache")

    def __repr__(self):
        """String representation of ImageCache."""
        return f"<ImageCache(id={self.id}, species_id={self.species_id})>"

    def to_dict(self, include_image_data=False):
        """
        Convert image cache to dictionary.

        Args:
            include_image_data: Whether to include binary image data (default: False for size)
        """
        data = {
            "id": self.id,
            "species_id": self.species_id,
            "page_url": self.page_url,
            "thumbnail_url": self.thumbnail_url,
            "attribution": self.attribution,
            "license": self.license,
        }

        if include_image_data and self.image_data:
            import base64
            data["image_data_base64"] = base64.b64encode(self.image_data).decode('utf-8')

        return data
