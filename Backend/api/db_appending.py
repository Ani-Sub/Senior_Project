import os
import json
from datetime import datetime
import uuid
from sqlalchemy import text

from database import SessionLocal

base = os.path.dirname(os.path.abspath(__file__))


# ── Private helpers (each accepts an open session — no commit/close) ──────────

def _insert_channels(db, board_id: str):
    file_path = os.path.join(base, "output", "latest", "db_ready", "channels.json")
    date = datetime.now()

    with open(file_path) as f:
        channels = json.load(f)

    for c in channels:
        db.execute(
            text('INSERT INTO "Channel" (channel_id, channel_name, total_claims, flagged_claims, '
                 'accuracy_rate, risk_level, risk_score, last_assessed_at) '
                 'VALUES (:channel_id, :channel_name, :total_claims, :flagged_claims, '
                 ':accuracy_rate, :risk_level, :risk_score, :last_assessed_at) '
                 'ON CONFLICT (channel_id) DO UPDATE SET '
                 'total_claims = EXCLUDED.total_claims, '
                 'flagged_claims = EXCLUDED.flagged_claims, '
                 'accuracy_rate = EXCLUDED.accuracy_rate, '
                 'risk_level = EXCLUDED.risk_level, '
                 'risk_score = EXCLUDED.risk_score, '
                 'last_assessed_at = EXCLUDED.last_assessed_at'),
            {"channel_id": c["channel_id"], "channel_name": c["channel_name"],
             "total_claims": c.get("total_claims", 0),
             "flagged_claims": c.get("flagged_claims", 0),
             "accuracy_rate": c.get("accuracy_rate", 0.0),
             "risk_level": c.get("risk_level", "low"),
             "risk_score": c.get("risk_score", 0.0),
             "last_assessed_at": date}
        )
        db.execute(
            text('INSERT INTO "BoardChannel" (board_id, channel_id) '
                 'VALUES (:board_id, :channel_id) '
                 'ON CONFLICT (board_id, channel_id) DO NOTHING'),
            {"board_id": board_id, "channel_id": c["channel_id"]}
        )


def _insert_videos(db, board_id: str):
    file_path = os.path.join(base, "output", "latest", "db_ready", "videos.json")

    with open(file_path) as f:
        videos = json.load(f)

    for v in videos:
        db.execute(
            text('INSERT INTO "Video" (video_id, board_id, channel_id, title, description, '
                 'view_count, duration_seconds, published_at, processed, processed_at) '
                 'VALUES (:video_id, :board_id, :channel_id, :title, :description, '
                 ':view_count, :duration_seconds, :published_at, :processed, :processed_at) '
                 'ON CONFLICT (video_id) DO UPDATE SET board_id = EXCLUDED.board_id'),
            {"video_id": v["video_id"], "board_id": board_id, "channel_id": v["channel_id"],
             "title": v["title"], "description": v["description"],
             "view_count": v["view_count"], "duration_seconds": v["duration_seconds"],
             "published_at": datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")),
             "processed": v["processed"],
             "processed_at": datetime.fromisoformat(v["processed_at"])}
        )


