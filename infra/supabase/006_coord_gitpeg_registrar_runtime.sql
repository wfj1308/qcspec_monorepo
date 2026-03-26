-- Runtime fields for GitPeg Registrar callback lifecycle.
alter table if exists public.coord_gitpeg_project_registry
  add column if not exists project_id uuid,
  add column if not exists partner_session_id text,
  add column if not exists registration_id text,
  add column if not exists industry_profile_id text,
  add column if not exists proof_hash text,
  add column if not exists node_uri text,
  add column if not exists token_payload jsonb default '{}'::jsonb,
  add column if not exists registration_result jsonb default '{}'::jsonb,
  add column if not exists activation_payload jsonb default '{}'::jsonb;

create index if not exists idx_coord_gitpeg_project_registry_project_id
  on public.coord_gitpeg_project_registry(project_id);

create index if not exists idx_coord_gitpeg_project_registry_partner_session_id
  on public.coord_gitpeg_project_registry(partner_session_id);

create index if not exists idx_coord_gitpeg_project_registry_registration_id
  on public.coord_gitpeg_project_registry(registration_id);
