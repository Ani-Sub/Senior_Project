"""
Test the full pipeline with mock data.
Skips YouTube API entirely - uses fake videos/transcripts.
"""

import json
from datetime import datetime, timedelta
from extraction.analyzer import analyze_video, synthesize_trends
from extraction.confidence import boost_confidence_by_agreement
from trends.aggregator import generate_trend_summary
from risk.aggregator import generate_risk_summary
from risk.detector import assess_video_risk
from utility.output import OutputManager

# Mock video data (3 videos about AI)
MOCK_VIDEOS = [
    {
        "video_id": "mock_video_001",
        "title": "AI Will Replace 50% of Jobs by 2030",
        "channel_id": "mock_channel_001",
        "channel_title": "Tech Insights",
        "published_at": (datetime.now() - timedelta(days=5)).isoformat(),
        "view_count": 150000,
        "like_count": 8000,
        "comment_count": 500,
    },
    {
        "video_id": "mock_video_002", 
        "title": "Why AI Job Fears Are Overblown",
        "channel_id": "mock_channel_002",
        "channel_title": "Future Tech",
        "published_at": (datetime.now() - timedelta(days=10)).isoformat(),
        "view_count": 200000,
        "like_count": 12000,
        "comment_count": 800,
    },
    {
        "video_id": "mock_video_003",
        "title": "OpenAI GPT-5 Changes Everything",
        "channel_id": "mock_channel_001",
        "channel_title": "Tech Insights",
        "published_at": (datetime.now() - timedelta(days=2)).isoformat(),
        "view_count": 500000,
        "like_count": 25000,
        "comment_count": 2000,
    },
]

MOCK_TRANSCRIPTS = {
    "mock_video_001": """
    Welcome back to Tech Insights. Today we're discussing a serious topic.
    According to Goldman Sachs, AI could automate 300 million jobs worldwide.
    McKinsey predicts that by 2030, up to 30% of hours worked could be automated.
    The World Economic Forum says 85 million jobs will be displaced by 2025.
    However, they also predict 97 million new jobs will be created.
    White collar workers are most at risk - lawyers, accountants, programmers.
    OpenAI's GPT-4 can already pass the bar exam and write complex code.
    Companies are already laying off workers and replacing them with AI.
    The question isn't if AI will take jobs, but how fast it will happen.
    Governments need to prepare universal basic income programs now.
    """,
    
    "mock_video_002": """
    Hey everyone, let's talk about why AI fears are completely overblown.
    Every technological revolution has created more jobs than it destroyed.
    The printing press, electricity, computers - all created massive employment.
    AI is a tool that augments human capabilities, not replaces them.
    Yes, some jobs will change, but new roles will emerge.
    Prompt engineers, AI trainers, ethics consultants - these didn't exist 5 years ago.
    The real concern should be wealth distribution, not job destruction.
    Companies using AI are actually hiring more, not less.
    Microsoft added 40,000 employees since launching Copilot.
    The narrative of mass unemployment is driven by fear, not data.
    We should focus on education and reskilling, not panic.
    """,
    
    "mock_video_003": """
    OpenAI just dropped GPT-5 and it's absolutely insane.
    This model scores 95% on complex reasoning benchmarks.
    It can write production-ready code in minutes that would take developers hours.
    Google is reportedly in panic mode trying to catch up.
    Anthropic's Claude is the only real competitor right now.
    The model can now browse the web and execute code autonomously.
    Sam Altman says AGI could arrive within 2 years.
    Microsoft is integrating GPT-5 into every product.
    Developers are worried - this thing can debug code better than most engineers.
    But it still makes mistakes, it's not replacing anyone yet.
    The real winners will be people who learn to use these tools effectively.
    """
}

MOCK_COMMENTS = {
    "mock_video_001": [
        {"text": "I already lost my job to AI at a call center", "likes": 500},
        {"text": "This is fear mongering, AI can't do creative work", "likes": 300},
        {"text": "UBI is the only solution, it's coming whether we like it or not", "likes": 450},
    ],
    "mock_video_002": [
        {"text": "Finally someone speaking sense about AI", "likes": 800},
        {"text": "Tell that to the writers and artists losing work to AI", "likes": 600},
        {"text": "AI helped me get a promotion, not lose my job", "likes": 350},
    ],
    "mock_video_003": [
        {"text": "GPT-5 wrote my entire backend in 10 minutes", "likes": 1200},
        {"text": "Still can't replace human creativity", "likes": 400},
        {"text": "Sam Altman has been saying AGI is 2 years away for 5 years", "likes": 900},
    ],
}


