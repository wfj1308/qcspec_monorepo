"""
Docx report row/context builders extracted from DocxEngine.
"""

from __future__ import annotations

from typing import Any

from services.api.specir_engine import derive_spec_uri as specir_derive_spec_uri
from services.api.specir_engine import evaluate_measurements as specir_evaluate_measurements
from services.api.specir_engine import resolve_spec_rule as specir_resolve_spec_rule
from services.api.specir_engine import threshold_text as specir_threshold_text


def build_docpeg_row(
    engine: Any,
    proof: dict[str, Any],
    project_meta: dict[str, Any],
    *,
    idx: int,
    normalized_type: str,
    schema_mode_design_limit: str,
    standard_op_plus_minus: str,
    pending_anchor_cn: str,
) -> tuple[dict[str, Any], bool]:
    sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
    signing = engine._first_signing(proof)
    test_type, test_type_name = engine._resolve_test_type(sd, fallback_type=normalized_type)
    schema_mode = engine._resolve_schema_mode(sd, test_type=test_type, test_type_name=test_type_name)
    unit_text = engine._extract_unit(sd)
    inline_unit = bool(unit_text and ("/" in unit_text or engine._is_flatness_like({"type": test_type, "type_name": test_type_name})))

    design = engine._to_float(sd.get("design"))
    standard_num = engine._to_float(sd.get("standard"))
    if design is None and schema_mode == schema_mode_design_limit and standard_num is not None:
        design = standard_num

    spec_uri = specir_derive_spec_uri(
        sd,
        row_norm_uri=proof.get("norm_uri"),
        fallback_norm_ref=project_meta.get("norm_ref"),
    )
    resolved_spec = specir_resolve_spec_rule(
        spec_uri=spec_uri,
        metric=test_type_name or test_type,
        test_type=test_type,
        test_name=test_type_name,
        context={
            "component_type": sd.get("component_type") or sd.get("structure_type"),
            "stake": sd.get("stake") or sd.get("location"),
        },
        sb=None,
    )
    rule_op, rule_standard, rule_tolerance = engine._resolve_standard_rule(
        state_data=sd,
        test_type=test_type,
        test_type_name=test_type_name,
        schema_mode=schema_mode,
        design=design,
        standard=standard_num,
    )
    if resolved_spec.get("operator"):
        rule_op = engine._normalize_standard_op(resolved_spec.get("operator")) or rule_op
    if resolved_spec.get("threshold") is not None:
        rule_standard = engine._to_float(resolved_spec.get("threshold"))
    if resolved_spec.get("tolerance") is not None:
        rule_tolerance = engine._to_float(resolved_spec.get("tolerance"))
    if not unit_text:
        unit_text = engine._to_text(resolved_spec.get("unit") or "").strip()
    values = engine._coerce_values(sd.get("values"), fallback_value=sd.get("value"))

    lower = None
    upper = None
    if rule_op == standard_op_plus_minus and rule_standard is not None and rule_tolerance is not None and values:
        lower = rule_standard - rule_tolerance
        upper = rule_standard + rule_tolerance

    proof_result = engine._to_text(proof.get("result") or sd.get("result") or "PENDING").upper()
    evaluated = specir_evaluate_measurements(
        values=values,
        operator=rule_op,
        threshold=rule_standard,
        tolerance=rule_tolerance,
        fallback_result=proof_result,
    )
    result_code = engine._to_text(evaluated.get("result") or proof_result).upper()
    result_cn = engine._result_cn(result_code)

    project_uri = engine._to_text(proof.get("project_uri") or project_meta.get("project_uri") or "")
    location_text = engine._to_text(sd.get("location") or sd.get("stake") or "-")
    segment_uri = engine._to_text(proof.get("segment_uri") or sd.get("segment_uri") or "")
    if not segment_uri and project_uri and location_text and location_text != "-":
        segment_uri = f"{project_uri.rstrip('/')}/segment/{location_text}/"
    proof_id = engine._to_text(proof.get("proof_id") or "")
    v_uri = engine._to_text(sd.get("v_uri") or proof.get("v_uri") or "")
    if not v_uri and project_uri and proof_id:
        v_uri = f"{project_uri.rstrip('/')}/{normalized_type}/{proof_id}/"

    executor_uri = engine._to_text(
        signing.get("executor_uri")
        or signing.get("uri")
        or proof.get("owner_uri")
        or project_meta.get("executor_uri")
        or "-"
    )
    ordosign_hash = engine._to_text(signing.get("ordosign_hash") or project_meta.get("ordosign_hash") or "-")
    executor_name = engine._extract_executor_name(signing, fallback_uri=executor_uri)
    executor_id = engine._extract_executor_id(signing, fallback_uri=executor_uri, fallback_name=executor_name)
    created_at_text = engine._format_display_time(proof.get("created_at") or "")
    signed_at = engine._format_signed_at(signing.get("ts") or proof.get("created_at") or "")
    norm_ref = engine._to_text(
        resolved_spec.get("effective_spec_uri")
        or spec_uri
        or sd.get("norm_ref")
        or proof.get("norm_uri")
        or project_meta.get("norm_ref")
        or "-"
    )
    value_num = engine._to_float(sd.get("value"))
    if value_num is None and values:
        value_num = values[0] if len(values) == 1 else round(sum(values) / len(values), 4)
    standard_text = engine._format_num(rule_standard) if rule_standard is not None else "-"
    value_text = engine._format_num(value_num) if value_num is not None else "-"
    norm_requirement = specir_threshold_text(
        rule_op,
        rule_standard,
        rule_tolerance,
        unit_text,
    )
    limit_text = (
        f"{standard_op_plus_minus}{engine._format_num(rule_tolerance)}"
        if rule_op == standard_op_plus_minus and rule_tolerance is not None
        else "-"
    )

    row = {
        "index": idx,
        "proof_id": proof_id,
        "proof_hash": engine._to_text(proof.get("proof_hash") or ""),
        "gitpeg_anchor": engine._to_text(proof.get("gitpeg_anchor") or pending_anchor_cn),
        "project_uri": project_uri,
        "segment_uri": segment_uri,
        "v_uri": v_uri,
        "location": location_text,
        "stake": location_text,
        "test_type": engine._to_text(test_type),
        "test_type_name": engine._to_text(test_type_name),
        "schema_mode": schema_mode,
        "standard_op": rule_op,
        "type": engine._to_text(test_type),
        "type_name": engine._to_text(test_type_name),
        "unit": unit_text or "-",
        "design": engine._with_unit(standard_text, unit_text, force_inline=inline_unit),
        "design_raw": standard_text,
        "standard": engine._with_unit(standard_text, unit_text, force_inline=inline_unit),
        "standard_raw": standard_text,
        "standard_value": engine._with_unit(standard_text, unit_text, force_inline=inline_unit),
        "limit": limit_text,
        "norm_requirement": norm_requirement,
        "limit_num": engine._format_num(rule_tolerance) if rule_tolerance is not None else "-",
        "value": engine._with_unit(value_text, unit_text, force_inline=inline_unit),
        "value_raw": value_text,
        "values": values,
        "val_str": engine._format_values_multiline(values, chunk=10, unit=unit_text, force_inline_unit=inline_unit),
        "range_str": (
            f"[{engine._format_num(lower)}, {engine._format_num(upper)}]"
            if lower is not None and upper is not None
            else "-"
        ),
        "result": result_code,
        "result_cn": result_cn,
        "deviation_percent": evaluated.get("deviation_percent"),
        "executor_uri": executor_uri,
        "ordosign_hash": ordosign_hash,
        "signed_by": executor_name,
        "executor_name": executor_name,
        "executor_id": executor_id,
        "signed_at": signed_at,
        "norm_ref": norm_ref,
        "spec_excerpt": engine._to_text(resolved_spec.get("excerpt") or ""),
        "spec_version": engine._to_text(resolved_spec.get("version") or ""),
        "created_at": created_at_text,
        "remark": engine._to_text(sd.get("remark") or ""),
    }
    return row, result_code == "FAIL"


