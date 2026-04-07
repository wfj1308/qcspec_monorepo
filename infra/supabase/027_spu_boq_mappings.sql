-- SPU <-> BOQItem mapping registry
-- Purpose:
--   After BOQ scan creates BOQItem + initial UTXO, persist explicit SPU mapping
--   relationships so execution/gate/reporting can query by capability.

create table if not exists public.spu_boq_mappings (
  id uuid primary key default gen_random_uuid(),
  mapping_id text not null unique,
  project_uri text not null default '',
  boq_item_id text not null default '',
  boq_v_uri text not null default '',
  bridge_uri text,
  spu_uri text not null default '',
  capability_type text not null default 'quantity_check',
  norm_ref text not null default '',
  weight numeric(18,6) not null default 1.0,
  proof_id text not null default '',
  proof_hash text not null default '',
  source_file text not null default '',
  created_at timestamptz not null default now()
);

create unique index if not exists uq_spu_boq_mappings_logical
  on public.spu_boq_mappings (project_uri, boq_v_uri, spu_uri, capability_type);

create index if not exists idx_spu_boq_mappings_project_uri
  on public.spu_boq_mappings (project_uri);

create index if not exists idx_spu_boq_mappings_boq_item_id
  on public.spu_boq_mappings (boq_item_id);

create index if not exists idx_spu_boq_mappings_bridge_uri
  on public.spu_boq_mappings (bridge_uri);

create index if not exists idx_spu_boq_mappings_spu_uri
  on public.spu_boq_mappings (spu_uri);

create or replace view public.spu_boq_mapping_summary as
select
  coalesce(project_uri, '') as project_uri,
  count(*) as mapping_rows,
  count(distinct boq_v_uri) as boq_item_count,
  count(distinct spu_uri) as spu_count,
  count(*) filter (where capability_type = 'quantity_check') as quantity_check_rows,
  count(*) filter (where capability_type = 'material_spec') as material_spec_rows,
  count(*) filter (where capability_type = 'construction_method') as construction_method_rows
from public.spu_boq_mappings
group by coalesce(project_uri, '')
order by project_uri;

-- Quick checks:
-- select * from public.spu_boq_mapping_summary;
-- select project_uri, boq_item_id, boq_v_uri, spu_uri, capability_type, norm_ref, proof_id
-- from public.spu_boq_mappings
-- order by created_at desc
-- limit 100;

