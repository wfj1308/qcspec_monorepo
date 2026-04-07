"""UTXO request models."""

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

