"""Compatibility shim for legacy project-create flow imports.

Prefer importing from ``services.api.domain.projects.create_flow`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.create_flow import create_project_flow

__all__ = ["create_project_flow"]
