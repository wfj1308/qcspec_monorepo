from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.smu.runtime import smu_docpeg_helpers as docpeg
from services.api.domain.smu.runtime import smu_evidence_helpers as evidence_helpers
from services.api.domain.smu.runtime import smu_execute_helpers as execute_helpers
from services.api.domain.smu.runtime import smu_flow_service as smu_flow
from services.api.domain.smu.runtime import smu_crypto_helpers as crypto_helpers
from services.api.domain.smu.runtime import smu_erp_helpers as erp
from services.api.domain.smu.runtime import smu_freeze_helpers as freeze
from services.api.domain.smu.runtime import smu_genesis_helpers as genesis_helpers
from services.api.domain.smu.runtime import smu_governance_context_helpers as govctx
from services.api.domain.smu.runtime import smu_governance_helpers as gov
from services.api.domain.smu.runtime import smu_primitives as primitives
from services.api.domain.smu.runtime import smu_response_builders as builders
from services.api.domain.smu.runtime import smu_sign_helpers as sign_helpers
from services.api.domain.smu.runtime import smu_state_helpers as state_helpers
from services.api.domain.smu.runtime import smu_validation_helpers as val
from services.api.domain.smu.runtime import smu_trip_helpers as trip


def test_smu_governance_helpers_basic_behaviors() -> None:
    assert gov.container_status_from_stage("INITIAL", "") == "Unspent"
    assert gov.container_status_from_stage("SETTLEMENT", "PASS") == "Approved"
    assert state_helpers.canonical_smu_status("Reviewing") == "DRAFT"
    assert state_helpers.canonical_smu_status("Approved") == "CONFIRMED"
    assert state_helpers.canonical_smu_status("Frozen") == "FROZEN"

    gatekeeper = gov.build_gatekeeper(
        {
            "qc_pass_count": 2,
            "lab_pass_count": 1,
            "ok": True,
            "latest_lab_pass_proof_id": "GP-LAB-1",
        }
    )
    assert gatekeeper["is_compliant"] is True
    assert gatekeeper["lab_ok"] is True
    assert gatekeeper["latest_lab_pass_proof_id"] == "GP-LAB-1"

    threshold_ok = gov.eval_threshold(">=", 10, 11.0)
    assert threshold_ok["ok"] is True
    threshold_fail = gov.eval_threshold("<", 5, 6.0)
    assert threshold_fail["ok"] is False


def test_smu_validation_helpers_build_summary_and_hash() -> None:
    rows = [
        {
            "proof_id": "P1",
            "result": "PASS",
            "state_data": {
                "geo_location": {"lat": 31.2, "lng": 121.5},
                "server_timestamp_proof": {"ntp_server": "pool.ntp.org"},
                "geo_compliance": {"trust_level": "HIGH"},
            },
        },
        {
            "proof_id": "P2",
            "result": "FAIL",
            "state_data": {
                "geo_location": {},
                "server_timestamp_proof": {},
                "geo_compliance": {"trust_level": "LOW"},
            },
        },
    ]
    counts, issues = val.collect_validate_counts_and_issues(rows)
    assert counts["fail_count"] == 1
    assert counts["missing_geo"] == 1
    assert any(x.get("issue") == "low_geo_trust" for x in issues)

    risk = val.calculate_validate_risk_score(
        total=2,
        fail_count=counts["fail_count"],
        low_trust_count=counts["low_trust_count"],
        missing_geo=counts["missing_geo"],
        missing_ntp=counts["missing_ntp"],
        rep_penalty=5.0,
    )
    assert 0.0 <= risk <= 100.0

    summary = val.build_validate_summary(
        total=2,
        counts=counts,
        risk_score=risk,
        qualification={"qualified_leaf_count": 1, "leaf_total": 2, "all_qualified": False},
        qualification_ratio=0.5,
        did_reputation={"aggregate_score": 88.0, "sampling_multiplier": 1.2, "did_count": 3},
    )
    logic_hash = val.build_validate_logic_hash(
        project_uri="v://proj/test",
        smu_id="400-01",
        summary=summary,
    )
    assert isinstance(logic_hash, str)
    assert len(logic_hash) == 64


