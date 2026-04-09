"""Realtime field validator with explain output."""

from __future__ import annotations

from typing import Any

from services.api.domain.signpeg.models import FieldValidationResult
from services.api.domain.signpeg.runtime.gate_explainer import generate_explanation


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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


async def validate_field_realtime(
    *,
    form_code: str,
    field_key: str,
    value: Any,
    context: dict[str, Any],
    language: str = "zh",
) -> FieldValidationResult:
    lang = _lang(language)
    v = _to_float(value)
    norm_ref = _to_text(context.get("norm_ref") or context.get("norm_uri")).strip()
    unit = _to_text(context.get("unit")).strip()

    design = _to_float(context.get("design_value") or context.get("design_diameter"))
    min_value = _to_float(context.get("min_value") or context.get("min"))
    max_value = _to_float(context.get("max_value") or context.get("max"))
    tolerance_pct = _to_float(context.get("tolerance_pct") or context.get("allowed_pct"))

    form_key = _to_text(form_code).strip().lower()
    field_token = _to_text(field_key).strip().lower()
    if design is None and field_token in {"hole_diameter", "diameter"} and ("桥施7" in form_code or "bridge7" in form_key):
        design = 1.5
    if tolerance_pct is None and field_token in {"hole_diameter", "diameter"} and ("桥施7" in form_code or "bridge7" in form_key):
        tolerance_pct = 5.0
    if not norm_ref and field_token in {"hole_diameter", "diameter"}:
        norm_ref = "JTG F80/1-2017 第7.1条"

    status: str = "ok"
    expected = ""
    actual = _to_text(value).strip()
    deviation = ""

    if v is None:
        status = "warning"
        expected = _to_text(context.get("expected")).strip()
    else:
        actual = f"{_fmt_number(v)}{unit}".strip()
        if min_value is not None:
            expected = f">={_fmt_number(min_value)}{unit}".strip()
            if v < min_value - 1e-9:
                status = "blocking"
                deviation = f"{_fmt_number(v - min_value)}{unit}".strip()
        if max_value is not None and status != "blocking":
            expected = f"<={_fmt_number(max_value)}{unit}".strip()
            if v > max_value + 1e-9:
                status = "blocking"
                deviation = f"+{_fmt_number(v - max_value)}{unit}".strip()
        if design is not None and tolerance_pct is not None:
            expected = f"{_fmt_number(design)}{unit} ±{_fmt_number(tolerance_pct)}%"
            if abs(design) > 1e-9:
                delta_pct = (v - design) / design * 100.0
                deviation = f"{delta_pct:+.1f}%"
                if abs(delta_pct) > tolerance_pct + 1e-9:
                    status = "blocking"
                elif abs(delta_pct) > tolerance_pct * 0.6 and status != "blocking":
                    status = "warning"

    if status == "ok":
        message = "Field value is within acceptable range." if lang == "en" else "当前数值在可接受范围内。"
    else:
        message = await generate_explanation(
            {
                "field": field_key,
                "expected": expected,
                "actual": actual,
                "deviation": deviation or "-",
                "norm_ref": norm_ref or "-",
                "severity": "blocking" if status == "blocking" else "warning",
            },
            language=lang,
        )
    return FieldValidationResult(
        field=_to_text(field_key).strip(),
        value=value,
        status=status,  # type: ignore[arg-type]
        message=message,
        norm_ref=norm_ref,
        expected=expected,
        actual=actual,
        deviation=deviation,
        language=lang,  # type: ignore[arg-type]
    )

