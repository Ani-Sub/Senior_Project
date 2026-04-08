"""
Trend analysis module for YouTube Intelligence System.

Tracks synthesized narratives over time:
- Time bucketing (daily/weekly)
- Activity metrics per period
- Pattern detection (surge/peak/decline/stable)
- Narrative trend aggregation
"""

from trends.temporal import (
    Granularity,
    bucket_videos,
    parse_iso_timestamp,
    get_bucket_key,
    generate_bucket_range
)

from trends.metrics import (
    BucketMetrics,
    calculate_bucket_metrics,
    calculate_all_bucket_metrics,
    calculate_metric_deltas
)

from trends.detector import (
    TrendPattern,
    TrendAnalysis,
    detect_pattern,
    detect_surge_periods,
    detect_decline_periods
)

from trends.aggregator import (
    aggregate_by_narrative,
    generate_trend_summary
)

__all__ = [
    # Types
    "Granularity",
    "TrendPattern",
    "BucketMetrics",
    "TrendAnalysis",
    # Temporal
    "bucket_videos",
    "parse_iso_timestamp",
    "get_bucket_key",
    "generate_bucket_range",
    # Metrics
    "calculate_bucket_metrics",
    "calculate_all_bucket_metrics",
    "calculate_metric_deltas",
    # Detection
    "detect_pattern",
    "detect_surge_periods",
    "detect_decline_periods",
    # Aggregation
    "aggregate_by_narrative",
    "generate_trend_summary",
]
