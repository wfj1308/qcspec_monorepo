"""Canonical BOQ-domain entry points for audit/history flows.

These wrappers keep domain callers decoupled from legacy module paths.
"""

from __future__ import annotations

from typing import Any

from services.api.domain.boq.integrations import (
    get_item_sovereign_history,
    run_boq_audit_engine,
)

__all__ = ["get_item_sovereign_history", "run_boq_audit_engine"]


def get_item_sovereign_history_flow(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    return get_item_sovereign_history(sb=sb, **kwargs)


def run_boq_audit_engine_flow(*, sb: Any, **kwargs: Any) -> dict[str, Any]:
    return run_boq_audit_engine(sb=sb, **kwargs)
