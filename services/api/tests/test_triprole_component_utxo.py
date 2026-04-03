from __future__ import annotations

import hashlib
import json

import pytest
from fastapi import HTTPException

from services.api.domain.execution.component.triprole_component_utxo import (
    ComponentMaterialBinding,
    ComponentUTXO,
    TripRoleAction,
    aggregate_child_components,
    build_component_doc_context,
    build_component_utxo_verification,
    evaluate_component_conservation,
    validate_component_conservation,
)


def test_validate_component_conservation_per_binding() -> None:
    component = ComponentUTXO(
        component_id="BEAM-L3",
        component_uri="v://project/demo/component/BEAM-L3",
        project_uri="v://project/demo",
        kind="precast_beam",
        bom={"steel": 100, "concrete": 20},
        material_bindings=[
            ComponentMaterialBinding(
                material_utxo_id="u-steel-1",
                material_role="steel",
                planned_qty=100,
                actual_qty=99,
                tolerance=2,
            ),
            ComponentMaterialBinding(
                material_utxo_id="u-concrete-1",
                material_role="concrete",
                planned_qty=20,
                actual_qty=21,
                tolerance=0.5,
            ),
        ],
    )
    result = validate_component_conservation(component)
    assert result["within_tolerance"] is False
    assert len(result["materials"]) == 2
    assert result["by_role"]["steel"]["actual"] == 99.0
    assert result["by_role"]["concrete"]["planned"] == 20.0


def test_aggregate_child_components_recursive() -> None:
    root = ComponentUTXO(
        component_id="ROOT",
        component_uri="v://project/demo/component/ROOT",
        project_uri="v://project/demo",
        kind="bridge_substructure",
        bom={"steel": 10},
        child_components=[
            "v://project/demo/component/C1",
            "v://project/demo/component/C2",
        ],
        material_bindings=[
            ComponentMaterialBinding(
                material_utxo_id="u-root-steel",
                material_role="steel",
                planned_qty=10,
                actual_qty=10,
            )
        ],
    )
    child1 = ComponentUTXO(
        component_id="C1",
        component_uri="v://project/demo/component/C1",
        project_uri="v://project/demo",
        kind="pile_cap",
        bom={"steel": 3},
        material_bindings=[
            ComponentMaterialBinding(
                material_utxo_id="u-c1-steel",
                material_role="steel",
                planned_qty=3,
                actual_qty=2,
            )
        ],
    )
    child2 = ComponentUTXO(
        component_id="C2",
        component_uri="v://project/demo/component/C2",
        project_uri="v://project/demo",
        kind="pile_cap",
        bom={"concrete": 6},
        material_bindings=[
            ComponentMaterialBinding(
                material_utxo_id="u-c2-concrete",
                material_role="concrete",
                planned_qty=6,
                actual_qty=6,
            )
        ],
    )
    agg = aggregate_child_components(
        {
            root.component_uri: root,
            child1.component_uri: child1,
            child2.component_uri: child2,
        },
        root.component_uri,
    )
    assert agg["total_materials"]["steel"] == 12.0
    assert agg["total_materials"]["concrete"] == 6.0
    assert len(agg["children"]) == 2


def test_triprole_action_executes_immutable_component_version() -> None:
    original = ComponentUTXO(
        component_id="BEAM-L3",
        component_uri="v://project/demo/component/BEAM-L3",
        project_uri="v://project/demo",
        kind="precast_beam",
        bom={"steel": 10},
        status="PENDING",
        version=1,
        material_bindings=[
            ComponentMaterialBinding(
                material_utxo_id="u-steel-1",
                material_role="steel",
                planned_qty=10,
                actual_qty=10,
                tolerance=0.1,
            )
        ],
    )
    action = TripRoleAction(
        trip_id="TRIP-001",
        action="quality.check",
        executor_uri="v://executor/qc/alice",
        component_uri=original.component_uri,
    )
    updated = action.execute(original)
    assert original.version == 1
    assert updated.version == 2
    assert updated.status == "QUALIFIED"
    assert updated.last_trip_id == "TRIP-001"
    assert updated.proof_hash.startswith("COMP-")


