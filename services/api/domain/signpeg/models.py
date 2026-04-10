"""SignPeg models: executor registry, signatures, scheduler, delegation."""

from __future__ import annotations

from datetime import date, datetime, timezone
from math import ceil
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Skill(BaseModel):
    skill_uri: str
    skill_name: str = ""
    level: int | str = 1
    verified_by: str = ""
    valid_until: date
    proof_uri: str = ""
    cert_no: str = ""
    issued_by: str = ""
    scope: list[str] = Field(default_factory=list)

    def is_valid_on(self, when: date) -> bool:
        return self.valid_until >= when

    @property
    def level_text(self) -> str:
        if isinstance(self.level, int):
            return str(self.level)
        return str(self.level or "").strip()


class Certificate(BaseModel):
    cert_id: str
    cert_type: str
    cert_no: str
    issued_by: str
    issued_date: date
    valid_until: date
    v_uri: str
    status: Literal["active", "expired", "revoked"] = "active"
    scan_hash: str = ""
    required: bool = True

    def is_valid_on(self, when: date) -> bool:
        return self.status == "active" and self.valid_until >= when

    def expires_within(self, days: int, *, today: date | None = None) -> bool:
        base = today or utc_now().date()
        return self.status == "active" and 0 <= (self.valid_until - base).days <= int(days)


