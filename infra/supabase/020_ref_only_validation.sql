-- Post-migration validation for ref-only storage.
-- Run after:
--   018_specir_registry.sql
--   019_project_ref_only_backfill.sql

create or replace view public.proof_utxo_ref_only_audit as
select
  p.proof_id,
  p.project_uri,
  p.proof_type,
  p.created_at,
  p.state_data,
  nullif(btrim(coalesce(p.state_data->>'ref_gate_uri', '')), '') as ref_gate_uri,
  nullif(btrim(coalesce(p.state_data->>'ref_spec_uri', '')), '') as ref_spec_uri,
  nullif(btrim(coalesce(p.state_data->>'ref_spec_dict_uri', '')), '') as ref_spec_dict_uri,
  nullif(btrim(coalesce(p.state_data->>'ref_spec_item_uri', '')), '') as ref_spec_item_uri,
  nullif(btrim(coalesce(p.state_data->>'ref_spu_uri', '')), '') as ref_spu_uri,
  nullif(btrim(coalesce(p.state_data->>'ref_quota_uri', '')), '') as ref_quota_uri,
  nullif(btrim(coalesce(p.state_data->>'ref_meter_rule_uri', '')), '') as ref_meter_rule_uri,
  (p.state_data ? 'linked_gate_rules') as has_legacy_gate_rules,
  (p.state_data ? 'spu_formula') as has_legacy_spu_formula,
  (p.state_data ? 'spu_form_schema') as has_legacy_spu_form_schema,
  (p.state_data ? 'spu_geometry') as has_legacy_spu_geometry
from public.proof_utxo p;

create or replace view public.proof_utxo_ref_only_summary as
select
  coalesce(project_uri, '') as project_uri,
  count(*) as total_rows,
  count(*) filter (where ref_gate_uri is not null) as rows_with_ref_gate,
  count(*) filter (where ref_spu_uri is not null) as rows_with_ref_spu,
  count(*) filter (where has_legacy_gate_rules) as rows_with_legacy_gate_rules,
  count(*) filter (where has_legacy_spu_formula or has_legacy_spu_form_schema or has_legacy_spu_geometry) as rows_with_legacy_spu_payload
from public.proof_utxo_ref_only_audit
group by coalesce(project_uri, '')
order by project_uri;

create or replace view public.proof_utxo_ref_missing_specir as
select
  a.proof_id,
  a.project_uri,
  a.proof_type,
  a.created_at,
  a.ref_gate_uri,
  a.ref_spu_uri,
  a.ref_quota_uri,
  a.ref_meter_rule_uri,
  (a.ref_gate_uri is not null and g.uri is null) as missing_ref_gate_uri,
  (a.ref_spu_uri is not null and s.uri is null) as missing_ref_spu_uri,
  (a.ref_quota_uri is not null and q.uri is null) as missing_ref_quota_uri,
  (a.ref_meter_rule_uri is not null and m.uri is null) as missing_ref_meter_rule_uri
from public.proof_utxo_ref_only_audit a
left join public.specir_objects g on g.uri = a.ref_gate_uri
left join public.specir_objects s on s.uri = a.ref_spu_uri
left join public.specir_objects q on q.uri = a.ref_quota_uri
left join public.specir_objects m on m.uri = a.ref_meter_rule_uri;

create or replace view public.proof_utxo_ref_missing_specir_summary as
select
  coalesce(project_uri, '') as project_uri,
  count(*) as total_rows,
  count(*) filter (where missing_ref_gate_uri) as missing_ref_gate_uri_rows,
  count(*) filter (where missing_ref_spu_uri) as missing_ref_spu_uri_rows,
  count(*) filter (where missing_ref_quota_uri) as missing_ref_quota_uri_rows,
  count(*) filter (where missing_ref_meter_rule_uri) as missing_ref_meter_rule_uri_rows
from public.proof_utxo_ref_missing_specir
group by coalesce(project_uri, '')
order by project_uri;

do $$
declare
  v_total bigint := 0;
  v_ref_gate bigint := 0;
  v_ref_spu bigint := 0;
  v_legacy_gate bigint := 0;
  v_legacy_spu bigint := 0;
  v_missing_ref_gate bigint := 0;
  v_missing_ref_spu bigint := 0;
  v_missing_ref_quota bigint := 0;
  v_missing_ref_meter_rule bigint := 0;
begin
  select count(*) into v_total from public.proof_utxo_ref_only_audit;
  select count(*) into v_ref_gate from public.proof_utxo_ref_only_audit where ref_gate_uri is not null;
  select count(*) into v_ref_spu from public.proof_utxo_ref_only_audit where ref_spu_uri is not null;
  select count(*) into v_legacy_gate from public.proof_utxo_ref_only_audit where has_legacy_gate_rules;
  select count(*) into v_legacy_spu
  from public.proof_utxo_ref_only_audit
  where has_legacy_spu_formula or has_legacy_spu_form_schema or has_legacy_spu_geometry;
  select count(*) into v_missing_ref_gate from public.proof_utxo_ref_missing_specir where missing_ref_gate_uri;
  select count(*) into v_missing_ref_spu from public.proof_utxo_ref_missing_specir where missing_ref_spu_uri;
  select count(*) into v_missing_ref_quota from public.proof_utxo_ref_missing_specir where missing_ref_quota_uri;
  select count(*) into v_missing_ref_meter_rule from public.proof_utxo_ref_missing_specir where missing_ref_meter_rule_uri;

  raise notice 'Ref-Only Audit Total Rows: %', v_total;
  raise notice 'Rows with ref_gate_uri: %', v_ref_gate;
  raise notice 'Rows with ref_spu_uri: %', v_ref_spu;
  raise notice 'Rows still carrying linked_gate_rules: %', v_legacy_gate;
  raise notice 'Rows still carrying spu_* payload: %', v_legacy_spu;
  raise notice 'Rows with missing ref_gate_uri registration in specir_objects: %', v_missing_ref_gate;
  raise notice 'Rows with missing ref_spu_uri registration in specir_objects: %', v_missing_ref_spu;
  raise notice 'Rows with missing ref_quota_uri registration in specir_objects: %', v_missing_ref_quota;
  raise notice 'Rows with missing ref_meter_rule_uri registration in specir_objects: %', v_missing_ref_meter_rule;
end $$;

-- Quick manual checks:
-- select * from public.proof_utxo_ref_only_summary;
-- select proof_id, project_uri, ref_gate_uri, has_legacy_gate_rules
-- from public.proof_utxo_ref_only_audit
-- where has_legacy_gate_rules
-- limit 50;
-- select proof_id, project_uri, ref_spu_uri, has_legacy_spu_formula, has_legacy_spu_form_schema, has_legacy_spu_geometry
-- from public.proof_utxo_ref_only_audit
-- where has_legacy_spu_formula or has_legacy_spu_form_schema or has_legacy_spu_geometry
-- limit 50;
-- select * from public.proof_utxo_ref_missing_specir_summary;
-- select *
-- from public.proof_utxo_ref_missing_specir
-- where missing_ref_gate_uri or missing_ref_spu_uri or missing_ref_quota_uri or missing_ref_meter_rule_uri
-- order by created_at desc
-- limit 50;
