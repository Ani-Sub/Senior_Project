"""
Aggregation utilities for trend analysis.
Groups and analyzes trends by topic, claim, and synthesized narrative.
"""

from collections import defaultdict
from trends.temporal import bucket_videos, Granularity
from trends.metrics import calculate_bucket_metrics, BucketMetrics
from trends.detector import detect_pattern, TrendAnalysis


def aggregate_by_topic(
    video_results: list[dict],
    granularity: Granularity
) -> dict[str, dict]:
    """
    Aggregate trend data by topic.
    
    Each video may have multiple topics. A video contributes its full
    metrics to each topic it belongs to.
    
    Returns:
        Dict mapping topic name to trend analysis:
        {
            "AI Safety": {
                "video_count": 5,
                "trend": {...},
                "timeline": [...]
            }
        }
    """
    # Group videos by topic
    topic_videos: dict[str, list[dict]] = defaultdict(list)
    
    for result in video_results:
        topics = result.get("topics", [])
        for topic in topics:
            topic_videos[topic].append(result)
    
    # Analyze each topic
    topic_trends = {}
    for topic, videos in topic_videos.items():
        # Bucket these videos by time
        bucketed = bucket_videos(videos, granularity)
        
        # Calculate metrics per bucket
        metrics = []
        for bucket_key in sorted(bucketed.keys()):
            metrics.append(calculate_bucket_metrics(bucket_key, bucketed[bucket_key]))
        
        # Detect pattern
        trend = detect_pattern(metrics)
        
        topic_trends[topic] = {
            "video_count": len(videos),
            "trend": trend.to_dict(),
            "timeline": [m.to_dict() for m in metrics]
        }
    
    return topic_trends


def aggregate_by_claim_type(
    video_results: list[dict],
    granularity: Granularity
) -> dict[str, dict]:
    """
    Aggregate trend data by claim type (factual, prediction, opinion, statistic).
    
    Returns dict mapping claim type to its trend analysis.
    """
    # First, restructure data to be claim-centric with timestamps
    claim_type_data: dict[str, list[dict]] = defaultdict(list)
    
    for result in video_results:
        metadata = result.get("video_metadata", {})
        published_at = metadata.get("published_at")
        
        for claim in result.get("claims", []):
            claim_type = claim.get("type", "unknown")
            claim_type_data[claim_type].append({
                "claim": claim,
                "video_id": result.get("video_id"),
                "published_at": published_at,
                "video_metadata": metadata
            })
    
    # Analyze each claim type
    type_trends = {}
    for claim_type, claims in claim_type_data.items():
        # Create pseudo-video results for bucketing
        pseudo_results = []
        for c in claims:
            pseudo_results.append({
                "video_metadata": {"published_at": c["published_at"]},
                "claims": [c["claim"]]
            })
        
        bucketed = bucket_videos(pseudo_results, granularity)
        
        metrics = []
        for bucket_key in sorted(bucketed.keys()):
            metrics.append(calculate_bucket_metrics(bucket_key, bucketed[bucket_key]))
        
        trend = detect_pattern(metrics, primary_metric="claim_count")
        
        type_trends[claim_type] = {
            "total_claims": len(claims),
            "trend": trend.to_dict(),
            "timeline": [m.to_dict() for m in metrics]
        }
    
    return type_trends


def aggregate_by_narrative(
    video_results: list[dict],
    synthesis: dict,
    granularity: Granularity
) -> list[dict]:
    """
    Aggregate trend data by synthesized narratives.
    
    Uses the synthesis output to identify narratives, then tracks
    which videos contribute to each narrative over time.
    
    Args:
        video_results: Per-video extraction results
        synthesis: The synthesis output containing common_topics and shared_narrative
        granularity: Time bucketing granularity
    
    Returns:
        List of narrative trend analyses
    """
    # Extract narratives from synthesis
    # Main narrative comes from shared_narrative
    # Additional narratives from common_topics that appear frequently
    
    narratives = []
    
    # Primary narrative
    shared_narrative = synthesis.get("shared_narrative", "")
    if shared_narrative:
        narratives.append({
            "name": "Primary narrative",
            "description": shared_narrative,
            "source": "shared_narrative"
        })
    
    # Topic-based narratives
    common_topics = synthesis.get("common_topics", [])
    for topic in common_topics[:5]:  # Top 5 common topics
        narratives.append({
            "name": topic,
            "description": f"Discussion around: {topic}",
            "source": "common_topic"
        })
    
    # Analyze each narrative
    narrative_trends = []
    
    for narrative in narratives:
        # Find videos that match this narrative
        matching_videos = []
        
        for result in video_results:
            topics = result.get("topics", [])
            claims = result.get("claims", [])
            
            # Check if video relates to this narrative
            if narrative["source"] == "common_topic":
                # Match by topic
                if narrative["name"].lower() in [t.lower() for t in topics]:
                    matching_videos.append(result)
            else:
                # For shared narrative, include all videos
                matching_videos.append(result)
        
        if not matching_videos:
            continue
        
        # Bucket and analyze
        bucketed = bucket_videos(matching_videos, granularity)
        
        metrics = []
        for bucket_key in sorted(bucketed.keys()):
            metrics.append(calculate_bucket_metrics(bucket_key, bucketed[bucket_key]))
        
        trend = detect_pattern(metrics)
        
        narrative_trends.append({
            "narrative": narrative["name"],
            "description": narrative["description"],
            "video_count": len(matching_videos),
            "pattern": trend.pattern,
            "peak_period": trend.peak_period,
            "confidence": round(trend.confidence, 2),
            "trend_description": trend.description,
            "timeline": [m.to_dict() for m in metrics]
        })
    
    return narrative_trends


def generate_trend_summary(
    video_results: list[dict],
    synthesis: dict,
    granularity: Granularity
) -> dict:
    """
    Generate a complete trend analysis summary.
    
    This is the main entry point for trend analysis, combining all
    aggregation methods into a single output structure.
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
    
    return {
        "granularity": granularity,
        "time_range": time_range,
        "overall": {
            "video_count": len(video_results),
            "trend": overall_trend.to_dict(),
            "timeline": [m.to_dict() for m in overall_metrics]
        },
        "by_narrative": aggregate_by_narrative(video_results, synthesis, granularity),
        "by_topic": aggregate_by_topic(video_results, granularity),
        "by_claim_type": aggregate_by_claim_type(video_results, granularity)
    }
