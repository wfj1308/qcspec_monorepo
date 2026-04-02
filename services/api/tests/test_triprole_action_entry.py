from __future__ import annotations

from services.api.domain.execution import triprole_action_entry as entry


def test_execute_triprole_action_entry_delegates_to_execute_flow(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_execute_flow(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True, "mode": "delegated"}

    monkeypatch.setattr(entry, "_execute_triprole_action_flow", _fake_execute_flow)

    aggregate_fn = lambda *_args, **_kwargs: {"ok": True}
    out = entry.execute_triprole_action(
        sb=object(),
        body={"action": "quality.check"},
        valid_actions={"quality.check"},
        consensus_required_roles=("contractor", "supervisor", "owner"),
        aggregate_provenance_chain_fn=aggregate_fn,
    )

    assert out == {"ok": True, "mode": "delegated"}
    assert captured["valid_actions"] == {"quality.check"}
    assert captured["consensus_required_roles"] == ("contractor", "supervisor", "owner")
    assert captured["aggregate_provenance_chain_fn"] is aggregate_fn
