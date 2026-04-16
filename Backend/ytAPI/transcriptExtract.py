import time
import logging
import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

log = logging.getLogger(__name__)

proxy_user = os.getenv("PROXY_USERNAME")
proxy_pass = os.getenv("PROXY_PASSWORD")

proxy_config = GenericProxyConfig(
    http_url=f"http://{proxy_user}:{proxy_pass}@p.webshare.io:80",
    https_url=f"http://{proxy_user}:{proxy_pass}@p.webshare.io:80",
)

def get_transcript(video_id: str, language: str = "en") -> str | None:
    try:
        log.info(f"  → Proxy username loaded: {bool(proxy_user)}")
        log.info(f"  → Proxy password loaded: {bool(proxy_pass)}")

        ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
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
        time.sleep(2)
        return " ".join([segment.text for segment in fetched])

    except Exception as e:
        log.warning(f"  → Transcript unavailable for {video_id}: {e}")
        return None