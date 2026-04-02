"""Canonical projects-domain dependency exports.

This module centralizes project-domain imports from legacy service modules so
router/domain orchestration can depend on a stable local entry point.
"""

from __future__ import annotations

from services.api.domain.autoreg.flows import (
    AutoRegisterProjectRequest,
    normalize_request as _normalize_request,
    upsert_autoreg as _upsert_autoreg,
)
from services.api.domain.projects.autoreg import (
    complete_gitpeg_registration_flow,
    process_gitpeg_webhook,
    run_project_autoreg_sync_safe,
    sync_project_autoreg_flow,
)
from services.api.domain.projects.create_flow import create_project_flow
from services.api.domain.projects.gitpeg_client import (
    gitpeg_create_registration_session,
    gitpeg_exchange_token,
    gitpeg_get_registration_result,
    gitpeg_get_registration_session,
    gitpeg_registrar_config,
    gitpeg_registrar_ready,
    to_bool,
)
from services.api.domain.projects.profile_normalize import (
    normalize_contract_segs,
    normalize_inspection_types,
    normalize_km_interval,
    normalize_perm_template,
    normalize_seg_type,
    normalize_structures,
    normalize_zero_equipment,
    normalize_zero_materials,
    normalize_zero_personnel,
    normalize_zero_sign_status,
    normalize_zero_subcontracts,
)
from services.api.domain.projects.query import (
    delete_project_data,
    export_projects_csv_text,
    get_project_data,
    list_project_activity_data,
    list_projects_data,
    normalize_project_patch,
    update_project_data,
)
from services.api.domain.erpnext.flows import fetch_erpnext_project_basics

normalize_request = _normalize_request
upsert_autoreg = _upsert_autoreg

__all__ = [
    "AutoRegisterProjectRequest",
    "normalize_request",
    "upsert_autoreg",
    "fetch_erpnext_project_basics",
    "complete_gitpeg_registration_flow",
    "process_gitpeg_webhook",
    "run_project_autoreg_sync_safe",
    "sync_project_autoreg_flow",
    "create_project_flow",
    "to_bool",
    "gitpeg_create_registration_session",
    "gitpeg_exchange_token",
    "gitpeg_get_registration_result",
    "gitpeg_get_registration_session",
    "gitpeg_registrar_config",
    "gitpeg_registrar_ready",
    "normalize_contract_segs",
    "normalize_inspection_types",
    "normalize_km_interval",
    "normalize_perm_template",
    "normalize_seg_type",
    "normalize_structures",
    "normalize_zero_equipment",
    "normalize_zero_materials",
    "normalize_zero_personnel",
    "normalize_zero_sign_status",
    "normalize_zero_subcontracts",
    "delete_project_data",
    "export_projects_csv_text",
    "get_project_data",
    "list_project_activity_data",
    "list_projects_data",
    "normalize_project_patch",
    "update_project_data",
]
