"""
Taxonomy Translation Database Model
Per-language common name and species-group translations sourced from the
eBird multilingual taxonomy file.

Version: 1.0.0
"""

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class TaxonomyTranslation(Base):
    """Localized common name (and optional species group name) for a species."""

    __tablename__ = "taxonomy_translation"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    species_id = Column(
        Integer,
        ForeignKey("species.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to species.id",
    )
    language_code = Column(
        String(16),
        nullable=False,
        index=True,
        comment="Language code as used in the eBird taxonomy file (e.g. 'es', 'es_AR', 'de')",
    )
    common_name = Column(String(300), nullable=True)
    group_name = Column(String(300), nullable=True)

    species = relationship("Species", backref="translations")

    __table_args__ = (
        UniqueConstraint(
            "species_id", "language_code", name="uq_taxonomy_translation_species_lang"
        ),
    )

    def __repr__(self):
        return (
            f"<TaxonomyTranslation(species_id={self.species_id}, "
            f"language_code='{self.language_code}', common_name='{self.common_name}')>"
        )
