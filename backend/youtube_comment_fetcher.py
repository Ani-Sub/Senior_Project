from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Video ID helper
def extract_video_id(s: str) -> str:

    # Accepts either a video ID or a YouTube URL and returns the video ID.
    s = s.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{8,20}", s):
        return s
    
    # Try to parse v=... from URL
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{8,20})", s)
    if m:
        return m.group(1)
    
    # Try youtu.be/<id>
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{8,20})", s)
    if m:
        return m.group(1)
    
    raise ValueError(f"Could not extract video id from: {s}")

# Core fetcher
def fetch_comments(
        video_or_url: str,
        api_key: Optional[str] = None,
        max_comments: int = 300,
        order: str = "relevance", # "time" for newest first
        include_replies: bool = True,
        language: str = "en",
) -> Dict[str, Any]:
    """
    Fetch top- level comments for a youtube video (+ replies if include_replies=True).
    
    Returns:
      {
        "ok": bool,
        "video_id": str,
        "error": str|None,
        "comments: [ { normalized comment row }, ...],
        "stats": { "requested_max": int, "returned": int, "order": str  }
      }
        
    Normalized row:
      {
        "comment_id": str,
        "parent_id": str|None,
        "video_id": str,
        "published_at": str|None,
        "like_count": int,
        "reply_count": int,
        "author": str|None,
        "author_channel_id": str|None,
        "text": str
      }
    """
    try:
        api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return {
                "ok": False,
                "video_id": None,
                "error": "Missing API key. Provide api_key=... or set YOUTUBE_API_KEY env var.",
                "comments": [],
                "stats": {"requested_max": max_comments, "returned": 0, "order": order}
            }
        
        video_id = extract_video_id(video_or_url)
        youtube = build("youtube", "v3", developerKey=api_key)

        out: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while len(out) < max_comments:
            req = youtube.commentThreads().list(
                part="snippet,replies" if include_replies else "snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(out)),
                pageToken=page_token,
                order=order,
                textFormat="plainText",
            )
            resp = req.execute()

            for item in resp.get("items", []):
                top = item["snippet"]["topLevelComment"]
                s = top["snippet"]

                out.append({
                    "comment_id": top["id"],
                    "parent_id": None,
                    "video_id": video_id,
                    "published_at": s.get("publishedAt"),
                    "like_count": int(s.get("likeCount", 0) or 0),
                    "reply_count": int(item["snippet"].get("totalReplyCount", 0) or 0),
                    "author": s.get("authorDisplayName"),
                    "author_channel_id": s.get("authorChannelId", {}).get("value"),
                    "text": (s.get("textDisplay") or "").strip(),
                })

                if include_replies:
                    for r in (item.get("replies") or {}).get("comments", []):
                        rs = r["snippet"]
                        out.append({
                            "comment_id": r["id"],
                            "parent_id": rs.get("parentId"),
                            "video_id": video_id,
                            "published_at": rs.get("publishedAt"),
                            "like_count": int(rs.get("likeCount", 0) or 0),
                            "reply_count": 0,
                            "author": rs.get("authorDisplayName"),
                            "author_channel_id": (rs.get("authorChannelId") or {}).get("value"),
                            "text": (rs.get("textDisplay") or "").strip(),
                        })

                if len(out) >= max_comments:
                    break

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return {
            "ok": True,
            "video_id": video_id,
            "error": None,
            "comments": out[:max_comments],
            "stats": {"requested_max": max_comments, "returned": min(len(out), max_comments), "order": order},
        }
    
    except ValueError as ve:
        return {
            "ok": False,
            "video_id": None,
            "error": str(ve),
            "comments": [],
            "stats": {"requested_max": max_comments, "returned": 0, "order": order},
        }
    except HttpError as he:
        return {
            "ok": False,
            "video_id": extract_video_id(video_or_url) if isinstance(video_or_url, str) else None,
            "error": f"YouTube API HttpError: {he}",
            "comments": [],
            "stats": {"requested_max": max_comments, "returned": 0, "order": order},
        }
    except Exception as e:
        return {
            "ok": False,
            "video_id": extract_video_id(video_or_url) if isinstance(video_or_url, str) else None,
            "error": f"Unexpected error: {e}",
            "comments": [],
            "stats": {"requested_max": max_comments, "returned": 0, "order": order},
        }



if __name__ == "__main__":
    import json
    test = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    result = fetch_comments(test, max_comments=50, order="relevance")
    print(json.dumps(result, indent=2, ensure_ascii=False))
