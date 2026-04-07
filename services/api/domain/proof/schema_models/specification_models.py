"""Specification and gate editor request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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

