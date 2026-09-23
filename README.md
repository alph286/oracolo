# Oracolo

Sincronizza le entry di un DB MySQL online in un archivio locale SQLite,
le tagga tramite un modello generativo su Ollama (in rete), e genera una
mappa a nodi interattiva basata sui tag condivisi tra le entry.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # poi compila le variabili
```

## Uso

```bash
python -m src.main sync      # scarica/aggiorna le entry da MySQL
python -m src.main tag       # tagga le entry nuove/modificate via Ollama
python -m src.main graph     # genera output/graph.html
python -m src.main pipeline  # sync + tag + graph, una volta
python -m src.main run       # come pipeline, ma in loop ogni SYNC_INTERVAL_MINUTES
```

## Note

- `OLLAMA_EMBED_MODEL` (bge-m3) e' pensato per usi futuri di similarita'
  semantica tra entry; il tagging attuale usa solo `OLLAMA_TAG_MODEL`
  (un modello generativo, es. llama3.1) per scrivere i tag testuali.
- Il DB locale (`data/local.db`) non e' versionato: verra' ricreato al
  primo `sync`.
