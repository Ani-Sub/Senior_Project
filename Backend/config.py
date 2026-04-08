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
# llm
#=====================================
LLM_MODEL = "llama3"
LLM_URL = "http://localhost:11434/api/generate"
LLM_NUM_PREDICT = 2500  # Max tokens for LLM response (increase if JSON truncation occurs)

#=====================================
# embeddings (Ollama)
#=====================================
EMBEDDING_MODEL = "nomic-embed-text"  # Run: ollama pull nomic-embed-text
EMBEDDING_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_DIMENSIONS = 768  # nomic-embed-text outputs 768 dimensions

#=====================================
# chunking parameters
#=====================================
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200

