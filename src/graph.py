from collections import Counter
from itertools import combinations

import networkx as nx

from src import db_local
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


def build_graph_json() -> dict:
    """Rappresentazione JSON del grafo dei tag, per il frontend (nodi + archi).

    Il cluster di ogni nodo e' l'indice della sua componente connessa, usato
    dal frontend solo per colorare gruppi di tag imparentati tra loro.
    """
    g = build_graph()
    cluster_of: dict[str, int] = {}
    for i, component in enumerate(nx.connected_components(g)):
        for node in component:
            cluster_of[node] = i

    nodes = [
        {"id": node, "label": node, "count": data.get("size", 1), "cluster": cluster_of.get(node, 0)}
        for node, data in g.nodes(data=True)
    ]
    links = [
        {"source": u, "target": v, "value": data.get("weight", 1)}
        for u, v, data in g.edges(data=True)
    ]
    return {"nodes": nodes, "links": links}
