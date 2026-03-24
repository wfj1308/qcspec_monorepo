-- GitPeg auto-registration mirror tables for Supabase
-- Source: handoff-core/deploy/sql/coord_gitpeg_autoreg.sql

create table if not exists public.coord_gitpeg_project_registry (
  id uuid primary key default gen_random_uuid(),
  project_code text not null unique,
  project_name text not null,
  site_code text not null,
  site_name text not null,
  namespace_uri text not null,
  project_uri text not null,
  site_uri text not null,
  executor_uri text,
  gitpeg_status text not null default 'active',
  source_system text not null default 'erpnext',
  updated_at timestamptz not null default now()
);

create index if not exists idx_coord_gitpeg_project_registry_site_code
  on public.coord_gitpeg_project_registry(site_code);

create index if not exists idx_coord_gitpeg_project_registry_updated_at
  on public.coord_gitpeg_project_registry(updated_at desc);

create table if not exists public.coord_gitpeg_nodes (
  id uuid primary key default gen_random_uuid(),
  uri text not null unique,
  uri_type text not null,
  project_code text not null,
  display_name text not null,
  namespace_uri text not null,
  source_system text not null default 'erpnext',
  updated_at timestamptz not null default now()
);

create index if not exists idx_coord_gitpeg_nodes_project_code
  on public.coord_gitpeg_nodes(project_code);

create index if not exists idx_coord_gitpeg_nodes_uri_type
  on public.coord_gitpeg_nodes(uri_type);

create index if not exists idx_coord_gitpeg_nodes_updated_at
  on public.coord_gitpeg_nodes(updated_at desc);
