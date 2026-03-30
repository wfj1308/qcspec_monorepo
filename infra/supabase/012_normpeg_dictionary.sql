-- NormPeg smart dictionary storage
-- Supports URI-addressed threshold routing with context overrides.

create table if not exists norm_entries (
  uri text primary key,
  code text not null,
  version text,
  path text,
  title text,
  content text,
  params jsonb not null default '{}'::jsonb,
  data jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_norm_entries_code_path on norm_entries(code, path);
create index if not exists idx_norm_entries_is_active on norm_entries(is_active);
create index if not exists idx_norm_entries_params_gin on norm_entries using gin(params);

create or replace function set_norm_entries_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if not exists (
    select 1 from pg_trigger
    where tgname = 'trg_norm_entries_updated_at'
      and tgrelid = 'public.norm_entries'::regclass
  ) then
    create trigger trg_norm_entries_updated_at
    before update on norm_entries
    for each row
    execute function set_norm_entries_updated_at();
  end if;
end $$;

insert into norm_entries (uri, code, version, path, title, content, params, data)
values (
  'v://norm/GB50204@2015/5.3.2',
  'GB50204',
  '2015',
  '5.3.2',
  'Rebar diameter deviation thresholds',
  'GB50204 5.3.2: rebar diameter deviation shall be controlled by component class.',
  '{
    "diameter_tolerance": {
      "default": [-2, 2],
      "contexts": {
        "main_beam": [-1, 1],
        "guardrail": [-5, 5]
      },
      "unit": "mm",
      "mode": "deviation_from_design",
      "operator": "range"
    }
  }'::jsonb,
  '{}'::jsonb
)
on conflict (uri) do update
set
  code = excluded.code,
  version = excluded.version,
  path = excluded.path,
  title = excluded.title,
  content = excluded.content,
  params = excluded.params,
  updated_at = now();

