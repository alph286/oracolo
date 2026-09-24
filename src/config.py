import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


# Endpoint PHP (hosting/api/export.php) che espone il DB via HTTP,
# protetto dalla stessa api_key definita in config.php sul server.
REMOTE_API_URL = os.getenv("REMOTE_API_URL", "")
REMOTE_API_KEY = os.getenv("REMOTE_API_KEY", "")

LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "data/local.db")

SYNC_INTERVAL_MINUTES = _int("SYNC_INTERVAL_MINUTES", 60)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
OLLAMA_TAG_MODEL = os.getenv("OLLAMA_TAG_MODEL", "llama3.1")
MAX_TAGS_PER_ENTRY = _int("MAX_TAGS_PER_ENTRY", 3)

GRAPH_OUTPUT_PATH = os.getenv("GRAPH_OUTPUT_PATH", "output/graph.html")
QUESTION_OUTPUT_PATH = os.getenv("QUESTION_OUTPUT_PATH", "output/question.html")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REMOTE_API_TIMEOUT_SECONDS = _int("REMOTE_API_TIMEOUT_SECONDS", 15)
OLLAMA_TIMEOUT_SECONDS = _int("OLLAMA_TIMEOUT_SECONDS", 60)
