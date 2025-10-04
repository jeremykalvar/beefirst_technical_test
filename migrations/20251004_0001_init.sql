CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS users (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email             citext NOT NULL UNIQUE,
  password_hash     text   NOT NULL,
  status            text   NOT NULL CHECK (status IN ('pending','active','locked')),
  failed_attempts   integer NOT NULL DEFAULT 0,
  last_code_sent_at timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outbox_messages (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic            text   NOT NULL,
  payload          jsonb  NOT NULL,
  idempotency_key  text   UNIQUE,
  status           text   NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','failed')),
  attempts         integer NOT NULL DEFAULT 0,
  last_error       text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  sent_at          timestamptz
);

CREATE INDEX IF NOT EXISTS idx_outbox_status_created_at
  ON outbox_messages (status, created_at DESC);
