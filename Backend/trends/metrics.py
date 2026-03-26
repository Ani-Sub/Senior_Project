"""
Activity metrics calculations for trend analysis.
Computes video count, views, comments, and engagement per time bucket.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BucketMetrics:
    """Metrics for a single time bucket."""
    period: str
    video_count: int
    total_views: int
    total_likes: int
    total_comments: int
    engagement_ratio: float  # (likes + comments) / views
    claim_count: int
    avg_confidence: float
    # DB/Frontend-friendly timestamps (set by calculate_bucket_metrics)
    period_start_iso: str = ""  # ISO 8601 date string
    period_start_ts: int = 0    # Unix timestamp (seconds)
    
    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "period_start_iso": self.period_start_iso,
            "period_start_ts": self.period_start_ts,
            "video_count": self.video_count,
            "total_views": self.total_views,
            "total_likes": self.total_likes,
            "total_comments": self.total_comments,
            "engagement_ratio": round(self.engagement_ratio, 4),
            "claim_count": self.claim_count,
            "avg_confidence": round(self.avg_confidence, 3)
        }


def calculate_engagement_ratio(views: int, likes: int, comments: int) -> float:
    """
    Calculate engagement ratio: (likes + comments) / views.
    Returns 0 if views is 0 to avoid division by zero.
    """
    if views == 0:
        return 0.0
    return (likes + comments) / views


def calculate_bucket_metrics(bucket_key: str, videos: list[dict]) -> BucketMetrics:
    """
    Calculate aggregate metrics for all videos in a time bucket.
    
    Args:
        bucket_key: The period identifier (e.g., "2026-03-15" or "2026-W11")
        videos: List of video result dicts with video_metadata and claims
    
    Returns:
        BucketMetrics dataclass with aggregated stats
    """
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_claims = 0
    confidence_sum = 0.0
    confidence_count = 0
    
    for video in videos:
        metadata = video.get("video_metadata", {})
        total_views += metadata.get("view_count", 0)
        total_likes += metadata.get("like_count", 0)
        total_comments += metadata.get("comment_count", 0)
        
        claims = video.get("claims", [])
        total_claims += len(claims)
        
        for claim in claims:
            conf = claim.get("confidence")
            if conf is not None:
                confidence_sum += conf
                confidence_count += 1
    
    engagement = calculate_engagement_ratio(total_views, total_likes, total_comments)
    avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0
    
    # Parse bucket_key to get timestamps for DB/frontend
    period_start_iso = ""
    period_start_ts = 0
    try:
        if "-W" in bucket_key:
            # Weekly format: "2026-W11"
            year, week = bucket_key.split("-W")
            dt = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
        else:
            # Daily format: "2026-03-15"
            dt = datetime.strptime(bucket_key, "%Y-%m-%d")
        
        period_start_iso = dt.strftime("%Y-%m-%d")
        period_start_ts = int(dt.timestamp())
    except (ValueError, TypeError):
        pass  # Keep defaults if parsing fails
    
    return BucketMetrics(
        period=bucket_key,
        period_start_iso=period_start_iso,
        period_start_ts=period_start_ts,
        video_count=len(videos),
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments,
        engagement_ratio=engagement,
        claim_count=total_claims,
        avg_confidence=avg_confidence
    )


def calculate_all_bucket_metrics(
    bucketed_videos: dict[str, list[dict]]
) -> list[BucketMetrics]:
    """
    Calculate metrics for all time buckets.
    
    Args:
        bucketed_videos: Dict mapping bucket keys to lists of video results
    
    Returns:
        List of BucketMetrics, sorted chronologically by period
    """
    metrics = []
    for bucket_key, videos in bucketed_videos.items():
        metrics.append(calculate_bucket_metrics(bucket_key, videos))
    
    # Sort by period (works for both YYYY-MM-DD and YYYY-Www formats)
    metrics.sort(key=lambda m: m.period)
    return metrics


def calculate_metric_deltas(metrics: list[BucketMetrics]) -> list[dict]:
    """
    Calculate period-over-period changes for each metric.
    
    Returns list of dicts with the metrics plus delta fields:
        video_count_delta, views_delta, engagement_delta, etc.
    """
    results = []
    
    for i, current in enumerate(metrics):
        result = current.to_dict()
        
        if i > 0:
            prev = metrics[i - 1]
            result["video_count_delta"] = current.video_count - prev.video_count
            result["views_delta"] = current.total_views - prev.total_views
            result["comments_delta"] = current.total_comments - prev.total_comments
            result["engagement_delta"] = round(
                current.engagement_ratio - prev.engagement_ratio, 4
            )
            result["claim_count_delta"] = current.claim_count - prev.claim_count
            
            # Percentage changes (avoid division by zero)
            if prev.total_views > 0:
                result["views_pct_change"] = round(
                    (current.total_views - prev.total_views) / prev.total_views * 100, 1
                )
            else:
                result["views_pct_change"] = None
        else:
            # First period has no deltas
            result["video_count_delta"] = None
            result["views_delta"] = None
            result["comments_delta"] = None
            result["engagement_delta"] = None
            result["claim_count_delta"] = None
            result["views_pct_change"] = None
        
        results.append(result)
    
    return results
