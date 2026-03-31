"""Specification and gate editor routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase import Client

from services.api.core import NormRefResolverService
from services.api.dependencies import get_normref_resolver, get_supabase
from services.api.proof_flow_service import (
    generate_gate_rules_via_ai_flow,
    get_gate_editor_payload_flow,
    get_spec_dict_flow,
    import_gate_rules_from_norm_flow,
    rollback_gate_rule_version_flow,
    save_gate_rule_version_flow,
    save_spec_dict_flow,
)
from services.api.proof_schemas import GateRuleGenerateBody, GateRuleNormImportBody, GateRuleRollbackBody, GateRuleSaveBody, SpecDictSaveBody

router = APIRouter()


@router.get("/gate-editor/{subitem_code}")
async def get_gate_editor_payload(
    subitem_code: str,
    project_uri: str,
    sb: Client = Depends(get_supabase),
):
    return get_gate_editor_payload_flow(
        project_uri=project_uri,
        subitem_code=subitem_code,
        sb=sb,
    )


@router.post("/gate-editor/import-norm")
async def import_gate_rules_from_norm(body: GateRuleNormImportBody, sb: Client = Depends(get_supabase)):
    return import_gate_rules_from_norm_flow(body=body, sb=sb)


@router.post("/gate-editor/generate-via-ai")
async def generate_gate_rules_via_ai(body: GateRuleGenerateBody, sb: Client = Depends(get_supabase)):
    return generate_gate_rules_via_ai_flow(body=body, sb=sb)


@router.post("/gate-editor/save")
async def save_gate_rule_version(body: GateRuleSaveBody, sb: Client = Depends(get_supabase)):
    return save_gate_rule_version_flow(body=body, sb=sb)


@router.post("/gate-editor/rollback")
async def rollback_gate_rule_version(body: GateRuleRollbackBody, sb: Client = Depends(get_supabase)):
    return rollback_gate_rule_version_flow(body=body, sb=sb)


@router.get("/spec-dict/{spec_dict_key}")
async def get_spec_dict(
    spec_dict_key: str,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.get_spec_dict(spec_dict_key=spec_dict_key)


@router.post("/spec-dict/save")
async def save_spec_dict(body: SpecDictSaveBody, sb: Client = Depends(get_supabase)):
    return save_spec_dict_flow(body=body, sb=sb)


@router.get("/spec-dict-resolve-threshold")
async def resolve_spec_dict_threshold(
    gate_id: str,
    context: str = "",
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.resolve_threshold(gate_id=gate_id, context=context)
