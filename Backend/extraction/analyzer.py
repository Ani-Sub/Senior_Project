import json
import logging
import requests
from config import LLM_URL, LLM_MODEL
from utility.parser import parse_json_response
from utility.chunker import chunk_text
from extraction.llmPrompts import (
    build_extraction_prompt,
    build_comment_prompt,
    build_synthesis_prompt
)

log = logging.getLogger(__name__)


def call_llm(prompt: str, num_predict: int = 1200) -> str | None:
    """Send a prompt to the local Ollama instance and return the response string."""
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
            timeout=120
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
        raw = call_llm(prompt, num_predict=1500)

        if not raw:
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
        raw = call_llm(comment_prompt, num_predict=1500)

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


def process_videos(video_ids: list[str], max_comments: int = 30) -> list[dict]:
    """Run the full extraction pipeline across a list of video IDs."""
    from ytAPI.transcriptExtract import get_transcript
    from ytAPI.commentExtract import get_comments

    all_results = []
    for vid in video_ids:
        log.info(f"\nProcessing video: {vid}")

        transcript = get_transcript(vid)
        if not transcript:
            continue

        comments = get_comments(vid, max_comments=max_comments)
        result = analyze_video(vid, transcript, comments)

        if result:
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
    raw = call_llm(prompt, num_predict=2000)

    if not raw:
        return None

    parsed = parse_json_response(raw)
    if not parsed:
        log.error("Synthesis output could not be parsed as JSON.")
        log.debug(f"Raw synthesis output:\n{raw}")
        return None

    return parsed