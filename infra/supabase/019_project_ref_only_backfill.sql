-- Backfill legacy proof_utxo.state_data into ref-only layout.
-- Goal:
-- 1) Populate ref_gate/ref_spec refs from legacy linked_* fields.
-- 2) Populate ref_spu/ref_quota/ref_meter refs from legacy spu_* fields.
-- 3) Prune duplicated heavy fields after refs are present.

create or replace function public.specir_safe_ref_token(raw text)
returns text
language sql
immutable
as $$
  select left(
    regexp_replace(
      trim(both '-/' from regexp_replace(
        replace(replace(replace(replace(coalesce(raw, ''), '::', '/'), '#', '/'), '@', '-'), ' ', ''),
        '[^0-9A-Za-z._/-]+',
        '-',
        'g'
      )),
      '/{2,}',
      '/',
      'g'
    ),
    180
  );
$$;

-- 1) Backfill gate/spec refs.
with source_rows as (
  select
    p.proof_id,
    p.state_data,
    nullif(btrim(coalesce(p.state_data->>'linked_gate_id', '')), '') as linked_gate_id,
    nullif(btrim(coalesce(p.state_data->>'linked_spec_uri', '')), '') as linked_spec_uri,
    nullif(btrim(coalesce(p.state_data->>'spec_dict_key', '')), '') as spec_dict_key,
    nullif(btrim(coalesce(p.state_data->>'spec_item', '')), '') as spec_item,
    nullif(btrim(coalesce(p.state_data->>'ref_gate_uri', '')), '') as ref_gate_uri_existing,
    nullif(btrim(coalesce(p.state_data->>'ref_spec_uri', '')), '') as ref_spec_uri_existing,
    nullif(btrim(coalesce(p.state_data->>'ref_spec_dict_uri', '')), '') as ref_spec_dict_uri_existing,
    nullif(btrim(coalesce(p.state_data->>'ref_spec_item_uri', '')), '') as ref_spec_item_uri_existing
  from public.proof_utxo p
),
computed as (
  select
    s.proof_id,
    s.state_data,
    coalesce(
      s.ref_gate_uri_existing,
      case
        when s.linked_gate_id is not null and public.specir_safe_ref_token(s.linked_gate_id) <> '' then
          'v://norm/gate/' || public.specir_safe_ref_token(s.linked_gate_id) || '@v1'
        else ''
      end
    ) as ref_gate_uri,
    coalesce(
      s.ref_spec_uri_existing,
      case when s.linked_spec_uri like 'v://%' then s.linked_spec_uri else '' end
    ) as ref_spec_uri,
    coalesce(
      s.ref_spec_dict_uri_existing,
      case
        when s.spec_dict_key is not null and public.specir_safe_ref_token(s.spec_dict_key) <> '' then
          'v://norm/specdict/' || public.specir_safe_ref_token(s.spec_dict_key) || '@v1'
        else ''
      end
    ) as ref_spec_dict_uri,
    coalesce(
      s.ref_spec_item_uri_existing,
      case
        when s.spec_item is not null and s.spec_item <> '' and s.ref_spec_dict_uri_existing is not null and s.ref_spec_dict_uri_existing <> '' then
          s.ref_spec_dict_uri_existing || '#' || public.specir_safe_ref_token(s.spec_item)
        when s.spec_item is not null and s.spec_item <> '' and s.spec_dict_key is not null and s.spec_dict_key <> '' then
          'v://norm/specdict/' || public.specir_safe_ref_token(s.spec_dict_key) || '@v1#' || public.specir_safe_ref_token(s.spec_item)
        when s.spec_item is not null and s.spec_item <> '' and (
          (s.ref_spec_uri_existing is not null and s.ref_spec_uri_existing <> '') or
          (s.linked_spec_uri is not null and s.linked_spec_uri like 'v://%')
        ) then
          coalesce(nullif(s.ref_spec_uri_existing, ''), s.linked_spec_uri) || '#' || public.specir_safe_ref_token(s.spec_item)
        else ''
      end
    ) as ref_spec_item_uri
  from source_rows s
),
patched as (
  select
    c.proof_id,
    c.state_data ||
    jsonb_build_object(
      'ref_gate_uri', c.ref_gate_uri,
      'ref_gate_uris',
        case
          when jsonb_typeof(c.state_data->'ref_gate_uris') = 'array'
               and jsonb_array_length(c.state_data->'ref_gate_uris') > 0 then c.state_data->'ref_gate_uris'
          when c.ref_gate_uri <> '' then jsonb_build_array(c.ref_gate_uri)
          else '[]'::jsonb
        end,
      'ref_spec_uri', c.ref_spec_uri,
      'ref_spec_dict_uri', c.ref_spec_dict_uri,
      'ref_spec_item_uri', c.ref_spec_item_uri
    ) as new_state
  from computed c
)
update public.proof_utxo p
set state_data = patched.new_state
from patched
where p.proof_id = patched.proof_id
  and p.state_data is distinct from patched.new_state;

