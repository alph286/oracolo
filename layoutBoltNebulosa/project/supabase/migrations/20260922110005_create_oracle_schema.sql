/*
# Create Oracle collective-memory schema

A shared, single-tenant knowledge graph. No sign-in: the app runs as anon
and all data is intentionally public/shared.

1. New Tables
- `sources`: a node in the knowledge nebula (book, pdf, link, note, paper).
  - id (uuid pk), title (text), kind (enum), author (text), url (text),
    description (text), cluster (int), pos_x/pos_y (float for initial position),
    created_at, updated_at.
- `connections`: an undirected edge between two sources.
  - id (uuid pk), source_id (fk), target_id (fk), created_at.
- `change_log`: append-only history of every change for collective memory.
  - id (uuid pk), action (enum), entity_type (text), entity_id (uuid),
    summary (text), payload (jsonb), created_at.

2. Security
- RLS enabled on all three tables.
- All policies use `TO anon, authenticated` (no-auth, shared app).
- `change_log` is INSERT + SELECT only so history is immutable.

3. Important notes
- Triggers auto-record source and connection changes into change_log.
- A unique index on LEAST/GREATEST prevents duplicate undirected edges.
- `change_log` has no UPDATE or DELETE policy: history is immutable.
*/

-- ── sources ──
CREATE TABLE IF NOT EXISTS sources (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text NOT NULL,
  kind        text NOT NULL DEFAULT 'note'
              CHECK (kind IN ('paper','pdf','link','note','book')),
  author      text,
  url         text,
  description text,
  cluster     int  NOT NULL DEFAULT 5,
  pos_x       double precision DEFAULT (random() * 400 - 200),
  pos_y       double precision DEFAULT (random() * 300 - 150),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE sources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_sources" ON sources;
CREATE POLICY "anon_select_sources" ON sources FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_sources" ON sources;
CREATE POLICY "anon_insert_sources" ON sources FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_sources" ON sources;
CREATE POLICY "anon_update_sources" ON sources FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_sources" ON sources;
CREATE POLICY "anon_delete_sources" ON sources FOR DELETE
  TO anon, authenticated USING (true);

-- ── connections ──
CREATE TABLE IF NOT EXISTS connections (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id  uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  target_id  uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT connections_no_self CHECK (source_id <> target_id)
);

ALTER TABLE connections ENABLE ROW LEVEL SECURITY;

-- Unique index on unordered pair to prevent duplicate edges
CREATE UNIQUE INDEX IF NOT EXISTS connections_pair_unique
  ON connections (LEAST(source_id, target_id), GREATEST(source_id, target_id));

DROP POLICY IF EXISTS "anon_select_connections" ON connections;
CREATE POLICY "anon_select_connections" ON connections FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_connections" ON connections;
CREATE POLICY "anon_insert_connections" ON connections FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_connections" ON connections;
CREATE POLICY "anon_delete_connections" ON connections FOR DELETE
  TO anon, authenticated USING (true);

-- ── change_log (append-only) ──
CREATE TABLE IF NOT EXISTS change_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action      text NOT NULL
              CHECK (action IN ('create_source','update_source','delete_source',
                     'create_connection','delete_connection','oracle_query')),
  entity_type text,
  entity_id   uuid,
  summary     text NOT NULL,
  payload     jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE change_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_select_changelog" ON change_log;
CREATE POLICY "anon_select_changelog" ON change_log FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_changelog" ON change_log;
CREATE POLICY "anon_insert_changelog" ON change_log FOR INSERT
  TO anon, authenticated WITH CHECK (true);

-- No UPDATE or DELETE policies: history is immutable.

-- ── trigger: auto-log source changes ──
CREATE OR REPLACE FUNCTION log_source_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_log (action, entity_type, entity_id, summary, payload)
    VALUES ('create_source', 'source', NEW.id,
            'Added source: ' || NEW.title,
            jsonb_build_object('title', NEW.title, 'kind', NEW.kind));
    RETURN NEW;
  ELSIF (TG_OP = 'UPDATE') THEN
    INSERT INTO change_log (action, entity_type, entity_id, summary, payload)
    VALUES ('update_source', 'source', NEW.id,
            'Updated source: ' || NEW.title,
            jsonb_build_object('title', NEW.title, 'kind', NEW.kind));
    RETURN NEW;
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_log (action, entity_type, entity_id, summary, payload)
    VALUES ('delete_source', 'source', OLD.id,
            'Removed source: ' || OLD.title,
            jsonb_build_object('title', OLD.title, 'kind', OLD.kind));
    RETURN OLD;
  END IF;
  RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS sources_change_trigger ON sources;
CREATE TRIGGER sources_change_trigger
  AFTER INSERT OR UPDATE OR DELETE ON sources
  FOR EACH ROW EXECUTE FUNCTION log_source_change();

-- ── trigger: auto-log connection changes ──
CREATE OR REPLACE FUNCTION log_connection_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO change_log (action, entity_type, entity_id, summary, payload)
    VALUES ('create_connection', 'connection', NEW.id,
            'Connected two sources',
            jsonb_build_object('source_id', NEW.source_id, 'target_id', NEW.target_id));
    RETURN NEW;
  ELSIF (TG_OP = 'DELETE') THEN
    INSERT INTO change_log (action, entity_type, entity_id, summary, payload)
    VALUES ('delete_connection', 'connection', OLD.id,
            'Removed a connection',
            jsonb_build_object('source_id', OLD.source_id, 'target_id', OLD.target_id));
    RETURN OLD;
  END IF;
  RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS connections_change_trigger ON connections;
CREATE TRIGGER connections_change_trigger
  AFTER INSERT OR DELETE ON connections
  FOR EACH ROW EXECUTE FUNCTION log_connection_change();

-- ── trigger: auto-update updated_at on sources ──
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS sources_touch_trigger ON sources;
CREATE TRIGGER sources_touch_trigger
  BEFORE UPDATE ON sources
  FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ── indexes ──
CREATE INDEX IF NOT EXISTS idx_sources_kind ON sources(kind);
CREATE INDEX IF NOT EXISTS idx_connections_source ON connections(source_id);
CREATE INDEX IF NOT EXISTS idx_connections_target ON connections(target_id);
CREATE INDEX IF NOT EXISTS idx_changelog_created ON change_log(created_at DESC);
