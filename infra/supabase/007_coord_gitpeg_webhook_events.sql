-- Replay guard ledger for GitPeg webhook events.
create table if not exists public.coord_gitpeg_webhook_events (
  event_id text primary key,
  partner_code text,
  signature text,
  received_at timestamptz not null default now()
);

create index if not exists idx_coord_gitpeg_webhook_events_received_at
  on public.coord_gitpeg_webhook_events(received_at desc);
