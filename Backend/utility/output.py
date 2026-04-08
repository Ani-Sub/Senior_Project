"""
Output manager for the YouTube Intelligence pipeline.

Handles:
- Checkpoint saves (crash recovery)
- Database-ready flat file exports
- Run organization
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class OutputManager:
    """
    Manages pipeline output with checkpoints and DB-ready exports.
    
    Directory structure:
        output/run_YYYYMMDD_HHMMSS/
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
    """
    
    def __init__(self, output_dir: str = "output"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path(output_dir) / f"run_{timestamp}"
        self.checkpoint_dir = self.run_dir / "checkpoints"
        self.db_ready_dir = self.run_dir / "db_ready"
        
        # Create directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.db_ready_dir.mkdir(parents=True, exist_ok=True)
        
        # Track what's been saved
        self.video_results = []
        self.synthesis = None
        self.trends = None
        self.risk = None
        
        log.info(f"Output directory: {self.run_dir}")
    
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
        
        # Extract and flatten data
        channels = self._extract_channels(video_results)
        videos = self._extract_videos(video_results)
        claims = self._extract_claims(video_results)
        narratives = self._extract_narratives(synthesis, video_results)
        narrative_videos = self._extract_narrative_videos(synthesis)
        risk_flags = self._extract_risk_flags(risk)
        
        # Save each table
        self._save_json(self.db_ready_dir / "channels.json", channels)
        log.info(f"  ✓ channels.json ({len(channels)} records)")
        
        self._save_json(self.db_ready_dir / "videos.json", videos)
        log.info(f"  ✓ videos.json ({len(videos)} records)")
        
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
            # Overall timeline
            timeline = self._extract_trends_timeline(trends)
            self._save_json(self.db_ready_dir / "trends_timeline.json", timeline)
            log.info(f"  ✓ trends_timeline.json ({len(timeline)} records)")
            
            # Per-narrative trends
            narrative_trends = self._extract_narrative_trends(trends)
            self._save_json(self.db_ready_dir / "narrative_trends.json", narrative_trends)
            log.info(f"  ✓ narrative_trends.json ({len(narrative_trends)} records)")
        
        # Save run metadata
        metadata = {
            "run_id": self.run_dir.name,
            "created_at": datetime.now().isoformat(),
            "search_params": search_params,
            "video_count": len(videos),
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
            channel_title = meta.get("channel_title")
            if channel_title and channel_title not in channels:
                channels[channel_title] = {
                    "channel_title": channel_title,
                    # channel_id would need to be added to video_metadata
                }
        return list(channels.values())
    
    def _extract_videos(self, video_results: list[dict]) -> list[dict]:
        """Extract video metadata in flat format."""
        videos = []
        for result in video_results:
            meta = result.get("video_metadata", {})
            videos.append({
                "video_id": result.get("video_id"),
                "title": meta.get("title"),
                "channel_title": meta.get("channel_title"),
                "published_at": meta.get("published_at"),
                "view_count": meta.get("view_count"),
                "like_count": meta.get("like_count"),
                "comment_count": meta.get("comment_count"),
                "duration": meta.get("duration"),
                "claim_count": result.get("claim_count", 0),
                "transcript_claim_count": result.get("transcript_claim_count", 0),
                "comment_claim_count": result.get("comment_claim_count", 0)
            })
        return videos
    
    def _extract_claims(self, video_results: list[dict]) -> list[dict]:
        """Extract all claims with auto-generated IDs."""
        claims = []
        claim_id = 1
        
        for result in video_results:
            video_id = result.get("video_id")
            for claim in result.get("claims", []):
                claims.append({
                    "claim_id": claim_id,
                    "video_id": video_id,
                    "claim_text": claim.get("text"),
                    "claim_type": claim.get("type"),
                    "confidence": claim.get("confidence"),
                    "source": claim.get("source"),  # "transcript" or "comment"
                    "supporting_quote": claim.get("supporting_quote"),
                    "narrative_id": None  # To be linked later
                })
                claim_id += 1
        
        return claims
    
    def _extract_narratives(
        self, 
        synthesis: dict | None, 
        video_results: list[dict]
    ) -> list[dict]:
        """Extract narratives from synthesis in DB-ready format."""
        narratives_out = []
        
        if not synthesis:
            return narratives_out
        
        # New structure: synthesis has "narratives" array
        for narrative in synthesis.get("narratives", []):
            video_ids = narrative.get("video_ids", [])
            
            # Count claims for videos in this narrative
            claim_count = 0
            for result in video_results:
                if result.get("video_id") in video_ids:
                    claim_count += result.get("claim_count", 0)
            
            narratives_out.append({
                "narrative_id": narrative.get("id"),
                "name": narrative.get("name"),
                "summary": narrative.get("summary"),
                "video_ids": video_ids,
                "video_count": len(video_ids),
                "claim_count": claim_count
            })
        
        # Also include overall summary as a special narrative
        if synthesis.get("overall_summary"):
            narratives_out.insert(0, {
                "narrative_id": "overall",
                "name": "Overall Summary",
                "summary": synthesis.get("overall_summary"),
                "video_ids": [r.get("video_id") for r in video_results],
                "video_count": len(video_results),
                "claim_count": sum(r.get("claim_count", 0) for r in video_results)
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
        """Extract trends timeline for database."""
        timeline = []
        
        overall = trends.get("overall", {})
        for entry in overall.get("timeline", []):
            timeline.append({
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
