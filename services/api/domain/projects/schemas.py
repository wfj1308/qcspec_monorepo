"""
Request models for projects router.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    type: str
    owner_unit: str
    erp_project_code: Optional[str] = None
    erp_project_name: Optional[str] = None
    contractor: Optional[str] = None
    supervisor: Optional[str] = None
    contract_no: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    seg_type: str = "km"
    seg_start: Optional[str] = None
    seg_end: Optional[str] = None
    km_interval: Optional[int] = 20
    inspection_types: Optional[list[str]] = None
    contract_segs: Optional[list[dict[str, Any]]] = None
    structures: Optional[list[dict[str, Any]]] = None
    zero_personnel: Optional[list[dict[str, Any]]] = None
    zero_equipment: Optional[list[dict[str, Any]]] = None
    zero_subcontracts: Optional[list[dict[str, Any]]] = None
    zero_materials: Optional[list[dict[str, Any]]] = None
    zero_sign_status: Optional[str] = "pending"
    qc_ledger_unlocked: Optional[bool] = False
    zeroPersonnel: Optional[list[dict[str, Any]]] = None
    zeroEquipment: Optional[list[dict[str, Any]]] = None
    zeroSubcontracts: Optional[list[dict[str, Any]]] = None
    zeroMaterials: Optional[list[dict[str, Any]]] = None
    zeroSignStatus: Optional[str] = None
    qcLedgerUnlocked: Optional[bool] = None
    perm_template: str = "standard"
    enterprise_id: str


class ProjectAutoregSyncRequest(BaseModel):
    enterprise_id: Optional[str] = None
    force: bool = True
    writeback: bool = True


class ProjectGitPegCompleteRequest(BaseModel):
    code: str
    registration_id: Optional[str] = None
    session_id: Optional[str] = None
    enterprise_id: Optional[str] = None
