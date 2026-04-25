"""
Localization helpers for response schemas.

Shared Pydantic v2 model validators that swap English common/group names for
the user-selected language at serialization time. Stores the original English
name in `english_name` (when the field is present on the schema) so URL and
image lookups can still rely on the canonical English string.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Optional

from app.services import taxonomy_translations as _tx


def _resolve_species_id(obj: Any) -> Optional[int]:
    """Find a DB-PK species id on the object via the usual field names."""
    for attr in ("id", "species_id"):
        val = getattr(obj, attr, None)
        if isinstance(val, int) and val > 0:
            return val
    sci = getattr(obj, "scientific_name", None)
    if isinstance(sci, str) and sci:
        # Fallback — currently unsupported without a scientific_name index.
        return None
    return None


def localize_common_name(obj: Any) -> Any:
    """
    Swap `obj.common_name` to the translated version for the app's current
    language. When `english_name` exists on the schema and is unset, store the
    original English name there for downstream URL/image generation.
    """
    lang = _tx.current_language()
    if not lang:
        return obj
    current = getattr(obj, "common_name", None)
    if not current:
        return obj
    sid = _resolve_species_id(obj)
    if not sid:
        sid = _tx.species_id_for_english_common_name(current)
    translated = _tx.translate_common_name(sid, None, language_code=lang)
    if not translated or translated == current:
        return obj
    if hasattr(obj, "english_name") and not getattr(obj, "english_name", None):
        obj.english_name = current
    obj.common_name = translated
    return obj


def localize_species_common_name(obj: Any) -> Any:
    """
    Variant of `localize_common_name` for schemas that use `species_common_name`
    (MonthlyChampion, SpeciesConfidenceScatter in species.py).
    """
    lang = _tx.current_language()
    if not lang:
        return obj
    current = getattr(obj, "species_common_name", None)
    if not current:
        return obj
    sid = _resolve_species_id(obj)
    if not sid:
        sid = _tx.species_id_for_english_common_name(current)
    translated = _tx.translate_common_name(sid, None, language_code=lang)
    if not translated or translated == current:
        return obj
    obj.species_common_name = translated
    return obj


def localize_species_pair(obj: Any) -> Any:
    """
    For CoOccurrenceCell — `species_1` and `species_2` are English common
    names. Reverse-lookup each to species_id, then translate. Best-effort:
    unresolved names pass through unchanged.
    """
    lang = _tx.current_language()
    if not lang:
        return obj
    for attr in ("species_1", "species_2"):
        current = getattr(obj, attr, None)
        if not current:
            continue
        sid = _tx.species_id_for_english_common_name(current)
        translated = _tx.translate_common_name(sid, None, language_code=lang)
        if translated and translated != current:
            setattr(obj, attr, translated)
    return obj
