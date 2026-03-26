-- Proof-UTXO Engine v0.1
-- Purpose: introduce semantic UTXO execution model while keeping proof_chain compatible.

create extension if not exists pgcrypto;

create table if not exists proof_transaction (
  tx_id text primary key,
  tx_type text not null check (tx_type in ('consume', 'merge', 'split', 'settle', 'archive')),
  input_proofs text[] not null default '{}'::text[],
  output_proofs text[] not null default '{}'::text[],
  trigger_action text,
  trigger_data jsonb not null default '{}'::jsonb,
  executor_uri text not null,
  ordosign_hash text,
  status text not null default 'success' check (status in ('success', 'failed', 'pending')),
  error_msg text,
  created_at timestamptz not null default now()
);

create table if not exists proof_utxo (
  proof_id text primary key,
  proof_hash text not null unique,
  owner_uri text not null,
  project_id uuid references projects(id) on delete set null,
  project_uri text not null,
  segment_uri text,
  proof_type text not null check (proof_type in (
    'inspection',
    'lab',
    'photo',
    'approval',
    'payment',
    'archive',
    'ordosign',
    'zero_ledger'
  )),
  result text not null check (result in ('PASS', 'FAIL', 'OBSERVE', 'PENDING', 'CANCELLED')),
  state_data jsonb not null default '{}'::jsonb,
  spent boolean not null default false,
  spend_tx_id text references proof_transaction(tx_id),
  spent_at timestamptz,
  conditions jsonb not null default '[]'::jsonb,
  parent_proof_id text references proof_utxo(proof_id),
  depth integer not null default 0 check (depth >= 0),
  norm_uri text,
  gitpeg_anchor text,
  signed_by jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists proof_condition_log (
  id bigserial primary key,
  proof_id text not null references proof_utxo(proof_id) on delete cascade,
  condition jsonb not null,
  checked_by text not null,
  passed boolean not null,
  detail text,
  checked_at timestamptz not null default now()
);

create index if not exists idx_proof_utxo_owner on proof_utxo(owner_uri);
create index if not exists idx_proof_utxo_project on proof_utxo(project_id);
create index if not exists idx_proof_utxo_project_uri on proof_utxo(project_uri);
create index if not exists idx_proof_utxo_segment on proof_utxo(segment_uri);
create index if not exists idx_proof_utxo_parent on proof_utxo(parent_proof_id);
create index if not exists idx_proof_utxo_type_result on proof_utxo(proof_type, result);
create index if not exists idx_proof_utxo_unspent on proof_utxo(project_uri, proof_type, result) where spent = false;
create index if not exists idx_proof_utxo_state_gin on proof_utxo using gin(state_data);
create index if not exists idx_proof_transaction_inputs_gin on proof_transaction using gin(input_proofs);
create index if not exists idx_proof_transaction_outputs_gin on proof_transaction using gin(output_proofs);
create index if not exists idx_proof_condition_log_proof on proof_condition_log(proof_id);

create or replace function set_proof_utxo_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$
begin
  if to_regclass('public.proof_utxo') is not null then
    if not exists (
      select 1
      from pg_trigger
      where tgname = 'trg_proof_utxo_updated_at'
        and tgrelid = 'public.proof_utxo'::regclass
    ) then
      create trigger trg_proof_utxo_updated_at
      before update on proof_utxo
      for each row
      execute function set_proof_utxo_updated_at();
    end if;
  end if;
end $$;

-- Backfill from proof_chain to keep historical data queryable in the new model.
do $$
begin
  if to_regclass('public.proof_chain') is not null then
    execute $sql$
      insert into proof_utxo (
        proof_id,
        proof_hash,
        owner_uri,
        project_id,
        project_uri,
        segment_uri,
        proof_type,
        result,
        state_data,
        spent,
        spend_tx_id,
        spent_at,
        conditions,
        parent_proof_id,
        depth,
        norm_uri,
        gitpeg_anchor,
        signed_by,
        created_at,
        updated_at
      )
      select
        pc.proof_id,
        coalesce(
          nullif(pc.proof_hash, ''),
          lower(replace(pc.proof_id, 'GP-PROOF-', '')),
          encode(digest(pc.proof_id, 'sha256'), 'hex')
        ) as proof_hash,
        coalesce(
          nullif(pc.actor_v_uri, ''),
          coalesce(nullif(p.v_uri, ''), nullif(pc.v_uri, ''), 'v://unknown/project/') || 'executor/system/'
        ) as owner_uri,
        pc.project_id,
        coalesce(nullif(p.v_uri, ''), nullif(pc.v_uri, ''), 'v://unknown/project/') as project_uri,
        null::text as segment_uri,
        case
          when pc.object_type in ('inspection', 'lab', 'photo', 'approval', 'payment', 'archive', 'ordosign', 'zero_ledger')
            then pc.object_type
          else 'inspection'
        end as proof_type,
        case
          when pc.status = 'confirmed' then 'PASS'
          when pc.status = 'pending' then 'PENDING'
          else 'OBSERVE'
        end as result,
        jsonb_build_object(
          'legacy_object_type', pc.object_type,
          'legacy_action', pc.action,
          'legacy_summary', pc.summary,
          'legacy_v_uri', pc.v_uri,
          'legacy_payload_hash', pc.payload_hash,
          'legacy_status', pc.status
        ) as state_data,
        false as spent,
        null::text as spend_tx_id,
        null::timestamptz as spent_at,
        '[]'::jsonb as conditions,
        null::text as parent_proof_id,
        0 as depth,
        null::text as norm_uri,
        null::text as gitpeg_anchor,
        case
          when nullif(pc.actor_v_uri, '') is not null then
            jsonb_build_array(
              jsonb_build_object(
                'executor_uri', pc.actor_v_uri,
                'role', 'AI',
                'ts', coalesce(pc.created_at, now())::text
              )
            )
          else '[]'::jsonb
        end as signed_by,
        coalesce(pc.created_at, now()) as created_at,
        coalesce(pc.created_at, now()) as updated_at
      from proof_chain pc
      left join projects p on p.id = pc.project_id
      on conflict (proof_id) do nothing
    $sql$;
  end if;
end $$;
