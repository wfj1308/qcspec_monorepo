"""Document governance request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
    dto_role: str = ""


class DocSpecHeaderV11(BaseModel):
    doc_type: str = "v://normref.com/doc-type/general-document@v1"
    doc_id: str = ""
    v_uri: str = ""
    version: str = "v1.1"
    created_at: str = ""
    project_ref: str = ""
    jurisdiction: str = "CN-JTG"
    trip_role: str = "document.register"
    dtorole_context: str = "PUBLIC"


class DocSpecGateV11(BaseModel):
    pre_conditions: list[Any] = Field(default_factory=list)
    entry_rules: list[Any] = Field(default_factory=list)
    trigger_event: str = ""
    norm_refs: list[str] = Field(default_factory=list)
    required_trip_roles: list[str] = Field(default_factory=list)
    dtorole_permissions: dict[str, Any] = Field(default_factory=dict)


class DocSpecBodyV11(BaseModel):
    basic: dict[str, Any] = Field(default_factory=dict)
    items: list[Any] = Field(default_factory=list)
    relations: list[dict[str, Any]] = Field(default_factory=list)
    trip_context: dict[str, Any] = Field(default_factory=dict)


class DocSpecProofV11(BaseModel):
    signatures: list[Any] = Field(default_factory=list)
    timestamps: list[Any] = Field(default_factory=list)
    data_hash: str = ""
    witness_logs: list[Any] = Field(default_factory=list)
    audit_trail: list[Any] = Field(default_factory=list)
    proof_hash: str = ""
    trip_proof_hash: str = ""
    dtorole_proof: dict[str, Any] = Field(default_factory=dict)


class DocSpecStateV11(BaseModel):
    lifecycle_stage: str = "draft"
    valid_until: str = ""
    retention_period: str = "P10Y"
    access_level: str = "project_internal"
    next_action: str = ""
    state_matrix: dict[str, Any] = Field(default_factory=lambda: {"completed": 0, "pending": 1, "total": 1})
    current_trip_role: str = "document.register"
    dtorole_state: dict[str, Any] = Field(default_factory=dict)


class DocPegSpecIRV11Body(BaseModel):
    schema_uri: str = "v://normref.com/schema/docpeg-specir-v1.1"
    version: str = "v1.1"
    header: DocSpecHeaderV11 = Field(default_factory=DocSpecHeaderV11)
    gate: DocSpecGateV11 = Field(default_factory=DocSpecGateV11)
    body: DocSpecBodyV11 = Field(default_factory=DocSpecBodyV11)
    proof: DocSpecProofV11 = Field(default_factory=DocSpecProofV11)
    state: DocSpecStateV11 = Field(default_factory=DocSpecStateV11)
