from __future__ import annotations

from services.api.domain.boqpeg import import_boq_upload_chain


def _sample_csv_bytes() -> bytes:
    csv_text = (
        "item_no,name,unit,division,subdivision,hierarchy,design_quantity,unit_price,approved_quantity\n"
        "403-1-2,Rebar processing and install,t,Bridge,Rebar,Bridge/Rebar,10,100,9.8\n"
    )
    return csv_text.encode("utf-8")


def test_boqpeg_import_minimal_chain_preview() -> None:
    result = import_boq_upload_chain(
        sb=None,
        project_uri="v://project/demo",
        project_id=None,
        upload_file_name="boq.csv",
        upload_content=_sample_csv_bytes(),
        boq_root_uri="v://project/demo/boq/400",
        norm_context_root_uri="v://project/demo/normContext",
        owner_uri="v://project/demo/role/system/",
        bridge_mappings={"403-1-2": "YK0+500-main"},
        dto_role="SUPERVISOR",
        commit=False,
    )
    assert result["ok"] is True
    chain = result["chain"]
    assert chain["preview"]
    assert int(chain.get("leaf_nodes") or 0) >= 1
    assert int(chain.get("total_nodes") or 0) >= int(chain.get("leaf_nodes") or 0)
    validation = chain.get("ref_only_validation") or {}
    assert validation.get("ok") is True
    assert int(validation.get("invalid_leaf_rows") or 0) == 0
    scan_proof = chain.get("scan_complete_proof") or {}
    assert str(scan_proof.get("proof_id") or "").startswith("GP-BOQ-SCAN-")
    assert str(scan_proof.get("proof_hash") or "").strip() != ""
    assert scan_proof.get("committed") is False
    assert int(result.get("boqpeg", {}).get("scan_pairs") or 0) >= 1
    assert int(result.get("boqpeg", {}).get("spu_mappings") or 0) >= 1
    assert str(result.get("boqpeg", {}).get("view_role") or "") == "SUPERVISOR"
    assert len(result.get("scan_results") or []) >= 1
    view = result.get("view") or {}
    assert str(view.get("view_role") or "") == "SUPERVISOR"
    view_items = view.get("boq_items") or []
    assert isinstance(view_items, list)
    assert len(view_items) >= 1
    assert "qc_gate_count" in view_items[0]
    assert "unit_price" not in view_items[0]
    mapping_view = view.get("spu_boq_mappings") or []
    assert isinstance(mapping_view, list)
    assert len(mapping_view) >= 1
    assert "proof_hash" in mapping_view[0]
    smu_view = view.get("smu_units") or []
    assert isinstance(smu_view, list)
    assert len(smu_view) >= 1
    assert "spu_composition" in smu_view[0]
    assert "total_settlement_value" not in smu_view[0]
    spu_mapping = chain.get("spu_boq_mapping") or {}
    assert spu_mapping.get("ok") is True
    assert int(spu_mapping.get("count") or 0) >= 1
    assert isinstance(spu_mapping.get("mappings"), list)
    assert isinstance(spu_mapping.get("mapping_by_boq_uri"), dict)

    leaf = None
    for row in chain["preview"]:
        state = row.get("state_data") or {}
        if bool(state.get("is_leaf")) and str(state.get("item_no") or "").strip() == "403-1-2":
            leaf = state
            break
    assert leaf is not None
    assert str(leaf.get("ref_spu_uri") or "").strip() != ""
    assert str(leaf.get("ref_quota_uri") or "").strip() != ""
    assert str(leaf.get("ref_meter_rule_uri") or "").strip() != ""
    assert str(leaf.get("genesis_hash") or "").strip() != ""
    assert str(leaf.get("utxo_kind") or "").strip() == "BOQ_INITIAL"
    assert str(leaf.get("utxo_state") or "").strip() == "UNSPENT"
    assert str(leaf.get("bridge_uri") or "").strip() != ""

    scan_row = (result.get("scan_results") or [])[0]
    attached_spus = (scan_row.get("initial_utxo") or {}).get("attached_spus") or []
    assert isinstance(attached_spus, list)
    assert len(attached_spus) >= 1
    assert str(attached_spus[0]).startswith("v://")

    graph = result.get("spu_boq_smu_graph") or {}
    counts = graph.get("counts") or {}
    assert int(counts.get("spu") or 0) >= 1
    assert int(counts.get("boq_items") or 0) >= 1
    assert int(counts.get("spu_boq_mappings") or 0) >= 1
    assert int(counts.get("smu") or 0) >= 1
    smu_units = graph.get("smu_units") or []
    assert isinstance(smu_units, list)
    assert len(smu_units) >= 1
    first_smu = smu_units[0]
    assert str(first_smu.get("smu_id") or "").startswith("SMU-")
    assert isinstance(first_smu.get("spu_composition") or [], list)
