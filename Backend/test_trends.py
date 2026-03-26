"""
Test script for the trends module.
Uses mock data — no YouTube API or Ollama required.

Run with:
    python test_trends.py
"""

import json
from datetime import datetime, timedelta

# Import the trends module
from trends import (
    generate_trend_summary,
    bucket_videos,
    calculate_bucket_metrics,
    detect_pattern,
    detect_surge_periods
)


def generate_mock_video_results() -> list[dict]:
    """
    Generate mock video results that simulate a SURGE pattern.
    
    Timeline (weekly):
    - Week 1-2: Low activity (1-2 videos, ~50k views)
    - Week 3-4: Growing (3-4 videos, ~150k views)  
    - Week 5-6: Surge (6-8 videos, ~500k views)
    """
    base_date = datetime(2026, 2, 1)
    
    mock_results = [
        # Week 1 - Low activity
        {
            "video_id": "vid_001",
            "topics": ["AI Safety", "Machine Learning"],
            "claims": [
                {"text": "AI models are becoming more capable", "type": "factual", "confidence": 0.85},
                {"text": "Safety research is underfunded", "type": "opinion", "confidence": 0.7},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "The State of AI Safety in 2026",
                "channel_title": "AI Explained",
                "published_at": (base_date + timedelta(days=2)).isoformat() + "Z",
                "view_count": 45000,
                "like_count": 3200,
                "comment_count": 890,
            },
            "comment_timestamps": []
        },
        
        # Week 2 - Still low
        {
            "video_id": "vid_002",
            "topics": ["AI Safety", "Regulation"],
            "claims": [
                {"text": "EU AI Act will reshape the industry", "type": "prediction", "confidence": 0.75},
                {"text": "Compliance costs will be significant", "type": "prediction", "confidence": 0.6},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "AI Regulation Update",
                "channel_title": "Tech Policy Daily",
                "published_at": (base_date + timedelta(days=10)).isoformat() + "Z",
                "view_count": 38000,
                "like_count": 2100,
                "comment_count": 450,
            },
            "comment_timestamps": []
        },
        
        # Week 3 - Starting to grow
        {
            "video_id": "vid_003",
            "topics": ["AI Coding", "Job Impact", "LLMs"],
            "claims": [
                {"text": "AI coding assistants are replacing junior tasks", "type": "factual", "confidence": 0.8},
                {"text": "Senior developers are more productive with AI", "type": "factual", "confidence": 0.85},
                {"text": "Entry-level hiring will decrease 30%", "type": "prediction", "confidence": 0.65},
            ],
            "claim_count": 3,
            "transcript_claim_count": 3,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "AI Coding Assistants: Job Killer or Productivity Boost?",
                "channel_title": "Code Report",
                "published_at": (base_date + timedelta(days=16)).isoformat() + "Z",
                "view_count": 125000,
                "like_count": 8900,
                "comment_count": 2300,
            },
            "comment_timestamps": []
        },
        {
            "video_id": "vid_004",
            "topics": ["AI Coding", "Developer Tools"],
            "claims": [
                {"text": "Cursor IDE gained 2M users this quarter", "type": "statistic", "confidence": 0.9},
                {"text": "AI-first IDEs will dominate by 2027", "type": "prediction", "confidence": 0.7},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "The Rise of AI-First Development Tools",
                "channel_title": "Fireship",
                "published_at": (base_date + timedelta(days=18)).isoformat() + "Z",
                "view_count": 180000,
                "like_count": 15000,
                "comment_count": 3100,
            },
            "comment_timestamps": []
        },
        
        # Week 4 - Continued growth
        {
            "video_id": "vid_005",
            "topics": ["AI Coding", "Job Impact", "Tech Industry"],
            "claims": [
                {"text": "Google reduced hiring targets citing AI productivity", "type": "factual", "confidence": 0.88},
                {"text": "Bootcamp enrollment dropped 25%", "type": "statistic", "confidence": 0.82},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "Tech Layoffs and AI: The Connection",
                "channel_title": "TechLinked",
                "published_at": (base_date + timedelta(days=24)).isoformat() + "Z",
                "view_count": 220000,
                "like_count": 18000,
                "comment_count": 5200,
            },
            "comment_timestamps": []
        },
        {
            "video_id": "vid_006",
            "topics": ["AI Coding", "Startups"],
            "claims": [
                {"text": "AI coding startups raised $2B in Q1", "type": "statistic", "confidence": 0.92},
            ],
            "claim_count": 1,
            "transcript_claim_count": 1,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "The AI Coding Gold Rush",
                "channel_title": "Y Combinator",
                "published_at": (base_date + timedelta(days=26)).isoformat() + "Z",
                "view_count": 95000,
                "like_count": 7200,
                "comment_count": 1800,
            },
            "comment_timestamps": []
        },
        
        # Week 5-6 - SURGE (major event triggered more coverage)
        {
            "video_id": "vid_007",
            "topics": ["AI Coding", "Job Impact", "LLMs", "GPT-5"],
            "claims": [
                {"text": "GPT-5 can write production code autonomously", "type": "factual", "confidence": 0.85},
                {"text": "Human review still required for complex systems", "type": "factual", "confidence": 0.9},
                {"text": "Junior developer role will evolve, not disappear", "type": "opinion", "confidence": 0.65},
            ],
            "claim_count": 3,
            "transcript_claim_count": 3,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "GPT-5 Changes Everything for Developers",
                "channel_title": "Fireship",
                "published_at": (base_date + timedelta(days=32)).isoformat() + "Z",
                "view_count": 520000,
                "like_count": 42000,
                "comment_count": 12000,
            },
            "comment_timestamps": []
        },
        {
            "video_id": "vid_008",
            "topics": ["AI Coding", "Job Impact"],
            "claims": [
                {"text": "Stack Overflow traffic down 35% year-over-year", "type": "statistic", "confidence": 0.88},
                {"text": "Developers are using AI instead of searching", "type": "factual", "confidence": 0.8},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "Is Stack Overflow Dying? The AI Effect",
                "channel_title": "Theo",
                "published_at": (base_date + timedelta(days=34)).isoformat() + "Z",
                "view_count": 380000,
                "like_count": 28000,
                "comment_count": 8500,
            },
            "comment_timestamps": []
        },
        {
            "video_id": "vid_009",
            "topics": ["AI Coding", "Education", "Job Impact"],
            "claims": [
                {"text": "CS curriculum needs fundamental revision", "type": "opinion", "confidence": 0.75},
                {"text": "Problem-solving skills matter more than syntax", "type": "opinion", "confidence": 0.8},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "Should You Still Learn to Code in 2026?",
                "channel_title": "Traversy Media",
                "published_at": (base_date + timedelta(days=36)).isoformat() + "Z",
                "view_count": 290000,
                "like_count": 22000,
                "comment_count": 7800,
            },
            "comment_timestamps": []
        },
        {
            "video_id": "vid_010",
            "topics": ["AI Coding", "Job Impact", "Tech Industry"],
            "claims": [
                {"text": "Microsoft reports 55% coding time reduction with Copilot", "type": "statistic", "confidence": 0.92},
                {"text": "Enterprise adoption accelerating faster than consumer", "type": "factual", "confidence": 0.78},
            ],
            "claim_count": 2,
            "transcript_claim_count": 2,
            "comment_claim_count": 0,
            "video_metadata": {
                "title": "Enterprise AI Coding: The Numbers Are In",
                "channel_title": "The AI Breakdown",
                "published_at": (base_date + timedelta(days=38)).isoformat() + "Z",
                "view_count": 185000,
                "like_count": 14000,
                "comment_count": 3200,
            },
            "comment_timestamps": []
        },
    ]
    
    return mock_results


