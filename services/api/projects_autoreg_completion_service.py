"""Compatibility shim for legacy projects autoreg-completion imports.

Prefer importing from ``services.api.domain.projects.autoreg_completion`` directly.
"""

from __future__ import annotations

from services.api.domain.projects.autoreg_completion import (
    complete_gitpeg_registration_flow,
    process_gitpeg_webhook,
)

__all__ = [
    "complete_gitpeg_registration_flow",
    "process_gitpeg_webhook",
]
