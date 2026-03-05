# IMPORTANT:: Required libraries and installations:
# pip install youtube-transcript-api
# pip install requests
# pip install google-api-python-client
# pip install python-dotenv



import os
import time
import requests
import json
import re
import logging
from datetime import datetime, timezone, timedelta
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ============================================================
# youtube API key
# ============================================================
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise EnvironmentError("YOUTUBE_API_KEY not set. Add it to your .env file.")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# ============================================================
# Config
#  ============================================================
CHUNK_SIZE = 3000        
CHUNK_OVERLAP = 200      
LLM_MODEL = "llama3"
LLM_URL = "http://localhost:11434/api/generate"


# ============================================================
# safe JSON parser
# ============================================================
def parse_json_response(raw: str) -> dict | None:
    cleaned = re.sub(r"```(?:json)?|```|\*\*.*?\*\*", "", raw).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find and extract the outermost { ... } block
    # Handles cases where LLM adds preamble or multiple separate JSON blocks
    brace_start = cleaned.find("{")
    if brace_start != -1:
        depth = 0
        for i, ch in enumerate(cleaned[brace_start:], start=brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[brace_start:i+1])
                    except json.JSONDecodeError as e:
                        log.warning(f"JSON parse failed: {e}\nRaw preview: {raw[:200]}")
                        return None

    log.warning(f"No JSON object found in response.\nRaw preview: {raw[:200]}")
    return None

# ============================================================
# chunk long transcripts so they fit in context window
# ============================================================
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ============================================================
# timestamp used as published_after filter
# ============================================================
def get_published_after(days: int) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.isoformat()


# ============================================================
# search channels by keyword
# ============================================================
def search_channels(query: str, max_results: int = 15) -> list[str]:
    response = youtube.search().list(
        q=query,
        type="channel",
        part="snippet",
        maxResults=max_results
    ).execute()

    return [item["snippet"]["channelId"] for item in response["items"]]


# ============================================================
# filter channels by subscriber/view thresholds
# ============================================================
def filter_channels(channel_ids: list[str],
                    min_subscribers: int = 50000,
                    min_total_views: int = 1_000_000) -> list[dict]:
    response = youtube.channels().list(
        part="statistics,snippet",
        id=",".join(channel_ids)
    ).execute()

    filtered = []
    for item in response["items"]:
        stats = item["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        if subs >= min_subscribers and views >= min_total_views:
            filtered.append({
                "channel_id": item["id"],
                "title": item["snippet"]["title"],
                "subscribers": subs
            })
    return filtered


# ============================================================
# get recent videos from a channel
# ============================================================
def get_recent_channel_videos(channel_id: str, days: int = 60, max_results: int = 10) -> list[str]:
    published_after = get_published_after(days)
    response = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        type="video",
        order="date",
        publishedAfter=published_after,
        maxResults=max_results
    ).execute()

    return [item["id"]["videoId"] for item in response["items"]]


# ============================================================
# filter videos by views + keyword in title
# ============================================================
def filter_videos(video_ids: list[str],
                  min_views: int = 10000,
                  keywords: list[str] | None = None) -> list[str]:
    if not video_ids:
        return []
    if keywords is None:
        keywords = []

    response = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()

    selected = []
    for item in response["items"]:
        views = int(item["statistics"].get("viewCount", 0))
        title = item["snippet"]["title"].lower()
        if views >= min_views and any(k.lower() in title for k in keywords):
            selected.append(item["id"])
    return selected


# ============================================================
#  full yt pipeline — search → filter channels → filter videos
# ============================================================
def discover_videos(search_keywords: str,
                    channel_sub_min: int,
                    video_view_min: int,
                    video_keywords: list[str],
                    days: int = 60) -> list[str]:
    log.info("Searching channels...")
    channel_ids = search_channels(search_keywords)

    log.info("Filtering channels...")
    channels = filter_channels(channel_ids, min_subscribers=channel_sub_min)

    all_video_ids = []
    for channel in channels:
        log.info(f"Getting recent videos for: {channel['title']}")
        vids = get_recent_channel_videos(channel["channel_id"], days=days, max_results=5)
        filtered = filter_videos(vids, min_views=video_view_min, keywords=video_keywords)
        all_video_ids.extend(filtered)

    return all_video_ids


