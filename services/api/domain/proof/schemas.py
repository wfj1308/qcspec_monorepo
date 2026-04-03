"""
Request models for proof router.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class UTXOCreateBody(BaseModel):
    proof_id: Optional[str] = None
    owner_uri: str
    project_uri: str
    project_id: Optional[str] = None
    segment_uri: Optional[str] = None
    proof_type: str = "inspection"
    result: str = "PENDING"
    state_data: dict = Field(default_factory=dict)
    conditions: list = Field(default_factory=list)
    parent_proof_id: Optional[str] = None
    norm_uri: Optional[str] = None
    signer_uri: Optional[str] = None
    signer_role: str = "AI"
    gitpeg_anchor: Optional[str] = None


class UTXOConsumeBody(BaseModel):
    input_proof_ids: list
    output_states: list
    executor_uri: str
    executor_role: str = "AI"
    trigger_action: Optional[str] = None
    trigger_data: dict = Field(default_factory=dict)
    tx_type: str = "consume"


class UTXOAutoSettleBody(BaseModel):
    inspection_proof_id: str
    executor_uri: str
    executor_role: str = "AI"
    trigger_action: str = "railpact.settle"
    anchor_config: Optional[dict[str, Any]] = None


class TripRoleExecuteBody(BaseModel):
    action: str = Field(..., description="quality.check | measure.record | variation.record | settlement.confirm")
    input_proof_id: str
    executor_uri: str
    executor_did: str = ""
    executor_role: str = "TRIPROLE"
    result: Optional[str] = None
    segment_uri: Optional[str] = None
    boq_item_uri: Optional[str] = None
    signatures: list[dict[str, Any]] = Field(default_factory=list)
    consensus_signatures: list[dict[str, Any]] = Field(default_factory=list)
    signer_metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    credentials_vc: list[dict[str, Any]] = Field(default_factory=list)
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)
    offline_packet_id: str = ""


class VariationApplyBody(BaseModel):
    boq_item_uri: str
    delta_amount: float
    reason: str = ""
    project_uri: Optional[str] = None
    executor_uri: str = "v://executor/system/"
    executor_did: str = ""
    executor_role: str = "TRIPROLE"
    metadata: dict[str, Any] = Field(default_factory=dict)
    credentials_vc: list[dict[str, Any]] = Field(default_factory=list)
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)
    offline_packet_id: str = ""


class OfflineProofPacketBody(BaseModel):
    offline_packet_id: str = ""
    packet_type: str = "triprole.execute"
    local_created_at: str = ""
    action: str = ""
    input_proof_id: str = ""
    boq_item_uri: str = ""
    delta_amount: Optional[float] = None
    reason: str = ""
    result: Optional[str] = None
    project_uri: Optional[str] = None
    segment_uri: Optional[str] = None
    executor_uri: str = "v://executor/system/"
    executor_did: str = ""
    executor_role: str = "TRIPROLE"
    signatures: list[dict[str, Any]] = Field(default_factory=list)
    consensus_signatures: list[dict[str, Any]] = Field(default_factory=list)
    signer_metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    credentials_vc: list[dict[str, Any]] = Field(default_factory=list)
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)


class OfflineReplayBody(BaseModel):
    packets: list[OfflineProofPacketBody] = Field(default_factory=list)
    stop_on_error: bool = False
    default_executor_uri: str = "v://executor/system/"
    default_executor_role: str = "TRIPROLE"


class ScanConfirmBody(BaseModel):
    input_proof_id: str
    scan_payload: str
    scanner_did: str
    scanner_role: str = "supervisor"
    executor_uri: str = "v://executor/system/"
    executor_role: str = "SUPERVISOR"
    signature_hash: str = ""
    signer_metadata: dict[str, Any] = Field(default_factory=dict)
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)


class SensorIngestBody(BaseModel):
    device_id: str
    raw_payload: Any
    boq_item_uri: str
    project_uri: Optional[str] = None
    executor_uri: str = "v://executor/system/"
    executor_did: str = ""
    executor_role: str = "TRIPROLE"
    metadata: dict[str, Any] = Field(default_factory=dict)
    credentials_vc: list[dict[str, Any]] = Field(default_factory=list)
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)


class DocFinalExportBody(BaseModel):
    project_uri: str
    project_name: Optional[str] = None
    passphrase: str = Field(default="", description="Optional encryption passphrase (AES-256).")
    verify_base_url: str = "https://verify.qcspec.com"
    include_unsettled: bool = False


class DocFinalFinalizeBody(BaseModel):
    project_uri: str
    project_name: Optional[str] = None
    passphrase: str = Field(default="", description="Optional encryption passphrase (AES-256).")
    verify_base_url: str = "https://verify.qcspec.com"
    include_unsettled: bool = False
    run_anchor_rounds: int = Field(default=1, ge=0, le=5, description="How many anchor rounds to run after export.")


class PaymentCertificateBody(BaseModel):
    project_uri: str
    period: str = Field(..., description="YYYY-MM or YYYY-MM-DD or YYYY-MM-DD~YYYY-MM-DD")
    project_name: Optional[str] = None
    verify_base_url: str = "https://verify.qcspec.com"
    create_proof: bool = True
    executor_uri: str = "v://executor/system/"
    enforce_dual_pass: bool = True


class LabTestRecordBody(BaseModel):
    project_uri: str
    boq_item_uri: str
    sample_id: str
    jtg_form_code: str = "JTG-E60"
    instrument_sn: str = ""
    tested_at: str = ""
    witness_record: dict[str, Any] = Field(default_factory=dict)
    sample_tracking: dict[str, Any] = Field(default_factory=dict)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    result: str = ""
    executor_uri: str = "v://executor/lab/system/"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FrequencyCalcBody(BaseModel):
    project_uri: str = ""
    boq_item_uri: str


class RemediationOpenBody(BaseModel):
    fail_proof_id: str
    notice: str = ""
    executor_uri: str = "v://executor/supervisor/system/"
    due_date: str = ""
    assignees: list[str] = Field(default_factory=list)


class RemediationReinspectBody(BaseModel):
    remediation_proof_id: str
    result: str
    payload: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str = "v://executor/inspector/system/"


class RemediationCloseBody(BaseModel):
    remediation_proof_id: str
    reinspection_proof_id: str
    close_note: str = ""
    executor_uri: str = "v://executor/supervisor/system/"


class RailPactInstructionBody(BaseModel):
    payment_id: str
    executor_uri: str = "v://executor/owner/system/"
    auto_submit: bool = False


class SpatialBindBody(BaseModel):
    utxo_id: str = Field(..., description="proof_id to bind spatial fingerprint")
    project_uri: Optional[str] = None
    bim_id: Optional[str] = None
    label: Optional[str] = None
    coordinate: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PredictiveQualityBody(BaseModel):
    project_uri: str
    near_threshold_ratio: float = Field(default=0.9, ge=0.5, le=0.995)
    min_samples: int = Field(default=3, ge=2, le=50)
    apply_dynamic_gate: bool = True
    default_critical_threshold: float = Field(default=2.0, gt=0)


class FinanceProofExportBody(BaseModel):
    payment_id: str
    bank_code: str = ""
    passphrase: str = ""
    run_anchor_rounds: int = Field(default=1, ge=0, le=5)


class RwaConvertBody(BaseModel):
    project_uri: str
    boq_group_id: str
    project_name: Optional[str] = None
    bank_code: str = ""
    passphrase: str = ""
    run_anchor_rounds: int = Field(default=1, ge=0, le=5)


class OMBundleExportBody(BaseModel):
    project_uri: str
    project_name: Optional[str] = None
    om_owner_uri: str = "v://operator/om/default"
    passphrase: str = ""
    run_anchor_rounds: int = Field(default=1, ge=0, le=5)


class OMEventBody(BaseModel):
    om_root_proof_id: str
    title: str
    event_type: str = "maintenance"
    payload: dict[str, Any] = Field(default_factory=dict)
    executor_uri: str = "v://operator/om/default"


class NormEvolutionBody(BaseModel):
    project_uris: list[str] = Field(default_factory=list)
    min_samples: int = Field(default=5, ge=3, le=100)
    near_threshold_ratio: float = Field(default=0.9, ge=0.5, le=0.995)
    anonymize: bool = True
    create_proof: bool = True


class SpecDictEvolutionBody(BaseModel):
    project_uris: list[str] = Field(default_factory=list)
    min_samples: int = Field(default=5, ge=3, le=200)


class SpecDictExportBody(BaseModel):
    project_uris: list[str] = Field(default_factory=list)
    min_samples: int = Field(default=5, ge=3, le=200)
    namespace_uri: str = "v://global/templates"
    commit: bool = False


class TransferAssetBody(BaseModel):
    item_id: str = Field(..., description="proof_id or boq_item_uri")
    amount: float = Field(..., gt=0)
    project_uri: Optional[str] = None
    executor_uri: str = "v://executor/system/"
    executor_role: str = "DOCPEG"
    docpeg_proof_id: Optional[str] = None
    docpeg_hash: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComponentBOQItemBody(BaseModel):
    item_id: str
    description: str = ""
    unit: str = ""
    qty: float = 0
    unit_price: float = 0
    spec_uri: str = ""


class ComponentBOMItemBody(BaseModel):
    material_role: str
    qty: float
    tolerance_spec_uri: str = ""
    tolerance_ratio: float | None = Field(default=None, ge=0)


class ComponentMaterialBindingBody(BaseModel):
    material_utxo_id: str = ""
    material_role: str
    planned_qty: float = 0
    actual_qty: float = 0
    tolerance: float | None = Field(default=None, ge=0)
    proof_hash: str = ""
    boq_item_id: str = ""
    tolerance_spec_uri: str = ""


class ComponentMaterialInputBody(BaseModel):
    utxo_id: str = ""
    material_role: str = ""
    material_type: str = ""
    qty: float = 0
    actual_qty: float = 0
    proof_hash: str = ""
    boq_item_id: str = ""


class ComponentNodeBody(BaseModel):
    component_id: str
    component_uri: str = ""
    project_uri: str = ""
    kind: str = "component"
    boq_items: list[ComponentBOQItemBody] = Field(default_factory=list)
    bom: list[ComponentBOMItemBody] | dict[str, float] = Field(default_factory=list)
    material_bindings: list[ComponentMaterialBindingBody] = Field(default_factory=list)
    material_inputs: list[ComponentMaterialInputBody] = Field(default_factory=list)
    child_components: list[str] = Field(default_factory=list)
    parent_component: str | None = None
    status: str = "PENDING"
    version: int = Field(default=1, ge=1)
    proof_hash: str = ""
    last_trip_id: str | None = None
    last_action: str | None = None
    timestamp: float | None = None


class ComponentUTXOVerifyBody(BaseModel):
    component_id: str
    component_uri: str = ""
    kind: str = "component"
    project_uri: str = ""
    boq_items: list[ComponentBOQItemBody] = Field(default_factory=list)
    bom: list[ComponentBOMItemBody] | dict[str, float] = Field(default_factory=list)
    material_bindings: list[ComponentMaterialBindingBody] = Field(default_factory=list)
    material_input_proof_ids: list[str] = Field(default_factory=list)
    material_inputs: list[ComponentMaterialInputBody] = Field(default_factory=list)
    child_components: list[str] = Field(default_factory=list)
    parent_component: str | None = None
    status: str = "PENDING"
    version: int = Field(default=1, ge=1)
    proof_hash: str = ""
    last_trip_id: str | None = None
    last_action: str | None = None
    timestamp: float | None = None
    trip_id: str = ""
    trip_action: str = ""
    trip_executor_uri: str = ""
    norm_ref: str = ""
    component_nodes: list[ComponentNodeBody] = Field(default_factory=list)
    default_tolerance_ratio: float = Field(default=0.05, ge=0)
    render_docpeg: bool = True
    verify_base_url: str = "https://verify.qcspec.com"
    template_path: str = ""
    include_docx_base64: bool = True


class GateRuleNormImportBody(BaseModel):
    spec_uri: str
    context: str = ""


class GateRuleGenerateBody(BaseModel):
    prompt: str
    subitem_code: str = ""


class GateRuleSaveBody(BaseModel):
    project_uri: str
    subitem_code: str
    gate_id_base: str = ""
    rules: list[dict[str, Any]] = Field(default_factory=list)
    execution_strategy: str = "all_pass"
    fail_action: str = "trigger_review_trip"
    apply_to_similar: bool = False
    executor_uri: str = "v://executor/chief-engineer/"
    metadata: dict[str, Any] = Field(default_factory=dict)


class GateRuleRollbackBody(BaseModel):
    project_uri: str
    subitem_code: str
    target_proof_id: str = ""
    target_version: str = ""
    apply_to_similar: bool = True
    executor_uri: str = "v://executor/chief-engineer/"


class SpecDictSaveBody(BaseModel):
    spec_dict_key: str
    title: str = ""
    version: str = "v1.0"
    authority: str = ""
    spec_uri: str = ""
    items: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class DocAutoClassifyBody(BaseModel):
    file_name: str = ""
    text_excerpt: str = ""
    mime_type: str = ""


class DocNodeCreateBody(BaseModel):
    project_uri: str
    parent_uri: str = ""
    node_name: str
    executor_uri: str = "v://executor/system/"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocNodeAutoGenerateBody(BaseModel):
    project_uri: str
    parent_uri: str = ""
    start_km: int
    end_km: int
    step_km: int = 1
    leaf_name: str = "inspection"
    executor_uri: str = "v://executor/system/"


class DocSearchBody(BaseModel):
    project_uri: str
    node_uri: str = ""
    include_descendants: bool = True
    query: str = ""
    tags: list[str] = Field(default_factory=list)
    field_filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=200, ge=1, le=2000)


class SMUExecuteBody(BaseModel):
    project_uri: str
    input_proof_id: str
    executor_uri: str = "v://executor/mobile/inspector/"
    executor_did: str = ""
    executor_role: str = "TRIPROLE"
    component_type: str = "generic"
    measurement: dict[str, Any] = Field(default_factory=dict)
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)
    evidence_hashes: list[str] = Field(default_factory=list)
    credentials_vc: list[dict[str, Any]] = Field(default_factory=list)
    force_reject: bool = False


class SMUSignBody(BaseModel):
    input_proof_id: str
    boq_item_uri: str
    supervisor_executor_uri: str = "v://executor/supervisor/mobile/"
    supervisor_did: str
    contractor_did: str
    owner_did: str
    signer_metadata: dict[str, Any] = Field(default_factory=dict)
    require_sm2: bool = False
    sm2_signatures: list[dict[str, Any]] = Field(default_factory=list)
    consensus_values: list[dict[str, Any]] = Field(default_factory=list)
    allowed_deviation: float | None = None
    allowed_deviation_percent: float | None = None
    geo_location: dict[str, Any] = Field(default_factory=dict)
    server_timestamp_proof: dict[str, Any] = Field(default_factory=dict)
    auto_docpeg: bool = True
    verify_base_url: str = "https://verify.qcspec.com"
    template_path: str = ""


class SMUValidateBody(BaseModel):
    project_uri: str
    smu_id: str


class SMUFreezeBody(BaseModel):
    project_uri: str
    smu_id: str
    executor_uri: str = "v://executor/owner/system/"
    min_risk_score: float = Field(default=60.0, ge=0.0, le=100.0)
