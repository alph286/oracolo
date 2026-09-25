# Oracolo

Sincronizza le entry di un DB MySQL online (tramite un endpoint PHP
sul hosting) in un archivio locale SQLite, le tagga tramite un modello
generativo su Ollama (in rete), e le mostra come una nebulosa di nodi
interattiva ("La Nebulosa", frontend React in `layoutBoltNebulosa/project`)
basata sui tag condivisi tra le entry.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # poi compila le variabili
```

Carica anche [hosting/api/export.php](hosting/api/export.php) nella stessa
cartella del `config.php` esistente sul server (vedi commento in testa al
file per l'unica cosa da adattare: il nome della tabella).

Per il frontend, la prima volta:

```bash
cd layoutBoltNebulosa/project
npm install
npm run build   # genera dist/, servito da `python -m src.main serve`
```

Va ricostruito (`npm run build`) ogni volta che si modifica il codice React;
i dati (tag/entry) invece sono live, letti dal server Python ad ogni richiesta.

## Uso

```bash
python -m src.main sync      # scarica/aggiorna le entry dalla sorgente remota
python -m src.main tag       # tagga le entry nuove/modificate via Ollama
python -m src.main pipeline  # sync + tag, una volta
python -m src.main run       # come pipeline, ma in loop ogni SYNC_INTERVAL_MINUTES
python -m src.main serve     # avvia il webserver locale (frontend + API)
python -m src.main seed      # inserisce dati di prova gia' taggati (per testare la nebulosa)
```

Apri `http://localhost:8000/` (con `serve` avviato) per esplorare la nebulosa
dei tag: cerca un tag dalla barra in basso, clicca un nodo per vedere i
frammenti che lo usano e i tag collegati.

Il server espone anche due endpoint JSON usati dal frontend:
- `GET /api/graph` — nodi (tag) e archi (co-occorrenze) dell'intero grafo
- `GET /api/tag/<nome>` — frammenti e tag collegati per un singolo tag

## Note

- `OLLAMA_EMBED_MODEL` (bge-m3) e' pensato per usi futuri di similarita'
  semantica tra entry; il tagging attuale usa solo `OLLAMA_TAG_MODEL`
  (un modello generativo, es. llama3.1) per scrivere i tag testuali.
- Il DB locale (`data/local.db`) non e' versionato: verra' ricreato al
  primo `sync`.
- `layoutBoltNebulosa/project` era in origine un progetto Bolt.new basato
  su Supabase (sorgenti/connessioni/history inserite a mano); e' stato
  adattato per leggere in sola lettura il grafo dei tag di Oracolo dal
  webserver Python locale, al posto di un database Supabase remoto.
