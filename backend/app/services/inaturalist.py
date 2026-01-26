"""
iNaturalist Integration Service
Fetches and caches taxon IDs from iNaturalist API.

Version: 1.0.0
"""

import httpx
from typing import Optional
from urllib.parse import quote_plus


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
