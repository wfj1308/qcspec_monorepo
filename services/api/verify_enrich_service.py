"""
Verify enrichment helpers.
services/api/verify_enrich_service.py
"""

from __future__ import annotations

from typing import Any, Callable

from supabase import Client

from services.api.specir_engine import (
    derive_spec_uri as specir_derive_spec_uri,
    evaluate_measurements as specir_evaluate_measurements,
    normalize_operator as specir_normalize_operator,
    resolve_spec_rule as specir_resolve_spec_rule,
    spec_excerpt as specir_spec_excerpt,
    threshold_text as specir_threshold_text,
)


def build_enriched_row(
    row: dict[str, Any],
    *,
    sb: Client | None = None,
    to_text: Callable[[Any, str], str],
    to_float: Callable[[Any], float | None],
    parse_limit: Callable[[Any], float | None],
    display_time: Callable[[Any], str],
    hash_payload_from_row: Callable[[dict[str, Any]], dict[str, Any]],
    hash_json: Callable[[dict[str, Any]], tuple[str, str]],
    result_cn: Callable[[Any], str],
) -> dict[str, Any]:
    def format_num(value: float) -> str:
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"

    def values_text(values: list[float], unit: str) -> str:
        if not values:
            return "-"
        arr = [format_num(v) for v in values]
        val = "/".join(arr)
        u = to_text(unit, "").strip()
        return f"{val} {u}".strip()

    def extract_sign_info(raw_row: dict[str, Any]) -> dict[str, str]:
        signed_by = raw_row.get("signed_by") if isinstance(raw_row.get("signed_by"), list) else []
        first = signed_by[0] if signed_by and isinstance(signed_by[0], dict) else {}

        name = ""
        for key in ("executor_name", "name", "display_name", "signer_name"):
            v = to_text(first.get(key), "").strip()
            if v:
                name = v
                break

        executor_uri = to_text(first.get("executor_uri") or raw_row.get("owner_uri") or "-", "")
        if not name:
            name = executor_uri.rstrip("/").split("/")[-1] if executor_uri else "-"
            if not name:
                name = "-"

        role = to_text(first.get("role") or "AI", "").strip().upper() or "AI"
        ordosign_hash = to_text(first.get("ordosign_hash") or raw_row.get("ordosign_hash") or "-", "")
        signed_at = display_time(first.get("ts") or raw_row.get("created_at"))

        return {
            "name": name,
            "executor_uri": executor_uri,
            "role": role,
            "ordosign_hash": ordosign_hash,
            "signed_at": signed_at,
        }

    def coerce_values(state_data: dict[str, Any]) -> list[float]:
        values: list[float] = []
        vals = state_data.get("values") if isinstance(state_data.get("values"), list) else []
        for v in vals:
            fv = to_float(v)
            if fv is not None:
                values.append(fv)
        if not values:
            fv = to_float(state_data.get("value"))
            if fv is not None:
                values.append(fv)
        return values

    def resolve_rule(state_data: dict[str, Any]) -> tuple[str, float | None, float | None]:
        op = specir_normalize_operator(
            state_data.get("standard_op")
            or state_data.get("standard_operator")
            or state_data.get("operator")
            or state_data.get("comparator")
            or ""
        )
        standard = to_float(state_data.get("standard_value"))
        if standard is None:
            standard = to_float(state_data.get("standard"))
        if standard is None:
            standard = to_float(state_data.get("design"))

        tolerance = to_float(state_data.get("standard_tolerance"))
        if tolerance is None:
            tolerance = parse_limit(state_data.get("limit"))

        token = f"{to_text(state_data.get('type') or '', '')} {to_text(state_data.get('type_name') or '', '')}".lower()
        if not op:
            if tolerance is not None and standard is not None:
                op = "±"
            elif any(k in token for k in ("compaction", "density", "压实度", "压实")):
                op = ">="
            else:
                op = "<="

        return op, standard, tolerance

    sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
    meta = sd.get("meta") if isinstance(sd.get("meta"), dict) else {}
    sign = extract_sign_info(row)
    test_type = to_text(sd.get("type") or sd.get("test_type") or row.get("proof_type") or "proof", "")
    test_name = to_text(sd.get("type_name") or sd.get("test_name") or test_type, "")
    stake = to_text(sd.get("stake") or sd.get("location") or "-", "") or "-"
    values = coerce_values(sd)
    spec_uri = specir_derive_spec_uri(
        sd,
        row_norm_uri=row.get("norm_uri"),
        fallback_norm_ref=sd.get("norm_ref"),
    )
    component_type = to_text(sd.get("component_type") or sd.get("structure_type") or sd.get("part_type"), "")
    spec_rule = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=test_name,
        test_type=test_type,
        test_name=test_name,
        context={"component_type": component_type, "stake": stake},
        sb=sb,
    )

    op, standard, tolerance = resolve_rule(sd)
    if to_text(spec_rule.get("operator"), "").strip():
        op = to_text(spec_rule.get("operator"), "")
    if spec_rule.get("threshold") is not None:
        standard = to_float(spec_rule.get("threshold"))
    if spec_rule.get("tolerance") is not None:
        tolerance = to_float(spec_rule.get("tolerance"))

    unit = to_text(sd.get("unit") or spec_rule.get("unit") or "", "").strip()
    evaluated = specir_evaluate_measurements(
        values=values,
        operator=op,
        threshold=standard,
        tolerance=tolerance,
        fallback_result=to_text(row.get("result") or "PENDING", ""),
    )
    computed = to_text(evaluated.get("result") or row.get("result") or "PENDING", "").upper()
    deviation_pct = evaluated.get("deviation_percent")

    threshold = specir_threshold_text(op, standard, tolerance, unit)
    measured = values_text(values, unit)
    effective_spec_uri = to_text(spec_rule.get("effective_spec_uri") or spec_uri, "")
    spec_snapshot = to_text(
        meta.get("spec_snapshot")
        or meta.get("spec_excerpt")
        or sd.get("spec_snapshot")
        or sd.get("spec_excerpt"),
        "",
    ).strip()
    spec_excerpt = spec_snapshot or specir_spec_excerpt(effective_spec_uri, fallback_excerpt=spec_rule.get("excerpt"))

    provided_hash = to_text(row.get("proof_hash") or "", "")
    hash_payload = hash_payload_from_row(row)
    recomputed_hash, _ = hash_json(hash_payload)
    hash_valid = bool(provided_hash and provided_hash.lower() == recomputed_hash.lower())

    return {
        "proof_id": to_text(row.get("proof_id") or "", ""),
        "proof_hash": provided_hash,
        "proof_hash_recomputed": recomputed_hash,
        "proof_hash_valid": hash_valid,
        "proof_type": to_text(row.get("proof_type") or "", ""),
        "parent_proof_id": to_text(row.get("parent_proof_id") or "", ""),
        "created_at": display_time(row.get("created_at")),
        "created_at_raw": to_text(row.get("created_at") or "", ""),
        "executor_name": sign["name"],
        "executor_uri": sign["executor_uri"],
        "executor_role": sign["role"],
        "ordosign_hash": sign["ordosign_hash"],
        "signed_at": sign["signed_at"],
        "spec_uri": effective_spec_uri or spec_uri,
        "spec_excerpt": spec_excerpt,
        "spec_version": to_text(spec_rule.get("version") or "", ""),
        "spec_code": to_text(spec_rule.get("code") or "", ""),
        "spec_source": to_text(spec_rule.get("source") or "", ""),
        "rule_source_uri": to_text(spec_rule.get("effective_spec_uri") or effective_spec_uri or spec_uri, ""),
        "operator": op,
        "threshold": threshold,
        "threshold_num": standard,
        "tolerance_num": tolerance,
        "measured": measured,
        "measured_values": values,
        "computed_result": computed,
        "computed_result_cn": result_cn(computed),
        "deviation_percent": deviation_pct,
        "stored_result": to_text(row.get("result") or "", "").upper(),
        "test_type": test_type,
        "test_name": test_name,
        "stake": stake,
        "component_type": component_type or "-",
        "geo_location": sd.get("geo_location") if isinstance(sd.get("geo_location"), dict) else {},
        "server_timestamp_proof": sd.get("server_timestamp_proof") if isinstance(sd.get("server_timestamp_proof"), dict) else {},
        "spatiotemporal_anchor_hash": to_text(sd.get("spatiotemporal_anchor_hash") or "", ""),
        "meta": {
            "spec_snapshot": spec_snapshot,
            "spec_uri": to_text(meta.get("spec_uri") or effective_spec_uri or spec_uri, ""),
            "spec_version": to_text(meta.get("spec_version") or spec_rule.get("version") or "", ""),
            "captured_at": display_time(meta.get("captured_at") or row.get("created_at")),
        },
        "evidence_hashes": [
            to_text(x, "").strip().lower()
            for x in (sd.get("evidence_hashes") if isinstance(sd.get("evidence_hashes"), list) else [])
            if to_text(x, "").strip()
        ],
    }
