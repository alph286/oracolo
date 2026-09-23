import requests

from src import config
from src.logging_utils import get_logger

log = get_logger(__name__)


def fetch_all_entries() -> list[dict]:
    """Scarica tutte le entry dall'endpoint PHP (hosting/api/export.php)
    e le normalizza nel formato atteso da db_local.upsert_entries.
    """
    log.info(
        "Richiesta a %s (timeout %ss)...",
        config.REMOTE_API_URL,
        config.REMOTE_API_TIMEOUT_SECONDS,
    )
    try:
        response = requests.get(
            config.REMOTE_API_URL,
            headers={"X-Api-Key": config.REMOTE_API_KEY},
            timeout=config.REMOTE_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException:
        log.exception(
            "Richiesta a %s fallita (URL/API key corretti in .env? "
            "il sito e' raggiungibile?)",
            config.REMOTE_API_URL,
        )
        raise

    rows = response.json()
    log.info("Lette %d righe da %s", len(rows), config.REMOTE_API_URL)

    return [
        {
            "id": row["id"],
            "text": row["text"],
            "created_at": row.get("created_at"),
            "status": row.get("status"),
            "ip": row.get("ip"),
            "likes": row.get("likes") or 0,
        }
        for row in rows
    ]
