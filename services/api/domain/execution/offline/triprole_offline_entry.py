"""Offline replay entry wiring."""

from __future__ import annotations

from typing import Any, Callable

from services.api.domain.execution.offline.triprole_offline import (
    replay_offline_packet as _replay_offline_packet,
    replay_offline_packets_batch as _replay_offline_packets_batch,
)


def replay_offline_packets(
    *,
    sb: Any,
    packets: list[dict[str, Any]],
    stop_on_error: bool = False,
    default_executor_uri: str = "v://executor/system/",
    default_executor_role: str = "TRIPROLE",
    apply_variation_fn: Callable[..., dict[str, Any]],
    execute_triprole_action_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    return _replay_offline_packets_batch(
        sb=sb,
        packets=packets,
        stop_on_error=stop_on_error,
        default_executor_uri=default_executor_uri,
        default_executor_role=default_executor_role,
        apply_variation_fn=apply_variation_fn,
        execute_triprole_action_fn=execute_triprole_action_fn,
        replay_offline_packet_fn=_replay_offline_packet,
    )
