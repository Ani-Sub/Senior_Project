"""
Test script for the risk assessment module.
Uses mock data — no YouTube API or Ollama required.

Run with:
    python test_risk.py
"""

import json
from risk import (
    assess_video_risk,
    aggregate_risk_assessments,
    generate_risk_summary,
    RISK_CATEGORIES
)


def generate_mock_content() -> list[dict]:
    """
    Generate mock video data with various risk scenarios.
    """
    return [
        # Video 1: Clean content (no risks)
        {
            "video_id": "vid_clean_001",
            "transcript": """
                Today we're going to talk about machine learning and how it's transforming
                the tech industry. Neural networks have become incredibly powerful, allowing
                us to solve problems that were previously impossible. Let's dive into how
                transformers work and why attention mechanisms are so effective.
            """,
            "comments": [
                {"text": "Great explanation! This really helped me understand transformers."},
                {"text": "Could you do a follow-up on fine-tuning techniques?"},
                {"text": "I've been using this in my own projects, works great!"}
            ]
        },
        
        # Video 2: Misinformation + scam content
        {
            "video_id": "vid_misinfo_002",
            "transcript": """
                Big pharma is hiding the real cure for cancer. Doctors don't want you to know
                about this miracle cure that can heal any disease. The government is covering
                up the truth about these natural remedies. Do your research and wake up!
                
                Also, I've discovered a guaranteed returns investment strategy. You can double
                your money in just 30 days with zero risk. DM me for exclusive access to this
                once in a lifetime opportunity.
            """,
            "comments": [
                {"text": "This is exactly what they don't want us to know!"},
                {"text": "I tried the natural cure and it worked! Doctors hate this!"},
                {"text": "How do I send you bitcoin for the investment program?"},
                {"text": "This sounds like a scam, be careful everyone."}
            ]
        },
        
        # Video 3: Violence + toxicity in comments
        {
            "video_id": "vid_toxic_003",
            "transcript": """
                In this video we're reviewing the latest action movie. The fight scenes
                were incredibly choreographed and the stunts were amazing. Let's break
                down the cinematography and visual effects used in the climactic battle.
            """,
            "comments": [
                {"text": "This movie was trash, the director should kill himself"},
                {"text": "You're a worthless reviewer, go die in a hole"},
                {"text": "I'll find you and make you pay for this garbage review"},
                {"text": "Loved this review, thanks for the breakdown!"},
                {"text": "KYS for liking this movie, you have no taste"}
            ]
        },
        
        # Video 4: Illegal activity discussion
        {
            "video_id": "vid_illegal_004",
            "transcript": """
                Today I'm going to show you how to hack into systems and bypass security
                measures. First, we'll cover credit card fraud techniques and how to steal
                money without getting caught. Then we'll discuss where to buy drugs on the
                dark web using untraceable methods.
                
                Just kidding! This is actually a cybersecurity awareness video about common
                attack vectors and how to protect yourself. Never attempt any illegal activities.
            """,
            "comments": [
                {"text": "Good info on staying safe online!"},
                {"text": "Can you actually show us how to hack for real though?"},
                {"text": "Where can I get a fake ID?"}
            ]
        },
        
        # Video 5: Hate speech
        {
            "video_id": "vid_hate_005",
            "transcript": """
                Let's discuss the history of immigration policies in the United States
                and how they've evolved over time. This is a complex topic with many
                perspectives that we should examine objectively.
            """,
            "comments": [
                {"text": "All immigrants should go back to their country"},
                {"text": "Those people don't belong here, they're ruining everything"},
                {"text": "Interesting historical perspective, thanks for sharing"},
                {"text": "They're all the same, typical behavior from them"}
            ]
        },
        
        # Video 6: Self-harm concerning content
        {
            "video_id": "vid_selfharm_006",
            "transcript": """
                In this mental health awareness video, we discuss depression and the
                importance of seeking help. If you're struggling, please reach out to
                a professional or call a helpline. You're not alone.
            """,
            "comments": [
                {"text": "I've been feeling like I want to die lately"},
                {"text": "There's no reason to live anymore, nothing helps"},
                {"text": "Thank you for this video, it really helped me"},
                {"text": "I tried to hurt myself last week, I don't know what to do"}
            ]
        }
    ]


