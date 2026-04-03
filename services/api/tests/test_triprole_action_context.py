from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.domain.execution.actions.triprole_action_context import build_triprole_action_context


def test_build_triprole_action_context_success() -> None:
    input_row = {
        "project_uri": "v://project/demo",
        "project_id": "p1",
        "owner_uri": "v://owner/demo",
        "proof_hash": "hash-1",
        "state_data": {
            "boq_item_uri": "v://boq/1-1",
            "trust_level": "MEDIUM",
        },
    }

    context = build_triprole_action_context(
        sb=object(),
        input_row=input_row,
        payload={"k": "v"},
        action="measure.record",
        input_proof_id="GP-1",
        executor_uri="v://executor/system/",
        executor_did="did:example:executor",
        credentials_vc_raw=[{"id": "vc1"}],
        signer_metadata_raw={"signers": [{"role": "owner"}]},
        body_geo_location_raw={"lat": 1},
        body_server_timestamp_raw={"ts": "1"},
        segment_uri_override="",
        boq_item_uri_override="",
        resolve_required_credential_fn=lambda **_: "cred-x",
        verify_credential_fn=lambda **_: {"ok": True, "required_credential": "cred-x"},
        resolve_segment_uri_fn=lambda *_: "v://segment/1",
        resolve_boq_item_uri_fn=lambda *_: "v://boq/1-1",
        resolve_subitem_gate_binding_fn=lambda **_: {
            "linked_gate_id": "gate-1",
            "linked_gate_ids": ["gate-1"],
            "linked_gate_rules": ["r1"],
            "linked_spec_uri": "v://norm/spec/1",
            "spec_dict_key": "k1",
            "spec_item": "i1",
            "gate_template_lock": True,
            "gate_binding_hash": "gbh1",
        },
        build_spatiotemporal_anchor_fn=lambda **_: {
            "geo_location": {"lat": 1},
            "server_timestamp_proof": {"ts": "1"},
            "spatiotemporal_anchor_hash": "anchor-1",
        },
        normalize_signer_metadata_fn=lambda _raw: {"signers": [{"role": "owner"}], "metadata_hash": "m1"},
        resolve_project_boundary_fn=lambda **_: {"enforced": False},
        check_location_compliance_fn=lambda _geo, _boundary: {
            "trust_level": "HIGH",
            "warning": "",
            "outside": False,
        },
    )

    assert context["project_uri"] == "v://project/demo"
    assert context["segment_uri"] == "v://segment/1"
    assert context["boq_item_uri"] == "v://boq/1-1"
    assert context["did_gate"]["ok"] is True
    assert context["gate_binding"]["linked_gate_id"] == "gate-1"
    assert context["anchor"]["spatiotemporal_anchor_hash"] == "anchor-1"
    assert context["geo_compliance"]["trust_level"] == "HIGH"

    next_state = context["next_state"]
    assert next_state["trip_action"] == "measure.record"
    assert next_state["boq_item_uri"] == "v://boq/1-1"
    assert next_state["linked_gate_id"] == "gate-1"
    assert next_state["linked_spec_uri"] == "v://norm/spec/1"
    assert next_state["trust_level"] == "HIGH"
    assert next_state["signer_metadata"]["metadata_hash"] == "m1"


def test_build_triprole_action_context_rejects_failed_did_gate() -> None:
    with pytest.raises(HTTPException) as exc:
        build_triprole_action_context(
            sb=object(),
            input_row={"state_data": {}},
            payload={},
            action="measure.record",
            input_proof_id="GP-1",
            executor_uri="v://executor/system/",
            executor_did="did:example:executor",
            credentials_vc_raw=[],
            signer_metadata_raw={},
            body_geo_location_raw=None,
            body_server_timestamp_raw=None,
            segment_uri_override="",
            boq_item_uri_override="",
            resolve_required_credential_fn=lambda **_: "cred-x",
            verify_credential_fn=lambda **_: {"ok": False, "reason": "missing", "required_credential": "cred-x"},
            resolve_segment_uri_fn=lambda *_: "",
            resolve_boq_item_uri_fn=lambda *_: "v://boq/1-1",
            resolve_subitem_gate_binding_fn=lambda **_: {},
            build_spatiotemporal_anchor_fn=lambda **_: {},
            normalize_signer_metadata_fn=lambda _raw: {},
            resolve_project_boundary_fn=lambda **_: {},
            check_location_compliance_fn=lambda _geo, _boundary: {},
        )

    assert exc.value.status_code == 403
    assert "DID gate rejected" in str(exc.value.detail)
