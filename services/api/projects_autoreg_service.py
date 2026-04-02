"""Compatibility shim for legacy projects-autoreg flow imports.

Prefer importing from ``services.api.domain.projects.autoreg`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.autoreg import (
    complete_gitpeg_registration_flow,
    process_gitpeg_webhook,
    run_project_autoreg_sync_safe,
    sync_project_autoreg_flow,
)

__all__ = [
    "complete_gitpeg_registration_flow",
    "process_gitpeg_webhook",
    "run_project_autoreg_sync_safe",
    "sync_project_autoreg_flow",
]
