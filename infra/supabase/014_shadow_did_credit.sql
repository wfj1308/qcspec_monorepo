-- Shadow mirror logs + DID credential registry for protocol-level governance.

create table if not exists public.proof_shadow_mirror_log (
  id uuid primary key default gen_random_uuid(),
  proof_id text not null,
  project_uri text not null,
  mirror_id text not null,
  mirror_endpoint text not null,
  status text not null default 'pending',
  http_status integer,
  error_msg text,
  packet_hash text,
  cipher_hash text,
  response_summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_proof_shadow_mirror_log_proof_id
  on public.proof_shadow_mirror_log(proof_id);

create index if not exists idx_proof_shadow_mirror_log_project_uri
  on public.proof_shadow_mirror_log(project_uri);

create index if not exists idx_proof_shadow_mirror_log_created_at
  on public.proof_shadow_mirror_log(created_at desc);

create table if not exists public.proof_did_credential (
  id uuid primary key default gen_random_uuid(),
  credential_id text not null unique,
  holder_did text not null,
  credential_role text not null,
  credential_type text not null default '',
  issuer_did text not null default '',
  status text not null default 'active',
  valid_from timestamptz,
  valid_to timestamptz,
  scope_project_uri text not null default '',
  scope_boq_patterns jsonb not null default '[]'::jsonb,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_proof_did_credential_holder_did
  on public.proof_did_credential(holder_did);

create index if not exists idx_proof_did_credential_role
  on public.proof_did_credential(credential_role);

create index if not exists idx_proof_did_credential_status
  on public.proof_did_credential(status);

create index if not exists idx_proof_did_credential_scope_project
  on public.proof_did_credential(scope_project_uri);

create or replace function set_proof_did_credential_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if to_regclass('public.proof_did_credential') is not null then
    if not exists (
      select 1
      from pg_trigger
      where tgname = 'trg_proof_did_credential_updated_at'
        and tgrelid = 'public.proof_did_credential'::regclass
    ) then
      create trigger trg_proof_did_credential_updated_at
      before update on public.proof_did_credential
      for each row
      execute function set_proof_did_credential_updated_at();
    end if;
  end if;
end $$;
