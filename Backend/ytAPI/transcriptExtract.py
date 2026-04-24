import time
import logging
from youtube_transcript_api import YouTubeTranscriptApi

log = logging.getLogger(__name__)


def get_transcript(video_id: str, language: str = "en") -> str | None:
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        transcript = None
        try:
            transcript = transcript_list.find_transcript([language])
            log.info(f"  → Found {language} transcript")
        except Exception:
            available = [t.language_code for t in transcript_list]
            log.warning(f"  → No {language} transcript for {video_id}. Available: {available}")

            for t in transcript_list:
                if t.is_translatable:
                    transcript = t.translate(language)
                    log.info(f"  → Using auto-translated {language} transcript")
                    break

        if transcript is None:
            log.warning(f"  → Skipping {video_id}: no {language} transcript available")
            return None

        fetched = transcript.fetch()
        time.sleep(1)
        return " ".join([segment.text for segment in fetched])

    except Exception as e:
        log.warning(f"  → Transcript unavailable for {video_id}: {e}")
        return None
