-- Audit view for Ultimate SPU schema completeness in SpecIR registry.
-- Non-destructive: reports invalid rows without blocking writes.

create or replace view public.specir_spu_schema_audit as
select
  s.uri,
  s.version,
  s.title,
  s.status,
  s.updated_at,
  (jsonb_typeof(s.content) = 'object') as is_object,
  (s.content ? 'identity') as has_identity,
  (s.content ? 'measure_rule') as has_measure_rule,
  (s.content ? 'consumption') as has_consumption,
  (s.content ? 'qc_gate') as has_qc_gate,
  (coalesce(s.content->>'schema', '') = 'qcspec.specir.spu.ultimate') as schema_id_ok,
  (s.content ? 'schema_modules') as has_schema_modules,
  (
    jsonb_typeof(s.content) = 'object'
    and s.content ? 'identity'
    and s.content ? 'measure_rule'
    and s.content ? 'consumption'
    and s.content ? 'qc_gate'
    and coalesce(s.content->>'schema', '') = 'qcspec.specir.spu.ultimate'
  ) as schema_ok
from public.specir_objects s
where s.kind = 'spu';

create or replace view public.specir_spu_schema_audit_summary as
select
  count(*) as total_spu_rows,
  count(*) filter (where schema_ok) as valid_rows,
  count(*) filter (where not schema_ok) as invalid_rows
from public.specir_spu_schema_audit;

do $$
declare
  v_total bigint := 0;
  v_valid bigint := 0;
  v_invalid bigint := 0;
begin
  select total_spu_rows, valid_rows, invalid_rows
  into v_total, v_valid, v_invalid
  from public.specir_spu_schema_audit_summary;

  raise notice 'SpecIR SPU schema audit total: %', v_total;
  raise notice 'SpecIR SPU schema valid rows: %', v_valid;
  raise notice 'SpecIR SPU schema invalid rows: %', v_invalid;
end $$;

-- Quick checks:
-- select * from public.specir_spu_schema_audit_summary;
-- select uri, schema_ok, has_identity, has_measure_rule, has_consumption, has_qc_gate
-- from public.specir_spu_schema_audit
-- where not schema_ok
-- order by updated_at desc;
