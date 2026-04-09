"""Process-chain status explain layer."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from services.api.domain.signpeg.models import ProcessBlockingReason, ProcessExplainResult


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _lang(language: str) -> str:
    return "en" if _to_text(language).strip().lower().startswith("en") else "zh"


def _build_reason(*, reason_type: str, text: str, action: str) -> ProcessBlockingReason:
    return ProcessBlockingReason(type=reason_type, description=text, action=action)


def _step_name(chain: dict[str, Any], step_id: str) -> str:
    for row in _as_list(chain.get("steps")):
        if not isinstance(row, dict):
            continue
        if _to_text(row.get("step_id")).strip() == step_id:
            return _to_text(row.get("name")).strip() or step_id
    return step_id


def _blocked_detail_for_step(chain: dict[str, Any], step_id: str) -> dict[str, Any]:
    matrix = _as_dict(chain.get("state_matrix"))
    for row in _as_list(matrix.get("blocked_details")):
        item = _as_dict(row)
        if _to_text(item.get("step_id")).strip() == step_id:
            return item
    return {}


def _reasons_from_blocked_detail(detail: dict[str, Any], language: str) -> list[ProcessBlockingReason]:
    lang = _lang(language)
    reasons: list[ProcessBlockingReason] = []

    for pre in _as_list(detail.get("missing_pre_conditions")):
        pre_name = _to_text(pre).strip()
        if not pre_name:
            continue
        reasons.append(
            _build_reason(
                reason_type="previous_step_incomplete",
                text=(
                    f"Previous step not complete: {pre_name}"
                    if lang == "en"
                    else f"前置工序未完成：{pre_name}"
                ),
                action=(f"Go handle {pre_name}" if lang == "en" else f"前往处理 {pre_name}"),
            )
        )

    for code in _as_list(detail.get("missing_materials")):
        m_code = _to_text(code).strip()
        if not m_code:
            continue
        reasons.append(
            _build_reason(
                reason_type="material_iqc_missing",
                text=(
                    f"Material IQC missing or not approved: {m_code}"
                    if lang == "en"
                    else f"材料IQC未录入或未通过：{m_code}"
                ),
                action=(f"Go submit IQC for {m_code}" if lang == "en" else f"前往录入 {m_code} 的进场检验"),
            )
        )

    for item in _as_list(detail.get("missing_inspection_batches")):
        row = _as_dict(item)
        code = _to_text(row.get("material_code")).strip()
        req = float(row.get("required_qty") or 0.0)
        act = float(row.get("actual_qty") or 0.0)
        if not code:
            continue
        reasons.append(
            _build_reason(
                reason_type="inspection_batch_missing",
                text=(
                    f"Inspection-batch quantity not enough for {code}: required {req}, actual {act}"
                    if lang == "en"
                    else f"{code} 检验批数量不足：要求 {req}，当前 {act}"
                ),
                action=(
                    f"Create inspection batch for {code}"
                    if lang == "en"
                    else f"前往录入 {code} 检验批"
                ),
            )
        )

    return reasons


def explain_process_status(
    *,
    chain: dict[str, Any],
    component_uri: str,
    step_id: str,
    current_status: str,
    language: str = "zh",
) -> ProcessExplainResult:
    lang = _lang(language)
    status = _to_text(current_status).strip().lower()
    if status not in {"locked", "active", "completed"}:
        raise HTTPException(status_code=400, detail=f"invalid current_status: {current_status}")

    name = _step_name(chain, step_id)
    if status == "completed":
        return ProcessExplainResult(
            step=name,
            status="completed",
            summary=("This step is completed." if lang == "en" else "该工序已完成。"),
            blocking_reasons=[],
            estimated_unblock=("Already unlocked." if lang == "en" else "已处于可继续状态。"),
            language=lang,  # type: ignore[arg-type]
        )
    if status == "active":
        return ProcessExplainResult(
            step=name,
            status="active",
            summary=("This step is active and can be processed now." if lang == "en" else "该工序已激活，可立即处理。"),
            blocking_reasons=[],
            estimated_unblock=("No blocker." if lang == "en" else "无阻塞项。"),
            language=lang,  # type: ignore[arg-type]
        )

    detail = _blocked_detail_for_step(chain, step_id)
    reasons = _reasons_from_blocked_detail(detail, lang)
    if not reasons:
        reasons = [
            _build_reason(
                reason_type="unknown_lock",
                text=(
                    f"Step is locked for component {component_uri}."
                    if lang == "en"
                    else f"构件 {component_uri} 当前工序处于锁定状态。"
                ),
                action=("Refresh process chain and check blockers." if lang == "en" else "刷新工序链并检查前置条件。"),
            )
        ]
    return ProcessExplainResult(
        step=name,
        status="locked",
        summary=(
            f"{name} is currently locked and cannot proceed."
            if lang == "en"
            else f"{name} 当前无法进行。"
        ),
        blocking_reasons=reasons,
        estimated_unblock=(
            f"Auto-unlock after finishing the {len(reasons)} blocker(s)."
            if lang == "en"
            else f"完成以上 {len(reasons)} 项后将自动解锁。"
        ),
        language=lang,  # type: ignore[arg-type]
    )

