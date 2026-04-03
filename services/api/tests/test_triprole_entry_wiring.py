from __future__ import annotations

from services.api.domain.execution.offline import triprole_offline_entry as offline_entry
from services.api.domain.execution.realtime import triprole_realtime_entry as realtime_entry
from services.api.domain.execution.scan import triprole_scan_confirm_entry as scan_entry


def test_offline_entry_wires_default_replay_packet_fn(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_batch(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(offline_entry, "_replay_offline_packets_batch", _fake_batch)

    out = offline_entry.replay_offline_packets(
        sb=object(),
        packets=[{"offline_packet_id": "p-1"}],
        stop_on_error=True,
        default_executor_uri="v://executor/custom/",
        default_executor_role="SUPERVISOR",
        apply_variation_fn=lambda **_kwargs: {},
        execute_triprole_action_fn=lambda **_kwargs: {},
    )

    assert out == {"ok": True}
    assert captured["stop_on_error"] is True
    assert captured["default_executor_uri"] == "v://executor/custom/"
    assert captured["default_executor_role"] == "SUPERVISOR"
    assert captured["replay_offline_packet_fn"] is offline_entry._replay_offline_packet


def test_scan_confirm_entry_forwards_consensus_roles(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_scan_confirm(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(scan_entry, "_execute_scan_confirm_signature", _fake_scan_confirm)

    out = scan_entry.scan_to_confirm_signature(
        sb=object(),
        input_proof_id="GP-IN-1",
        scan_payload="scan://payload",
        scanner_did="did:example:scanner",
        scanner_role="supervisor",
        consensus_required_roles=("contractor", "supervisor", "owner"),
    )

    assert out == {"ok": True}
    assert captured["input_proof_id"] == "GP-IN-1"
    assert captured["consensus_required_roles"] == ("contractor", "supervisor", "owner")


def test_realtime_entry_injects_status_builder(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_fetch(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(realtime_entry, "_fetch_boq_realtime_status", _fake_fetch)
    aggregate = lambda _utxo_id: {"ok": True}

    out = realtime_entry.get_boq_realtime_status(
        sb=object(),
        project_uri="v://project/demo",
        limit=3000,
        aggregate_provenance_chain_fn=aggregate,
    )

    assert out == {"ok": True}
    assert captured["limit"] == 3000
    assert captured["aggregate_provenance_chain_fn"] is aggregate
    assert captured["build_boq_realtime_status_fn"] is realtime_entry._build_boq_realtime_status
