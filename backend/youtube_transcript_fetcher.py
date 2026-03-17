from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import json
import re
from typing import List, Dict, Any

def extract_video_id(s: str) -> str:
    
    "Accepts either a video ID or a YouTube URL and returns the video ID."
    s = s.strip()
    # Already looks like an ID (most are 11 chars; allow a bit more just in case)
    if re.fullmatch(r"[A-Za-z0-9_-]{8,20}", s):
        return s

    # Try to parse v=... from URL
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{8,20})", s)
    if m:
        return m.group(1)

    # Try youtu.be/<id>
    m = re.search(r"youtu\.be/([A-Za-z0-9_-]{8,20})", s)
    if m:
        return m.group(1)

    raise ValueError(f"Could not extract video id from: {s}")


# Transcription quality check (heuristic + optional LLM hook)
FILLER_RE = re.compile(r"\b(um+|uh+|er+|ah+|like)\b", re.IGNORECASE)
BRACKET_RE = re.compile(r"\[(music|applause|laughter|inaudible|silence)\]", re.IGNORECASE)

def transcript_quality_heuristic(chunk_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Cheap, local quality checks that catch obvious issues quickly.
    Returns a score (0-100), label, and stats.
    """
    texts = [c.get("text", "").strip() for c in chunk_dicts]
    joined = " ".join(t for t in texts if t)

    total_chars = len(joined)
    total_words = len(joined.split())
    empty_lines = sum(1 for t in texts if not t)

    filler_hits = len(FILLER_RE.findall(joined))
    bracket_hits = len(BRACKET_RE.findall(joined))

    # Timestamp sanity
    bad_time = 0
    last_start = -1.0
    for c in chunk_dicts:
        s = float(c.get("start", 0))
        d = float(c.get("duration", 0))
        if d <= 0 or s < last_start:
            bad_time += 1
        last_start = s

    # Simple score
    score = 100
    if total_words < 200:
        score -= 25
    if total_chars < 1000:
        score -= 25
    if empty_lines > 0:
        score -= min(10, empty_lines)
    score -= min(20, bracket_hits * 2)
    score -= min(15, filler_hits // 20)
    score -= min(30, bad_time * 10)

    score = max(0, min(100, score))
    label = "good" if score >= 80 else "ok" if score >= 60 else "poor"

    return {
        "score": score,
        "label": label,
        "stats": {
            "total_words": total_words,
            "total_chars": total_chars,
            "filler_hits": filler_hits,
            "bracket_hits": bracket_hits,
            "bad_time_entries": bad_time,
            "empty_lines": empty_lines
        }
    }

def sample_transcript_for_quality(chunk_dicts: List[Dict[str, Any]], seconds: float = 45.0) -> str:
    """
    Builds a small sample (START/MIDDLE/END) for an LLM to judge quality.
    Keeps token/cost down and avoids sending the whole transcript.
    """
    if not chunk_dicts:
        return ""

    chunk_dicts = sorted(chunk_dicts, key=lambda x: float(x.get("start", 0)))
    total_end = max(float(c["start"]) + float(c["duration"]) for c in chunk_dicts)

    def collect(start_t: float) -> str:
        end_t = start_t + seconds
        parts = []
        for c in chunk_dicts:
            s = float(c["start"])
            if s < start_t:
                continue
            if s >= end_t:
                break
            t = c.get("text", "").strip()
            if t:
                parts.append(t)
        return " ".join(parts)

    start = collect(0.0)
    mid = collect(max(0.0, total_end / 2 - seconds / 2))
    end = collect(max(0.0, total_end - seconds))

    return f"[START]\n{start}\n\n[MIDDLE]\n{mid}\n\n[END]\n{end}"



# Objective 2: Define a chunking strategy (time-based: 60s windows + overlap)
def chunk_by_time(chunk_dicts: List[Dict[str, Any]], window_s: float = 60.0, overlap_s: float = 10.0) -> List[Dict[str, Any]]:
    """
    Groups transcript lines into time windows.
    Output chunks have: start, end, text.
    """
    if not chunk_dicts:
        return []

    chunk_dicts = sorted(chunk_dicts, key=lambda x: float(x.get("start", 0)))
    out: List[Dict[str, Any]] = []
    i, n = 0, len(chunk_dicts)

    while i < n:
        start_t = float(chunk_dicts[i]["start"])
        end_t = start_t + window_s

        texts: List[str] = []
        last_end_seen = start_t
        j = i

        while j < n:
            s = float(chunk_dicts[j]["start"])
            d = float(chunk_dicts[j]["duration"])
            if s >= end_t:
                break
            t = chunk_dicts[j].get("text", "").strip()
            if t:
                texts.append(t)
            last_end_seen = max(last_end_seen, s + d)
            j += 1

        combined = " ".join(texts).strip()
        if combined:
            out.append({"start": start_t, "end": last_end_seen, "text": combined})

        # advance with overlap
        next_start = end_t - overlap_s
        k = i
        while k < n and float(chunk_dicts[k]["start"]) < next_start:
            k += 1
        i = max(i + 1, k)  # ensure progress

    return out



# Transcript fetch 
def get_youtube_transcript(video_or_url: str, languages=("en",)):
    video_id = extract_video_id(video_or_url)
    api = YouTubeTranscriptApi()

    try:
        chunks = api.fetch(video_id, languages=list(languages))

        # In v1.2.x chunks are objects with .text/.start/.duration
        text = " ".join(c.text for c in chunks)
        chunk_dicts = [{"text": c.text, "start": c.start, "duration": c.duration} for c in chunks]

        # Objective 1: Quality checks
        heuristic = transcript_quality_heuristic(chunk_dicts)
        sample_text = sample_transcript_for_quality(chunk_dicts, seconds=45.0)
        

        # Objective 2: Chunking strategy
        strategy = {"type": "time_window", "window_s": 60.0, "overlap_s": 10.0}
        chunks_v2 = chunk_by_time(chunk_dicts, window_s=strategy["window_s"], overlap_s=strategy["overlap_s"])

        return {
            "video_id": video_id,
            "method": "youtube_transcript_api",
            "ok": True,
            "text": text,
            "chunks": chunk_dicts,

            # merged outputs
            "quality": {
                "heuristic": heuristic,
                "llm_sample": sample_text   # what will send to the LLM
            },
            "chunk_strategy": strategy,
            "chunks_v2": chunks_v2
        }

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        return {"video_id": video_id, "method": "youtube_transcript_api", "ok": False, "error": str(e)}
    
    

if __name__ == "__main__":
    videos = [
        # Put REAL IDs or URLs here:
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=tJS_ycc2lNs",
        "https://www.youtube.com/watch?v=zt0JA5rxdfM",
    ]

    results = [get_youtube_transcript(v) for v in videos]
    print(json.dumps(results, indent=2, ensure_ascii=False))
