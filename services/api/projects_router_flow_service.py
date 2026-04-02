"""Compatibility shim for legacy projects router flow imports.

Prefer importing from ``services.api.domain.projects.router_flows`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.router_flows import (
    complete_project_gitpeg_registration_flow as complete_project_gitpeg_registration_router_flow,
    create_project_router_domain_flow as create_project_router_flow,
    delete_project_router_flow as delete_project_flow,
    export_projects_csv_router_flow as export_projects_csv_flow,
    get_project_router_flow as get_project_flow,
    gitpeg_registrar_webhook_flow as gitpeg_registrar_webhook_router_flow,
    list_activity_router_flow as list_activity_flow,
    list_projects_router_flow as list_projects_flow,
    sync_project_autoreg_router_flow as sync_project_autoreg_endpoint_flow,
    update_project_router_flow as update_project_flow,
)

__all__ = [
    "list_projects_flow",
    "list_activity_flow",
    "export_projects_csv_flow",
    "create_project_router_flow",
    "sync_project_autoreg_endpoint_flow",
    "complete_project_gitpeg_registration_router_flow",
    "gitpeg_registrar_webhook_router_flow",
    "get_project_flow",
    "update_project_flow",
    "delete_project_flow",
]
