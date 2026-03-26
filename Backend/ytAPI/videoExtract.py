import logging
from datetime import datetime, timezone, timedelta
from config import youtube
from ytAPI.channelExtract import search_channels, filter_channels
from utility.debugLog import log_videos_raw, log_videos_filtered

log = logging.getLogger(__name__)


def get_published_after(days: int) -> str:
    """Return an ISO timestamp for N days ago, used as a YouTube API filter."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.isoformat()


def get_recent_channel_videos(
    channel_id: str,
    days: int = 30,
    max_results: int = 5
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
    channel_title: str = "unknown",
    min_views: int = 10_000,
    keywords: list[str] | None = None
) -> list[dict]:
    """
    Filter videos by minimum view count and keyword match in title.
    Returns rich video metadata objects for trend analysis.
    Logs both accepted and rejected videos with rejection reasons.
    """
    if not video_ids:
        return []
    if keywords is None:
        keywords = []

    response = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()

    selected = []
    rejected = []

    for item in response["items"]:
        vid_id = item["id"]
        stats = item["statistics"]
        snippet = item["snippet"]
        
        views = int(stats.get("viewCount", 0))
        title = snippet["title"]
        title_lower = title.lower()
        keyword_match = any(k.lower() in title_lower for k in keywords)

        if views >= min_views and keyword_match:
            # Return rich metadata for trend analysis
            selected.append({
                "video_id": vid_id,
                "title": title,
                "channel_title": snippet.get("channelTitle", channel_title),
                "published_at": snippet.get("publishedAt"),  # ISO 8601 timestamp
                "view_count": views,
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration": item["contentDetails"].get("duration"),  # ISO 8601 duration
            })
        else:
            reasons = []
            if views < min_views:
                reasons.append(f"views={views:,} < min={min_views:,}")
            if not keyword_match:
                reasons.append(f"no keyword match (keywords={keywords}, title='{title}')")
            rejected.append({
                "video_id": vid_id,
                "title": title,
                "views": views,
                "reasons": reasons
            })

    # Log just the IDs for compatibility with existing debug logs
    log_videos_filtered(channel_title, [v["video_id"] for v in selected], rejected)
    return selected


def discover_videos(
    search_keywords: str,
    channel_sub_min: int,
    video_view_min: int,
    video_keywords: list[str],
    days: int = 30
) -> list[dict]:
    """
    Full discovery pipeline:
    search channels → filter by size → get recent videos → filter by views/keywords
    
    Returns list of video metadata dicts with keys:
        video_id, title, channel_title, published_at, 
        view_count, like_count, comment_count, duration
    """
    log.info("Searching channels...")
    channel_ids = search_channels(search_keywords)

    log.info("Filtering channels...")
    channels = filter_channels(channel_ids, min_subscribers=channel_sub_min)

    all_videos = []
    for channel in channels:
        log.info(f"Getting recent videos for: {channel['title']}")
        vids = get_recent_channel_videos(channel["channel_id"], days=days, max_results=5)
        log_videos_raw(channel["title"], channel["channel_id"], vids)
        filtered = filter_videos(
            vids,
            channel_title=channel["title"],
            min_views=video_view_min,
            keywords=video_keywords
        )
        all_videos.extend(filtered)

    return all_videos



