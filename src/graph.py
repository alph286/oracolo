from collections import Counter
from itertools import combinations
from pathlib import Path

import networkx as nx
from pyvis.network import Network

from src import config, db_local
from src.logging_utils import get_logger

log = get_logger(__name__)


def build_graph() -> nx.Graph:
    entries = db_local.get_entries_with_tags()
    log.info("Costruisco il grafo da %d entry", len(entries))

    tag_counts: Counter = Counter()
    edge_weights: Counter = Counter()

    for entry in entries:
        tags = sorted(set(entry["tags"]))
        tag_counts.update(tags)
        for tag_a, tag_b in combinations(tags, 2):
            edge_weights[(tag_a, tag_b)] += 1

    g = nx.Graph()
    for tag, count in tag_counts.items():
        g.add_node(tag, size=count)
    for (tag_a, tag_b), weight in edge_weights.items():
        g.add_edge(tag_a, tag_b, weight=weight)

    log.info("Grafo: %d nodi (tag), %d archi", g.number_of_nodes(), g.number_of_edges())
    return g


def render_graph(g: nx.Graph, output_path: str | None = None) -> str:
    output_path = output_path or config.GRAPH_OUTPUT_PATH
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    net = Network(
        height="900px",
        width="100%",
        bgcolor="#1a1a1a",
        font_color="#ffffff",
        notebook=False,
        cdn_resources="remote",
    )
    net.barnes_hut()

    for node, data in g.nodes(data=True):
        size = 10 + data.get("size", 1) * 4
        net.add_node(node, label=node, size=size, color="#e91ee9")

    for source, target, data in g.edges(data=True):
        net.add_edge(source, target, value=data.get("weight", 1), color="#4a8fa8")

    net.write_html(output_path, open_browser=False, notebook=False)
    log.info("Grafo scritto in %s", output_path)
    return output_path


def generate() -> str:
    g = build_graph()
    if g.number_of_nodes() == 0:
        log.warning(
            "Nessun tag trovato: il grafo sara' vuoto. "
            "Hai gia' eseguito 'sync' e 'tag' (o 'seed' per dati di prova)?"
        )
    return render_graph(g)