def test_smu_validation_helpers_scope_and_issue_helpers() -> None:
    rows = [
        {"segment_uri": "v://project/p1/boq/400-01-01", "proof_id": "A"},
        {"segment_uri": "v://project/p1/boq/400-02-01", "proof_id": "B"},
        {"segment_uri": "v://project/p1/smu/400-01", "proof_id": "C"},
    ]
    scoped = val.filter_rows_by_smu_id(rows, "400-01")
    assert [x["proof_id"] for x in scoped] == ["A"]

    did_issues = val.build_did_reputation_issues(
        {
            "high_risk_dids": [
                {"participant_did": "did:example:a", "identity_uri": "v://id/a", "score": 12.3},
            ]
        }
    )
    assert len(did_issues) == 1
    assert did_issues[0]["issue"] == "did_reputation_low"

    ratio = val.calculate_qualification_ratio({"qualified_leaf_count": 2, "leaf_total": 5})
    assert ratio == 0.4
    issue = val.build_unqualified_leaf_issue({"all_qualified": False, "unqualified_leaf_count": 3})
    assert issue and issue["pending_leaf_count"] == 3
    assert val.build_unqualified_leaf_issue({"all_qualified": True}) is None


def test_smu_trip_helpers_sign_inputs() -> None:
    sign_inputs = trip.build_sign_inputs(
        in_id="GP-TEST-1",
        now_iso="2026-04-02T00:00:00+00:00",
        contractor_did="did:example:contractor",
        supervisor_did="did:example:supervisor",
        owner_did="did:example:owner",
        signer_metadata={},
        consensus_values=[{"k": "v"}],
        allowed_deviation=0.1,
        allowed_deviation_percent=1.0,
    )
    signatures = sign_inputs["signatures"]
    assert isinstance(signatures, list)
    assert len(signatures) == 3
    assert sign_inputs["approval_payload"]["approved_from"] == "SMU_APPROVAL_PANEL"
    assert sign_inputs["approval_payload"]["status_target"] == "CONFIRMED"
    assert sign_inputs["approval_payload"]["status_target_legacy"] == "Approved"


def test_smu_trip_helpers_sign_inputs_attaches_sm2_metadata() -> None:
    sign_inputs = trip.build_sign_inputs(
        in_id="GP-TEST-SM2-1",
        now_iso="2026-04-02T00:00:00+00:00",
        contractor_did="did:example:contractor",
        supervisor_did="did:example:supervisor",
        owner_did="did:example:owner",
        signer_metadata={
            "sm2_signatures": [
                {
                    "role": "owner",
                    "did": "did:example:owner",
                    "signature_hex": "ab" * 64,
                    "public_key_hex": "cd" * 64,
                }
            ]
        },
        consensus_values=None,
        allowed_deviation=None,
        allowed_deviation_percent=None,
    )
    owner_sig = [x for x in sign_inputs["signatures"] if x.get("role") == "owner"][0]
    assert owner_sig["signature_scheme"] == "SM2_WITH_HASH_SHA256_FALLBACK"
    assert owner_sig["sm2_signature_hex"] == "ab" * 64
    assert sign_inputs["biometric"]["sm2_required"] is False
    assert "owner" in sign_inputs["biometric"]["sm2_attached_roles"]


def test_smu_trip_helpers_sign_inputs_strict_sm2_rejects_missing_roles() -> None:
    with pytest.raises(HTTPException) as exc:
        trip.build_sign_inputs(
            in_id="GP-TEST-SM2-2",
            now_iso="2026-04-02T00:00:00+00:00",
            contractor_did="did:example:contractor",
            supervisor_did="did:example:supervisor",
            owner_did="did:example:owner",
            signer_metadata={"require_sm2": True, "sm2_signatures": []},
            consensus_values=None,
            allowed_deviation=None,
            allowed_deviation_percent=None,
            sm2_verifier=lambda *_args: True,
        )
    assert exc.value.status_code == 409
    assert "sm2_signature_missing_roles" in str(exc.value.detail)


