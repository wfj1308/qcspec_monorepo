"""Specification and gate editor routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.api.core import NormRefResolverService
from services.api.dependencies import get_boq_specification_service, get_normref_resolver
from services.api.domain import BOQSpecificationService
from services.api.domain.proof.schemas import GateRuleGenerateBody, GateRuleNormImportBody, GateRuleRollbackBody, GateRuleSaveBody, SpecDictSaveBody

router = APIRouter()


class NormRefVerifyBody(BaseModel):
    uri: str = ""
    protocol_uri: str = ""
    spu_uri: str = ""
    actual_data: dict[str, Any] = Field(default_factory=dict)
    design_data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class NormRefBatchValidateBody(BaseModel):
    rules: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    normref_version: str = "latest"
    scope: str = ""


class NormRefOverrideSetBody(BaseModel):
    rule_id: str
    version: str
    selected_uri: str
    reason: str = ""
    updated_by: str = ""


class NormRefOverrideClearBody(BaseModel):
    rule_id: str
    version: str


def _resolve_verify_uri(*, uri: str, protocol_uri: str, spu_uri: str) -> str:
    direct = (uri or protocol_uri).strip()
    if direct:
        return direct
    spu = spu_uri.strip()
    if not spu:
        return ""
    if "/spu/" in spu:
        head, tail = spu.split("/spu/", 1)
        return f"{head}/qc/{tail}"
    return spu


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


@router.get("/resolve")
async def resolve_normref_protocol(
    uri: str,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    out = resolver.resolve_protocol(uri=uri)
    if not bool(out.get("ok")):
        raise HTTPException(404, str(out.get("error") or "protocol_not_found"))
    return out


@router.post("/verify")
async def verify_normref_protocol(
    body: NormRefVerifyBody,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    resolved_uri = _resolve_verify_uri(
        uri=str(body.uri or ""),
        protocol_uri=str(body.protocol_uri or ""),
        spu_uri=str(body.spu_uri or ""),
    )
    if not resolved_uri:
        raise HTTPException(400, "uri or protocol_uri or spu_uri is required")
    out = resolver.verify_protocol(
        uri=resolved_uri,
        actual_data=dict(body.actual_data or {}),
        design_data=dict(body.design_data or {}),
        context=dict(body.context or {}),
    )
    if not bool(out.get("ok")):
        if str(out.get("error") or "") == "protocol_not_found":
            raise HTTPException(404, "protocol_not_found")
        raise HTTPException(400, str(out.get("error") or "verify_failed"))
    return out


@router.get("/rules/{rule_id}")
async def get_normref_rule(
    rule_id: str,
    version: str = "latest",
    scope: str = "",
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    out = resolver.get_rule(rule_id=rule_id, version=version, scope=scope)
    if not bool(out.get("ok")):
        error = str(out.get("error") or "")
        if error in {"rule_not_found", "rule_version_not_found", "rule_scope_not_found"}:
            raise HTTPException(404, error)
        raise HTTPException(400, error or "get_rule_failed")
    return out


@router.get("/rules")
async def list_normref_rules(
    category: str = "",
    version: str = "latest",
    scope: str = "",
    refresh: bool = False,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    if refresh:
        resolver.refresh_rule_catalog()
    return resolver.list_rules(category=category, version=version, scope=scope)


@router.get("/rules-conflicts")
async def list_normref_rule_conflicts(
    category: str = "",
    version: str = "latest",
    scope: str = "",
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.list_rule_conflicts(category=category, version=version, scope=scope)


@router.post("/rules/refresh")
async def refresh_normref_rules(
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.refresh_rule_catalog()


@router.get("/rules-overrides")
async def list_normref_rule_overrides(
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    return resolver.list_rule_overrides()


@router.post("/rules-overrides/set")
async def set_normref_rule_override(
    body: NormRefOverrideSetBody,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    out = resolver.set_rule_override(
        rule_id=body.rule_id,
        version=body.version,
        selected_uri=body.selected_uri,
        reason=body.reason,
        updated_by=body.updated_by,
    )
    if not bool(out.get("ok")):
        error = str(out.get("error") or "set_override_failed")
        if error in {"rule_not_found", "selected_uri_not_in_candidates"}:
            raise HTTPException(404, error)
        raise HTTPException(400, error)
    return out


@router.post("/rules-overrides/clear")
async def clear_normref_rule_override(
    body: NormRefOverrideClearBody,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    out = resolver.clear_rule_override(rule_id=body.rule_id, version=body.version)
    if not bool(out.get("ok")):
        raise HTTPException(400, str(out.get("error") or "clear_override_failed"))
    return out


@router.post("/validate")
async def validate_normref_rules(
    body: NormRefBatchValidateBody,
    resolver: NormRefResolverService = Depends(get_normref_resolver),
):
    if not body.rules:
        raise HTTPException(400, "rules is required")
    return resolver.validate_rules(
        rules=[str(x).strip() for x in body.rules if str(x).strip()],
        data=dict(body.data or {}),
        normref_version=str(body.normref_version or "latest"),
        scope=str(body.scope or ""),
    )
