"""
Confidence scoring for claims using cross-video agreement and language analysis.
"""

from collections import defaultdict
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

# Claim type base weights
TYPE_WEIGHTS = {
    "statistic": 0.7,
    "factual": 0.6,
    "prediction": 0.4,
    "opinion": 0.3,
}

# Language adjustments
DEFINITIVE_WORDS = ["will", "definitely", "proven", "confirmed", "always", "never", "fact", "certainly"]
HEDGING_WORDS = ["might", "maybe", "could", "possibly", "perhaps", "some say", "reportedly", "appears", "seems"]
STATISTIC_MARKERS = ["percent", "%", "million", "billion", "trillion", "study", "research", "data"]


def adjust_by_language(claim_text: str, base_confidence: float) -> float:
    """Adjust confidence based on language patterns."""
    text = claim_text.lower()
    adjustment = 0.0
    
    # Definitive language → boost
    if any(word in text for word in DEFINITIVE_WORDS):
        adjustment += 0.1
    
    # Hedging language → reduce
    if any(word in text for word in HEDGING_WORDS):
        adjustment -= 0.15
    
    # Statistics/data references → boost (more verifiable)
    if any(marker in text for marker in STATISTIC_MARKERS):
        adjustment += 0.1
    
    return max(0.1, min(1.0, base_confidence + adjustment))


def adjust_by_type(claim_type: str, llm_confidence: float) -> float:
    """Weight confidence by claim type."""
    type_weight = TYPE_WEIGHTS.get(claim_type, 0.5)
    # Average the LLM confidence with type weight
    return (llm_confidence + type_weight) / 2


def cluster_similar_claims(
    all_claims: list[dict],
    similarity_threshold: float = 0.7
) -> list[list[dict]]:
    """
    Group similar claims together using TF-IDF cosine similarity.
    Caps input at 200 highest-confidence claims to keep clustering fast.

    Returns:
        List of clusters, each cluster is a list of similar claims
    """
    if not all_claims:
        return []

    # Cap to 200 highest-confidence claims to bound worst-case runtime
    working = sorted(all_claims, key=lambda c: c.get("confidence", 0), reverse=True)[:200]

    texts = [c.get("text", "") or "" for c in working]
    vect = TfidfVectorizer(stop_words="english")
    matrix = vect.fit_transform(texts)
    sim = cosine_similarity(matrix)  # (n, n) numpy array — O(1) per lookup

    clusters = []
    used = set()

    for i, claim in enumerate(working):
        if i in used:
            continue

        cluster = [claim]
        used.add(i)

        for j, other in enumerate(working):
            if j in used:
                continue
            # Only cluster across different videos (cross-video agreement)
            if claim.get("video_id") == other.get("video_id"):
                continue
            if sim[i, j] >= similarity_threshold:
                cluster.append(other)
                used.add(j)

        clusters.append(cluster)

    return clusters


def boost_confidence_by_agreement(
    all_results: list[dict],
    similarity_threshold: float = 0.7
) -> list[dict]:
    """
    Boost claim confidence based on cross-video agreement.
    
    Claims that appear in multiple videos get confidence boost.
    Also applies language and type adjustments.
    
    Args:
        all_results: List of video analysis results
        similarity_threshold: Min similarity to consider claims the same
    
    Returns:
        Updated results with adjusted confidence scores
    """
    # Collect all claims with video_id
    all_claims = []
    claim_to_result_idx = {}  # Map claim index to (result_idx, claim_idx)
    
    for r_idx, result in enumerate(all_results):
        for c_idx, claim in enumerate(result.get("claims", [])):
            claim_copy = claim.copy()
            claim_copy["video_id"] = result.get("video_id")
            claim_copy["_result_idx"] = r_idx
            claim_copy["_claim_idx"] = c_idx
            all_claims.append(claim_copy)
    
    if not all_claims:
        return all_results
    
    # Cluster similar claims
    clusters = cluster_similar_claims(all_claims, similarity_threshold)
    
    # Count cross-video agreement and build boost map
    boost_map = {}  # (result_idx, claim_idx) -> boost_amount
    
    for cluster in clusters:
        # Count unique videos in cluster
        unique_videos = set(c.get("video_id") for c in cluster)
        video_count = len(unique_videos)
        
        # Calculate boost based on agreement
        if video_count >= 4:
            boost = 0.25
        elif video_count >= 3:
            boost = 0.2
        elif video_count >= 2:
            boost = 0.1
        else:
            boost = 0.0
        
        # Apply boost to all claims in cluster
        for claim in cluster:
            key = (claim["_result_idx"], claim["_claim_idx"])
            boost_map[key] = boost
    
    # Apply adjustments to all claims
    adjusted_count = 0
    
    for r_idx, result in enumerate(all_results):
        for c_idx, claim in enumerate(result.get("claims", [])):
            original = claim.get("confidence", 0.5)
            
            # 1. Adjust by claim type
            claim_type = claim.get("type", "factual")
            adjusted = adjust_by_type(claim_type, original)
            
            # 2. Adjust by language
            claim_text = claim.get("text", "")
            adjusted = adjust_by_language(claim_text, adjusted)
            
            # 3. Boost by cross-video agreement
            key = (r_idx, c_idx)
            boost = boost_map.get(key, 0.0)
            adjusted = min(1.0, adjusted + boost)
            
            # Update claim
            if adjusted != original:
                adjusted_count += 1
            claim["confidence"] = round(adjusted, 2)
            claim["agreement_boost"] = round(boost, 2)
    
    log.info(f"  → Adjusted confidence for {adjusted_count} claims")
    log.info(f"  → Found {sum(1 for c in clusters if len(set(x.get('video_id') for x in c)) > 1)} cross-video agreements")
    
    return all_results


def get_top_claims(
    all_results: list[dict],
    max_claims: int = 50,
    min_confidence: float = 0.4
) -> list[dict]:
    """
    Get top claims by confidence for synthesis.
    
    Args:
        all_results: List of video analysis results
        max_claims: Maximum claims to return
        min_confidence: Minimum confidence threshold
    
    Returns:
        List of top claims with video_id attached
    """
    all_claims = []
    
    for result in all_results:
        video_id = result.get("video_id")
        for claim in result.get("claims", []):
            if claim.get("confidence", 0) >= min_confidence:
                claim_copy = claim.copy()
                claim_copy["video_id"] = video_id
                all_claims.append(claim_copy)
    
    # Sort by confidence descending
    all_claims.sort(key=lambda c: c.get("confidence", 0), reverse=True)
    
    return all_claims[:max_claims]
