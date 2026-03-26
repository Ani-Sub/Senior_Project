"""
Aggregate risk analysis across all videos in a pipeline run.
"""

from dataclasses import dataclass, field
from collections import defaultdict

from risk.keywords import RiskCategory, RISK_CATEGORIES, get_category_description
from risk.detector import VideoRiskAssessment, RiskFlag


@dataclass
class AggregateRiskAssessment:
    """Aggregate risk assessment across all videos."""
    total_videos: int = 0
    videos_with_risks: int = 0
    total_flags: int = 0
    overall_risk_score: float = 0.0
    overall_risk_level: str = "none"
    
    # Distribution by category
    risk_distribution: dict[str, int] = field(default_factory=dict)
    
    # Distribution by risk level
    level_distribution: dict[str, int] = field(default_factory=dict)
    
    # High-risk videos
    high_risk_videos: list[str] = field(default_factory=list)
    critical_risk_videos: list[str] = field(default_factory=list)
    
    # Top excerpts by category (for summary)
    top_excerpts_by_category: dict[str, list[dict]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "total_videos": self.total_videos,
            "videos_with_risks": self.videos_with_risks,
            "total_flags": self.total_flags,
            "overall_risk_score": round(self.overall_risk_score, 2),
            "overall_risk_level": self.overall_risk_level,
            "risk_distribution": self.risk_distribution,
            "risk_distribution_detailed": {
                cat: {
                    "count": self.risk_distribution.get(cat, 0),
                    "description": get_category_description(cat)
                }
                for cat in RISK_CATEGORIES
            },
            "level_distribution": self.level_distribution,
            "high_risk_videos": self.high_risk_videos,
            "critical_risk_videos": self.critical_risk_videos,
            "top_excerpts_by_category": self.top_excerpts_by_category
        }


def aggregate_risk_assessments(
    assessments: list[VideoRiskAssessment],
    top_excerpts_per_category: int = 3
) -> AggregateRiskAssessment:
    """
    Aggregate individual video risk assessments into an overall summary.
    
    Args:
        assessments: List of per-video risk assessments
        top_excerpts_per_category: How many top excerpts to keep per category
    
    Returns:
        AggregateRiskAssessment with overall statistics
    """
    if not assessments:
        return AggregateRiskAssessment()
    
    # Initialize counters
    risk_distribution: dict[str, int] = defaultdict(int)
    level_distribution: dict[str, int] = defaultdict(int)
    category_excerpts: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    
    total_risk_score = 0.0
    videos_with_risks = 0
    total_flags = 0
    high_risk_videos = []
    critical_risk_videos = []
    
    for assessment in assessments:
        # Count by risk level
        level_distribution[assessment.risk_level] += 1
        
        # Track total risk
        total_risk_score += assessment.risk_score
        
        if assessment.flags:
            videos_with_risks += 1
            total_flags += len(assessment.flags)
        
        # Track high/critical risk videos
        if assessment.risk_level == "high":
            high_risk_videos.append(assessment.video_id)
        elif assessment.risk_level == "critical":
            critical_risk_videos.append(assessment.video_id)
        
        # Count by category and collect excerpts
        for flag in assessment.flags:
            risk_distribution[flag.category] += 1
            
            # Store excerpt with confidence for later sorting
            category_excerpts[flag.category].append((
                flag.confidence,
                {
                    "video_id": assessment.video_id,
                    "excerpt": flag.excerpt,
                    "context": flag.context,
                    "confidence": round(flag.confidence, 2),
                    "source": flag.source
                }
            ))
    
    # Calculate overall risk score (average)
    overall_risk_score = total_risk_score / len(assessments)
    
    # Determine overall risk level
    if critical_risk_videos:
        overall_risk_level = "critical"
    elif len(high_risk_videos) > len(assessments) * 0.3:
        overall_risk_level = "high"
    elif overall_risk_score >= 0.4:
        overall_risk_level = "medium"
    elif overall_risk_score >= 0.1:
        overall_risk_level = "low"
    else:
        overall_risk_level = "none"
    
    # Get top excerpts per category (sorted by confidence)
    top_excerpts_by_category = {}
    for category, excerpts in category_excerpts.items():
        # Sort by confidence descending
        excerpts.sort(key=lambda x: x[0], reverse=True)
        top_excerpts_by_category[category] = [
            e[1] for e in excerpts[:top_excerpts_per_category]
        ]
    
    return AggregateRiskAssessment(
        total_videos=len(assessments),
        videos_with_risks=videos_with_risks,
        total_flags=total_flags,
        overall_risk_score=overall_risk_score,
        overall_risk_level=overall_risk_level,
        risk_distribution=dict(risk_distribution),
        level_distribution=dict(level_distribution),
        high_risk_videos=high_risk_videos,
        critical_risk_videos=critical_risk_videos,
        top_excerpts_by_category=top_excerpts_by_category
    )


def generate_risk_summary(
    video_results: list[dict],
    per_video_assessments: list[VideoRiskAssessment]
) -> dict:
    """
    Generate a complete risk analysis summary for the pipeline output.
    
    Args:
        video_results: The per-video extraction results
        per_video_assessments: Risk assessments for each video
    
    Returns:
        Dict with per_video and aggregate risk data
    """
    # Create lookup for assessments
    assessment_lookup = {a.video_id: a for a in per_video_assessments}
    
    # Aggregate
    aggregate = aggregate_risk_assessments(per_video_assessments)
    
    # Build per-video risk data (aligned with video_results order)
    per_video_risk = []
    for result in video_results:
        vid = result.get("video_id")
        if vid and vid in assessment_lookup:
            per_video_risk.append(assessment_lookup[vid].to_dict())
    
    return {
        "per_video": per_video_risk,
        "aggregate": aggregate.to_dict()
    }
