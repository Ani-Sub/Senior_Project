import logging
from config import youtube
from utility.debugLog import log_comments

log = logging.getLogger(__name__)


def get_comments(video_id: str, max_comments: int = 30) -> list[dict]:
    """
    Fetch top comments for a video, sorted by relevance (likes-weighted).
    Filters out very short comments unlikely to contain claims.
    Returns a list of dicts with 'text' and 'likes'.
    """
    try:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            order="relevance",
            maxResults=min(max_comments, 100),
            textFormat="plainText"
        ).execute()

        comments = []
        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            likes = snippet.get("likeCount", 0)
            text = snippet.get("textDisplay", "").strip()

            # Skip very short comments — unlikely to contain claims
            if len(text) < 20:
                continue

            comments.append({
                "text": text,
                "likes": likes
            })

        # Sort by likes descending and return top N
        comments.sort(key=lambda x: x["likes"], reverse=True)
        comments = comments[:max_comments]

        log_comments(video_id, comments)
        log.info(f"  → Fetched {len(comments)} comments for {video_id}")
        return comments

    except Exception as e:
        log.warning(f"Comments unavailable for {video_id}: {e}")
        return []