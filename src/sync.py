from src import config, db_local, db_online
from src.logging_utils import get_logger

log = get_logger(__name__)


def run_sync() -> int:
    """Scarica tutte le entry dal MySQL online e le sincronizza in locale.

    Ritorna il numero di entry sincronizzate.
    """
    log.info("Inizializzo il DB locale (%s)...", config.LOCAL_DB_PATH)
    db_local.init_db()
    rows = db_online.fetch_all_entries()
    n = db_local.upsert_entries(rows)
    log.info("Sincronizzate %d entry nel DB locale", n)
    return n
