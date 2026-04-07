"""Shared FastAPI dependencies and service providers."""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from services.api.domain.auth.runtime.auth import ensure_no_proxy_for_supabase, require_auth_user
from services.api.core import DIDGuardService, NormRefResolverService, ProofUTXOService
from services.api.core.docpeg import DocPegExecutionGateService
from services.api.domain import (
    AuthService,
    AutoregService,
    BOQService,
    BOQPegService,
    BOQSpecificationService,
    DocumentGovernanceService,
    ERPNextIntegrationService,
    ExecutionService,
    FinanceAuditService,
    InspectionsService,
    IntelligenceService,
    PhotosService,
    ProofApplicationService,
    ProjectsService,
    PublicVerifyService,
    ReportingService,
    SettingsService,
    SMUService,
    TeamService,
    UTXOService,
)
from services.api.domain.specir import SpecirNormRefResolverAdapter
from services.api.infrastructure.database import get_supabase_client
from services.api.infrastructure.document.generator import (
    DocumentGenerator,
    get_document_generator_singleton,
)

security = HTTPBearer()


def get_supabase() -> Client:
    return get_supabase_client()


def get_autoreg_supabase() -> Client:
    return get_supabase_client(
        url_envs=("GITPEG_SUPABASE_URL", "SUPABASE_URL"),
        key_envs=("GITPEG_SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY"),
        error_detail="supabase not configured for autoreg",
    )


def get_supabase_for_auth() -> Client:
    ensure_no_proxy_for_supabase()
    return get_supabase_client()


def get_auth_service(sb: Client = Depends(get_supabase_for_auth)) -> AuthService:
    return AuthService(sb=sb)


def get_utxo_service(sb: Client = Depends(get_supabase)) -> ProofUTXOService:
    return ProofUTXOService(sb=sb)


def get_proof_application_service(sb: Client = Depends(get_supabase)) -> ProofApplicationService:
    return ProofApplicationService(sb=sb)


def get_execution_service(sb: Client = Depends(get_supabase)) -> ExecutionService:
    return ExecutionService(sb=sb)


def get_document_governance_service(sb: Client = Depends(get_supabase)) -> DocumentGovernanceService:
    return DocumentGovernanceService(sb=sb)


def get_boq_service(sb: Client = Depends(get_supabase)) -> BOQService:
    return BOQService(sb=sb)


def get_boqpeg_service(sb: Client = Depends(get_supabase)) -> BOQPegService:
    return BOQPegService(sb=sb)


def get_autoreg_service(sb: Client = Depends(get_autoreg_supabase)) -> AutoregService:
    return AutoregService(sb=sb)


def get_boq_specification_service(sb: Client = Depends(get_supabase)) -> BOQSpecificationService:
    return BOQSpecificationService(sb=sb)


def get_erpnext_integration_service(sb: Client = Depends(get_supabase)) -> ERPNextIntegrationService:
    return ERPNextIntegrationService(sb=sb)


def get_inspections_service(sb: Client = Depends(get_supabase)) -> InspectionsService:
    return InspectionsService(sb=sb)


def get_utxo_application_service(sb: Client = Depends(get_supabase)) -> UTXOService:
    return UTXOService(sb=sb)


def get_smu_service(sb: Client = Depends(get_supabase)) -> SMUService:
    return SMUService(sb=sb)


def get_intelligence_service(sb: Client = Depends(get_supabase)) -> IntelligenceService:
    return IntelligenceService(sb=sb)


def get_reporting_service(sb: Client = Depends(get_supabase)) -> ReportingService:
    return ReportingService(sb=sb)


def get_finance_audit_service(sb: Client = Depends(get_supabase)) -> FinanceAuditService:
    return FinanceAuditService(sb=sb)


def get_photos_service(sb: Client = Depends(get_supabase)) -> PhotosService:
    return PhotosService(sb=sb)


def get_settings_service(sb: Client = Depends(get_supabase)) -> SettingsService:
    return SettingsService(sb=sb)


def get_team_service(sb: Client = Depends(get_supabase)) -> TeamService:
    return TeamService(sb=sb)


def get_public_verify_service(sb: Client = Depends(get_supabase)) -> PublicVerifyService:
    return PublicVerifyService(sb=sb)


def get_projects_service(sb: Client = Depends(get_supabase)) -> ProjectsService:
    return ProjectsService(sb=sb)


@lru_cache(maxsize=1)
def get_normref_resolver() -> NormRefResolverService:
    return NormRefResolverService(
        sb=get_supabase_client(),
        port=SpecirNormRefResolverAdapter(),
    )


def get_document_generator() -> DocumentGenerator:
    return get_document_generator_singleton()


def get_did_guard_service() -> DIDGuardService:
    return DIDGuardService()


def get_docpeg_execution_gate_service(sb: Client = Depends(get_supabase)) -> DocPegExecutionGateService:
    return DocPegExecutionGateService(sb=sb)


def require_auth_identity(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sb: Client = Depends(get_supabase_for_auth),
) -> dict:
    return require_auth_user(token=credentials.credentials, sb=sb)


def require_dto_roles(*roles: str) -> Callable[[dict], dict]:
    def dependency(
        identity: dict = Depends(require_auth_identity),
        guard: DIDGuardService = Depends(get_did_guard_service),
    ) -> dict:
        return guard.require_roles(identity, roles)

    return dependency
