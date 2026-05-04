import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Annotated
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from fastapi import Header, status
from fastapi.security import OAuth2PasswordBearer
from db_appending import import_pipeline_data

load_dotenv()

from database import SessionLocal

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise EnvironmentError("SECRET_KEY not set. This is required for JWT signing.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def create_access_token(user_id: str):
    
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid token"})
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid token"})


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
    plan: str | None = None


#Create app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://senior-project-pied-five.vercel.app"],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True
)



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

    existing = db.execute(text("SELECT user_id FROM \"User\" WHERE email = :email"), {"email": body.email}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": "Email already registered"})

    t = text("INSERT INTO \"User\" (name, email, initials, password) VALUES (:name, :email, :initials, :password) RETURNING *")
    result = db.execute(t, {"name": body.name, "email": body.email, "initials": initials, "password": body.password}).fetchone()
    db.commit()
    
    return {
        "token": create_access_token(dict(result._mapping)["user_id"]),
        "user": dict(result._mapping)
    }


@app.post("/api/v1/auth/login")
async def login(body: LoginBody, db: db_dependency):
    
    t = text("SELECT * FROM \"User\" WHERE email = :email AND password = :password")
    result = db.execute(t, {"email": body.email, "password": body.password}).fetchone()
    
    if not result:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid Login Information"})
    return {
        "token": create_access_token(dict(result._mapping)["user_id"]),
        "user": dict(result._mapping)
    }

@app.post("/api/v1/auth/logout")
async def logout():
    return {
        "message": "Logged Out"
    }

@app.get("/api/v1/auth/me")
async def me(db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    result = db.execute(t, {"user_id": user_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})
    return dict(result._mapping)



# dashboard methods                               
@app.get("/api/v1/dashboards")
def get_dashboards(db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"Board\" WHERE user_id = :user_id")
    dashboards = db.execute(t, {"user_id": user_id}).fetchall()
    
    result = []
    for board in dashboards:
        tempBoard = dict(board._mapping)
        result.append(tempBoard)
    
    return result




@app.post("/api/v1/dashboards")
def create_dashboard(body: CreateDashboardBody, db: db_dependency, user_id: str = Depends(get_current_user)):

    plan_limits = {"free": 1, "analyst": 5, "enterprise": None}

    user = db.execute(text("SELECT plan FROM \"User\" WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})

    user_plan = dict(user._mapping)["plan"]
    limit = plan_limits.get(user_plan, 1)

    if limit is not None:
        count = db.execute(text("SELECT COUNT(*) FROM \"Board\" WHERE user_id = :user_id"), {"user_id": user_id}).scalar()
        if count >= limit:
            raise HTTPException(status_code=403, detail={"error": "plan_limit", "message": f"Your {user_plan} plan allows {limit} dashboard(s). Upgrade to create more."})

    t = text("INSERT INTO \"Board\" (user_id, board_name, description, search_terms, layout, last_updated_at) VALUES (:user_id, :board_name, :description, :search_terms, :layout, NOW()) RETURNING *")
    result = db.execute(t, {"user_id": user_id, "board_name": body.name, "description": body.description, "search_terms": body.search_terms, "layout": body.layout}).fetchone()
    db.commit()

    board = dict(result._mapping)

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "latest", "db_ready", "channels.json")
    if not os.path.exists(output_path):
        return board

    try:
        import_pipeline_data(board["board_id"])
    except Exception as e:
        print(f"[ERROR] Pipeline import failed for board {board['board_id']}: {e}")

    return board
 
@app.get("/api/v1/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str, db: db_dependency, user_id: str = Depends(get_current_user)):

    t = text("SELECT * FROM \"Board\" WHERE board_id = :board_id AND user_id = :user_id")
    result = db.execute(t, {"board_id": dashboard_id, "user_id": user_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Dashboard not found"})

    return dict(result._mapping)

@app.delete("/api/v1/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str, db: db_dependency, user_id: str = Depends(get_current_user)):

    t = text("DELETE FROM \"Board\" WHERE board_id = :board_id AND user_id = :user_id")
    result = db.execute(t, {"board_id": dashboard_id, "user_id": user_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Dashboard not found"})

    return {"message": "Dashboard deleted"}
 

@app.get("/api/v1/dashboards/{dashboard_id}/claims")
def get_claims(dashboard_id: str, db: db_dependency, user_id: str = Depends(get_current_user), page: int = 1, limit: int = 20, claim_type: str = None, risk: str = None, narrative: str = None, channel: str = None, search: str = None):

    if limit > 100:
        limit = 100

    offset = (page - 1) * limit
    where_clause = "WHERE v.board_id = :board_id"
    parameters = {"board_id": dashboard_id, "limit": limit, "offset": offset}

    if claim_type:
        where_clause += " AND c.claim_type = :claim_type"
        parameters["claim_type"] = claim_type
    if risk:
        where_clause += " AND c.risk_level = :risk"
        parameters["risk"] = risk
    if narrative:
        where_clause += " AND c.narrative_id = :narrative"
        parameters["narrative"] = narrative
    if channel:
        where_clause += " AND ch.channel_id = :channel"
        parameters["channel"] = channel
    if search:
        where_clause += " AND c.claim_text ILIKE :search"
        parameters["search"] = f"%{search}%"

    t = text(f"SELECT c.claim_id AS claim_id, c.video_id AS video_id, ch.channel_id AS channel_id, ch.channel_name AS channel_name, c.claim_text AS claim_text, c.claim_type AS claim_type, c.confidence_score AS confidence_score, c.risk_level AS risk_level, n.narrative_id AS narrative_id, n.title AS narrative_name, c.processed_at AS published_at, c.is_verified AS is_verified, c.accuracy_rating AS accuracy_rating FROM \"Claim\" c JOIN \"Video\" v ON c.video_id = v.video_id JOIN \"Channel\" ch ON v.channel_id = ch.channel_id LEFT JOIN \"Narrative\" n ON c.narrative_id = n.narrative_id {where_clause} LIMIT :limit OFFSET :offset")
    result = db.execute(t, parameters).fetchall()

    claims = []
    for claim in result:
        c = dict(claim._mapping)
        claims.append(c)

    count_params = {k: v for k, v in parameters.items() if k not in ("limit", "offset")}
    t = text(f"SELECT COUNT(*) FROM \"Claim\" c JOIN \"Video\" v ON c.video_id = v.video_id JOIN \"Channel\" ch ON v.channel_id = ch.channel_id {where_clause}")
    total = db.execute(t, count_params).scalar()
    
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "claims": claims
    }
 
@app.get("/api/v1/claims/{claim_id}")
def get_claim(claim_id: str, db: db_dependency, _user_id: str = Depends(get_current_user)):
    
    t = text("SELECT c.claim_id AS claim_id, c.video_id AS video_id, ch.channel_id AS channel_id, ch.channel_name AS channel_name, c.claim_text AS claim_text, c.claim_type AS claim_type, c.confidence_score AS confidence_score, c.risk_level AS risk_level, n.narrative_id AS narrative_id, n.title AS narrative_name, c.processed_at AS published_at, c.is_verified AS is_verified, c.accuracy_rating AS accuracy_rating FROM \"Claim\" c JOIN \"Video\" v ON c.video_id = v.video_id JOIN \"Channel\" ch ON v.channel_id = ch.channel_id LEFT JOIN \"Narrative\" n ON c.narrative_id = n.narrative_id WHERE c.claim_id = :claim_id")
    result = db.execute(t, {"claim_id": claim_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Claim not found"})
    

    return dict(result._mapping)


@app.get("/api/v1/dashboards/{dashboard_id}/narratives")
def get_narratives(dashboard_id: str, db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"Narrative\" WHERE board_id = :board_id")
    narratives = db.execute(t, {"board_id": dashboard_id}).fetchall()
    
    result = []
    for narrative in narratives:
        tempNarrative = dict(narrative._mapping)
        result.append(tempNarrative)
    
    return result
    
 
@app.get("/api/v1/narratives/{narrative_id}")
def get_narrative(narrative_id: str, db: db_dependency, _user_id: str = Depends(get_current_user)):
    
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
def get_trends(dashboard_id: str, db: db_dependency, user_id: str = Depends(get_current_user), range: str = "3m"):

    range_to_periods = {"2w": 2, "1m": 4, "3m": 13, "6m": 26, "1y": 52}
    max_periods = range_to_periods.get(range)  # None = "all", no slicing

    t = text("SELECT * FROM \"Trend\" WHERE board_id = :board_id ORDER BY created_at DESC LIMIT 1")
    trends = db.execute(t, {"board_id": dashboard_id}).fetchall()

    result = []
    for trend in trends:
        tempTrend = dict(trend._mapping)
        labels = tempTrend["labels"] or []
        if max_periods is not None:
            labels = labels[-max_periods:]

        t = text("SELECT * FROM \"TrendData\" WHERE trend_id = :trend_id")
        datasets = db.execute(t, {"trend_id": tempTrend["trend_id"]}).fetchall()

        data = []
        for dataset in datasets:
            tempDataset = dict(dataset._mapping)
            if max_periods is not None and tempDataset.get("data"):
                tempDataset["data"] = tempDataset["data"][-max_periods:]
            data.append(tempDataset)

        result.append({"labels": labels, "datasets": data})

    return result



@app.get("/api/v1/dashboards/{dashboard_id}/creators")
def get_creators(dashboard_id: str, db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"Channel\" c JOIN \"BoardChannel\" bc ON bc.channel_id = c.channel_id WHERE bc.board_id = :board_id")
    channels = db.execute(t, {"board_id": dashboard_id}).fetchall()
    
    result = []
    for channel in channels:
        tempChannel = dict(channel._mapping)
        result.append(tempChannel)
    
    return result
    
 
@app.get("/api/v1/creators/{channel_id}/risk")
def get_creator_risk(channel_id: str, db: db_dependency, _user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"Channel\" WHERE channel_id = :channel_id")
    result = db.execute(t, {"channel_id": channel_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Creator not found"})

    return dict(result._mapping)






@app.get("/api/v1/users/me")
def get_user(db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    result = db.execute(t, {"user_id": user_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})
    
    return dict(result._mapping)



# mark
@app.patch("/api/v1/users/me")
def update_user(body: UpdateUserBody, db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT password FROM \"User\" WHERE user_id = :user_id")
    password = db.execute(t, {"user_id": user_id}).fetchone()

    if not password:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "User not found"})

    if body.name is None:
        newInitials = None
    else:
        newInitials = "".join(word[0].upper() for word in body.name.split())

    stored_password = dict(password._mapping)["password"]

    if body.new_password:
        if not body.current_password:
            raise HTTPException(status_code=400, detail={"error": "bad_request", "message": "current_password required to set a new password"})
        if body.current_password != stored_password:
            raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Current password is incorrect"})
        t = text("UPDATE \"User\" SET name = COALESCE(:name, name), email = COALESCE(:email, email), initials = COALESCE(:initials, initials), password = :password, plan = COALESCE(:plan, plan) WHERE user_id = :user_id RETURNING *")
        result = db.execute(t, {"user_id": user_id, "name": body.name, "email": body.email, "initials": newInitials, "password": body.new_password, "plan": body.plan}).fetchone()
    else:
        t = text("UPDATE \"User\" SET name = COALESCE(:name, name), email = COALESCE(:email, email), initials = COALESCE(:initials, initials), plan = COALESCE(:plan, plan) WHERE user_id = :user_id RETURNING *")
        result = db.execute(t, {"user_id": user_id, "name": body.name, "email": body.email, "initials": newInitials, "plan": body.plan}).fetchone()

    db.commit()

    return dict(result._mapping)
    


 
@app.get("/api/v1/users/me/plan")
def get_plan(db: db_dependency, user_id: str = Depends(get_current_user)):
    
    t = text("SELECT * FROM \"User\" WHERE user_id = :user_id")
    userProfile = db.execute(t, {"user_id": user_id}).fetchone()
    userProfile = dict(userProfile._mapping)

    t = text("SELECT COUNT(*) AS num FROM \"Board\" WHERE user_id = :user_id")
    numDashboards = db.execute(t, {"user_id": user_id}).fetchone()
    numDashboards = dict(numDashboards._mapping)["num"]
    
        
    plan_names = {"free": "Free Plan", "analyst": "Analyst Plan", "enterprise": "Enterprise Plan"}
    plan_limits = {"free": 1, "analyst": 5, "enterprise": None}
    plan_key = userProfile["plan"]

    return {
        "plan": plan_key,
        "plan_name": plan_names.get(plan_key, "Free Plan"),
        "dashboard_limit": plan_limits.get(plan_key, 1),
        "dashboards_used": numDashboards
    }




@app.post("/api/v1/dashboards/{dashboard_id}/run")
def run_endpoint(db: db_dependency, dashboard_id: str, user_id: str = Depends(get_current_user)):
    t = text("SELECT * FROM \"Board\" WHERE board_id = :board_id AND user_id = :user_id")
    result = db.execute(t, {"board_id": dashboard_id, "user_id": user_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Dashboard not found"})

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "latest", "db_ready", "channels.json")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=409, detail={"error": "no_data", "message": "No pipeline output available. Run the pipeline first."})

    board = dict(result._mapping)

    import_pipeline_data(board["board_id"])

    return {
        "message": "Pipeline Completed"
    }