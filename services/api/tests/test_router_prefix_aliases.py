from __future__ import annotations

from services.api.routers import ROUTER_REGISTRY


def test_legacy_proof_prefix_stays_registered() -> None:
    prefixes = {item.get("prefix", "") for item in ROUTER_REGISTRY}
    assert "/v1/proof" in prefixes


def test_new_structured_prefixes_registered() -> None:
    prefixes = {item.get("prefix", "") for item in ROUTER_REGISTRY}
    assert "/v1/docpeg/proof" in prefixes
    assert "/v1/docpeg" in prefixes
    assert "/v1/qcspec" in prefixes
    assert "/v1/docfinal" in prefixes
    assert "/v1/railpact" in prefixes
    assert "/v1/normref" in prefixes
    assert "/api/normref" in prefixes
    assert "/v1/normref/specir" in prefixes
