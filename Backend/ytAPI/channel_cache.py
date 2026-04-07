"""
Channel cache for reducing YouTube API quota usage.

Stores discovered channels by search keyword so future searches
can use RSS feeds instead of the expensive search API.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path(__file__).parent.parent / "channel_cache.json"
CACHE_MAX_AGE_DAYS = 30  # Re-search after this many days


def load_cache(cache_path: Path = DEFAULT_CACHE_PATH) -> dict:
    """Load channel cache from disk."""
    if not cache_path.exists():
        return {}
    
    try:
        with open(cache_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log.warning(f"Failed to load cache: {e}")
        return {}


def save_cache(cache: dict, cache_path: Path = DEFAULT_CACHE_PATH) -> None:
    """Save channel cache to disk."""
    try:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        log.warning(f"Failed to save cache: {e}")


def normalize_keyword(keyword: str) -> str:
    """Normalize keyword for cache lookup."""
    return keyword.lower().strip()


def get_cached_channels(
    search_keyword: str,
    max_age_days: int = CACHE_MAX_AGE_DAYS,
    cache_path: Path = DEFAULT_CACHE_PATH
) -> list[dict] | None:
    """
    Get cached channels for a search keyword.
    
    Args:
        search_keyword: The search term to look up
        max_age_days: Maximum age of cache entry in days
        cache_path: Path to cache file
    
    Returns:
        List of channel dicts if cache hit and not expired, None otherwise
    """
    cache = load_cache(cache_path)
    key = normalize_keyword(search_keyword)
    
    if key not in cache:
        log.info(f"  → Cache MISS for '{search_keyword}' (not found)")
        return None
    
    entry = cache[key]
    cached_at = datetime.fromisoformat(entry["cached_at"])
    age_days = (datetime.now(timezone.utc) - cached_at).days
    
    if age_days > max_age_days:
        log.info(f"  → Cache EXPIRED for '{search_keyword}' ({age_days} days old)")
        return None
    
    log.info(f"  → Cache HIT for '{search_keyword}' ({len(entry['channels'])} channels, {age_days} days old)")
    return entry["channels"]


def cache_channels(
    search_keyword: str,
    channels: list[dict],
    cache_path: Path = DEFAULT_CACHE_PATH
) -> None:
    """
    Cache channels for a search keyword.
    
    Args:
        search_keyword: The search term
        channels: List of channel dicts (must have 'channel_id' and 'title')
        cache_path: Path to cache file
    """
    cache = load_cache(cache_path)
    key = normalize_keyword(search_keyword)
    
    cache[key] = {
        "channels": [
            {
                "channel_id": ch["channel_id"],
                "title": ch["title"],
                "subscriber_count": ch.get("subscriber_count", 0)
            }
            for ch in channels
        ],
        "cached_at": datetime.now(timezone.utc).isoformat()
    }
    
    save_cache(cache, cache_path)
    log.info(f"  → Cached {len(channels)} channels for '{search_keyword}'")


def clear_cache(cache_path: Path = DEFAULT_CACHE_PATH) -> None:
    """Clear the entire cache."""
    save_cache({}, cache_path)
    log.info("  → Cache cleared")


def list_cached_keywords(cache_path: Path = DEFAULT_CACHE_PATH) -> list[str]:
    """List all cached search keywords."""
    cache = load_cache(cache_path)
    return list(cache.keys())
