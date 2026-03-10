import googleapiclient.discovery
from datetime import datetime, timezone, timedelta
import json
from youtube_transcript_api import YouTubeTranscriptApi

# days = 183 which is half a year (365 days) rounded up
Time_Window = (datetime.now(timezone.utc) - timedelta(days=183)).strftime("%Y-%m-%dT%H:%M:%SZ")

# insert api key when using 
API_KEY = ""


YouTubeTranscriptApiInstance = YouTubeTranscriptApi()

Youtube_Channel_IDS = [
    "UCKWaEZ-_VweaEx1j62do_vQ",
    "@freecodecamp"

]

Key_Words = [
    "Artificial",
    "Intelligence"
]

def main():
    
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

# find the channel IDs
    channel_ids = []

    for id in Youtube_Channel_IDS:
        request = youtube.search().list(
                part="snippet",
                maxResults=1,
                type="channel",
                q=id
            )
        response = request.execute()
        
        for item in response["items"]:
            channel_ids.append(item["snippet"]["channelId"])




# search for videos
    Key_Words_Query = " ".join(Key_Words)
    videos = []
    for channel in channel_ids:
        request = youtube.search().list(
            part="snippet",
            maxResults=5,
            channelId=channel,
            type="video",
            publishedAfter=Time_Window,
            q=Key_Words_Query
        )
        response = request.execute()
        
        for video in response["items"]:
            videos.append(video["id"]["videoId"])

# filter videos above 5k views
    filteredVideos = []
    request1 = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(videos)
        )
    response1 = request1.execute()

    for i in response1["items"]:
        numViews = int(i["statistics"]["viewCount"])
        transcriptChunks = YouTubeTranscriptApiInstance.fetch(i["id"])
        fullTranscript = " ".join([chunk.text for chunk in transcriptChunks])

        if numViews > 5000:
            filteredVideos.append(
            {
                "id": i["id"],
                "Video Title": i["snippet"]["title"],
                "Published Date": i["snippet"]["publishedAt"],
                "Channel Title": i["snippet"]["channelTitle"],
                "View Count": i["statistics"]["viewCount"],
                "Processed Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Transcript": fullTranscript
            })

    
    with open("filtered_videos_tester.json", "w", encoding="utf-8") as f:
        json.dump(filteredVideos, f, ensure_ascii=False, indent=2)

    

if __name__ == "__main__":
    main()

    with open("filtered_videos_tester.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print(data)