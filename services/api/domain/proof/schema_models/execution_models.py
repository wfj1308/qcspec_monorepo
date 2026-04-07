"""Trip/execution request models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


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


class TransferAssetBody(BaseModel):
    item_id: str = Field(..., description="proof_id or boq_item_uri")
    amount: float = Field(..., gt=0)
    project_uri: Optional[str] = None
    executor_uri: str = "v://executor/system/"
    executor_role: str = "DOCPEG"
    docpeg_proof_id: Optional[str] = None
    docpeg_hash: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

