# IMPORTANT:: Required libraries and installations:
# Run: pip install youtube-transcript-api
# pip install requests
# pip install ollama


import requests
from youtube_transcript_api import YouTubeTranscriptApi
#getting video transcripts (Eventually add functionality for multiple videos)
video_id = "XUAxfjUHVHs"
def get_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    full_text = " ".join([segment.text for segment in transcript])

    return full_text

# testing comment out when running whole pipeline
# text = get_transcript(video_id)
# print(text)

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
#call llm
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

# process multiple videos
def process_videos(video_ids):
    all_results = []
    for vid in video_ids:
        print(f"\nProcessing video: {vid}")
        transcript = get_transcript(vid)
        
        #test with part of transcript 
        #transcript = transcript[:4000]
        
        prompt = build_prompt(transcript)
        analysis = analyze_with_llama(prompt)
        
        all_results.append({
            "video_id": vid,
            "analysis": analysis
        })
    return all_results
# call llm again to extract commonalities between each video
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
# test pipeline
if __name__ == "__main__":

    video_ids = ["Cf90NTJu2zQ", "9ul66L-ZRkI", "5YBN340qwb8"]
    
    print("Starting multi-video extraction...\n")
    
    # extract and analyze each video
    all_results = process_videos(video_ids)
    
    # print per-video analysis
    for res in all_results:
        print(f"\n--- Video: {res['video_id']} ---\n")
        print(res["analysis"])
    
    # show cross-video trends
    print("\nGenerating cross-video summary...\n")
    final_summary = synthesize_trends(all_results)
    
    print("\n=== CROSS-VIDEO SUMMARY ===\n")
    print(final_summary)