def test_build_component_utxo_verification_supports_recursive_and_trip_action() -> None:
    payload = build_component_utxo_verification(
        sb=object(),
        component_id="BEAM-L3",
        component_uri="v://project/demo/component/BEAM-L3",
        project_uri="v://project/demo",
        kind="precast_beam",
        bom=[
            {"material_role": "steel", "qty": 1885, "tolerance_ratio": 0.03},
            {"material_role": "concrete", "qty": 23.6, "tolerance_ratio": 0.03},
        ],
        material_bindings=[
            {
                "material_utxo_id": "u-steel",
                "material_role": "steel",
                "planned_qty": 1885,
                "actual_qty": 1880,
                "tolerance": 60,
                "proof_hash": "a" * 64,
            },
            {
                "material_utxo_id": "u-concrete",
                "material_role": "concrete",
                "planned_qty": 23.6,
                "actual_qty": 23.5,
                "tolerance": 1,
                "proof_hash": "b" * 64,
            },
        ],
        child_components=["v://project/demo/component/C1"],
        component_nodes=[
            {
                "component_id": "C1",
                "component_uri": "v://project/demo/component/C1",
                "project_uri": "v://project/demo",
                "kind": "pile_cap",
                "bom": {"steel": 10},
                "material_bindings": [
                    {
                        "material_utxo_id": "u-child-steel",
                        "material_role": "steel",
                        "planned_qty": 10,
                        "actual_qty": 9,
                        "tolerance": 1,
                    }
                ],
            }
        ],
        trip_id="TRIP-002",
        trip_action="quality.check",
        trip_executor_uri="v://executor/qc/bob",
        include_docx_base64=False,
    )
    assert payload["ok"] is True
    assert payload["passed"] is True
    assert payload["status"] == "QUALIFIED"
    assert payload["version"] == 2
    assert payload["proof_hash"].startswith("COMP-")
    assert payload["trip_execution"]["after"]["status"] == "QUALIFIED"
    assert payload["recursive_totals"]["total_materials"]["steel"] == 1889.0
    assert payload["doc_context"]["component_uri"] == "v://project/demo/component/BEAM-L3"
    assert payload["docpeg_request"]["template_key"] == "component_conservation_report"
    assert payload["docpeg_bundle"]["ok"] is True
    assert payload["docpeg_bundle"]["proof_embedded"] is True


def test_component_doc_context_contains_proof_fields() -> None:
    component = ComponentUTXO(
        component_id="BEAM-L3",
        component_uri="v://project/demo/component/BEAM-L3",
        project_uri="v://project/demo",
        kind="precast_beam",
        bom={"steel": 1},
        status="ACCEPTED",
        version=3,
        proof_hash="COMP-ABC",
        last_trip_id="TRIP-9",
        last_action="structure.accept",
    )
    context = build_component_doc_context(
        component,
        {
            "materials": [{"material_role": "steel"}],
            "within_tolerance": True,
            "total_delta": 0.0,
        },
    )
    assert context["proof_hash"] == "COMP-ABC"
    assert context["last_trip"] == "TRIP-9"
    assert context["action"] == "structure.accept"


def test_evaluate_component_conservation_uses_normref_and_binding_override() -> None:
    component = ComponentUTXO(
        component_id="BEAM-L3",
        component_uri="v://project/demo/component/BEAM-L3",
        project_uri="v://project/demo",
        kind="precast_beam",
        bom={"steel": 1885, "concrete": 23.6},
        material_bindings=[
            ComponentMaterialBinding(
                material_utxo_id="u-steel",
                material_role="steel",
                planned_qty=1885,
                actual_qty=1905,
                tolerance_spec_uri="v://norm/bridge/steel_ratio",
            ),
            ComponentMaterialBinding(
                material_utxo_id="u-concrete",
                material_role="concrete",
                planned_qty=23.6,
                actual_qty=24.8,
                tolerance=1.5,
            ),
        ],
    )

    def _fake_resolve(uri: str, _ctx: dict[str, object]) -> dict[str, object]:
        if uri == "v://norm/bridge/steel_ratio":
            return {"tolerance": 0.02}
        return {}

    result = evaluate_component_conservation(
        component,
        default_tolerance_ratio=0.01,
        resolve_norm_rule_fn=_fake_resolve,
    )
    by_role = {item["material_role"]: item for item in result["materials"]}
    assert by_role["steel"]["tolerance_source"] == "v://norm/bridge/steel_ratio"
    assert by_role["steel"]["within_tolerance"] is True
    assert by_role["concrete"]["tolerance_source"] == "binding_absolute"
    assert by_role["concrete"]["tolerance_ratio"] > 0.06
    assert by_role["concrete"]["within_tolerance"] is True
    assert result["within_tolerance"] is True