def run_mock_pipeline():
    print("=" * 60)
    print("RUNNING FULL PIPELINE WITH MOCK DATA")
    print("=" * 60)
    
    # Initialize output manager
    output = OutputManager()
    print(f"\nOutput folder: {output.run_dir}")
    
    # Step 1: Analyze each video
    print("\n[Step 1/4] Analyzing videos...")
    all_results = []
    
    for video in MOCK_VIDEOS:
        video_id = video["video_id"]
        print(f"  → Analyzing: {video['title'][:40]}...")
        
        transcript = MOCK_TRANSCRIPTS.get(video_id, "")
        comments = MOCK_COMMENTS.get(video_id, [])
        
        result = analyze_video(
            video_id=video_id,
            transcript=transcript,
            comments=comments
        )
        
        if result:
            # Add video metadata to result for later use
            result["video_metadata"] = video
            all_results.append(result)
            output.save_video_checkpoint(result)
            claim_count = len(result.get("claims", []))
            print(f"    ✓ Extracted {claim_count} claims")
        else:
            print(f"    ✗ Analysis failed")
    
    print(f"\n  Total videos analyzed: {len(all_results)}")
    
    # Step 1.5: Boost confidence by cross-video agreement
    print("\n[Step 1.5] Adjusting claim confidence...")
    all_results = boost_confidence_by_agreement(all_results)
    
    # Step 2: Synthesize narratives
    print("\n[Step 2/4] Synthesizing narratives...")
    synthesis = synthesize_trends(all_results)
    
    if synthesis:
        output.save_synthesis_checkpoint(synthesis)
        narrative_count = len(synthesis.get("narratives", []))
        print(f"  ✓ Found {narrative_count} narratives")
    else:
        print("  ✗ Synthesis failed")
        synthesis = {"narratives": [], "high_confidence_claims": []}
    
    # Step 3: Trend analysis
    print("\n[Step 3/4] Analyzing trends...")
    trends_result = generate_trend_summary(
        video_results=all_results,
        synthesis=synthesis,
        granularity="daily"
    )
    output.save_trends_checkpoint(trends_result)
    print(f"  ✓ Generated trend timeline")
    
    # Step 4: Risk assessment
    print("\n[Step 4/4] Assessing risk...")
    
    # First assess each video
    risk_assessments = []
    for result in all_results:
        video_id = result.get("video_id", "unknown")
        transcript = MOCK_TRANSCRIPTS.get(video_id, "")
        comments = MOCK_COMMENTS.get(video_id, [])
        
        assessment = assess_video_risk(
            video_id=video_id,
            transcript=transcript,
            comments=comments,
            llm_call_fn=None,  # Skip LLM verification for speed
            verify_borderline=False
        )
        risk_assessments.append(assessment)
    
    # Then generate summary
    risk_result = generate_risk_summary(
        video_results=all_results,
        per_video_assessments=risk_assessments
    )
    output.save_risk_checkpoint(risk_result)
    flag_count = len(risk_result.get("per_video", []))
    print(f"  ✓ Assessed {flag_count} videos for risk")
    
    # Write db-ready output
    print("\n[Finalizing] Writing db-ready files...")
    output.export_db_ready(
        video_results=all_results,
        synthesis=synthesis,
        trends=trends_result,
        risk=risk_result
    )
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"\nOutput written to: {output.run_dir}")
    print(f"DB-ready files in: {output.run_dir}/db_ready/")
    
    # Print summary
    print("\n--- Summary ---")
    print(f"Videos analyzed: {len(all_results)}")
    total_claims = sum(len(r.get("claims", [])) for r in all_results)
    print(f"Total claims extracted: {total_claims}")
    print(f"Narratives found: {len(synthesis.get('narratives', []))}")
    total_flags = risk_result.get("aggregate", {}).get("total_flags", 0)
    print(f"Risk flags: {total_flags}")


if __name__ == "__main__":
    run_mock_pipeline()
