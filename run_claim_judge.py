import json
from youtube_transcript_fetcher import get_youtube_transcript
from claim_judge import OllamaClient, analyze_chunks

if __name__ == "__main__":
    video = "https://www.youtube.com/watch?v=tJS_ycc2lNs"

    # 1) Get transcript + chunks_v2 from your existing script
    data = get_youtube_transcript(video)
    if not data.get("ok"):
        raise SystemExit(f"Transcript failed: {data}")

    video_id = data["video_id"]
    chunks_v2 = data["chunks_v2"]

    # 2) LLM
    llm = OllamaClient(model="phi3:latest", temperature=0.0, num_predict=400)

    # 3) Analyze
    out = analyze_chunks(
        llm=llm,
        video_id=video_id,
        chunks_v2=chunks_v2,
        max_claims_per_chunk=5,
    )

    print(json.dumps(out, indent=2, ensure_ascii=False))