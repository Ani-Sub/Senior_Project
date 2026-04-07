import json
import logging
import requests
from config import LLM_URL, LLM_MODEL, LLM_NUM_PREDICT
from utility.parser import parse_json_response
from utility.chunker import chunk_text
from utility.debugLog import (
    log_llm_prompt,
    log_llm_response,
    log_llm_synthesis_prompt,
    log_llm_synthesis_response
)
from extraction.llmPrompts import (
    build_extraction_prompt,
    build_comment_prompt,
    build_synthesis_prompt
)

log = logging.getLogger(__name__)


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
            timeout=180  # Increased timeout for longer responses
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.RequestException as e:
        log.error(f"LLM call failed: {e}")
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

        log_llm_prompt("transcript", video_id, i + 1, prompt)
        raw = call_llm(prompt)

        if not raw:
            log_llm_response("transcript", video_id, i + 1, "(no response)", None)
            continue

        parsed = parse_json_response(raw)
        log_llm_response("transcript", video_id, i + 1, raw, parsed)

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

        log_llm_prompt("comments", video_id, None, comment_prompt)
        raw = call_llm(comment_prompt)

        if raw:
            parsed = parse_json_response(raw)
            log_llm_response("comments", video_id, None, raw, parsed)

            if parsed:
                comment_claims = parsed.get("comment_claims", [])
                for claim in comment_claims:
                    claim["source"] = "comment"
                all_claims.extend(comment_claims)
                log.info(f"  → Added {len(comment_claims)} comment claims")
            else:
                log.warning("  → Comment extraction produced unparseable output")
        else:
            log_llm_response("comments", video_id, None, "(no response)", None)
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


def process_videos(
    videos: list[dict], 
    max_comments: int = 30,
    assess_risk: bool = True,
    llm_verify_risk: bool = True
) -> list[dict]:
    """
    Run the full extraction pipeline across a list of video metadata dicts.
    
    Each video dict should contain:
        video_id, title, channel_title, published_at,
        view_count, like_count, comment_count, duration
    
    Args:
        videos: List of video metadata dicts
        max_comments: Maximum comments to fetch per video
        assess_risk: Whether to run risk assessment
        llm_verify_risk: Whether to use LLM for borderline risk cases
    
    Returns:
        Results with video metadata, claims, and risk assessment.
    """
    from ytAPI.transcriptExtract import get_transcript
    from ytAPI.commentExtract import get_comments

    all_results = []
    for video in videos:
        vid = video["video_id"]
        log.info(f"\nProcessing video: {vid}")

        transcript = get_transcript(vid)
        if not transcript:
            continue

        comments = get_comments(vid, max_comments=max_comments)
        result = analyze_video(vid, transcript, comments)

        if result:
            # Merge video metadata into result for trend analysis
            result["video_metadata"] = {
                "title": video.get("title"),
                "channel_title": video.get("channel_title"),
                "published_at": video.get("published_at"),
                "view_count": video.get("view_count"),
                "like_count": video.get("like_count"),
                "comment_count": video.get("comment_count"),
                "duration": video.get("duration"),
            }
            # Also store comment timestamps for finer-grained trend analysis
            result["comment_timestamps"] = [c.get("published_at") for c in comments if c.get("published_at")]
            
            # Store raw content for risk assessment
            result["_transcript"] = transcript
            result["_comments"] = comments
            
            all_results.append(result)
            log.info(
                f"  ✓ {result['claim_count']} total claims "
                f"({result['transcript_claim_count']} transcript, "
                f"{result['comment_claim_count']} comments)"
            )

    return all_results


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

    log_llm_synthesis_prompt(prompt)
    raw = call_llm(prompt)

    if not raw:
        log_llm_synthesis_response("(no response)", None)
        return None

    parsed = parse_json_response(raw)
    log_llm_synthesis_response(raw, parsed)

    if not parsed:
        log.error("Synthesis output could not be parsed as JSON.")
        log.debug(f"Raw synthesis output:\n{raw}")
        return None

    return parsed