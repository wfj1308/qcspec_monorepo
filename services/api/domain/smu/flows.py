"""Canonical SMU-domain flow entry points."""

from __future__ import annotations

from services.api.domain.smu.integrations import (
    execute_smu_trip,
    freeze_smu,
    get_active_smu_import_job,
    get_governance_context,
    get_smu_import_job,
    import_genesis_trip,
    list_spu_template_library,
    preview_genesis_tree,
    retry_erpnext_push_queue_smu,
    sign_smu_approval,
    start_smu_import_job,
    validate_logic,
)

__all__ = [
    "import_genesis_trip",
    "preview_genesis_tree",
    "start_smu_import_job",
    "get_smu_import_job",
    "get_active_smu_import_job",
    "list_spu_template_library",
    "get_governance_context",
    "execute_smu_trip",
    "sign_smu_approval",
    "validate_logic",
    "freeze_smu",
    "retry_erpnext_push_queue",
    "retry_erpnext_push_queue_smu",
]


def retry_erpnext_push_queue(*, sb, limit: int = 20):
    return retry_erpnext_push_queue_smu(sb=sb, limit=limit)
