-- SpecIR global standard registry
-- Goal: keep standard-library objects in a reusable global store.
-- Project-side BOQ/SMU rows should only keep references (ref_* URIs).

create table if not exists public.specir_objects (
  id uuid primary key default gen_random_uuid(),
  uri text not null unique,
  kind text not null,
  version text not null default 'v1',
  title text not null default '',
  content jsonb not null default '{}'::jsonb,
  content_hash text not null default '',
  status text not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_specir_objects_uri on public.specir_objects(uri);
create index if not exists idx_specir_objects_kind on public.specir_objects(kind);
create index if not exists idx_specir_objects_status on public.specir_objects(status);
create index if not exists idx_specir_objects_content_gin on public.specir_objects using gin(content);

create or replace function set_specir_objects_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if to_regclass('public.specir_objects') is not null then
    if not exists (
      select 1
      from pg_trigger
      where tgname = 'trg_specir_objects_updated_at'
        and tgrelid = 'public.specir_objects'::regclass
    ) then
      create trigger trg_specir_objects_updated_at
      before update on public.specir_objects
      for each row
      execute function set_specir_objects_updated_at();
    end if;
  end if;
end $$;

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
values
(
  'v://norm/spu/pier-concrete-casting@v1',
  'spu',
  'v1',
  '墩身混凝土浇筑',
  '{
    "label":"墩身混凝土浇筑",
    "unit":"m3",
    "norm_refs":["v://norm/GB50204@2015"],
    "gate_refs":["v://norm/gate/gb50204-concrete-strength@v1"],
    "quota_refs":["v://norm/quota/concrete-casting@v1"],
    "meter_rule_refs":["v://norm/meter-rule/concrete-by-volume@v1"]
  }'::jsonb,
  md5('v://norm/spu/pier-concrete-casting@v1'),
  'active',
  '{"seeded_by":"018_specir_registry"}'::jsonb
),
(
  'v://norm/spu/rebar-processing@v1',
  'spu',
  'v1',
  '钢筋加工及安装',
  '{
    "label":"钢筋加工及安装",
    "unit":"t",
    "norm_refs":["v://norm/GB50204@2015"],
    "gate_refs":["v://norm/gate/gb50204-rebar-spacing@v1"],
    "quota_refs":["v://norm/quota/rebar-processing@v1"],
    "meter_rule_refs":["v://norm/meter-rule/rebar-by-ton@v1"]
  }'::jsonb,
  md5('v://norm/spu/rebar-processing@v1'),
  'active',
  '{"seeded_by":"018_specir_registry"}'::jsonb
),
(
  'v://norm/meter-rule/rebar-by-ton@v1',
  'meter_rule',
  'v1',
  '钢筋按吨计量规则',
  '{
    "unit":"t",
    "expression":"quantity_ton",
    "description":"以吨为计量单位，按实际过磅量或核验量确认。"
  }'::jsonb,
  md5('v://norm/meter-rule/rebar-by-ton@v1'),
  'active',
  '{"seeded_by":"018_specir_registry"}'::jsonb
)
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
