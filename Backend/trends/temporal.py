"""
Time bucketing utilities for trend analysis.
Converts ISO 8601 timestamps into daily or weekly buckets.
"""

from datetime import datetime, timedelta
from typing import Literal

Granularity = Literal["daily", "weekly"]


def parse_iso_timestamp(iso_str: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string into a datetime object."""
    if not iso_str:
        return None
    try:
        # Handle YouTube's format: 2026-03-15T14:30:00Z
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return None


def get_bucket_key(dt: datetime, granularity: Granularity) -> str:
    """
    Convert a datetime to a bucket key string.
    
    Daily:  "2026-03-15"
    Weekly: "2026-W11" (ISO week number)
    """
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    else:  # weekly
        return dt.strftime("%Y-W%W")


def get_bucket_start(bucket_key: str, granularity: Granularity) -> datetime:
    """Convert a bucket key back to a datetime (start of period)."""
    if granularity == "daily":
        return datetime.strptime(bucket_key, "%Y-%m-%d")
    else:  # weekly
        # Parse "2026-W11" format
        year, week = bucket_key.split("-W")
        return datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")


def generate_bucket_range(
    start_date: datetime,
    end_date: datetime,
    granularity: Granularity
) -> list[str]:
    """
    Generate all bucket keys between start and end dates (inclusive).
    Useful for ensuring we have entries for periods with zero activity.
    """
    buckets = []
    current = start_date
    
    if granularity == "daily":
        step = timedelta(days=1)
    else:  # weekly
        step = timedelta(weeks=1)
    
    while current <= end_date:
        buckets.append(get_bucket_key(current, granularity))
        current += step
    
    return buckets


def bucket_items(
    items: list[dict],
    timestamp_key: str,
    granularity: Granularity
) -> dict[str, list[dict]]:
    """
    Group items into time buckets based on a timestamp field.
    
    Args:
        items: List of dicts, each containing a timestamp field
        timestamp_key: Key to extract timestamp from each item
        granularity: "daily" or "weekly"
    
    Returns:
        Dict mapping bucket keys to lists of items in that bucket
    """
    buckets: dict[str, list[dict]] = {}
    
    for item in items:
        ts = parse_iso_timestamp(item.get(timestamp_key))
        if not ts:
            continue
        
        bucket_key = get_bucket_key(ts, granularity)
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(item)
    
    return buckets


def bucket_videos(
    video_results: list[dict],
    granularity: Granularity
) -> dict[str, list[dict]]:
    """
    Bucket video results by their publish date.
    
    Expects video_results where each item has:
        video_metadata.published_at
    """
    items_with_ts = []
    for result in video_results:
        metadata = result.get("video_metadata", {})
        if metadata.get("published_at"):
            items_with_ts.append({
                **result,
                "_published_at": metadata["published_at"]
            })
    
    buckets = bucket_items(items_with_ts, "_published_at", granularity)
    
    # Remove the temporary key
    for bucket_key in buckets:
        for item in buckets[bucket_key]:
            item.pop("_published_at", None)
    
    return buckets
