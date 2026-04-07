"""QCSpec product exports (compatibility facade over domain services)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AuthService",
    "AutoregService",
    "BOQService",
    "BOQPegService",
    "BOQSpecificationService",
    "ExecutionService",
    "ERPNextIntegrationService",
    "InspectionsService",
    "IntelligenceService",
    "PhotosService",
    "ProofApplicationService",
    "ProjectsService",
    "ReportingService",
    "SettingsService",
    "SMUService",
    "TeamService",
    "UTXOService",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "AuthService": ("services.api.domain.auth", "AuthService"),
    "AutoregService": ("services.api.domain.autoreg", "AutoregService"),
    "BOQService": ("services.api.domain.boq", "BOQService"),
    "BOQPegService": ("services.api.domain.boqpeg", "BOQPegService"),
    "BOQSpecificationService": ("services.api.domain.boq", "BOQSpecificationService"),
    "ExecutionService": ("services.api.domain.execution", "ExecutionService"),
    "ERPNextIntegrationService": ("services.api.domain.erpnext", "ERPNextIntegrationService"),
    "InspectionsService": ("services.api.domain.inspections", "InspectionsService"),
    "IntelligenceService": ("services.api.domain.intelligence", "IntelligenceService"),
    "PhotosService": ("services.api.domain.photos", "PhotosService"),
    "ProofApplicationService": ("services.api.domain.proof", "ProofApplicationService"),
    "ProjectsService": ("services.api.domain.projects", "ProjectsService"),
    "ReportingService": ("services.api.domain.reporting", "ReportingService"),
    "SettingsService": ("services.api.domain.settings", "SettingsService"),
    "SMUService": ("services.api.domain.smu", "SMUService"),
    "TeamService": ("services.api.domain.team", "TeamService"),
    "UTXOService": ("services.api.domain.utxo", "UTXOService"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
