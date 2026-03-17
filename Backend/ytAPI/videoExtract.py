import logging
from datetime import datetime, timezone, timedelta
from config import youtube
from ytAPI.channelExtract import search_channels, filter_channels

log = logging.getLogger(__name__)


def get_published_after(days: int) -> str:
    """Return an ISO timestamp for N days ago, used as a YouTube API filter."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.isoformat()


def get_recent_channel_videos(
    channel_id: str,
    days: int = 30,
    max_results: int = 10
) -> list[str]:
    """Fetch video IDs from a channel published within the last N days."""
    published_after = get_published_after(days)
    response = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        type="video",
        order="date",
        publishedAfter=published_after,
        maxResults=max_results
    ).execute()

    return [item["id"]["videoId"] for item in response["items"]]


def filter_videos(
    video_ids: list[str],
    min_views: int = 10_000,
    keywords: list[str] | None = None
) -> list[str]:
    """Filter videos by minimum view count and keyword match in title."""
    if not video_ids:
        return []
    if keywords is None:
        keywords = []

    response = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()

    selected = []
    for item in response["items"]:
        views = int(item["statistics"].get("viewCount", 0))
        title = item["snippet"]["title"].lower()
        if views >= min_views and any(k.lower() in title for k in keywords):
            selected.append(item["id"])

    return selected


def discover_videos(
    search_keywords: str,
    channel_sub_min: int,
    video_view_min: int,
    video_keywords: list[str],
    days: int = 30
) -> list[str]:
    """
    Full discovery pipeline:
    search channels → filter by size → get recent videos → filter by views/keywords
    """
    log.info("Searching channels...")
    channel_ids = search_channels(search_keywords)

    log.info("Filtering channels...")
    channels = filter_channels(channel_ids, min_subscribers=channel_sub_min)

    all_video_ids = []
    for channel in channels:
        log.info(f"Getting recent videos for: {channel['title']}")
        vids = get_recent_channel_videos(channel["channel_id"], days=days, max_results=5)
        filtered = filter_videos(vids, min_views=video_view_min, keywords=video_keywords)
        all_video_ids.extend(filtered)

    return all_video_ids





