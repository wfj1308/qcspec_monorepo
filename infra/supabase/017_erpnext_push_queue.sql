-- ERPNext push queue for DocPeg sync retries

create table if not exists public.erpnext_push_queue (
  id uuid primary key default gen_random_uuid(),
  project_uri text not null,
  boq_item_uri text not null,
  payload jsonb not null default '{}'::jsonb,
  response jsonb not null default '{}'::jsonb,
  attempts integer not null default 0,
  status text not null default 'queued',
  created_at timestamptz not null default now()
);

create index if not exists idx_erpnext_push_queue_status on public.erpnext_push_queue(status);
create index if not exists idx_erpnext_push_queue_project_uri on public.erpnext_push_queue(project_uri);
create index if not exists idx_erpnext_push_queue_boq_item_uri on public.erpnext_push_queue(boq_item_uri);
create index if not exists idx_erpnext_push_queue_created_at on public.erpnext_push_queue(created_at);
