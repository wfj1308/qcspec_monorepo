"""Specification and gate-editor flow helpers."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.domain.boq.specification_flows import (
    generate_rules_via_ai,
    get_gate_editor_payload,
    import_from_norm_library,
    rollback_gate_rule,
    save_gate_rule_version,
    get_spec_dict,
    resolve_dynamic_threshold,
    save_spec_dict,
)


def get_gate_editor_payload_flow(
    *,
    project_uri: str,
    subitem_code: str,
    sb: Client,
) -> dict[str, Any]:
    return get_gate_editor_payload(
        sb=sb,
        project_uri=project_uri,
        subitem_code=subitem_code,
    )


def import_gate_rules_from_norm_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return import_from_norm_library(
        sb=sb,
        spec_uri=str(body.spec_uri or ""),
        context=str(body.context or ""),
    )


def generate_gate_rules_via_ai_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return generate_rules_via_ai(
        prompt=str(body.prompt or ""),
        subitem_code=str(body.subitem_code or ""),
    )


def save_gate_rule_version_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return save_gate_rule_version(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        subitem_code=str(body.subitem_code or ""),
        gate_id_base=str(body.gate_id_base or ""),
        rules=list(body.rules or []),
        execution_strategy=str(body.execution_strategy or "all_pass"),
        fail_action=str(body.fail_action or "trigger_review_trip"),
        apply_to_similar=bool(body.apply_to_similar),
        executor_uri=str(body.executor_uri or "v://executor/chief-engineer/"),
        metadata=dict(body.metadata or {}),
    )


def rollback_gate_rule_version_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return rollback_gate_rule(
        sb=sb,
        project_uri=str(body.project_uri or ""),
        subitem_code=str(body.subitem_code or ""),
        target_proof_id=str(body.target_proof_id or ""),
        target_version=str(body.target_version or ""),
        apply_to_similar=bool(body.apply_to_similar),
        executor_uri=str(body.executor_uri or "v://executor/chief-engineer/"),
    )


def get_spec_dict_flow(*, spec_dict_key: str, sb: Client) -> dict[str, Any]:
    return get_spec_dict(
        sb=sb,
        spec_dict_key=spec_dict_key,
    )


def save_spec_dict_flow(*, body: Any, sb: Client) -> dict[str, Any]:
    return save_spec_dict(
        sb=sb,
        spec_dict_key=str(body.spec_dict_key or ""),
        title=str(body.title or ""),
        version=str(body.version or "v1.0"),
        authority=str(body.authority or ""),
        spec_uri=str(body.spec_uri or ""),
        items=dict(body.items or {}),
        metadata=dict(body.metadata or {}),
        is_active=bool(body.is_active if body.is_active is not None else True),
    )


def resolve_dynamic_threshold_flow(*, gate_id: str, context: str, sb: Client) -> dict[str, Any]:
    return resolve_dynamic_threshold(
        sb=sb,
        gate_id=gate_id,
        context={"context": context},
    )
