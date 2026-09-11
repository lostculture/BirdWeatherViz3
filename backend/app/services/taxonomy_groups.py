"""
Taxonomy Groups
Classifies species into the ecological groups the Nocturnal page reports on.

Classification uses the ``order`` and ``family`` columns where they are
populated, and falls back to the scientific name where they are not.

The fallback is not optional. The eBird taxonomy only covers birds, so every
bat arrives with ``order`` and ``family`` NULL, and a column-only classifier
finds no bats at all. BirdWeather puts the taxon name straight into
``scientific_name`` at whatever rank the detector resolved - 'Chiroptera' for
an order, 'Vespertilionidae' for a family, 'Myotis' for a genus, 'Myotis
septentrionalis' for a species - so matching the *first word* of the
scientific name against a known taxon list picks up all four shapes with one
rule.

Scientific names are matched, never common names: "Barred Owl" and "Northern
Rough-winged Swallow" are not separable by string matching in a robust way, and
a wrong guess is worse than an absent row. Genus names are unambiguous - no
bird genus collides with Myotis or Lasiurus.

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

# Bat genera. Needed because bats carry no order/family columns at all.
# Weighted towards North America and Europe, where the detectors are, but broad
# enough not to silently drop other regions.
BAT_GENERA = {
    # North America - Vespertilionidae
    "myotis", "lasiurus", "aeorestes", "dasypterus", "eptesicus",
    "lasionycteris", "perimyotis", "pipistrellus", "nycticeius",
    "corynorhinus", "antrozous", "euderma", "idionycteris", "parastrellus",
    "rhogeessa", "baeodon", "bauerus",
    # North America - Molossidae, Mormoopidae, Phyllostomidae and others
    "tadarida", "nyctinomops", "eumops", "molossus", "promops",
    "mormoops", "pteronotus", "macrotus", "choeronycteris", "leptonycteris",
    "desmodus", "diphylla", "artibeus", "sturnira", "natalus", "noctilio",
    "glossophaga", "carollia", "micronycteris", "lampronycteris",
    "balantiopteryx", "peropteryx",
    # Europe
    "nyctalus", "plecotus", "barbastella", "miniopterus", "rhinolophus",
    "hypsugo", "vespertilio",
    # Elsewhere
    "chalinolobus", "scotophilus", "scotorepens", "falsistrellus",
    "vespadelus", "mormopterus", "chaerephon", "mops", "saccolaimus",
    "taphozous", "rhinopoma", "hipposideros", "megaderma", "macroderma",
    "nycteris", "pteropus", "rousettus", "eidolon", "epomophorus",
    "cynopterus", "murina", "harpiocephalus", "kerivoula", "phoniscus",
    "nyctophilus", "otonycteris", "glauconycteris", "neoromicia",
}

# Owls.
OWL_ORDERS = {"strigiformes"}
OWL_FAMILIES = {"strigidae", "tytonidae"}
OWL_GENERA = {
    "strix", "bubo", "megascops", "asio", "tyto", "otus", "athene",
    "aegolius", "glaucidium", "surnia", "ninox", "pulsatrix", "ciccaba",
    "phodilus", "micrathene", "psiloscops", "pseudoscops", "xenoglaux",
    "margarobyas", "lophostrix", "jubula", "nesasio", "uroglaux",
    "taenioptynx", "heteroglaux",
}

# Nightjars and allies — nightjars, nighthawks, potoos, frogmouths, oilbirds.
NIGHTJAR_ORDERS = {"caprimulgiformes", "nyctibiiformes", "podargiformes",
                   "steatornithiformes", "aegotheliformes"}
NIGHTJAR_FAMILIES = {"caprimulgidae", "nyctibiidae", "podargidae",
                     "steatornithidae", "aegothelidae"}
NIGHTJAR_GENERA = {
    "caprimulgus", "antrostomus", "chordeiles", "phalaenoptilus",
    "nyctidromus", "nyctibius", "podargus", "steatornis", "aegotheles",
    "lurocalis", "nyctiphrynus", "hydropsalis", "systellura", "setopagis",
    "uropsalis", "macropsalis", "eleothreptus", "siphonorhis", "nyctipolus",
    "batrachostomus", "eurostopodus", "lyncornis", "gactornis", "veles",
}

# The groups the Nocturnal page exposes, in display order.
GROUPS = {
    "bats": {
        "label": "Bats",
        "orders": BAT_ORDERS,
        "families": BAT_FAMILIES,
        "genera": BAT_GENERA,
        "description": "Chiroptera — recorded by ultrasonic bat detectors.",
    },
    "owls": {
        "label": "Owls",
        "orders": OWL_ORDERS,
        "families": OWL_FAMILIES,
        "genera": OWL_GENERA,
        "description": "Strigiformes — Strigidae and Tytonidae.",
    },
    "nightjars": {
        "label": "Nightjars & allies",
        "orders": NIGHTJAR_ORDERS,
        "families": NIGHTJAR_FAMILIES,
        "genera": NIGHTJAR_GENERA,
        "description": "Nightjars, nighthawks, potoos and frogmouths.",
    },
}

# Every taxon name a group can be recognised by from the scientific name
# alone, at any rank. Matched against the first word, so 'Chiroptera',
# 'Vespertilionidae', 'Myotis' and 'Myotis septentrionalis' all resolve.
for _spec in GROUPS.values():
    _spec["taxa"] = _spec["orders"] | _spec["families"] | _spec["genera"]
del _spec

# Every group treated as nocturnal when no specific group is requested.
NOCTURNAL_GROUPS = ["bats", "owls", "nightjars"]


def _leading_taxon():
    """
    SQL expression for the first word of the scientific name, lowercased.

    'Myotis septentrionalis' becomes 'myotis'; a bare 'Chiroptera' or
    'Vespertilionidae' is returned whole. The trailing space appended before
    INSTR keeps single-word names working, which is the case that matters most
    here: higher-rank bat detections have no second word.
    """
    return func.lower(
        func.substr(
            Species.scientific_name,
            1,
            func.instr(Species.scientific_name + " ", " ") - 1,
        )
    )


def group_filter(group: str):
    """
    Build the SQLAlchemy filter selecting one group's species.

    Matches the order and family columns where they are populated, and the
    leading word of the scientific name otherwise. The latter is the only thing
    that finds bats, since no bird taxonomy source fills their columns in.

    Comparison is case-insensitive because taxonomy sources disagree on
    capitalisation ("Strigidae" vs "STRIGIDAE").
    """
    spec = GROUPS.get(group)
    if spec is None:
        raise ValueError(f"Unknown taxonomy group {group!r}")

    clauses = []
    if spec["orders"]:
        clauses.append(func.lower(Species.order).in_(sorted(spec["orders"])))
    if spec["families"]:
        clauses.append(func.lower(Species.family).in_(sorted(spec["families"])))
    if spec["taxa"]:
        clauses.append(_leading_taxon().in_(sorted(spec["taxa"])))
    return or_(*clauses)


def nocturnal_filter(groups: Optional[List[str]] = None):
    """Filter selecting every species in the given groups (all, by default)."""
    selected = groups or NOCTURNAL_GROUPS
    return or_(*[group_filter(g) for g in selected])


def classify(
    species_order: Optional[str],
    species_family: Optional[str],
    scientific_name: Optional[str] = None,
) -> Optional[str]:
    """
    Return the group key for a species, or None if it isn't nocturnal.

    Mirrors :func:`group_filter`: taxonomy columns first, then the leading word
    of the scientific name.
    """
    order = (species_order or "").strip().lower()
    family = (species_family or "").strip().lower()
    leading = (scientific_name or "").strip().split(" ")[0].lower()

    for key, spec in GROUPS.items():
        if order and order in spec["orders"]:
            return key
        if family and family in spec["families"]:
            return key
        if leading and leading in spec["taxa"]:
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
        .filter(
            or_(
                Species.order.isnot(None),
                Species.family.isnot(None),
                # A bats-only database has no columns filled but is still
                # classifiable from the scientific name.
                nocturnal_filter(),
            )
        )
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
