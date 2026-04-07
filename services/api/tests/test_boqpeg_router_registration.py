from __future__ import annotations

from services.api.routers import ROUTER_REGISTRY, boqpeg, smu


def test_boqpeg_router_is_registered_on_legacy_and_new_prefixes() -> None:
    prefixes = [item.get("prefix", "") for item in ROUTER_REGISTRY if item.get("router") is boqpeg.router]
    assert "/v1/proof" in prefixes
    assert "/v1/qcspec" in prefixes
    assert "/v1/boqpeg" in prefixes
    assert "/v1/listpeg" in prefixes


def test_boqpeg_public_router_is_registered_on_legacy_and_new_prefixes() -> None:
    prefixes = [item.get("prefix", "") for item in ROUTER_REGISTRY if item.get("router") is boqpeg.public_router]
    assert "/v1/proof" in prefixes
    assert "/v1/qcspec" in prefixes
    assert "/v1/boqpeg" in prefixes
    assert "/v1/listpeg" in prefixes


def test_boqpeg_router_exposes_import_and_preview_paths() -> None:
    paths = {route.path for route in boqpeg.router.routes}
    assert "/boqpeg/import" in paths
    assert "/boqpeg/preview" in paths
    assert "/boqpeg/import-async" in paths
    assert "/boqpeg/import-job/{job_id}" in paths
    assert "/boqpeg/import-job-active" in paths
    assert "/product/manifest" in paths
    assert "/boqpeg/engine/parse" in paths
    assert "/boqpeg/engine/forward-bom" in paths
    assert "/boqpeg/engine/reverse-conservation" in paths
    assert "/boqpeg/engine/payment-progress" in paths
    assert "/boqpeg/engine/unified-align" in paths
    assert "/boqpeg/engine/design/parse" in paths
    assert "/boqpeg/engine/design-boq/match" in paths
    assert "/boqpeg/engine/design-boq/closure" in paths
    assert "/boqpeg/bridge/entity" in paths
    assert "/boqpeg/bridge/bind-sub-items" in paths
    assert "/boqpeg/pile/entity" in paths
    assert "/boqpeg/pile/state" in paths
    assert "/boqpeg/bridge/{bridge_name}/pile/{pile_id}" in paths
    assert "/boqpeg/project/full-line/piles" in paths
    assert "/boqpeg/bridge/{bridge_name}/piles" in paths
    assert "/boqpeg/bridge/{bridge_name}/schedule" in paths
    assert "/boqpeg/bridge/{bridge_name}/schedule/sync" in paths
    assert "/boqpeg/project/full-line/schedule" in paths
    assert "/boqpeg/bridge/{bridge_name}/pile/{pile_id}/process-chain" in paths
    assert "/boqpeg/bridge/{bridge_name}/pile/{pile_id}/process-chain/submit-table" in paths
    assert "/product/mvp/phase1/bridge-pile-report" in paths
    assert "/product/normref/logic-scaffold" in paths
    assert "/product/normref/tab-to-peg" in paths


def test_boqpeg_public_router_exposes_job_query_paths() -> None:
    paths = {route.path for route in boqpeg.public_router.routes}
    assert "/boqpeg/import-job-public/{job_id}" in paths
    assert "/boqpeg/import-job-active-public" in paths


def test_smu_router_keeps_legacy_and_docpeg_prefix_for_genesis_aliases() -> None:
    prefixes = [item.get("prefix", "") for item in ROUTER_REGISTRY if item.get("router") is smu.router]
    assert "/v1/proof" in prefixes
    assert "/v1/docpeg" in prefixes

    paths = {route.path for route in smu.router.routes}
    assert "/smu/genesis/import" in paths
    assert "/smu/genesis/import-async" in paths
