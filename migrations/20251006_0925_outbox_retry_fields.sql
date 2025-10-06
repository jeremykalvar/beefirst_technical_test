ALTER TABLE outbox
  ADD COLUMN IF NOT EXISTS attempts         integer    NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS next_attempt_at  timestamptz,
  ADD COLUMN IF NOT EXISTS last_error       text;

CREATE INDEX IF NOT EXISTS outbox_pending_next_attempt_idx
  ON outbox (next_attempt_at)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS outbox_pending_created_idx
  ON outbox (created_at)
  WHERE status = 'pending';
