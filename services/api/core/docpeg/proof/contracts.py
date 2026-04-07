"""Proof kernel value contracts.

These are lightweight protocol-level types used to stabilize module boundaries.
They do not alter current runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ProofKernelRecord:
    proof_id: str
    project_uri: str = ""
    proof_type: str = ""
    state_data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

