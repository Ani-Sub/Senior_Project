"""
Video analysis module for extracting claims from transcripts and comments.
"""

import logging
import time
import requests
from config import LLM_URL, LLM_MODEL, LLM_MAX_TOKENS, GROQ_API_KEY
from utility.parser import parse_json_response
from utility.chunker import chunk_text
from extraction.llmPrompts import (
    build_extraction_prompt,
    build_comment_prompt,
    build_synthesis_prompt
)

log = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
RETRY_CODES = {429, 500, 502, 503, 504}  # Rate limit + server errors


def call_llm(prompt: str, max_tokens: int | None = None) -> str | None:
    """Send a prompt to Groq API and return the response string."""
    if max_tokens is None:
        max_tokens = LLM_MAX_TOKENS
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                LLM_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": max_tokens
                },
                timeout=180
            )
            
            # Check for retryable errors
            if response.status_code in RETRY_CODES:
                wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                log.warning(f"Groq API error {response.status_code}, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                log.error(f"Groq API error {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            
            # Extract text from Groq response (OpenAI format)
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content")
            
            log.warning("Groq returned empty response")
            return None
            
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt
                log.warning(f"Request failed: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                continue
            log.error(f"LLM call failed after {MAX_RETRIES} attempts: {e}")
            return None
    
    log.error(f"LLM call failed after {MAX_RETRIES} retries")
    return None


def analyze_video(
    video_id: str,
    transcript: str,
    comments: list[dict]
) -> dict | None:
    """
    Extract claims from a single video's transcript and comments.
    
    - Transcript is chunked and processed in passes
    - Comments are processed after transcript so they can reference existing claims
    - Every claim is tagged with its source ("transcript" or "comment")
    """
    chunks = chunk_text(transcript)
    log.info(f"  → {len(chunks)} chunk(s) for video {video_id}")

    all_topics = []
    all_claims = []

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
    Synthesize claims across all videos into unified narratives.
    
    Uses two-pass approach:
    1. Group all claims into themes (compressed format)
    2. Expand each theme into detailed narrative
    """
    if not all_results:
        log.warning("No results to synthesize.")
        return None
    
    # Count total claims
    total_claims = sum(len(r.get("claims", [])) for r in all_results)
    log.info(f"  → Synthesizing {total_claims} claims from {len(all_results)} videos")
    
    # Build flat list of all claims with video_id
    all_claims = []
    for r in all_results:
        video_id = r.get("video_id")
        for claim in r.get("claims", []):
            claim_copy = claim.copy()
            claim_copy["video_id"] = video_id
            all_claims.append(claim_copy)
    
    # Build video lookup for titles
    video_lookup = {}
    for r in all_results:
        vid = r.get("video_id")
        video_lookup[vid] = {
            "title": r.get("video_metadata", {}).get("title", ""),
            "topics": r.get("topics", [])
        }
    
    # ─── PASS 1: Group claims into themes ───────────────────────────────
    log.info("  → Pass 1: Grouping claims into themes...")
    
    from extraction.llmPrompts import build_theme_grouping_prompt, build_narrative_expansion_prompt
    
    theme_prompt = build_theme_grouping_prompt(all_results)
    theme_response = call_llm(theme_prompt)
    
    if not theme_response:
        log.error("No LLM response for theme grouping")
        return None
    
    themes_parsed = parse_json_response(theme_response)
    
    if not themes_parsed or "themes" not in themes_parsed:
        log.error("Theme grouping output could not be parsed")
        return None
    
    themes = themes_parsed.get("themes", [])
    log.info(f"  → Found {len(themes)} themes")
    
    # ─── PASS 2: Expand each theme into narrative ───────────────────────
    log.info("  → Pass 2: Expanding themes into narratives...")
    
    narratives = []
    high_confidence_claims = []
    
    for theme in themes:
        # Get claims for this theme
        indices = theme.get("claim_indices", [])
        theme_claims = [all_claims[i] for i in indices if i < len(all_claims)]
        
        if not theme_claims:
            continue
        
        # Expand theme
        expand_prompt = build_narrative_expansion_prompt(theme, theme_claims, video_lookup)
        expand_response = call_llm(expand_prompt)
        
        if not expand_response:
            log.warning(f"  → Failed to expand theme: {theme.get('name', 'unknown')}")
            continue
        
        narrative = parse_json_response(expand_response)
        
        if narrative:
            narratives.append(narrative)
            
            # Collect high confidence claims from this narrative
            for claim in theme_claims:
                if claim.get("confidence", 0) >= 0.7:
                    high_confidence_claims.append({
                        "text": claim.get("text"),
                        "video_id": claim.get("video_id"),
                        "narrative_id": narrative.get("id"),
                        "confidence": claim.get("confidence")
                    })
    
    log.info(f"  → Generated {len(narratives)} narratives")
    
    # Build overall summary from narrative summaries
    narrative_summaries = [n.get("summary", "") for n in narratives]
    overall_summary = " ".join(narrative_summaries[:3])  # Combine first 3
    
    return {
        "narratives": narratives,
        "high_confidence_claims": high_confidence_claims[:20],  # Top 20
        "overall_summary": overall_summary,
        "total_claims_processed": total_claims,
        "theme_count": len(themes)
    }
