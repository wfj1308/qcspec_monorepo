"""Business domain exports (lazy-loaded to avoid circular imports)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AuthService",
    "BOQService",
    "BOQPegService",
    "BOQSpecificationService",
    "AutoregService",
    "DocumentGovernanceService",
    "ExecutionService",
    "ERPNextIntegrationService",
    "FinanceAuditService",
    "InspectionsService",
    "IntelligenceService",
    "PhotosService",
    "ProofApplicationService",
    "ProjectsService",
    "ReportingService",
    "SettingsService",
    "SignPegService",
    "LogPegService",
    "SMUService",
    "TeamService",
    "UTXOService",
    "PublicVerifyService",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "AuthService": ("services.api.domain.auth", "AuthService"),
    "BOQService": ("services.api.domain.boq", "BOQService"),
    "BOQPegService": ("services.api.domain.boqpeg", "BOQPegService"),
    "BOQSpecificationService": ("services.api.domain.boq", "BOQSpecificationService"),
    "AutoregService": ("services.api.domain.autoreg", "AutoregService"),
    "DocumentGovernanceService": ("services.api.domain.documents", "DocumentGovernanceService"),
    "ExecutionService": ("services.api.domain.execution", "ExecutionService"),
    "ERPNextIntegrationService": ("services.api.domain.erpnext", "ERPNextIntegrationService"),
    "FinanceAuditService": ("services.api.domain.finance", "FinanceAuditService"),
    "InspectionsService": ("services.api.domain.inspections", "InspectionsService"),
    "IntelligenceService": ("services.api.domain.intelligence", "IntelligenceService"),
    "PhotosService": ("services.api.domain.photos", "PhotosService"),
    "ProofApplicationService": ("services.api.domain.proof", "ProofApplicationService"),
    "ProjectsService": ("services.api.domain.projects", "ProjectsService"),
    "ReportingService": ("services.api.domain.reporting", "ReportingService"),
    "SettingsService": ("services.api.domain.settings", "SettingsService"),
    "SignPegService": ("services.api.domain.signpeg", "SignPegService"),
    "LogPegService": ("services.api.domain.logpeg", "LogPegService"),
    "SMUService": ("services.api.domain.smu", "SMUService"),
    "TeamService": ("services.api.domain.team", "TeamService"),
    "UTXOService": ("services.api.domain.utxo", "UTXOService"),
    "PublicVerifyService": ("services.api.domain.verify", "PublicVerifyService"),
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
