"""DocFinal package orchestration for one BOQ item."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from services.api.domain.execution.integrations import (
    build_sealing_trip,
    calculate_sovereign_credit,
    get_all_evidence_for_item,
    get_project_name_by_id,
    get_proof_chain,
    build_dsp_zip_package,
    build_rebar_report_context,
    render_rebar_inspection_docx,
    render_rebar_inspection_pdf,
)
from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)
from services.api.domain.execution.triprole_docfinal import (
    apply_hierarchy_asset_filter as _apply_hierarchy_asset_filter,
    build_recursive_hierarchy_summary as _build_recursive_hierarchy_summary,
)
from services.api.domain.execution.triprole_docfinal_audit import (
    compute_docfinal_risk_audit as _compute_docfinal_risk_audit,
)
from services.api.domain.execution.triprole_docfinal_context import (
    attach_docfinal_asset_origin as _attach_docfinal_asset_origin,
    attach_docfinal_biometric as _attach_docfinal_biometric,
    attach_docfinal_credit as _attach_docfinal_credit,
    attach_docfinal_geo as _attach_docfinal_geo,
    attach_docfinal_hierarchy as _attach_docfinal_hierarchy,
    attach_docfinal_lineage_snapshot as _attach_docfinal_lineage_snapshot,
    attach_docfinal_risk_audit as _attach_docfinal_risk_audit,
    attach_docfinal_sealing_trip as _attach_docfinal_sealing_trip,
    attach_docfinal_sensor as _attach_docfinal_sensor,
    build_docfinal_meta as _build_docfinal_meta,
    finalize_docfinal_context as _finalize_docfinal_context,
    resolve_docfinal_credit_participant_did as _resolve_docfinal_credit_participant_did,
)
from services.api.domain.execution.triprole_docfinal_render import (
    render_docfinal_artifacts as _render_docfinal_artifacts,
)
from services.api.domain.execution.triprole_component_utxo import (
    build_component_utxo_verification as _build_component_utxo_verification,
)
from services.api.domain.execution.triprole_docfinal_runtime import (
    load_docfinal_chain as _load_docfinal_chain,
    resolve_docfinal_lineage_and_asset_origin as _resolve_docfinal_lineage_and_asset_origin,
    resolve_docfinal_transfer_receipt as _resolve_docfinal_transfer_receipt,
)
from services.api.domain.execution.triprole_lineage import (
    _extract_settled_quantity,
    _item_no_from_boq_uri,
    _smu_id_from_item_no,
)


def build_docfinal_package_for_boq(
    *,
    boq_item_uri: str,
    sb: Any,
    project_meta: dict[str, Any] | None = None,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str | Path | None = None,
    apply_asset_transfer: bool = False,
    transfer_amount: float | None = None,
    transfer_executor_uri: str = "v://executor/system/",
    aggregate_anchor_code: str = "",
    aggregate_direction: str = "all",
    aggregate_level: str = "all",
    module_file: str = __file__,
    get_boq_realtime_status_fn: Callable[..., dict[str, Any]],
    get_full_lineage_fn: Callable[..., dict[str, Any]],
    trace_asset_origin_fn: Callable[..., dict[str, Any]],
    transfer_asset_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    normalized_uri, chain = _load_docfinal_chain(
        boq_item_uri=boq_item_uri,
        sb=sb,
        project_meta=project_meta,
        load_chain=lambda uri, supabase: get_proof_chain(uri, supabase),
    )

    latest = chain[-1]
    latest_sd = _as_dict(latest.get("state_data"))

    meta = _build_docfinal_meta(
        project_meta=project_meta,
        latest_row=latest,
        latest_state=latest_sd,
        resolve_project_name=lambda project_id: get_project_name_by_id(sb, project_id, default="-"),
    )

    context = build_rebar_report_context(
        boq_item_uri=normalized_uri,
        chain_rows=chain,
        project_meta=meta,
        verify_base_url=verify_base_url,
    )
    context["timeline_rows"] = _as_list(context.get("timeline"))
    context["record_rows"] = _as_list(context.get("records"))

    risk_audit = _compute_docfinal_risk_audit(
        sb=sb,
        project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
        boq_item_uri=normalized_uri,
        chain_rows=chain,
    )
    context = _attach_docfinal_risk_audit(
        context=context,
        risk_audit=risk_audit,
    )

    status_snapshot = get_boq_realtime_status_fn(
        sb=sb,
        project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
        limit=10000,
    )
    hierarchy_summary = _build_recursive_hierarchy_summary(
        items=_as_list(status_snapshot.get("items")),
        focus_item_no=_to_text(latest_sd.get("item_no") or "").strip(),
    )
    hierarchy_rows_all = _as_list(hierarchy_summary.get("rows"))
    hierarchy_filtered = _apply_hierarchy_asset_filter(
        rows=hierarchy_rows_all,
        focus_item_no=_to_text(latest_sd.get("item_no") or "").strip(),
        anchor_code=aggregate_anchor_code,
        direction=aggregate_direction,
        level=aggregate_level,
    )
    context = _attach_docfinal_hierarchy(
        context=context,
        hierarchy_summary=hierarchy_summary,
        hierarchy_filtered=hierarchy_filtered,
    )

    credit_endorsement = _as_dict(latest_sd.get("credit_endorsement"))
    if not credit_endorsement:
        participant_did = _resolve_docfinal_credit_participant_did(latest_sd)
        if participant_did.startswith("did:"):
            try:
                credit_endorsement = calculate_sovereign_credit(
                    sb=sb,
                    project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
                    participant_did=participant_did,
                )
            except Exception:
                credit_endorsement = {}
    context = _attach_docfinal_credit(
        context=context,
        credit_endorsement=credit_endorsement,
    )
    context = _attach_docfinal_sensor(
        context=context,
        latest_state=latest_sd,
    )
    context = _attach_docfinal_geo(
        context=context,
        latest_state=latest_sd,
    )
    context = _attach_docfinal_biometric(
        context=context,
        latest_state=latest_sd,
    )

    latest_proof_id = _to_text(latest.get("proof_id") or "").strip()
    lineage_snapshot, asset_origin = _resolve_docfinal_lineage_and_asset_origin(
        latest_proof_id=latest_proof_id,
        sb=sb,
        boq_item_uri=normalized_uri,
        project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
        get_full_lineage=get_full_lineage_fn,
        trace_asset_origin=trace_asset_origin_fn,
    )
    context = _attach_docfinal_lineage_snapshot(
        context=context,
        lineage_snapshot=lineage_snapshot,
    )
    context = _attach_docfinal_asset_origin(
        context=context,
        asset_origin=asset_origin,
    )

    total_proof_hash = _to_text(context.get("total_proof_hash") or context.get("chain_root_hash") or "").strip()
    if total_proof_hash:
        sealing_trip = build_sealing_trip(
            total_proof_hash=total_proof_hash,
            project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
            boq_item_uri=normalized_uri,
            smu_id=_smu_id_from_item_no(_to_text(latest_sd.get("item_no") or _item_no_from_boq_uri(normalized_uri)).strip()),
        )
        context = _attach_docfinal_sealing_trip(
            context=context,
            sealing_trip=sealing_trip,
        )

    transfer_receipt = _resolve_docfinal_transfer_receipt(
        apply_asset_transfer=apply_asset_transfer,
        sb=sb,
        transfer_amount=transfer_amount,
        latest_row=latest,
        boq_item_uri=normalized_uri,
        transfer_executor_uri=transfer_executor_uri,
        verify_uri=_to_text(context.get("verify_uri") or "").strip(),
        settled_quantity=lambda row: _extract_settled_quantity(row, fallback_design=None),
        transfer_asset=transfer_asset_fn,
    )

    context = _finalize_docfinal_context(
        context=context,
        meta=meta,
        transfer_receipt=transfer_receipt,
    )

    component_verification: dict[str, Any] = {}
    component_payload = _as_dict(latest_sd.get("component_utxo"))
    if not component_payload:
        component_payload = {
            "component_id": _to_text(latest_sd.get("component_id") or "").strip(),
            "kind": _to_text(latest_sd.get("component_kind") or "component").strip(),
            "boq_items": _as_list(latest_sd.get("component_boq_items")),
            "bom": _as_list(latest_sd.get("component_bom")),
            "material_input_proof_ids": _as_list(latest_sd.get("component_material_input_proof_ids")),
            "material_inputs": _as_list(latest_sd.get("component_material_inputs")),
            "default_tolerance_ratio": latest_sd.get("component_default_tolerance_ratio"),
        }
    if _to_text(component_payload.get("component_id") or "").strip():
        try:
            component_verification = _build_component_utxo_verification(
                sb=sb,
                component_id=_to_text(component_payload.get("component_id") or "").strip(),
                kind=_to_text(component_payload.get("kind") or "component").strip(),
                boq_items=_as_list(component_payload.get("boq_items")),
                bom=_as_list(component_payload.get("bom")),
                material_inputs=_as_list(component_payload.get("material_inputs")),
                material_input_proof_ids=_as_list(component_payload.get("material_input_proof_ids")),
                project_uri=_to_text(meta.get("project_uri") or latest.get("project_uri") or "").strip(),
                default_tolerance_ratio=float(component_payload.get("default_tolerance_ratio") or 0.05),
            )
            context["component_utxo"] = component_verification
            context["component_proof_hash"] = _to_text(component_verification.get("proof_hash") or "").strip()
        except Exception as exc:
            component_verification = {
                "ok": False,
                "component_id": _to_text(component_payload.get("component_id") or "").strip(),
                "error": f"{type(exc).__name__}: {exc}",
            }
            context["component_utxo"] = component_verification

    artifacts = _render_docfinal_artifacts(
        module_file=module_file,
        template_path=template_path,
        normalized_uri=normalized_uri,
        context=context,
        chain=chain,
        sb=sb,
        render_docx=render_rebar_inspection_docx,
        render_pdf=render_rebar_inspection_pdf,
        get_evidence=get_all_evidence_for_item,
        build_zip=build_dsp_zip_package,
    )
    context = _as_dict(artifacts.get("context"))
    docx_bytes = artifacts.get("docx_bytes") or b""
    pdf_bytes = artifacts.get("pdf_bytes") or b""
    zip_bytes = artifacts.get("zip_bytes") or b""
    file_base = _to_text(artifacts.get("filename_base") or "docfinal").strip() or "docfinal"

    return {
        "ok": True,
        "boq_item_uri": normalized_uri,
        "context": context,
        "proof_chain": chain,
        "docx_bytes": docx_bytes,
        "pdf_bytes": pdf_bytes,
        "zip_bytes": zip_bytes,
        "filename_base": file_base,
        "asset_transfer": transfer_receipt,
        "full_lineage": lineage_snapshot,
        "asset_origin": asset_origin,
        "component_utxo": component_verification,
    }


__all__ = ["build_docfinal_package_for_boq"]
