import time
import itertools
import logging
import os
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

log = logging.getLogger(__name__)


def _load_proxies() -> list[GenericProxyConfig]:
    api_key = os.getenv("WEBSHARE_API_KEY")
    if not api_key:
        log.warning("WEBSHARE_API_KEY not set — running without proxy")
        return []
    try:
        resp = requests.get(
            "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=25",
            headers={"Authorization": f"Token {api_key}"},
            timeout=10
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        configs = []
        for p in results:
            url = f"http://{p['username']}:{p['password']}@{p['proxy_address']}:{p['port']}"
            configs.append(GenericProxyConfig(http_url=url, https_url=url))
        log.info(f"Loaded {len(configs)} proxies from Webshare")
        return configs
    except Exception as e:
        log.warning(f"Failed to load proxies from Webshare: {e} — running without proxy")
        return []


# Fetch once at startup, rotate round-robin across all transcript calls
_proxy_pool = _load_proxies()
_proxy_cycle = itertools.cycle(_proxy_pool) if _proxy_pool else None


def get_transcript(video_id: str, language: str = "en") -> str | None:
    try:
        if _proxy_cycle:
            ytt_api = YouTubeTranscriptApi(proxy_config=next(_proxy_cycle))
        else:
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
        time.sleep(2)
        return " ".join([segment.text for segment in fetched])

    except Exception as e:
        log.warning(f"  → Transcript unavailable for {video_id}: {e}")
        return None
