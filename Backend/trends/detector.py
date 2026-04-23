"""
Trend pattern detection for narrative activity.
Identifies rising, peaking, declining, and stable patterns in time series data.
"""

from dataclasses import dataclass
from typing import Literal
from trends.metrics import BucketMetrics


# Direction enum values matching Prisma schema
Direction = Literal["rising", "peaking", "declining", "stable"]


@dataclass
class TrendAnalysis:
    """Result of trend pattern detection."""
    pattern: Direction
    confidence: float  # 0.0-1.0, how confident we are in this pattern
    peak_period: str | None  # The period with highest activity
    peak_value: float  # The metric value at peak
    start_period: str
    end_period: str
    total_periods: int
    description: str
    
    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "confidence": round(self.confidence, 2),
            "peak_period": self.peak_period,
            "peak_value": self.peak_value,
            "start_period": self.start_period,
            "end_period": self.end_period,
            "total_periods": self.total_periods,
            "description": self.description
        }


def detect_pattern(
    metrics: list[BucketMetrics],
    primary_metric: str = "total_views",
    rising_threshold: float = 2.0,  # 2x increase = rising
    decline_threshold: float = 0.5  # 50% drop = declining
) -> TrendAnalysis:
    """
    Detect the overall trend pattern in a time series of metrics.
    
    Args:
        metrics: List of BucketMetrics, sorted chronologically
        primary_metric: Which metric to analyze (total_views, video_count, etc.)
        rising_threshold: Multiplier for detecting rising trends (2.0 = 100% increase)
        decline_threshold: Multiplier for detecting declines (0.5 = 50% drop)
    
    Returns:
        TrendAnalysis with pattern classification (rising, peaking, declining, stable)
    """
    if len(metrics) < 2:
        return TrendAnalysis(
            pattern="stable",
            confidence=0.5,
            peak_period=metrics[0].period if metrics else None,
            peak_value=getattr(metrics[0], primary_metric, 0) if metrics else 0,
            start_period=metrics[0].period if metrics else "",
            end_period=metrics[-1].period if metrics else "",
            total_periods=len(metrics),
            description="Not enough data points to detect a trend pattern."
        )
    
    # Extract the time series for the primary metric
    values = [getattr(m, primary_metric, 0) for m in metrics]
    periods = [m.period for m in metrics]
    
    # Find peak
    max_value = max(values)
    max_idx = values.index(max_value)
    peak_period = periods[max_idx]
    
    # Calculate key ratios
    first_value = values[0] if values[0] > 0 else 1
    last_value = values[-1] if values[-1] > 0 else 1
    avg_value = sum(values) / len(values) if values else 1
    
    # Determine pattern based on shape
    first_half_avg = sum(values[:len(values)//2]) / max(len(values)//2, 1)
    second_half_avg = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
    
    # Pattern detection logic
    pattern: Direction
    confidence: float
    description: str
    
    # Check for peaking (rise then fall - peak in the middle)
    if max_idx > 0 and max_idx < len(values) - 1:
        pre_peak_growth = max_value / (values[0] if values[0] > 0 else 1)
        post_peak_decline = values[-1] / max_value if max_value > 0 else 1
        
        if pre_peak_growth >= 1.5 and post_peak_decline <= 0.7:
            pattern = "peaking"
            confidence = min(1.0, pre_peak_growth / 2)
            description = f"Activity peaked at {peak_period}, rising {pre_peak_growth:.1f}x before declining."
            
            return TrendAnalysis(
                pattern=pattern,
                confidence=confidence,
                peak_period=peak_period,
                peak_value=max_value,
                start_period=periods[0],
                end_period=periods[-1],
                total_periods=len(metrics),
                description=description
            )
    
    # Check for rising (significant increase over time)
    if last_value >= first_value * rising_threshold or second_half_avg > first_half_avg * 1.3:
        pattern = "rising"
        if last_value >= first_value * rising_threshold:
            confidence = min(1.0, (last_value / first_value - 1) / (rising_threshold - 1))
            description = f"Activity rising {last_value/first_value:.1f}x from {periods[0]} to {periods[-1]}."
        else:
            confidence = min(1.0, second_half_avg / first_half_avg - 1)
            description = f"Activity is rising, with recent periods showing {second_half_avg/first_half_avg:.1f}x more activity."
    
    # Check for declining (significant drop)
    elif last_value <= first_value * decline_threshold:
        pattern = "declining"
        confidence = min(1.0, (1 - last_value / first_value) / (1 - decline_threshold))
        description = f"Activity declined {(1 - last_value/first_value)*100:.0f}% from {periods[0]} to {periods[-1]}."
    
    # Default to stable
    else:
        pattern = "stable"
        variance = _calculate_variance(values)
        confidence = max(0.0, 1.0 - variance / avg_value) if avg_value > 0 else 0.5
        description = f"Activity remained relatively stable across {len(periods)} periods."
    
    return TrendAnalysis(
        pattern=pattern,
        confidence=confidence,
        peak_period=peak_period,
        peak_value=max_value,
        start_period=periods[0],
        end_period=periods[-1],
        total_periods=len(metrics),
        description=description
    )


def _calculate_variance(values: list[float]) -> float:
    """Calculate variance of a list of values."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def detect_surge_periods(
    metrics: list[BucketMetrics],
    primary_metric: str = "total_views",
    threshold: float = 2.0
) -> list[dict]:
    """
    Find specific periods where activity surged compared to previous period.
    
    Returns list of surge events with before/after values.
    """
    surges = []
    
    for i in range(1, len(metrics)):
        prev_value = getattr(metrics[i-1], primary_metric, 0)
        curr_value = getattr(metrics[i], primary_metric, 0)
        
        if prev_value > 0 and curr_value >= prev_value * threshold:
            surges.append({
                "period": metrics[i].period,
                "previous_period": metrics[i-1].period,
                "previous_value": prev_value,
                "current_value": curr_value,
                "multiplier": round(curr_value / prev_value, 2),
                "metric": primary_metric
            })
    
    return surges


def detect_decline_periods(
    metrics: list[BucketMetrics],
    primary_metric: str = "total_views",
    threshold: float = 0.5
) -> list[dict]:
    """
    Find specific periods where activity dropped significantly.
    
    Returns list of decline events with before/after values.
    """
    declines = []
    
    for i in range(1, len(metrics)):
        prev_value = getattr(metrics[i-1], primary_metric, 0)
        curr_value = getattr(metrics[i], primary_metric, 0)
        
        if prev_value > 0 and curr_value <= prev_value * threshold:
            declines.append({
                "period": metrics[i].period,
                "previous_period": metrics[i-1].period,
                "previous_value": prev_value,
                "current_value": curr_value,
                "decline_pct": round((1 - curr_value / prev_value) * 100, 1),
                "metric": primary_metric
            })
    
    return declines
