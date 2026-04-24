import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

engine = create_engine(
    os.getenv("DATABASE_URL"),
    pool_size=5,
    max_overflow=2
)
SessionLocal = sessionmaker(autoflush=False, bind=engine)
