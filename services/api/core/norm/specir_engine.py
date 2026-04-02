"""
SpecIR shared engine:
- resolve executable rules from v://norm URIs
- context-aware threshold/operator matching
- dynamic PASS/FAIL evaluation with deviation percentage
"""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

_SUPABASE_RULE_CACHE: list[dict[str, Any]] | None = None


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        m = re.search(r"[-+]?\d+(?:\.\d+)?", _to_text(value))
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _fmt_num(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _tokenize(*parts: Any) -> set[str]:
    merged = " ".join(_to_text(x).lower() for x in parts if _to_text(x).strip())
    merged = merged.replace("/", " ").replace("-", " ").replace("_", " ")
    words = [x for x in re.split(r"\s+", merged) if x]
    return set(words)


def normalize_operator(raw_op: Any) -> str:
    raw = _to_text(raw_op).strip()
    if not raw:
        return ""
    text = (
        raw.replace("≤", "<=")
        .replace("≥", ">=")
        .replace("＝", "=")
        .replace("﹤", "<")
        .replace("﹥", ">")
        .strip()
        .lower()
    )
    if text in {"<=", "le", "lte", "max", "upper", "not_more_than", "less_or_equal"}:
        return "<="
    if text in {">=", "ge", "gte", "min", "lower", "not_less_than", "greater_or_equal"}:
        return ">="
    if text in {"=", "==", "eq", "equals", "equal"}:
        return "="
    if text in {"<", "lt"}:
        return "<"
    if text in {">", "gt"}:
        return ">"
    if (
        "±" in raw
        or text in {"+/-", "+-", "plusminus", "range", "between"}
        or "容差" in text
        or "偏差" in text
        or "区间" in text
    ):
        return "±"
    return text


def normalize_spec_uri(raw: Any) -> str:
    text = _to_text(raw).strip()
    if not text:
        return ""
    text = text.replace("v://standard/", "v://norm/")
    if text.startswith("v://norm/"):
        return text
    compact = re.sub(r"\s+", "_", text)
    return f"v://norm/{compact}"


def derive_spec_uri(
    state_data: dict[str, Any] | None,
    *,
    row_norm_uri: Any = None,
    fallback_norm_ref: Any = None,
) -> str:
    sd = state_data if isinstance(state_data, dict) else {}
    candidates = [
        sd.get("spec_uri"),
        sd.get("norm_uri"),
        row_norm_uri,
        sd.get("norm_ref"),
        sd.get("rule_ref"),
        fallback_norm_ref,
    ]
    for cand in candidates:
        uri = normalize_spec_uri(cand)
        if uri:
            return uri
    return ""


def _parse_spec_uri(spec_uri: str) -> dict[str, str]:
    text = normalize_spec_uri(spec_uri)
    m = re.match(
        r"^v://norm/(?P<code>[^/@#?]+)(?:@(?P<version>[^/#?]+))?(?P<path>/[^#?]*)?(?:#(?P<anchor>[^?]+))?",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return {"uri": text, "code": "", "version": "", "path": "", "anchor": ""}
    return {
        "uri": text,
        "code": _to_text(m.group("code")).upper(),
        "version": _to_text(m.group("version")),
        "path": _to_text(m.group("path")).strip("/"),
        "anchor": _to_text(m.group("anchor")),
    }


@lru_cache(maxsize=1)
def _builtin_rules() -> list[dict[str, Any]]:
    return [
        {
            "code": "GB50204",
            "version": "2015",
            "path": "5.3.3",
            "anchor": "spacing_tolerance",
            "spec_uri": "v://norm/GB50204@2015/5.3.3#spacing_tolerance",
            "operator": "±",
            "threshold": 200.0,
            "tolerance": 10.0,
            "unit": "mm",
            "metric_keywords": ["spacing", "rebar", "steel", "钢筋", "间距"],
            "component_keywords": [],
            "excerpt": "GB50204 5.3.3: 钢筋间距允许偏差按构件类型执行控制范围。",
            "source": "builtin",
        },
        {
            "code": "GB50204",
            "version": "2015",
            "path": "5.3.2",
            "anchor": "diameter_tolerance",
            "spec_uri": "v://norm/GB50204@2015/5.3.2#diameter_tolerance",
            "operator": "±",
            "threshold": 0.0,
            "tolerance": 0.2,
            "unit": "mm",
            "metric_keywords": ["diameter", "偏差", "diameter_tolerance", "直径"],
            "component_keywords": [],
            "excerpt": "GB50204 5.3.2: 钢筋直径偏差应处于允许容差区间内。",
            "source": "builtin",
        },
        {
            "code": "GB50204",
            "version": "2015",
            "path": "5.3.4",
            "anchor": "deviation_limit",
            "spec_uri": "v://norm/GB50204@2015/5.3.4#deviation_limit",
            "operator": "<=",
            "threshold": 8.0,
            "tolerance": None,
            "unit": "mm",
            "metric_keywords": ["deviation", "偏差"],
            "component_keywords": ["main_beam", "主梁"],
            "excerpt": "GB50204 5.3.4: 主梁相关偏差控制值更严格。",
            "source": "builtin",
        },
        {
            "code": "GB50204",
            "version": "2015",
            "path": "5.3.4",
            "anchor": "deviation_limit",
            "spec_uri": "v://norm/GB50204@2015/5.3.4#deviation_limit",
            "operator": "<=",
            "threshold": 5.0,
            "tolerance": None,
            "unit": "mm",
            "metric_keywords": ["deviation", "偏差"],
            "component_keywords": ["guardrail", "护栏"],
            "excerpt": "GB50204 5.3.4: 护栏偏差控制值按构件类别单独判定。",
            "source": "builtin",
        },
        {
            "code": "JTG_F80",
            "version": "2017",
            "path": "3.1",
            "anchor": "compaction_min",
            "spec_uri": "v://norm/JTG_F80@2017/3.1#compaction_min",
            "operator": ">=",
            "threshold": 96.0,
            "tolerance": None,
            "unit": "%",
            "metric_keywords": ["compaction", "density", "压实度", "压实"],
            "component_keywords": [],
            "excerpt": "JTG F80 3.1: 压实度检测值不得低于规范最低阈值。",
            "source": "builtin",
        },
        {
            "code": "JTG_F80",
            "version": "2017",
            "path": "4.2",
            "anchor": "flatness_max",
            "spec_uri": "v://norm/JTG_F80@2017/4.2#flatness_max",
            "operator": "<=",
            "threshold": 2.0,
            "tolerance": None,
            "unit": "m/km",
            "metric_keywords": ["flatness", "iri", "平整度", "路面"],
            "component_keywords": [],
            "excerpt": "JTG F80 4.2: 路面平整度需控制在最大允许值以内。",
            "source": "builtin",
        },
        {
            "code": "JTG_F80",
            "version": "2017",
            "path": "4.3",
            "anchor": "crack_width_max",
            "spec_uri": "v://norm/JTG_F80@2017/4.3#crack_width_max",
            "operator": "<=",
            "threshold": 0.2,
            "tolerance": None,
            "unit": "mm",
            "metric_keywords": ["crack", "width", "裂缝", "缝宽"],
            "component_keywords": [],
            "excerpt": "JTG F80 4.3: 裂缝宽度应满足最大允许值控制。",
            "source": "builtin",
        },
        {
            "code": "GB50204",
            "version": "2015",
            "path": "7.1",
            "anchor": "concrete_strength_min",
            "spec_uri": "v://norm/GB50204@2015/7.1#concrete_strength_min",
            "operator": ">=",
            "threshold": 30.0,
            "tolerance": None,
            "unit": "MPa",
            "metric_keywords": ["strength", "concrete", "混凝土", "强度"],
            "component_keywords": [],
            "excerpt": "GB50204 7.1: 混凝土强度应满足设计与规范的最低要求。",
            "source": "builtin",
        },
    ]


def _fetch_supabase_rules(sb: Any) -> list[dict[str, Any]]:
    global _SUPABASE_RULE_CACHE
    if _SUPABASE_RULE_CACHE is not None:
        return _SUPABASE_RULE_CACHE
    if sb is None:
        return []
    tables = ("spec_ir_rules", "specir_rules", "qc_spec_rules")
    for table in tables:
        try:
            res = sb.table(table).select("*").limit(500).execute()
            rows = res.data if isinstance(getattr(res, "data", None), list) else []
            parsed: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                uri = normalize_spec_uri(
                    row.get("spec_uri")
                    or row.get("norm_uri")
                    or row.get("uri")
                    or ""
                )
                parsed_uri = _parse_spec_uri(uri)
                parsed.append(
                    {
                        "code": _to_text(row.get("code") or parsed_uri["code"]).upper(),
                        "version": _to_text(row.get("version") or parsed_uri["version"]),
                        "path": _to_text(row.get("path") or parsed_uri["path"]),
                        "anchor": _to_text(row.get("anchor") or parsed_uri["anchor"]),
                        "spec_uri": uri,
                        "operator": normalize_operator(row.get("operator") or row.get("standard_op") or ""),
                        "threshold": _to_float(row.get("threshold") or row.get("standard_value")),
                        "tolerance": _to_float(row.get("tolerance") or row.get("standard_tolerance")),
                        "unit": _to_text(row.get("unit")),
                        "metric_keywords": row.get("metric_keywords") if isinstance(row.get("metric_keywords"), list) else [],
                        "component_keywords": row.get("component_keywords") if isinstance(row.get("component_keywords"), list) else [],
                        "excerpt": _to_text(row.get("excerpt") or row.get("summary") or ""),
                        "source": "supabase",
                    }
                )
            if parsed:
                _SUPABASE_RULE_CACHE = parsed
                return parsed
        except Exception:
            continue
    _SUPABASE_RULE_CACHE = []
    return []


def _version_key(version: str) -> tuple[int, str]:
    nums = re.findall(r"\d+", _to_text(version))
    if nums:
        return (int(nums[0]), _to_text(version))
    return (0, _to_text(version))


def _infer_default_spec_uri(metric_tokens: set[str]) -> str:
    if {"compaction", "density", "压实度", "压实"} & metric_tokens:
        return "v://norm/JTG_F80/3.1#compaction_min"
    if {"flatness", "iri", "平整度", "路面"} & metric_tokens:
        return "v://norm/JTG_F80/4.2#flatness_max"
    if {"spacing", "rebar", "钢筋", "间距"} & metric_tokens:
        return "v://norm/GB50204/5.3.3#spacing_tolerance"
    if {"concrete", "strength", "混凝土", "强度"} & metric_tokens:
        return "v://norm/GB50204/7.1#concrete_strength_min"
    if {"deviation", "偏差"} & metric_tokens:
        return "v://norm/GB50204/5.3.4#deviation_limit"
    return ""


def resolve_spec_rule(
    *,
    spec_uri: Any = None,
    metric: Any = None,
    test_type: Any = None,
    test_name: Any = None,
    context: dict[str, Any] | None = None,
    sb: Any = None,
) -> dict[str, Any]:
    ctx = context if isinstance(context, dict) else {}
    metric_tokens = _tokenize(metric, test_type, test_name, ctx.get("component_type"), ctx.get("structure_type"))

    requested_uri = normalize_spec_uri(spec_uri)
    if not requested_uri:
        requested_uri = _infer_default_spec_uri(metric_tokens)
    parsed = _parse_spec_uri(requested_uri)

    candidates = _builtin_rules() + _fetch_supabase_rules(sb)
    if not candidates:
        return {
            "spec_uri": requested_uri,
            "effective_spec_uri": requested_uri,
            "code": parsed.get("code") or "",
            "version": parsed.get("version") or "",
            "path": parsed.get("path") or "",
            "anchor": parsed.get("anchor") or "",
            "operator": "",
            "threshold": None,
            "tolerance": None,
            "unit": "",
            "excerpt": "规范条文未命中规则库，使用原始 URI 透传。",
            "source": "none",
            "context_matched": False,
            "version_auto_upgraded": False,
        }

    scored: list[tuple[int, dict[str, Any]]] = []
    req_code = _to_text(parsed.get("code")).upper()
    req_anchor = _to_text(parsed.get("anchor")).lower()
    req_path = _to_text(parsed.get("path")).lower()
    req_version = _to_text(parsed.get("version")).strip()
    component_tokens = _tokenize(ctx.get("component_type"), ctx.get("structure_type"))

    for rule in candidates:
        score = 0
        rule_code = _to_text(rule.get("code")).upper()
        if req_code and req_code == rule_code:
            score += 50
        elif req_code:
            continue

        rule_path = _to_text(rule.get("path")).lower()
        rule_anchor = _to_text(rule.get("anchor")).lower()
        if req_anchor and (req_anchor == rule_anchor or req_anchor in _to_text(rule.get("spec_uri")).lower()):
            score += 25
        if req_path and (req_path == rule_path or req_path in _to_text(rule.get("spec_uri")).lower()):
            score += 20

        rule_metrics = _tokenize(*((rule.get("metric_keywords") or [])))
        if metric_tokens and rule_metrics:
            overlap = metric_tokens & rule_metrics
            score += min(len(overlap) * 8, 24)

        rule_components = _tokenize(*((rule.get("component_keywords") or [])))
        context_matched = bool(rule_components and component_tokens and (rule_components & component_tokens))
        if context_matched:
            score += 18
        elif rule_components and component_tokens:
            score -= 8

        if req_version:
            if _to_text(rule.get("version")) == req_version:
                score += 20
            else:
                score -= 10

        scored.append((score, rule))

    if not scored:
        return {
            "spec_uri": requested_uri,
            "effective_spec_uri": requested_uri,
            "code": parsed.get("code") or "",
            "version": parsed.get("version") or "",
            "path": parsed.get("path") or "",
            "anchor": parsed.get("anchor") or "",
            "operator": "",
            "threshold": None,
            "tolerance": None,
            "unit": "",
            "excerpt": "规范条文未命中规则库，使用原始 URI 透传。",
            "source": "none",
            "context_matched": False,
            "version_auto_upgraded": False,
        }

    scored.sort(key=lambda item: (item[0], _version_key(_to_text(item[1].get("version")))), reverse=True)
    best_score = scored[0][0]
    top = [rule for score, rule in scored if score == best_score]
    top.sort(key=lambda r: _version_key(_to_text(r.get("version"))), reverse=True)
    winner = top[0]

    effective_uri = normalize_spec_uri(winner.get("spec_uri") or requested_uri)
    version_auto_upgraded = bool(not req_version and _to_text(winner.get("version")).strip())

    rule_components = _tokenize(*((winner.get("component_keywords") or [])))
    context_matched = bool(rule_components and component_tokens and (rule_components & component_tokens))

    return {
        "spec_uri": requested_uri,
        "effective_spec_uri": effective_uri,
        "code": _to_text(winner.get("code")).upper(),
        "version": _to_text(winner.get("version")),
        "path": _to_text(winner.get("path")),
        "anchor": _to_text(winner.get("anchor")),
        "operator": normalize_operator(winner.get("operator")),
        "threshold": _to_float(winner.get("threshold")),
        "tolerance": _to_float(winner.get("tolerance")),
        "unit": _to_text(winner.get("unit")),
        "excerpt": _to_text(winner.get("excerpt") or "该规范条文作为判定基准。"),
        "source": _to_text(winner.get("source") or "builtin"),
        "context_matched": context_matched,
        "version_auto_upgraded": version_auto_upgraded,
    }


def threshold_text(operator: Any, threshold: float | None, tolerance: float | None, unit: Any = "") -> str:
    op = normalize_operator(operator)
    u = _to_text(unit).strip()
    if op == "±" and threshold is not None and tolerance is not None:
        base = f"{_fmt_num(threshold)} ± {_fmt_num(tolerance)}"
        return f"{base} {u}".strip()
    if threshold is not None and op:
        return f"{op} {_fmt_num(threshold)} {u}".strip()
    if threshold is not None:
        return f"{_fmt_num(threshold)} {u}".strip()
    return "-"


def result_cn(result: Any) -> str:
    token = _to_text(result).strip().upper()
    if token == "PASS":
        return "合格"
    if token == "FAIL":
        return "不合格"
    if token == "OBSERVE":
        return "观察"
    if token == "CANCELLED":
        return "取消"
    return "待定"


def spec_excerpt(spec_uri: Any, *, fallback_excerpt: Any = None) -> str:
    text = _to_text(fallback_excerpt).strip()
    if text:
        return text
    uri = _to_text(spec_uri).upper()
    if "GB50204" in uri:
        return "GB50204: 该条文用于约束结构施工质量阈值与允许偏差。"
    if "JTG" in uri:
        return "JTG: 该条文用于公路工程检测项的合格性判定。"
    return "该规范条文作为本次检测判定的基准来源。"


def evaluate_measurements(
    *,
    values: list[float],
    operator: Any,
    threshold: float | None,
    tolerance: float | None = None,
    fallback_result: Any = "PENDING",
) -> dict[str, Any]:
    fb = _to_text(fallback_result).strip().upper() or "PENDING"
    vals = [float(v) for v in values] if values else []
    if not vals:
        return {"result": fb, "deviation_percent": None}

    op = normalize_operator(operator)
    rep = sum(vals) / len(vals)
    t = threshold
    tol = tolerance
    dev: float | None = None
    result = fb

    if op == "±" and t is not None and tol is not None:
        lower = t - tol
        upper = t + tol
        result = "PASS" if all(lower <= v <= upper for v in vals) else "FAIL"
        exceed = max((abs(v - t) - tol) for v in vals)
        denom = abs(t) if abs(t) > 1e-9 else (abs(tol) if abs(tol) > 1e-9 else 1.0)
        dev = (exceed / denom) * 100.0
    elif t is not None and op == "<=":
        result = "PASS" if all(v <= t for v in vals) else "FAIL"
        dev = ((max(vals) - t) / (abs(t) if abs(t) > 1e-9 else 1.0)) * 100.0
    elif t is not None and op == ">=":
        result = "PASS" if all(v >= t for v in vals) else "FAIL"
        dev = ((t - min(vals)) / (abs(t) if abs(t) > 1e-9 else 1.0)) * 100.0
    elif t is not None and op == "=":
        result = "PASS" if all(abs(v - t) < 1e-9 for v in vals) else "FAIL"
        dev = (abs(rep - t) / (abs(t) if abs(t) > 1e-9 else 1.0)) * 100.0
    elif t is not None and op == "<":
        result = "PASS" if all(v < t for v in vals) else "FAIL"
        dev = ((max(vals) - t) / (abs(t) if abs(t) > 1e-9 else 1.0)) * 100.0
    elif t is not None and op == ">":
        result = "PASS" if all(v > t for v in vals) else "FAIL"
        dev = ((t - min(vals)) / (abs(t) if abs(t) > 1e-9 else 1.0)) * 100.0

    if dev is not None:
        dev = round(dev, 4)

    return {
        "result": result,
        "result_cn": result_cn(result),
        "deviation_percent": dev,
        "representative_value": round(rep, 4),
    }
