"""SMU request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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

