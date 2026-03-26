-- Persist register step-3 (zero ledger) metadata on projects.
alter table if exists projects
  add column if not exists zero_personnel jsonb default '[]'::jsonb,
  add column if not exists zero_equipment jsonb default '[]'::jsonb,
  add column if not exists zero_subcontracts jsonb default '[]'::jsonb,
  add column if not exists zero_materials jsonb default '[]'::jsonb,
  add column if not exists zero_sign_status text default 'pending',
  add column if not exists qc_ledger_unlocked boolean default false;

update projects
set
  zero_personnel = coalesce(zero_personnel, '[]'::jsonb),
  zero_equipment = coalesce(zero_equipment, '[]'::jsonb),
  zero_subcontracts = coalesce(zero_subcontracts, '[]'::jsonb),
  zero_materials = coalesce(zero_materials, '[]'::jsonb),
  zero_sign_status = coalesce(nullif(zero_sign_status, ''), 'pending'),
  qc_ledger_unlocked = coalesce(qc_ledger_unlocked, false);

