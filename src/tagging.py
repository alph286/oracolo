import json

import requests

from src import config, db_local
from src.logging_utils import get_logger

log = get_logger(__name__)

TAG_PROMPT = """Analizza il seguente testo e assegna da 1 a {max_tags} tag \
brevi (una o due parole ciascuno) che ne descrivano il tema/argomento principale.
Rispondi SOLO con un array JSON di stringhe, senza altro testo. Esempio: ["amore", "gioco"]

Testo:
\"\"\"{text}\"\"\"
"""


def _ask_ollama_for_tags(text: str) -> list[str]:
    prompt = TAG_PROMPT.format(text=text, max_tags=config.MAX_TAGS_PER_ENTRY)
    response = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_TAG_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=config.OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    raw = response.json()["response"]
    try:
        tags = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Risposta di Ollama non e' JSON valido: %r", raw)
        return []
    if not isinstance(tags, list):
        log.warning("Risposta di Ollama non e' una lista: %r", tags)
        return []
    return [str(t) for t in tags][: config.MAX_TAGS_PER_ENTRY]


def tag_pending_entries() -> int:
    """Chiama Ollama per ogni entry non ancora taggata (o modificata dall'ultimo
    tagging). Ritorna il numero di entry taggate con successo.
    """
    entries = db_local.get_untagged_entries()
    log.info(
        "%d entry da taggare, modello '%s' su %s",
        len(entries),
        config.OLLAMA_TAG_MODEL,
        config.OLLAMA_HOST,
    )
    if not entries:
        return 0

    tagged = 0
    for i, entry in enumerate(entries, start=1):
        try:
            tags = _ask_ollama_for_tags(entry["text"])
        except requests.RequestException:
            log.exception(
                "Chiamata a Ollama fallita per entry id=%s (host %s raggiungibile?)",
                entry["id"],
                config.OLLAMA_HOST,
            )
            continue
        if tags:
            db_local.set_entry_tags(entry["id"], tags)
            tagged += 1
            log.debug("[%d/%d] entry id=%s -> tag %s", i, len(entries), entry["id"], tags)
        else:
            log.warning("[%d/%d] entry id=%s: nessun tag ottenuto", i, len(entries), entry["id"])
    return tagged
