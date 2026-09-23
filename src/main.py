import argparse
import time

import schedule

from src import config, graph, sync, tagging


def do_sync() -> None:
    n = sync.run_sync()
    print(f"[sync] {n} entry sincronizzate da MySQL")


def do_tag() -> None:
    n = tagging.tag_pending_entries()
    print(f"[tag] {n} entry taggate con Ollama")


def do_graph() -> None:
    path = graph.generate()
    print(f"[graph] grafo generato in {path}")


def do_pipeline() -> None:
    do_sync()
    do_tag()
    do_graph()


def run_loop() -> None:
    print(
        f"[run] avvio con intervallo di {config.SYNC_INTERVAL_MINUTES} minuti "
        "(Ctrl+C per fermare)"
    )
    do_pipeline()
    schedule.every(config.SYNC_INTERVAL_MINUTES).minutes.do(do_pipeline)
    while True:
        schedule.run_pending()
        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Oracolo: sync + tagging + grafo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sync", help="Sincronizza le entry da MySQL a locale")
    subparsers.add_parser("tag", help="Tagga le entry non ancora processate")
    subparsers.add_parser("graph", help="Genera il grafo HTML dai tag")
    subparsers.add_parser("pipeline", help="Esegue sync + tag + graph una volta")
    subparsers.add_parser("run", help="Esegue la pipeline in loop, a intervalli")

    args = parser.parse_args()

    commands = {
        "sync": do_sync,
        "tag": do_tag,
        "graph": do_graph,
        "pipeline": do_pipeline,
        "run": run_loop,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