def _insert_narratives(db, board_id: str) -> dict:
    file_path = os.path.join(base, "output", "latest", "db_ready", "narratives.json")

    with open(file_path) as f:
        narratives = json.load(f)

    id_map = {}

    for n in narratives:
        new_claims = n["claim_count"]

        last_seen_raw = n.get("last_seen_at")
        last_seen = (datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
                     if last_seen_raw else datetime.now())
        first_seen_raw = n.get("first_seen_at")
        first_seen = (datetime.fromisoformat(first_seen_raw.replace("Z", "+00:00"))
                      if first_seen_raw else datetime.now())

        existing = db.execute(
            text('SELECT narrative_id FROM "Narrative" WHERE board_id = :board_id AND title = :title'),
            {"board_id": board_id, "title": n["title"]}
        ).fetchone()

        if existing:
            db_id = dict(existing._mapping)["narrative_id"]
            db.execute(
                text('UPDATE "Narrative" SET claim_count = claim_count + :new_claims, '
                     'last_seen_at = :last_seen_at, summary = :summary '
                     'WHERE narrative_id = :narrative_id'),
                {"narrative_id": db_id, "new_claims": new_claims,
                 "last_seen_at": last_seen, "summary": n.get("summary")}
            )
        else:
            db_id = str(uuid.uuid4())
            db.execute(
                text('INSERT INTO "Narrative" (narrative_id, board_id, title, summary, topic_label, '
                     'claim_count, color, first_seen_at, last_seen_at) '
                     'VALUES (:narrative_id, :board_id, :title, :summary, :topic_label, '
                     ':claim_count, :color, :first_seen_at, :last_seen_at)'),
                {"narrative_id": db_id, "board_id": board_id, "title": n["title"],
                 "summary": n.get("summary"), "topic_label": n.get("topic_label"),
                 "claim_count": new_claims, "color": n["color"],
                 "first_seen_at": first_seen, "last_seen_at": last_seen}
            )

        id_map[n["narrative_id"]] = db_id

    return id_map


def _insert_claims(db, id_map: dict):
    file_path1 = os.path.join(base, "output", "latest", "db_ready", "claims.json")
    file_path2 = os.path.join(base, "output", "latest", "db_ready", "narrative_videos.json")

    with open(file_path1) as f:
        claims = json.load(f)
    with open(file_path2) as f:
        narrative_videos = json.load(f)

    narrative_videos_map = {nv["video_id"]: nv["narrative_id"] for nv in narrative_videos}

    CLAIM_TYPE_MAP = {
        "factual": "factual",
        "opinion": "opinion",
        "prediction": "opinion",
        "statistic": "factual",
    }
    
    for c in claims:
        llm_narrative_id = narrative_videos_map.get(c["video_id"])
        db_narrative_id = id_map.get(llm_narrative_id)

        db.execute(
            text('INSERT INTO "Claim" (video_id, narrative_id, video_title, claim_text, claim_type, '
                 'confidence_score, risk_level, processed_at, is_verified, accuracy_rating) '
                 'VALUES (:video_id, :narrative_id, :video_title, :claim_text, :claim_type, '
                 ':confidence_score, :risk_level, :processed_at, :is_verified, :accuracy_rating) '
                 'ON CONFLICT DO NOTHING'),
            {"video_id": c["video_id"], "narrative_id": db_narrative_id,
             "video_title": c["video_title"], "claim_text": c["claim_text"],
             "claim_type": CLAIM_TYPE_MAP.get(c["claim_type"], "factual"), "confidence_score": c["confidence_score"],
             "risk_level": c["risk_level"],
             "processed_at": datetime.fromisoformat(c["processed_at"]),
             "is_verified": c["is_verified"], "accuracy_rating": c.get("accuracy_rating")}
        )


def _trend_color(direction: str) -> str:
    return {
        "rising": "#00FF00",
        "peaking": "#FFBF00",
        "declining": "#FF0000",
        "stable": "#808080",
    }.get(direction or "", "#808080")