# ============================================================
# fetch transcript for a video
# ============================================================
def get_transcript(video_id: str) -> str | None:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        time.sleep(2)
        return " ".join([segment.text for segment in transcript])
    except Exception as e:
        log.warning(f"Transcript unavailable for {video_id}: {e}")
        return None

# ============================================================
# fetch top comments for a video (sorted by likes)
# ============================================================
def get_comments(video_id: str, max_comments: int = 30) -> list[dict]:
    try:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            order="relevance",     
            maxResults=min(max_comments, 100),
            textFormat="plainText"
        ).execute()

        comments = []
        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            likes = snippet.get("likeCount", 0)
            text = snippet.get("textDisplay", "").strip()

            if len(text) < 20:
                continue

            comments.append({
                "text": text,
                "likes": likes
            })

        comments.sort(key=lambda x: x["likes"], reverse=True)
        log.info(f"  → Fetched {len(comments)} comments for {video_id}")
        return comments[:max_comments]

    except Exception as e:
        log.warning(f"Comments unavailable for {video_id}: {e}")
        return []
    
# ============================================================
# comment prompt
# ============================================================
def build_comment_prompt(comments: list[dict], transcript_claims: list[dict], video_id: str) -> str:
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



# ============================================================
# initial extraction 
# ============================================================
def build_extraction_prompt(transcript_chunk: str, video_id: str) -> str:
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

IMPORTANT: Return ONLY valid JSON. No explanation, no markdown fences.

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


# ============================================================
# call local Ollama instance
# ============================================================
def call_llm(prompt: str, num_predict: int = 1200) -> str | None:
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


# ============================================================
# analyze a single video
# ============================================================
def analyze_video(video_id: str, transcript: str, comments: list[dict]) -> dict | None:
    chunks = chunk_text(transcript)
    log.info(f"  → {len(chunks)} chunk(s) for video {video_id}")

    all_topics = []
    all_claims = []

    # -- Transcript extraction --
    for i, chunk in enumerate(chunks):
        log.info(f"  → Extracting transcript chunk {i+1}/{len(chunks)}")
        prompt = build_extraction_prompt(chunk, video_id)
        raw = call_llm(prompt, num_predict=1500)

        if not raw:
            continue

        parsed = parse_json_response(raw)
        if not parsed:
            log.warning(f"  → Skipping unparseable chunk {i+1}")
            continue

        all_topics.extend(parsed.get("topics", []))
        # Tag every transcript claim with its source
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
                # Tag every comment claim with its source
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


# ============================================================
# run extraction across all discovered videos
# ============================================================
def process_videos(video_ids: list[str], max_comments: int = 30) -> list[dict]:
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


# ============================================================
# build narrative prompt from structured results
# ============================================================
def build_synthesis_prompt(all_results: list[dict]) -> str:
    # Serialize structured results cleanly
    structured_input = json.dumps(all_results, indent=2)

    return f"""You are an analytical assistant synthesizing intelligence across multiple YouTube videos.

Below is structured data extracted from {len(all_results)} videos.

Respond with a SINGLE JSON object — no preamble, no explanation, no markdown, no bold headers.
Start your response with {{ and end with }}. Nothing else.

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



# ============================================================
# synthesis cross-video intelligence aggregation
# ============================================================
def synthesize_trends(all_results: list[dict]) -> dict | None:
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


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    discovered_videos = discover_videos(
        search_keywords="AI news",
        channel_sub_min=100_000,
        video_view_min=20_000,
        video_keywords=["ai industry", "tech", "ai", "llm"],
        days=90
    )

    log.info(f"\nDiscovered {len(discovered_videos)} videos\n")

    all_results = process_videos(discovered_videos)

    log.info(f"\nSynthesizing across {len(all_results)} videos...\n")
    final_summary = synthesize_trends(all_results)

    if final_summary:
        print("\n=== FINAL INTELLIGENCE SUMMARY ===\n")
        print(json.dumps(final_summary, indent=2))

        # Optional: save to file
        output_path = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "video_count": len(all_results),
                "per_video": all_results,
                "synthesis": final_summary
            }, f, indent=2)
        log.info(f"Saved to {output_path}")
    else:
        log.error("Pipeline completed but synthesis failed.")
