import json
import random
from pathlib import Path

import requests

from src import config, db_local
from src.logging_utils import get_logger

log = get_logger(__name__)

QUESTION_PROMPT = """Sei l'Oracolo. Di seguito trovi dei temi (tag) e alcuni \
pensieri anonimi delle persone che li hanno ispirati.

Temi ricorrenti: {tags}

Alcuni pensieri:
{samples}

Scrivi UNA sola domanda, in italiano, evocativa e introspettiva, che inviti \
chi la legge a riflettere su questi temi. Non fare riferimento esplicito ai \
tag o ai pensieri riportati sopra: la domanda deve reggersi da sola.
Rispondi SOLO con un oggetto JSON con questa forma esatta, senza altro testo:
{{"question": "..."}}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Oracolo</title>
<style>
  html, body {{
    height: 100%;
    margin: 0;
    background: #1a1a1a;
    color: #ffffff;
    font-family: Georgia, "Times New Roman", serif;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    box-sizing: border-box;
  }}
  .question {{
    max-width: 40rem;
    font-size: 2rem;
    line-height: 1.4;
    color: #e91ee9;
  }}
</style>
</head>
<body>
  <div class="question">{question}</div>
</body>
</html>
"""


def _sample_entries(entries: list[dict], n: int = 8) -> list[dict]:
    tagged = [e for e in entries if e["tags"]]
    if len(tagged) <= n:
        return tagged
    return random.sample(tagged, n)


def _ask_ollama_for_question(tags: list[str], samples: list[dict]) -> str:
    prompt = QUESTION_PROMPT.format(
        tags=", ".join(tags),
        samples="\n".join(f"- {e['text']}" for e in samples),
    )
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
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Risposta di Ollama non e' JSON valido: %r", raw)
        return ""
    question = parsed.get("question") if isinstance(parsed, dict) else None
    return str(question).strip() if question else ""


def generate_question() -> str:
    entries = db_local.get_entries_with_tags()
    tags = sorted({tag for e in entries for tag in e["tags"]})
    if not tags:
        log.warning(
            "Nessun tag trovato: impossibile generare una domanda. "
            "Hai gia' eseguito 'sync' e 'tag' (o 'seed')?"
        )
        return ""

    samples = _sample_entries(entries)
    log.info("Genero la domanda dell'oracolo da %d tag e %d entry campione", len(tags), len(samples))
    try:
        question = _ask_ollama_for_question(tags, samples)
    except requests.RequestException:
        log.exception("Chiamata a Ollama fallita (host %s raggiungibile?)", config.OLLAMA_HOST)
        return ""
    if not question:
        log.warning("Nessuna domanda ottenuta da Ollama")
    return question


def render_question(question: str, output_path: str | None = None) -> str:
    output_path = output_path or config.QUESTION_OUTPUT_PATH
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.format(question=question or "L'oracolo tace, per ora.")
    Path(output_path).write_text(html, encoding="utf-8")
    log.info("Domanda scritta in %s", output_path)
    return output_path


def generate() -> str:
    question = generate_question()
    return render_question(question)
