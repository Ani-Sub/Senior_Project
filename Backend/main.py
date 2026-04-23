"""
YouTube Intelligence Pipeline — Main Entry Point

Pipeline steps:
1. Discover videos (with RSS/cache optimization)
2. Extract claims from each video (checkpoint after each)
3. Synthesize cross-video narrative (checkpoint)
4. Analyze temporal trends (checkpoint)
5. Assess content risk (cheoutckpoint)
6. Export database-ready files
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal
#Added Imports for Railway DB
import os
import json
import uuid
import psycopg2
from psycopg2.extras import Json

from ytAPI.videoExtract import discover_videos, SearchMode
from ytAPI.transcriptExtract import get_transcript
from ytAPI.commentExtract import get_comments
from extraction.analyzer import analyze_video, synthesize_trends, call_llm
from extraction.confidence import boost_confidence_by_agreement
from utility.output import OutputManager
from trends import generate_trend_summary, Granularity
from risk import assess_video_risk, generate_risk_summary

# Output directory inside Backend folder
BACKEND_DIR = Path(__file__).parent
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "output"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def save_results_to_railway(
    video_results,
    synthesis,
    trends,
    risk_analysis,
    search_params
):
    datebase_url = os.getenv("DATABASE_URL")
    if not datebase_url:
        log.error("DATABASE_URL not set. Skipping Railway DB save.")
        return
    
    

    conn = psycopg2.connect(datebase_url)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT board_id, board_name
            FROM "Board"
        """)

        boards = cur.fetchall()

        if not boards:
            raise RuntimeError("No boards found in database.") 
    
        default_color = "#00d4ff"

        for board_id, board_name in boards:
            log.info(f"Saving results to board: {board_name} ({board_id})")

            cur.execute("""
                INSERT INTO "Channel" (
                    channel_id,
                    channel_name,
                    total_claims,
                    flagged_claims,
                    accuracy_rate,
                    risk_level,
                    risk_score,
                    processed_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (channel_id) DO NOTHING;
            """, (
                meta.get("channel_id"),
                meta.get("channel_title", "Unknown"),
                0,
                0,
                0.0,
                "low",
                0.0
            ))

            # Save videos
            for result in video_results:
                meta = result.get("video_metadata", {})

                cur.execute("""
                INSERT INTO "Channel" (
                    channel_id,
                    channel_name,
                    total_claims,
                    flagged_claims,
                    accuracy_rate,
                    risk_level,
                    risk_score,
                    processed_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (channel_id) DO NOTHING;
            """, (
                meta.get("channel_id"),
                meta.get("channel_title", "Unknown"),
                0,
                0,
                0.0,
                "low",
                0.0
            ))

                cur.execute("""
                    INSERT INTO "Video" (
                        video_id,
                        board_id,
                        channel_id,
                        title,
                        description,
                        view_count,
                        duration_seconds,
                        published_at,
                        processed,
                        processed_at    
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (video_id)
                    DO UPDATE SET
                        board_id = EXCLUDED.board_id,
                        channel_id = EXCLUDED.channel_id,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        view_count = EXCLUDED.view_count,
                        duration_seconds = EXCLUDED.duration_seconds,
                        published_at = EXCLUDED.published_at,
                        processed = EXCLUDED.processed,
                        processed_at = NOW();
                """, (
                    meta.get("video_id"),
                    board_id,
                    meta.get("channel_id"),
                    meta.get("title"),
                    meta.get("description", ""),
                    meta.get("view_count"),
                    meta.get("duration_seconds"),
                    meta.get("published_at"),
                    True
                ))

            # Match trend narratives by narrative_id
            trend_narratives = {
                n.get("narrative_id"): n for n in trends.get("narratives", [])
            }

            # Save narratives
            for narrative in synthesis.get("narratives", []):
                narrative_id = narrative.get("id")
                if not narrative_id:
                    continue

                matching_trend = trend_narratives.get(narrative_id, {})
                timeline = matching_trend.get("timeline", [])

            
                if timeline:
                    first_seen_at = timeline[0].get("period_start_iso")
                    last_seen_at = timeline[-1].get("period_start_iso")
                else:
                    first_seen_at = trends.get("time_range", {}).get("start")
                    last_seen_at = trends.get("time_range", {}).get("end")

                claim_count = sum(point.get("claim_count", 0) for point in timeline) if timeline else 0
        
                cur.execute("""
                    INSERT INTO "Narrative" (
                        narrative_id,
                        board_id,
                        title,
                        summary,
                        topic_label,
                        claim_count,
                        color,
                        first_seen_at,
                        last_seen_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (narrative_id)
                    DO UPDATE SET
                        board_id = EXCLUDED.board_id,
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        topic_label = EXCLUDED.topic_label,
                        claim_count = EXCLUDED.claim_count,
                        color = EXCLUDED.color,
                        first_seen_at = EXCLUDED.first_seen_at,
                        last_seen_at = EXCLUDED.last_seen_at;
                """, (
                    narrative_id,
                    board_id,
                    narrative.get("name"),
                    narrative.get("summary"),
                    narrative.get("topic_label"),
                    claim_count,
                    default_color,
                    first_seen_at,
                    last_seen_at
                ))

            # Save trend row
            trend_id = str(uuid.uuid4())
            labels = [p.get("period") for p in trends.get("overall", {}).get("timeline", [])]

            cur.execute("""
                INSERT INTO "Trend" (
                    trend_id,
                    board_id,
                    labels,
                    created_at
                )
                VALUES (%s, %s, %s, NOW());
            """, (
                trend_id,
                board_id,
                labels
            ))

            # Save trend datasets
            valid_directions = {"rising", "peaking", "declining", "stable"}

            for narrative in trends.get("narratives", []):
                direction = narrative.get("trend", {}).get("pattern", "stable")
                if direction not in valid_directions:
                    direction = "stable"

                data_points = [p.get("total_views", 0) for p in narrative.get("timeline", [])]

                cur.execute("""
                    INSERT INTO "TrendData" (
                        dataset_id,
                        trend_id,
                        narrative_id,
                        label,
                        color,
                        data,
                        direction
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (
                    str(uuid.uuid4()),
                    trend_id,
                    narrative.get("narrative_id"),
                    narrative.get("name"),
                    default_color,
                    data_points,
                    direction
                ))

        conn.commit()
        log.info("✓ Results saved to Railway")

    except Exception as e:
        conn.rollback()
        log.error(f"Failed to save results to Railway: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def run_pipeline(
    search_keywords: str,
    channel_sub_min: int,
    video_view_min: int,
    video_keywords: list[str],
    days: int = 90,
    max_comments: int = 30,
    trend_granularity: Granularity = "weekly",
    assess_risk: bool = True,
    llm_verify_risk: bool = True,
    use_cache: bool = True,
    cache_max_age_days: int = 30,
    search_mode: SearchMode = "videos",
    output_dir: str | Path | None = None
) -> str | None:
    """
    Run the full YouTube intelligence pipeline with checkpoint saves.
    
    Each major step saves progress, so crashes don't lose data.
    Final output is exported in database-ready format.
    
    Args:
        search_keywords: Keywords to search for
        channel_sub_min: Minimum subscriber count for channels
        video_view_min: Minimum view count for videos
        video_keywords: Keywords that must appear in video titles
        days: How far back to look for videos
        max_comments: Maximum comments to extract per video
        trend_granularity: Time granularity for trend analysis ("daily" or "weekly")
        assess_risk: Whether to run risk assessment on content
        llm_verify_risk: Whether to use LLM for borderline risk cases
        use_cache: Use channel cache + RSS feeds to reduce API quota
        cache_max_age_days: Days before cached channels expire
        search_mode: "videos" (default) or "channels"
            - "videos": Search videos first, extract channels (catches more creators)
            - "channels": Search channels by name only
        output_dir: Base directory for output files
    
    Returns:
        Path to the run directory, or None if pipeline failed
    """
    
    # Use Backend/output as default if not specified
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    
    # Initialize output manager
    output = OutputManager(output_dir=output_dir)
    log.info(f"Pipeline started — output: {output.get_run_path()}")
    
    search_params = {
        "keywords": search_keywords,
        "channel_sub_min": channel_sub_min,
        "video_view_min": video_view_min,
        "video_keywords": video_keywords,
        "days": days,
        "trend_granularity": trend_granularity,
        "risk_assessment_enabled": assess_risk
    }
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 1: Discovery
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info("STEP 1: Discovering videos")
    log.info("="*60)
    
    discovered_videos = discover_videos(
        search_keywords=search_keywords,
        channel_sub_min=channel_sub_min,
        video_view_min=video_view_min,
        video_keywords=video_keywords,
        days=days,
        use_cache=use_cache,
        cache_max_age_days=cache_max_age_days,
        search_mode=search_mode
    )
    
    if not discovered_videos:
        log.warning("No videos found. Try broadening your search criteria.")
        return None
    
    log.info(f"✓ Discovered {len(discovered_videos)} videos")
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 2: Extract claims (checkpoint after each video)
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info("STEP 2: Extracting claims from videos")
    log.info("="*60)
    
    all_results = []
    
    for i, video in enumerate(discovered_videos, 1):
        video_id = video["video_id"]
        log.info(f"\n[{i}/{len(discovered_videos)}] Processing: {video_id}")
        log.info(f"  Title: {video.get('title', 'Unknown')[:60]}...")
        
        # Fetch transcript
        transcript = get_transcript(video_id)
        if not transcript:
            log.warning(f"  ✗ No transcript available, skipping")
            continue
        
        # Fetch comments
        comments = get_comments(video_id, max_comments=max_comments)
        log.info(f"  → Fetched {len(comments)} comments")
        
        # Analyze video
        result = analyze_video(video_id, transcript, comments)
        
        if not result:
            log.warning(f"  ✗ Analysis failed, skipping")
            continue
        
        # Add metadata
        result["video_metadata"] = {
            "video_id": video.get("video_id"),
            "channel_id": video.get("channel_id"),
            "title": video.get("title"),
            "description": video.get("description", ""),
            "channel_title": video.get("channel_title"),
            "published_at": video.get("published_at"),
            "view_count": video.get("view_count"),
            "like_count": video.get("like_count"),
            "comment_count": video.get("comment_count"),
            "duration": video.get("duration"),
            "duration_seconds": video.get("duration_seconds"),
        }
        result["comment_timestamps"] = [c.get("published_at") for c in comments if c.get("published_at")]
        
        # Store raw content for DB export
        result["_transcript"] = transcript
        result["_comments"] = comments
        
        # CHECKPOINT: Save immediately
        output.save_video_checkpoint(result)
        all_results.append(result)
        
        log.info(f"  ✓ Extracted {result['claim_count']} claims ({result['transcript_claim_count']} transcript, {result['comment_claim_count']} comments)")
    
    if not all_results:
        log.error("No videos were successfully processed.")
        return None
    
    log.info(f"\n✓ Processed {len(all_results)}/{len(discovered_videos)} videos")
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 2.5: Confidence Adjustment
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info("STEP 2.5: Adjusting claim confidence (cross-video agreement)")
    log.info("="*60)
    
    all_results = boost_confidence_by_agreement(all_results)
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 3: Synthesis
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info("STEP 3: Synthesizing cross-video narrative")
    log.info("="*60)
    
    synthesis = synthesize_trends(all_results)
    
    if synthesis:
        output.save_synthesis_checkpoint(synthesis)
        log.info(f"✓ Synthesis complete")
        log.info(f"  Common topics: {synthesis.get('common_topics', [])}")
    else:
        log.warning("✗ Synthesis failed — continuing with other steps")
        synthesis = {}
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 4: Trend Analysis
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info(f"STEP 4: Analyzing trends ({trend_granularity} granularity)")
    log.info("="*60)
    
    trends = generate_trend_summary(
        video_results=all_results,
        synthesis=synthesis,
        granularity=trend_granularity
    )
    
    output.save_trends_checkpoint(trends)
    
    pattern = trends.get("overall", {}).get("trend", {}).get("pattern", "unknown")
    log.info(f"✓ Trend analysis complete: {pattern} pattern detected")
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 5: Risk Assessment
    # ══════════════════════════════════════════════════════════════════════
    risk_analysis = None
    
    if assess_risk:
        log.info("\n" + "="*60)
        log.info("STEP 5: Assessing content risk")
        log.info("="*60)
        
        risk_assessments = []
        llm_fn = call_llm if llm_verify_risk else None
        
        for result in all_results:
            video_id = result["video_id"]
            transcript = result.get("_transcript", "")
            comments = result.get("_comments", [])
            
            assessment = assess_video_risk(
                video_id=video_id,
                transcript=transcript,
                comments=comments,
                llm_call_fn=llm_fn,
                verify_borderline=llm_verify_risk
            )
            risk_assessments.append(assessment)
            
            if assessment.flags:
                log.info(f"  ⚠ {video_id}: {len(assessment.flags)} flags ({assessment.risk_level})")
        
        risk_analysis = generate_risk_summary(all_results, risk_assessments)
        output.save_risk_checkpoint(risk_analysis)
        
        flagged = risk_analysis["aggregate"]["videos_with_risks"]
        total_flags = risk_analysis["aggregate"]["total_flags"]
        log.info(f"✓ Risk assessment complete: {flagged} videos with {total_flags} flags")
    
    # ══════════════════════════════════════════════════════════════════════
    # STEP 6: Export database-ready files
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info("STEP 6: Exporting database-ready files")
    log.info("="*60)
    
    output.export_db_ready(
        video_results=all_results,
        synthesis=synthesis,
        trends=trends,
        risk=risk_analysis,
        search_params=search_params
    )

    save_results_to_railway(
    video_results=all_results,
    synthesis=synthesis,
    trends=trends,
    risk_analysis=risk_analysis,
    search_params=search_params
    )
    
    # Clean up internal fields after export
    for result in all_results:
        result.pop("_transcript", None)
        result.pop("_comments", None)
    
    # ══════════════════════════════════════════════════════════════════════
    # DONE
    # ══════════════════════════════════════════════════════════════════════
    log.info("\n" + "="*60)
    log.info("PIPELINE COMPLETE")
    log.info("="*60)
    log.info(f"Output directory: {output.get_run_path()}")
    log.info(f"Videos processed: {len(all_results)}")
    log.info(f"Total claims: {sum(r.get('claim_count', 0) for r in all_results)}")
    log.info(f"Trend pattern: {pattern}")
    if risk_analysis:
        log.info(f"Risk level: {risk_analysis['aggregate']['overall_risk_level']}")
    
    return output.get_run_path()


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
        llm_verify_risk=True,
        use_cache=True,
        cache_max_age_days=30,
        search_mode="videos",  # "videos" (recommended) or "channels"
    )
