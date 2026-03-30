-- Doc governance: tags table + jsonb/trgm indexes for searchable sovereign documents

create extension if not exists pg_trgm;

create table if not exists public.doc_tags (
  id uuid primary key default gen_random_uuid(),
  proof_id text not null,
  project_uri text not null,
  node_uri text not null,
  tag text not null,
  tag_type text not null default 'document',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_doc_tags_proof_id on public.doc_tags(proof_id);
create index if not exists idx_doc_tags_project_uri on public.doc_tags(project_uri);
create index if not exists idx_doc_tags_node_uri on public.doc_tags(node_uri);
create index if not exists idx_doc_tags_tag on public.doc_tags(tag);
create index if not exists idx_doc_tags_tag_trgm on public.doc_tags using gin(tag gin_trgm_ops);
create index if not exists idx_doc_tags_metadata_gin on public.doc_tags using gin(metadata);

create unique index if not exists uq_doc_tags_proof_tag
  on public.doc_tags(proof_id, tag, tag_type);

create index if not exists idx_proof_utxo_state_data_gin
  on public.proof_utxo using gin(state_data);

create index if not exists idx_proof_utxo_state_file_name_trgm
  on public.proof_utxo using gin((coalesce(state_data->>'file_name', '')) gin_trgm_ops);

create index if not exists idx_proof_utxo_state_summary_trgm
  on public.proof_utxo using gin((coalesce(state_data->>'summary', '')) gin_trgm_ops);

create index if not exists idx_proof_utxo_state_text_excerpt_trgm
  on public.proof_utxo using gin((coalesce(state_data->>'text_excerpt', '')) gin_trgm_ops);
