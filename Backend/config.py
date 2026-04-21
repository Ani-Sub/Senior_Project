import os
import logging
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

#=====================================
# logging
#=====================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

#=====================================
# yt API key
#=====================================
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise EnvironmentError("YOUTUBE_API_KEY not set. Add it to your .env file.")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

#=====================================
# Groq LLM
#=====================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY not set. Add it to your .env file.")

LLM_MODEL = "llama-3.3-70b-versatile"
LLM_URL = "https://api.groq.com/openai/v1/chat/completions"
LLM_MAX_TOKENS = 2000   # Reduced - JSON responses don't need 8k

#=====================================
# chunking parameters
#=====================================
CHUNK_SIZE = 3000       # Characters per chunk (~750 tokens)
CHUNK_OVERLAP = 200     # Overlap between chunks