def test_aggregate_child_components_detects_cycle() -> None:
    a = ComponentUTXO(
        component_id="A",
        component_uri="v://project/demo/component/A",
        project_uri="v://project/demo",
        kind="beam",
        bom={"steel": 1},
        child_components=["v://project/demo/component/B"],
    )
    b = ComponentUTXO(
        component_id="B",
        component_uri="v://project/demo/component/B",
        project_uri="v://project/demo",
        kind="beam",
        bom={"steel": 1},
        child_components=["v://project/demo/component/A"],
    )
    with pytest.raises(HTTPException) as exc:
        aggregate_child_components(
            {
                a.component_uri: a,
                b.component_uri: b,
            },
            a.component_uri,
        )
    assert exc.value.status_code == 409
    assert "component recursion cycle detected" in str(exc.value)


def test_build_component_utxo_verification_uses_material_inputs_as_primary() -> None:
    payload = build_component_utxo_verification(
        sb=object(),
        component_id="BEAM-L3",
        component_uri="v://project/demo/component/BEAM-L3",
        project_uri="v://project/demo",
        kind="precast_beam",
        boq_items=[
            {
                "item_id": "403-1-2",
                "description": "Rebar fabrication and installation",
                "unit": "kg",
                "qty": 1885,
                "unit_price": 5.8,
            },
            {
                "item_id": "404-2-1",
                "description": "Concrete casting",
                "unit": "m3",
                "qty": 23.6,
                "unit_price": 460,
            },
        ],
        bom={"steel": 1885, "concrete": 23.6},
        material_inputs=[
            {
                "utxo_id": "UTXO-STEEL-20",
                "material_role": "steel",
                "qty": 1200,
                "proof_hash": "a" * 64,
                "boq_item_id": "403-1-2",
            },
            {
                "utxo_id": "UTXO-STEEL-16",
                "material_role": "steel",
                "qty": 685,
                "proof_hash": "b" * 64,
                "boq_item_id": "403-1-2",
            },
            {
                "utxo_id": "UTXO-CONCRETE-C40",
                "material_role": "concrete",
                "qty": 23.6,
                "proof_hash": "c" * 64,
                "boq_item_id": "404-2-1",
            },
        ],
        include_docx_base64=False,
    )

    assert payload["ok"] is True
    assert payload["passed"] is True
    by_role = {item["material_role"]: item for item in payload["materials"]}
    assert by_role["steel"]["actual"] == 1885.0
    assert by_role["steel"]["planned"] == 1885.0
    assert by_role["steel"]["source_input_count"] == 2
    assert set(by_role["steel"]["material_input_utxo_ids"]) == {"UTXO-STEEL-20", "UTXO-STEEL-16"}
    assert by_role["concrete"]["actual"] == 23.6
    assert payload["boq_items"][0]["item_id"] == "403-1-2"
    assert len(payload["material_inputs"]) == 3


def test_component_proof_factors_hash_all_material_input_chain_items() -> None:
    payload = build_component_utxo_verification(
        sb=object(),
        component_id="PIER-P2",
        component_uri="v://project/demo/component/PIER-P2",
        project_uri="v://project/demo",
        kind="pier",
        bom={"steel": 10},
        material_inputs=[
            {"utxo_id": "u1", "material_role": "steel", "qty": 4, "proof_hash": "1" * 64},
            {"utxo_id": "u2", "material_role": "steel", "qty": 6, "proof_hash": "2" * 64},
        ],
        include_docx_base64=False,
    )
    expected_chain_items = [
        {"utxo_id": "u1", "material_role": "steel", "qty": 4.0, "proof_hash": "1" * 64},
        {"utxo_id": "u2", "material_role": "steel", "qty": 6.0, "proof_hash": "2" * 64},
    ]
    expected_hash = hashlib.sha256(
        json.dumps(expected_chain_items, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    assert payload["proof_factors"]["material_chain_root_hash"] == expected_hash
