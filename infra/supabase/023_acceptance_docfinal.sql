-- Acceptance + DocFinal closure tables (桥施64表成品验收闭环)

alter table if exists public.gate_trips
  add column if not exists metadata jsonb not null default '{}'::jsonb;

create table if not exists public.docpeg_acceptances (
  id uuid primary key default gen_random_uuid(),
  acceptance_id text not null unique,
  component_uri text not null,
  doc_id text not null,
  status text not null default 'conditional',
  latest_trip_uri text not null default '',
  pre_doc_ids jsonb not null default '[]'::jsonb,
  conclusion jsonb not null default '{}'::jsonb,
  on_approved jsonb not null default '{}'::jsonb,
  pre_conditions_passed boolean not null default false,
  final_proof_uri text not null default '',
  boq_status text not null default '',
  archived_to_docfinal boolean not null default false,
  component_locked boolean not null default false,
  pre_rejection_trip_uri text not null default '',
  updated_at timestamptz not null default now(),
  constraint docpeg_acceptances_status_ck check (status in ('qualified', 'rejected', 'conditional'))
);

create index if not exists idx_docpeg_acceptances_component on public.docpeg_acceptances(component_uri);
create index if not exists idx_docpeg_acceptances_doc_id on public.docpeg_acceptances(doc_id);
create index if not exists idx_docpeg_acceptances_status on public.docpeg_acceptances(status);

create table if not exists public.docpeg_acceptance_conditions (
  id uuid primary key default gen_random_uuid(),
  acceptance_id text not null,
  condition_id text not null,
  content text not null,
  status text not null default 'pending',
  signed_by text not null default '',
  signed_at timestamptz null,
  updated_at timestamptz not null default now(),
  unique (acceptance_id, condition_id),
  constraint docpeg_acceptance_conditions_status_ck check (status in ('pending', 'signed', 'waived'))
);

create index if not exists idx_docpeg_acceptance_conditions_acceptance on public.docpeg_acceptance_conditions(acceptance_id);

create table if not exists public.docpeg_component_locks (
  id uuid primary key default gen_random_uuid(),
  component_uri text not null unique,
  acceptance_id text not null,
  locked_at timestamptz not null default now(),
  lock_reason text not null default 'acceptance_approved'
);

create table if not exists public.docfinal_archives (
  id uuid primary key default gen_random_uuid(),
  acceptance_id text not null unique,
  component_uri text not null,
  doc_id text not null,
  final_proof_uri text not null default '',
  docfinal_uri text not null default '',
  archived_at timestamptz not null default now()
);

create index if not exists idx_docfinal_archives_component on public.docfinal_archives(component_uri);

create table if not exists public.docpeg_boq_status (
  id uuid primary key default gen_random_uuid(),
  acceptance_id text not null,
  doc_id text not null,
  boq_item_code text not null,
  status text not null default 'PROOF_VERIFIED',
  updated_at timestamptz not null default now(),
  unique (acceptance_id, boq_item_code)
);

create index if not exists idx_docpeg_boq_status_doc_id on public.docpeg_boq_status(doc_id);

create table if not exists public.docpeg_rectification_notices (
  id uuid primary key default gen_random_uuid(),
  acceptance_id text not null,
  doc_id text not null,
  component_uri text not null,
  rejection_trip_uri text not null,
  reason text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_docpeg_rectification_notices_acceptance on public.docpeg_rectification_notices(acceptance_id);
