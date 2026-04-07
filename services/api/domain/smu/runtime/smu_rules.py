"""SPU/template and rule resolution helpers for SMU flow orchestration."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

from services.api.domain.specir.runtime.refs import resolve_spu_ref_pack
from services.api.domain.smu.templates import (
    NORMREF_BY_PREFIX,
    ROLE_ALLOW_BY_PREFIX,
    SPU_LIBRARY_ROOT_URI,
    SPU_NAME_HINTS,
    SPU_TEMPLATE_LIBRARY,
)


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = _to_text(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _round4(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except Exception:
        return None


def _normalized_hint_text(text: str) -> str:
    lowered = _to_text(text).strip().lower()
    lowered = lowered.replace("_", "").replace("-", "").replace(" ", "")
    return lowered


def _match_spu_template_by_name(item_name: str) -> tuple[str, list[str]]:
    normalized = _normalized_hint_text(item_name)
    if not normalized:
        return ("", [])
    matched: list[str] = []
    template_id = ""
    for candidate, keywords in SPU_NAME_HINTS.items():
        for kw in keywords:
            norm_kw = _normalized_hint_text(kw)
            if norm_kw and norm_kw in normalized:
                template_id = candidate
                matched.append(kw)
        if template_id:
            break
    return (template_id, matched)


def _safe_eval_formula(expression: str, variables: dict[str, float]) -> float | None:
    expr = _to_text(expression).strip()
    if not expr:
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return None

    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError("unsupported_constant")
        if isinstance(node, ast.Name):
            key = _to_text(node.id).strip()
            if key in variables:
                return float(variables[key])
            raise KeyError(key)
        if isinstance(node, ast.BinOp):
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if abs(right) <= 1e-12:
                    raise ZeroDivisionError
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
            raise ValueError("unsupported_operator")
        if isinstance(node, ast.UnaryOp):
            val = _eval_node(node.operand)
            if isinstance(node.op, ast.USub):
                return -val
            if isinstance(node.op, ast.UAdd):
                return +val
            raise ValueError("unsupported_unary")
        raise ValueError("unsupported_expression")

    try:
        return float(_eval_node(tree))
    except Exception:
        return None


def _formula_aliases_map() -> dict[str, tuple[str, ...]]:
    return {
        "length": ("length", "l"),
        "width": ("width", "w"),
        "height": ("height", "h"),
        "pile_length": ("pile_length", "length", "l"),
        "pile_diameter": ("pile_diameter", "diameter", "d"),
        "pile_count": ("pile_count", "count"),
        "unit_weight": ("unit_weight",),
        "count": ("count",),
        "claimed_amount": ("claimed_amount", "claim_quantity", "amount"),
        "quantity": ("quantity", "claim_quantity", "measured_value", "design_quantity", "approved_quantity"),
    }


def _resolve_formula_variables(*, formula_def: dict[str, Any], measurement: dict[str, Any], design_quantity: float | None, approved_quantity: float | None) -> tuple[dict[str, float], list[str]]:
    aliases = _formula_aliases_map()
    inputs = _as_dict(measurement)
    target_qty = approved_quantity if approved_quantity is not None and approved_quantity > 0 else design_quantity
    vars_out: dict[str, float] = {}
    missing: list[str] = []
    for var in _as_list(formula_def.get("variables")):
        key = _to_text(var).strip()
        if not key:
            continue
        candidates = aliases.get(key) or (key,)
        val: float | None = None
        for name in candidates:
            candidate = _to_float(inputs.get(name))
            if candidate is not None:
                val = candidate
                break
        if val is None and key in {"quantity", "claimed_amount"} and target_qty is not None:
            val = float(target_qty)
        if val is None:
            missing.append(key)
        else:
            vars_out[key] = float(val)
    return (vars_out, missing)


def _build_spu_formula_audit(
    *,
    template: dict[str, Any],
    measurement: dict[str, Any],
    design_quantity: float | None,
    approved_quantity: float | None,
) -> dict[str, Any]:
    formula = _as_dict(template.get("formula"))
    if not formula:
        return {}
    expected = _to_float(measurement.get("claim_quantity"))
    if expected is None:
        expected = _to_float(measurement.get("measured_value"))
    if expected is None:
        expected = approved_quantity if approved_quantity is not None else design_quantity
    expected = _round4(expected)
    expression = _to_text(formula.get("expression") or "").strip()
    fallback_expression = _to_text(formula.get("fallback_expression") or "").strip()
    variables, missing = _resolve_formula_variables(
        formula_def=formula,
        measurement=measurement,
        design_quantity=design_quantity,
        approved_quantity=approved_quantity,
    )
    actual = _safe_eval_formula(expression, variables) if expression else None
    if actual is None and fallback_expression:
        actual = _safe_eval_formula(fallback_expression, variables)
    actual = _round4(actual)
    tolerance_ratio = _to_float(formula.get("tolerance_ratio"))
    if tolerance_ratio is None:
        tolerance_ratio = 0.05
    diff = None if expected is None or actual is None else _round4(abs(expected - actual))
    allowed = None if expected is None else _round4(abs(expected) * tolerance_ratio)
    status = "PENDING"
    if expected is not None and actual is not None and diff is not None and allowed is not None:
        status = "PASS" if diff <= allowed + 1e-9 else "FAIL"
    return {
        "formula_name": _to_text(formula.get("name") or "").strip(),
        "expression": expression,
        "fallback_expression": fallback_expression,
        "variables": variables,
        "missing_variables": missing,
        "expected_quantity": expected,
        "computed_quantity": actual,
        "difference": diff,
        "allowed_difference": allowed,
        "tolerance_ratio": tolerance_ratio,
        "quantity_unit": _to_text(formula.get("quantity_unit") or "").strip(),
        "status": status,
    }


def _resolve_spu_template(item_no: str, item_name: str) -> dict[str, Any]:
    code = _to_text(item_no).strip()
    prefix = code.split("-")[0] if code else ""
    template_by_prefix = {
        "101": "SPU_Contract",
        "102": "SPU_Contract",
        "401": "SPU_Bridge",
        "403": "SPU_Reinforcement",
        "405": "SPU_Concrete",
        "600": "SPU_Physical",
        "702": "SPU_Landscape",
    }
    template_id = template_by_prefix.get(prefix, "SPU_Physical")
    from_name, matched = _match_spu_template_by_name(item_name)
    if from_name:
        template_id = from_name
    template = _as_dict(SPU_TEMPLATE_LIBRARY.get(template_id))
    formula = _as_dict(template.get("formula"))
    quantity_unit = _to_text(formula.get("quantity_unit") or "").strip()
    ref_pack = resolve_spu_ref_pack(
        item_code=code,
        item_name=item_name,
        quantity_unit=quantity_unit,
        template_id=template_id,
    )
    ref_spu_uri = _to_text(ref_pack.get("ref_spu_uri") or "").strip()
    ref_quota_uri = _to_text(ref_pack.get("ref_quota_uri") or "").strip()
    ref_meter_rule_uri = _to_text(ref_pack.get("ref_meter_rule_uri") or "").strip()
    return {
        "spu_template_id": template_id,
        "spu_root_uri": SPU_LIBRARY_ROOT_URI,
        "spu_library_uri": _to_text(template.get("library_uri") or f"{SPU_LIBRARY_ROOT_URI}/{template_id}").strip(),
        "spu_label": _to_text(template.get("label") or template_id).strip(),
        "spu_contexts": list(template.get("contexts") or []),
        "spu_geometry": template.get("geometry") or {},
        "spu_formula": formula,
        "spu_normpeg_refs": list(template.get("normpeg_refs") or []),
        "spu_form_schema": list(template.get("form_schema") or []),
        "ref_spu_uri": ref_spu_uri,
        "ref_quota_uri": ref_quota_uri,
        "ref_meter_rule_uri": ref_meter_rule_uri,
        "match_hints": matched,
    }


def list_spu_template_library() -> dict[str, Any]:
    templates: list[dict[str, Any]] = []
    for template_id in sorted(SPU_TEMPLATE_LIBRARY.keys()):
        tpl = _as_dict(SPU_TEMPLATE_LIBRARY.get(template_id))
        templates.append(
            {
                "template_id": template_id,
                "library_uri": _to_text(tpl.get("library_uri") or f"{SPU_LIBRARY_ROOT_URI}/{template_id}").strip(),
                "label": _to_text(tpl.get("label") or template_id).strip(),
                "contexts": list(tpl.get("contexts") or []),
                "normpeg_refs": list(tpl.get("normpeg_refs") or []),
                "formula": _as_dict(tpl.get("formula")),
                "geometry": _as_dict(tpl.get("geometry")),
                "form_schema": list(tpl.get("form_schema") or []),
            }
        )
    return {
        "ok": True,
        "library_root_uri": SPU_LIBRARY_ROOT_URI,
        "templates": templates,
        "count": len(templates),
    }


def _resolve_norm_refs(item_no: str, item_name: str, *, template_norm_refs: list[str] | None = None) -> list[str]:
    refs: list[str] = []
    prefix = _to_text(item_no).strip().split("-")[0]
    if template_norm_refs:
        refs.extend([_to_text(x).strip() for x in template_norm_refs if _to_text(x).strip()])
    if prefix in NORMREF_BY_PREFIX:
        refs.extend(list(NORMREF_BY_PREFIX[prefix]))
    lowered = _to_text(item_name).strip().lower()
    if "桥" in item_name or "beam" in lowered or "pier" in lowered:
        refs.extend(list(NORMREF_BY_PREFIX.get("401") or []))
    if "路面" in item_name or "pavement" in lowered:
        refs.extend(list(NORMREF_BY_PREFIX.get("600") or []))
    if "绿化" in item_name or "landscape" in lowered:
        refs.extend(list(NORMREF_BY_PREFIX.get("702") or []))
    if "钢筋" in item_name or "rebar" in lowered:
        refs.extend(list(NORMREF_BY_PREFIX.get("403") or []))
    out: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        token = _to_text(ref).strip()
        if not token:
            continue
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _resolve_allowed_roles(item_no: str, spu_template_id: str) -> list[str]:
    prefix = _to_text(item_no).strip().split("-")[0]
    mapped = ROLE_ALLOW_BY_PREFIX.get(prefix)
    if mapped:
        return list(mapped)
    if spu_template_id == "SPU_Contract":
        return ["OWNER", "SUPERVISOR"]
    return ["AI", "SUPERVISOR", "OWNER"]


def _is_contract_payload(item_name: str, measurement: dict[str, Any]) -> bool:
    lowered = _to_text(item_name).lower()
    if "合同" in item_name or "contract" in lowered:
        return True
    for key in ("voucher_ref", "claimed_amount", "payment_cycle"):
        if _to_text(measurement.get(key) or "").strip():
            return True
    return False


def _resolve_bridge_table_template_path() -> str:
    env_path = _to_text(os.getenv("DOCPEG_BRIDGE_TEMPLATE") or "").strip()
    candidates = [
        env_path,
        "services/templates/bridge_table_template.docx",
        "services/api/templates/bridge_table_template.docx",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        p = Path(candidate)
        try:
            if p.is_file():
                return str(p.resolve())
        except Exception:
            continue
    return ""


def _resolve_docpeg_template(item_no: str, item_name: str) -> dict[str, Any]:
    bridge_template = _resolve_bridge_table_template_path()
    prefix = _to_text(item_no).strip().split("-")[0]
    lowered = _to_text(item_name).strip().lower()
    if prefix in {"401", "403", "405"} or "桥" in item_name or "beam" in lowered or "pier" in lowered:
        return {
            "template_id": "DOCPEG_BRIDGE_TABLE",
            "template_path": bridge_template,
            "fallback_template": "bridge_table_template",
            "render_mode": "table",
            "doc_type": "bridge_progress_certificate",
            "auto_docpeg": True,
        }
    if prefix in {"101", "102"} or "合同" in item_name or "contract" in lowered:
        return {
            "template_id": "DOCPEG_CONTRACT_SETTLEMENT",
            "template_path": "",
            "fallback_template": "contract_settlement",
            "render_mode": "json",
            "doc_type": "contract_settlement_certificate",
            "auto_docpeg": True,
        }
    return {
        "template_id": "DOCPEG_GENERIC",
        "template_path": "",
        "fallback_template": "generic_docpeg",
        "render_mode": "json",
        "doc_type": "generic_progress_certificate",
        "auto_docpeg": True,
    }


__all__ = [
    "_build_spu_formula_audit",
    "_is_contract_payload",
    "_resolve_allowed_roles",
    "_resolve_docpeg_template",
    "_resolve_norm_refs",
    "_resolve_spu_template",
    "list_spu_template_library",
]
