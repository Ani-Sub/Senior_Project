import time
import logging
from youtube_transcript_api import YouTubeTranscriptApi

log = logging.getLogger(__name__)


def get_transcript(video_id: str) -> str | None:
    """
    Fetch the full transcript for a video as a single string.
    Returns None if no transcript is available.
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        time.sleep(2)  # be polite to the API
        return " ".join([segment.text for segment in transcript])
    except Exception as e:
        log.warning(f"Transcript unavailable for {video_id}: {e}")
        return None