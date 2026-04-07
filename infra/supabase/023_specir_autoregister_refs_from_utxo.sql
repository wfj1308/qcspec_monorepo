-- Auto-register ref URIs from proof_utxo.state_data into specir_objects.
-- Run after:
--   018_specir_registry.sql
--   019_project_ref_only_backfill.sql
-- Optional before 021_ref_only_assertions.sql to close long-tail refs.

create extension if not exists pgcrypto;

create or replace function public.specir_kind_from_uri(uri text)
returns text
language sql
immutable
as $$
  select case
    when coalesce(uri, '') like 'v://norm/gate/%' then 'gate'
    when coalesce(uri, '') like 'v://norm/spec-rule/%' then 'spec_rule'
    when coalesce(uri, '') like 'v://norm/specdict/%#%' then 'spec_item'
    when coalesce(uri, '') like 'v://norm/specdict/%' then 'spec_dict'
    when coalesce(uri, '') like 'v://norm/spu/%' then 'spu'
    when coalesce(uri, '') like 'v://norm/quota/%' then 'quota'
    when coalesce(uri, '') like 'v://norm/meter-rule/%' then 'meter_rule'
    when coalesce(uri, '') like 'v://norm/%' then 'spec_ref'
    else 'unknown'
  end;
$$;

with raw_refs as (
  select nullif(btrim(coalesce(state_data->>'ref_gate_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_spec_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_spec_dict_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_spec_item_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_spu_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_quota_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_meter_rule_uri', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_spu', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_quota', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(coalesce(state_data->>'ref_meter_rule', '')), '') as uri from public.proof_utxo
  union all
  select nullif(btrim(value), '') as uri
  from public.proof_utxo p
  cross join lateral jsonb_array_elements_text(
    case
      when jsonb_typeof(p.state_data->'ref_gate_uris') = 'array' then p.state_data->'ref_gate_uris'
      else '[]'::jsonb
    end
  )
),
normalized as (
  select distinct uri
  from raw_refs
  where uri is not null
    and uri like 'v://%'
),
missing as (
  select n.uri
  from normalized n
  left join public.specir_objects s on s.uri = n.uri
  where s.uri is null
),
payloads as (
  select
    m.uri,
    k.kind,
    coalesce(nullif(split_part(m.uri, '@', 2), ''), 'v1') as version,
    regexp_replace(split_part(split_part(m.uri, '#', 1), '@', 1), '^.*/', '') as title_token,
    case
      when k.kind = 'spu' then
        jsonb_build_object(
          'schema', 'qcspec.specir.spu.ultimate',
          'schema_version', '1.0.0',
          'identity', jsonb_build_object(
            'spu_uri', m.uri,
            'sovereignty_uri', 'v://norm',
            'industry', 'Highway',
            'standard_codes', '[]'::jsonb,
            'category_path', to_jsonb(regexp_split_to_array(split_part(split_part(m.uri, '@', 1), '/spu/', 2), '/')),
            'aliases', '[]'::jsonb,
            'authority_refs', '[]'::jsonb
          ),
          'measure_rule', jsonb_build_object(
            'unit', '',
            'payable_unit', '',
            'meter_rule_ref', '',
            'statement', 'Auto-registered from proof_utxo ref scan; refine before production use.',
            'algorithm', jsonb_build_object(
              'key', 'auto-register-placeholder',
              'expression', 'approved_quantity',
              'description', '',
              'parameters', '{}'::jsonb,
              'exclusion_rules', '[]'::jsonb
            ),
            'settlement_clauses', '[]'::jsonb,
            'examples', '[]'::jsonb
          ),
          'consumption', jsonb_build_object(
            'unit_basis', '',
            'quota_ref', '',
            'materials', '[]'::jsonb,
            'machinery', '[]'::jsonb,
            'labor', '[]'::jsonb,
            'notes', '[]'::jsonb
          ),
          'qc_gate', jsonb_build_object(
            'strategy', 'all_pass',
            'fail_action', 'trigger_review_trip',
            'gate_refs', '[]'::jsonb,
            'rules', '[]'::jsonb,
            'checklist', '[]'::jsonb
          ),
          'extensions', jsonb_build_object(
            'auto_registered', true,
            'source', 'proof_utxo_ref_scan',
            'uri', m.uri
          ),
          'schema_modules', jsonb_build_array('Identity', 'MeasureRule', 'Consumption', 'QCGate'),
          'label', regexp_replace(split_part(split_part(m.uri, '#', 1), '@', 1), '^.*/', ''),
          'unit', '',
          'norm_refs', '[]'::jsonb,
          'gate_refs', '[]'::jsonb,
          'quota_ref', '',
          'meter_rule_ref', '',
          'quota_refs', '[]'::jsonb,
          'meter_rule_refs', '[]'::jsonb
        )
      else
        jsonb_build_object(
          'auto_registered', true,
          'source', 'proof_utxo_ref_scan',
          'uri', m.uri
        )
    end as content,
    jsonb_build_object(
      'seed', '023',
      'source', 'proof_utxo_ref_scan'
    ) as metadata
  from missing m
  cross join lateral (
    select public.specir_kind_from_uri(m.uri) as kind
  ) k
)
insert into public.specir_objects (
  uri,
  kind,
  version,
  title,
  content,
  content_hash,
  status,
  metadata
)
select
  p.uri,
  p.kind,
  p.version,
  coalesce(nullif(p.title_token, ''), p.kind) as title,
  p.content,
  encode(digest(convert_to(coalesce(p.content::text, ''), 'utf8'), 'sha256'), 'hex') as content_hash,
  'active' as status,
  p.metadata
from payloads p
on conflict (uri) do nothing;

do $$
declare
  v_inserted bigint := 0;
begin
  select count(*)
  into v_inserted
  from public.specir_objects
  where (metadata->>'seed') = '023'
    and (metadata->>'source') = 'proof_utxo_ref_scan';
  raise notice 'SpecIR auto-registration scanned refs; total rows marked by seed=023: %', v_inserted;
end $$;
