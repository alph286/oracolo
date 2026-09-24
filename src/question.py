import json
import random
import re
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

# Iniettati in graph.html: uno stile (prima di </head>) e un blocco con il
# div centrale della domanda + script (prima di </body>). Cosi' la pagina
# del grafo resta l'unica pagina, con la domanda sovrapposta al centro.
OVERLAY_STYLE = """<style>
  html, body {{
    height: 100%;
    margin: 0;
    overflow: hidden;
    background: #1a1a1a !important;
  }}
  .card, .card-body, #mynetwork {{
    width: 100% !important;
    height: 100% !important;
    margin: 0 !important;
    border: none !important;
    background-color: #1a1a1a !important;
  }}
  .oracolo-overlay {{
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 1;
  }}
  .oracolo-content {{
    position: fixed;
    inset: 0;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    box-sizing: border-box;
    font-family: Georgia, "Times New Roman", serif;
    color: #ffffff;
  }}
  .oracolo-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .oracolo-question {{
    max-width: 40rem;
    font-size: 2rem;
    line-height: 1.4;
    color: #e91ee9;
    transition: opacity 1s ease;
  }}
  .oracolo-question.fade {{
    opacity: 0;
  }}
  .oracolo-buttons {{
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    justify-content: center;
  }}
  .oracolo-reroll {{
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
  .oracolo-reroll:hover {{
    background: #e91ee9;
    color: #1a1a1a;
  }}
  .oracolo-reroll:disabled {{
    opacity: 0.5;
    cursor: default;
  }}
  .oracolo-answer {{
    margin-top: 1.5rem;
    max-width: 36rem;
    font-size: 1.1rem;
    line-height: 1.5;
    color: #cfcfcf;
    font-style: italic;
    min-height: 1.5rem;
  }}
</style>
"""

OVERLAY_BODY = """<div class="oracolo-overlay"></div>
<div class="oracolo-content">
  <div class="oracolo-wrap">
    <div class="oracolo-question" id="oracolo-question">{first_question}</div>
    <div class="oracolo-buttons">
      <button class="oracolo-reroll" id="oracolo-reroll" type="button">un'altra domanda</button>
      <button class="oracolo-reroll" id="oracolo-answer-btn" type="button">chiedi la risposta</button>
    </div>
    <div class="oracolo-answer" id="oracolo-answer"></div>
  </div>
</div>
<script>
  const ORACOLO_QUESTIONS = {questions_json};
  const oracoloEl = document.getElementById("oracolo-question");
  const oracoloReroll = document.getElementById("oracolo-reroll");
  const oracoloAnswerBtn = document.getElementById("oracolo-answer-btn");
  const oracoloAnswerEl = document.getElementById("oracolo-answer");
  let oracoloLast = ORACOLO_QUESTIONS.indexOf(oracoloEl.textContent);

  function oracoloPickNext() {{
    if (ORACOLO_QUESTIONS.length <= 1) return ORACOLO_QUESTIONS[0] || "";
    let i;
    do {{
      i = Math.floor(Math.random() * ORACOLO_QUESTIONS.length);
    }} while (i === oracoloLast);
    oracoloLast = i;
    return ORACOLO_QUESTIONS[i];
  }}

  function oracoloShowNext() {{
    oracoloAnswerEl.textContent = "";
    oracoloEl.classList.add("fade");
    setTimeout(() => {{
      oracoloEl.textContent = oracoloPickNext();
      oracoloEl.classList.remove("fade");
    }}, 1000);
  }}

  oracoloReroll.addEventListener("click", oracoloShowNext);

  oracoloAnswerBtn.addEventListener("click", async () => {{
    oracoloAnswerBtn.disabled = true;
    oracoloAnswerEl.textContent = "l'oracolo riflette...";
    try {{
      const res = await fetch("/api/answer", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ question: oracoloEl.textContent }}),
      }});
      const data = await res.json();
      oracoloAnswerEl.textContent = res.ok
        ? data.answer
        : (data.error || "l'oracolo non risponde");
    }} catch (err) {{
      oracoloAnswerEl.textContent =
        "impossibile contattare l'oracolo (serve avviato con 'python -m src.main serve'?)";
    }} finally {{
      oracoloAnswerBtn.disabled = false;
    }}
  }});
</script>
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


def render_questions(questions: list[str], graph_path: str | None = None) -> str:
    """Inietta la domanda dell'oracolo come overlay centrale dentro graph.html."""
    graph_path = graph_path or config.GRAPH_OUTPUT_PATH
    graph_file = Path(graph_path)
    try:
        html = graph_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning(
            "Nessun grafo trovato in %s: impossibile sovrapporre la domanda (esegui 'graph'?)",
            graph_path,
        )
        return graph_path

    questions = questions or [FALLBACK_QUESTION]
    first = random.choice(questions)
    style = OVERLAY_STYLE.format()
    body = OVERLAY_BODY.format(
        first_question=first,
        questions_json=json.dumps(questions, ensure_ascii=False),
    )

    html = re.sub(r"</head>", style + "</head>", html, count=1, flags=re.IGNORECASE)
    html = re.sub(r"</body>", body + "</body>", html, count=1, flags=re.IGNORECASE)

    graph_file.write_text(html, encoding="utf-8")
    log.info("%d domande sovrapposte a %s", len(questions), graph_path)
    return graph_path


def generate() -> str:
    questions = generate_questions()
    return render_questions(questions)
