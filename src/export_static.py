import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

from src import db_local, graph
from src.logging_utils import get_logger
from src.tagdetail import build_tag_detail

log = get_logger(__name__)

FRONTEND_PROJECT_DIR = Path("layoutBoltNebulosa/project")


def _js_encode_uri_component(value: str) -> str:
    """Replica encodeURIComponent() di JS, cosi' i nomi dei file combaciano
    esattamente con l'URL che il frontend richiede in produzione."""
    return quote(value, safe="!*'()~")


def export_static(output_dir: Path, base_path: str) -> None:
    if not base_path.startswith("/"):
        base_path = "/" + base_path
    if not base_path.endswith("/"):
        base_path += "/"

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    _build_frontend(base_path, output_dir)
    _write_api_snapshot(output_dir)

    log.info("Export statico pronto in %s (base: %s)", output_dir.resolve(), base_path)


def _build_frontend(base_path: str, output_dir: Path) -> None:
    build_dir = FRONTEND_PROJECT_DIR / "dist_export"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError("npx non trovato nel PATH. Installa Node.js/npm.")

    log.info("Build del frontend con base %s...", base_path)
    subprocess.run(
        [npx, "vite", "build", f"--base={base_path}", f"--outDir={build_dir.name}"],
        cwd=FRONTEND_PROJECT_DIR,
        check=True,
    )

    for item in build_dir.iterdir():
        dest = output_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    shutil.rmtree(build_dir)


def _write_api_snapshot(output_dir: Path) -> None:
    api_dir = output_dir / "api"
    api_dir.mkdir()

    graph_json = graph.build_graph_json()
    (api_dir / "graph").write_text(
        json.dumps(graph_json, ensure_ascii=False), encoding="utf-8"
    )
    log.info(
        "api/graph: %d tag, %d collegamenti",
        len(graph_json["nodes"]), len(graph_json["links"]),
    )

    tag_dir = api_dir / "tag"
    tag_dir.mkdir()
    tag_names = sorted({t for entry in db_local.get_entries_with_tags() for t in entry["tags"]})
    for tag_name in tag_names:
        detail = build_tag_detail(tag_name)
        if detail is None:
            continue
        (tag_dir / _js_encode_uri_component(tag_name)).write_text(
            json.dumps(detail, ensure_ascii=False), encoding="utf-8"
        )
    log.info("api/tag/: %d tag esportati", len(tag_names))
