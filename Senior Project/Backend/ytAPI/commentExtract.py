import logging
from config import youtube

log = logging.getLogger(__name__)


def get_comments(video_id: str, max_comments: int = 30) -> list[dict]:
    """
    Fetch top comments for a video, sorted by relevance (likes-weighted).
    Filters out very short comments unlikely to contain claims.
    
    Returns a list of dicts with full comment data for DB export:
        comment_id, video_id, commenter_name, comment_text, 
        published_at, is_reply, top_level_comment_id, likes
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
            top_comment = item["snippet"]["topLevelComment"]
            comment_id = top_comment["id"]
            snippet = top_comment["snippet"]
            
            text = snippet.get("textDisplay", "").strip()
            likes = snippet.get("likeCount", 0)
            published_at = snippet.get("publishedAt")
            commenter_name = snippet.get("authorDisplayName", "")

            # Skip very short comments — unlikely to contain claims
            if len(text) < 20:
                continue

            comments.append({
                "comment_id": comment_id,
                "video_id": video_id,
                "commenter_name": commenter_name,
                "comment_text": text,
                "published_at": published_at,
                "is_reply": False,  # Top-level comments
                "top_level_comment_id": None,
                "likes": likes,
                # Keep these for backward compatibility with analyzer
                "text": text,
            })

        # Sort by likes descending and return top N
        comments.sort(key=lambda x: x["likes"], reverse=True)
        comments = comments[:max_comments]

        return comments

    except Exception as e:
        log.warning(f"Comments unavailable for {video_id}: {e}")
        return []