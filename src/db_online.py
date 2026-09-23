import mysql.connector

from src import config
from src.logging_utils import get_logger

log = get_logger(__name__)


def fetch_all_entries() -> list[dict]:
    """Legge tutte le righe dalla tabella MySQL online e le normalizza
    nel formato atteso da db_local.upsert_entries.
    """
    log.info(
        "Connessione a MySQL %s:%s/%s come utente '%s' (timeout %ss)...",
        config.MYSQL_HOST,
        config.MYSQL_PORT,
        config.MYSQL_DATABASE,
        config.MYSQL_USER,
        config.MYSQL_CONNECT_TIMEOUT_SECONDS,
    )
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE,
            connection_timeout=config.MYSQL_CONNECT_TIMEOUT_SECONDS,
        )
    except mysql.connector.Error:
        log.exception("Connessione a MySQL fallita")
        raise
    log.info("Connesso. Leggo la tabella '%s'...", config.MYSQL_TABLE)
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"SELECT id, {config.MYSQL_TEXT_COLUMN} AS text, created_at, "
            f"status, ip, likes FROM {config.MYSQL_TABLE}"
        )
        rows = cursor.fetchall()
        cursor.close()
    except mysql.connector.Error:
        log.exception("Query sulla tabella '%s' fallita", config.MYSQL_TABLE)
        raise
    finally:
        conn.close()

    log.info("Lette %d righe da MySQL", len(rows))
    return [
        {
            "id": row["id"],
            "text": row["text"],
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "status": row.get("status"),
            "ip": row.get("ip"),
            "likes": row.get("likes") or 0,
        }
        for row in rows
    ]