def test_smu_trip_helpers_sign_inputs_strict_sm2_accepts_all_roles_with_verifier() -> None:
    sign_inputs = trip.build_sign_inputs(
        in_id="GP-TEST-SM2-3",
        now_iso="2026-04-02T00:00:00+00:00",
        contractor_did="did:example:contractor",
        supervisor_did="did:example:supervisor",
        owner_did="did:example:owner",
        signer_metadata={
            "require_sm2": True,
            "sm2_signatures": [
                {
                    "role": "contractor",
                    "did": "did:example:contractor",
                    "signature_hex": "aa" * 64,
                    "public_key_hex": "bb" * 64,
                },
                {
                    "role": "supervisor",
                    "did": "did:example:supervisor",
                    "signature_hex": "cc" * 64,
                    "public_key_hex": "dd" * 64,
                },
                {
                    "role": "owner",
                    "did": "did:example:owner",
                    "signature_hex": "ee" * 64,
                    "public_key_hex": "ff" * 64,
                },
            ],
        },
        consensus_values=None,
        allowed_deviation=None,
        allowed_deviation_percent=None,
        sm2_verifier=lambda *_args: True,
    )
    assert sign_inputs["biometric"]["sm2_required"] is True
    assert sorted(sign_inputs["biometric"]["sm2_attached_roles"]) == ["contractor", "owner", "supervisor"]
    assert all(bool(x.get("sm2_verified")) for x in sign_inputs["signatures"])


def test_smu_trip_helpers_signatures_reject_invalid_did() -> None:
    with pytest.raises(HTTPException):
        trip.build_signatures(
            input_proof_id="GP-TEST-2",
            now_iso="2026-04-02T00:00:00+00:00",
            contractor_did="not-did-format",
            supervisor_did="did:example:supervisor",
            owner_did="did:example:owner",
        )


def test_smu_trip_helpers_export_execute_actions() -> None:
    assert callable(trip.run_execute_actions)


def test_smu_docpeg_helpers_export_smoke() -> None:
    assert callable(docpeg.run_auto_docpeg_after_sign)


def test_smu_erp_helpers_export_smoke() -> None:
    assert callable(erp.push_docpeg_to_erpnext)
    assert callable(erp.create_erpnext_receipt_proof)
    assert callable(erp.retry_erpnext_push_queue)


def test_smu_freeze_helpers_export_smoke() -> None:
    assert callable(freeze.build_freeze_payloads_from_context)
    assert callable(freeze.build_freeze_proof_create_payload)
    assert callable(freeze.build_freeze_proof_id)
    assert callable(freeze.build_freeze_state_data)
    assert callable(freeze.build_freeze_response)
    assert callable(freeze.normalize_freeze_context)
    assert callable(freeze.resolve_freeze_context)


def test_smu_genesis_helpers_export_smoke() -> None:
    assert callable(genesis_helpers.resolve_genesis_roots)
    assert callable(genesis_helpers.initialize_genesis_chain)
    assert callable(genesis_helpers.enrich_genesis_preview_rows)
    assert callable(genesis_helpers.persist_genesis_created_enrichment)


def test_smu_genesis_helpers_roots_resolution() -> None:
    root_uri, norm_root = genesis_helpers.resolve_genesis_roots(
        project_uri="v://project/p1",
        boq_root_uri="",
        norm_context_root_uri="",
    )
    assert root_uri.endswith("/boq/400")
    assert norm_root.endswith("/normContext")


def test_smu_state_helpers_export_smoke() -> None:
    assert callable(state_helpers.smu_id_from_item_code)
    assert callable(state_helpers.canonical_smu_status)
    assert callable(state_helpers.legacy_smu_status)
    assert callable(state_helpers.is_smu_frozen)
    assert callable(state_helpers.resolve_smu_leaf_items)
    assert callable(state_helpers.collect_smu_qualification)
    assert callable(state_helpers.mark_smu_scope_immutable)


def test_smu_evidence_helpers_export_smoke() -> None:
    assert callable(evidence_helpers.resolve_boq_balance)
    assert callable(evidence_helpers.resolve_lab_pass_for_sample)
    assert callable(evidence_helpers.resolve_lab_status)
    assert callable(evidence_helpers.verify_conservation)


def test_smu_primitives_export_smoke() -> None:
    assert callable(primitives.to_text)
    assert callable(primitives.as_dict)
    assert callable(primitives.as_list)
    assert callable(primitives.to_float)
    assert callable(primitives.utc_iso)