-- 2) Backfill SPU/quota/meter refs for SMU-related rows.
with source_rows as (
  select
    p.proof_id,
    p.state_data,
    nullif(btrim(coalesce(p.state_data->>'spu_template_id', '')), '') as spu_template_id,
    nullif(btrim(coalesce(p.state_data->>'spu_library_uri', '')), '') as spu_library_uri,
    nullif(btrim(coalesce(p.state_data->>'ref_spu_uri', '')), '') as ref_spu_uri_existing,
    nullif(btrim(coalesce(p.state_data->>'ref_quota_uri', '')), '') as ref_quota_uri_existing,
    nullif(btrim(coalesce(p.state_data->>'ref_meter_rule_uri', '')), '') as ref_meter_rule_uri_existing,
    nullif(btrim(coalesce(p.state_data->>'item_no', '')), '') as item_no,
    lower(
      nullif(
        btrim(
          coalesce(
            p.state_data #>> '{spu_formula,quantity_unit}',
            p.state_data->>'unit',
            ''
          )
        ),
        ''
      )
    ) as quantity_unit
  from public.proof_utxo p
),
normalized as (
  select
    s.proof_id,
    s.state_data,
    coalesce(
      s.spu_template_id,
      nullif(regexp_replace(trim(trailing '/' from coalesce(s.spu_library_uri, '')), '^.*/', ''), ''),
      case
        when split_part(coalesce(s.item_no, ''), '-', 1) in ('101', '102') then 'contract-payment'
        when split_part(coalesce(s.item_no, ''), '-', 1) = '403' then 'rebar-processing'
        when split_part(coalesce(s.item_no, ''), '-', 1) in ('401', '405') then 'pier-concrete-casting'
        when split_part(coalesce(s.item_no, ''), '-', 1) = '702' then 'landscape-work'
        when split_part(coalesce(s.item_no, ''), '-', 1) = '600' then 'pavement-laying'
        else null
      end
    ) as template_id_raw,
    s.ref_spu_uri_existing,
    s.ref_quota_uri_existing,
    s.ref_meter_rule_uri_existing,
    s.quantity_unit
  from source_rows s
),
tokenized as (
  select
    n.proof_id,
    n.state_data,
    n.ref_spu_uri_existing,
    n.ref_quota_uri_existing,
    n.ref_meter_rule_uri_existing,
    n.quantity_unit,
    case
      when lower(coalesce(n.template_id_raw, '')) in ('spu-contract', 'contract-payment') then 'contract-payment'
      when lower(coalesce(n.template_id_raw, '')) in ('spu-reinforcement', 'rebar-processing') then 'rebar-processing'
      when lower(coalesce(n.template_id_raw, '')) in ('spu-bridge', 'spu-concrete', 'spu-capbeam', 'spu-pilefoundation', 'pier-concrete-casting') then 'pier-concrete-casting'
      when lower(coalesce(n.template_id_raw, '')) in ('spu-landscape', 'landscape-work') then 'landscape-work'
      when lower(coalesce(n.template_id_raw, '')) in ('spu-physical', 'pavement-laying') then 'pavement-laying'
      when n.template_id_raw is not null and n.template_id_raw <> '' then public.specir_safe_ref_token(lower(replace(n.template_id_raw, '_', '-')))
      else ''
    end as template_token
  from normalized n
),
computed as (
  select
    n.proof_id,
    n.state_data,
    coalesce(
      n.ref_spu_uri_existing,
      case
        when n.template_token <> '' then
          'v://norm/spu/' || n.template_token || '@v1'
        else ''
      end
    ) as ref_spu_uri,
    coalesce(
      n.ref_quota_uri_existing,
      case
        when n.template_token <> '' then
          'v://norm/quota/' || n.template_token || '@v1'
        else ''
      end
    ) as ref_quota_uri,
    coalesce(
      n.ref_meter_rule_uri_existing,
      case
        when n.quantity_unit in ('m3', 'm^3') then 'v://norm/meter-rule/by-volume@v1'
        when n.quantity_unit in ('m2', 'm^2') then 'v://norm/meter-rule/by-area@v1'
        when n.quantity_unit in ('t', 'ton', 'kg') then 'v://norm/meter-rule/by-weight@v1'
        when n.template_token <> '' then
          'v://norm/meter-rule/' || n.template_token || '@v1'
        else ''
      end
    ) as ref_meter_rule_uri
  from tokenized n
),
patched as (
  select
    c.proof_id,
    c.state_data ||
    jsonb_build_object(
      'ref_spu_uri', c.ref_spu_uri,
      'ref_quota_uri', c.ref_quota_uri,
      'ref_meter_rule_uri', c.ref_meter_rule_uri,
      -- compatibility aliases for external integrations
      'ref_spu', c.ref_spu_uri,
      'ref_quota', c.ref_quota_uri,
      'ref_meter_rule', c.ref_meter_rule_uri
    ) as new_state
  from computed c
)
update public.proof_utxo p
set state_data = patched.new_state
from patched
where p.proof_id = patched.proof_id
  and p.state_data is distinct from patched.new_state;

-- 3) Prune duplicated rule/form payloads once refs exist.
update public.proof_utxo p
set state_data = (p.state_data - 'linked_gate_rules')
where p.state_data ? 'linked_gate_rules'
  and nullif(btrim(coalesce(p.state_data->>'ref_gate_uri', '')), '') is not null;

update public.proof_utxo p
set state_data = ((p.state_data - 'spu_formula') - 'spu_form_schema') - 'spu_geometry'
where (
    p.state_data ? 'spu_formula'
    or p.state_data ? 'spu_form_schema'
    or p.state_data ? 'spu_geometry'
  )
  and nullif(btrim(coalesce(p.state_data->>'ref_spu_uri', '')), '') is not null;
