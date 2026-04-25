"""
Taxonomy Translations Service
In-memory cache of (species_id, language_code) -> (common_name, group_name)
plus a request-scoped "current language" contextvar used by response schemas
to swap English common names for the user-selected language at serialization
time. Pure display-layer — the canonical English name stays in Species.common_name.

Version: 1.0.0
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.db.models.setting import Setting
from app.db.models.species import Species
from app.db.models.taxonomy_translation import TaxonomyTranslation

logger = logging.getLogger(__name__)

TAXONOMY_LANGUAGE_KEY = "taxonomy_language"
# Language code stored in Species.common_name (eBird PRIMARY_COM_NAME is English)
PRIMARY_LANGUAGE = "en"


# species_id -> lang -> (common_name, group_name)
_translations: Dict[int, Dict[str, Tuple[Optional[str], Optional[str]]]] = {}
# common_name (lowercased, English) -> species_id, for reverse lookup (co-occurrence etc.)
_english_name_to_species_id: Dict[str, int] = {}
_available_languages: Set[str] = set()
_loaded = False
_lock = threading.Lock()

# App-wide preferred language (mirrors the taxonomy_language setting). Updated
# on startup and whenever the setting is written.
_app_language: Optional[str] = None


def load_cache(db: Session) -> None:
    """
    Populate the in-memory translation cache from the database.

    Safe to call on startup and after every taxonomy upload.
    """
    global _loaded
    with _lock:
        _translations.clear()
        _english_name_to_species_id.clear()
        _available_languages.clear()

        try:
            species_rows = db.query(Species.id, Species.common_name).all()
            for sid, cname in species_rows:
                if cname:
                    _english_name_to_species_id[cname.strip().lower()] = sid

            rows = db.query(
                TaxonomyTranslation.species_id,
                TaxonomyTranslation.language_code,
                TaxonomyTranslation.common_name,
                TaxonomyTranslation.group_name,
            ).all()

            for species_id, lang, common, group in rows:
                if not lang:
                    continue
                _available_languages.add(lang)
                bucket = _translations.setdefault(species_id, {})
                bucket[lang] = (common, group)
        except Exception as e:
            # Table may not exist yet on first boot before create_all().
            logger.warning("Could not load taxonomy translations cache: %s", e)

        _loaded = True
        logger.info(
            "Taxonomy translations cache loaded: %d species, %d languages",
            len(_translations),
            len(_available_languages),
        )


def invalidate_cache() -> None:
    """Mark cache as stale; next access will trigger a reload."""
    global _loaded
    with _lock:
        _loaded = False


def is_loaded() -> bool:
    return _loaded


def ensure_loaded(db: Session) -> None:
    if not _loaded:
        load_cache(db)


def available_languages() -> List[str]:
    return sorted(_available_languages)


def get_translation(
    species_id: int, language_code: str
) -> Optional[Tuple[Optional[str], Optional[str]]]:
    """Return (common_name, group_name) for the given species + language, or None."""
    if not species_id or not language_code or language_code == PRIMARY_LANGUAGE:
        return None
    return _translations.get(species_id, {}).get(language_code)


def translate_common_name(
    species_id: Optional[int],
    fallback: Optional[str],
    language_code: Optional[str] = None,
) -> Optional[str]:
    """
    Return the translated common name if available, otherwise `fallback`.

    Defaults to the app-wide language (`_app_language`). Pass an explicit
    language_code to override (e.g., for tests).
    """
    lang = language_code if language_code is not None else _app_language
    if not lang or lang == PRIMARY_LANGUAGE or not species_id:
        return fallback
    entry = _translations.get(species_id, {}).get(lang)
    if entry and entry[0]:
        return entry[0]
    return fallback


def translate_group_name(
    species_id: Optional[int],
    fallback: Optional[str],
    language_code: Optional[str] = None,
) -> Optional[str]:
    lang = language_code if language_code is not None else _app_language
    if not lang or lang == PRIMARY_LANGUAGE or not species_id:
        return fallback
    entry = _translations.get(species_id, {}).get(lang)
    if entry and entry[1]:
        return entry[1]
    return fallback


def species_id_for_english_common_name(name: str) -> Optional[int]:
    """Reverse lookup: English common_name -> species_id (best-effort, case-insensitive)."""
    if not name:
        return None
    return _english_name_to_species_id.get(name.strip().lower())


def set_app_language(language_code: Optional[str]) -> None:
    """Update the app-wide preferred language. Called on setting change."""
    global _app_language
    with _lock:
        if language_code:
            code = language_code.strip()
            _app_language = code if code and code != PRIMARY_LANGUAGE else None
        else:
            _app_language = None


def current_language() -> Optional[str]:
    return _app_language


def load_app_language(db: Session) -> None:
    """Read the configured taxonomy_language setting and cache it."""
    try:
        setting = db.query(Setting).filter(Setting.key == TAXONOMY_LANGUAGE_KEY).first()
        set_app_language(setting.value if setting else None)
    except Exception as e:
        logger.warning("Could not load taxonomy_language setting: %s", e)
        set_app_language(None)
