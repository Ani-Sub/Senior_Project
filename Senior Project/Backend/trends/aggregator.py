"""
Aggregation utilities for trend analysis.
Tracks synthesized narratives over time.
"""

from collections import defaultdict
from trends.temporal import bucket_videos, Granularity
from trends.metrics import calculate_bucket_metrics, BucketMetrics
from trends.detector import detect_pattern, TrendAnalysis


def aggregate_by_narrative(
    video_results: list[dict],
    synthesis: dict,
    granularity: Granularity
) -> list[dict]:
    """
    Track each synthesized narrative over time.
    
    Uses the narratives from synthesis (each with video_ids) and
    analyzes how each narrative's presence changes over time.
    
    Args:
        video_results: Per-video extraction results
        synthesis: The synthesis output containing narratives list
        granularity: Time bucketing granularity
    
    Returns:
        List of narrative trend analyses
    """
    narratives = synthesis.get("narratives", [])
    
    if not narratives:
        return []
    
    # Build a lookup for video results by video_id
    video_lookup = {r.get("video_id"): r for r in video_results}
    
    narrative_trends = []
    
    for narrative in narratives:
        narrative_id = narrative.get("id", "")
        narrative_name = narrative.get("name", "Unknown")
        narrative_summary = narrative.get("summary", "")
        video_ids = narrative.get("video_ids", [])
        
        # Get the actual video results for this narrative
        matching_videos = []
        for vid in video_ids:
            if vid in video_lookup:
                matching_videos.append(video_lookup[vid])
        
        if not matching_videos:
            continue
        
        # Bucket videos by publish date
        bucketed = bucket_videos(matching_videos, granularity)
        
        # Calculate metrics per time bucket
        metrics = []
        for bucket_key in sorted(bucketed.keys()):
            metrics.append(calculate_bucket_metrics(bucket_key, bucketed[bucket_key]))
        
        # Detect trend pattern
        trend = detect_pattern(metrics)
        
        narrative_trends.append({
            "narrative_id": narrative_id,
            "name": narrative_name,
            "summary": narrative_summary,
            "video_count": len(matching_videos),
            "video_ids": video_ids,
            "trend": {
                "pattern": trend.pattern,
                "confidence": round(trend.confidence, 2),
                "peak_period": trend.peak_period,
                "description": trend.description
            },
            "timeline": [m.to_dict() for m in metrics]
        })
    
    return narrative_trends


def generate_trend_summary(
    video_results: list[dict],
    synthesis: dict,
    granularity: Granularity
) -> dict:
    """
    Generate trend analysis for synthesized narratives.
    
    Tracks:
    - Overall activity timeline
    - Each narrative's presence over time
    """
    # Get time range
    all_timestamps = []
    for result in video_results:
        ts = result.get("video_metadata", {}).get("published_at")
        if ts:
            all_timestamps.append(ts)
    
    all_timestamps.sort()
    time_range = {
        "start": all_timestamps[0] if all_timestamps else None,
        "end": all_timestamps[-1] if all_timestamps else None
    }
    
    # Overall metrics timeline
    overall_bucketed = bucket_videos(video_results, granularity)
    overall_metrics = []
    for bucket_key in sorted(overall_bucketed.keys()):
        overall_metrics.append(
            calculate_bucket_metrics(bucket_key, overall_bucketed[bucket_key])
        )
    
    overall_trend = detect_pattern(overall_metrics)
    
    # Narrative trends
    narrative_trends = aggregate_by_narrative(video_results, synthesis, granularity)
    
    return {
        "granularity": granularity,
        "time_range": time_range,
        "overall": {
            "video_count": len(video_results),
            "trend": overall_trend.to_dict(),
            "timeline": [m.to_dict() for m in overall_metrics]
        },
        "narratives": narrative_trends
    }
