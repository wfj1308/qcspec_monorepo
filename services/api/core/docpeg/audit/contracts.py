"""Audit kernel value contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    event_id: str
    project_uri: str = ""
    category: str = ""
    actor_uri: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

