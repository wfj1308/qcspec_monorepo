"""Explain layer orchestration for Gate, process status and realtime validation."""

from __future__ import annotations

from typing import Any

from services.api.domain.signpeg.models import (
    FieldValidateRequest,
    FieldValidationResult,
    GateExplainRequest,
    GateExplainResult,
    ProcessExplainRequest,
    ProcessExplainResult,
)
from services.api.domain.signpeg.runtime.gate_explainer import explain_gate_result
from services.api.domain.signpeg.runtime.process_explainer import explain_process_status
from services.api.domain.signpeg.runtime.realtime_validator import validate_field_realtime


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


async def explain_gate(*, body: GateExplainRequest) -> GateExplainResult:
    return await explain_gate_result(
        form_code=body.form_code,
        gate_result=_as_dict(body.gate_result),
        norm_context=_as_dict(body.norm_context),
        language=body.language,
    )


def _load_process_chain(
    *,
    sb: Any,
    project_uri: str,
    component_uri: str,
    chain_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if chain_snapshot:
        return _as_dict(chain_snapshot)
    from services.api.domain.boqpeg.runtime.process_chain import get_process_chain

    loaded = get_process_chain(
        sb=sb,
        project_uri=project_uri,
        component_uri=component_uri,
        chain_snapshot=None,
    )
    return _as_dict(loaded.get("chain"))


def explain_process(
    *,
    sb: Any,
    body: ProcessExplainRequest,
) -> ProcessExplainResult:
    chain = _load_process_chain(
        sb=sb,
        project_uri=body.project_uri,
        component_uri=body.component_uri,
        chain_snapshot=body.chain_snapshot,
    )
    return explain_process_status(
        chain=chain,
        component_uri=body.component_uri,
        step_id=body.step_id,
        current_status=body.current_status,
        language=body.language,
    )


async def validate_field(*, body: FieldValidateRequest) -> FieldValidationResult:
    return await validate_field_realtime(
        form_code=body.form_code,
        field_key=body.field_key,
        value=body.value,
        context=_as_dict(body.context),
        language=body.language,
    )

