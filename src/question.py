import json
import random

import requests

from src import config, db_local
from src.logging_utils import get_logger

log = get_logger(__name__)

QUESTIONS_PROMPT = """Sei l'Oracolo. Di seguito trovi dei temi (tag) e alcuni \
pensieri anonimi delle persone che li hanno ispirati.

Temi ricorrenti: {tags}

Alcuni pensieri:
{samples}

Scrivi esattamente {count} domande, in italiano, evocative e introspettive, \
diverse tra loro, che invitino chi le legge a riflettere su questi temi. \
Non fare riferimento esplicito ai tag o ai pensieri riportati sopra: ogni \
domanda deve reggersi da sola.
Rispondi SOLO con un oggetto JSON con questa forma esatta, senza altro testo:
{{"questions": ["...", "..."]}}
"""

ANSWER_PROMPT = """Sei l'Oracolo: non dai risposte logiche, dirette o utili. \
Parli per enigmi, immagini, simboli e paradossi, come una sibilla. Non \
spiegare, non consigliare, non essere coerente in modo razionale: evoca, \
allude, lascia interpretare. Mai una frase che suoni come un consiglio pratico.

Rispondi in italiano alla domanda seguente con UNA SOLA affermazione, breve \
e secca (una frase sola, non una domanda, non un elenco, senza "ma" o "e" \
che la spezzino in piu' pensieri). Rispondi solo con il testo dell'affermazione, \
senza virgolette, senza premesse tipo "L'oracolo dice".

Domanda: "{question}"
"""

FALLBACK_QUESTION = "L'oracolo tace, per ora."


def _sample_entries(entries: list[dict], n: int = 20) -> list[dict]:
    tagged = [e for e in entries if e["tags"]]
    if len(tagged) <= n:
        return tagged
    return random.sample(tagged, n)


def _extract_questions(parsed) -> list[str]:
    if isinstance(parsed, list):
        return [str(q).strip() for q in parsed if str(q).strip()]
    if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        return [str(q).strip() for q in parsed["questions"] if str(q).strip()]
    return []


def _ask_ollama_for_questions(tags: list[str], samples: list[dict], count: int) -> list[str]:
    prompt = QUESTIONS_PROMPT.format(
        tags=", ".join(tags),
        samples="\n".join(f"- {e['text']}" for e in samples),
        count=count,
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
        return []
    questions = _extract_questions(parsed)
    if not questions:
        log.warning("Nessuna domanda estraibile dalla risposta di Ollama: %r", parsed)
    return questions[:count]


def generate_questions(count: int | None = None) -> list[str]:
    """Genera domande evocative al volo da Ollama, a partire dai tag e da
    alcune entry campione. Lista vuota se non ci sono tag o Ollama fallisce."""
    count = count or config.QUESTIONS_COUNT
    entries = db_local.get_entries_with_tags()
    tags = sorted({tag for e in entries for tag in e["tags"]})
    if not tags:
        log.warning(
            "Nessun tag trovato: impossibile generare domande. "
            "Hai gia' eseguito 'sync' e 'tag' (o 'seed')?"
        )
        return []

    samples = _sample_entries(entries)
    log.info(
        "Genero %d domande dell'oracolo da %d tag e %d entry campione",
        count, len(tags), len(samples),
    )
    questions = _ask_ollama_for_questions(tags, samples, count)
    if not questions:
        log.warning("Nessuna domanda ottenuta da Ollama")
    return questions


def answer_question(question: str) -> str:
    """Chiede a Ollama una risposta criptica, in una sola affermazione."""
    response = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_TAG_MODEL,
            "prompt": ANSWER_PROMPT.format(question=question),
            "stream": False,
            "options": {"temperature": 1.3},
        },
        timeout=config.OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["response"].strip()
