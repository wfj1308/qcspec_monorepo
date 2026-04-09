"""AI explain layer for Gate verdicts."""

from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any

import httpx

from services.api.domain.signpeg.models import ExplainIssue, GateExplainResult


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _to_text(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _lang(language: str) -> str:
    return "en" if _to_text(language).strip().lower().startswith("en") else "zh"


def _fmt_number(value: float) -> str:
    if abs(value - int(value)) < 1e-9:
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _threshold_to_expected(threshold: dict[str, Any]) -> str:
    if not threshold:
        return ""
    op = _to_text(threshold.get("operator")).strip().lower()
    target = _to_text(threshold.get("value")).strip()
    unit = _to_text(threshold.get("unit")).strip()
    op_map = {
        "gte": "≥",
        "gt": ">",
        "lte": "≤",
        "lt": "<",
        "eq": "=",
        "between": "between",
    }
    symbol = op_map.get(op, op or "requirement")
    if op == "between":
        low = _to_text(threshold.get("min")).strip()
        high = _to_text(threshold.get("max")).strip()
        if low or high:
            return f"{low} ~ {high}{unit}" if unit else f"{low} ~ {high}"
    if target:
        return f"{symbol}{target}{unit}" if unit else f"{symbol}{target}"
    return _to_text(threshold.get("raw")).strip()


def _compute_deviation(check: dict[str, Any]) -> str:
    direct = _to_text(check.get("deviation")).strip()
    if direct:
        return direct
    actual = _to_float(check.get("actual_value") or check.get("actual"))
    design = _to_float(check.get("design_value") or check.get("target_value"))
    if actual is None or design is None or abs(design) < 1e-9:
        return ""
    pct = (actual - design) / design * 100.0
    sign = "+" if pct >= 0 else ""
    return f"{sign}{_fmt_number(pct)}%"


def _normalize_check_rows(gate_result: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [row for row in _as_list(gate_result.get("checks")) if isinstance(row, dict)]
    if checks:
        return checks
    out: list[dict[str, Any]] = []
    for row in _as_list(gate_result.get("failed_mandatory")):
        if isinstance(row, dict):
            out.append({**row, "pass": False, "severity": row.get("severity") or "mandatory"})
    for row in _as_list(gate_result.get("failed_warning")):
        if isinstance(row, dict):
            out.append({**row, "pass": False, "severity": row.get("severity") or "warning"})
    return out


def _severity_from_check(check: dict[str, Any]) -> str:
    if bool(check.get("pass")):
        return "info"
    severity = _to_text(check.get("severity")).strip().lower()
    if severity in {"mandatory", "critical", "blocking"}:
        return "blocking"
    if severity in {"warning", "warn"}:
        return "warning"
    return "blocking"


def _fallback_explanation(context: dict[str, Any], language: str) -> str:
    field = _to_text(context.get("field")).strip() or "check item"
    expected = _to_text(context.get("expected")).strip() or "-"
    actual = _to_text(context.get("actual")).strip() or "-"
    deviation = _to_text(context.get("deviation")).strip() or "-"
    norm_ref = _to_text(context.get("norm_ref")).strip() or "-"
    severity = _to_text(context.get("severity")).strip().lower()
    if _lang(language) == "en":
        lead = "This item does not satisfy the Gate requirement." if severity == "blocking" else "Please review this item."
        return (
            f"{lead} {field}: expected {expected}, actual {actual}, deviation {deviation}. "
            f"Reference: {norm_ref}. Recommended action: correct and re-check before resubmission."
        )
    lead = "该检查项不满足Gate要求。" if severity == "blocking" else "该检查项建议复核。"
    return (
        f"{lead}{field}：要求 {expected}，实测 {actual}，偏差 {deviation}。"
        f"依据 {norm_ref}，建议整改后复检并重新提交。"
    )


async def generate_explanation(context: dict[str, Any], language: str = "zh") -> str:
    api_key = _to_text(os.getenv("ANTHROPIC_API_KEY")).strip()
    model = _to_text(os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022").strip()
    timeout_s = float(_to_text(os.getenv("EXPLAIN_AI_TIMEOUT") or "10").strip() or "10")
    if not api_key:
        return _fallback_explanation(context, language)

    lang = _lang(language)
    prompt = (
        "You are a civil engineering quality-control expert.\n"
        "Explain the failed check in simple, practical language.\n"
        "Output plain text with 2-3 short sentences.\n"
        f"Language: {'English' if lang == 'en' else 'Chinese'}.\n\n"
        f"Field: {_to_text(context.get('field')).strip()}\n"
        f"Expected: {_to_text(context.get('expected')).strip()}\n"
        f"Actual: {_to_text(context.get('actual')).strip()}\n"
        f"Deviation: {_to_text(context.get('deviation')).strip()}\n"
        f"NormRef: {_to_text(context.get('norm_ref')).strip()}\n"
        f"Severity: {_to_text(context.get('severity')).strip()}\n"
    )
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 220,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if res.status_code < 400:
                content_blocks = _as_list(_as_dict(res.json()).get("content"))
                text = _to_text(_as_dict(content_blocks[0]).get("text") if content_blocks else "").strip()
                if text:
                    return text
    except Exception:
        pass
    return _fallback_explanation(context, language)


def _build_next_steps(issues: list[ExplainIssue], language: str) -> list[str]:
    lang = _lang(language)
    if not issues:
        return [
            "Proceed to signature submission." if lang == "en" else "可继续提交签名。",
        ]
    has_blocking = any(item.severity == "blocking" for item in issues)
    key_field = issues[0].field if issues else ""
    if lang == "en":
        if has_blocking:
            return [
                f"Rectify {key_field or 'the failed check'} to meet the requirement.",
                "Re-check measurements and submit the form again.",
                "Ask supervisor to confirm the re-inspection plan.",
            ]
        return [
            "Review warning items before final submission.",
            "Keep evidence and continue to the next step.",
        ]
    if has_blocking:
        return [
            f"先整改“{key_field or '不合格项'}”，达到规范要求。",
            "复测后重新提交该表单。",
            "联系监理确认复检方案。",
        ]
    return [
        "建议先复核告警项，再提交签认。",
        "保留现场证据后可继续下一步。",
    ]


async def explain_gate_result(
    *,
    form_code: str,
    gate_result: dict[str, Any],
    norm_context: dict[str, Any],
    language: str = "zh",
) -> GateExplainResult:
    lang = _lang(language)
    checks = _normalize_check_rows(_as_dict(gate_result))
    norm_refs: list[str] = []
    issues: list[ExplainIssue] = []

    for idx, check in enumerate(checks):
        passed = bool(check.get("pass"))
        if passed:
            continue
        field = _to_text(check.get("label") or check.get("field") or check.get("check_id")).strip() or f"check-{idx + 1}"
        expected = (
            _to_text(check.get("expected")).strip()
            or _threshold_to_expected(_as_dict(check.get("threshold")))
            or _to_text(_as_dict(norm_context).get("expected")).strip()
        )
        actual = _to_text(check.get("actual") or check.get("actual_value")).strip()
        if not actual:
            actual_data = _as_dict(gate_result).get("actual_data")
            if isinstance(actual_data, dict):
                actual = _to_text(actual_data.get(_to_text(check.get("check_id")).strip())).strip()
        deviation = _compute_deviation(check)
        norm_ref = (
            _to_text(check.get("norm_ref")).strip()
            or _to_text(_as_dict(norm_context).get("norm_ref")).strip()
            or _to_text(_as_dict(norm_context).get("protocol_uri")).strip()
        )
        severity = _severity_from_check(check)
        explanation = await generate_explanation(
            {
                "field": field,
                "expected": expected,
                "actual": actual,
                "deviation": deviation,
                "norm_ref": norm_ref,
                "severity": severity,
            },
            language=lang,
        )
        issues.append(
            ExplainIssue(
                field=field,
                expected=expected,
                actual=actual,
                deviation=deviation,
                norm_ref=norm_ref,
                severity=severity,  # type: ignore[arg-type]
                explanation=explanation,
            )
        )
        if norm_ref and norm_ref not in norm_refs:
            norm_refs.append(norm_ref)

    protocol_uri = _to_text(norm_context.get("protocol_uri") or norm_context.get("doc_type")).strip()
    if protocol_uri and protocol_uri not in norm_refs:
        norm_refs.append(protocol_uri)

    result_token = _to_text(gate_result.get("result")).strip().upper()
    passed = result_token == "PASS" and not any(item.severity == "blocking" for item in issues)

    if passed:
        summary = "Gate passed. This form can proceed to signing." if lang == "en" else "Gate校验通过，可进入签名流程。"
    elif issues:
        lead = issues[0]
        if lang == "en":
            summary = f"{_to_text(form_code).strip() or 'Form'} failed: {lead.field} is out of tolerance."
        else:
            summary = f"{_to_text(form_code).strip() or '表单'}未通过：{lead.field}存在超差。"
    else:
        summary = "Gate check failed." if lang == "en" else "Gate校验未通过。"

    return GateExplainResult(
        passed=passed,
        summary=summary,
        issues=issues,
        next_steps=_build_next_steps(issues, lang),
        norm_refs=norm_refs,
        language=lang,  # type: ignore[arg-type]
    )


def make_demo_failed_gate_result(*, hole_diameter: float, design_diameter: float = 1.5) -> dict[str, Any]:
    deviation_pct = ((hole_diameter - design_diameter) / design_diameter * 100.0) if abs(design_diameter) > 1e-9 else 0.0
    return {
        "result": "FAIL",
        "actual_data": {"hole_diameter": hole_diameter},
        "checks": [
            {
                "check_id": "hole_diameter",
                "label": "孔径检查",
                "pass": False,
                "severity": "mandatory",
                "actual_value": hole_diameter,
                "design_value": design_diameter,
                "deviation": f"{deviation_pct:+.1f}%",
                "threshold": {"operator": "gte", "value": design_diameter, "unit": "m"},
                "norm_ref": "JTG F80/1-2017 第7.1条",
                "evaluated_at": datetime.now(UTC).isoformat(),
            }
        ],
    }
