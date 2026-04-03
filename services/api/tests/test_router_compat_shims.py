from __future__ import annotations

from services.api.routers import finance, reporting, reports, settlement


def test_reports_router_shim_points_to_reporting_router() -> None:
    assert reports.router is reporting.router


def test_settlement_router_shim_points_to_finance_router() -> None:
    assert settlement.router is finance.router
