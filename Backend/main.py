import json
import logging
from datetime import datetime
from typing import Literal
 
from ytAPI.videoExtract import discover_videos
from extraction.analyzer import process_videos, synthesize_trends, call_llm
from utility.debugLog import init_debug_log, close_debug_log
from trends import generate_trend_summary, Granularity
from risk import assess_video_risk, generate_risk_summary
 
log = logging.getLogger(__name__)
 
 
def run_pipeline(
    search_keywords: str,
    channel_sub_min: int,
    video_view_min: int,
    video_keywords: list[str],
    days: int = 90,
    max_comments: int = 30,
    trend_granularity: Granularity = "weekly",
    assess_risk: bool = True,
    llm_verify_risk: bool = True
) -> dict | None:
    """
    Run the full YouTube intelligence pipeline:
    1. Discover relevant videos
    2. Extract claims from transcripts + comments
    3. Synthesize cross-video narrative
    4. Analyze temporal trends
    5. Assess content risk
    6. Save results to a timestamped JSON file
    
    Args:
        search_keywords: Keywords to search for channels
        channel_sub_min: Minimum subscriber count for channels
        video_view_min: Minimum view count for videos
        video_keywords: Keywords that must appear in video titles
        days: How far back to look for videos
        max_comments: Maximum comments to extract per video
        trend_granularity: Time granularity for trend analysis ("daily" or "weekly")
        assess_risk: Whether to run risk assessment on content
        llm_verify_risk: Whether to use LLM for borderline risk cases
    """
 
    # ── Debug log init ──────────────────────────────────────
    debug_path = init_debug_log(output_dir="logs")
    log.info(f"Debug log: {debug_path}")
 
    try:
        # ── Step 1: Discovery ───────────────────────────────────
        discovered_videos = discover_videos(
            search_keywords=search_keywords,
            channel_sub_min=channel_sub_min,
            video_view_min=video_view_min,
            video_keywords=video_keywords,
            days=days
        )
        log.info(f"\nDiscovered {len(discovered_videos)} videos\n")
 
        if not discovered_videos:
            log.warning("No videos found. Try broadening your search criteria.")
            return None
 
        # ── Step 2: Extraction ──────────────────────────────────
        all_results = process_videos(discovered_videos, max_comments=max_comments)
 
        if not all_results:
            log.warning("No results extracted from any video.")
            return None
 
        # ── Step 3: Synthesis ───────────────────────────────────
        log.info(f"\nSynthesizing across {len(all_results)} videos...\n")
        final_summary = synthesize_trends(all_results)
 
        if not final_summary:
            log.error("Pipeline completed but synthesis failed.")
            return None
 
        # ── Step 4: Trend Analysis ──────────────────────────────
        log.info(f"\nAnalyzing trends ({trend_granularity} granularity)...\n")
        trend_analysis = generate_trend_summary(
            video_results=all_results,
            synthesis=final_summary,
            granularity=trend_granularity
        )
        log.info(f"  ✓ Trend analysis complete: {trend_analysis['overall']['trend']['pattern']} pattern detected")
 
        # ── Step 5: Risk Assessment ─────────────────────────────
        risk_analysis = None
        if assess_risk:
            log.info(f"\nAssessing content risk...\n")
            risk_assessments = []
            
            # LLM function for borderline verification
            llm_fn = call_llm if llm_verify_risk else None
            
            for result in all_results:
                vid = result.get("video_id")
                transcript = result.get("_transcript", "")
                comments = result.get("_comments", [])
                
                log.info(f"  Assessing risk for: {vid}")
                assessment = assess_video_risk(
                    video_id=vid,
                    transcript=transcript,
                    comments=comments,
                    llm_call_fn=llm_fn,
                    verify_borderline=llm_verify_risk
                )
                risk_assessments.append(assessment)
                
                if assessment.flags:
                    log.info(f"    ⚠ {len(assessment.flags)} risk flags ({assessment.risk_level})")
            
            risk_analysis = generate_risk_summary(all_results, risk_assessments)
            
            flagged_count = risk_analysis["aggregate"]["videos_with_risks"]
            total_flags = risk_analysis["aggregate"]["total_flags"]
            log.info(f"  ✓ Risk assessment complete: {flagged_count} videos with {total_flags} total flags")
        
        # ── Step 6: Clean up and Output ─────────────────────────
        # Remove internal fields before saving
        for result in all_results:
            result.pop("_transcript", None)
            result.pop("_comments", None)
        
        output = {
            "generated_at": datetime.now().isoformat(),
            "search_params": {
                "keywords": search_keywords,
                "channel_sub_min": channel_sub_min,
                "video_view_min": video_view_min,
                "video_keywords": video_keywords,
                "days": days,
                "trend_granularity": trend_granularity,
                "risk_assessment_enabled": assess_risk
            },
            "video_count": len(all_results),
            "per_video": all_results,
            "synthesis": final_summary,
            "trends": trend_analysis
        }
        
        if risk_analysis:
            output["risk"] = risk_analysis
 
        output_path = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
 
        log.info(f"Saved to {output_path}")
        print("\n=== FINAL INTELLIGENCE SUMMARY ===\n")
        print(json.dumps(final_summary, indent=2))
        print("\n=== TREND ANALYSIS ===\n")
        print(f"Pattern: {trend_analysis['overall']['trend']['pattern']}")
        print(f"Description: {trend_analysis['overall']['trend']['description']}")
        
        if risk_analysis:
            print("\n=== RISK ASSESSMENT ===\n")
            print(f"Videos with risks: {risk_analysis['aggregate']['videos_with_risks']}/{len(all_results)}")
            print(f"Total flags: {risk_analysis['aggregate']['total_flags']}")
            print(f"Overall risk level: {risk_analysis['aggregate']['overall_risk_level']}")
 
        return output
 
    finally:
        # Always close the debug log even if pipeline errors out
        close_debug_log()
 
 
if __name__ == "__main__":
    run_pipeline(
        search_keywords="AI",
        channel_sub_min=100_000,
        video_view_min=50_000,
        video_keywords=["tech", "ai", "llm", "artificial intelligence"],
        days=60,
        max_comments=30,
        trend_granularity="weekly",
        assess_risk=True,
        llm_verify_risk=True
    )