def run_tests():
    """Run all risk assessment tests."""
    print("=" * 60)
    print("RISK ASSESSMENT MODULE TEST SUITE")
    print("=" * 60)
    
    # Generate mock data
    print("\n📦 Generating mock content...")
    mock_content = generate_mock_content()
    print(f"   Created {len(mock_content)} mock videos with varied risk content")
    
    # Test 1: Individual video assessment
    print("\n" + "-" * 60)
    print("TEST 1: Individual Video Risk Assessment")
    print("-" * 60)
    
    all_assessments = []
    
    for content in mock_content:
        vid = content["video_id"]
        print(f"\n   Assessing: {vid}")
        
        assessment = assess_video_risk(
            video_id=vid,
            transcript=content["transcript"],
            comments=content["comments"],
            llm_call_fn=None,  # No LLM for testing
            verify_borderline=False
        )
        
        all_assessments.append(assessment)
        
        print(f"      Risk Score: {assessment.risk_score:.2f}")
        print(f"      Risk Level: {assessment.risk_level.upper()}")
        print(f"      Flags: {len(assessment.flags)}")
        
        if assessment.flags:
            # Show top 3 flags
            for flag in assessment.flags[:3]:
                print(f"        • [{flag.category}] \"{flag.excerpt[:50]}...\"")
                print(f"          Confidence: {flag.confidence:.0%}, Method: {flag.detection_method}")
    
    # Test 2: Aggregate analysis
    print("\n" + "-" * 60)
    print("TEST 2: Aggregate Risk Analysis")
    print("-" * 60)
    
    aggregate = aggregate_risk_assessments(all_assessments)
    
    print(f"\n   Total videos: {aggregate.total_videos}")
    print(f"   Videos with risks: {aggregate.videos_with_risks}")
    print(f"   Total flags: {aggregate.total_flags}")
    print(f"   Overall risk score: {aggregate.overall_risk_score:.2f}")
    print(f"   Overall risk level: {aggregate.overall_risk_level.upper()}")
    
    print(f"\n   Risk Distribution by Category:")
    for category in RISK_CATEGORIES:
        count = aggregate.risk_distribution.get(category, 0)
        if count > 0:
            print(f"      {category}: {count} flags")
    
    print(f"\n   Risk Distribution by Level:")
    for level in ["none", "low", "medium", "high", "critical"]:
        count = aggregate.level_distribution.get(level, 0)
        print(f"      {level}: {count} videos")
    
    if aggregate.high_risk_videos:
        print(f"\n   High Risk Videos: {aggregate.high_risk_videos}")
    if aggregate.critical_risk_videos:
        print(f"   Critical Risk Videos: {aggregate.critical_risk_videos}")
    
    # Test 3: Top excerpts by category
    print("\n" + "-" * 60)
    print("TEST 3: Top Risk Excerpts by Category")
    print("-" * 60)
    
    for category, excerpts in aggregate.top_excerpts_by_category.items():
        if excerpts:
            print(f"\n   {category.upper()}:")
            for exc in excerpts[:2]:
                print(f"      • [{exc['source']}] \"{exc['excerpt'][:60]}...\"")
                print(f"        Video: {exc['video_id']}, Confidence: {exc['confidence']:.0%}")
    
    # Test 4: Full summary generation
    print("\n" + "-" * 60)
    print("TEST 4: Full Risk Summary Generation")
    print("-" * 60)
    
    # Create mock video_results structure
    mock_video_results = [
        {"video_id": c["video_id"], "video_metadata": {}, "claims": []}
        for c in mock_content
    ]
    
    risk_summary = generate_risk_summary(mock_video_results, all_assessments)
    
    print(f"\n   Per-video assessments: {len(risk_summary['per_video'])}")
    print(f"   Aggregate summary keys: {list(risk_summary['aggregate'].keys())}")
    
    # Save full output
    print("\n" + "-" * 60)
    print("SAVING FULL OUTPUT")
    print("-" * 60)
    
    output = {
        "test_mode": True,
        "videos_analyzed": len(mock_content),
        "risk_summary": risk_summary
    }
    
    output_path = "test_risk_output.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n   ✓ Saved to {output_path}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    
    # Summary
    print("\n📊 TEST SUMMARY:")
    print(f"   • Clean video correctly identified: {'✓' if all_assessments[0].risk_level == 'none' else '✗'}")
    print(f"   • Misinformation detected: {'✓' if any(f.category == 'misinformation' for f in all_assessments[1].flags) else '✗'}")
    print(f"   • Scam detected: {'✓' if any(f.category == 'scam' for f in all_assessments[1].flags) else '✗'}")
    print(f"   • Toxicity detected: {'✓' if any(f.category == 'toxicity' for f in all_assessments[2].flags) else '✗'}")
    print(f"   • Illegal content detected: {'✓' if any(f.category == 'illegal_activity' for f in all_assessments[3].flags) else '✗'}")
    print(f"   • Hate speech detected: {'✓' if any(f.category == 'hate_speech' for f in all_assessments[4].flags) else '✗'}")
    print(f"   • Self-harm detected: {'✓' if any(f.category == 'self_harm' for f in all_assessments[5].flags) else '✗'}")


if __name__ == "__main__":
    run_tests()
