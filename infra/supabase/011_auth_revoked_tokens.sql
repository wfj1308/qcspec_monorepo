-- Persist revoked auth tokens so logout is consistent across multi-worker API processes.
create table if not exists public.auth_revoked_tokens (
    token_fp text primary key,
    expires_at timestamptz not null,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_auth_revoked_tokens_expires_at
    on public.auth_revoked_tokens (expires_at);

alter table public.auth_revoked_tokens enable row level security;

drop policy if exists "service_role_manage_auth_revoked_tokens"
    on public.auth_revoked_tokens;

create policy "service_role_manage_auth_revoked_tokens"
    on public.auth_revoked_tokens
    for all
    to service_role
    using (true)
    with check (true);
