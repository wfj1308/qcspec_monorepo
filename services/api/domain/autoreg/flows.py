"""Canonical autoreg-domain flow entry points."""

from __future__ import annotations

from services.api.domain.autoreg.integrations import (
    AutoRegisterProjectRequest,
    autoreg_project_flow,
    autoreg_projects_flow,
    normalize_request,
    upsert_autoreg,
)

__all__ = [
    "AutoRegisterProjectRequest",
    "autoreg_project_flow",
    "autoreg_projects_flow",
    "normalize_request",
    "upsert_autoreg",
]
