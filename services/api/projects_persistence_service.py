"""Compatibility shim for legacy project persistence imports.

Prefer importing from ``services.api.domain.projects.persistence`` directly.
"""

from __future__ import annotations

from services.api.domain.projects import persistence as _project_persistence


def _ordered_unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


extract_missing_column_name = _project_persistence.extract_missing_column_name
insert_project_with_schema_fallback = _project_persistence.insert_project_with_schema_fallback
project_zero_ledger_mismatch = _project_persistence.project_zero_ledger_mismatch
_extract_missing_column_name = _project_persistence._extract_missing_column_name
_insert_project_with_schema_fallback = _project_persistence._insert_project_with_schema_fallback
_project_zero_ledger_mismatch = _project_persistence._project_zero_ledger_mismatch
create_project_record = _project_persistence.create_project_record
reconcile_created_project = _project_persistence.reconcile_created_project

_create_project_record = create_project_record
_reconcile_created_project = reconcile_created_project

__all__ = _ordered_unique(
    [
        *_project_persistence.__all__,
        "_create_project_record",
        "_reconcile_created_project",
    ]
)
