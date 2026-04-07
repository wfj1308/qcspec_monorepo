-- Full SPU library (v2024) seed for SpecIR.
-- Goal: provide a SQL-only bootstrap path for the expanded standard library.
-- Run after:
--   018_specir_registry.sql
--   024_specir_spu_ultimate_schema.sql

create extension if not exists pgcrypto;

with seed(uri, title, industry, unit, quota_ref, meter_rule_ref, gate_refs, standard_codes, category_path) as (
  values
  (
    'v://norm/spu/highway/bridge/bored_pile_concrete@v2024',
    'Bored pile concrete casting',
    'Highway',
    'm3',
    'v://norm/quota/concrete-casting@v1',
    'v://norm/meter-rule/by-volume@v1',
    array['v://norm/gate/concrete-strength-check@v1']::text[],
    array['GB50204-2015','JTG/T 3650-2020']::text[],
    array['highway','bridge','bored_pile_concrete']::text[]
  ),
  (
    'v://norm/spu/highway/bridge/rebar_processing_install@v2024',
    'Rebar processing and installation',
    'Highway',
    't',
    'v://norm/quota/rebar-processing@v1',
    'v://norm/meter-rule/by-weight@v1',
    array['v://norm/gate/rebar-diameter-check@v1','v://norm/gate/rebar-spacing-check@v1']::text[],
    array['GB50204-2015']::text[],
    array['highway','bridge','rebar_processing_install']::text[]
  ),
  (
    'v://norm/spu/highway/bridge/pier_column_concrete@v2024',
    'Pier column concrete',
    'Highway',
    'm3',
    'v://norm/quota/concrete-casting@v1',
    'v://norm/meter-rule/by-volume@v1',
    array['v://norm/gate/concrete-strength-check@v1']::text[],
    array['GB50204-2015']::text[],
    array['highway','bridge','pier_column_concrete']::text[]
  ),
  (
    'v://norm/spu/highway/bridge/cap_beam_casting@v2024',
    'Cap beam casting',
    'Highway',
    'm3',
    'v://norm/quota/concrete-casting@v1',
    'v://norm/meter-rule/by-volume@v1',
    array['v://norm/gate/concrete-strength-check@v1']::text[],
    array['GB50204-2015']::text[],
    array['highway','bridge','cap_beam_casting']::text[]
  ),
  (
    'v://norm/spu/highway/bridge/box_girder_precast_erect@v2024',
    'Precast box girder erection',
    'Highway',
    'piece',
    'v://norm/quota/contract-payment@v1',
    'v://norm/meter-rule/contract-payment@v1',
    array[]::text[],
    array['JTG/T F50-2011']::text[],
    array['highway','bridge','box_girder_precast_erect']::text[]
  ),
  (
    'v://norm/spu/highway/subgrade/compaction_fill@v2024',
    'Subgrade compaction fill',
    'Highway',
    'm3',
    'v://norm/quota/pavement-laying@v1',
    'v://norm/meter-rule/by-volume@v1',
    array[]::text[],
    array['JTG F80/1-2017']::text[],
    array['highway','subgrade','compaction_fill']::text[]
  ),
  (
    'v://norm/spu/highway/pavement/asphalt_surface_course@v2024',
    'Asphalt surface course',
    'Highway',
    'm2',
    'v://norm/quota/pavement-laying@v1',
    'v://norm/meter-rule/by-area@v1',
    array['v://norm/gate/pavement-flatness-check@v1']::text[],
    array['JTG F40-2004','JTG F80/1-2017']::text[],
    array['highway','pavement','asphalt_surface_course']::text[]
  ),
  (
    'v://norm/spu/highway/drainage/side_ditch_masonry@v2024',
    'Side ditch masonry',
    'Highway',
    'm',
    'v://norm/quota/landscape-work@v1',
    'v://norm/meter-rule/contract-payment@v1',
    array[]::text[],
    array['JTG/T 3610-2019']::text[],
    array['highway','drainage','side_ditch_masonry']::text[]
  ),
  (
    'v://norm/spu/highway/safety/guardrail_installation@v2024',
    'Guardrail installation',
    'Highway',
    'm',
    'v://norm/quota/contract-payment@v1',
    'v://norm/meter-rule/contract-payment@v1',
    array[]::text[],
    array['JT/T 281-2007']::text[],
    array['highway','safety','guardrail_installation']::text[]
  )
),
payloads as (
  select
    s.uri,
    s.title,
    jsonb_build_object(
      'schema', 'qcspec.specir.spu.ultimate',
      'schema_version', '1.0.0',
      'identity', jsonb_build_object(
        'spu_uri', s.uri,
        'sovereignty_uri', 'v://norm',
        'industry', s.industry,
        'standard_codes', to_jsonb(s.standard_codes),
        'category_path', to_jsonb(s.category_path),
        'aliases', '[]'::jsonb,
        'authority_refs', '[]'::jsonb
      ),
      'measure_rule', jsonb_build_object(
        'unit', s.unit,
        'payable_unit', s.unit,
        'meter_rule_ref', s.meter_rule_ref,
        'statement', 'Seeded from 026 full SPU library baseline.',
        'algorithm', jsonb_build_object(
          'key', 'seed-baseline',
          'expression', 'approved_quantity',
          'description', '',
          'parameters', '{}'::jsonb,
          'exclusion_rules', '[]'::jsonb
        ),
        'settlement_clauses', '[]'::jsonb,
        'examples', '[]'::jsonb
      ),
      'consumption', jsonb_build_object(
        'unit_basis', s.unit,
        'quota_ref', s.quota_ref,
        'materials', '[]'::jsonb,
        'machinery', '[]'::jsonb,
        'labor', '[]'::jsonb,
        'notes', '[]'::jsonb
      ),
      'qc_gate', jsonb_build_object(
        'strategy', 'all_pass',
        'fail_action', 'trigger_review_trip',
        'gate_refs', to_jsonb(s.gate_refs),
        'rules', '[]'::jsonb,
        'checklist', '[]'::jsonb
      ),
      'extensions', jsonb_build_object(
        'seed', '026',
        'source', 'full_spu_library_v2024'
      ),
      'schema_modules', jsonb_build_array('Identity', 'MeasureRule', 'Consumption', 'QCGate'),
      'label', s.title,
      'unit', s.unit,
      'norm_refs', to_jsonb(s.standard_codes),
      'gate_refs', to_jsonb(s.gate_refs),
      'quota_ref', s.quota_ref,
      'meter_rule_ref', s.meter_rule_ref,
      'quota_refs', jsonb_build_array(s.quota_ref),
      'meter_rule_refs', jsonb_build_array(s.meter_rule_ref)
    ) as content,
    jsonb_build_object(
      'domain', 'qcspec',
      'seed', '026',
      'source', 'full_spu_library_v2024'
    ) as metadata
  from seed s
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
  'spu' as kind,
  coalesce(nullif(split_part(p.uri, '@', 2), ''), 'v1') as version,
  p.title,
  p.content,
  encode(digest(convert_to(coalesce(p.content::text, ''), 'utf8'), 'sha256'), 'hex') as content_hash,
  'active' as status,
  p.metadata
from payloads p
on conflict (uri) do update
set
  kind = excluded.kind,
  version = excluded.version,
  title = excluded.title,
  content = excluded.content,
  content_hash = excluded.content_hash,
  status = excluded.status,
  metadata = excluded.metadata,
  updated_at = now();

do $$
declare
  v_count bigint := 0;
begin
  select count(*)
  into v_count
  from public.specir_objects
  where kind = 'spu'
    and uri like 'v://norm/spu/%@v2024';
  raise notice 'SpecIR full SPU library v2024 rows available: %', v_count;
end $$;