def build_docpeg_context(
    engine: Any,
    rows: list[dict[str, Any]],
    project_meta: dict[str, Any],
    *,
    normalized_type: str,
    any_fail: bool,
    fail_cn: str,
    pass_cn: str,
    pending_anchor_cn: str,
) -> dict[str, Any]:
    latest = rows[-1] if rows else {}
    primary = latest if rows else {}
    verify_uri = (
        f"{engine._verify_base_url()}/v/{latest.get('proof_id')}?trace=true"
        if latest.get("proof_id")
        else ""
    )
    signed_at_key = engine._format_signed_at(
        latest.get("signed_at") or latest.get("created_at") or engine._now_seconds()
    )
    v_uri_tree = engine._build_v_uri_tree(
        project_uri=engine._to_text(latest.get("project_uri") or project_meta.get("project_uri") or ""),
        segment_uri=engine._to_text(latest.get("segment_uri") or ""),
        v_uri=engine._to_text(latest.get("v_uri") or ""),
        proof_id=engine._to_text(latest.get("proof_id") or ""),
        stake=engine._to_text(latest.get("stake") or latest.get("location") or project_meta.get("stake_range") or "-"),
        verify_uri=verify_uri,
    )
    summary_result_cn = fail_cn if any_fail else pass_cn
    named_items = engine._build_named_items(rows)

    return {
        "report_type": normalized_type,
        "construction_unit": engine._to_text(
            project_meta.get("construction_unit")
            or project_meta.get("enterprise_name")
            or project_meta.get("org_name")
            or "-"
        ),
        "project_name": engine._to_text(project_meta.get("name") or project_meta.get("project_name") or ""),
        "project_uri": engine._to_text(project_meta.get("project_uri") or latest.get("project_uri") or ""),
        "contract_no": engine._to_text(project_meta.get("contract_no") or "-"),
        "stake_range": engine._to_text(project_meta.get("stake_range") or project_meta.get("location") or "-"),
        "check_date": engine._to_text(project_meta.get("check_date") or engine._now()[:10]),
        "inspector": engine._to_text(project_meta.get("inspector") or project_meta.get("operator") or "-"),
        "tech_leader": engine._to_text(project_meta.get("tech_leader") or "-"),
        "generated_at": engine._now(),
        "records": rows,
        "rows": rows,
        "items": named_items,
        "test": {
            "name": engine._to_text(primary.get("test_type_name") or primary.get("test_type") or ""),
            "val_str": engine._to_text(primary.get("val_str") or "-"),
            "value": engine._to_text(primary.get("value") or "-"),
            "unit": engine._to_text(primary.get("unit") or "-"),
            "standard": engine._to_text(primary.get("standard") or "-"),
            "standard_value": engine._to_text(primary.get("standard_value") or primary.get("standard") or "-"),
            "standard_op": engine._to_text(primary.get("standard_op") or "-"),
            "limit": engine._to_text(primary.get("norm_requirement") or primary.get("limit") or "-"),
            "stake": engine._to_text(primary.get("stake") or primary.get("location") or "-"),
            "result_cn": engine._to_text(primary.get("result_cn") or "-"),
        },
        "total_count": len(rows),
        "pass_count": sum(1 for x in rows if x.get("result") == "PASS"),
        "fail_count": sum(1 for x in rows if x.get("result") == "FAIL"),
        "summary_result_cn": summary_result_cn,
        "conclusion": summary_result_cn,
        "proof_id": engine._to_text(latest.get("proof_id") or ""),
        "proof_hash": engine._to_text(latest.get("proof_hash") or ""),
        "gitpeg_anchor": engine._to_text(latest.get("gitpeg_anchor") or pending_anchor_cn),
        "v_uri": engine._to_text(latest.get("v_uri") or ""),
        "segment_uri": engine._to_text(latest.get("segment_uri") or ""),
        "stake": engine._to_text(latest.get("stake") or latest.get("location") or project_meta.get("stake_range") or "-"),
        "executor_uri": engine._to_text(latest.get("executor_uri") or project_meta.get("executor_uri") or "-"),
        "executor_id": engine._to_text(latest.get("executor_id") or ""),
        "ordosign_hash": engine._to_text(latest.get("ordosign_hash") or project_meta.get("ordosign_hash") or "-"),
        "signed_by": engine._to_text(latest.get("signed_by") or latest.get("executor_uri") or "-"),
        "executor_name": engine._to_text(latest.get("executor_name") or latest.get("signed_by") or "-"),
        "signed_at": signed_at_key,
        "time_primary_key": signed_at_key,
        "created_at": engine._format_display_time(latest.get("created_at") or ""),
        "norm_ref": engine._to_text(latest.get("norm_ref") or project_meta.get("norm_ref") or "-"),
        "verify_uri": verify_uri,
        "v_uri_tree": v_uri_tree,
        "v_uri_nodes": v_uri_tree.get("nodes", []),
        "utxo_locator": {
            "proof_id": engine._to_text(latest.get("proof_id") or ""),
            "stake": engine._to_text(latest.get("stake") or latest.get("location") or "-"),
            "segment_uri": engine._to_text(latest.get("segment_uri") or ""),
            "v_uri": engine._to_text(latest.get("v_uri") or ""),
            "verify_uri": verify_uri,
        },
    }
