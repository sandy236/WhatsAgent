from pathlib import Path
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
CHROMA_DIR = os.getenv("CHROMA_DIR", str(DATA_DIR / "chromadb"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
GEMINI_URL = os.getenv("GEMINI_URL", "https://api.openai.com/v1/chat/completions")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-3-flash-preview,gemini-3.5-pro,gemini-3.5-mini").split(",") if m.strip()]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
GEMINI_RETRY_COUNT = int(os.getenv("GEMINI_RETRY_COUNT", "3"))
GEMINI_RETRY_BACKOFF = float(os.getenv("GEMINI_RETRY_BACKOFF", "1.0"))
GEMINI_RETRY_BACKOFF_FACTOR = float(os.getenv("GEMINI_RETRY_BACKOFF_FACTOR", "2.0"))
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "120"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "100"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))
RETRIEVAL_COUNT = int(os.getenv("RETRIEVAL_COUNT", "4"))
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
