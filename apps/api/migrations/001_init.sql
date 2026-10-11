-- DocuMind initial schema.
-- {{EMBED_DIM}} and {{TS_CONFIG}} are substituted from settings by app/migrate.py.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  text NOT NULL DEFAULT 'public',
  title         text NOT NULL,
  filename      text NOT NULL,
  mime_type     text NOT NULL,
  sha256        text NOT NULL,
  storage_path  text NOT NULL,
  source_url    text,                      -- where the official document came from
  status        text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','parsing','embedding','ready','failed')),
  error         text,
  page_count    int,
  chunk_count   int,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, sha256)
);

CREATE TABLE chunks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  text NOT NULL,
  document_id   uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal       int  NOT NULL,
  section_path  text NOT NULL DEFAULT '',
  page_start    int,
  page_end      int,
  content       text NOT NULL,
  token_count   int  NOT NULL,
  embedding     vector({{EMBED_DIM}}) NOT NULL,
  tsv           tsvector GENERATED ALWAYS AS
                (to_tsvector('{{TS_CONFIG}}', section_path || ' ' || content)) STORED
);
CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
CREATE INDEX chunks_tsv_gin ON chunks USING gin (tsv);
CREATE INDEX chunks_ws_doc ON chunks (workspace_id, document_id);

CREATE TABLE conversations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  text NOT NULL,
  title         text,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id  uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role             text NOT NULL CHECK (role IN ('user','assistant')),
  content          text NOT NULL,
  rewritten_query  text,
  model            text,
  input_tokens     int,
  output_tokens    int,
  latency_ms       int,
  ttft_ms          int,                    -- time to first token
  phantom_citations int DEFAULT 0,
  feedback         smallint CHECK (feedback IN (-1, 0, 1)),
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX messages_conv ON messages (conversation_id, created_at);

CREATE TABLE message_citations (
  message_id   uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  marker       int  NOT NULL,
  chunk_id     uuid REFERENCES chunks(id) ON DELETE SET NULL,
  PRIMARY KEY (message_id, marker)
);

CREATE TABLE eval_runs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  git_sha     text,
  config      jsonb NOT NULL,
  metrics     jsonb NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
