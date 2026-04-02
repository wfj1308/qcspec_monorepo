"""DocFinal context assembly helpers."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.triprole_common import (
    as_dict as _as_dict,
    as_list as _as_list,
    to_text as _to_text,
)


def build_docfinal_meta(
    *,
    project_meta: dict[str, Any] | None,
    latest_row: dict[str, Any],
    latest_state: dict[str, Any],
    resolve_project_name: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    meta = dict(project_meta or {})
    if not _to_text(meta.get("project_uri") or "").strip():
        meta["project_uri"] = _to_text(latest_row.get("project_uri") or "").strip()

    project_id = _to_text(latest_row.get("project_id") or "").strip()
    if (
        not _to_text(meta.get("project_name") or meta.get("name") or "").strip()
        and project_id
        and callable(resolve_project_name)
    ):
        try:
            meta["project_name"] = _to_text(resolve_project_name(project_id) or "").strip()
        except Exception:
            pass

    if not _to_text(meta.get("artifact_uri") or "").strip():
        project_uri = _to_text(meta.get("project_uri") or "").strip().rstrip("/")
        pid = _to_text(latest_row.get("proof_id") or "").strip()
        meta["artifact_uri"] = (
            _to_text(latest_state.get("artifact_uri") or "").strip()
            or (f"{project_uri}/artifact/{pid}" if project_uri and pid else "")
        )

    if not _to_text(meta.get("gitpeg_anchor") or "").strip():
        meta["gitpeg_anchor"] = _to_text(latest_row.get("gitpeg_anchor") or "").strip()

    return meta


def attach_docfinal_risk_audit(
    *,
    context: dict[str, Any],
    risk_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(context or {})
    audit = _as_dict(risk_audit)
    if not audit:
        return out
    audit["total_proof_hash"] = _to_text(
        out.get("total_proof_hash") or out.get("chain_root_hash") or ""
    ).strip()
    out["risk_audit"] = audit
    out["risk_score"] = audit.get("risk_score")
    out["risk_issue_count"] = len(audit.get("issues") or [])
    return out


def attach_docfinal_hierarchy(
    *,
    context: dict[str, Any],
    hierarchy_summary: dict[str, Any],
    hierarchy_filtered: dict[str, Any],
) -> dict[str, Any]:
    out = dict(context or {})
    summary = _as_dict(hierarchy_summary)
    filtered = _as_dict(hierarchy_filtered)
    out["hierarchy_summary_rows_all"] = _as_list(summary.get("rows"))
    out["hierarchy_summary_rows"] = _as_list(filtered.get("rows"))
    out["hierarchy_root_hash"] = _to_text(summary.get("root_hash") or "").strip()
    out["hierarchy_filtered_root_hash"] = _to_text(filtered.get("filtered_root_hash") or "").strip()
    out["hierarchy_root_codes"] = _as_list(summary.get("root_codes"))
    out["chapter_progress"] = _as_dict(summary.get("chapter_progress"))
    out["chapter_progress_percent"] = _as_dict(summary.get("chapter_progress")).get("progress_percent")
    out["hierarchy_filter"] = _as_dict(filtered.get("filter"))
    return out


def resolve_docfinal_credit_participant_did(latest_state: dict[str, Any]) -> str:
    did_gate = _as_dict(_as_dict(latest_state).get("did_gate"))
    return _to_text(
        did_gate.get("user_did")
        or _as_dict(latest_state).get("executor_did")
        or _as_dict(latest_state).get("operator_did")
        or ""
    ).strip()


def attach_docfinal_credit(
    *,
    context: dict[str, Any],
    credit_endorsement: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(context or {})
    credit = _as_dict(credit_endorsement)
    if not credit:
        return out
    out["credit_endorsement"] = credit
    out["credit_score"] = credit.get("score")
    out["credit_grade"] = credit.get("grade")
    out["credit_fast_track_eligible"] = bool(credit.get("fast_track_eligible"))
    out["credit_sample_count"] = _as_dict(credit.get("stats")).get("sample_count")
    return out


def attach_docfinal_sensor(
    *,
    context: dict[str, Any],
    latest_state: dict[str, Any],
) -> dict[str, Any]:
    out = dict(context or {})
    latest_sd = _as_dict(latest_state)
    sensor_hardware = _as_dict(latest_sd.get("sensor_hardware"))
    if not sensor_hardware:
        sensor_hardware = _as_dict(_as_dict(latest_sd.get("measurement")).get("sensor_hardware"))
    if not sensor_hardware:
        return out
    out["sensor_hardware"] = sensor_hardware
    out["sensor_device_sn"] = _to_text(sensor_hardware.get("device_sn") or "").strip()
    out["sensor_calibration_valid_until"] = _to_text(sensor_hardware.get("calibration_valid_until") or "").strip()
    out["sensor_calibration_valid"] = bool(sensor_hardware.get("calibration_valid"))
    return out


def attach_docfinal_geo(
    *,
    context: dict[str, Any],
    latest_state: dict[str, Any],
) -> dict[str, Any]:
    out = dict(context or {})
    latest_sd = _as_dict(latest_state)
    geo_compliance = _as_dict(latest_sd.get("geo_compliance"))
    if not geo_compliance:
        return out
    out["geo_compliance"] = geo_compliance
    out["trust_level"] = _to_text(
        geo_compliance.get("trust_level")
        or latest_sd.get("trust_level")
        or ""
    ).strip()
    out["geo_fence_warning"] = _to_text(
        geo_compliance.get("warning")
        or latest_sd.get("geo_fence_warning")
        or ""
    ).strip()
    return out


def attach_docfinal_biometric(
    *,
    context: dict[str, Any],
    latest_state: dict[str, Any],
) -> dict[str, Any]:
    out = dict(context or {})
    latest_sd = _as_dict(latest_state)
    biometric = _as_dict(latest_sd.get("biometric_verification"))
    if biometric:
        out["biometric_verification"] = biometric
        out["biometric_ok"] = bool(biometric.get("ok"))
        out["biometric_verified_count"] = biometric.get("verified_count")
        out["biometric_required_count"] = biometric.get("required_count")
    signer_metadata = _as_dict(latest_sd.get("signer_metadata"))
    signer_list = _as_list(signer_metadata.get("signers"))
    if signer_list:
        out["signer_metadata"] = signer_metadata
        out["biometric_signer_count"] = len(signer_list)
    return out


def attach_docfinal_lineage_snapshot(
    *,
    context: dict[str, Any],
    lineage_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(context or {})
    lineage = _as_dict(lineage_snapshot)
    if not lineage:
        return out
    out["lineage_total_hash"] = _to_text(lineage.get("total_proof_hash") or "").strip()
    out["lineage_norm_ref_count"] = len(_as_list(lineage.get("norm_refs")))
    out["lineage_evidence_hash_count"] = len(_as_list(lineage.get("evidence_hashes")))
    return out


def attach_docfinal_asset_origin(
    *,
    context: dict[str, Any],
    asset_origin: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(context or {})
    origin = _as_dict(asset_origin)
    if not origin:
        return out
    out["asset_origin"] = origin
    out["asset_origin_statement"] = _to_text(origin.get("statement") or "").strip()
    return out


def attach_docfinal_sealing_trip(
    *,
    context: dict[str, Any],
    sealing_trip: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(context or {})
    trip = _as_dict(sealing_trip)
    if not trip:
        return out
    out["sealing_trip"] = trip
    out["sealing_pattern_id"] = _to_text(trip.get("pattern_id") or "").strip()
    out["sealing_margin_microtext"] = _as_list(trip.get("margin_microtext"))
    out["sealing_scan_hint"] = _to_text(trip.get("scan_hint") or "").strip()
    return out


def finalize_docfinal_context(
    *,
    context: dict[str, Any],
    meta: dict[str, Any] | None,
    transfer_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    out = dict(context or {})
    m = _as_dict(meta)
    if not _to_text(out.get("artifact_uri") or "").strip():
        out["artifact_uri"] = _to_text(m.get("artifact_uri") or "").strip()
    if not _to_text(out.get("gitpeg_anchor") or "").strip():
        out["gitpeg_anchor"] = _to_text(m.get("gitpeg_anchor") or "").strip()
    if transfer_receipt is not None:
        out["asset_transfer"] = transfer_receipt
    return out


__all__ = [
    "build_docfinal_meta",
    "attach_docfinal_risk_audit",
    "attach_docfinal_hierarchy",
    "resolve_docfinal_credit_participant_did",
    "attach_docfinal_credit",
    "attach_docfinal_sensor",
    "attach_docfinal_geo",
    "attach_docfinal_biometric",
    "attach_docfinal_lineage_snapshot",
    "attach_docfinal_asset_origin",
    "attach_docfinal_sealing_trip",
    "finalize_docfinal_context",
]
