from __future__ import annotations

from fastapi import HTTPException

from services.api.domain.execution.offline.triprole_offline import replay_offline_packets_batch


def test_replay_offline_packets_batch_success() -> None:
    out = replay_offline_packets_batch(
        sb=object(),
        packets=[
            {"offline_packet_id": "off-1", "type": "triprole.execute"},
            {"offline_packet_id": "off-2", "type": "variation.apply"},
        ],
        stop_on_error=False,
        default_executor_uri="v://executor/system/",
        default_executor_role="TRIPROLE",
        apply_variation_fn=lambda **_: {"ok": True},
        execute_triprole_action_fn=lambda **_: {"ok": True},
        replay_offline_packet_fn=lambda **kwargs: {
            "offline_packet_id": kwargs["packet"]["offline_packet_id"],  # type: ignore[index]
            "packet_type": kwargs["packet"].get("type"),  # type: ignore[index]
            "result": {"ok": True},
        },
        sort_key_fn=lambda packet: (0, 0, str(packet.get("offline_packet_id") or "")),
    )

    assert out["ok"] is True
    assert out["replayed_count"] == 2
    assert out["error_count"] == 0
    assert out["results"][0]["offline_packet_id"] == "off-1"


def test_replay_offline_packets_batch_http_error_keeps_packet_context() -> None:
    def _replay_stub(**kwargs: object) -> dict[str, object]:
        packet = kwargs["packet"]  # type: ignore[index]
        if packet.get("offline_packet_id") == "off-err":
            raise HTTPException(409, "bad packet")
        return {
            "offline_packet_id": packet.get("offline_packet_id"),
            "packet_type": packet.get("type") or "triprole.execute",
            "result": {"ok": True},
        }

    out = replay_offline_packets_batch(
        sb=object(),
        packets=[
            {"offline_packet_id": "off-err", "type": "variation.apply"},
            {"offline_packet_id": "off-ok", "type": "triprole.execute"},
        ],
        stop_on_error=False,
        default_executor_uri="v://executor/system/",
        default_executor_role="TRIPROLE",
        apply_variation_fn=lambda **_: {"ok": True},
        execute_triprole_action_fn=lambda **_: {"ok": True},
        replay_offline_packet_fn=_replay_stub,
        sort_key_fn=lambda packet: (0, 0, str(packet.get("offline_packet_id") or "")),
    )

    assert out["ok"] is False
    assert out["error_count"] == 1
    assert out["replayed_count"] == 1
    assert out["errors"][0]["offline_packet_id"] == "off-err"
    assert out["errors"][0]["packet_type"] == "variation.apply"
    assert out["errors"][0]["status_code"] == 409


def test_replay_offline_packets_batch_stop_on_error_breaks_loop() -> None:
    calls = {"count": 0}

    def _replay_stub(**kwargs: object) -> dict[str, object]:
        calls["count"] += 1
        packet = kwargs["packet"]  # type: ignore[index]
        if packet.get("offline_packet_id") == "off-err":
            raise HTTPException(400, "stop")
        return {
            "offline_packet_id": packet.get("offline_packet_id"),
            "packet_type": packet.get("type") or "triprole.execute",
            "result": {"ok": True},
        }

    out = replay_offline_packets_batch(
        sb=object(),
        packets=[
            {"offline_packet_id": "off-err", "type": "triprole.execute"},
            {"offline_packet_id": "off-next", "type": "triprole.execute"},
        ],
        stop_on_error=True,
        default_executor_uri="v://executor/system/",
        default_executor_role="TRIPROLE",
        apply_variation_fn=lambda **_: {"ok": True},
        execute_triprole_action_fn=lambda **_: {"ok": True},
        replay_offline_packet_fn=_replay_stub,
        sort_key_fn=lambda packet: (0, 0, str(packet.get("offline_packet_id") or "")),
    )

    assert calls["count"] == 1
    assert out["error_count"] == 1
    assert out["replayed_count"] == 0
