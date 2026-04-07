-- Strict assertions for ref-only migration acceptance.
-- Run after:
--   018_specir_registry.sql
--   019_project_ref_only_backfill.sql
--   023_specir_autoregister_refs_from_utxo.sql (recommended)
--   020_ref_only_validation.sql

do $$
declare
  v_legacy_gate bigint := 0;
  v_legacy_spu bigint := 0;
  v_missing_ref_gate bigint := 0;
  v_missing_ref_spu bigint := 0;
  v_missing_ref_quota bigint := 0;
  v_missing_ref_meter_rule bigint := 0;
begin
  if to_regclass('public.proof_utxo_ref_only_audit') is null then
    raise exception 'proof_utxo_ref_only_audit view not found; run 020_ref_only_validation.sql first';
  end if;
  if to_regclass('public.proof_utxo_ref_missing_specir') is null then
    raise exception 'proof_utxo_ref_missing_specir view not found; run 020_ref_only_validation.sql first';
  end if;

  select count(*) into v_legacy_gate
  from public.proof_utxo_ref_only_audit
  where has_legacy_gate_rules;

  select count(*) into v_legacy_spu
  from public.proof_utxo_ref_only_audit
  where has_legacy_spu_formula or has_legacy_spu_form_schema or has_legacy_spu_geometry;

  select count(*) into v_missing_ref_gate
  from public.proof_utxo_ref_missing_specir
  where missing_ref_gate_uri;

  select count(*) into v_missing_ref_spu
  from public.proof_utxo_ref_missing_specir
  where missing_ref_spu_uri;

  select count(*) into v_missing_ref_quota
  from public.proof_utxo_ref_missing_specir
  where missing_ref_quota_uri;

  select count(*) into v_missing_ref_meter_rule
  from public.proof_utxo_ref_missing_specir
  where missing_ref_meter_rule_uri;

  if v_legacy_gate > 0 then
    raise exception 'Assertion failed: % rows still contain legacy linked_gate_rules', v_legacy_gate;
  end if;

  if v_legacy_spu > 0 then
    raise exception 'Assertion failed: % rows still contain legacy spu_* payload', v_legacy_spu;
  end if;

  if v_missing_ref_gate > 0 then
    raise exception 'Assertion failed: % rows have ref_gate_uri missing in specir_objects', v_missing_ref_gate;
  end if;

  if v_missing_ref_spu > 0 then
    raise exception 'Assertion failed: % rows have ref_spu_uri missing in specir_objects', v_missing_ref_spu;
  end if;

  if v_missing_ref_quota > 0 then
    raise exception 'Assertion failed: % rows have ref_quota_uri missing in specir_objects', v_missing_ref_quota;
  end if;

  if v_missing_ref_meter_rule > 0 then
    raise exception 'Assertion failed: % rows have ref_meter_rule_uri missing in specir_objects', v_missing_ref_meter_rule;
  end if;

  raise notice 'All ref-only assertions passed.';
end $$;
