-- allow 'processing' as a valid outbox status

ALTER TABLE outbox
  DROP CONSTRAINT IF EXISTS outbox_status_check;

ALTER TABLE outbox
  ADD CONSTRAINT outbox_status_check
  CHECK (status IN ('pending','processing','dispatched','failed'));
