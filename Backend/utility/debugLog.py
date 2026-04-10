import json
import logging
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

_debug_file = None
_debug_path = None


def init_debug_log(output_dir: str = ".") -> str:
    """
    Call once at pipeline start. Creates a timestamped debug log file.
    Returns the file path so you know where to look.
    """
    global _debug_file, _debug_path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _debug_path = Path(output_dir) / f"debug_{timestamp}.log"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    _debug_file = open(_debug_path, "w", encoding="utf-8")
    _write_section("DEBUG SESSION STARTED", {"timestamp": datetime.now().isoformat()})
    log.info(f"Debug log writing to: {_debug_path}")
    return str(_debug_path)


def close_debug_log():
    """Call at pipeline end to flush and close the file."""
    global _debug_file
    if _debug_file:
        _write_section("DEBUG SESSION ENDED", {"timestamp": datetime.now().isoformat()})
        _debug_file.flush()
        _debug_file.close()
        _debug_file = None


def _write_section(title: str, data=None):
    """Write a clearly delimited section to the debug file."""
    if not _debug_file:
        return
    separator = "=" * 80
    _debug_file.write(f"\n{separator}\n")
    _debug_file.write(f"  {title}\n")
    _debug_file.write(f"  {datetime.now().isoformat()}\n")
    _debug_file.write(f"{separator}\n")
    if data is not None:
        if isinstance(data, (dict, list)):
            _debug_file.write(json.dumps(data, indent=2, default=str))
        else:
            _debug_file.write(str(data))
    _debug_file.write("\n")
    _debug_file.flush()


# ── Channel debug helpers ────────────────────────────────────────────────────

def log_channels_found(channel_ids: list[str], query: str):
    _write_section(f"CHANNELS FOUND — query: '{query}'", {
        "count": len(channel_ids),
        "channel_ids": channel_ids
    })


def log_channels_filtered(channels: list[dict], min_subscribers: int, min_total_views: int):
    _write_section(
        f"CHANNELS AFTER FILTER — min_subs={min_subscribers:,}  min_views={min_total_views:,}",
        {
            "count": len(channels),
            "channels": channels
        }
    )


# ── Video debug helpers ──────────────────────────────────────────────────────

def log_videos_raw(channel_title: str, channel_id: str, video_ids: list[str]):
    _write_section(f"RAW VIDEOS — channel: '{channel_title}' ({channel_id})", {
        "count": len(video_ids),
        "video_ids": video_ids
    })


def log_videos_filtered(channel_title: str, selected: list[str], rejected: list[dict]):
    _write_section(f"VIDEOS AFTER FILTER — channel: '{channel_title}'", {
        "accepted_count": len(selected),
        "accepted": selected,
        "rejected_count": len(rejected),
        "rejected": rejected   # includes title, views, reason
    })


# ── Comment debug helpers ────────────────────────────────────────────────────

def log_comments(video_id: str, comments: list[dict]):
    _write_section(f"COMMENTS — video: {video_id}", {
        "count": len(comments),
        "comments": comments
    })


# ── LLM prompt/response debug helpers ───────────────────────────────────────

def log_llm_prompt(stage: str, video_id: str, chunk_index: int | None, prompt: str):
    label = f"LLM PROMPT — stage: {stage}  video: {video_id}"
    if chunk_index is not None:
        label += f"  chunk: {chunk_index}"
    _write_section(label, prompt)


def log_llm_response(stage: str, video_id: str, chunk_index: int | None, raw: str, parsed: dict | None):
    label = f"LLM RESPONSE — stage: {stage}  video: {video_id}"
    if chunk_index is not None:
        label += f"  chunk: {chunk_index}"
    _write_section(label, {
        "raw_response": raw,
        "parsed_successfully": parsed is not None,
        "parsed": parsed
    })


def log_llm_synthesis_prompt(prompt: str):
    _write_section("LLM PROMPT — stage: synthesis", prompt)


def log_llm_synthesis_response(raw: str, parsed: dict | None):
    _write_section("LLM RESPONSE — stage: synthesis", {
        "raw_response": raw,
        "parsed_successfully": parsed is not None,
        "parsed": parsed
    })