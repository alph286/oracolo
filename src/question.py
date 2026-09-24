import json
import random
from pathlib import Path

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
    transition: opacity 1s ease;
  }}
  .question.fade {{
    opacity: 0;
  }}
  .reroll {{
    margin-top: 2rem;
    background: transparent;
    color: #e91ee9;
    border: 1px solid #e91ee9;
    border-radius: 999px;
    padding: 0.6rem 1.4rem;
    font-family: inherit;
    font-size: 1rem;
    cursor: pointer;
  }}
  .reroll:hover {{
    background: #e91ee9;
    color: #1a1a1a;
  }}
  .reroll:disabled {{
    opacity: 0.5;
    cursor: default;
  }}
  .reroll.toggled {{
    background: #e91ee9;
    color: #1a1a1a;
  }}
  .buttons {{
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    justify-content: center;
  }}
  .wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .answer {{
    margin-top: 1.5rem;
    max-width: 36rem;
    font-size: 1.1rem;
    line-height: 1.5;
    color: #cfcfcf;
    font-style: italic;
    min-height: 1.5rem;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="question" id="question">{first_question}</div>
    <div class="buttons">
      <button class="reroll" id="reroll" type="button">un'altra domanda</button>
      <button class="reroll" id="toggle-rotation" type="button">metti in pausa</button>
      <button class="reroll" id="answer-btn" type="button">chiedi la risposta</button>
    </div>
    <div class="answer" id="answer"></div>
  </div>
  <script>
    const QUESTIONS = {questions_json};
    const ROTATE_SECONDS = {rotate_seconds};
    const el = document.getElementById("question");
    const rerollButton = document.getElementById("reroll");
    const toggleButton = document.getElementById("toggle-rotation");
    const answerButton = document.getElementById("answer-btn");
    const answerEl = document.getElementById("answer");
    let last = QUESTIONS.indexOf(el.textContent);
    let timer = null;
    let paused = false;

    function pickNext() {{
      if (QUESTIONS.length <= 1) return QUESTIONS[0] || "";
      let i;
      do {{
        i = Math.floor(Math.random() * QUESTIONS.length);
      }} while (i === last);
      last = i;
      return QUESTIONS[i];
    }}

    function showNext() {{
      answerEl.textContent = "";
      el.classList.add("fade");
      setTimeout(() => {{
        el.textContent = pickNext();
        el.classList.remove("fade");
      }}, 1000);
    }}

    function startRotation() {{
      if (!paused && ROTATE_SECONDS > 0 && QUESTIONS.length > 1) {{
        timer = setInterval(showNext, ROTATE_SECONDS * 1000);
      }}
    }}

    function stopRotation() {{
      if (timer) {{
        clearInterval(timer);
        timer = null;
      }}
    }}

    rerollButton.addEventListener("click", () => {{
      showNext();
      if (!paused) {{
        stopRotation();
        startRotation();
      }}
    }});

    toggleButton.addEventListener("click", () => {{
      paused = !paused;
      toggleButton.textContent = paused ? "riprendi rotazione" : "metti in pausa";
      toggleButton.classList.toggle("toggled", paused);
      if (paused) {{
        stopRotation();
      }} else {{
        startRotation();
      }}
    }});

    answerButton.addEventListener("click", async () => {{
      answerButton.disabled = true;
      answerEl.textContent = "l'oracolo riflette...";
      try {{
        const res = await fetch("/api/answer", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ question: el.textContent }}),
        }});
        const data = await res.json();
        answerEl.textContent = res.ok
          ? data.answer
          : (data.error || "l'oracolo non risponde");
      }} catch (err) {{
        answerEl.textContent =
          "impossibile contattare l'oracolo (serve avviato con 'python -m src.main serve'?)";
      }} finally {{
        answerButton.disabled = false;
      }}
    }});

    startRotation();
  </script>
</body>
</html>
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
    try:
        questions = _ask_ollama_for_questions(tags, samples, count)
    except requests.RequestException:
        log.exception("Chiamata a Ollama fallita (host %s raggiungibile?)", config.OLLAMA_HOST)
        return []
    if not questions:
        log.warning("Nessuna domanda ottenuta da Ollama")
    return questions


def render_questions(questions: list[str], output_path: str | None = None) -> str:
    output_path = output_path or config.QUESTION_OUTPUT_PATH
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    questions = questions or [FALLBACK_QUESTION]
    first = random.choice(questions)
    html = HTML_TEMPLATE.format(
        first_question=first,
        questions_json=json.dumps(questions, ensure_ascii=False),
        rotate_seconds=config.QUESTIONS_ROTATE_SECONDS,
    )
    Path(output_path).write_text(html, encoding="utf-8")
    log.info("%d domande scritte in %s", len(questions), output_path)
    return output_path


def generate() -> str:
    questions = generate_questions()
    return render_questions(questions)
