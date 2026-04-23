"""
YouTube RSS feed fetcher — zero quota cost.

Each channel's feed provides the 15 most recent videos with:
- video_id, title, published date, description, thumbnail
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import requests

log = logging.getLogger(__name__)

RSS_URL_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# XML namespaces used in YouTube feeds
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/"
}


def fetch_channel_feed(channel_id: str) -> list[dict]:
    """
    Fetch recent videos from a channel's RSS feed.
    
    Args:
        channel_id: YouTube channel ID
    
    Returns:
        List of video dicts with: video_id, title, published_at, description, channel_title
    """
    url = RSS_URL_TEMPLATE.format(channel_id=channel_id)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"  → RSS fetch failed for {channel_id}: {e}")
        return []
    
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as e:
        log.warning(f"  → RSS parse failed for {channel_id}: {e}")
        return []
    
    # Get channel title from feed
    channel_title = root.find("atom:title", NAMESPACES)
    channel_title = channel_title.text if channel_title is not None else "Unknown"
    
    videos = []
    for entry in root.findall("atom:entry", NAMESPACES):
        video_id = entry.find("yt:videoId", NAMESPACES)
        title = entry.find("atom:title", NAMESPACES)
        published = entry.find("atom:published", NAMESPACES)
        
        # Description is in media:group/media:description
        media_group = entry.find("media:group", NAMESPACES)
        description = None
        if media_group is not None:
            desc_elem = media_group.find("media:description", NAMESPACES)
            description = desc_elem.text if desc_elem is not None else ""
        
        if video_id is not None and title is not None:
            videos.append({
                "video_id": video_id.text,
                "title": title.text,
                "published_at": published.text if published is not None else None,
                "description": description or "",
                "channel_title": channel_title,
                "channel_id": channel_id
            })
    
    return videos


def fetch_videos_from_channels(
    channel_ids: list[str],
    days: int = 30,
    keywords: list[str] | None = None
) -> list[dict]:
    """
    Fetch recent videos from multiple channels via RSS.
    
    Args:
        channel_ids: List of channel IDs to fetch
        days: Only include videos from last N days
        keywords: Filter by keywords in title (optional)
    
    Returns:
        List of video dicts that match criteria
    """
    if keywords is None:
        keywords = []
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_videos = []
    
    for channel_id in channel_ids:
        log.info(f"  → Fetching RSS for channel: {channel_id}")
        videos = fetch_channel_feed(channel_id)
        
        for video in videos:
            # Check publish date
            if video["published_at"]:
                try:
                    pub_date = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
                    if pub_date < cutoff:
                        continue  # Too old
                except ValueError:
                    pass  # Can't parse date, include anyway
            
            # Check keyword match if keywords specified
            if keywords:
                title_lower = video["title"].lower()
                if not any(k.lower() in title_lower for k in keywords):
                    continue  # No keyword match
            
            all_videos.append(video)
    
    log.info(f"  → RSS found {len(all_videos)} videos matching criteria")
    return all_videos
