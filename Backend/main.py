import json
import logging
from datetime import datetime
 
from ytAPI.videoExtract import discover_videos
from extraction.analyzer import process_videos, synthesize_trends
from utility.debugLog import init_debug_log, close_debug_log
 
log = logging.getLogger(__name__)
 
 
def run_pipeline(
    search_keywords: str,
    channel_sub_min: int,
    video_view_min: int,
    video_keywords: list[str],
    days: int = 90,
    max_comments: int = 30
) -> dict | None:
    """
    Run the full YouTube intelligence pipeline:
    1. Discover relevant videos
    2. Extract claims from transcripts + comments
    3. Synthesize cross-video narrative
    4. Save results to a timestamped JSON file
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
 
        # ── Step 4: Output ──────────────────────────────────────
        output = {
            "generated_at": datetime.now().isoformat(),
            "video_count": len(all_results),
            "per_video": all_results,
            "synthesis": final_summary
        }
 
        output_path = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
 
        log.info(f"Saved to {output_path}")
        print("\n=== FINAL INTELLIGENCE SUMMARY ===\n")
        print(json.dumps(final_summary, indent=2))
 
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
        max_comments=30
    )