def test_smu_crypto_helpers_export_smoke() -> None:
    assert callable(crypto_helpers.attach_sm2_signatures)
    assert callable(crypto_helpers.verify_sm2_signature)


def test_smu_execute_and_sign_helpers_export_smoke() -> None:
    assert callable(execute_helpers.resolve_execute_context)
    assert callable(execute_helpers.enforce_execute_guards)
    assert callable(execute_helpers.build_execute_state_patch)
    assert callable(sign_helpers.normalize_sign_context)
    assert callable(sign_helpers.normalize_sign_inputs)
    assert callable(sign_helpers.normalize_docpeg_bundle)
    assert callable(sign_helpers.resolve_sign_context)
    assert callable(sign_helpers.resolve_sign_docpeg_bundle)
    assert callable(sign_helpers.build_sign_output_patch)
    assert callable(val.resolve_validate_logic)


def test_smu_governance_context_helpers_export_smoke() -> None:
    assert callable(govctx.resolve_governance_payload)
    assert callable(govctx.normalize_governance_payload)
    assert callable(govctx.build_governance_context_response_from_payload)


def test_smu_response_builders_basic_behaviors() -> None:
    preview_items = builders.build_genesis_preview_items(
        [
            {
                "state_data": {
                    "is_leaf": True,
                    "boq_item_uri": "v://p/boq/100-01-01",
                    "item_no": "100-01-01",
                    "item_name": "test item",
                    "unit": "m",
                    "design_quantity": 3,
                    "approved_quantity": 2,
                }
            }
        ]
    )
    assert preview_items and preview_items[0]["item_no"] == "100-01-01"

    execute_bundle = builders.build_execute_quality_bundle(
        project_uri="v://p",
        input_proof_id="GP-1",
        boq_item_uri="v://p/boq/100-01-01",
        smu_id="100-01",
        measurement_data={"values": [1, 2, 3]},
        formula_validation={"status": "PASS"},
        norm_refs=["v://norm/spec/1"],
        geo_location={"lat": 30, "lng": 120},
        server_timestamp_proof={"ntp_server": "pool.ntp.org"},
        executor_did="did:example:executor",
        evidence_hashes=["h1"],
        component_type="generic",
        is_contract_trip=True,
    )
    assert execute_bundle["snappeg_hash"]
    assert execute_bundle["contract_formula_ok"] is True

    sign_response = builders.build_sign_approval_response(
        supervisor_executor_uri="v://executor/supervisor/mobile/",
        supervisor_did="did:example:supervisor",
        in_id="GP-IN",
        out_id="GP-OUT",
        settle={"result": "PASS"},
        lineage_total_hash="root-1",
        item_uri="v://project/p1/boq/100-01-01",
        input_smu_id="100-01",
        docpeg={"ok": True},
        sm2_summary={"required": True, "verified_roles": ["owner"]},
    )
    assert sign_response["container"]["status"] == "CONFIRMED"
    assert sign_response["container"]["status_legacy"] == "Approved"
    assert sign_response["sm2"]["required"] is True

