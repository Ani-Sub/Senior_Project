"""
Hybrid risk detection: keyword scan first, LLM verification for borderline cases.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Literal

from risk.keywords import (
    RiskCategory, 
    RISK_CATEGORIES,
    RISK_KEYWORDS, 
    compile_patterns,
    get_category_description
)

log = logging.getLogger(__name__)


DetectionMethod = Literal["keyword_high", "keyword_medium", "pattern", "llm"]


@dataclass
class RiskFlag:
    """A single detected risk instance."""
    category: RiskCategory
    confidence: float               # 0.0 - 1.0
    source: Literal["transcript", "comment"]
    excerpt: str                    # The flagged text snippet
    context: str                    # Surrounding text for context
    detection_method: DetectionMethod
    matched_term: str = ""          # What triggered the flag
    llm_reasoning: str = ""         # If LLM verified, its explanation
    
    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "category_description": get_category_description(self.category),
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "excerpt": self.excerpt,
            "context": self.context,
            "detection_method": self.detection_method,
            "matched_term": self.matched_term,
            "llm_reasoning": self.llm_reasoning
        }


@dataclass
class VideoRiskAssessment:
    """Risk assessment results for a single video."""
    video_id: str
    risk_score: float = 0.0         # Aggregate score 0.0 - 1.0
    risk_level: Literal["none", "low", "medium", "high", "critical"] = "none"
    flags: list[RiskFlag] = field(default_factory=list)
    transcript_scanned: bool = False
    comments_scanned: int = 0
    
    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "flag_count": len(self.flags),
            "flags": [f.to_dict() for f in self.flags],
            "transcript_scanned": self.transcript_scanned,
            "comments_scanned": self.comments_scanned
        }


def extract_context(text: str, match_start: int, match_end: int, window: int = 100) -> tuple[str, str]:
    """
    Extract the matched excerpt and surrounding context.
    
    Returns:
        (excerpt, context) tuple
    """
    excerpt = text[match_start:match_end]
    
    # Get surrounding context
    ctx_start = max(0, match_start - window)
    ctx_end = min(len(text), match_end + window)
    
    context = text[ctx_start:ctx_end]
    
    # Add ellipsis if truncated
    if ctx_start > 0:
        context = "..." + context
    if ctx_end < len(text):
        context = context + "..."
    
    return excerpt, context


def scan_text_keywords(
    text: str,
    source: Literal["transcript", "comment"],
    video_id: str
) -> list[RiskFlag]:
    """
    Scan text for keyword matches across all risk categories.
    
    Returns list of RiskFlags for all matches found.
    """
    flags = []
    text_lower = text.lower()
    
    for category in RISK_CATEGORIES:
        keywords = RISK_KEYWORDS.get(category)
        if not keywords:
            continue
        
        # Check high confidence keywords
        for keyword in keywords.high_confidence:
            keyword_lower = keyword.lower()
            start = 0
            while True:
                idx = text_lower.find(keyword_lower, start)
                if idx == -1:
                    break
                
                excerpt, context = extract_context(text, idx, idx + len(keyword))
                flags.append(RiskFlag(
                    category=category,
                    confidence=0.9,
                    source=source,
                    excerpt=excerpt,
                    context=context,
                    detection_method="keyword_high",
                    matched_term=keyword
                ))
                start = idx + 1
        
        # Check medium confidence keywords (these may need LLM verification)
        for keyword in keywords.medium_confidence:
            keyword_lower = keyword.lower()
            start = 0
            while True:
                idx = text_lower.find(keyword_lower, start)
                if idx == -1:
                    break
                
                excerpt, context = extract_context(text, idx, idx + len(keyword))
                flags.append(RiskFlag(
                    category=category,
                    confidence=0.5,  # Lower confidence, may need LLM
                    source=source,
                    excerpt=excerpt,
                    context=context,
                    detection_method="keyword_medium",
                    matched_term=keyword
                ))
                start = idx + 1
        
        # Check regex patterns
        for pattern in compile_patterns(category):
            for match in pattern.finditer(text):
                excerpt, context = extract_context(text, match.start(), match.end())
                flags.append(RiskFlag(
                    category=category,
                    confidence=0.7,
                    source=source,
                    excerpt=excerpt,
                    context=context,
                    detection_method="pattern",
                    matched_term=match.group()
                ))
    
    return flags


def deduplicate_flags(flags: list[RiskFlag]) -> list[RiskFlag]:
    """
    Remove duplicate flags for the same excerpt.
    Keeps the flag with highest confidence per excerpt.
    """
    seen: dict[str, RiskFlag] = {}
    
    for flag in flags:
        key = f"{flag.category}:{flag.excerpt[:50]}"
        if key not in seen or flag.confidence > seen[key].confidence:
            seen[key] = flag
    
    return list(seen.values())


def verify_with_llm(
    flags: list[RiskFlag],
    llm_call_fn=None,
    confidence_threshold: float = 0.6
) -> list[RiskFlag]:
    """
    Use LLM to verify borderline flags (confidence < threshold).
    
    Args:
        flags: List of detected flags
        llm_call_fn: Function to call LLM (signature: fn(prompt) -> str)
        confidence_threshold: Flags below this get LLM verification
    
    Returns:
        Updated list with LLM-verified confidence scores
    """
    if not llm_call_fn:
        return flags
    
    borderline = [f for f in flags if f.confidence < confidence_threshold]
    
    if not borderline:
        return flags
    
    log.info(f"  → Verifying {len(borderline)} borderline flags with LLM")
    
    for flag in borderline:
        prompt = build_verification_prompt(flag)
        try:
            response = llm_call_fn(prompt, max_tokens=300)
            if response:
                is_risk, confidence, reasoning = parse_llm_verification(response)
                flag.confidence = confidence
                flag.llm_reasoning = reasoning
                flag.detection_method = "llm"
        except Exception as e:
            log.warning(f"LLM verification failed: {e}")
    
    return flags


def build_verification_prompt(flag: RiskFlag) -> str:
    """Build a prompt for LLM to verify a potential risk flag."""
    return f"""Analyze this text excerpt for potential {flag.category} risk.

