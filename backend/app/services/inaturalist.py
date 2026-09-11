"""
iNaturalist Integration Service
Fetches taxon IDs and taxonomy (order/family) from the iNaturalist API.

iNaturalist covers all life, which is why it backs the taxonomy backfill: the
eBird taxonomy only has birds, so bats, insects and everything else arrive with
``order`` and ``family`` NULL. See services/taxonomy_backfill.py.

API notes, learned from the live API rather than the docs:

* ``/v1/taxa?q=<name>`` returns ``ancestor_ids`` but *not* ``ancestors``, so the
  rank and name of each ancestor need a second lookup.
* ``/v1/taxa/<id>,<id>,...`` resolves up to 30 ids in one request, and the same
  order/family ids repeat across every species in a group, so a cache makes the
  ancestor lookups almost free after the first few species.
* No rank filter is used when searching. BirdWeather reports higher-rank hits
  ("Chiroptera", "Vespertilionidae"), and ``rank=species`` silently drops them.

Version: 2.0.0
"""

import logging
import threading
import time
import httpx
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote_plus

from app.version import __version__

logger = logging.getLogger(__name__)

INAT_API = "https://api.inaturalist.org/v1"

# iNaturalist asks for a descriptive User-Agent so they can contact the author
# of a misbehaving client.
USER_AGENT = (
    f"BirdWeatherViz3/{__version__} "
    "(+https://github.com/lostculture/BirdWeatherViz3)"
)

# iNaturalist allows 100 requests/minute and asks that sustained use stay well
# under it. One request per second keeps us comfortably inside that.
MIN_REQUEST_INTERVAL = 1.1

# Ids per batched ancestor lookup. The API caps this at 30.
ANCESTOR_BATCH = 30

# Scientific names that cannot be looked up: slashes are "either species",
# "sp." is an unidentified genus, brackets are subspecies groups, " x " is a
# hybrid. Searching these returns confident nonsense, so skip them.
UNRESOLVABLE_MARKERS = ("/", " sp.", "[", " x ", "(hybrid)")


def is_resolvable(scientific_name: Optional[str]) -> bool:
    """Whether a scientific name is worth sending to iNaturalist at all."""
    if not scientific_name or not scientific_name.strip():
        return False
    lowered = scientific_name.lower()
    return not any(marker in lowered for marker in UNRESOLVABLE_MARKERS)


async def fetch_inat_taxon_id(scientific_name: str) -> Optional[int]:
    """
    Fetch taxon ID from iNaturalist API.

    Args:
        scientific_name: Scientific name like "Corvus brachyrhynchos"

    Returns:
        Taxon ID if found, None otherwise
    """
    try:
        url = f"https://api.inaturalist.org/v1/taxa?q={quote_plus(scientific_name)}&rank=species"
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    # Find exact match on scientific name
                    for result in data['results']:
                        if result.get('name', '').lower() == scientific_name.lower():
                            return result.get('id')
                    # If no exact match, return first result
                    return data['results'][0].get('id')
    except Exception as e:
        print(f"Error fetching iNat taxon ID for {scientific_name}: {e}")
    return None


class TaxonomyResolver:
    """
    Resolves scientific names to iNaturalist taxon ids plus order and family.

    Holds an ancestor cache for its lifetime, so a run over a few thousand
    species issues roughly one request per species plus a handful of batched
    ancestor lookups. Not thread-safe by design: create one per backfill run.
    """

    def __init__(self, min_interval: float = MIN_REQUEST_INTERVAL, timeout: float = 15.0):
        self._client = httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT}
        )
        self._min_interval = min_interval
        self._last_request = 0.0
        # taxon id -> (rank, name)
        self._ancestors: Dict[int, Tuple[str, str]] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    def _get(self, url: str) -> Optional[dict]:
        self._throttle()
        try:
            response = self._client.get(url)
        except Exception as exc:  # noqa: BLE001 - network errors are expected
            logger.warning("iNat request failed (%s): %s", url, exc)
            return None

        if response.status_code == 429:
            # Backing off once is enough at our request rate; a second 429
            # means something else is using the quota, so give up this item.
            logger.warning("iNat rate limited; backing off")
            time.sleep(60)
            return None
        if response.status_code != 200:
            logger.warning("iNat returned %s for %s", response.status_code, url)
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def search(self, scientific_name: str) -> Optional[dict]:
        """Find the taxon record best matching a scientific name."""
        data = self._get(f"{INAT_API}/taxa?q={quote_plus(scientific_name)}&per_page=5")
        results = (data or {}).get("results") or []
        if not results:
            return None

        # Prefer an exact name match; the search is fuzzy and will happily
        # return a congener when the exact taxon exists.
        target = scientific_name.strip().lower()
        for result in results:
            if (result.get("name") or "").lower() == target:
                return result
        return results[0]

    def _cache_ancestors(self, ids: Iterable[int]) -> None:
        unknown = [i for i in dict.fromkeys(ids) if i not in self._ancestors]
        for start in range(0, len(unknown), ANCESTOR_BATCH):
            batch = unknown[start:start + ANCESTOR_BATCH]
            joined = ",".join(str(i) for i in batch)
            data = self._get(f"{INAT_API}/taxa/{joined}")
            for result in (data or {}).get("results") or []:
                taxon_id = result.get("id")
                rank = result.get("rank")
                name = result.get("name")
                if taxon_id is not None and rank and name:
                    self._ancestors[taxon_id] = (rank, name)

    def taxonomy_for(self, scientific_name: str) -> Optional[dict]:
        """
        Resolve a scientific name to ``{taxon_id, rank, order, family}``.

        ``order`` and ``family`` come from the ancestor chain, or from the
        taxon itself when it *is* an order or family — which is exactly the
        "Chiroptera" / "Vespertilionidae" case that made this necessary.
        Either may be None if iNaturalist has no such ancestor.
        """
        if not is_resolvable(scientific_name):
            return None

        taxon = self.search(scientific_name)
        if not taxon:
            return None

        found: Dict[str, str] = {}

        # A hit that is itself an order or family answers directly.
        rank = taxon.get("rank")
        if rank in ("order", "family") and taxon.get("name"):
            found[rank] = taxon["name"]

        ancestor_ids = taxon.get("ancestor_ids") or []
        if not all(r in found for r in ("order", "family")) and ancestor_ids:
            self._cache_ancestors(ancestor_ids)
            for ancestor_id in ancestor_ids:
                cached = self._ancestors.get(ancestor_id)
                if cached and cached[0] in ("order", "family"):
                    found.setdefault(cached[0], cached[1])

        return {
            "taxon_id": taxon.get("id"),
            "rank": rank,
            "order": found.get("order"),
            "family": found.get("family"),
        }


def generate_inat_url(scientific_name: str, taxon_id: Optional[int] = None) -> str:
    """
    Generate iNaturalist URL for a species.

    Args:
        scientific_name: Scientific name like "Corvus brachyrhynchos"
        taxon_id: Optional cached taxon ID

    Returns:
        Direct taxon URL if taxon_id provided, search URL otherwise
    """
    if taxon_id:
        # Direct URL with taxon ID
        scientific_hyphen = scientific_name.replace(' ', '-')
        return f"https://www.inaturalist.org/taxa/{taxon_id}-{scientific_hyphen}"
    else:
        # Fallback to search
        return f"https://www.inaturalist.org/taxa/search?q={quote_plus(scientific_name)}"
