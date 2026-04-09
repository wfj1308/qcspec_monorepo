-- SignPeg executor + signature lifecycle tables
-- P0: executor registry, holder history, trip ledger, doc states, delegation, railpact settlements

create extension if not exists pgcrypto;

create table if not exists public.san_executors (
  id uuid primary key default gen_random_uuid(),
  executor_id text unique,
  executor_uri text not null unique,
  executor_type text not null default 'human',
  name text not null,
  org_uri text not null,
  certificates jsonb not null default '[]'::jsonb,
  skills jsonb not null default '[]'::jsonb,
  energy jsonb not null default '{}'::jsonb,
  capacity jsonb not null default '{}'::jsonb,
  requires jsonb not null default '[]'::jsonb,
  used_by jsonb not null default '[]'::jsonb,
  tool_spec jsonb,
  org_spec jsonb,
  business_license_file text not null default '',
  registration_proof text not null default '',
  proof_history jsonb not null default '[]'::jsonb,
  status text not null default 'available',
  registered_at timestamptz not null default now(),
  last_active timestamptz not null default now(),
  trip_count integer not null default 0,
  proof_count integer not null default 0,
  holder_name text not null,
  holder_id text not null,
  holder_since timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint san_executors_type_ck check (executor_type in ('human', 'machine', 'tool', 'ai', 'org')),
  constraint san_executors_status_ck check (status in ('active', 'inactive', 'suspended', 'available', 'busy', 'offline', 'in_use', 'maintenance', 'depleted', 'retired'))
);

alter table if exists public.san_executors add column if not exists executor_id text unique;
alter table if exists public.san_executors add column if not exists executor_type text not null default 'human';
alter table if exists public.san_executors add column if not exists certificates jsonb not null default '[]'::jsonb;
alter table if exists public.san_executors add column if not exists registration_proof text not null default '';
alter table if exists public.san_executors add column if not exists proof_history jsonb not null default '[]'::jsonb;
alter table if exists public.san_executors add column if not exists last_active timestamptz not null default now();
alter table if exists public.san_executors add column if not exists requires jsonb not null default '[]'::jsonb;
alter table if exists public.san_executors add column if not exists used_by jsonb not null default '[]'::jsonb;
alter table if exists public.san_executors add column if not exists tool_spec jsonb;
alter table if exists public.san_executors add column if not exists org_spec jsonb;
alter table if exists public.san_executors add column if not exists business_license_file text not null default '';

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conname = 'san_executors_status_ck'
      and conrelid = 'public.san_executors'::regclass
  ) then
    alter table public.san_executors drop constraint san_executors_status_ck;
  end if;
  alter table public.san_executors
    add constraint san_executors_status_ck
    check (status in ('active', 'inactive', 'suspended', 'available', 'busy', 'offline', 'in_use', 'maintenance', 'depleted', 'retired'));
exception when others then
  null;
end $$;

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conname = 'san_executors_type_ck'
      and conrelid = 'public.san_executors'::regclass
  ) then
    alter table public.san_executors drop constraint san_executors_type_ck;
  end if;
  alter table public.san_executors
    add constraint san_executors_type_ck
    check (executor_type in ('human', 'machine', 'tool', 'ai', 'org'));
exception when others then
  null;
end $$;

create index if not exists idx_san_executors_org_uri on public.san_executors(org_uri);
create index if not exists idx_san_executors_status on public.san_executors(status);
create index if not exists idx_san_executors_executor_type on public.san_executors(executor_type);
create index if not exists idx_san_executors_executor_id on public.san_executors(executor_id);

create table if not exists public.san_executor_holders (
  id uuid primary key default gen_random_uuid(),
  executor_uri text not null,
  holder_name text not null,
  holder_id text not null,
  holder_since timestamptz not null,
  changed_at timestamptz not null default now(),
  reason text not null default 'holder_change'
);

create index if not exists idx_san_executor_holders_uri on public.san_executor_holders(executor_uri);
create index if not exists idx_san_executor_holders_changed_at on public.san_executor_holders(changed_at desc);

