"""
Bird Image API
Fetches and caches bird images from Wikipedia/Wikimedia Commons.

Version: 1.1.0
"""

import os
import hashlib
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Cache directory - use relative path for local dev, absolute for Docker
_base = Path(os.environ.get("DATA_DIR", "./data"))
CACHE_DIR = _base / "image_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(species_name: str) -> Path:
    """Get cache file path for a species."""
    safe_name = hashlib.md5(species_name.lower().encode()).hexdigest()
    return CACHE_DIR / f"{safe_name}.jpg"


# User-Agent header required by Wikipedia/Wikimedia API
# Using a browser-compatible User-Agent for image downloads from Wikimedia Commons
WIKI_API_HEADERS = {
    "User-Agent": "BirdWeatherViz/1.0 (Bird detection visualization; Python httpx)",
    "Accept": "application/json",
}

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def fetch_wikipedia_image_for_title(title: str) -> str | None:
    """
    Fetch bird image URL from Wikipedia API for a given title.

    Args:
        title: Wikipedia page title

    Returns:
        Image URL or None if not found
    """
    wiki_api = "https://en.wikipedia.org/w/api.php"
    # Format title: replace spaces with underscores
    formatted_title = title.replace(" ", "_")

    params = {
        "action": "query",
        "titles": formatted_title,
        "prop": "pageimages",
        "format": "json",
        "pithumbsize": 300,
        "redirects": 1,  # Follow redirects
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, headers=WIKI_API_HEADERS) as client:
            response = await client.get(wiki_api, params=params)
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id != "-1" and "thumbnail" in page_data:
                    return page_data["thumbnail"]["source"]
    except Exception as e:
        logger.warning(f"Failed to fetch Wikipedia image for {title}: {e}")

    return None


async def fetch_wikipedia_image(scientific_name: str, common_name: str = None) -> str | None:
    """
    Fetch bird image URL from Wikipedia API.
    Tries scientific name first, then common name.

    Args:
        scientific_name: Scientific name of the bird
        common_name: Common name of the bird (optional)

    Returns:
        Image URL or None if not found
    """
    # Try scientific name first
    image_url = await fetch_wikipedia_image_for_title(scientific_name)
    if image_url:
        return image_url

    # Try common name if provided
    if common_name:
        image_url = await fetch_wikipedia_image_for_title(common_name)
        if image_url:
            return image_url

    return None


async def download_and_cache_image(image_url: str, cache_path: Path) -> bool:
    """Download image and save to cache."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=DOWNLOAD_HEADERS) as client:
            response = await client.get(image_url)
            if response.status_code == 200:
                cache_path.write_bytes(response.content)
                return True
    except Exception as e:
        logger.warning(f"Failed to download image: {e}")
    return False


@router.get("/bird/{scientific_name}")
async def get_bird_image(scientific_name: str, common_name: str = None):
    """
    Get bird image by scientific name.

    Fetches from Wikipedia and caches locally for performance.
    Returns cached image if available.
    """
    cache_path = get_cache_path(scientific_name)

    # Return cached image if exists
    if cache_path.exists():
        return FileResponse(
            cache_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"}  # Cache for 1 day
        )

    # Fetch from Wikipedia (try scientific name, then common name)
    image_url = await fetch_wikipedia_image(scientific_name, common_name)

    if image_url:
        # Download and cache
        if await download_and_cache_image(image_url, cache_path):
            return FileResponse(
                cache_path,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=86400"}
            )
        else:
            # Return redirect to original if caching fails
            return RedirectResponse(url=image_url)

    # Return 404 if no image found
    raise HTTPException(status_code=404, detail="Bird image not found")


@router.get("/bird/{scientific_name}/url")
async def get_bird_image_url(scientific_name: str, common_name: str = None):
    """
    Get the URL for a bird image (for frontend use).

    Returns local cached URL if available, otherwise fetches and caches.
    """
    cache_path = get_cache_path(scientific_name)

    # Check if cached
    if cache_path.exists():
        return {"url": f"/api/v1/images/bird/{scientific_name}", "cached": True}

    # Fetch from Wikipedia (try scientific name, then common name)
    image_url = await fetch_wikipedia_image(scientific_name, common_name)

    if image_url:
        # Cache in background (don't wait)
        await download_and_cache_image(image_url, cache_path)
        return {"url": f"/api/v1/images/bird/{scientific_name}", "cached": False}

    return {"url": None, "cached": False}
