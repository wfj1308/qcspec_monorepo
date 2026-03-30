-- SpecDict <-> Gate two-tier decoupling
-- 1) spec_dicts: normalized, versioned spec dictionary with context_rules
-- 2) gates: subitem binding layer referencing spec_dicts

create table if not exists public.spec_dicts (
  id uuid primary key default gen_random_uuid(),
  spec_dict_key text not null unique,
  title text not null default '',
  version text not null default 'v1.0',
  authority text not null default '',
  spec_uri text not null default '',
  items jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_spec_dicts_key on public.spec_dicts(spec_dict_key);
create index if not exists idx_spec_dicts_active on public.spec_dicts(is_active);
create index if not exists idx_spec_dicts_items_gin on public.spec_dicts using gin(items);

create table if not exists public.gates (
  id uuid primary key default gen_random_uuid(),
  gate_id text not null unique,
  gate_id_base text not null default '',
  subitem_code text not null,
  match_kind text not null default 'exact',
  execution_strategy text not null default 'all_pass',
  fail_action text not null default 'trigger_review_trip',
  spec_dict_key text not null,
  spec_item text not null default '',
  context text not null default '',
  gate_rules jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint fk_gates_spec_dict_key
    foreign key (spec_dict_key)
    references public.spec_dicts(spec_dict_key)
    on update cascade
    on delete restrict
);

create index if not exists idx_gates_gate_id on public.gates(gate_id);
create index if not exists idx_gates_subitem on public.gates(subitem_code);
create index if not exists idx_gates_match_kind on public.gates(match_kind);
create index if not exists idx_gates_active on public.gates(is_active);
create index if not exists idx_gates_spec_dict_key on public.gates(spec_dict_key);

create or replace function set_spec_dicts_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create or replace function set_gates_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if to_regclass('public.spec_dicts') is not null then
    if not exists (
      select 1
      from pg_trigger
      where tgname = 'trg_spec_dicts_updated_at'
        and tgrelid = 'public.spec_dicts'::regclass
    ) then
      create trigger trg_spec_dicts_updated_at
      before update on public.spec_dicts
      for each row
      execute function set_spec_dicts_updated_at();
    end if;
  end if;

  if to_regclass('public.gates') is not null then
    if not exists (
      select 1
      from pg_trigger
      where tgname = 'trg_gates_updated_at'
        and tgrelid = 'public.gates'::regclass
    ) then
      create trigger trg_gates_updated_at
      before update on public.gates
      for each row
      execute function set_gates_updated_at();
    end if;
  end if;
end $$;

insert into public.spec_dicts (
  spec_dict_key,
  title,
  version,
  authority,
  spec_uri,
  items,
  metadata
)
values
(
  'GB50204-2015-5.3.2',
  'GB50204-2015 Clause 5.3.2',
  'v1.0',
  'GB50204-2015',
  'v://norm/GB50204@2015/5.3.2',
  '{
    "diameter_tolerance": {
      "operator": "range",
      "unit": "mm",
      "mode": "deviation_from_design",
      "default_threshold": [-2, 2],
      "context_rules": {
        "main_beam": [-1, 1],
        "guardrail": [-3, 3],
        "pier": [-2, 2]
      }
    }
  }'::jsonb,
  '{"seeded_by":"015_specdict_gate_decoupling"}'::jsonb
),
(
  'GB50204-2015-5.3.3',
  'GB50204-2015 Clause 5.3.3',
  'v1.0',
  'GB50204-2015',
  'v://norm/GB50204@2015/5.3.3',
  '{
    "spacing_tolerance": {
      "operator": "range",
      "unit": "mm",
      "mode": "deviation_from_design",
      "default_threshold": [-10, 10],
      "context_rules": {
        "main_beam": [-8, 8],
        "guardrail": [-12, 12],
        "pier": [-10, 10]
      }
    }
  }'::jsonb,
  '{"seeded_by":"015_specdict_gate_decoupling"}'::jsonb
),
(
  'JTG-F80-2017-4.3',
  'JTG F80-2017 Clause 4.3',
  'v1.0',
  'JTG F80-2017',
  'v://norm/JTG_F80@2017/4.3',
  '{
    "crack_width_max": {
      "operator": "<=",
      "unit": "mm",
      "mode": "absolute",
      "default_threshold": 0.2,
      "context_rules": {
        "main_beam": 0.2,
        "guardrail": 0.3,
        "pier": 0.2
      }
    }
  }'::jsonb,
  '{"seeded_by":"015_specdict_gate_decoupling"}'::jsonb
)
on conflict (spec_dict_key) do update
set
  title = excluded.title,
  version = excluded.version,
  authority = excluded.authority,
  spec_uri = excluded.spec_uri,
  items = excluded.items,
  metadata = excluded.metadata,
  updated_at = now();

insert into public.gates (
  gate_id,
  gate_id_base,
  subitem_code,
  match_kind,
  execution_strategy,
  fail_action,
  spec_dict_key,
  spec_item,
  context,
  gate_rules,
  metadata
)
values
(
  'QCGate::403-1-2::gate_403_rebar_hrb400_yield',
  'QCGate::403-1-2::gate_403_rebar_hrb400_yield',
  '403-1-2',
  'exact',
  'all_pass',
  'trigger_review_trip',
  'GB50204-2015-5.3.2',
  'diameter_tolerance',
  '',
  '[]'::jsonb,
  '{"seeded_by":"015_specdict_gate_decoupling"}'::jsonb
),
(
  'QCGate::403-1-2::gate_403_rebar_spacing',
  'QCGate::403-1-2::gate_403_rebar_spacing',
  '403-1-2',
  'exact',
  'all_pass',
  'trigger_review_trip',
  'GB50204-2015-5.3.3',
  'spacing_tolerance',
  '',
  '[]'::jsonb,
  '{"seeded_by":"015_specdict_gate_decoupling"}'::jsonb
),
(
  'QCGate::403::gate_403_rebar_crack',
  'QCGate::403::gate_403_rebar_crack',
  '403',
  'prefix',
  'all_pass',
  'trigger_review_trip',
  'JTG-F80-2017-4.3',
  'crack_width_max',
  '',
  '[]'::jsonb,
  '{"seeded_by":"015_specdict_gate_decoupling"}'::jsonb
)
on conflict (gate_id) do update
set
  gate_id_base = excluded.gate_id_base,
  subitem_code = excluded.subitem_code,
  match_kind = excluded.match_kind,
  execution_strategy = excluded.execution_strategy,
  fail_action = excluded.fail_action,
  spec_dict_key = excluded.spec_dict_key,
  spec_item = excluded.spec_item,
  context = excluded.context,
  metadata = excluded.metadata,
  updated_at = now();
