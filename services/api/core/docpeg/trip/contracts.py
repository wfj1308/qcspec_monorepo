"""Trip kernel value contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TripExecutionEnvelope:
    trip_id: str
    action: str
    input_proof_id: str
    executor_uri: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    signatures: list[dict[str, Any]] = field(default_factory=list)

