import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

API_TITLE = os.getenv("PROJECT_NAME", "Zenith: Multi-Modal RAG Platform")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploaded_documents"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "5"))
RETRIEVAL_CANDIDATE_K = int(os.getenv("RETRIEVAL_CANDIDATE_K", "20"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "zenith-docs")
QDRANT_STORAGE_PATH = Path(os.getenv("QDRANT_STORAGE_PATH", BASE_DIR / "qdrant_storage"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "meta-llama/Llama-3.1-8B-Instruct")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")
ENABLE_LOCAL_LLM_FALLBACK = os.getenv("ENABLE_LOCAL_LLM_FALLBACK", "false").lower() in ("true", "1", "yes")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
VISION_MODEL_ID = os.getenv(
    "VISION_MODEL_ID", "Salesforce/blip-image-captioning-base"
)
SESSION_DB_PATH = Path(os.getenv("SESSION_DB_PATH", BASE_DIR / "sessions.sqlite3"))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN") or None
GITHUB_MAX_FILES = int(os.getenv("GITHUB_MAX_FILES", "500"))
GITHUB_MAX_FILE_BYTES = int(os.getenv("GITHUB_MAX_FILE_BYTES", "200000"))
