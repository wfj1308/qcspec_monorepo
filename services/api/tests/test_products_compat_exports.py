from __future__ import annotations

from services.api.domain import BOQPegService
from services.api.domain import BOQService
from services.api.domain import FinanceAuditService
from services.api.domain import ProjectsService
from services.api.products.boqpeg import BOQPegService as BOQPegProductService
from services.api.products.listpeg import BOQPegService as ListPegProductService
from services.api.products.docfinal import DocumentGovernanceService
from services.api.products.normref import list_spu_library
from services.api.products.qcspec import BOQPegService as QCSpecBOQPegService
from services.api.products.qcspec import BOQService as QCSpecBOQService
from services.api.products.qcspec import ProjectsService as QCSpecProjectsService
from services.api.products.railpact import FinanceAuditService as RailPactFinanceAuditService


def test_qcspec_product_exports_match_domain_services() -> None:
    assert QCSpecBOQService is BOQService
    assert QCSpecBOQPegService is BOQPegService
    assert QCSpecProjectsService is ProjectsService


def test_boqpeg_and_listpeg_product_exports_match_domain_service() -> None:
    assert BOQPegProductService is BOQPegService
    assert ListPegProductService is BOQPegService


def test_railpact_product_export_matches_domain_service() -> None:
    assert RailPactFinanceAuditService is FinanceAuditService


def test_docfinal_product_export_resolves_domain_service() -> None:
    assert DocumentGovernanceService.__name__ == "DocumentGovernanceService"


def test_normref_product_export_resolves_specir_function() -> None:
    assert callable(list_spu_library)
