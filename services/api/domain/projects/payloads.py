"""Canonical projects payload builders."""

from __future__ import annotations

from typing import Any, Callable, Optional


def build_project_create_payload(
    body: Any,
    *,
    v_uri: str,
    enterprise_name: str,
    basics_patch: dict[str, str],
    erp_sync_enabled: bool,
    normalize_seg_type: Callable[[Any], str],
    normalize_km_interval: Callable[[Any], int],
    normalize_inspection_types: Callable[[Any], list[str]],
    normalize_contract_segs: Callable[[Any], list[dict[str, Any]]],
    normalize_structures: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_personnel: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_equipment: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_subcontracts: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_materials: Callable[[Any], list[dict[str, Any]]],
    normalize_zero_sign_status: Callable[[Any], str],
    normalize_perm_template: Callable[[Any], str],
) -> dict[str, Any]:
    def pick_text(*values: Any) -> Optional[str]:
        for value in values:
            text = str(value or "").strip()
            if text and text not in {"-", "--", "~", "N/A", "n/a"}:
                return text
        return None

    zero_personnel_input = (
        body.zero_personnel if body.zero_personnel is not None else getattr(body, "zeroPersonnel", None)
    )
    zero_equipment_input = (
        body.zero_equipment if body.zero_equipment is not None else getattr(body, "zeroEquipment", None)
    )
    zero_subcontracts_input = (
        body.zero_subcontracts if body.zero_subcontracts is not None else getattr(body, "zeroSubcontracts", None)
    )
    zero_materials_input = (
        body.zero_materials if body.zero_materials is not None else getattr(body, "zeroMaterials", None)
    )
    zero_sign_status_input = (
        body.zero_sign_status if body.zero_sign_status is not None else getattr(body, "zeroSignStatus", None)
    )
    qc_ledger_unlocked_input = (
        body.qc_ledger_unlocked if body.qc_ledger_unlocked is not None else getattr(body, "qcLedgerUnlocked", None)
    )

    owner_unit = pick_text(body.owner_unit, basics_patch.get("owner_unit"), enterprise_name)
    if erp_sync_enabled:
        # ERP sync mode must bind against ERP returned canonical fields.
        erp_project_code = pick_text(basics_patch.get("project_code"))
        erp_project_name = pick_text(basics_patch.get("project_name"))
    else:
        erp_project_code = pick_text(body.erp_project_code, body.contract_no)
        erp_project_name = pick_text(body.erp_project_name, body.name)
    contractor = pick_text(body.contractor, basics_patch.get("contractor"))
    supervisor = pick_text(body.supervisor, basics_patch.get("supervisor"))
    contract_no = pick_text(body.contract_no, basics_patch.get("contract_no"))
    start_date = pick_text(body.start_date, basics_patch.get("start_date"))
    end_date = pick_text(body.end_date, basics_patch.get("end_date"))
    description = pick_text(body.description, basics_patch.get("description"))

    rec = {
        "enterprise_id": body.enterprise_id,
        "v_uri": v_uri,
        "name": body.name,
        "type": body.type,
        "erp_project_code": erp_project_code,
        "erp_project_name": erp_project_name,
        "owner_unit": owner_unit or "",
        "contractor": contractor,
        "supervisor": supervisor,
        "contract_no": contract_no,
        "start_date": start_date,
        "end_date": end_date,
        "description": description,
        "seg_type": normalize_seg_type(body.seg_type),
        "seg_start": body.seg_start,
        "seg_end": body.seg_end,
        "km_interval": normalize_km_interval(body.km_interval),
        "inspection_types": normalize_inspection_types(body.inspection_types),
        "contract_segs": normalize_contract_segs(body.contract_segs),
        "structures": normalize_structures(body.structures),
        "zero_personnel": normalize_zero_personnel(zero_personnel_input),
        "zero_equipment": normalize_zero_equipment(zero_equipment_input),
        "zero_subcontracts": normalize_zero_subcontracts(zero_subcontracts_input),
        "zero_materials": normalize_zero_materials(zero_materials_input),
        "zero_sign_status": normalize_zero_sign_status(zero_sign_status_input),
        "qc_ledger_unlocked": bool(qc_ledger_unlocked_input),
        "perm_template": normalize_perm_template(body.perm_template),
        "status": "active",
    }
    zero_ledger_patch = {
        "zero_personnel": rec["zero_personnel"],
        "zero_equipment": rec["zero_equipment"],
        "zero_subcontracts": rec["zero_subcontracts"],
        "zero_materials": rec["zero_materials"],
        "zero_sign_status": rec["zero_sign_status"],
        "qc_ledger_unlocked": rec["qc_ledger_unlocked"],
    }
    return {
        "record": rec,
        "zero_ledger_patch": zero_ledger_patch,
        "erp_project_code": erp_project_code,
        "erp_project_name": erp_project_name,
    }


__all__ = ["build_project_create_payload"]
