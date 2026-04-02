"""Specification and gate editor routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.api.core import NormRefResolverService
from services.api.dependencies import get_boq_specification_service, get_normref_resolver
from services.api.domain import BOQSpecificationService
from services.api.proof_schemas import GateRuleGenerateBody, GateRuleNormImportBody, GateRuleRollbackBody, GateRuleSaveBody, SpecDictSaveBody

router = APIRouter()


@router.get("/gate-editor/{subitem_code}")
async def get_gate_editor_payload(
    subitem_code: str,
    project_uri: str,
    specification_service: BOQSpecificationService = Depends(get_boq_specification_service),
):
    return await specification_service.gate_editor_payload(
        project_uri=project_uri,
        subitem_code=subitem_code,
    )


@router.post("/gate-editor/import-norm")
async def import_gate_rules_from_norm(
    body: GateRuleNormImportBody,
    specification_service: BOQSpecificationService = Depends(get_boq_specification_service),
):
    return await specification_service.import_gate_rules_from_norm(body=body)


@router.post("/gate-editor/generate-via-ai")
async def generate_gate_rules_via_ai(
    body: GateRuleGenerateBody,
    specification_service: BOQSpecificationService = Depends(get_boq_specification_service),
):
    return await specification_service.generate_gate_rules_via_ai(body=body)


@router.post("/gate-editor/save")
async def save_gate_rule_version(
    body: GateRuleSaveBody,
    specification_service: BOQSpecificationService = Depends(get_boq_specification_service),
):
    return await specification_service.save_gate_rule_version(body=body)


@router.post("/gate-editor/rollback")
async def rollback_gate_rule_version(
    body: GateRuleRollbackBody,
    specification_service: BOQSpecificationService = Depends(get_boq_specification_service),
):
    return await specification_service.rollback_gate_rule_version(body=body)


@router.get("/spec-dict/{spec_dict_key}")
async def get_spec_dict(
    spec_dict_key: str,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.get_spec_dict(spec_dict_key=spec_dict_key)


@router.post("/spec-dict/save")
async def save_spec_dict(
    body: SpecDictSaveBody,
    specification_service: BOQSpecificationService = Depends(get_boq_specification_service),
):
    return await specification_service.save_spec_dict(body=body)


@router.get("/spec-dict-resolve-threshold")
async def resolve_spec_dict_threshold(
    gate_id: str,
    context: str = "",
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.resolve_threshold(gate_id=gate_id, context=context)
