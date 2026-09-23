from src import db_local, db_online


def run_sync() -> int:
    """Scarica tutte le entry dal MySQL online e le sincronizza in locale.

    Ritorna il numero di entry sincronizzate.
    """
    db_local.init_db()
    rows = db_online.fetch_all_entries()
    return db_local.upsert_entries(rows)
