import json


def build_extraction_prompt(transcript_chunk: str, video_id: str) -> str:
    """
    Prompt for per-video transcript claim extraction.
    Focused on topics + claims only — narrative and trends
    are cross-video concepts handled in synthesis.
    """
    return f"""You are an analytical assistant extracting structured intelligence from a YouTube transcript.

From the transcript below, extract:

1. topics — main subjects discussed (list of short strings)
2. claims — every explicit or implied assertion made. For each claim include:
   - "text": the claim in one clear sentence
   - "type": one of "factual", "prediction", "opinion", "statistic"
   - "confidence": float 0.0–1.0 (how clearly and directly is this stated?)
   - "supporting_quote": a short verbatim phrase from the transcript that supports it

Focus entirely on extracting as many distinct, specific claims as possible.
Do NOT summarize. Do NOT infer a narrative. Just extract claims.

Respond with a SINGLE JSON object. Start with {{ and end with }}. No preamble, no markdown.

Format:
{{
  "video_id": "{video_id}",
  "topics": ["...", "..."],
  "claims": [
    {{
      "text": "...",
      "type": "factual|prediction|opinion|statistic",
      "confidence": 0.85,
      "supporting_quote": "..."
    }}
  ]
}}

Transcript chunk:
{transcript_chunk}
"""


def build_comment_prompt(
    comments: list[dict],
    transcript_claims: list[dict],
    video_id: str
) -> str:
    """
    Prompt for extracting claims from top comments.
    Passes existing transcript claims so the LLM can identify
    new claims vs. ones that support/contradict what was already said.
    Confidence is capped at 0.7 since comments are unverified.
    """
    comments_text = "\n".join([f"- [{c['likes']} likes] {c['text']}" for c in comments])
    existing_claims = json.dumps([c["text"] for c in transcript_claims], indent=2)

    return f"""You are an analytical assistant extracting intelligence from YouTube comments.

You are given:
1. A list of top comments (sorted by likes) from a YouTube video
2. A list of claims already extracted from the video transcript

Your job:
- Extract any NEW claims made in the comments not already covered by the transcript claims
- For each new claim, note whether any other comments support or contradict it
- Skip low-quality comments (spam, jokes, off-topic, pure reactions like "great video!")

For each comment claim include:
  - "text": the claim in one clear sentence
  - "type": one of "factual", "prediction", "opinion", "statistic"
  - "confidence": float 0.0–0.7 (comments are unverified — max is 0.7)
  - "supporting_quote": the exact comment text or phrase that contains this claim
  - "relation_to_transcript": one of "new_claim", "supports_transcript", "contradicts_transcript"

Respond with a SINGLE JSON object. Start with {{ and end with }}. No preamble, no markdown.

Format:
{{
  "video_id": "{video_id}",
  "comment_claims": [
    {{
      "text": "...",
      "type": "factual|prediction|opinion|statistic",
      "confidence": 0.6,
      "supporting_quote": "...",
      "relation_to_transcript": "new_claim|supports_transcript|contradicts_transcript"
    }}
  ]
}}

Existing transcript claims:
{existing_claims}

Top comments:
{comments_text}
"""


def build_synthesis_prompt(all_results: list[dict]) -> str:
    """
    Prompt for cross-video narrative synthesis.
    Extracts distinct narratives and maps them to supporting videos.
    """
    # Build simplified input with just video_id, topics, and claim texts
    simplified = []
    for r in all_results:
        simplified.append({
            "video_id": r.get("video_id"),
            "title": r.get("video_metadata", {}).get("title", ""),
            "topics": r.get("topics", []),
            "claims": [c.get("text") for c in r.get("claims", [])]
        })
    
    structured_input = json.dumps(simplified, indent=2)

    return f"""Synthesize the following {len(all_results)} YouTube video analyses into distinct narratives.

A narrative is a high-level theme or storyline that multiple videos discuss. 
Identify 2-5 distinct narratives and map each to the videos that support it.

RESPOND WITH VALID JSON ONLY. NO PREAMBLE. NO MARKDOWN.

{{
  "narratives": [
    {{
      "id": "narrative_1",
      "name": "Short name for the narrative (3-6 words)",
      "summary": "2-3 sentence description of this narrative",
      "video_ids": ["list", "of", "video_ids", "that", "discuss", "this"]
    }}
  ],
  "high_confidence_claims": [
    {{
      "text": "claim with high confidence",
      "video_id": "...",
      "narrative_id": "narrative_1"
    }}
  ],
  "overall_summary": "2-3 sentence summary of the entire dataset"
}}

Video analyses:
{structured_input}
"""


def build_theme_grouping_prompt(all_results: list[dict]) -> str:
    """
    Pass 1: Group all claims into themes (compressed format).
    Returns theme names and which claims belong to each.
    """
    # Compress claims to minimal format: "video_id: claim text"
    claim_lines = []
    claim_index = 0
    
    for r in all_results:
        video_id = r.get("video_id", "unknown")
        for claim in r.get("claims", []):
            text = claim.get("text", "")
            confidence = claim.get("confidence", 0.5)
            claim_lines.append(f"[{claim_index}] ({video_id}, conf:{confidence:.1f}) {text}")
            claim_index += 1
    
    claims_text = "\n".join(claim_lines)
    
    return f"""Analyze these {claim_index} claims from {len(all_results)} videos and group them into 3-7 distinct themes.

CLAIMS:
{claims_text}

For each theme, list the claim indices [N] that belong to it.

RESPOND WITH VALID JSON ONLY. NO PREAMBLE. NO MARKDOWN.

{{
  "themes": [
    {{
      "id": "theme_1",
      "name": "Short theme name (3-6 words)",
      "claim_indices": [0, 5, 12, 23],
      "summary": "One sentence describing this theme"
    }}
  ]
}}
"""


def build_narrative_expansion_prompt(
    theme: dict,
    claims: list[dict],
    video_lookup: dict[str, dict]
) -> str:
    """
    Pass 2: Expand a single theme into a detailed narrative.
    """
    # Build claim details for this theme
    claim_details = []
    video_ids = set()
    
    for claim in claims:
        video_id = claim.get("video_id", "unknown")
        video_ids.add(video_id)
        title = video_lookup.get(video_id, {}).get("title", "")
        claim_details.append(f"- {claim.get('text', '')} (from: {title})")
    
    claims_text = "\n".join(claim_details)
    
    return f"""Expand this theme into a detailed narrative.

THEME: {theme.get('name', '')}
INITIAL SUMMARY: {theme.get('summary', '')}

SUPPORTING CLAIMS:
{claims_text}

RESPOND WITH VALID JSON ONLY. NO PREAMBLE. NO MARKDOWN.

{{
  "id": "{theme.get('id', '')}",
  "name": "{theme.get('name', '')}",
  "summary": "2-4 sentence detailed description synthesizing all claims",
  "video_ids": {json.dumps(list(video_ids))},
  "key_claims": ["most important claim 1", "most important claim 2", "most important claim 3"],
  "confidence": 0.0-1.0
}}
"""





