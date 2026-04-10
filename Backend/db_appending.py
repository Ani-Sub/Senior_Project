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


def insert_channels():

    db = SessionLocal()
    file_path = ""
    date = datetime.now()

    with open(file_path) as file:
        channels = json.load(file)

    for c in channels:
        t = text("INSERT INTO \"Channel\" (channel_id, channel_name, total_claims, flagged_claims, accuracy_rate, risk_level, risk_score, last_assessed_at) VALUES (:channel_id, :channel_name, :total_claims, :flagged_claims, :accuracy_rate, :risk_level, :risk_score, :last_assessed_at) ON CONFLICT (channel_id) DO NOTHING")
        db.execute(t, {"channel_id": c["channel_id"], "channel_name": c["channel_title"], "total_claims": 0, "flagged_claims": 0, "accuracy_rate": 0.0, "risk_level": "low", "risk_score": 0.0, "last_assessed_at": date})
    
    db.commit()


def insert_videos(board_id: str):

    db = SessionLocal()
    file_path = ""

    with open(file_path) as file:
        videos = json.load(file)

    for v in videos:
        t = text("INSERT INTO \"Video\" (video_id, board_id, channel_id, title, description, view_count, duration_seconds, published_at, processed, processed_at) VALUES (:video_id, :board_id, :channel_id, :title, :description, :view_count, :duration_seconds, :published_at, :processed, :processed_at) ON CONFLICT (video_id) DO NOTHING")
        db.execute(t, {"video_id": v["video_id"], "board_id": board_id, "channel_id": v["channel_id"], "title": v["title"], "description": v["description"], "view_count": v["view_count"], "duration_seconds": v["duration_seconds"], "published_at": datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")), "processed": v["processed"], "processed_at": datetime.fromisoformat(v["processed_at"])})
    
    db.commit()


def insert_transcripts():

    db = SessionLocal()
    file_path = ""

    with open(file_path) as file:
        transcripts = json.load(file)

    for ts in transcripts:
        t = text("INSERT INTO \"Transcript\" (transcript_id, video_id, channel_id, video_title, transcript, processed_at) VALUES (:transcript_id, :video_id, :channel_id, :video_title, :transcript, :processed_at) ON CONFLICT (video_id) DO NOTHING")
        db.execute(t, {"transcript_id": ts["transcript_id"], "video_id": ts["video_id"], "channel_id": "n/a", "video_title": "n/a", "transcript": ts["transcript"], "processed_at": datetime.fromisoformat(ts["processed_at"])})
    
    db.commit()


'''
def insert_transcript_chunks():

    db = SessionLocal()
    file_path = ""

    with open(file_path) as file:
        chunks = json.load(file)

    for c in chunks:
        t = text("INSERT INTO \"TranscriptChunk\" (chunk_id, transcript_id, chunk_text, chunk_number, processed_at) VALUES (:chunk_id, :transcript_id, :chunk_text, :chunk_number, :processed_at)")
        db.execute(t, {"chunk_id": c["chunk_id"], "transcript_id": c["transcript_id"], "chunk_text": c["chunk_text"], "chunk_number": c["chunk_number"], "processed_at": datetime.fromisoformat(c["processed_at"])})
    
    db.commit()


def insert_comments():

    db = SessionLocal()
    file_path = ""

    with open(file_path) as file:
        comments = json.load(file)

    for c in comments:
        t = text("INSERT INTO \"TranscriptChunk\" (chunk_id, transcript_id, chunk_text, chunk_number, processed_at) VALUES (:chunk_id, :transcript_id, :chunk_text, :chunk_number, :processed_at)")
        db.execute(t, {"chunk_id": c["chunk_id"], "transcript_id": c["transcript_id"], "chunk_text": c["chunk_text"], "chunk_number": c["chunk_number"], "processed_at": datetime.fromisoformat(c["processed_at"])})
    
    db.commit()
'''