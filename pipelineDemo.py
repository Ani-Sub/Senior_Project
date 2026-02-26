# IMPORTANT:: Required libraries and installations:
# Run: pip install youtube-transcript-api
# pip install requests
# pip install ollama
# pip install google-api-python-client


import time
import requests
import json
from datetime import datetime, timezone, timedelta
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build

YOUTUBE_API_KEY = "AIzaSyCuP70Ec9esUDyW83QOI15gJntRFdy7Wyk"

youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)
#============================================================
# timestamp to be used as criteria
#============================================================
def get_published_after(days: int) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.isoformat()

#============================================================
# search channels based on keywords
#============================================================
def search_channels(query, max_results=50):
    request = youtube.search().list(
        q=query,
        type="channel",
        part="snippet",
        maxResults=max_results
    )
    response = request.execute()

    channel_ids = [
        item["snippet"]["channelId"]
        for item in response["items"]
    ]

    return channel_ids

#============================================================
# filter channels based on criteria i.e. subcribers, views, country, etc.
#============================================================
def filter_channels(channel_ids,
                    min_subscribers=50000,
                    min_total_views=1000000):
    
    request = youtube.channels().list(
        part="statistics,snippet",
        id=",".join(channel_ids)
    )
    response = request.execute()

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

#============================================================
#pull videos from channels
#============================================================
def get_recent_channel_videos(channel_id, days=30, max_results=50):
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

#============================================================
#filtering step for videos
#============================================================
def filter_videos(video_ids,
                  min_views=10000,
                  keywords=None):
    
    if keywords is None:
        keywords = []

    request = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=",".join(video_ids)
    )

    response = request.execute()
    selected = []

    for item in response["items"]:
        views = int(item["statistics"].get("viewCount", 0))
        title = item["snippet"]["title"].lower()

        if views >= min_views and any(k.lower() in title for k in keywords):
            selected.append(item["id"])

    return selected
#============================================================
#condense all data derived from the filtering and search steps
#============================================================
def discover_videos(search_keywords,
                    channel_sub_min,
                    video_view_min,
                    video_keywords, days=30):
    
    print("Searching channels...")
    channel_ids = search_channels(search_keywords)

    print("Filtering channels...")
    channels = filter_channels(channel_ids,
                                min_subscribers=channel_sub_min)

    all_video_ids = []

    for channel in channels:
        print(f"Getting recent videos for {channel['title']} (last {days} days)")

        vids = get_recent_channel_videos(channel["channel_id"], days=days, max_results=30)

        filtered = filter_videos(
            vids,
            min_views=video_view_min,
            keywords=video_keywords
        )

        all_video_ids.extend(filtered)

    return all_video_ids

#============================================================
#getting video transcripts 
#============================================================
#video_id = "XUAxfjUHVHs"
def get_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    time.sleep(10)
    full_text = " ".join([segment.text for segment in transcript])

    return full_text

# testing comment out when running whole pipeline
# text = get_transcript(video_id)
# print(text)

#============================================================
#create prompt for extraction
#============================================================
def build_prompt(transcript):
    return f"""
You are an analytical assistant. 

From the following YouTube transcript, extract:

1. Topics – main subjects discussed.
2. Claims – explicit or implied assertions.
3. Overall Narrative – the main story or framing.
4. Trends – recurring themes, patterns, or shifts.

Return ONLY valid JSON in this format:

{{
  "topics": ["...", "..."],
  "claims": ["...", "..."],
  "narrative": "...",
  "trends": ["...", "..."]
}}

Transcript:
{transcript}
"""

#============================================================
#call llm
#============================================================
def analyze_with_llama(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 700
            }
        }
    )

    return response.json()["response"]

#============================================================
# process multiple videos
#============================================================
def process_videos(video_ids):
    all_results = []
    for vid in video_ids:
        print(f"\nProcessing video: {vid}")
        try:
            transcript = get_transcript(vid)
        except:
            print("Transcript unavailable")
            continue
        
        #test with part of transcript 
        #transcript = transcript[:4000]
        
        prompt = build_prompt(transcript)
        analysis = analyze_with_llama(prompt)
        
        all_results.append({
            "video_id": vid,
            "analysis": analysis
        })
    return all_results

#============================================================
# call llm again to extract commonalities between each video
#============================================================
def synthesize_trends(all_results):
    combined = "\n\n".join([res["analysis"] for res in all_results])
    
    prompt = f"""
You are an analytical assistant.

From the following analyses of multiple YouTube videos:

{combined}

Extract:

1. Common Topics
2. Repeated Claims
3. Shared Narrative
4. Overall Trends

Return ONLY valid JSON.
"""
    summary = analyze_with_llama(prompt)
    return summary

#============================================================
# test pipeline
#============================================================
if __name__ == "__main__":

    discovered_videos = discover_videos(
        search_keywords="AI news",
        channel_sub_min=100000,
        video_view_min=20000,
        video_keywords=["ai industry", "tech", "ai"],
        days=90 
    )

    print(f"\nDiscovered {len(discovered_videos)} videos\n")

    all_results = process_videos(discovered_videos)

    final_summary = synthesize_trends(all_results)

    print(final_summary)