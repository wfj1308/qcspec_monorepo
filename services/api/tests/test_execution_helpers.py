from __future__ import annotations

from types import SimpleNamespace

from services.api.domain.execution import helpers


class _ModelPacket:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return dict(self._payload)


def test_replay_offline_packets_flow_normalizes_packets_and_defaults(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_replay_offline_packets(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True, "count": len(kwargs.get("packets", []))}

    monkeypatch.setattr(helpers, "replay_offline_packets", _fake_replay_offline_packets)

    body = SimpleNamespace(
        packets=[_ModelPacket({"id": "p-1"}), {"id": "p-2"}],
        stop_on_error=False,
        default_executor_uri="",
        default_executor_role="",
    )
    out = helpers.replay_offline_packets_flow(body=body, sb=object())

    assert out == {"ok": True, "count": 2}
    assert captured["packets"] == [{"id": "p-1"}, {"id": "p-2"}]
    assert captured["stop_on_error"] is False
    assert captured["default_executor_uri"] == "v://executor/system/"
    assert captured["default_executor_role"] == "TRIPROLE"


def test_replay_offline_packets_flow_respects_override_values(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_replay_offline_packets(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(helpers, "replay_offline_packets", _fake_replay_offline_packets)

    body = SimpleNamespace(
        packets=[],
        stop_on_error=True,
        default_executor_uri="v://executor/custom/",
        default_executor_role="SUPERVISOR",
    )
    helpers.replay_offline_packets_flow(body=body, sb=object())

    assert captured["stop_on_error"] is True
    assert captured["default_executor_uri"] == "v://executor/custom/"
    assert captured["default_executor_role"] == "SUPERVISOR"
