import logging
from config import youtube

log = logging.getLogger(__name__)


def search_channels(query: str, max_results: int = 10) -> list[str]:
    """Search YouTube for channels matching a keyword query."""
    response = youtube.search().list(
        q=query,
        type="channel",
        part="snippet",
        maxResults=max_results
    ).execute()

    channel_ids = [item["snippet"]["channelId"] for item in response["items"]]
    log.info(f"  → Found {len(channel_ids)} channels for query: '{query}'")
    return channel_ids


def filter_channels(
    channel_ids: list[str],
    min_subscribers: int = 50_000,
    min_total_views: int = 1_000_000
) -> list[dict]:
    """Filter channels by subscriber count and total view thresholds."""
    response = youtube.channels().list(
        part="statistics,snippet",
        id=",".join(channel_ids)
    ).execute()

    filtered = []
    for item in response["items"]:
        stats = item["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        if subs >= min_subscribers and views >= min_total_views:
            filtered.append({
                "channel_id": item["id"],
                "title": item["snippet"]["title"],
                "subscriber_count": subs
            })

    log.info(f"  → {len(filtered)} channels passed filter (min subs: {min_subscribers:,})")
    return filtered