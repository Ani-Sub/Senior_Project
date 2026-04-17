import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Annotated
from pathlib import Path
import json
from datetime import datetime


load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autoflush=False, bind=engine)

base = os.path.dirname(os.path.abspath(__file__))

def insert_channels():

    db = SessionLocal()
    file_path = os.path.join(base, "output", "latest", "db_ready", "channels.json")
    date = datetime.now()

    with open(file_path) as file:
        channels = json.load(file)

    for c in channels:
        t = text("INSERT INTO \"Channel\" (channel_id, channel_name, total_claims, flagged_claims, accuracy_rate, risk_level, risk_score, last_assessed_at) VALUES (:channel_id, :channel_name, :total_claims, :flagged_claims, :accuracy_rate, :risk_level, :risk_score, :last_assessed_at) ON CONFLICT (channel_id) DO NOTHING")
        db.execute(t, {"channel_id": c["channel_id"], "channel_name": c["channel_title"], "total_claims": 0, "flagged_claims": 0, "accuracy_rate": 0.0, "risk_level": "low", "risk_score": 0.0, "last_assessed_at": date})
    
    db.commit()
    db.close()


def insert_videos(board_id: str):

    db = SessionLocal()
    file_path = os.path.join(base, "output", "latest", "db_ready", "videos.json")

    with open(file_path) as file:
        videos = json.load(file)

    for v in videos:
        t = text("INSERT INTO \"Video\" (video_id, board_id, channel_id, title, description, view_count, duration_seconds, published_at, processed, processed_at) VALUES (:video_id, :board_id, :channel_id, :title, :description, :view_count, :duration_seconds, :published_at, :processed, :processed_at) ON CONFLICT (video_id) DO UPDATE SET board_id = EXCLUDED.board_id")
        db.execute(t, {"video_id": v["video_id"], "board_id": board_id, "channel_id": v["channel_id"], "title": v["title"], "description": v["description"], "view_count": v["view_count"], "duration_seconds": v["duration_seconds"], "published_at": datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")), "processed": v["processed"], "processed_at": datetime.fromisoformat(v["processed_at"])})
    
    db.commit()
    db.close()


def insert_claims():

    db = SessionLocal()
    file_path1 = os.path.join(base, "output", "latest", "db_ready", "claims.json")
    file_path2 = os.path.join(base, "output", "latest", "db_ready", "narrative_videos.json")

    with open(file_path1) as file:
        claims = json.load(file)

    with open(file_path2) as file:
        narrative_videos = json.load(file)


    narrative_videos_map = {}
    for nv in narrative_videos:
        narrative_videos_map[nv["video_id"]] = nv["narrative_id"]

    for c in claims:
        t = text("INSERT INTO \"Claim\" (video_id, narrative_id, video_title, claim_text, claim_type, confidence_score, risk_level, processed_at, is_verified, accuracy_rating) VALUES (:video_id, :narrative_id, :video_title, :claim_text, :claim_type, :confidence_score, :risk_level, :processed_at, :is_verified, :accuracy_rating)")
        db.execute(t, {"video_id": c["video_id"], "narrative_id": narrative_videos_map.get(c["video_id"]), "video_title": c["video_title"], "claim_text": c["claim_text"], "claim_type": c["claim_type"], "confidence_score": c["confidence_score"], "risk_level": c["risk_level"], "processed_at": datetime.fromisoformat(c["processed_at"]), "is_verified": c["is_verified"], "accuracy_rating": c.get("accuracy_rating")})
    
    db.commit()
    db.close()


def insert_narratives(board_id: str):

    db = SessionLocal()
    file_path = os.path.join(base, "output", "latest", "db_ready", "narratives.json")

    with open(file_path) as file:
        narratives = json.load(file)

    for n in narratives:
        t = text("INSERT INTO \"Narrative\" (narrative_id, board_id, title, summary, topic_label, claim_count, color, first_seen_at, last_seen_at) VALUES (:narrative_id, :board_id, :title, :summary, :topic_label, :claim_count, :color, :first_seen_at, :last_seen_at) ON CONFLICT (narrative_id) DO UPDATE SET board_id = EXCLUDED.board_id")
        db.execute(t, {"narrative_id": n["narrative_id"], "board_id": board_id, "title": n["title"], "summary": n.get("summary"), "topic_label": n.get("topic_label"), "claim_count": n["claim_count"], "color": n["color"], "first_seen_at": datetime.fromisoformat(n["first_seen_at"].replace("Z", "+00:00")), "last_seen_at": datetime.fromisoformat(n["last_seen_at"].replace("Z", "+00:00"))})
    
    db.commit()
    db.close()







def trend_color(direction: str):

    if direction == "rising":
        return "#00FF00"
    
    if direction == "peaking":
        return "#FFBF00"
    
    if direction == "declining":
        return "#FF0000"
    
    if direction == "stable":
        return "#808080"

def insert_trends(board_id: str):

    db = SessionLocal()
    file_path1 = os.path.join(base, "output", "latest", "db_ready", "narrative_trends.json")
    file_path2 = os.path.join(base, "output", "latest", "db_ready", "trends_timeline.json")

    with open(file_path1) as file:
        narrative_trends = json.load(file)

    with open(file_path2) as file:
        trends_timeline = json.load(file)


    labels = []
    data = []
    for tt in trends_timeline:
        labels.append(tt["period"])
        data.append(tt["claim_count"])


    #does trends exist in board
    t = text("SELECT * FROM \"Trend\" WHERE board_id = :board_id ORDER BY created_at DESC LIMIT 1")
    result = db.execute(t, {"board_id": board_id}).fetchone()


    if result:
        
        trend_id = dict(result._mapping)["trend_id"]

        #append labels if trends exist
        t = text("UPDATE \"Trend\" SET labels = labels || :new_labels WHERE trend_id = :trend_id")
        db.execute(t, {"trend_id": trend_id, "new_labels": labels})


        for n in narrative_trends:
            
            t = text("SELECT * FROM \"TrendData\" WHERE trend_id = :trend_id AND narrative_id = :narrative_id")
            result = db.execute(t, {"trend_id": trend_id, "narrative_id": n["narrative_id"]}).fetchone()

            if result:

                t = text("UPDATE \"TrendData\" SET data = data || :new_data, direction = :direction WHERE trend_id = :trend_id AND narrative_id = :narrative_id")
                db.execute(t, {"trend_id": trend_id, "narrative_id": n["narrative_id"], "new_data": data, "direction": n["pattern"]})

            else:
                
                color = trend_color(n["pattern"])
                t = text("INSERT INTO \"TrendData\" (trend_id, narrative_id, label, color, data, direction) VALUES (:trend_id, :narrative_id, :label, :color, :data, :direction)")
                db.execute(t, {"trend_id": trend_id, "narrative_id": n["narrative_id"], "label": n["name"], "color": color, "data": data, "direction": n["pattern"]})
    else:

        t = text("INSERT INTO \"Trend\" (board_id, labels) VALUES (:board_id, :labels) RETURNING *")
        trend = db.execute(t, {"board_id": board_id,"labels": labels}).fetchone()
        
        trend_id = dict(trend._mapping)["trend_id"]
        
        for n in narrative_trends:
            color = trend_color(n["pattern"])
            t = text("INSERT INTO \"TrendData\" (trend_id, narrative_id, label, color, data, direction) VALUES (:trend_id, :narrative_id, :label, :color, :data, :direction)")
            db.execute(t, {"trend_id": trend_id, "narrative_id": n["narrative_id"], "label": n["name"], "color": color, "data": data, "direction": n["pattern"]})
    
    db.commit()
    db.close()


