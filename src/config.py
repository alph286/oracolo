import os

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


MYSQL_HOST = os.getenv("MYSQL_HOST", "")
MYSQL_PORT = _int("MYSQL_PORT", 3306)
MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "")
MYSQL_TABLE = os.getenv("MYSQL_TABLE", "messages")
MYSQL_TEXT_COLUMN = os.getenv("MYSQL_TEXT_COLUMN", "text")

LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "data/local.db")

SYNC_INTERVAL_MINUTES = _int("SYNC_INTERVAL_MINUTES", 60)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
OLLAMA_TAG_MODEL = os.getenv("OLLAMA_TAG_MODEL", "llama3.1")
MAX_TAGS_PER_ENTRY = _int("MAX_TAGS_PER_ENTRY", 3)

GRAPH_OUTPUT_PATH = os.getenv("GRAPH_OUTPUT_PATH", "output/graph.html")
