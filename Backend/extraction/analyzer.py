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

# Rate limit delay (seconds between calls)
# Groq: 12k TPM, ~2k per call = 6 calls/min = 10s between calls
CALL_DELAY = 10  # seconds between API calls


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
                result = message.get("content")
                
                # Rate limit delay to avoid hitting limits
                time.sleep(CALL_DELAY)
                return result
            
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
    
    Uses batched three-pass approach:
    1. Split claims into batches, get themes per batch
    2. Merge similar themes across batches
    3. Expand each merged theme into detailed narrative
    """
    if not all_results:
        log.warning("No results to synthesize.")
        return None
    
    # Count total claims
    total_claims = sum(len(r.get("claims", [])) for r in all_results)
    log.info(f"  → Synthesizing {total_claims} claims from {len(all_results)} videos")
    
    # Build flat list of all claims with video_id and global index
    all_claims = []
    for r in all_results:
        video_id = r.get("video_id")
        for claim in r.get("claims", []):
            claim_copy = claim.copy()
            claim_copy["video_id"] = video_id
            claim_copy["global_index"] = len(all_claims)
            all_claims.append(claim_copy)
    
    # Build video lookup for titles
    video_lookup = {}
    for r in all_results:
        vid = r.get("video_id")
        video_lookup[vid] = {
            "title": r.get("video_metadata", {}).get("title", ""),
            "topics": r.get("topics", [])
        }
    
    from extraction.llmPrompts import (
        build_batch_theme_prompt,
        build_theme_merge_prompt,
        build_narrative_expansion_prompt
    )
    
    # ─── PASS 1: Batch theme extraction ─────────────────────────────────
    BATCH_SIZE = 50
    batches = [all_claims[i:i + BATCH_SIZE] for i in range(0, len(all_claims), BATCH_SIZE)]
    log.info(f"  → Pass 1: Grouping claims in {len(batches)} batches of ~{BATCH_SIZE}...")
    
    all_batch_themes = []
    
    for batch_idx, batch in enumerate(batches):
        log.info(f"    → Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} claims)")
        
        batch_prompt = build_batch_theme_prompt(batch, batch_idx)
        batch_response = call_llm(batch_prompt)
        
        if not batch_response:
            log.warning(f"    → No response for batch {batch_idx + 1}")
            continue
        
        parsed = parse_json_response(batch_response)
        if parsed and "themes" in parsed:
            # Tag themes with batch index for tracking
            for theme in parsed["themes"]:
                theme["batch_idx"] = batch_idx
            all_batch_themes.extend(parsed["themes"])
    
    if not all_batch_themes:
        log.error("No themes extracted from any batch")
        return None
    
    log.info(f"  → Extracted {len(all_batch_themes)} themes across all batches")
    
    # ─── PASS 2: Merge similar themes ───────────────────────────────────
    if len(batches) > 1:
        log.info("  → Pass 2: Merging similar themes...")
        
        merge_prompt = build_theme_merge_prompt(all_batch_themes)
        merge_response = call_llm(merge_prompt)
        
        if not merge_response:
            log.warning("  → Merge failed, using unmerged themes")
            merged_themes = all_batch_themes
        else:
            parsed = parse_json_response(merge_response)
            if parsed and "merged_themes" in parsed:
                merged_themes = parsed["merged_themes"]
                log.info(f"  → Merged into {len(merged_themes)} themes")
            else:
                merged_themes = all_batch_themes
    else:
        merged_themes = all_batch_themes
    
    # ─── PASS 3: Expand each theme into narrative ───────────────────────
    log.info("  → Pass 3: Expanding themes into narratives...")
    
    narratives = []
    high_confidence_claims = []
    
    for theme in merged_themes:
        # Get claims for this theme (handle both global and batch indices)
        theme_claims = []
        
        # Check for global_indices (from merge) or claim_indices (from batch)
        indices = theme.get("global_indices", theme.get("claim_indices", []))
        
        for idx in indices:
            if isinstance(idx, int) and idx < len(all_claims):
                theme_claims.append(all_claims[idx])
        
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
        "batch_count": len(batches),
        "theme_count": len(merged_themes)
    }
