"""Component UTXO and material linkage request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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

