from __future__ import annotations

from services.api.domain.execution.offline.triprole_offline import replay_offline_packet


def test_replay_offline_packet_dispatches_variation_apply() -> None:
    captured: dict[str, object] = {}

    def _apply_variation(**kwargs: object) -> dict[str, object]:
        captured["variation"] = kwargs
        return {"ok": True, "mode": "variation"}

    out = replay_offline_packet(
        sb=object(),
        packet={
            "type": "variation.apply",
            "boq_item_uri": "v://boq/1-1",
            "delta_amount": "2.5",
            "reason": "site adjustment",
            "credentials_vc": [{"id": "vc1"}],
        },
        default_executor_uri="v://executor/system/",
        default_executor_role="TRIPROLE",
        apply_variation_fn=_apply_variation,
        execute_triprole_action_fn=lambda **_: {"ok": False},
    )

    assert out["packet_type"] == "variation.apply"
    assert out["result"] == {"ok": True, "mode": "variation"}
    assert len(str(out["offline_packet_id"])) == 64
    kwargs = dict(captured["variation"])  # type: ignore[arg-type]
    assert kwargs["executor_uri"] == "v://executor/system/"
    assert kwargs["executor_role"] == "TRIPROLE"
    assert kwargs["delta_amount"] == 2.5


def test_replay_offline_packet_dispatches_triprole_execute() -> None:
    captured: dict[str, object] = {}

    def _execute(**kwargs: object) -> dict[str, object]:
        captured["execute"] = kwargs
        return {"ok": True, "mode": "execute"}

    out = replay_offline_packet(
        sb=object(),
        packet={
            "offline_packet_id": "off-1",
            "action": "quality.check",
            "input_proof_id": "GP-IN-1",
            "payload": {"k": "v"},
            "credentials_vc": [{"id": "vc1"}],
        },
        default_executor_uri="v://executor/default/",
        default_executor_role="DEFAULT",
        apply_variation_fn=lambda **_: {"ok": False},
        execute_triprole_action_fn=_execute,
    )

    assert out["offline_packet_id"] == "off-1"
    assert out["packet_type"] == "triprole.execute"
    assert out["result"] == {"ok": True, "mode": "execute"}
    kwargs = dict(captured["execute"])  # type: ignore[arg-type]
    body = dict(kwargs["body"])  # type: ignore[index]
    assert body["action"] == "quality.check"
    assert body["input_proof_id"] == "GP-IN-1"
    assert body["executor_uri"] == "v://executor/default/"
    assert body["executor_role"] == "DEFAULT"
    assert body["offline_packet_id"] == "off-1"
