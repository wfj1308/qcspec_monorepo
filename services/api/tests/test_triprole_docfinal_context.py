from __future__ import annotations

from services.api.domain.execution.docfinal import triprole_docfinal_context as ctx


def test_build_docfinal_meta_fills_defaults() -> None:
    meta = ctx.build_docfinal_meta(
        project_meta={},
        latest_row={
            "project_uri": "v://project/demo",
            "project_id": "p1",
            "proof_id": "proof-1",
            "gitpeg_anchor": "anchor-x",
        },
        latest_state={"artifact_uri": ""},
        resolve_project_name=lambda project_id: f"name-{project_id}",
    )
    assert meta["project_uri"] == "v://project/demo"
    assert meta["project_name"] == "name-p1"
    assert meta["artifact_uri"] == "v://project/demo/artifact/proof-1"
    assert meta["gitpeg_anchor"] == "anchor-x"


def test_attach_helpers_update_context_shape() -> None:
    context: dict[str, object] = {"total_proof_hash": "h1"}
    context = ctx.attach_docfinal_risk_audit(
        context=context,
        risk_audit={"risk_score": 88.0, "issues": [{"issue": "x"}]},
    )
    assert context["risk_score"] == 88.0
    assert context["risk_issue_count"] == 1
    assert context["risk_audit"]["total_proof_hash"] == "h1"  # type: ignore[index]

    context = ctx.attach_docfinal_hierarchy(
        context=context,
        hierarchy_summary={"rows": [{"code": "1"}], "root_hash": "r1", "root_codes": ["1"], "chapter_progress": {"progress_percent": 12.3}},
        hierarchy_filtered={"rows": [{"code": "1-1"}], "filtered_root_hash": "r2", "filter": {"level": "leaf"}},
    )
    assert context["hierarchy_root_hash"] == "r1"
    assert context["hierarchy_filtered_root_hash"] == "r2"
    assert context["chapter_progress_percent"] == 12.3


def test_credit_sensor_geo_biometric_lineage_asset_sealing_and_finalize() -> None:
    latest_state = {
        "did_gate": {"user_did": "did:example:a"},
        "sensor_hardware": {"device_sn": "SN-1", "calibration_valid_until": "2026-12-31", "calibration_valid": True},
        "geo_compliance": {"trust_level": "HIGH", "warning": ""},
        "biometric_verification": {"ok": True, "verified_count": 3, "required_count": 3},
        "signer_metadata": {"signers": [{"did": "did:1"}]},
    }
    assert ctx.resolve_docfinal_credit_participant_did(latest_state) == "did:example:a"

    context: dict[str, object] = {}
    context = ctx.attach_docfinal_credit(context=context, credit_endorsement={"score": 92, "grade": "A", "fast_track_eligible": True, "stats": {"sample_count": 8}})
    context = ctx.attach_docfinal_sensor(context=context, latest_state=latest_state)
    context = ctx.attach_docfinal_geo(context=context, latest_state=latest_state)
    context = ctx.attach_docfinal_biometric(context=context, latest_state=latest_state)
    context = ctx.attach_docfinal_lineage_snapshot(context=context, lineage_snapshot={"total_proof_hash": "lh", "norm_refs": [1], "evidence_hashes": [1, 2]})
    context = ctx.attach_docfinal_asset_origin(context=context, asset_origin={"statement": "origin-ok"})
    context = ctx.attach_docfinal_sealing_trip(context=context, sealing_trip={"pattern_id": "ptn-1", "margin_microtext": ["m1"], "scan_hint": "hint"})
    context = ctx.finalize_docfinal_context(
        context=context,
        meta={"artifact_uri": "v://a", "gitpeg_anchor": "g1"},
        transfer_receipt={"ok": True},
    )

    assert context["credit_score"] == 92
    assert context["sensor_device_sn"] == "SN-1"
    assert context["trust_level"] == "HIGH"
    assert context["biometric_ok"] is True
    assert context["lineage_total_hash"] == "lh"
    assert context["asset_origin_statement"] == "origin-ok"
    assert context["sealing_pattern_id"] == "ptn-1"
    assert context["artifact_uri"] == "v://a"
    assert context["gitpeg_anchor"] == "g1"
    assert context["asset_transfer"] == {"ok": True}