class CapacitySpec(BaseModel):
    current: int = 0
    maximum: int = 10
    unit: str = "concurrent"
    overload_policy: str = "reject"

    @model_validator(mode="before")
    @classmethod
    def _normalize_capacity_input(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            merged = dict(obj)
            if "current" not in merged and "current_load" in merged:
                merged["current"] = merged.get("current_load")
            if "maximum" not in merged and "max_concurrent" in merged:
                merged["maximum"] = merged.get("max_concurrent")
            if "unit" not in merged:
                merged["unit"] = "concurrent"
            return merged
        return obj

    @property
    def current_load(self) -> int:
        return int(self.current)

    @property
    def max_concurrent(self) -> int:
        return int(self.maximum)

    @property
    def available(self) -> int:
        return max(int(self.maximum) - int(self.current), 0)


class EnergySpec(BaseModel):
    billing_unit: str = "trip"
    rate: float = 0.0
    currency: str = "CNY"
    billing_formula: str = "trip.units * rate"
    time_cost: float = 1.0
    fee_rate: float = 0.0
    credit_limit: int = 1000
    consumed: int = 0
    smu_type: str = "labor"

    @model_validator(mode="before")
    @classmethod
    def _normalize_energy_input(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            merged = dict(obj)
            fee_rate = float(merged.get("fee_rate") or 0.0)
            rate = float(merged.get("rate") or 0.0)
            if rate <= 0 and fee_rate > 0:
                merged["rate"] = fee_rate
            if fee_rate <= 0 and rate > 0:
                merged["fee_rate"] = rate
            if "billing_unit" not in merged:
                merged["billing_unit"] = "trip"
            if "billing_formula" not in merged:
                merged["billing_formula"] = "trip.units * rate"
            if "smu_type" not in merged:
                merged["smu_type"] = "labor"
            return merged
        return obj

    @property
    def credit_remaining(self) -> int:
        return max(int(self.credit_limit) - int(self.consumed), 0)

    def bill_units(self, *, duration_hours: float = 0.0, shifts: float = 0.0, tokens_used: int = 0) -> float:
        unit = str(self.billing_unit or "").strip().lower()
        if unit in {"工时", "hour", "hours"}:
            if float(duration_hours or 0.0) > 0:
                return float(duration_hours)
            return max(float(self.time_cost or 0.0), 1.0)
        if unit in {"台班", "shift", "shifts"}:
            if float(shifts or 0.0) > 0:
                return float(shifts)
            if float(duration_hours or 0.0) > 0:
                return float(duration_hours) / 8.0
            return 1.0
        if unit in {"tokens", "token"}:
            return float(max(int(tokens_used or 0), 0))
        if float(duration_hours or 0.0) > 0:
            return float(duration_hours)
        if float(shifts or 0.0) > 0:
            return float(shifts)
        return float(self.time_cost or 1.0)

    def bill_amount(self, *, duration_hours: float = 0.0, shifts: float = 0.0, tokens_used: int = 0) -> float:
        units = self.bill_units(duration_hours=duration_hours, shifts=shifts, tokens_used=tokens_used)
        return float(units) * float(self.rate or 0.0)

    def consume_delta(self, *, duration_hours: float = 0.0, shifts: float = 0.0, tokens_used: int = 0) -> int:
        units = self.bill_units(duration_hours=duration_hours, shifts=shifts, tokens_used=tokens_used)
        return max(int(ceil(units)) if units > 0 else 0, 1)


class EnergyProfile(EnergySpec):
    pass


class CapacityProfile(CapacitySpec):
    pass


class ConsumableDetail(BaseModel):
    sku_uri: str
    initial_qty: float = 0.0
    remaining_qty: float = 0.0
    unit: str = ""
    replenish_threshold: float = 0.0


class ReusableDetail(BaseModel):
    purchase_price: float = 0.0
    purchase_date: date | None = None
    expected_life: int = 0
    current_uses: int = 0
    remaining_uses: int = 0
    maintenance_cycle: int = 0
    next_maintenance_at: int = 0
    depreciation_per_use: float = 0.0


class CapabilityDetail(BaseModel):
    api_endpoint: str = ""
    model_version: str = ""
    quota_total: int = 0
    quota_used: int = 0
    quota_remaining: int = 0
    cost_per_1k_tokens: float = 0.0


class ToolSpec(BaseModel):
    tool_category: Literal["consumable", "reusable", "capability"]
    consumable: ConsumableDetail | None = None
    reusable: ReusableDetail | None = None
    capability: CapabilityDetail | None = None


class OrgSpec(BaseModel):
    org_type: str = ""
    business_license: str = ""
    qualification_summary: dict[str, str] = Field(default_factory=dict)
    branches: list[str] = Field(default_factory=list)
    branch_count: int = 0
    member_executor_uris: list[str] = Field(default_factory=list)
    member_role_bindings: dict[str, list[str]] = Field(default_factory=dict)
    member_project_bindings: dict[str, list[str]] = Field(default_factory=dict)
    project_uris: list[str] = Field(default_factory=list)
    business_license_scan_hash: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_org_spec_input(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            merged = dict(obj)
            branches = merged.get("branches")
            if isinstance(branches, int):
                merged["branch_count"] = int(branches)
                merged["branches"] = []
            elif isinstance(branches, list):
                merged["branch_count"] = int(merged.get("branch_count") or len(branches))
            return merged
        return obj


_ROLE_SKILL_HINTS: dict[str, tuple[str, ...]] = {
    "supervisor": ("bridge-inspection", "supervisor", "review", "approve"),
    "inspector": ("inspection", "check", "inspector"),
    "recorder": ("record", "recorder", "documentation"),
    "reviewer": ("review", "reviewer", "audit"),
    "constructor": ("construction", "contractor", "build"),
}


class Executor(BaseModel):
    executor_id: str = ""
    executor_uri: str
    executor_type: Literal["human", "machine", "tool", "ai", "org"] = "human"
    name: str
    org_uri: str
    capacity: CapacitySpec = Field(default_factory=CapacitySpec)
    certificates: list[Certificate] = Field(default_factory=list)
    energy: EnergySpec = Field(default_factory=EnergySpec)
    skills: list[Skill] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    used_by: list[str] = Field(default_factory=list)
    tool_spec: ToolSpec | None = None
    org_spec: OrgSpec | None = None
    business_license_file: str = ""
    status: Literal["active", "inactive", "suspended", "available", "busy", "offline", "in_use", "maintenance", "depleted", "retired"] = "available"
    registration_proof: str = ""
    proof_history: list[str] = Field(default_factory=list)
    registered_at: datetime
    last_active: datetime = Field(default_factory=utc_now)
    trip_count: int = 0
    proof_count: int = 0
    holder_name: str
    holder_id: str
    holder_since: datetime

    def cert_valid(self, when: date | None = None) -> bool:
        target = when or utc_now().date()
        if self.certificates:
            required = [item for item in self.certificates if item.required]
            if not required:
                required = self.certificates
            return all(item.is_valid_on(target) for item in required)
        return any(skill.is_valid_on(target) for skill in self.skills)

    def status_available(self) -> bool:
        return str(self.status).strip().lower() in {"active", "available", "in_use"}

    def has_skill_for(self, dto_role: str, when: date | None = None) -> bool:
        role = str(dto_role or "").strip().lower()
        if not role:
            return False
        hints = _ROLE_SKILL_HINTS.get(role, (role,))
        target = when or utc_now().date()
        for skill in self.skills:
            if not skill.is_valid_on(target):
                continue
            scope_blob = " ".join([skill.skill_uri, skill.skill_name, skill.level_text, " ".join(skill.scope)]).lower()
            if any(token in scope_blob for token in hints):
                return True
        return False

    def expiring_certificates(self, *, within_days: int = 30, today: date | None = None) -> list[Certificate]:
        if not self.certificates:
            return []
        base = today or utc_now().date()
        return [item for item in self.certificates if item.expires_within(within_days, today=base)]


class ExecutorSummary(BaseModel):
    executor_uri: str
    name: str
    org_uri: str
    status: str
    holder_name: str

    @classmethod
    def from_executor(cls, executor: Executor) -> "ExecutorSummary":
        return cls(
            executor_uri=executor.executor_uri,
            name=executor.name,
            org_uri=executor.org_uri,
            status=executor.status,
            holder_name=executor.holder_name,
        )


class HolderChangeRequest(BaseModel):
    holder_name: str
    holder_id: str
    holder_since: datetime = Field(default_factory=utc_now)
    reason: str = "holder_change"


class HolderHistoryItem(BaseModel):
    executor_uri: str
    holder_name: str
    holder_id: str
    holder_since: datetime
    changed_at: datetime
    reason: str = ""


class ExecutorRegisterRequest(BaseModel):
    executor_id: str = ""
    executor_uri: str
    executor_type: Literal["human", "machine", "tool", "ai", "org"] = "human"
    name: str
    org_uri: str
    capacity: CapacitySpec = Field(default_factory=CapacitySpec)
    certificates: list[Certificate] = Field(default_factory=list)
    energy: EnergySpec = Field(default_factory=EnergySpec)
    skills: list[Skill] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    used_by: list[str] = Field(default_factory=list)
    tool_spec: ToolSpec | None = None
    org_spec: OrgSpec | None = None
    business_license_file: str = ""
    status: Literal["active", "inactive", "suspended", "available", "busy", "offline", "in_use", "maintenance", "depleted", "retired"] = "available"
    registration_proof: str = ""
    proof_history: list[str] = Field(default_factory=list)
    registered_at: datetime = Field(default_factory=utc_now)
    last_active: datetime = Field(default_factory=utc_now)
    holder_name: str
    holder_id: str
    holder_since: datetime = Field(default_factory=utc_now)


class ExecutorCreateRequest(BaseModel):
    name: str
    executor_type: Literal["human", "machine", "tool", "ai", "org"] = "human"
    org_uri: str
    capacity: CapacitySpec = Field(default_factory=CapacitySpec)
    certificates: list[Certificate] = Field(default_factory=list)
    energy: EnergySpec = Field(default_factory=EnergySpec)
    skills: list[Skill] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    tool_spec: ToolSpec | None = None
    org_spec: OrgSpec | None = None
    business_license_file: str = ""
    status: Literal["active", "inactive", "suspended", "available", "busy", "offline", "in_use", "maintenance", "depleted", "retired"] = "available"
    holder_name: str = ""
    holder_id: str = ""
    machine_code: str = ""
    tool_code: str = ""
    ai_version: str = ""


class CertificateAddRequest(BaseModel):
    certificate: Certificate


class SkillAddRequest(BaseModel):
    skill: Skill


class RequiresAddRequest(BaseModel):
    tool_executor_uris: list[str] = Field(default_factory=list)


class ExecutorUseRequest(BaseModel):
    trip_id: str = ""
    trip_uri: str = ""
    trip_role: str = ""
    shifts: float = 0.0
    duration_hours: float = 0.0
    tokens_used: int = 0
    consumed_qty: float = 0.0
    note: str = ""


class ExecutorMaintainRequest(BaseModel):
    note: str = ""
    performed_at: datetime = Field(default_factory=utc_now)


class OrgMemberAddRequest(BaseModel):
    member_executor_uri: str


class OrgMemberCreateRequest(BaseModel):
    name: str
    executor_type: Literal["human", "machine", "tool", "ai"] = "human"
    role_keys: list[str] = Field(default_factory=list)
    project_uris: list[str] = Field(default_factory=list)
    capacity: CapacitySpec = Field(default_factory=CapacitySpec)
    certificates: list[Certificate] = Field(default_factory=list)
    energy: EnergySpec = Field(default_factory=EnergySpec)
    skills: list[Skill] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    tool_spec: ToolSpec | None = None
    status: Literal[
        "active",
        "inactive",
        "suspended",
        "available",
        "busy",
        "offline",
        "in_use",
        "maintenance",
        "depleted",
        "retired",
    ] = "available"
    holder_name: str = ""
    holder_id: str = ""
    machine_code: str = ""
    tool_code: str = ""
    ai_version: str = ""


class OrgProjectAddRequest(BaseModel):
    project_uri: str


class OrgMemberUpdateRequest(BaseModel):
    role_keys: list[str] = Field(default_factory=list)
    project_uris: list[str] = Field(default_factory=list)
    status: Literal[
        "active",
        "inactive",
        "suspended",
        "available",
        "busy",
        "offline",
        "in_use",
        "maintenance",
        "depleted",
        "retired",
    ] | None = None


class OrgMemberDisableRequest(BaseModel):
    reason: str = "disabled_by_org_admin"


class ExecutorStatusResponse(BaseModel):
    executor_id: str
    executor_uri: str
    status: str
    capacity: CapacitySpec
    certificates_valid: bool
    expiring_soon: list[Certificate] = Field(default_factory=list)
    remaining_life: int | None = None
    remaining_qty: float | None = None
    quota_remaining: int | None = None


class ExecutorListItem(BaseModel):
    executor_id: str
    executor_uri: str
    org_uri: str
    name: str
    executor_type: str
    status: str
    capacity: CapacitySpec
    certificates: list[Certificate] = Field(default_factory=list)
    certificates_valid: bool = True


class ExecutorListResponse(BaseModel):
    items: list[ExecutorListItem] = Field(default_factory=list)


class ExecutorSearchRequest(BaseModel):
    skill_uri: str = ""
    org_uri: str = ""
    type: str = ""
    available: bool = False


class ExecutorImportRequest(BaseModel):
    items: list[ExecutorCreateRequest] = Field(default_factory=list)


class ToolCertificate(BaseModel):
    cert_type: str
    cert_no: str
    valid_until: date
    issued_by: str = ""
    status: Literal["active", "expired", "revoked"] = "active"
    scan_hash: str = ""

    def is_valid_on(self, when: date) -> bool:
        return self.status == "active" and self.valid_until >= when

    def expires_within(self, days: int, *, today: date | None = None) -> bool:
        base = today or utc_now().date()
        return self.status == "active" and 0 <= (self.valid_until - base).days <= int(days)


class ToolEnergy(BaseModel):
    energy_type: str = ""
    unit: str = ""
    rate: float = 0.0
    cost_per_unit: float = 0.0
    smu_type: str = "equipment"


class ConsumableSpec(BaseModel):
    sku_uri: str
    initial_qty: float = 0.0
    remaining_qty: float = 0.0
    unit: str = ""
    replenish_threshold: float = 0.0
    unit_price: float = 0.0


class ReusableSpec(BaseModel):
    purchase_price: float = 0.0
    purchase_date: date | None = None
    expected_life: int = 0
    current_uses: int = 0
    remaining_uses: int = 0
    maintenance_cycle: int = 0
    next_maintenance_at: int = 0
    last_maintenance: date | None = None
    depreciation_per_use: float = 0.0


class CapabilitySpec(BaseModel):
    api_endpoint: str = ""
    model_version: str = ""
    quota_total: int = 0
    quota_used: int = 0
    quota_remaining: int = 0
    rate_limit: str = ""
    cost_per_1k_tokens: float = 0.0


class Tool(BaseModel):
    tool_id: str
    tool_uri: str
    tool_name: str
    tool_code: str
    tool_type: Literal["consumable", "reusable", "capability"]
    owner_type: Literal["executor", "pool", "org"] = "org"
    owner_uri: str
    project_uri: str = ""
    certificates: list[ToolCertificate] = Field(default_factory=list)
    tool_energy: ToolEnergy | None = None
    consumable_spec: ConsumableSpec | None = None
    reusable_spec: ReusableSpec | None = None
    capability_spec: CapabilitySpec | None = None
    status: Literal["available", "in_use", "maintenance", "depleted", "retired", "suspended"] = "available"
    use_history: list[str] = Field(default_factory=list)
    registration_proof: str = ""
    registered_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def certificates_valid(self, when: date | None = None) -> bool:
        target = when or utc_now().date()
        return all(item.is_valid_on(target) for item in self.certificates)

    def expiring_certificates(self, *, within_days: int = 30, today: date | None = None) -> list[ToolCertificate]:
        if not self.certificates:
            return []
        base = today or utc_now().date()
        return [item for item in self.certificates if item.expires_within(within_days, today=base)]


class ToolRegisterRequest(BaseModel):
    tool_name: str
    tool_code: str
    tool_type: Literal["consumable", "reusable", "capability"]
    owner_type: Literal["executor", "pool", "org"] = "org"
    owner_uri: str
    project_uri: str = ""
    certificates: list[ToolCertificate] = Field(default_factory=list)
    tool_energy: ToolEnergy | None = None
    consumable_spec: ConsumableSpec | None = None
    reusable_spec: ReusableSpec | None = None
    capability_spec: CapabilitySpec | None = None


class ToolUseRequest(BaseModel):
    trip_id: str = ""
    trip_uri: str = ""
    trip_role: str = ""
    shifts: float = 0.0
    duration_hours: float = 0.0
    tokens_used: int = 0
    consumed_qty: float = 0.0
    note: str = ""


class ToolMaintainRequest(BaseModel):
    note: str = ""
    performed_at: datetime = Field(default_factory=utc_now)


class ToolRetireRequest(BaseModel):
    reason: str = ""


class ToolStatusResponse(BaseModel):
    tool_id: str
    tool_uri: str
    status: str
    certificates_valid: bool
    remaining_life: int | None = None
    remaining_qty: float | None = None
    quota_remaining: int | None = None
    expiring_soon: list[ToolCertificate] = Field(default_factory=list)


class ToolUseResponse(BaseModel):
    ok: bool = True
    tool: Tool
    smu_entries: list[dict[str, Any]] = Field(default_factory=list)
    gate_result: dict[str, Any] = Field(default_factory=dict)


class ToolListItem(BaseModel):
    tool_id: str
    tool_uri: str
    tool_name: str
    tool_type: str
    status: str
    owner_uri: str
    project_uri: str
    certificates_valid: bool
    remaining_life: int | None = None
    remaining_qty: float | None = None
    quota_remaining: int | None = None


class ToolListResponse(BaseModel):
    items: list[ToolListItem] = Field(default_factory=list)


class ToolUsageItem(BaseModel):
    tool_uri: str
    trip_role: str = ""
    shifts: float = 0.0
    duration_hours: float = 0.0
    tokens_used: int = 0
    consumed_qty: float = 0.0
    note: str = ""


class ExecutorRecord(BaseModel):
    executor: Executor
    holder_history: list[HolderHistoryItem] = Field(default_factory=list)


class DelegationRequest(BaseModel):
    from_executor_uri: str
    to_executor_uri: str
    scope: list[str] = Field(default_factory=list)
    valid_from: datetime
    valid_until: datetime
    proof_doc: str


class Delegation(BaseModel):
    delegation_uri: str
    from_executor_uri: str
    to_executor_uri: str
    scope: list[str] = Field(default_factory=list)
    valid_from: datetime
    valid_until: datetime
    proof_doc: str
    status: str = "active"
    created_at: datetime

    def allows(self, action: str, now: datetime | None = None) -> bool:
        ts = now or utc_now()
        if self.status != "active":
            return False
        if ts < self.valid_from or ts > self.valid_until:
            return False
        token = str(action or "").strip().lower()
        return token in {str(item).strip().lower() for item in self.scope}


class SignPegRequest(BaseModel):
    doc_id: str
    body_hash: str
    executor_uri: str
    dto_role: str
    trip_role: str
    action: str
    actor_executor_uri: str = ""
    delegation_uri: str = ""
    project_trip_root: str = "v://cn.大锦/DJGS"
    signature_mode: Literal["process", "archive"] = "process"
    ca_provider: str = ""
    ca_signature_id: str = ""
    ca_signed_payload_hash: str = ""
    duration_hours: float = 0.0
    shifts: float = 0.0
    tokens_used: int = 0
    tool_usages: list[ToolUsageItem] = Field(default_factory=list)


class SignPegResult(BaseModel):
    sig_type: str = "signpeg"
    sig_data: str
    signed_at: datetime
    executor_uri: str
    executor_name: str
    dto_role: str
    trip_role: str
    doc_id: str
    body_hash: str
    trip_uri: str
    verified: bool = True
    delegation_uri: str = ""
    signature_mode: Literal["process", "archive"] = "process"
    ca_provider: str = ""
    ca_signature_id: str = ""


class VerifyRequest(BaseModel):
    sig_data: str
    doc_id: str
    body_hash: str
    executor_uri: str
    dto_role: str
    trip_role: str
    signed_at: datetime


class VerifyResponse(BaseModel):
    verified: bool
    executor: ExecutorSummary | None = None
    trip_uri: str = ""


class SignStatusItem(BaseModel):
    dto_role: str
    trip_role: str
    executor_uri: str
    executor_name: str
    signed_at: datetime
    sig_data: str
    trip_uri: str
    verified: bool = True


class SignStatusResponse(BaseModel):
    signatures: list[SignStatusItem] = Field(default_factory=list)
    all_signed: bool = False
    next_required: str = ""
    next_executor: str = ""
    current_slot: int = 0
    next_slot: int = 0
    blocked_reason: str = ""


class RailPactEntry(BaseModel):
    trip_uri: str
    executor_uri: str
    doc_id: str
    amount: float
    energy_delta: int = 1
    settled_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplainIssue(BaseModel):
    field: str
    expected: str
    actual: str
    deviation: str
    norm_ref: str
    severity: Literal["blocking", "warning", "info"] = "info"
    explanation: str


class GateExplainResult(BaseModel):
    passed: bool
    summary: str
    issues: list[ExplainIssue] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    norm_refs: list[str] = Field(default_factory=list)
    language: Literal["zh", "en"] = "zh"


class GateExplainRequest(BaseModel):
    form_code: str
    gate_result: dict[str, Any] = Field(default_factory=dict)
    norm_context: dict[str, Any] = Field(default_factory=dict)
    language: Literal["zh", "en"] = "zh"


class ProcessBlockingReason(BaseModel):
    type: str
    description: str
    action: str


class ProcessExplainResult(BaseModel):
    step: str
    status: Literal["locked", "active", "completed"]
    summary: str
    blocking_reasons: list[ProcessBlockingReason] = Field(default_factory=list)
    estimated_unblock: str = ""
    language: Literal["zh", "en"] = "zh"


class ProcessExplainRequest(BaseModel):
    project_uri: str
    component_uri: str
    step_id: str
    current_status: Literal["locked", "active", "completed"]
    chain_snapshot: dict[str, Any] | None = None
    language: Literal["zh", "en"] = "zh"


class FieldValidationResult(BaseModel):
    field: str
    value: Any
    status: Literal["ok", "warning", "blocking"]
    message: str
    norm_ref: str = ""
    expected: str = ""
    actual: str = ""
    deviation: str = ""
    language: Literal["zh", "en"] = "zh"


class FieldValidateRequest(BaseModel):
    form_code: str
    field_key: str
    value: Any
    context: dict[str, Any] = Field(default_factory=dict)
    language: Literal["zh", "en"] = "zh"


class AcceptanceCondition(BaseModel):
    condition_id: str
    content: str
    status: Literal["pending", "signed", "waived"] = "pending"
    signed_by: str = ""
    signed_at: datetime | None = None


class AcceptanceOnApproved(BaseModel):
    generate_final_proof: bool = True
    update_boq: str = ""
    trigger_railpact: bool = True
    archive_to_docfinal: bool = True
    lock_component_uri: bool = True


class AcceptanceConclusion(BaseModel):
    result: Literal["qualified", "rejected", "conditional"]
    conditions: list[str] = Field(default_factory=list)
    remarks: str = ""


class AcceptanceSubmitRequest(BaseModel):
    acceptance_id: str
    component_uri: str
    doc_id: str
    body_hash: str
    executor_uri: str
    dto_role: str = "supervisor"
    trip_role: str = "acceptance.approve"
    action: Literal["approve", "reject", "conditional_approve"]
    project_trip_root: str = "v://cn.大锦/DJGS"
    pre_doc_ids: list[str] = Field(default_factory=list)
    pre_rejection_trip_uri: str = ""
    conclusion: AcceptanceConclusion
    on_approved: AcceptanceOnApproved = Field(default_factory=AcceptanceOnApproved)
    payment_amount: float = 0.0
    ca_provider: str = ""
    ca_signature_id: str = ""
    ca_signed_payload_hash: str = ""


class AcceptanceSubmitResponse(BaseModel):
    acceptance_id: str
    component_uri: str
    result: Literal["qualified", "rejected", "conditional"]
    trip_uri: str
    sig_data: str
    signed_at: datetime
    pre_conditions_passed: bool
    final_proof_uri: str = ""
    boq_status: str = ""
    railpact_triggered: bool = False
    archived_to_docfinal: bool = False
    component_locked: bool = False
    pre_rejection_trip_uri: str = ""
    ca_provider: str = ""
    ca_signature_id: str = ""


class AcceptanceRecord(BaseModel):
    acceptance_id: str
    component_uri: str
    doc_id: str
    status: Literal["qualified", "rejected", "conditional"]
    latest_trip_uri: str
    pre_rejection_trip_uri: str = ""
    final_proof_uri: str = ""
    boq_status: str = ""
    archived_to_docfinal: bool = False
    component_locked: bool = False
    conditions: list[AcceptanceCondition] = Field(default_factory=list)
    updated_at: datetime


class AcceptanceConditionSignRequest(BaseModel):
    acceptance_id: str
    condition_id: str
    executor_uri: str
    dto_role: str = "supervisor"
    body_hash: str
    project_trip_root: str = "v://cn.大锦/DJGS"
    ca_provider: str = ""
    ca_signature_id: str = ""


class AcceptanceConditionSignResponse(BaseModel):
    acceptance_id: str
    condition_id: str
    signed: bool
    signed_at: datetime
    trip_uri: str
    acceptance_promoted: bool = False
    final_proof_uri: str = ""

