-- Extend SPU<->BOQ mapping table with default_quantity_per_unit.
-- This field represents how much SPU capability is consumed per BOQ unit.

alter table if exists public.spu_boq_mappings
  add column if not exists default_quantity_per_unit numeric(18,6) not null default 1.0;

update public.spu_boq_mappings
set default_quantity_per_unit = coalesce(default_quantity_per_unit, weight, 1.0)
where default_quantity_per_unit is null;

create or replace view public.spu_boq_mapping_summary as
select
  coalesce(project_uri, '') as project_uri,
  count(*) as mapping_rows,
  count(distinct boq_v_uri) as boq_item_count,
  count(distinct spu_uri) as spu_count,
  count(*) filter (where capability_type = 'quantity_check') as quantity_check_rows,
  count(*) filter (where capability_type = 'material_spec') as material_spec_rows,
  count(*) filter (where capability_type = 'construction_method') as construction_method_rows,
  coalesce(avg(default_quantity_per_unit), 0) as avg_default_quantity_per_unit
from public.spu_boq_mappings
group by coalesce(project_uri, '')
order by project_uri;

