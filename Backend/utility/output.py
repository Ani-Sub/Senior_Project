"""
Output manager for the YouTube Intelligence pipeline.

Handles:
- Checkpoint saves (crash recovery)
- Database-ready flat file exports
- Run organization
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class OutputManager:
    """
    Manages pipeline output with checkpoints and DB-ready exports.
    
    Directory structure:
        output/latest/
        ├── checkpoints/
        │   ├── video_abc123.json
        │   ├── video_def456.json
        │   ├── synthesis.json
        │   ├── trends.json
        │   └── risk.json
        │
        └── db_ready/
            ├── channels.json
            ├── videos.json
            ├── claims.json
            ├── narratives.json
            └── risk_flags.json
    
    Note: Each run overwrites the previous. Use static path: output/latest/db_ready/
    """
    
    def __init__(self, output_dir: str | Path = "output"):
        self.run_dir = Path(output_dir) / "latest"
        self.checkpoint_dir = self.run_dir / "checkpoints"
        self.db_ready_dir = self.run_dir / "db_ready"
        
        # Clear previous run data
        self._clear_directory(self.checkpoint_dir)
        self._clear_directory(self.db_ready_dir)
        
        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.db_ready_dir.mkdir(parents=True, exist_ok=True)
        
        # Track what's been saved
        self.video_results = []
        self.synthesis = None
        self.trends = None
        self.risk = None
        
        log.info(f"Output directory: {self.run_dir}")
    
    def _clear_directory(self, dir_path: Path) -> None:
        """Clear all files in a directory (if it exists)."""
        if dir_path.exists():
            for file in dir_path.iterdir():
                if file.is_file():
                    file.unlink()
            log.info(f"Cleared previous data from {dir_path}")
    
    def _save_json(self, path: Path, data: Any) -> None:
        """Save data as JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_json(self, path: Path) -> Any:
        """Load JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # ─── Checkpoint Methods ───────────────────────────────────────────────
    
    def save_video_checkpoint(self, video_result: dict) -> None:
        """Save individual video result immediately after processing."""
        video_id = video_result.get("video_id", "unknown")
        path = self.checkpoint_dir / f"video_{video_id}.json"
        self._save_json(path, video_result)
        self.video_results.append(video_result)
        log.info(f"  ✓ Checkpoint saved: {path.name}")
    
    def save_synthesis_checkpoint(self, synthesis: dict) -> None:
        """Save synthesis results."""
        path = self.checkpoint_dir / "synthesis.json"
        self._save_json(path, synthesis)
        self.synthesis = synthesis
        log.info(f"  ✓ Checkpoint saved: synthesis.json")
    
    def save_trends_checkpoint(self, trends: dict) -> None:
        """Save trend analysis results."""
        path = self.checkpoint_dir / "trends.json"
        self._save_json(path, trends)
        self.trends = trends
        log.info(f"  ✓ Checkpoint saved: trends.json")
    
    def save_risk_checkpoint(self, risk: dict) -> None:
        """Save risk assessment results."""
        path = self.checkpoint_dir / "risk.json"
        self._save_json(path, risk)
        self.risk = risk
        log.info(f"  ✓ Checkpoint saved: risk.json")
    
    def load_checkpoints(self) -> dict:
        """
        Load all checkpoints from a previous run.
        Useful for resuming a failed pipeline.
        """
        results = {
            "videos": [],
            "synthesis": None,
            "trends": None,
            "risk": None
        }
        
        # Load video checkpoints
        for path in self.checkpoint_dir.glob("video_*.json"):
            results["videos"].append(self._load_json(path))
        
        # Load other checkpoints if they exist
        synthesis_path = self.checkpoint_dir / "synthesis.json"
        if synthesis_path.exists():
            results["synthesis"] = self._load_json(synthesis_path)
        
        trends_path = self.checkpoint_dir / "trends.json"
        if trends_path.exists():
            results["trends"] = self._load_json(trends_path)
        
        risk_path = self.checkpoint_dir / "risk.json"
        if risk_path.exists():
            results["risk"] = self._load_json(risk_path)
        
        return results
    
    # ─── Database-Ready Export ────────────────────────────────────────────
    
    def export_db_ready(
        self,
        video_results: list[dict],
        synthesis: dict | None = None,
        trends: dict | None = None,
        risk: dict | None = None,
        search_params: dict | None = None
    ) -> None:
        """
        Export all data in flat, database-ready format.
        Each file maps directly to a database table.
        """
        log.info("Exporting database-ready files...")
        
        processed_at = datetime.now().isoformat()
        
        # Extract and flatten data
        channels = self._extract_channels(video_results)
        videos = self._extract_videos(video_results, processed_at)
        transcripts = self._extract_transcripts(video_results, processed_at)
        comments = self._extract_comments(video_results, processed_at)
        claims = self._extract_claims(video_results, risk, processed_at)


        #COMPUTE CHANNEL RISK STATS; NEW
        channel_stats = {}

        #Initialize stats
        for ch in channels:
            channel_stats[ch["channel_id"]] = {
                "total": 0,
                "flagged": 0,
                "confidence_sum": 0.0
            }

        #Get channel data from claims
        claims_with_channel = 0
        claims_without_channel = 0
        for claim in claims:
            ch_id = claim.get("channel_id")
            if not ch_id or ch_id not in channel_stats:
                claims_without_channel += 1
                continue
            claims_with_channel += 1
            channel_stats[ch_id]["total"] += 1
            channel_stats[ch_id]["confidence_sum"] += claim.get("confidence_score", 0)

        # Count flagged claims from risk flags (flag count per video, by channel)
        # This replaces exact-text matching which never fires in practice
        if risk:
            video_to_channel = {
                r.get("video_id"): r.get("video_metadata", {}).get("channel_id")
                for r in video_results if r.get("video_id")
            }
            for video_risk in risk.get("per_video", []):
                vid = video_risk.get("video_id")
                ch_id = video_to_channel.get(vid)
                if ch_id and ch_id in channel_stats:
                    channel_stats[ch_id]["flagged"] += len(video_risk.get("flags", []))

        log.info(f"  → Channel stats: {len(channels)} channels, {len(claims)} total claims, "
                 f"{claims_with_channel} matched to channels, {claims_without_channel} unmatched")
        for ch_id, s in channel_stats.items():
            log.info(f"    {ch_id}: total={s['total']} flagged={s['flagged']}")

        #Apply stats back to channels
        for ch in channels:
            ch_id = ch["channel_id"]
            stats = channel_stats.get(ch_id, {})

            total = stats.get("total", 0)
            flagged = stats.get("flagged", 0)
            confidence_sum = stats.get("confidence_sum", 0.0)

            ch["total_claims"] = total
            ch["flagged_claims"] = flagged
            ch["accuracy_rate"] = (confidence_sum / total) if total > 0 else 0

            risk_score = (flagged / total) if total > 0 else 0
            ch["risk_score"] = risk_score
            ch["risk_level"] = self._confidence_to_risk_level(risk_score)
            ch["processed_at"] = processed_at

        narratives = self._extract_narratives(synthesis, video_results)
        narrative_videos = self._extract_narrative_videos(synthesis)
        risk_flags = self._extract_risk_flags(risk)
        
        # Save each table
        self._save_json(self.db_ready_dir / "channels.json", channels)
        log.info(f"  ✓ channels.json ({len(channels)} records)")
        
        self._save_json(self.db_ready_dir / "videos.json", videos)
        log.info(f"  ✓ videos.json ({len(videos)} records)")
        
        self._save_json(self.db_ready_dir / "transcripts.json", transcripts)
        log.info(f"  ✓ transcripts.json ({len(transcripts)} records)")

        self._save_json(self.db_ready_dir / "comments.json", comments)
        log.info(f"  ✓ comments.json ({len(comments)} records)")
        
        self._save_json(self.db_ready_dir / "claims.json", claims)
        log.info(f"  ✓ claims.json ({len(claims)} records)")
        
        self._save_json(self.db_ready_dir / "narratives.json", narratives)
        log.info(f"  ✓ narratives.json ({len(narratives)} records)")
        
        self._save_json(self.db_ready_dir / "narrative_videos.json", narrative_videos)
        log.info(f"  ✓ narrative_videos.json ({len(narrative_videos)} records)")
        
        self._save_json(self.db_ready_dir / "risk_flags.json", risk_flags)
        log.info(f"  ✓ risk_flags.json ({len(risk_flags)} records)")
        
        # Save trends data
        if trends:
            # Per-narrative timeline (one row per narrative per period)
            timeline = self._extract_trends_timeline(trends)
            self._save_json(self.db_ready_dir / "trends_timeline.json", timeline)
            log.info(f"  ✓ trends_timeline.json ({len(timeline)} records)")
            
            # Per-narrative trends
            narrative_trends = self._extract_narrative_trends(trends)
            self._save_json(self.db_ready_dir / "narrative_trends.json", narrative_trends)
            log.info(f"  ✓ narrative_trends.json ({len(narrative_trends)} records)")
        
        # Save run metadata
        metadata = {
            "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": processed_at,
            "search_params": search_params,
            "video_count": len(videos),
            "transcript_count": len(transcripts),
            "comment_count": len(comments),
            "claim_count": len(claims),
            "narrative_count": len(narratives),
            "risk_flag_count": len(risk_flags)
        }
        self._save_json(self.db_ready_dir / "run_metadata.json", metadata)
        log.info(f"  ✓ run_metadata.json")
    
    def _extract_channels(self, video_results: list[dict]) -> list[dict]:
        """Extract unique channels from video results."""
        channels = {}
        for result in video_results:
            meta = result.get("video_metadata", {})
            channel_id = meta.get("channel_id")
            channel_title = meta.get("channel_title")
            
            if channel_id and channel_id not in channels:
                channels[channel_id] = {
                    "channel_id": channel_id,
                    "channel_name": channel_title or "",  # Schema uses channel_name
                    "total_claims": 0,  # Will be calculated
                    "flagged_claims": 0,
                    "accuracy_rate": 0.0,
                    "risk_level": "low",
                    "risk_score": 0.0,
                    "processed_at": None,
                }
        
        # Calculate claim counts per channel
        for result in video_results:
            ch_id = result.get("video_metadata", {}).get("channel_id")
            if ch_id and ch_id in channels:
                channels[ch_id]["total_claims"] += result.get("claim_count", 0)
        
        return list(channels.values())
    
    def _extract_videos(self, video_results: list[dict], processed_at: str) -> list[dict]:
        """Extract video metadata matching Prisma Video model."""
        videos = []
        for result in video_results:
            meta = result.get("video_metadata", {})
            videos.append({
                "video_id": result.get("video_id"),
                "channel_id": meta.get("channel_id"),
                "title": meta.get("title"),
                "description": meta.get("description", ""),
                "view_count": meta.get("view_count"),
                "duration_seconds": meta.get("duration_seconds"),
                "published_at": meta.get("published_at"),
                "processed": True,
                "processed_at": processed_at,
            })
        return videos
    
    def _extract_transcripts(self, video_results: list[dict], processed_at: str) -> list[dict]:
        """Extract transcripts matching Prisma Transcript model."""
        transcripts = []
        transcript_id = 1
        
        for result in video_results:
            video_id = result.get("video_id")
            meta = result.get("video_metadata", {})
            transcript_text = result.get("_transcript", "")
            
            if transcript_text:
                transcripts.append({
                    "transcript_id": transcript_id,
                    "video_id": video_id,
                    "channel_id": meta.get("channel_id"),
                    "video_title": meta.get("title", ""),
                    "transcript": transcript_text,
                    "processed_at": processed_at,
                })
                transcript_id += 1
        
        return transcripts
    
    def _extract_transcript_chunks(self, video_results: list[dict], processed_at: str) -> list[dict]:
        """Extract transcript chunks matching Prisma TranscriptChunk model."""
        from utility.chunker import chunk_text
        
        chunks = []
        chunk_id = 1
        transcript_id = 1
        
        for result in video_results:
            transcript_text = result.get("_transcript", "")
            video_title = result.get("video_metadata", {}).get("title", "")
            
            if transcript_text:
                video_chunks = chunk_text(transcript_text)
                for chunk_number, chunk_text_content in enumerate(video_chunks, start=1):
                    chunks.append({
                        "chunk_id": chunk_id,
                        "transcript_id": transcript_id,
                        "video_title": video_title,
                        "chunk_text": chunk_text_content,
                        "chunk_number": chunk_number,
                        "processed_at": processed_at,
                    })
                    chunk_id += 1
                transcript_id += 1
        
        return chunks
    
    def _extract_comments(self, video_results: list[dict], processed_at: str) -> list[dict]:
        """Extract comments matching Prisma Comment model."""
        comments = []
        
        for result in video_results:
            video_comments = result.get("_comments", [])
            
            for comment in video_comments:
                comments.append({
                    "comment_id": comment.get("comment_id"),
                    "video_id": comment.get("video_id"),
                    "commenter_name": comment.get("commenter_name", "")[:50],  # Schema limit
                    "comment_text": (comment.get("comment_text") or comment.get("text", ""))[:500],  # Schema limit
                    "published_date": comment.get("published_at", ""),  # Schema uses published_date as String
                    "is_reply": comment.get("is_reply", False),
                    "top_level_comment_id": comment.get("top_level_comment_id"),
                    "processed_at": processed_at,
                })
        
        return comments
    
    def _map_claim_type(self, llm_type: str | None) -> str:
        if not llm_type:
            return "factual"
        llm_type = llm_type.lower()
        valid = {"factual", "opinion", "prediction", "statistic"}
        return llm_type if llm_type in valid else "factual"
    
    def _confidence_to_risk_level(self, confidence: float) -> str:
        """Map confidence score to risk level (low/medium/high)."""
        if confidence >= 0.7:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _get_claim_risk_level(
        self, 
        claim_text: str, 
        video_flags: list[dict]
    ) -> str:
        """
        Determine risk level for a claim by checking if it matches any risk flags.
        
        Checks if the claim text appears in the excerpt or context of any flag.
        Returns the highest risk level if multiple matches found.
        """
        if not claim_text or not video_flags:
            return "low"
        
        claim_lower = claim_text.lower().strip()
        highest_confidence = 0.0
        
        for flag in video_flags:
            excerpt = (flag.get("excerpt") or "").lower().strip()
            
           # Exact match only (prevents false positives)
            if claim_lower.strip() == excerpt.strip():
                flag_confidence = float(flag.get("confidence") or 0.5)
                highest_confidence = max(highest_confidence, flag_confidence)
        
        if highest_confidence > 0:
            return self._confidence_to_risk_level(highest_confidence)
        
        return "low"
    
    def _extract_claims(
        self, 
        video_results: list[dict], 
        risk_data: dict | None,
        processed_at: str
    ) -> list[dict]:
        """Extract all claims matching Prisma Claim model."""
        claims = []
        claim_id = 1
        
        # Build risk flags lookup by video_id
        video_flags_lookup: dict[str, list[dict]] = {}
        if risk_data:
            for video_risk in risk_data.get("per_video", []):
                vid = video_risk.get("video_id")
                if vid is not None:
                    flags = video_risk.get("flags", [])
                    video_flags_lookup[vid] = flags
        
        for result in video_results:
            video_id = result.get("video_id", "")
            video_title = result.get("video_metadata", {}).get("title", "")
            video_flags = video_flags_lookup.get(video_id, []) if video_id else []
            
            for claim in result.get("claims", []):
                claim_text = claim.get("text", "")
                
                # Check if this specific claim matches any risk flags
                risk_level = self._get_claim_risk_level(claim_text, video_flags)
                
                claims.append({
                    "claim_id": claim_id,
                    "video_id": video_id,
                    "channel_id": result.get("video_metadata", {}).get("channel_id"), 
                    "narrative_id": None,  # To be linked later
                    "video_title": video_title,
                    "claim_text": claim_text,
                    "claim_type": self._map_claim_type(claim.get("type")),
                    "confidence_score": float(claim.get("confidence", 0.5)),
                    "risk_level": risk_level,
                    "processed_at": processed_at,
                    "is_verified": False,
                    "accuracy_rating": None,
                })
                claim_id += 1
        
        return claims
    
    def _extract_narratives(
        self, 
        synthesis: dict | None, 
        video_results: list[dict]
    ) -> list[dict]:
        """Extract narratives matching Prisma Narrative model."""
        narratives_out = []
        
        if not synthesis:
            return narratives_out
        
        # Color palette for narratives
        colors = [
            "#3B82F6",  # Blue
            "#10B981",  # Emerald
            "#F59E0B",  # Amber
            "#EF4444",  # Red
            "#8B5CF6",  # Violet
            "#EC4899",  # Pink
            "#06B6D4",  # Cyan
            "#84CC16",  # Lime
        ]
        
        # Build video lookup for timestamps and claims
        video_lookup = {r.get("video_id"): r for r in video_results}
        
        # New structure: synthesis has "narratives" array
        for idx, narrative in enumerate(synthesis.get("narratives", [])):
            if not narrative.get("name"):
                continue

            video_ids = narrative.get("video_ids", [])
            
            # Collect claims and timestamps for this narrative
            claim_count = 0
            timestamps = []
            
            for vid in video_ids:
                if vid in video_lookup:
                    result = video_lookup[vid]
                    claim_count += result.get("claim_count", 0)
                    pub_at = result.get("video_metadata", {}).get("published_at")
                    if pub_at:
                        timestamps.append(pub_at)
            
            timestamps.sort()
            
            narratives_out.append({
                "narrative_id": narrative.get("id"),
                "title": narrative.get("name"),  # Schema uses "title"
                "summary": narrative.get("summary"),
                "topic_label": narrative.get("name"),  # Use name as topic label
                "claim_count": claim_count,
                "color": colors[idx % len(colors)],  # Assign color from palette
                "first_seen_at": timestamps[0] if timestamps else None,
                "last_seen_at": timestamps[-1] if timestamps else None,
            })
        
        # Also include overall summary as a special narrative
        if synthesis.get("overall_summary"):
            all_timestamps = []
            
            for result in video_results:
                pub_at = result.get("video_metadata", {}).get("published_at")
                if pub_at:
                    all_timestamps.append(pub_at)
            
            all_timestamps.sort()
            
            narratives_out.insert(0, {
                "narrative_id": str(uuid.uuid4()),
                "title": "Overall Summary",
                "summary": synthesis.get("overall_summary"),
                "topic_label": "Overall",
                "claim_count": sum(r.get("claim_count", 0) for r in video_results),
                "color": "#6B7280",  # Gray for overall
                "first_seen_at": all_timestamps[0] if all_timestamps else None,
                "last_seen_at": all_timestamps[-1] if all_timestamps else None,
            })
        
        return narratives_out
    
    def _extract_risk_flags(self, risk: dict | None) -> list[dict]:
        """Extract risk flags in flat format."""
        flags = []
        
        if not risk:
            return flags
        
        flag_id = 1
        for video_risk in risk.get("per_video", []):
            video_id = video_risk.get("video_id")
            for flag in video_risk.get("flags", []):
                flags.append({
                    "flag_id": flag_id,
                    "video_id": video_id,
                    "category": flag.get("category"),
                    "confidence": flag.get("confidence"),
                    "source": flag.get("source"),
                    "excerpt": flag.get("excerpt"),
                    "context": flag.get("context"),
                    "detection_method": flag.get("detection_method")
                })
                flag_id += 1
        
        return flags
    
    def _extract_trends_timeline(self, trends: dict) -> list[dict]:
        """Extract trends timeline for database - one row per narrative per period."""
        timeline = []
        
        # Extract from per-narrative timelines (each narrative has its own metrics)
        for narrative in trends.get("narratives", []):
            narrative_id = narrative.get("narrative_id")
            
            for entry in narrative.get("timeline", []):
                timeline.append({
                    "narrative_id": narrative_id,
                    "period": entry.get("period"),
                    "period_start_iso": entry.get("period_start_iso"),
                    "period_start_ts": entry.get("period_start_ts"),
                    "video_count": entry.get("video_count"),
                    "total_views": entry.get("total_views"),
                    "total_likes": entry.get("total_likes"),
                    "total_comments": entry.get("total_comments"),
                    "engagement_ratio": entry.get("engagement_ratio"),
                    "claim_count": entry.get("claim_count"),
                    "avg_confidence": entry.get("avg_confidence")
                })
        
        return timeline
    
    def _extract_narrative_videos(self, synthesis: dict | None) -> list[dict]:
        """Extract narrative-video links (many-to-many relationship)."""
        links = []
        
        if not synthesis:
            return links
        
        for narrative in synthesis.get("narratives", []):
            narrative_id = narrative.get("id")
            for video_id in narrative.get("video_ids", []):
                links.append({
                    "narrative_id": narrative_id,
                    "video_id": video_id
                })
        
        return links
    
    def _extract_narrative_trends(self, trends: dict) -> list[dict]:
        """Extract per-narrative trend data."""
        narrative_trends = []
        
        for narrative in trends.get("narratives", []):
            trend_data = narrative.get("trend", {})
            narrative_trends.append({
                "narrative_id": narrative.get("narrative_id"),
                "name": narrative.get("name"),
                "video_count": narrative.get("video_count"),
                "pattern": trend_data.get("pattern"),
                "confidence": trend_data.get("confidence"),
                "peak_period": trend_data.get("peak_period"),
                "description": trend_data.get("description")
            })
        
        return narrative_trends
    
    def get_run_path(self) -> str:
        """Return the path to the current run directory."""
        return str(self.run_dir)
    
    def cleanup(self) -> None:
        """
        Delete all output data after successful DB import.
        
        Removes all files from checkpoints/ and db_ready/ directories.
        """
        cleanup_output(self.run_dir)


def cleanup_output(output_dir: str | Path = "output") -> bool:
    """
    Delete the entire output folder after successful DB import.
    
    Call this after importing data to your database to free up disk space.
    
    Args:
        output_dir: Path to the output directory (default: output)
    
    Returns:
        True if cleanup succeeded, False if directory doesn't exist
    
    Usage:
        from utility.output import cleanup_output
        
        # After successful DB import:
        cleanup_output()  # Deletes entire output/ folder
    """
    import shutil
    
    output_path = Path(output_dir)
    
    if not output_path.exists():
        log.warning(f"Output directory does not exist: {output_path}")
        return False
    
    # Remove entire output folder
    shutil.rmtree(output_path)
    log.info(f"Removed output directory: {output_path}")
    
    log.info("Output cleanup complete")
    return True
