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

    # check to see if email already exists in db

    t = text("INSERT INTO \"User\" (name, email, initials, password) VALUES (:name, :email, :initials, :password) RETURNING *")
    result = db.execute(t, {"name": body.name, "email": body.email, "initials": initials, "password": body.password}).fetchone()
    db.commit()
    
    return {
        "token": "fake token",
        "user": dict(result._mapping)
    }


@app.post("/api/v1/auth/login")
async def login(body: LoginBody, db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE email = :email AND password = :password")
    result = db.execute(t, {"email": body.email, "password": body.password}).fetchone()
    
    if not result:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid Login Information"})
    return {
        "token": "fake token",
        "user": dict(result._mapping)
    }

@app.post("/api/v1/auth/logout")
async def logout():
    return {
        "message": "Logged Out"
    }

@app.get("/api/v1/auth/me")
async def me(db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    result = db.execute(t, {"user_id": 1}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})
    return dict(result._mapping)



# dashboard methods                               
@app.get("/api/v1/dashboards")
def get_dashboards(db: db_dependency):
    
    t = text("SELECT * FROM \"Board\" WHERE user_id = :user_id")
    dashboards = db.execute(t, {"user_id": 1}).fetchall()
    
    result = []
    for board in dashboards:
        tempBoard = dict(board._mapping)
        result.append(tempBoard)
    
    return result




@app.post("/api/v1/dashboards")
def create_dashboard(body: CreateDashboardBody, db: db_dependency):
    
    t = text("INSERT INTO \"Board\" (user_id, board_name, description, search_terms, layout, last_updated_at) VALUES (:user_id, :board_name, :description, :search_terms, :layout, NOW()) RETURNING *")
    result = db.execute(t, {"user_id": 1, "board_name": body.name, "description": body.description, "search_terms": body.search_terms, "layout": body.layout}).fetchone()
    db.commit()

    return dict(result._mapping)
 
@app.get("/api/v1/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str, db: db_dependency):
    
    t = text("SELECT * FROM \"Board\" WHERE board_id = :board_id")
    result = db.execute(t, {"board_id": dashboard_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Dashboard not found"})
    
    return dict(result._mapping)
 
@app.delete("/api/v1/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str, db: db_dependency):
    
    t = text("DELETE FROM \"Board\" WHERE board_id = :board_id")
    result = db.execute(t, {"board_id": dashboard_id})
    db.commit()
    
    return {"message": "Dashboard deleted"}
 

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
def get_claim(claim_id: str, db: db_dependency):
    
    t = text("SELECT c.claim_id AS claim_id, c.video_id AS video_id, ch.channel_id AS channel_id, ch.channel_name AS channel_name, c.claim_text AS claim_text, c.claim_type AS claim_type, c.confidence_score AS confidence_score, c.risk_level AS risk_level, n.narrative_id AS narrative_id, n.title AS narrative_name, c.processed_at AS published_at, c.is_verified AS is_verified, c.accuracy_rating AS accuracy_rating FROM \"Claim\" c JOIN \"Video\" v ON c.video_id = v.video_id JOIN \"Channel\" ch ON v.channel_id = ch.channel_id LEFT JOIN \"Narrative\" n ON c.narrative_id = n.narrative_id WHERE c.claim_id = :claim_id")
    result = db.execute(t, {"claim_id": claim_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Claim not found"})
    

    return dict(result._mapping)


@app.get("/api/v1/dashboards/{dashboard_id}/narratives")
def get_narratives(dashboard_id: str, db: db_dependency):
    
    t = text("SELECT * FROM \"Narrative\" WHERE board_id = :board_id")
    narratives = db.execute(t, {"board_id": dashboard_id}).fetchall()
    
    result = []
    for narrative in narratives:
        tempNarrative = dict(narrative._mapping)
        result.append(tempNarrative)
    
    return result
    
 
@app.get("/api/v1/narratives/{narrative_id}")
def get_narrative(narrative_id: str, db: db_dependency):
    
    t = text("SELECT * FROM \"Narrative\" WHERE narrative_id = :narrative_id")
    narrative = db.execute(t, {"narrative_id": narrative_id}).fetchone()

    if not narrative:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Narrative not found"})
    
    t = text("SELECT * FROM \"Claim\" WHERE narrative_id = :narrative_id")
    claims = db.execute(t, {"narrative_id": narrative_id}).fetchall()


    result = dict(narrative._mapping)
    result["claims"] = []
    for claim in claims:
        tempClaim = dict(claim._mapping)
        result["claims"].append(tempClaim)

    return result



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
def get_creators(dashboard_id: str, db: db_dependency):
    
    t = text("SELECT * FROM \"Channel\" c JOIN \"BoardChannel\" bc ON bc.channel_id = c.channel_id WHERE bc.board_id = :board_id")
    channels = db.execute(t, {"board_id": dashboard_id}).fetchall()
    
    result = []
    for channel in channels:
        tempChannel = dict(channel._mapping)
        result.append(tempChannel)
    
    return result
    
 
@app.get("/api/v1/creators/{channel_id}/risk")
def get_creator_risk(channel_id: str, db: db_dependency):
    
    t = text("SELECT * FROM \"Channel\" WHERE channel_id = :channel_id")
    result = db.execute(t, {"channel_id": channel_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Creator not found"})

    return dict(result._mapping)






@app.get("/api/v1/users/me")
def get_user(db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    result = db.execute(t, {"user_id": 1}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})
    
    return dict(result._mapping)



# mark
@app.patch("/api/v1/users/me")
def update_user(body: UpdateUserBody, db: db_dependency):
    
    t = text("SELECT password FROM \"User\" WHERE user_id = :user_id")
    password = db.execute(t, {"user_id": 1}).fetchone()

    if body.name is None:
        newInitials = None
    else:
        newInitials = "".join(word[0].upper() for word in body.name.split())


    if body.current_password == dict(password._mapping)["password"] and body.new_password:

        t = text("UPDATE \"User\" SET name = COALESCE(:name, name), email = COALESCE(:email, email), initials = COALESCE(:initials, initials), password = :password WHERE user_id = :user_id RETURNING *")
        result = db.execute(t, {"user_id": 1, "name": body.name, "email": body.email, "initials": newInitials, "password": body.new_password}).fetchone()

    else:

        t = text("UPDATE \"User\" SET name = COALESCE(:name, name), email = COALESCE(:email, email), initials = COALESCE(:initials, initials) WHERE user_id = :user_id RETURNING *")
        result = db.execute(t, {"user_id": 1, "name": body.name, "email": body.email, "initials": newInitials}).fetchone()

    db.commit()

    return dict(result._mapping)
    


 
@app.get("/api/v1/users/me/plan")
def get_plan(db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    userProfile = db.execute(t, {"user_id": 1}).fetchone()
    userProfile = dict(userProfile._mapping)

    t = text("SELECT COUNT(*) AS num FROM \"Board\" WHERE user_id = :user_id")
    numDashboards = db.execute(t, {"user_id": 1}).fetchone()
    numDashboards = dict(numDashboards._mapping)["num"]
    
        
    plan_names = {"free": "Free Plan", "analyst": "Analyst Plan", "enterprise": "Enterprise Plan"}
    plan_limits = {"free": 1, "analyst": 100, "enterprise": 9999}      
    
    return {
        "plan": userProfile["plan"],
        "plan_name": plan_names[userProfile["plan"]],
        "dashboard_limit": plan_limits[userProfile["plan"]],
        "dashboards_used": numDashboards
    }






# change create dashboard to make sure that if a user cannot make more boards an error pops up
# change delete dashboard to update number of dashboards left for user
# implement get claims and trends query