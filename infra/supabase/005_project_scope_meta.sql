-- Persist register step-2 metadata on projects.
alter table if exists projects
  add column if not exists km_interval int default 20,
  add column if not exists inspection_types jsonb default '[]'::jsonb,
  add column if not exists contract_segs jsonb default '[]'::jsonb,
  add column if not exists structures jsonb default '[]'::jsonb;

update projects
set
  km_interval = coalesce(km_interval, 20),
  inspection_types = coalesce(inspection_types, '[]'::jsonb),
  contract_segs = coalesce(contract_segs, '[]'::jsonb),
  structures = coalesce(structures, '[]'::jsonb);
