-- Mobile runtime persistence tables (QCSpec mobile workflow)

create table if not exists public.mobile_workorders (
  component_code text primary key,
  component_name text not null default '',
  v_uri text not null default '',
  steps jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists public.mobile_submissions (
  submission_id text primary key,
  component_code text not null,
  v_uri text not null default '',
  step_key text not null default '',
  step_name text not null default '',
  result text not null default '',
  proof_id text not null default '',
  executor_uri text not null default '',
  device_id text not null default '',
  timestamp timestamptz not null default now(),
  form_data jsonb not null default '{}'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  signature jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.mobile_anchors (
  anchor_id text primary key,
  trip_id text not null default '',
  hash text not null,
  location jsonb not null default '{}'::jsonb,
  timestamp timestamptz not null default now(),
  anchored_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_mobile_submissions_component on public.mobile_submissions(component_code);
create index if not exists idx_mobile_submissions_timestamp on public.mobile_submissions(timestamp desc);
create index if not exists idx_mobile_anchors_trip on public.mobile_anchors(trip_id);
create index if not exists idx_mobile_anchors_hash on public.mobile_anchors(hash);