def test_smu_governance_context_helpers_basic_behaviors() -> None:
    payload = govctx.resolve_governance_payload(
        sb=object(),
        project_uri="v://project/p1",
        boq_item_uri="v://project/p1/boq/100-01-01",
        component_type="generic",
        measured_value=1.2,
        latest_unspent_leaf=lambda *_args, **_kwargs: {
            "result": "PASS",
            "state_data": {
                "item_no": "100-01-01",
                "item_name": "demo",
                "design_quantity": 10,
                "approved_quantity": 8,
            },
        },
        resolve_spu_template=lambda *_args, **_kwargs: {"spu_formula": {}, "spu_template_id": "SPU-1"},
        resolve_norm_refs=lambda *_args, **_kwargs: ["v://norm/spec/1"],
        build_spu_formula_audit=lambda **_kwargs: {"status": "PASS"},
        resolve_allowed_roles=lambda *_args, **_kwargs: ["SUPERVISOR"],
        resolve_docpeg_template=lambda *_args, **_kwargs: {"template_path": "/tmp/a"},
        resolve_dynamic_threshold=lambda **_kwargs: {"operator": ">=", "threshold": 1.0},
        eval_threshold=lambda *_args, **_kwargs: {"status": "SUCCESS", "ok": True},
        container_status_from_stage=lambda *_args, **_kwargs: "Reviewing",
        smu_id_from_item_code=lambda *_args, **_kwargs: "100-01",
        is_smu_frozen=lambda **_kwargs: {"frozen": False},
        derive_display_metadata=lambda *_args, **_kwargs: {"unit_project": "A", "subdivision_project": "B", "wbs_path": ""},
        resolve_lab_status=lambda **_kwargs: {"status": "PASS"},
        resolve_dual_pass_gate=lambda **_kwargs: {"ok": True, "qc_pass_count": 1, "lab_pass_count": 1},
        build_gatekeeper=lambda payload: payload,
    )
    assert payload["item_no"] == "100-01-01"
    assert payload["container"].smu_id == "100-01"

    normalized = govctx.normalize_governance_payload(
        payload=payload,
        boq_item_uri="v://project/p1/boq/100-01-01",
        smu_id_from_item_code=lambda *_args, **_kwargs: "100-01",
    )
    assert normalized["item_no"] == "100-01-01"

    response = govctx.build_governance_context_response_from_payload(
        payload=payload,
        boq_item_uri="v://project/p1/boq/100-01-01",
        component_type="generic",
        smu_id_from_item_code=lambda *_args, **_kwargs: "100-01",
        build_governance_context_response=lambda **kwargs: kwargs,
    )
    assert response["item_no"] == "100-01-01"


def test_smu_sign_helpers_build_output_patch() -> None:
    patch = sign_helpers.build_sign_output_patch(
        item_uri="v://project/p1/boq/100-01-01",
        input_smu_id="100-01",
        lineage_total_hash="abc",
        docpeg_document={"ok": True},
        risk_audit={"score": 90},
        erpnext_push={"success": True},
        erpnext_receipt={"proof_id": "GP-ERP-1"},
    )
    assert patch["container"]["status"] == "CONFIRMED"
    assert patch["container"]["status_legacy"] == "Approved"
    assert patch["smu_id"] == "100-01"


def test_smu_validation_and_freeze_context_helpers_basic_behaviors() -> None:
    audit = val.resolve_validate_logic(
        sb=object(),
        project_uri="v://project/p1",
        smu_id="100-01",
        boq_rows=lambda *_args, **_kwargs: [
            {
                "segment_uri": "v://project/p1/boq/100-01-01",
                "proof_id": "P1",
                "result": "PASS",
                "state_data": {
                    "geo_location": {"lat": 30, "lng": 120},
                    "server_timestamp_proof": {"ntp_server": "pool.ntp.org"},
                },
            }
        ],
        build_did_reputation_summary=lambda **_kwargs: {
            "risk_penalty": 0,
            "aggregate_score": 90,
            "sampling_multiplier": 1,
            "did_count": 1,
            "high_risk_dids": [],
        },
        collect_smu_qualification=lambda **_kwargs: {
            "all_qualified": True,
            "qualified_leaf_count": 1,
            "leaf_total": 1,
        },
    )
    assert audit["ok"] is True
    assert audit["smu_id"] == "100-01"

    freeze_ctx = freeze.resolve_freeze_context(
        sb=object(),
        project_uri="v://project/p1",
        smu_id="100-01",
        min_risk_score=60.0,
        is_smu_frozen=lambda **_kwargs: {"frozen": False},
        validate_logic=lambda **_kwargs: {
            "qualification": {"all_qualified": True},
            "summary": {"risk_score": 88},
            "logic_hash": "h",
        },
        build_unit_merkle_snapshot=lambda **_kwargs: {"unit_root_hash": "root-1", "leaf_count": 1},
    )
    assert freeze_ctx["status"] == "PASS"
    assert freeze_ctx["total_proof_hash"] == "root-1"

    freeze_payloads = freeze.build_freeze_payloads_from_context(
        freeze_ctx=freeze_ctx,
        project_uri="v://project/p1",
        smu_id="100-01",
        executor_uri="v://executor/owner/system/",
    )
    assert freeze_payloads["status"] == "PASS"
    assert freeze_payloads["freeze_proof_id"].startswith("GP-SMU-")
