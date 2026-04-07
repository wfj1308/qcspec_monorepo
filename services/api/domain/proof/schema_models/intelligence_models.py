"""Intelligence and analytics request models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


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

