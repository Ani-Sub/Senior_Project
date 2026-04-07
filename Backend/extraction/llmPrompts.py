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
    Receives all structured per-video results and produces
    a unified intelligence summary.
    """
    structured_input = json.dumps(all_results, indent=2)

    return f"""You are a JSON-generating assistant. Synthesize the following YouTube video analyses.

Below is structured data extracted from {len(all_results)} videos.

RESPOND WITH VALID JSON ONLY. NO PREAMBLE. NO EXPLANATION. NO MARKDOWN.
YOUR ENTIRE RESPONSE MUST START WITH {{ AND END WITH }}. NOTHING ELSE.

The JSON must have exactly these keys:
{{
  "common_topics": ["list of topics appearing across multiple videos"],
  "repeated_claims": [
    {{
      "text": "claim that appears in 2+ videos",
      "videos": ["video_id_1", "video_id_2"],
      "type": "factual|prediction|opinion|statistic"
    }}
  ],
  "high_confidence_claims": [
    {{
      "text": "claim with confidence >= 0.75",
      "video_id": "...",
      "confidence": 0.9,
      "supporting_quote": "..."
    }}
  ],
  "shared_narrative": "2-3 sentence overarching story across all videos",
  "overall_trends": ["dominant patterns across the dataset"]
}}

Video analyses:
{structured_input}
"""





