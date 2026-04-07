import time
import logging
from youtube_transcript_api import YouTubeTranscriptApi

log = logging.getLogger(__name__)


def get_transcript(video_id: str, language: str = "en") -> str | None:
    """
    Fetch the transcript for a video, preferring the specified language.
    
    Args:
        video_id: YouTube video ID
        language: Preferred language code (default: "en" for English)
    
    Returns:
        Transcript text as a single string, or None if no suitable transcript found.
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        
        # List available transcripts to find the right language
        transcript_list = ytt_api.list(video_id)
        
        # Try to get manual transcript in preferred language first
        transcript = None
        try:
            transcript = transcript_list.find_transcript([language])
            log.info(f"  → Found {language} transcript (manual or generated)")
        except Exception:
            # No transcript in preferred language
            # Check what languages ARE available
            available = []
            for t in transcript_list:
                available.append(f"{t.language_code}")
            
            log.warning(f"  → No {language} transcript for {video_id}. Available: {available}")
            
            # Try to get auto-translated English if available
            try:
                for t in transcript_list:
                    if t.is_translatable:
                        transcript = t.translate(language)
                        log.info(f"  → Using auto-translated {language} transcript")
                        break
            except Exception:
                pass
        
        if transcript is None:
            log.warning(f"  → Skipping {video_id}: no {language} transcript available")
            return None
        
        # Fetch the actual transcript content
        fetched = transcript.fetch()
        time.sleep(2)  # be polite to the API
        
        return " ".join([segment.text for segment in fetched])
        
    except Exception as e:
        log.warning(f"  → Transcript unavailable for {video_id}: {e}")
        return None