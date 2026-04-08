-- Track current head proof id for each mobile workorder to bridge TripRole chain.

alter table if exists public.mobile_workorders
  add column if not exists head_proof_id text not null default '';

create index if not exists idx_mobile_workorders_head_proof
  on public.mobile_workorders(head_proof_id);