Category: {flag.category}
Description: {get_category_description(flag.category)}
Matched term: "{flag.matched_term}"

Context:
"{flag.context}"

Is this actually {flag.category} content, or is it a false positive?
Consider: Is the term used literally or figuratively? Is it educational/reporting vs promoting?

Respond with ONLY a JSON object:
{{"is_risk": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
"""


def parse_llm_verification(response: str) -> tuple[bool, float, str]:
    """Parse LLM verification response."""
    import json
    
    try:
        # Try to extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return (
                data.get("is_risk", False),
                float(data.get("confidence", 0.5)),
                data.get("reasoning", "")
            )
    except (json.JSONDecodeError, ValueError):
        pass
    
    return False, 0.3, "Could not parse LLM response"


def calculate_risk_score(flags: list[RiskFlag]) -> tuple[float, str]:
    """
    Calculate overall risk score and level from flags.
    
    Returns:
        (risk_score, risk_level) tuple
    """
    if not flags:
        return 0.0, "none"
    
    # Weight by confidence and severity
    category_weights = {
        "self_harm": 1.0,
        "violence": 1.0,
        "illegal_activity": 0.9,
        "hate_speech": 0.9,
        "harassment": 0.8,
        "misinformation": 0.7,
        "scam": 0.7,
        "toxicity": 0.5
    }
    
    total_weight = 0.0
    for flag in flags:
        weight = category_weights.get(flag.category, 0.5)
        total_weight += flag.confidence * weight
    
    # Normalize to 0-1 scale (cap at 10 flags for normalization)
    score = min(1.0, total_weight / 5.0)
    
    # Determine risk level
    if score >= 0.8:
        level = "critical"
    elif score >= 0.6:
        level = "high"
    elif score >= 0.4:
        level = "medium"
    elif score >= 0.1:
        level = "low"
    else:
        level = "none"
    
    return score, level


def assess_video_risk(
    video_id: str,
    transcript: str | None = None,
    comments: list[dict] | None = None,
    llm_call_fn=None,
    verify_borderline: bool = True
) -> VideoRiskAssessment:
    """
    Perform full risk assessment on a video's content.
    
    Args:
        video_id: Video identifier
        transcript: Full transcript text
        comments: List of comment dicts with 'text' key
        llm_call_fn: Optional function for LLM verification
        verify_borderline: Whether to use LLM for borderline cases
    
    Returns:
        VideoRiskAssessment with all detected flags
    """
    all_flags = []
    transcript_scanned = False
    comments_scanned = 0
    
    # Scan transcript
    transcript_flag_count = 0
    if transcript:
        transcript_flags = scan_text_keywords(transcript, "transcript", video_id)
        all_flags.extend(transcript_flags)
        transcript_flag_count = len(transcript_flags)
        transcript_scanned = True
        log.info(f"  → Scanned transcript: {transcript_flag_count} potential flags")

    # Scan comments
    if comments:
        for comment in comments:
            comment_text = comment.get("text", "")
            if comment_text:
                comment_flags = scan_text_keywords(comment_text, "comment", video_id)
                all_flags.extend(comment_flags)
                comments_scanned += 1
        log.info(f"  → Scanned {comments_scanned} comments: {len(all_flags) - transcript_flag_count} potential flags")
    
    # Deduplicate
    all_flags = deduplicate_flags(all_flags)
    
    # LLM verification for borderline cases
    if verify_borderline and llm_call_fn and all_flags:
        all_flags = verify_with_llm(all_flags, llm_call_fn)
    
    # Filter out low-confidence flags after verification
    all_flags = [f for f in all_flags if f.confidence >= 0.4]
    
    # Calculate overall risk
    risk_score, risk_level = calculate_risk_score(all_flags)
    
    return VideoRiskAssessment(
        video_id=video_id,
        risk_score=risk_score,
        risk_level=risk_level,
        flags=all_flags,
        transcript_scanned=transcript_scanned,
        comments_scanned=comments_scanned
    )
