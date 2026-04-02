from __future__ import annotations

from services.api.domain.execution import triprole_action_special as special


class _FakeEngine:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None

    def create(self, **kwargs: object) -> dict[str, object]:
        self.created = kwargs
        return {
            "proof_id": str(kwargs.get("proof_id") or ""),
            "proof_hash": "hash-created",
        }


def test_execute_scan_entry_action_uses_scan_state(monkeypatch: object) -> None:
    engine = _FakeEngine()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        special,
        "_build_special_action_context",
        lambda **_: {
            "input_sd": {"existing": "v1", "boq_item_uri": "v://boq/1-1"},
            "project_uri": "v://project/demo",
            "project_id": "p1",
            "owner_uri": "v://owner/demo",
            "segment_uri": "v://segment/1",
            "boq_item_uri": "v://boq/1-1",
            "did_gate": {"ok": True},
            "parent_hash": "parent-hash",
            "now_iso": "2026-01-01T00:00:00Z",
            "anchor": {
                "geo_location": {"lat": 1},
                "server_timestamp_proof": {"ts": "1"},
                "spatiotemporal_anchor_hash": "anchor-1",
            },
            "geo_compliance": {"warning": "", "trust_level": "HIGH"},
        },
    )

    payload = {"status": "ok"}
    out = special.execute_scan_entry_action(
        sb=object(),
        engine=engine,
        input_row={"conditions": []},
        payload=payload,
        input_proof_id="GP-IN-1",
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:1",
        credentials_vc_raw=[],
        segment_uri_override="",
        boq_item_uri_override="",
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
    )

    assert out["ok"] is True
    assert out["proof_type"] == "scan_entry"
    assert out["result"] == "PASS"
    assert out["spatiotemporal_anchor_hash"] == "anchor-1"
    assert engine.created is not None
    state_data = dict(engine.created["state_data"])  # type: ignore[index]
    assert state_data["lifecycle_stage"] == "SCAN_ENTRY"
    assert state_data["scan_entry_hash"]
    assert state_data["scan_entry"]["scan_entry_at"] == "2026-01-01T00:00:00Z"


def test_execute_gateway_style_action_maps_formula_price(monkeypatch: object) -> None:
    engine = _FakeEngine()

    monkeypatch.setattr(  # type: ignore[attr-defined]
        special,
        "_build_special_action_context",
        lambda **_: {
            "input_sd": {"boq_item_uri": "v://boq/1-1"},
            "project_uri": "v://project/demo",
            "project_id": "p1",
            "owner_uri": "v://owner/demo",
            "segment_uri": "v://segment/1",
            "boq_item_uri": "v://boq/1-1",
            "did_gate": {"ok": True},
            "parent_hash": "parent-hash",
            "now_iso": "2026-01-01T00:00:00Z",
            "anchor": {
                "geo_location": {"lat": 1},
                "server_timestamp_proof": {"ts": "1"},
                "spatiotemporal_anchor_hash": "anchor-1",
            },
            "geo_compliance": {"warning": "warn", "trust_level": "LOW"},
        },
    )

    out = special.execute_gateway_style_action(
        sb=object(),
        engine=engine,
        input_row={"conditions": []},
        payload={"status": "fail"},
        action="formula.price",
        input_proof_id="GP-IN-2",
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:2",
        credentials_vc_raw=[],
        segment_uri_override="",
        boq_item_uri_override="",
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
    )

    assert out["ok"] is True
    assert out["proof_type"] == "railpact"
    assert out["result"] == "FAIL"
    assert engine.created is not None
    assert engine.created["norm_uri"] == "v://norm/CoordOS/FormulaPeg/1.0"
    state_data = dict(engine.created["state_data"])  # type: ignore[index]
    assert state_data["lifecycle_stage"] == "PRICING"
    assert state_data["railpact_hash"]


def test_maybe_execute_special_action_routes_scan_entry() -> None:
    called: dict[str, object] = {}

    def _scan_stub(**kwargs: object) -> dict[str, object]:
        called["scan"] = kwargs
        return {"ok": True, "action": "scan.entry"}

    out = special.maybe_execute_special_action(
        action="scan.entry",
        sb=object(),
        engine=object(),
        input_row={},
        payload={},
        input_proof_id="GP-IN-1",
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:1",
        credentials_vc_raw=[],
        segment_uri_override="",
        boq_item_uri_override="",
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
        execute_scan_entry_action_fn=_scan_stub,
        execute_gateway_style_action_fn=lambda **_: {"ok": False},
    )

    assert out == {"ok": True, "action": "scan.entry"}
    assert "scan" in called


def test_maybe_execute_special_action_routes_gateway_actions() -> None:
    called: dict[str, object] = {}

    def _gateway_stub(**kwargs: object) -> dict[str, object]:
        called["gateway"] = kwargs
        return {"ok": True, "action": "formula.price"}

    out = special.maybe_execute_special_action(
        action="formula.price",
        sb=object(),
        engine=object(),
        input_row={},
        payload={},
        input_proof_id="GP-IN-2",
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:2",
        credentials_vc_raw=[],
        segment_uri_override="",
        boq_item_uri_override="",
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
        execute_scan_entry_action_fn=lambda **_: {"ok": False},
        execute_gateway_style_action_fn=_gateway_stub,
    )

    assert out == {"ok": True, "action": "formula.price"}
    assert "gateway" in called


def test_maybe_execute_special_action_returns_none_for_non_special_action() -> None:
    out = special.maybe_execute_special_action(
        action="quality.check",
        sb=object(),
        engine=object(),
        input_row={},
        payload={},
        input_proof_id="GP-IN-3",
        executor_uri="v://executor/system/",
        executor_role="TRIPROLE",
        executor_did="did:example:3",
        credentials_vc_raw=[],
        segment_uri_override="",
        boq_item_uri_override="",
        body_geo_location_raw=None,
        body_server_timestamp_raw=None,
    )
    assert out is None
