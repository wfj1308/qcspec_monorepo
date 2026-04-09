"""BOQPeg domain models for process materials and IQC linkage."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MaterialRequirement(BaseModel):
    step_id: str
    material_code: str
    material_name: str
    iqc_form_code: str
    iqc_uri: str | None = None
    status: Literal["pending", "approved", "rejected"] = "pending"
    required: bool = True
    min_qty: float = 0.0
    inspection_batch_required: bool = False


class IQCSubmitRequest(BaseModel):
    project_uri: str
    component_uri: str
    step_id: str = ""
    material_code: str
    material_name: str = ""
    iqc_form_code: str = ""
    batch_no: str
    total_qty: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    supplier: str = ""
    test_results: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str
    owner_uri: str = ""
    status: Literal["pending", "approved", "rejected"] = "approved"


class IQCResult(BaseModel):
    material_code: str
    material_name: str
    iqc_form_code: str
    batch_no: str
    total_qty: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    supplier: str = ""
    status: Literal["pending", "approved", "rejected"]
    iqc_uri: str
    submitted_at: datetime = Field(default_factory=utc_now)
    proof_id: str = ""
    proof_hash: str = ""
    committed: bool = False
    component_uri: str
    project_uri: str
    executor_uri: str


class MaterialUTXO(BaseModel):
    utxo_id: str
    material_code: str
    batch_no: str
    iqc_uri: str
    total_qty: float
    used_qty: float
    remaining: float
    unit: str
    unit_price: float = 0.0
    supplier: str = ""
    inspection_batch_no: str
    inspection_form: str = ""
    inspection_uri: str
    inspection_result: Literal["approved", "rejected", "pending"] = "approved"
    component_uri: str
    process_step: str
    quantity: float
    status: Literal["available", "reserved", "consumed", "rejected"] = "consumed"
    v_uri: str
    data_hash: str
    signed_by: str
    created_at: datetime = Field(default_factory=utc_now)
    proof_id: str = ""
    proof_hash: str = ""


class InspectionBatchCreateRequest(BaseModel):
    project_uri: str
    iqc_uri: str
    component_uri: str
    process_step: str
    quantity: float
    unit: str = ""
    inspection_form: str = ""
    inspection_batch_no: str = ""
    inspection_result: Literal["approved", "rejected", "pending"] = "approved"
    test_results: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str
    owner_uri: str = ""
    commit: bool = True


class InspectionBatchResult(BaseModel):
    iqc_uri: str
    component_uri: str
    process_step: str
    quantity: float
    unit: str
    total_qty: float
    used_qty: float
    remaining: float
    material_code: str
    inspection_batch_no: str
    inspection_uri: str
    inspection_result: Literal["approved", "rejected", "pending"]
    utxo: MaterialUTXO
    committed: bool = False


class MaterialUTXOQueryResult(BaseModel):
    scope: Literal["iqc", "component"]
    key: str
    records: list[MaterialUTXO] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class TripSignature(BaseModel):
    signer_uri: str
    signer_name: str = ""
    signed_at: datetime = Field(default_factory=utc_now)
    sig_data: str = ""
    sig_type: str = "signpeg"


class ConsumableItem(BaseModel):
    name: str
    batch_ref: str
    quantity_used: float
    quantity_unit: str
    standard_qty: float = 0.0
    over_reason: str = ""
    material_code: str = ""
    unit_price: float = 0.0


class ConsumptionTrip(BaseModel):
    v_uri: str
    trip_role: str
    location: str = ""
    work_on: list[str] = Field(default_factory=list)
    consumables: list[ConsumableItem] = Field(default_factory=list)
    process_params: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str
    equipment_uri: str = ""
    signatures: list[TripSignature] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    test_reports: list[str] = Field(default_factory=list)
    result: Literal["合格", "不合格"] = "合格"
    cost_aggregate: float = 0.0
    project_uri: str = ""
    component_uri: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    proof_id: str = ""
    proof_hash: str = ""
    overuse_alerted: bool = False


class FormworkAsset(BaseModel):
    v_uri: str
    name: str
    purchase_price: float
    expected_uses: int
    current_uses: int = 0
    remaining_uses: int = 0
    use_history: list[str] = Field(default_factory=list)
    cumulative_wear: float = 0.0
    status: Literal["in_service", "maintenance", "retired"] = "in_service"
    updated_at: datetime = Field(default_factory=utc_now)


class ConsumptionTripRequest(BaseModel):
    project_uri: str
    component_uri: str
    location: str = ""
    work_on: list[str] = Field(default_factory=list)
    consumables: list[ConsumableItem] = Field(default_factory=list)
    process_params: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str
    equipment_uri: str = ""
    signatures: list[TripSignature] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    test_reports: list[str] = Field(default_factory=list)
    owner_uri: str = ""
    commit: bool = True


class WeldingTripRequest(ConsumptionTripRequest):
    trip_role: str = "construction.welding"
    form_code: str = "焊接记录"


class FormworkUseTripRequest(ConsumptionTripRequest):
    trip_role: str = "construction.formwork"
    form_code: str = "模板使用记录"
    formwork_asset_uri: str
    formwork_asset_name: str = ""
    purchase_price: float = 0.0
    expected_uses: int = 50


class PrestressingTripRequest(ConsumptionTripRequest):
    trip_role: str = "construction.prestressing"
    form_code: str = "预应力张拉记录"
    theoretical_elongation: float
    actual_elongation: float
    tolerance_ratio: float = 0.06


class ConsumptionTripSubmitResult(BaseModel):
    ok: bool = True
    trip: ConsumptionTrip
    gate_passed: bool = True
    gate_reason: str = ""
    batch_usage: list[dict[str, Any]] = Field(default_factory=list)
    formwork_asset: FormworkAsset | None = None
    warnings: list[str] = Field(default_factory=list)


class CostBreakdown(BaseModel):
    component_uri: str
    direct_materials: float = 0.0
    consumables: float = 0.0
    equipment_depreciation: float = 0.0
    equipment_cost: float = 0.0
    labor: float = 0.0
    overhead: float = 0.0
    total: float = 0.0
    proof_refs: list[str] = Field(default_factory=list)


class ToolAsset(BaseModel):
    v_uri: str
    project_uri: str
    name: str
    model_no: str = ""
    asset_mode: Literal["rental", "owned"] = "owned"
    equipment_manager_uri: str = ""
    calibration_cert_no: str = ""
    calibration_valid_until: date | None = None
    annual_inspection_status: Literal["valid", "expired", "pending", "failed"] = "valid"
    annual_inspection_valid_until: date | None = None
    operator_skill_required: list[str] = Field(default_factory=list)
    maintenance_status: Literal["normal", "due", "overdue", "in_maintenance"] = "normal"
    maintenance_due_at: datetime | None = None
    rental_shift_rate: float = 0.0
    purchase_price: float = 0.0
    depreciation_years: float = 8.0
    annual_work_hours: float = 2000.0
    status: Literal["in_service", "blocked", "retired"] = "in_service"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ToolAssetRegisterRequest(BaseModel):
    project_uri: str
    v_uri: str
    name: str
    model_no: str = ""
    asset_mode: Literal["rental", "owned"] = "owned"
    equipment_manager_uri: str = ""
    calibration_cert_no: str = ""
    calibration_valid_until: date | None = None
    annual_inspection_status: Literal["valid", "expired", "pending", "failed"] = "valid"
    annual_inspection_valid_until: date | None = None
    operator_skill_required: list[str] = Field(default_factory=list)
    maintenance_status: Literal["normal", "due", "overdue", "in_maintenance"] = "normal"
    maintenance_due_at: datetime | None = None
    rental_shift_rate: float = 0.0
    purchase_price: float = 0.0
    depreciation_years: float = 8.0
    annual_work_hours: float = 2000.0
    status: Literal["in_service", "blocked", "retired"] = "in_service"
    metadata: dict[str, Any] = Field(default_factory=dict)
    owner_uri: str = ""
    executor_uri: str = ""
    commit: bool = True


class ToolAssetStatusResult(BaseModel):
    equipment_uri: str
    ready: bool
    status: str
    calibration_valid_until: date | None = None
    annual_inspection_status: str = ""
    annual_inspection_valid_until: date | None = None
    maintenance_status: str = ""
    maintenance_due_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list)
    gate_reasons: list[str] = Field(default_factory=list)
    asset: ToolAsset


class EquipmentTrip(BaseModel):
    trip_uri: str
    project_uri: str
    component_uri: str
    equipment_uri: str
    equipment_name: str
    trip_role: str = "equipment.shift"
    operator_executor_uri: str
    work_hours: float = 0.0
    shift_count: float = 0.0
    mode: Literal["rental", "owned"] = "owned"
    unit_rate: float = 0.0
    rental_cost: float = 0.0
    depreciation_cost: float = 0.0
    machine_cost: float = 0.0
    gate_passed: bool = True
    gate_reason: str = ""
    process_params: dict[str, Any] = Field(default_factory=dict)
    signatures: list[TripSignature] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    proof_id: str = ""
    proof_hash: str = ""


class EquipmentTripRequest(BaseModel):
    project_uri: str
    component_uri: str
    equipment_uri: str
    operator_executor_uri: str
    trip_role: str = "equipment.shift"
    work_hours: float = 0.0
    shift_count: float = 0.0
    unit_rate: float = 0.0
    process_params: dict[str, Any] = Field(default_factory=dict)
    signatures: list[TripSignature] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    owner_uri: str = ""
    commit: bool = True


class EquipmentTripSubmitResult(BaseModel):
    ok: bool = True
    trip: EquipmentTrip
    gate_passed: bool = True
    gate_reason: str = ""
    equipment_status: ToolAssetStatusResult
    warnings: list[str] = Field(default_factory=list)


class EquipmentHistoryResult(BaseModel):
    equipment_uri: str
    trips: list[EquipmentTrip] = Field(default_factory=list)
    asset_snapshots: list[ToolAsset] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