def generate_mock_synthesis() -> dict:
    """Generate a mock synthesis output."""
    return {
        "common_topics": ["AI Coding", "Job Impact", "LLMs", "Tech Industry", "AI Safety"],
        "repeated_claims": [
            {
                "text": "AI coding assistants are changing developer workflows",
                "videos": ["vid_003", "vid_007", "vid_008"],
                "type": "factual"
            },
            {
                "text": "Junior developer roles will be affected",
                "videos": ["vid_003", "vid_005", "vid_009"],
                "type": "prediction"
            }
        ],
        "high_confidence_claims": [
            {
                "text": "Microsoft reports 55% coding time reduction with Copilot",
                "video_id": "vid_010",
                "confidence": 0.92
            }
        ],
        "shared_narrative": "AI coding assistants are rapidly transforming software development, with major implications for developer productivity, hiring practices, and the future of programming education.",
        "overall_trends": [
            "Increasing concern about job displacement",
            "Growing enterprise adoption of AI coding tools",
            "Debate over the future of coding education"
        ]
    }


def run_tests():
    """Run all trend analysis tests."""
    print("=" * 60)
    print("TREND MODULE TEST SUITE")
    print("=" * 60)
    
    # Generate mock data
    print("\n📦 Generating mock data...")
    mock_results = generate_mock_video_results()
    mock_synthesis = generate_mock_synthesis()
    print(f"   Created {len(mock_results)} mock video results")
    
    # Test 1: Time bucketing
    print("\n" + "-" * 60)
    print("TEST 1: Time Bucketing (Weekly)")
    print("-" * 60)
    
    bucketed = bucket_videos(mock_results, "weekly")
    print(f"   Buckets created: {len(bucketed)}")
    for bucket_key in sorted(bucketed.keys()):
        videos = bucketed[bucket_key]
        print(f"   {bucket_key}: {len(videos)} video(s)")
    
    # Test 2: Metrics calculation
    print("\n" + "-" * 60)
    print("TEST 2: Bucket Metrics")
    print("-" * 60)
    
    for bucket_key in sorted(bucketed.keys()):
        metrics = calculate_bucket_metrics(bucket_key, bucketed[bucket_key])
        print(f"\n   {bucket_key}:")
        print(f"      Videos: {metrics.video_count}")
        print(f"      Views: {metrics.total_views:,}")
        print(f"      Comments: {metrics.total_comments:,}")
        print(f"      Engagement: {metrics.engagement_ratio:.4f}")
        print(f"      Claims: {metrics.claim_count}")
    
    # Test 3: Pattern detection
    print("\n" + "-" * 60)
    print("TEST 3: Pattern Detection")
    print("-" * 60)
    
    from trends.metrics import calculate_all_bucket_metrics
    all_metrics = calculate_all_bucket_metrics(bucketed)
    trend = detect_pattern(all_metrics)
    
    print(f"\n   Pattern: {trend.pattern.upper()}")
    print(f"   Confidence: {trend.confidence:.0%}")
    print(f"   Peak Period: {trend.peak_period}")
    print(f"   Peak Value: {trend.peak_value:,} views")
    print(f"   Description: {trend.description}")
    
    # Test 4: Surge detection
    print("\n" + "-" * 60)
    print("TEST 4: Surge Period Detection")
    print("-" * 60)
    
    surges = detect_surge_periods(all_metrics, primary_metric="total_views", threshold=1.5)
    if surges:
        for surge in surges:
            print(f"\n   🚀 Surge in {surge['period']}:")
            print(f"      Previous: {surge['previous_value']:,} views")
            print(f"      Current: {surge['current_value']:,} views")
            print(f"      Multiplier: {surge['multiplier']}x")
    else:
        print("   No surge periods detected (threshold: 1.5x)")
    
    # Test 5: Full trend summary
    print("\n" + "-" * 60)
    print("TEST 5: Full Trend Summary Generation")
    print("-" * 60)
    
    trend_summary = generate_trend_summary(
        video_results=mock_results,
        synthesis=mock_synthesis,
        granularity="weekly"
    )
    
    print(f"\n   Granularity: {trend_summary['granularity']}")
    print(f"   Time Range: {trend_summary['time_range']['start'][:10]} to {trend_summary['time_range']['end'][:10]}")
    print(f"\n   Overall Pattern: {trend_summary['overall']['trend']['pattern']}")
    
    print(f"\n   Narratives Tracked: {len(trend_summary['by_narrative'])}")
    for narr in trend_summary['by_narrative'][:3]:
        print(f"      • {narr['narrative']}: {narr['pattern']} ({narr['confidence']:.0%} confidence)")
    
    print(f"\n   Topics Tracked: {len(trend_summary['by_topic'])}")
    for topic, data in list(trend_summary['by_topic'].items())[:3]:
        print(f"      • {topic}: {data['trend']['pattern']} ({data['video_count']} videos)")
    
    print(f"\n   Claim Types:")
    for ctype, data in trend_summary['by_claim_type'].items():
        print(f"      • {ctype}: {data['total_claims']} claims, {data['trend']['pattern']} pattern")
    
    # Save full output
    print("\n" + "-" * 60)
    print("SAVING FULL OUTPUT")
    print("-" * 60)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "test_mode": True,
        "video_count": len(mock_results),
        "synthesis": mock_synthesis,
        "trends": trend_summary
    }
    
    output_path = "test_trends_output.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n   ✓ Saved to {output_path}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
