"""Compatibility shim for legacy projects query/payload helper imports.

Prefer importing from ``services.api.domain.projects.query`` and
``services.api.domain.projects.payloads`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.payloads import build_project_create_payload
from services.api.domain.projects.query import (
    delete_project_data,
    export_projects_csv_text,
    get_project_data,
    list_project_activity_data,
    list_projects_data,
    normalize_project_patch,
    update_project_data,
)

__all__ = [
    "list_projects_data",
    "list_project_activity_data",
    "export_projects_csv_text",
    "get_project_data",
    "normalize_project_patch",
    "update_project_data",
    "delete_project_data",
    "build_project_create_payload",
]
