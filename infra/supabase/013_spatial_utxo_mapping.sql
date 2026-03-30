-- Spatial UTXO mapping table for digital twin indexing.

create table if not exists public.proof_spatial_map (
  id uuid primary key default gen_random_uuid(),
  proof_id text not null unique,
  project_uri text not null,
  boq_item_uri text not null default '',
  bim_id text not null default '',
  label text not null default '',
  coordinate jsonb not null default '{}'::jsonb,
  spatial_fingerprint text not null,
  status text not null default 'in_progress',
  updated_at timestamptz not null default now()
);

create index if not exists idx_proof_spatial_map_project_uri
  on public.proof_spatial_map(project_uri);

create index if not exists idx_proof_spatial_map_bim_id
  on public.proof_spatial_map(bim_id);

create index if not exists idx_proof_spatial_map_boq_item_uri
  on public.proof_spatial_map(boq_item_uri);

create index if not exists idx_proof_spatial_map_status
  on public.proof_spatial_map(status);

create index if not exists idx_proof_spatial_map_coordinate_gin
  on public.proof_spatial_map using gin (coordinate);
