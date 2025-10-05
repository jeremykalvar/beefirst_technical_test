-- Create the outbox table for async email dispatch

CREATE TABLE IF NOT EXISTS outbox (
  id               BIGSERIAL PRIMARY KEY,
  topic            TEXT        NOT NULL,
  payload          JSONB       NOT NULL,
  status           TEXT        NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending','sent','failed')),
  attempts         INTEGER     NOT NULL DEFAULT 0,
  last_error       TEXT,
  idempotency_key  TEXT UNIQUE,
  available_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outbox_status_available
  ON outbox (status, available_at);
