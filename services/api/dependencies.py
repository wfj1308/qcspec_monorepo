"""Shared FastAPI dependencies and service providers."""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from services.api.auth_service import ensure_no_proxy_for_supabase, require_auth_user
from services.api.core import DIDGuardService, NormRefResolverService, ProofUTXOService
from services.api.domain import (
    BOQService,
    DocumentGovernanceService,
    ExecutionService,
    FinanceAuditService,
    IntelligenceService,
    ProofApplicationService,
    ReportingService,
    SMUService,
    UTXOService,
)
from services.api.infrastructure.database import get_supabase_client
from services.api.infrastructure.document.generator import (
    DocumentGenerator,
    get_document_generator_singleton,
)

security = HTTPBearer()


def get_supabase() -> Client:
    return get_supabase_client()


def get_supabase_for_auth() -> Client:
    ensure_no_proxy_for_supabase()
    return get_supabase_client()


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


@lru_cache(maxsize=1)
def get_normref_resolver() -> NormRefResolverService:
    return NormRefResolverService(sb=get_supabase_client())


def get_document_generator() -> DocumentGenerator:
    return get_document_generator_singleton()


def get_did_guard_service() -> DIDGuardService:
    return DIDGuardService()


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
