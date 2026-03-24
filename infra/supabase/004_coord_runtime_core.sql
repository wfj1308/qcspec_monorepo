-- CoordOS stage-1 runtime mirror (Odoo/ERP -> Supabase)
-- Source: handoff-core/integrations/odoo-bridge/adapters-integrations-odoo/migrations/supabase/001_coord_runtime_core.sql
-- Scope: skills / containers / shells / executors + 2 M2M + migration runs.

create extension if not exists pgcrypto;

create table if not exists public.coord_skills (
  id uuid primary key default gen_random_uuid(),
  legacy_odoo_id bigint unique,
  name text not null,
  registry_uri text,
  version text,
  description text,
  energy_cost numeric(18, 6) default 0,
  enabled boolean not null default true,
  spu_kind text,
  trip_role text,
  smu_kind text,
  semantic_code text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_coord_skills_registry_uri on public.coord_skills(registry_uri);
create index if not exists idx_coord_skills_name on public.coord_skills(name);

create table if not exists public.coord_containers (
  id uuid primary key default gen_random_uuid(),
  legacy_odoo_id bigint unique,
  name text not null,
  registry_uri text,
  version text,
  capability_name text,
  capability text,
  description text,
  capacity_per_hour numeric(18, 6),
  cycle_time numeric(18, 6),
  energy_kw numeric(18, 6),
  operator_required integer,
  unit text,
  capability_code text,
  spu_kind text,
  trip_role text,
  smu_kind text,
  semantic_code text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_coord_containers_registry_uri on public.coord_containers(registry_uri);
create index if not exists idx_coord_containers_capability_name on public.coord_containers(capability_name);

create table if not exists public.coord_shells (
  id uuid primary key default gen_random_uuid(),
  legacy_odoo_id bigint unique,
  name text not null,
  shell_type text not null,
  version text,
  capability text,
  registry_uri text,
  device_id text,
  platform text,
  status text,
  spu_kind text,
  trip_role text,
  smu_kind text,
  semantic_code text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  constraint coord_shells_shell_type_ck check (shell_type in ('android', 'odoo', 'pwa', 'ai_agent')),
  constraint coord_shells_status_ck check (status is null or status in ('draft', 'online', 'offline', 'disabled'))
);

create unique index if not exists uq_coord_shells_device_registry
  on public.coord_shells(device_id, registry_uri);
create index if not exists idx_coord_shells_registry_uri on public.coord_shells(registry_uri);

create table if not exists public.coord_executors (
  id uuid primary key default gen_random_uuid(),
  legacy_odoo_id bigint unique,
  name text not null,
  executor_type text not null,
  shell_id uuid references public.coord_shells(id) on delete set null,
  container_id uuid references public.coord_containers(id) on delete set null,
  wallet_balance numeric(18, 6) default 0,
  energy_balance numeric(18, 6) default 0,
  status text,
  spu_kind text,
  trip_role text,
  smu_kind text,
  semantic_code text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  constraint coord_executors_type_ck check (executor_type in ('person', 'ai', 'device', 'robot')),
  constraint coord_executors_status_ck check (status is null or status in ('idle', 'busy', 'offline'))
);

create index if not exists idx_coord_executors_shell_id on public.coord_executors(shell_id);
create index if not exists idx_coord_executors_container_id on public.coord_executors(container_id);

create table if not exists public.coord_shell_skills (
  shell_id uuid not null references public.coord_shells(id) on delete cascade,
  skill_id uuid not null references public.coord_skills(id) on delete cascade,
  primary key (shell_id, skill_id)
);

create table if not exists public.coord_container_skills (
  container_id uuid not null references public.coord_containers(id) on delete cascade,
  skill_id uuid not null references public.coord_skills(id) on delete cascade,
  primary key (container_id, skill_id)
);

create table if not exists public.coord_migration_runs (
  id uuid primary key default gen_random_uuid(),
  migration_name text not null,
  source_system text not null default 'odoo',
  status text not null default 'started',
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  summary jsonb not null default '{}'::jsonb,
  error_text text
);

create index if not exists idx_coord_migration_runs_name
  on public.coord_migration_runs(migration_name);
