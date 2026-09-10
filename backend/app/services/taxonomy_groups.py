"""
Taxonomy Groups
Classifies species into the ecological groups the Nocturnal page reports on.

Classification is driven entirely by the ``order`` and ``family`` columns on
the species table, which are populated by the eBird taxonomy upload in
Configuration. Nothing here guesses from common names: "Barred Owl" and
"Northern Rough-winged Swallow" are not separable by string matching in a
robust way, and a wrong guess is worse than an absent row.

If a station's species rows have no taxonomy the Nocturnal page will be empty
and the API reports ``taxonomy_available: false`` so the UI can point the user
at the eBird taxonomy upload rather than showing a bare "no data" panel.

Version: 1.0.0
"""

from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models.species import Species


# Bats. Chiroptera covers every bat family, but families are listed too because
# some taxonomy sources populate family without order.
BAT_ORDERS = {"chiroptera"}
BAT_FAMILIES = {
    "vespertilionidae",   # evening bats — the bulk of temperate detections
    "molossidae",         # free-tailed bats
    "rhinolophidae",      # horseshoe bats
    "hipposideridae",
    "phyllostomidae",
    "emballonuridae",
    "mormoopidae",
    "natalidae",
    "noctilionidae",
    "nycteridae",
    "megadermatidae",
    "craseonycteridae",
    "furipteridae",
    "thyropteridae",
    "myzopodidae",
    "mystacinidae",
    "miniopteridae",
    "cistugidae",
    "pteropodidae",
    "rhinopomatidae",
    "rhinonycteridae",
}

# Owls.
OWL_ORDERS = {"strigiformes"}
OWL_FAMILIES = {"strigidae", "tytonidae"}

# Nightjars and allies — nightjars, nighthawks, potoos, frogmouths, oilbirds.
NIGHTJAR_ORDERS = {"caprimulgiformes", "nyctibiiformes", "podargiformes",
                   "steatornithiformes", "aegotheliformes"}
NIGHTJAR_FAMILIES = {"caprimulgidae", "nyctibiidae", "podargidae",
                     "steatornithidae", "aegothelidae"}

# The groups the Nocturnal page exposes, in display order.
GROUPS = {
    "bats": {
        "label": "Bats",
        "orders": BAT_ORDERS,
        "families": BAT_FAMILIES,
        "description": "Chiroptera — recorded by ultrasonic bat detectors.",
    },
    "owls": {
        "label": "Owls",
        "orders": OWL_ORDERS,
        "families": OWL_FAMILIES,
        "description": "Strigiformes — Strigidae and Tytonidae.",
    },
    "nightjars": {
        "label": "Nightjars & allies",
        "orders": NIGHTJAR_ORDERS,
        "families": NIGHTJAR_FAMILIES,
        "description": "Nightjars, nighthawks, potoos and frogmouths.",
    },
}

# Every group treated as nocturnal when no specific group is requested.
NOCTURNAL_GROUPS = ["bats", "owls", "nightjars"]


def group_filter(group: str):
    """
    Build the SQLAlchemy filter selecting one group's species.

    Comparison is case-insensitive because taxonomy sources disagree on
    capitalisation ("Strigidae" vs "STRIGIDAE").
    """
    spec = GROUPS.get(group)
    if spec is None:
        raise ValueError(f"Unknown taxonomy group {group!r}")

    clauses = []
    if spec["orders"]:
        clauses.append(func.lower(Species.order).in_(spec["orders"]))
    if spec["families"]:
        clauses.append(func.lower(Species.family).in_(spec["families"]))
    return or_(*clauses)


def nocturnal_filter(groups: Optional[List[str]] = None):
    """Filter selecting every species in the given groups (all, by default)."""
    selected = groups or NOCTURNAL_GROUPS
    return or_(*[group_filter(g) for g in selected])


def classify(species_order: Optional[str], species_family: Optional[str]) -> Optional[str]:
    """Return the group key for a species, or None if it isn't nocturnal."""
    order = (species_order or "").strip().lower()
    family = (species_family or "").strip().lower()

    for key, spec in GROUPS.items():
        if order and order in spec["orders"]:
            return key
        if family and family in spec["families"]:
            return key
    return None


def taxonomy_available(db: Session) -> bool:
    """
    Whether any species carries taxonomy at all.

    Used to distinguish "you have no bats or owls" from "taxonomy has never
    been loaded, so we cannot tell".
    """
    return db.query(
        db.query(Species)
        .filter(or_(Species.order.isnot(None), Species.family.isnot(None)))
        .exists()
    ).scalar() or False


def group_counts(db: Session) -> dict:
    """Species count per group, for the Nocturnal page header."""
    counts = {}
    for key in GROUPS:
        counts[key] = (
            db.query(func.count(Species.id))
            .filter(group_filter(key))
            .scalar() or 0
        )
    return counts
