import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from src import config
from src.logging_utils import get_logger

log = get_logger(__name__)

ANSWER_PROMPT = """Sei l'Oracolo. Rispondi alla domanda seguente in italiano, \
con un tono riflessivo e poetico, in modo breve (massimo 3-4 frasi). \
Rispondi solo con il testo della risposta, senza virgolette o altro.

Domanda: "{question}"
"""


def _ask_ollama_for_answer(question: str) -> str:
    response = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_TAG_MODEL,
            "prompt": ANSWER_PROMPT.format(question=question),
            "stream": False,
        },
        timeout=config.OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/answer":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "body non valido"})
            return

        question = str(body.get("question", "")).strip()
        if not question:
            self._send_json(400, {"error": "manca 'question'"})
            return

        try:
            answer = _ask_ollama_for_answer(question)
        except requests.RequestException:
            log.exception("Chiamata a Ollama fallita (host %s raggiungibile?)", config.OLLAMA_HOST)
            self._send_json(502, {"error": "l'oracolo non risponde"})
            return

        self._send_json(200, {"answer": answer or "L'oracolo resta in silenzio."})

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)


def run_server() -> None:
    directory = str(Path(config.QUESTION_OUTPUT_PATH).parent)
    handler = partial(Handler, directory=directory)
    with ThreadingHTTPServer((config.SERVE_HOST, config.SERVE_PORT), handler) as httpd:
        log.info(
            "Server in ascolto su http://%s:%d (cartella servita: %s)",
            config.SERVE_HOST, config.SERVE_PORT, directory,
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            log.info("Server fermato")