def _insert_trends(db, board_id: str, id_map: dict):
    file_path1 = os.path.join(base, "output", "latest", "db_ready", "narrative_trends.json")
    file_path2 = os.path.join(base, "output", "latest", "db_ready", "trends_timeline.json")

    with open(file_path1) as f:
        narrative_trends = json.load(f)
    with open(file_path2) as f:
        trends_timeline = json.load(f)

    seen: set = set()
    labels = []
    for tt in trends_timeline:
        if tt["period"] not in seen:
            labels.append(tt["period"])
            seen.add(tt["period"])

    existing_trend = db.execute(
        text('SELECT * FROM "Trend" WHERE board_id = :board_id ORDER BY created_at DESC LIMIT 1'),
        {"board_id": board_id}
    ).fetchone()

    if existing_trend:
        trend_id = dict(existing_trend._mapping)["trend_id"]

        existing_labels_row = db.execute(
            text('SELECT labels FROM "Trend" WHERE trend_id = :trend_id'),
            {"trend_id": trend_id}
        ).fetchone()
        existing_labels: list = dict(existing_labels_row._mapping)["labels"] or []
        existing_labels_set = set(existing_labels)

        new_labels = [l for l in labels if l not in existing_labels_set]
        if new_labels:
            db.execute(
                text('UPDATE "Trend" SET labels = labels || :new_labels WHERE trend_id = :trend_id'),
                {"trend_id": trend_id, "new_labels": new_labels}
            )

        for n in narrative_trends:
            db_narrative_id = id_map.get(n["narrative_id"])
            data = [tt["claim_count"] for tt in trends_timeline
                    if tt["narrative_id"] == n["narrative_id"]]

            existing_dataset = db.execute(
                text('SELECT * FROM "TrendData" WHERE trend_id = :trend_id AND narrative_id = :narrative_id'),
                {"trend_id": trend_id, "narrative_id": db_narrative_id}
            ).fetchone()

            if existing_dataset:
                # Align by period label so re-runs with different windows don't corrupt the array
                new_data = [count for period, count in zip(labels, data)
                            if period not in existing_labels_set]
                if new_data:
                    db.execute(
                        text('UPDATE "TrendData" SET data = data || :new_data, direction = :direction '
                             'WHERE trend_id = :trend_id AND narrative_id = :narrative_id'),
                        {"trend_id": trend_id, "narrative_id": db_narrative_id,
                         "new_data": new_data, "direction": n["pattern"]}
                    )
            else:
                db.execute(
                    text('INSERT INTO "TrendData" (trend_id, narrative_id, label, color, data, direction) '
                         'VALUES (:trend_id, :narrative_id, :label, :color, :data, :direction) '
                         'ON CONFLICT (trend_id, narrative_id) DO NOTHING'),
                    {"trend_id": trend_id, "narrative_id": db_narrative_id,
                     "label": n["name"], "color": _trend_color(n["pattern"]),
                     "data": data, "direction": n["pattern"]}
                )
    else:
        new_trend = db.execute(
            text('INSERT INTO "Trend" (board_id, labels) VALUES (:board_id, :labels) RETURNING *'),
            {"board_id": board_id, "labels": labels}
        ).fetchone()
        trend_id = dict(new_trend._mapping)["trend_id"]

        for n in narrative_trends:
            db_narrative_id = id_map.get(n["narrative_id"])
            data = [tt["claim_count"] for tt in trends_timeline
                    if tt["narrative_id"] == n["narrative_id"]]
            db.execute(
                text('INSERT INTO "TrendData" (trend_id, narrative_id, label, color, data, direction) '
                     'VALUES (:trend_id, :narrative_id, :label, :color, :data, :direction) '
                     'ON CONFLICT (trend_id, narrative_id) DO NOTHING'),
                {"trend_id": trend_id, "narrative_id": db_narrative_id,
                 "label": n["name"], "color": _trend_color(n["pattern"]),
                 "data": data, "direction": n["pattern"]}
            )


# ── Public entry points ───────────────────────────────────────────────────────

def import_channels_and_videos(board_id: str):
    """
    Phase 1: always-safe import of channels and videos.
    Runs unconditionally — commits even when synthesis failed.
    """
    db = SessionLocal()
    try:
        _insert_channels(db, board_id)
        _insert_videos(db, board_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def import_narrative_data(board_id: str):
    """
    Phase 2: narratives, claims, and trends.
    Only call this when synthesis succeeded and id_map is populated.
    """
    db = SessionLocal()
    try:
        id_map = _insert_narratives(db, board_id)
        _insert_claims(db, id_map)
        _insert_trends(db, board_id, id_map)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def import_pipeline_data(board_id: str):
    """
    Full import used by the dashboard creation API endpoint.
    All steps in one transaction — either everything commits or everything rolls back.
    """
    db = SessionLocal()
    try:
        _insert_channels(db, board_id)
        _insert_videos(db, board_id)
        id_map = _insert_narratives(db, board_id)
        _insert_claims(db, id_map)
        _insert_trends(db, board_id, id_map)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
