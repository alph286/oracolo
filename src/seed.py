"""Dati di prova per testare il grafo senza MySQL/Ollama collegati."""

from src import db_local
from src.logging_utils import get_logger

log = get_logger(__name__)

FIXTURE_ENTRIES = [
    {"id": 1, "text": "Ti voglio bene", "tags": ["amore", "connessione"]},
    {"id": 2, "text": "La forza sta nelle relazioni", "tags": ["connessione", "forza"]},
    {"id": 3, "text": "Impara giocando", "tags": ["gioco", "apprendimento"]},
    {"id": 4, "text": "Il gioco è la base della creatività", "tags": ["gioco", "creativita"]},
    {"id": 5, "text": "Capire se stessi richiede consapevolezza", "tags": ["apprendimento", "consapevolezza"]},
    {"id": 6, "text": "L'umorismo aiuta ad affrontare le sfide", "tags": ["umorismo", "sfida"]},
]


def seed_test_data() -> None:
    db_local.init_db()
    rows = [
        {
            "id": e["id"],
            "text": e["text"],
            "created_at": None,
            "status": "test",
            "ip": None,
            "likes": 0,
        }
        for e in FIXTURE_ENTRIES
    ]
    db_local.upsert_entries(rows)
    for e in FIXTURE_ENTRIES:
        db_local.set_entry_tags(e["id"], e["tags"])
    log.info("Inserite %d entry di prova, gia' taggate", len(FIXTURE_ENTRIES))
