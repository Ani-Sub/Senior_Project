import logging
from datetime import datetime, timezone, timedelta
from config import youtube
from ytAPI.channelExtract import search_channels, filter_channels
from ytAPI.rss_feed import fetch_videos_from_channels
from ytAPI.channel_cache import get_cached_channels, cache_channels

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
    """Fetch video IDs from a channel published within the last N days (API method)."""
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


def parse_iso_duration(iso_duration: str | None) -> int:
    """
    Convert ISO 8601 duration (PT15M30S) to seconds.
    
    Examples:
        PT1H2M3S -> 3723
        PT15M30S -> 930
        PT45S -> 45
    """
    if not iso_duration:
        return 0
    
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, iso_duration)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def enrich_video_metadata(video_ids: list[str]) -> list[dict]:
    """
    Fetch full metadata for videos (view count, likes, duration).
    Batches up to 50 videos per API call.
    
    This is needed for both RSS and API-discovered videos since
    RSS doesn't include view counts.
    """
    if not video_ids:
        return []
    
    all_metadata = []
    
    # Batch into groups of 50 (API limit)
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        
        response = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=",".join(batch)
        ).execute()
        
        for item in response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            iso_duration = item.get("contentDetails", {}).get("duration")
            
            all_metadata.append({
                "video_id": item["id"],
                "channel_id": snippet.get("channelId"),
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration": iso_duration,
                "duration_seconds": parse_iso_duration(iso_duration),
            })
    
    return all_metadata


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
            iso_duration = item["contentDetails"].get("duration")
            # Return rich metadata for trend analysis
            selected.append({
                "video_id": vid_id,
                "channel_id": snippet.get("channelId"),
                "title": title,
                "description": snippet.get("description", ""),
                "channel_title": snippet.get("channelTitle", channel_title),
                "published_at": snippet.get("publishedAt"),  # ISO 8601 timestamp
                "view_count": views,
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration": iso_duration,
                "duration_seconds": parse_iso_duration(iso_duration),
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

    log.info(f"  → {channel_title}: {len(selected)} videos passed filter, {len(rejected)} rejected")
    return selected


def discover_videos_via_rss(
    channels: list[dict],
    video_view_min: int,
    video_keywords: list[str],
    days: int = 30
) -> list[dict]:
    """
    Discover videos using RSS feeds (FREE) + minimal API for metadata.
    
    Args:
        channels: List of channel dicts with 'channel_id' and 'title'
        video_view_min: Minimum view count for videos
        video_keywords: Keywords that must appear in video titles
        days: How far back to look for videos
    
    Returns:
        List of filtered video metadata dicts
    """
    channel_ids = [ch["channel_id"] for ch in channels]
    
    # Step 1: Get videos from RSS (FREE)
    log.info(f"  → Fetching videos via RSS feeds ({len(channel_ids)} channels)...")
    rss_videos = fetch_videos_from_channels(
        channel_ids=channel_ids,
        days=days,
        keywords=video_keywords  # Pre-filter by keywords
    )
    
    if not rss_videos:
        log.info("  → No videos found in RSS feeds")
        return []
    
    # Step 2: Get view counts from API (costs 1 unit per 50 videos)
    video_ids = [v["video_id"] for v in rss_videos]
    log.info(f"  → Enriching {len(video_ids)} videos with API metadata...")
    enriched = enrich_video_metadata(video_ids)
    
    # Step 3: Filter by view count
    selected = []
    rejected = []
    
    for video in enriched:
        if video["view_count"] >= video_view_min:
            selected.append(video)
        else:
            rejected.append({
                "video_id": video["video_id"],
                "title": video["title"],
                "views": video["view_count"],
                "reasons": [f"views={video['view_count']:,} < min={video_view_min:,}"]
            })
    
    log.info(f"  → {len(selected)} videos passed view filter, {len(rejected)} rejected")
    return selected


def discover_videos_via_api(
    channels: list[dict],
    video_view_min: int,
    video_keywords: list[str],
    days: int = 30
) -> list[dict]:
    """
    Discover videos using YouTube API (original method, costs quota).
    
    Used as fallback when RSS isn't sufficient.
    """
    all_videos = []
    
    for channel in channels:
        log.info(f"  → API search for: {channel['title']}")
        vids = get_recent_channel_videos(channel["channel_id"], days=days, max_results=5)
        log.info(f"    Found {len(vids)} recent videos")
        filtered = filter_videos(
            vids,
            channel_title=channel["title"],
            min_views=video_view_min,
            keywords=video_keywords
        )
        all_videos.extend(filtered)
    
    return all_videos


def discover_videos(
    search_keywords: str,
    channel_sub_min: int,
    video_view_min: int,
    video_keywords: list[str],
    days: int = 30,
    use_cache: bool = True,
    cache_max_age_days: int = 30
) -> list[dict]:
    """
    Full discovery pipeline with quota optimization:
    
    1. Check cache for channels matching search keywords
    2. If cache hit → use RSS feeds (FREE)
    3. If cache miss → use API search (costs quota) → save to cache
    
    Args:
        search_keywords: Keywords to search for channels
        channel_sub_min: Minimum subscriber count for channels
        video_view_min: Minimum view count for videos
        video_keywords: Keywords that must appear in video titles
        days: How far back to look for videos
        use_cache: Whether to use channel cache (set False to always use API)
        cache_max_age_days: Maximum age of cache entries in days
    
    Returns:
        List of video metadata dicts
    """
    channels = None
    used_cache = False
    
    # Step 1: Try cache first
    if use_cache:
        cached = get_cached_channels(search_keywords, max_age_days=cache_max_age_days)
        if cached:
            channels = cached
            used_cache = True
            log.info(f"Using cached channels for '{search_keywords}'")
    
    # Step 2: Fall back to API if no cache
    if channels is None:
        log.info(f"Searching channels via API (cache miss)...")
        channel_ids = search_channels(search_keywords)
        
        log.info("Filtering channels by subscriber count...")
        channels = filter_channels(channel_ids, min_subscribers=channel_sub_min)
        
        # Save to cache for next time
        if use_cache and channels:
            cache_channels(search_keywords, channels)
    
    if not channels:
        log.warning("No channels found matching criteria")
        return []
    
    log.info(f"Found {len(channels)} channels")
    
    # Step 3: Get videos — use RSS if we have cached channels, API otherwise
    if used_cache:
        log.info("Discovering videos via RSS (FREE)...")
        videos = discover_videos_via_rss(
            channels=channels,
            video_view_min=video_view_min,
            video_keywords=video_keywords,
            days=days
        )
    else:
        log.info("Discovering videos via API...")
        videos = discover_videos_via_api(
            channels=channels,
            video_view_min=video_view_min,
            video_keywords=video_keywords,
            days=days
        )
    
    log.info(f"Discovered {len(videos)} videos total")
    return videos



