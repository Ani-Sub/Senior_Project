"""
Video analysis module for extracting claims from transcripts and comments.
"""

import logging
import requests
from config import LLM_URL, LLM_MODEL, LLM_NUM_PREDICT
from utility.parser import parse_json_response
from utility.chunker import chunk_text
from utility.embeddings import get_embedding, check_embedding_service
from extraction.llmPrompts import (
    build_extraction_prompt,
    build_comment_prompt,
    build_synthesis_prompt
)

log = logging.getLogger(__name__)

# Check embedding service once at module load
_embedding_available = None


def is_embedding_available() -> bool:
    """Check if embedding service is available (cached)."""
    global _embedding_available
    if _embedding_available is None:
        _embedding_available = check_embedding_service()
        if _embedding_available:
            log.info("Embedding service available")
        else:
            log.warning("Embedding service unavailable - claims will not have embeddings")
    return _embedding_available


def call_llm(prompt: str, num_predict: int | None = None) -> str | None:
    """Send a prompt to the local Ollama instance and return the response string."""
    if num_predict is None:
        num_predict = LLM_NUM_PREDICT
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": num_predict
                }
            },
            timeout=180
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.RequestException as e:
        log.error(f"LLM call failed: {e}")
        return None


def analyze_video(
    video_id: str,
    transcript: str,
    comments: list[dict],
    generate_embeddings: bool = True
) -> dict | None:
    """
    Extract claims from a single video's transcript and comments.
    
    - Transcript is chunked and processed in passes
    - Comments are processed after transcript so they can reference existing claims
    - Every claim is tagged with its source ("transcript" or "comment")
    - Optionally generates embeddings for each claim
    """
    chunks = chunk_text(transcript)
    log.info(f"  → {len(chunks)} chunk(s) for video {video_id}")

    all_topics = []
    all_claims = []
    
    # Check if embeddings should be generated
    do_embeddings = generate_embeddings and is_embedding_available()

    # -- Transcript extraction --
    for i, chunk in enumerate(chunks):
        log.info(f"  → Extracting transcript chunk {i + 1}/{len(chunks)}")
        prompt = build_extraction_prompt(chunk, video_id)
        raw = call_llm(prompt)

        if not raw:
            log.warning(f"  → No LLM response for chunk {i + 1}")
            continue

        parsed = parse_json_response(raw)

        if not parsed:
            log.warning(f"  → Skipping unparseable chunk {i + 1}")
            continue

        all_topics.extend(parsed.get("topics", []))
        for claim in parsed.get("claims", []):
            claim["source"] = "transcript"
        all_claims.extend(parsed.get("claims", []))

    if not all_claims:
        log.warning(f"  → No transcript claims extracted for {video_id}")
        return None

    # -- Comment extraction --
    if comments:
        log.info(f"  → Extracting claims from {len(comments)} comments")
        comment_prompt = build_comment_prompt(comments, all_claims, video_id)
        raw = call_llm(comment_prompt)

        if raw:
            parsed = parse_json_response(raw)

            if parsed:
                comment_claims = parsed.get("comment_claims", [])
                for claim in comment_claims:
                    claim["source"] = "comment"
                all_claims.extend(comment_claims)
                log.info(f"  → Added {len(comment_claims)} comment claims")
            else:
                log.warning("  → Comment extraction produced unparseable output")
        else:
            log.warning("  → No LLM response for comments")
    else:
        log.info("  → No comments available for this video")

    # -- Generate embeddings for claims --
    if do_embeddings:
        log.info(f"  → Generating embeddings for {len(all_claims)} claims")
        embedded_count = 0
        for claim in all_claims:
            claim_text = claim.get("text", "")
            if claim_text:
                embedding = get_embedding(claim_text)
                claim["embedding"] = embedding
                if embedding:
                    embedded_count += 1
        log.info(f"  → Generated {embedded_count}/{len(all_claims)} embeddings")

    transcript_count = sum(1 for c in all_claims if c.get("source") == "transcript")
    comment_count = sum(1 for c in all_claims if c.get("source") == "comment")

    return {
        "video_id": video_id,
        "topics": list(set(all_topics)),
        "claims": all_claims,
        "claim_count": len(all_claims),
        "transcript_claim_count": transcript_count,
        "comment_claim_count": comment_count
    }


def synthesize_trends(all_results: list[dict]) -> dict | None:
    """
    Synthesize claims across all videos into a unified narrative.
    
    Produces: common topics, repeated claims, high-confidence claims,
    shared narrative, and overall trends.
    """
    if not all_results:
        log.warning("No results to synthesize.")
        return None

    prompt = build_synthesis_prompt(all_results)
    raw = call_llm(prompt)

    if not raw:
        log.error("No LLM response for synthesis")
        return None

    parsed = parse_json_response(raw)

    if not parsed:
        log.error("Synthesis output could not be parsed as JSON.")
        return None

    return parsed
