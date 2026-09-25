import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

from src import config, graph
from src.logging_utils import get_logger
from src.question import answer_question, generate_questions
from src.tagdetail import build_tag_detail

log = get_logger(__name__)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/graph":
            self._send_json(200, graph.build_graph_json())
            return
        if path.startswith("/api/tag/"):
            tag_name = unquote(path[len("/api/tag/"):])
            self._handle_tag_detail(tag_name)
            return
        if path == "/api/questions":
            self._handle_questions()
            return
        super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == "/api/answer":
            self._handle_answer()
            return
        self.send_error(404)

    def _handle_tag_detail(self, tag_name: str) -> None:
        detail = build_tag_detail(tag_name)
        if detail is None:
            self._send_json(404, {"error": "tag non trovato"})
            return
        self._send_json(200, detail)

    def _handle_questions(self) -> None:
        try:
            questions = generate_questions()
        except requests.RequestException:
            log.exception("Chiamata a Ollama fallita (host %s raggiungibile?)", config.OLLAMA_HOST)
            self._send_json(502, {"error": "l'oracolo non risponde"})
            return
        if not questions:
            self._send_json(502, {"error": "nessuna domanda disponibile"})
            return
        self._send_json(200, {"questions": questions})

    def _handle_answer(self) -> None:
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
            answer = answer_question(question)
        except requests.RequestException:
            log.exception("Chiamata a Ollama fallita (host %s raggiungibile?)", config.OLLAMA_HOST)
            self._send_json(502, {"error": "l'oracolo non risponde"})
            return

        self._send_json(200, {"answer": answer or "L'oracolo resta in silenzio."})

    def _send_json(self, status: int, payload) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)


def run_server() -> None:
    directory = str(Path(config.FRONTEND_DIST_PATH).resolve())
    handler = partial(Handler, directory=directory)
    with ThreadingHTTPServer((config.SERVE_HOST, config.SERVE_PORT), handler) as httpd:
        log.info(
            "Server in ascolto su http://%s:%d (frontend: %s)",
            config.SERVE_HOST, config.SERVE_PORT, directory,
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            log.info("Server fermato")
