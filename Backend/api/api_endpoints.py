import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Annotated


load_dotenv()

#Request Bodies
class SignupBody(BaseModel):
    name: str
    email: str
    password: str

class LoginBody(BaseModel):
    email: str
    password: str

class CreateDashboardBody(BaseModel):
    name: str
    description: str | None = None
    search_terms: list[str]
    layout: str
 
class UpdateUserBody(BaseModel):
    name: str | None = None
    email: str | None = None
    current_password: str | None = None
    new_password: str | None = None


#Create app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True
)



# Database connection

engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]



#Authentication Methods
@app.post("/api/v1/auth/signup")
async def signup(body: SignupBody, db: db_dependency):
    
    initials = "".join(word[0].upper() for word in body.name.split())

    t = text("INSERT INTO \"User\" (name, email, initials, password) VALUES (:name, :email, :initials, :password) RETURNING *")
    result = db.execute(t, {"name": body.name, "email": body.email, "initials": initials, "password": body.password}).fetchone()
    db.commit()
    
    return {
        "token": "fake token",
        "user": dict(result)
    }


@app.post("/api/v1/auth/login")
async def login(body: LoginBody, db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE email = :email AND password = :password")
    result = db.execute(t, {"email": body.email, "password": body.password}).fetchone()
    
    if not result:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid Login Information"})
    return {
        "token": "fake token",
        "user": dict(result)
    }

@app.post("/api/v1/auth/logout")
async def logout():
    return {
        "Message": "Logged Out"
    }

@app.get("/api/v1/auth/me")
async def me(db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    result = db.execute(t, {"user_id": 1}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})
    return dict(result)



# dashboard methods                                                WIP
@app.get("/api/v1/dashboards")
def get_dashboards(db: db_dependency):
    
    t = text("SELECT * FROM \"Board\" WHERE user_id = :user_id")
    dashboards = db.execute(t, {"user_id": 1}).fetchall()
    
    result = []
    for board in dashboards:
        tempBoard = dict(board)
        t = text("SELECT keyword FROM \"Keyword\" WHERE board_id = :board_id")
        keywords = db.execute(t, {"board_id": tempBoard["board_id"]}).fetchall()

        tempBoard["keywords"] = [row["keyword"] for row in keywords]
        result.append(tempBoard)
    
    return result




@app.post("/api/v1/dashboards")
def create_dashboard(body: CreateDashboardBody, db: db_dependency):
    return {
        "dashboard_id": "dashboard-id 2",
        "user_id": "user 1",
        "name": "Dashboard 2",
        "description": "Second dashboard",
        "search_terms": ["Dashboard", "Size"],
        "layout": "trends",
        "created_at": "2025-01-01T00:00:00Z"
    }
 
@app.get("/api/v1/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str):
    return {
        "dashboard_id": "dashboard-id 1",
        "user_id": "user 1",
        "name": "AI Trends",
        "description": "Tracking AI on YouTube",
        "search_terms": ["artificial intelligence", "LLM"],
        "layout": "overview",
        "created_at": "2025-01-01T00:00:00Z"
    }
 
@app.delete("/api/v1/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str):
    return {"Message": "Dashboard deleted"}
 

@app.get("/api/v1/dashboards/{dashboard_id}/claims")
def get_claims(dashboard_id: str):
    return {
        "page": 1,
        "limit": 20,
        "total": 1,
        "claims": [
            {
                "claim_id": "claim-id 1",
                "video_id": "video-id 1",
                "channel_id": "channel-id 1",
                "channel_name": "Technology channel",
                "claim_text": "Some claim",
                "claim_type": "factual",
                "confidence_score": 0.87,
                "risk_level": "medium",
                "narrative_id": "narritive-id 1",
                "narrative_name": "AI Technology name",
                "published_at": "2025-03-01T00:00:00Z",
                "is_verified": False,
                "accuracy_rating": None
            }
        ]
    }
 
@app.get("/api/v1/claims/{claim_id}")
def get_claim(claim_id: str):
    return {
        "claim_id": "claim-id 1",
            "video_id": "video-id 1",
            "channel_id": "channel-id 1",
            "channel_name": "Technology channel",
            "claim_text": "Some claim",
            "claim_type": "factual",
            "confidence_score": 0.87,
            "risk_level": "medium",
            "narrative_id": "narritive-id 1",
            "narrative_name": "AI Technology name",
            "published_at": "2025-03-01T00:00:00Z",
            "is_verified": False,
            "accuracy_rating": None
    }


@app.get("/api/v1/dashboards/{dashboard_id}/narratives")
def get_narratives(dashboard_id: str):
    return [
        {
            "narrative_id": "narritive-id 1",
            "title": "AI Replacing Developers",
            "summary": "Some Summary",
            "topic_label": "Artificial Intelligence",
            "claim_count": 42,
            "color": "#00d4ff",
            "first_seen_at": "2025-01-10T00:00:00Z",
            "last_seen_at": "2025-03-10T00:00:00Z"
        }
    ]
 
@app.get("/api/v1/narratives/{narrative_id}")
def get_narrative(narrative_id: str):
    return {
        "narrative_id": "narritive-id 1",
        "title": "AI Replacing Developers",
        "summary": "Some Summary",
        "topic_label": "Artificial Intelligence",
        "claim_count": 42,
        "color": "#00d4ff",
        "first_seen_at": "2025-01-10T00:00:00Z",
        "last_seen_at": "2025-03-10T00:00:00Z",
        "claims": ["some claim"]
    }


@app.get("/api/v1/dashboards/{dashboard_id}/trends")
def get_trends(dashboard_id: str, range: str = "3m"):
    return {
        "labels": ["Jan W1", "Jan W2", "Jan W3", "Jan W4", "Feb W1", "Feb W2", "Feb W3", "Feb W4", "Mar W1", "Mar W2", "Mar W3", "Mar W4"],
        "datasets": [
            {
                "narrative_id": "narritive-id 1",
                "label": "AI Replacing Developers",
                "color": "#00d4ff",
                "data": [2, 4, 5, 6, 8, 10],
                "direction": "rising"
            }
        ]
    }


@app.get("/api/v1/dashboards/{dashboard_id}/creators")
def get_creators(dashboard_id: str):
    return [
        {
            "channel_id": "channel-id 1",
            "channel_name": "Technology channel",
            "total_claims": 38,
            "flagged_claims": 12,
            "accuracy_rate": 0.68,
            "risk_level": "medium",
            "risk_score": 5.4,
            "last_assessed_at": "2025-03-10T00:00:00Z"
        }
    ]
 
@app.get("/api/v1/creators/{channel_id}/risk")
def get_creator_risk(channel_id: str):
    return {
        "channel_id": "channel-id 1",
        "channel_name": "Technology channel",
        "total_claims": 38,
        "flagged_claims": 12,
        "accuracy_rate": 0.68,
        "risk_level": "medium",
        "risk_score": 5.4,
        "last_assessed_at": "2025-03-10T00:00:00Z"
    }






@app.get("/api/v1/users/me")
def get_user():
    return {
        "user_id": "user 1",
        "name": "Test User",
        "email": "Test Email",
        "initials": "TN",
        "plan": "free",
        "role": "user",
        "created_at": "2025-01-01T00:00:00Z"
    }
 
@app.patch("/api/v1/users/me")
def update_user(body: UpdateUserBody):
    return {
        "user_id": "user 1",
        "name": "Test Name" or "Temp Name",
        "email": "Test Email" or "Temp Email",
        "initials": "TN",
        "plan": "free",
        "role": "user",
        "created_at": "2025-01-01T00:00:00Z"
    }
 
@app.get("/api/v1/users/me/plan")
def get_plan():
    return {
        "plan": "free",
        "plan_name": "Free Plan",
        "dashboard_limit": 1,
        "dashboards_used": 1
    }