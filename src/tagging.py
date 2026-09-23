import json

import requests

from src import config, db_local

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
        timeout=60,
    )
    response.raise_for_status()
    raw = response.json()["response"]
    try:
        tags = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(tags, list):
        return []
    return [str(t) for t in tags][: config.MAX_TAGS_PER_ENTRY]


def tag_pending_entries() -> int:
    """Chiama Ollama per ogni entry non ancora taggata (o modificata dall'ultimo
    tagging). Ritorna il numero di entry taggate con successo.
    """
    entries = db_local.get_untagged_entries()
    tagged = 0
    for entry in entries:
        tags = _ask_ollama_for_tags(entry["text"])
        if tags:
            db_local.set_entry_tags(entry["id"], tags)
            tagged += 1
    return tagged
