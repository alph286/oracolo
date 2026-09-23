import mysql.connector

from src import config


def fetch_all_entries() -> list[dict]:
    """Legge tutte le righe dalla tabella MySQL online e le normalizza
    nel formato atteso da db_local.upsert_entries.
    """
    conn = mysql.connector.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE,
    )
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f"SELECT id, {config.MYSQL_TEXT_COLUMN} AS text, created_at, "
            f"status, ip, likes FROM {config.MYSQL_TABLE}"
        )
        rows = cursor.fetchall()
        cursor.close()
    finally:
        conn.close()

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
