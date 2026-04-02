"""Inspections-domain integration entry points."""

from __future__ import annotations

from services.api.inspections_service import (
    create_inspection_flow,
    delete_inspection_flow,
    list_inspections_flow,
    project_stats_flow,
)

__all__ = [
    "list_inspections_flow",
    "create_inspection_flow",
    "project_stats_flow",
    "delete_inspection_flow",
]
