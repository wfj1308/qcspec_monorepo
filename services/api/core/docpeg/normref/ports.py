"""Ports for NormRef resolver kernel."""

from __future__ import annotations

from typing import Any, Protocol


class NormRefResolverPort(Protocol):
    def resolve_threshold(self, *, sb: Any, gate_id: str, context: Any = "") -> dict[str, Any]:
        ...

    def get_spec_dict(self, *, sb: Any, spec_dict_key: str) -> dict[str, Any]:
        ...

