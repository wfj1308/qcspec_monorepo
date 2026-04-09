"""LogPeg models: system-evidence based construction logs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class MaterialConsumed(BaseModel):
    name: str = ""
    code: str = ""
    qty: float = 0.0
    unit: str = ""
    unit_price: float = 0.0
    total_cost: float = 0.0
    iqc_batch: str = ""


class DailyActivity(BaseModel):
    time: datetime
    component_uri: str = ""
    pile_id: str = ""
    location: str = ""
    process_step: str = ""
    form_code: str = ""
    trip_id: str = ""
    primary_executor: str = ""
    executor_org: str = ""
    supervisor: str = ""
    equipment_used: list[str] = Field(default_factory=list)
    gate_result: str = ""
    proof_id: str = ""
    materials_consumed: list[MaterialConsumed] = Field(default_factory=list)
    cost_labor: float = 0.0
    cost_equipment: float = 0.0
    cost_material: float = 0.0
    cost_total: float = 0.0
    remarks: str = ""


class MaterialSummary(BaseModel):
    name: str = ""
    code: str = ""
    total_qty: float = 0.0
    unit: str = ""
    total_cost: float = 0.0


class EquipmentSummary(BaseModel):
    name: str = ""
    executor_uri: str = ""
    shifts: float = 0.0
    hours: float = 0.0
    cost: float = 0.0


class PersonnelSummary(BaseModel):
    name: str = ""
    role: str = ""
    executor_uri: str = ""
    hours: float = 0.0
    cost: float = 0.0


class ProgressSummary(BaseModel):
    completed_steps: int = 0
    generated_proofs: int = 0
    components_completed: int = 0
    components_in_progress: int = 0
    pending_steps: int = 0


class QualitySummary(BaseModel):
    total_inspections: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0


class CostSummary(BaseModel):
    daily_labor: float = 0.0
    daily_equipment: float = 0.0
    daily_material: float = 0.0
    daily_total: float = 0.0
    cumulative_total: float = 0.0


class Anomaly(BaseModel):
    type: str
    severity: Literal["high", "medium", "low"] = "low"
    component_uri: str = ""
    description: str = ""
    action_required: str = ""


class DailyLog(BaseModel):
    log_date: str
    project_uri: str
    project_name: str = ""
    contract_section: str = ""
    weather: str = ""
    temperature_range: str = ""
    wind_level: str = ""
    activities: list[DailyActivity] = Field(default_factory=list)
    material_summary: list[MaterialSummary] = Field(default_factory=list)
    equipment_summary: list[EquipmentSummary] = Field(default_factory=list)
    personnel_summary: list[PersonnelSummary] = Field(default_factory=list)
    progress_summary: ProgressSummary = Field(default_factory=ProgressSummary)
    quality_summary: QualitySummary = Field(default_factory=QualitySummary)
    cost_summary: CostSummary = Field(default_factory=CostSummary)
    anomalies: list[Anomaly] = Field(default_factory=list)
    process_snapshot: dict[str, Any] = Field(default_factory=dict)
    signed_by: str = ""
    signed_at: datetime | None = None
    sign_proof: str = ""
    v_uri: str = ""
    data_hash: str = ""
    language: Literal["zh", "en"] = "zh"
    locked: bool = False

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_payload(cls, obj: Any) -> Any:
        if not isinstance(obj, dict):
            return obj
        merged = dict(obj)
        if "log_date" not in merged and "date" in merged:
            merged["log_date"] = merged.get("date")
        if "temperature_range" not in merged and "temperature" in merged:
            merged["temperature_range"] = merged.get("temperature")
        if "sign_proof" not in merged and "signature_proof_id" in merged:
            merged["sign_proof"] = merged.get("signature_proof_id")
        return merged


class AggregateSummary(BaseModel):
    total_completed_steps: int = 0
    total_generated_proofs: int = 0
    total_pending_steps: int = 0
    total_failed: int = 0
    total_material_cost: float = 0.0
    total_labor_cost: float = 0.0
    total_equipment_cost: float = 0.0
    total_cost: float = 0.0
    total_components_completed: int = 0
    total_components_in_progress: int = 0
    average_pass_rate: float = 0.0


class WeeklyLog(BaseModel):
    project_uri: str
    week_start: str
    week_end: str
    daily_logs: list[DailyLog] = Field(default_factory=list)
    weekly_summary: AggregateSummary = Field(default_factory=AggregateSummary)
    language: Literal["zh", "en"] = "zh"


class MonthlyLog(BaseModel):
    project_uri: str
    month: str
    daily_logs: list[DailyLog] = Field(default_factory=list)
    monthly_summary: AggregateSummary = Field(default_factory=AggregateSummary)
    language: Literal["zh", "en"] = "zh"


class LogPegSignRequest(BaseModel):
    date: str
    executor_uri: str = ""
    signed_by: str = ""
    weather: str = ""
    temperature_range: str = ""
    wind_level: str = ""
    language: Literal["zh", "en"] = "zh"

    @model_validator(mode="before")
    @classmethod
    def _normalize_sign_input(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            merged = dict(obj)
            if "temperature_range" not in merged and "temperature" in merged:
                merged["temperature_range"] = merged.get("temperature")
            return merged
        return obj


class LogPegExportRequest(BaseModel):
    date: str
    format: Literal["pdf", "word", "json"] = "pdf"
    language: Literal["zh", "en"] = "zh"


class LogPegAutoGenerateResult(BaseModel):
    date: str
    generated: int = 0
    failed: int = 0
    details: list[dict[str, Any]] = Field(default_factory=list)
