import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from src import config, graph
from src.logging_utils import get_logger
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
        super().do_GET()

    def _handle_tag_detail(self, tag_name: str) -> None:
        detail = build_tag_detail(tag_name)
        if detail is None:
            self._send_json(404, {"error": "tag non trovato"})
            return
        self._send_json(200, detail)

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
