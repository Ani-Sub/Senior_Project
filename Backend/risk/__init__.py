"""
Risk assessment module for YouTube Intelligence System.

Provides hybrid risk detection (keyword + LLM) for content analysis:
- Self-harm references
- Violence or threats
- Illegal activities (fraud, drugs, hacking)
- Misinformation or harmful advice
- Hate speech or harassment
- Toxicity
- Scams
"""

from risk.keywords import (
    RiskCategory,
    RISK_CATEGORIES,
    RISK_KEYWORDS,
    get_category_description
)

from risk.detector import (
    RiskFlag,
    VideoRiskAssessment,
    assess_video_risk,
    scan_text_keywords,
    calculate_risk_score
)

from risk.aggregator import (
    AggregateRiskAssessment,
    aggregate_risk_assessments,
    generate_risk_summary
)

__all__ = [
    # Types
    "RiskCategory",
    "RiskFlag",
    "VideoRiskAssessment",
    "AggregateRiskAssessment",
    # Constants
    "RISK_CATEGORIES",
    "RISK_KEYWORDS",
    # Functions
    "get_category_description",
    "assess_video_risk",
    "scan_text_keywords",
    "calculate_risk_score",
    "aggregate_risk_assessments",
    "generate_risk_summary",
]
