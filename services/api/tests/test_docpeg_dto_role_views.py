from __future__ import annotations

from services.api.core.docpeg import DTORole, Role


def test_dto_role_normalize_with_admin_alias() -> None:
    assert DTORole.normalize("ADMIN") == Role.OWNER
    assert DTORole.normalize("owner") == Role.OWNER
    assert DTORole.normalize("SUPERVISOR") == Role.SUPERVISOR
    assert DTORole.normalize("unknown") == Role.PUBLIC


def test_boq_item_role_views_minimal_exposure() -> None:
    sample = {
        "boq_v_uri": "v://project/demo/boq/400/403-1-2",
        "boq_item_id": "403-1-2",
        "description": "Rebar processing and install",
        "unit": "t",
        "boq_quantity": 9.8,
        "unit_price": 100.0,
        "total_amount": 980.0,
        "bridge_name": "yk0-500-main",
        "attached_spus": ["v://norm/spu/rebar-processing@v1"],
        "norm_refs": ["v://norm/GB50204@2015"],
        "settlement_rules": ["v://norm/meter-rule/rebar-by-ton@v1"],
        "genesis_hash": "hash-demo",
    }
    public = DTORole.boq_item(sample, "PUBLIC").to_dict()
    supervisor = DTORole.boq_item(sample, "SUPERVISOR").to_dict()
    owner = DTORole.boq_item(sample, "OWNER").to_dict()

    assert public["role"] == "PUBLIC"
    assert "unit_price" not in public
    assert "total_amount" not in public

    assert supervisor["role"] == "SUPERVISOR"
    assert supervisor["qc_gate_count"] == 1
    assert "unit_price" not in supervisor

    assert owner["role"] == "OWNER"
    assert owner["unit_price"] == 100.0
    assert owner["total_amount"] == 980.0
    assert owner["settlement_rules"] == ["v://norm/meter-rule/rebar-by-ton@v1"]


def test_spu_mapping_role_views_minimal_exposure() -> None:
    sample = {
        "mapping_id": "SPUMAP-1",
        "boq_item_id": "403-1-2",
        "boq_v_uri": "v://project/demo/boq/400/403-1-2",
        "bridge_uri": "v://project/demo/bridge/yk0-500-main",
        "spu_uri": "v://norm/spu/rebar-processing@v1",
        "capability_type": "quantity_check",
        "norm_ref": "v://norm/meter-rule/rebar-by-ton@v1",
        "weight": "1.0",
        "proof_id": "GP-SPUMAP-1",
        "proof_hash": "hash-demo",
        "source_file": "boq.csv",
    }
    public = DTORole.spu_boq_mapping(sample, "PUBLIC").to_dict()
    supervisor = DTORole.spu_boq_mapping(sample, "SUPERVISOR").to_dict()
    owner = DTORole.spu_boq_mapping(sample, "OWNER").to_dict()

    assert public["role"] == "PUBLIC"
    assert "proof_hash" not in public
    assert "source_file" not in public

    assert supervisor["role"] == "SUPERVISOR"
    assert supervisor["proof_hash"] == "hash-demo"
    assert "source_file" not in supervisor

    assert owner["role"] == "OWNER"
    assert owner["proof_id"] == "GP-SPUMAP-1"
    assert owner["source_file"] == "boq.csv"


def test_smu_role_views_minimal_exposure() -> None:
    sample = {
        "smu_id": "SMU-PIER-001",
        "name": "YK0+500 主桥 3#墩身",
        "component_type": "pier",
        "bridge_uri": "v://project/demo/bridge/yk0-500-main",
        "spu_composition": [
            {"spu_uri": "v://norm/spu/pier-concrete", "quantity": "45.6", "unit": "m3"},
            {"spu_uri": "v://norm/spu/rebar-per-meter", "quantity": "3280", "unit": "kg"},
        ],
        "total_settlement_value": "980000.5",
        "settlement_proof_hash": "proof-hash-demo",
        "sealed_at": "2026-04-07T09:00:00Z",
    }
    public = DTORole.smu(sample, "PUBLIC").to_dict()
    supervisor = DTORole.smu(sample, "SUPERVISOR").to_dict()
    owner = DTORole.smu(sample, "OWNER").to_dict()

    assert public["role"] == "PUBLIC"
    assert public["composition_count"] == 2
    assert "spu_composition" not in public
    assert "total_settlement_value" not in public

    assert supervisor["role"] == "SUPERVISOR"
    assert len(supervisor["spu_composition"]) == 2
    assert supervisor["settlement_proof_hash"] == "proof-hash-demo"
    assert "total_settlement_value" not in supervisor

    assert owner["role"] == "OWNER"
    assert len(owner["spu_composition"]) == 2
    assert owner["total_settlement_value"] == 980000.5