create table if not exists public.san_delegations (
  id uuid primary key default gen_random_uuid(),
  delegation_uri text not null unique,
  from_executor_uri text not null,
  to_executor_uri text not null,
  scope jsonb not null default '[]'::jsonb,
  valid_from timestamptz not null,
  valid_until timestamptz not null,
  proof_doc text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  constraint san_delegations_status_ck check (status in ('active', 'revoked', 'expired'))
);

create index if not exists idx_san_delegations_from_to on public.san_delegations(from_executor_uri, to_executor_uri);
create index if not exists idx_san_delegations_valid_until on public.san_delegations(valid_until);

create table if not exists public.san_executor_alerts (
  id uuid primary key default gen_random_uuid(),
  executor_id text not null default '',
  executor_uri text not null,
  org_uri text not null default '',
  alert_type text not null,
  message text not null,
  certificate jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_san_executor_alerts_executor_id on public.san_executor_alerts(executor_id);
create index if not exists idx_san_executor_alerts_alert_type on public.san_executor_alerts(alert_type);

create table if not exists public.gate_trips (
  id uuid primary key default gen_random_uuid(),
  trip_uri text not null unique,
  doc_id text not null,
  body_hash text not null,
  executor_uri text not null,
  executor_name text not null,
  dto_role text not null,
  trip_role text not null,
  action text not null,
  sig_data text not null,
  signed_at timestamptz not null,
  verified boolean not null default true,
  delegation_uri text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_gate_trips_doc_id on public.gate_trips(doc_id);
create index if not exists idx_gate_trips_executor_uri on public.gate_trips(executor_uri);
create index if not exists idx_gate_trips_signed_at on public.gate_trips(signed_at desc);

create table if not exists public.docpeg_states (
  id uuid primary key default gen_random_uuid(),
  doc_id text not null unique,
  lifecycle_stage text not null default 'submitted',
  all_signed boolean not null default false,
  next_required text not null default '',
  next_executor text not null default '',
  state_data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists idx_docpeg_states_stage on public.docpeg_states(lifecycle_stage);

create table if not exists public.railpact_settlements (
  id uuid primary key default gen_random_uuid(),
  trip_uri text not null,
  executor_uri text not null,
  doc_id text not null,
  amount numeric(18, 6) not null default 0,
  energy_delta integer not null default 1,
  settled_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists idx_railpact_settlements_trip_uri on public.railpact_settlements(trip_uri);
create index if not exists idx_railpact_settlements_executor_uri on public.railpact_settlements(executor_uri);
create index if not exists idx_railpact_settlements_settled_at on public.railpact_settlements(settled_at desc);

create table if not exists public.san_tools (
  id uuid primary key default gen_random_uuid(),
  tool_id text not null unique,
  tool_uri text not null unique,
  tool_name text not null,
  tool_code text not null,
  tool_type text not null,
  owner_type text not null default 'org',
  owner_uri text not null,
  project_uri text not null default '',
  certificates jsonb not null default '[]'::jsonb,
  tool_energy jsonb,
  consumable_spec jsonb,
  reusable_spec jsonb,
  capability_spec jsonb,
  status text not null default 'available',
  use_history jsonb not null default '[]'::jsonb,
  registration_proof text not null default '',
  registered_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  constraint san_tools_type_ck check (tool_type in ('consumable', 'reusable', 'capability')),
  constraint san_tools_owner_type_ck check (owner_type in ('executor', 'pool', 'org')),
  constraint san_tools_status_ck check (status in ('available', 'in_use', 'maintenance', 'depleted', 'retired', 'suspended'))
);

create index if not exists idx_san_tools_owner_uri on public.san_tools(owner_uri);
create index if not exists idx_san_tools_project_uri on public.san_tools(project_uri);
create index if not exists idx_san_tools_status on public.san_tools(status);
create index if not exists idx_san_tools_type on public.san_tools(tool_type);

create table if not exists public.san_tool_alerts (
  id uuid primary key default gen_random_uuid(),
  tool_id text not null,
  tool_uri text not null,
  owner_uri text not null,
  alert_type text not null,
  message text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_san_tool_alerts_tool_id on public.san_tool_alerts(tool_id);
create index if not exists idx_san_tool_alerts_alert_type on public.san_tool_alerts(alert_type);
create index if not exists idx_san_tool_alerts_created_at on public.san_tool_alerts(created_at desc);
