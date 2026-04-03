from __future__ import annotations

from services.api.domain.execution.docfinal import triprole_docfinal_audit as audit


def test_compute_docfinal_risk_audit_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "resolve_dual_pass_gate",
        lambda **_: {"ok": True},
    )
    monkeypatch.setattr(
        audit,
        "build_did_reputation_summary",
        lambda **_: {"available": False},
    )

    result = audit.compute_docfinal_risk_audit(
        sb=object(),
        project_uri="v://project/demo",
        boq_item_uri="v://boq/1-1-1",
        chain_rows=[
            {
                "proof_id": "p1",
                "created_at": "2026-01-01T00:00:00Z",
                "state_data": {
                    "lifecycle_stage": "ENTRY",
                    "geo_location": {"lat": 30.0, "lng": 120.0},
                    "server_timestamp_proof": {"ntp_server": "pool.ntp.org"},
                },
            },
            {
                "proof_id": "p2",
                "parent_proof_id": "p1",
                "created_at": "2026-01-01T01:00:00Z",
                "state_data": {
                    "lifecycle_stage": "INSTALLATION",
                    "geo_location": {"lat": 30.1, "lng": 120.1},
                    "server_timestamp_proof": {"ntp_server": "pool.ntp.org"},
                },
            },
        ],
    )

    assert result["ok"] is True
    assert result["total"] == 2
    assert result["risk_score"] == 100.0
    assert result["timestamp_conflicts"] == 0
    assert result["stage_conflicts"] == 0
    assert result["missing_geo"] == 0
    assert result["missing_ntp"] == 0
    assert result["issues"] == []


def test_compute_docfinal_risk_audit_penalties_and_issues(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "resolve_dual_pass_gate",
        lambda **_: {"ok": False, "reason": "missing"},
    )
    monkeypatch.setattr(
        audit,
        "build_did_reputation_summary",
        lambda **_: {
            "available": True,
            "risk_penalty": 5.0,
            "sampling_multiplier": 1.3,
            "high_risk_dids": [
                {
                    "participant_did": "did:example:risky",
                    "identity_uri": "v://identity/risky",
                    "score": 45.0,
                }
            ],
        },
    )

    result = audit.compute_docfinal_risk_audit(
        sb=object(),
        project_uri="v://project/demo",
        boq_item_uri="v://boq/1-1-1",
        chain_rows=[
            {
                "proof_id": "p1",
                "created_at": "2026-01-02T00:00:00Z",
                "state_data": {
                    "lifecycle_stage": "INSTALLATION",
                    "geo_compliance": {"trust_level": "LOW"},
                },
            },
            {
                "proof_id": "p2",
                "parent_proof_id": "p1",
                "created_at": "2026-01-01T00:00:00Z",
                "state_data": {
                    "lifecycle_stage": "ENTRY",
                },
            },
        ],
    )

    assert result["risk_score"] < 100.0
    assert result["timestamp_conflicts"] == 1
    assert result["stage_conflicts"] == 1
    assert result["geo_outside_count"] == 1
    assert result["missing_geo"] == 2
    assert result["missing_ntp"] == 2
    assert result["sampling_multiplier"] == 1.3

    issue_names = {item["issue"] for item in result["issues"]}
    assert "dual_pass_gate_missing" in issue_names
    assert "stage_order_conflict" in issue_names
    assert "timestamp_conflict" in issue_names
    assert "geo_outside_boundary" in issue_names
    assert "missing_geo_location" in issue_names
    assert "missing_ntp_proof" in issue_names
    assert "did_reputation_low" in issue_names
