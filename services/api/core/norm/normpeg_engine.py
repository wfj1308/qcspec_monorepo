"""
NormPeg dynamic dictionary and context-aware threshold resolver.

This module provides:
- structured NormEntry loading (builtin + optional Supabase table)
- URI + fragment parsing for v://norm/...#param
- get_threshold(spec_uri, context) dynamic routing
- deterministic evaluation helpers for QCGate integration
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        text = _to_text(value).strip()
        if not text:
            return None
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None


def _parse_version_key(version: str) -> tuple[int, str]:
    nums = re.findall(r"\d+", _to_text(version))
    if nums:
        return int(nums[0]), _to_text(version)
    return 0, _to_text(version)


def _normalize_context_values(context: Any) -> list[str]:
    values: list[str] = []
    alias_map = {
        "主梁": "main_beam",
        "梁": "main_beam",
        "mainbeam": "main_beam",
        "main_beam": "main_beam",
        "护栏": "guardrail",
        "栏杆": "guardrail",
        "guard_rail": "guardrail",
        "guardrail": "guardrail",
    }

    def _append_token(raw: Any) -> None:
        text = _to_text(raw).strip().lower()
        if not text:
            return
        values.append(text)
        mapped = alias_map.get(_to_text(raw).strip().lower())
        if mapped:
            values.append(mapped)

    if isinstance(context, str):
        _append_token(context)
        return values
    if isinstance(context, dict):
        for key in (
            "context",
            "context_key",
            "component_type",
            "structure_type",
            "part_type",
            "stake",
            "name",
        ):
            _append_token(context.get(key))
    dedup: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item and item not in seen:
            dedup.append(item)
            seen.add(item)
    return dedup


def _normalize_norm_uri(raw_uri: Any) -> str:
    uri = _to_text(raw_uri).strip()
    if not uri:
        return ""
    if uri.startswith("v://standard/"):
        uri = uri.replace("v://standard/", "v://norm/")
    if not uri.startswith("v://norm/"):
        uri = f"v://norm/{uri.strip('/')}"
    return uri


def parse_norm_uri(raw_uri: Any) -> dict[str, str]:
    uri = _normalize_norm_uri(raw_uri)
    m = re.match(
        r"^v://norm/(?P<code>[^/@#?]+)(?:@(?P<version>[^/#?]+))?(?P<path>/[^#?]*)?(?:#(?P<fragment>[^?]+))?",
        uri,
        flags=re.IGNORECASE,
    )
    if not m:
        return {
            "uri": uri,
            "code": "",
            "version": "",
            "path": "",
            "fragment": "",
            "base_uri": uri,
        }
    code = _to_text(m.group("code")).upper()
    version = _to_text(m.group("version"))
    path = _to_text(m.group("path")).strip("/")
    fragment = _to_text(m.group("fragment")).strip()
    base_uri = f"v://norm/{code}{('@' + version) if version else ''}{('/' + path) if path else ''}"
    return {
        "uri": uri,
        "code": code,
        "version": version,
        "path": path,
        "fragment": fragment,
        "base_uri": base_uri,
    }


@dataclass(slots=True)
class NormEntry:
    uri: str
    title: str
    content: str
    params: dict[str, Any]
    code: str = ""
    version: str = ""
    path: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "NormEntry":
        raw_uri = _normalize_norm_uri(payload.get("uri") or payload.get("spec_uri") or "")
        parsed = parse_norm_uri(raw_uri)
        return cls(
            uri=raw_uri,
            title=_to_text(payload.get("title") or ""),
            content=_to_text(payload.get("content") or payload.get("excerpt") or ""),
            params=payload.get("params") if isinstance(payload.get("params"), dict) else {},
            code=_to_text(payload.get("code") or parsed["code"]).upper(),
            version=_to_text(payload.get("version") or parsed["version"]),
            path=_to_text(payload.get("path") or parsed["path"]),
        )


def _builtin_entries() -> list[NormEntry]:
    rows = [
        {
            "uri": "v://norm/GB50204@2015/5.3.2",
            "title": "Rebar diameter deviation thresholds",
            "content": "GB50204 5.3.2: rebar diameter deviation shall be controlled by component class.",
            "params": {
                "diameter_tolerance": {
                    "default": [-2.0, 2.0],
                    "contexts": {
                        "main_beam": [-1.0, 1.0],
                        "guardrail": [-5.0, 5.0],
                    },
                    "unit": "mm",
                    "mode": "deviation_from_design",
                    "operator": "range",
                }
            },
        },
        {
            "uri": "v://norm/GB50204@2015/5.3.3",
            "title": "Rebar spacing tolerance",
            "content": "GB50204 5.3.3: spacing shall meet design +/- tolerance range.",
            "params": {
                "spacing_tolerance": {
                    "default": [-10.0, 10.0],
                    "unit": "mm",
                    "mode": "deviation_from_design",
                    "operator": "range",
                }
            },
        },
        {
            "uri": "v://norm/JTG_F80@2017/4.3",
            "title": "Crack width threshold",
            "content": "JTG F80 4.3: crack width must be less than or equal to threshold.",
            "params": {
                "crack_width_max": {
                    "default": 0.2,
                    "unit": "mm",
                    "mode": "absolute",
                    "operator": "<=",
                }
            },
        },
    ]
    return [NormEntry.from_payload(x) for x in rows]


def _load_entries_from_supabase(sb: Any) -> list[NormEntry]:
    if sb is None:
        return []
    table_names = ("norm_entries", "norm_entry", "spec_norm_entries")
    entries: list[NormEntry] = []
    for table in table_names:
        try:
            res = sb.table(table).select("*").limit(2000).execute()
        except Exception:
            continue
        rows = res.data if isinstance(getattr(res, "data", None), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            payload = {
                "uri": row.get("uri") or row.get("spec_uri") or data.get("uri"),
                "title": row.get("title") or data.get("title"),
                "content": row.get("content") or row.get("excerpt") or data.get("content"),
                "params": row.get("params") if isinstance(row.get("params"), dict) else data.get("params"),
                "code": row.get("code") or data.get("code"),
                "version": row.get("version") or data.get("version"),
                "path": row.get("path") or data.get("path"),
            }
            uri = _normalize_norm_uri(payload.get("uri"))
            if not uri:
                continue
            payload["uri"] = uri
            entries.append(NormEntry.from_payload(payload))
        if entries:
            break
    return entries


class NormPegEngine:
    """URI-addressable smart dictionary with context routing."""

    def __init__(self, entries: list[NormEntry]):
        self.entries = entries
        self._by_exact_uri: dict[str, NormEntry] = {}
        self._by_code_path: dict[tuple[str, str], list[NormEntry]] = {}
        for entry in entries:
            parsed = parse_norm_uri(entry.uri)
            base_uri = parsed["base_uri"]
            self._by_exact_uri[base_uri] = entry
            key = (_to_text(entry.code or parsed["code"]).upper(), _to_text(entry.path or parsed["path"]).strip("/"))
            self._by_code_path.setdefault(key, []).append(entry)
        for key, group in self._by_code_path.items():
            group.sort(key=lambda item: _parse_version_key(item.version), reverse=True)

    @classmethod
    def from_sources(cls, *, sb: Any = None) -> "NormPegEngine":
        merged: dict[str, NormEntry] = {}
        for entry in _builtin_entries() + _load_entries_from_supabase(sb):
            base_uri = parse_norm_uri(entry.uri)["base_uri"]
            if not base_uri:
                continue
            merged[base_uri] = entry
        return cls(list(merged.values()))

    def _select_entry(self, spec_uri: Any) -> tuple[NormEntry | None, dict[str, str]]:
        parsed = parse_norm_uri(spec_uri)
        if not parsed["uri"]:
            return None, parsed

        if parsed["base_uri"] in self._by_exact_uri:
            return self._by_exact_uri[parsed["base_uri"]], parsed

        key = (parsed["code"], parsed["path"])
        candidates = self._by_code_path.get(key) or []
        if not candidates:
            return None, parsed

        if parsed["version"]:
            for entry in candidates:
                if _to_text(entry.version) == _to_text(parsed["version"]):
                    return entry, parsed
        return candidates[0], parsed

    def resolve_norm_rule(self, spec_uri: Any, context: Any = None) -> dict[str, Any]:
        """Public API alias for context-routed norm rule resolution."""
        return self.get_threshold(spec_uri, context)

    def get_threshold(self, spec_uri: Any, context: Any = None) -> dict[str, Any]:
        """
        Resolve threshold for URI like:
        v://norm/GB50204/5.3.2#diameter_tolerance
        and dynamically route by context.
        """
        entry, parsed = self._select_entry(spec_uri)
        if entry is None:
            return {
                "found": False,
                "spec_uri": _normalize_norm_uri(spec_uri),
                "effective_spec_uri": _normalize_norm_uri(spec_uri),
                "requested_version": parsed.get("version") or "",
                "resolved_version": "",
                "version_auto_upgraded": False,
                "context_key": "",
                "context_matched": False,
                "param_key": parsed.get("fragment") or "",
                "threshold": None,
                "unit": "",
                "operator": "",
                "mode": "absolute",
                "spec_excerpt": "",
                "version": "",
                "code": parsed.get("code") or "",
            }

        param_key = _to_text(parsed.get("fragment") or "").strip()
        params = entry.params if isinstance(entry.params, dict) else {}
        if not param_key and len(params) == 1:
            param_key = next(iter(params.keys()))

        param_cfg = params.get(param_key) if param_key else None
        if not isinstance(param_cfg, dict):
            return {
                "found": False,
                "spec_uri": _normalize_norm_uri(spec_uri),
                "effective_spec_uri": entry.uri,
                "requested_version": parsed.get("version") or "",
                "resolved_version": entry.version,
                "version_auto_upgraded": False,
                "context_key": "",
                "context_matched": False,
                "param_key": param_key,
                "threshold": None,
                "unit": "",
                "operator": "",
                "mode": "absolute",
                "spec_excerpt": entry.content,
                "version": entry.version,
                "code": entry.code,
            }

        context_keys = _normalize_context_values(context)
        contexts = param_cfg.get("contexts") if isinstance(param_cfg.get("contexts"), dict) else {}
        selected_context = ""
        selected_threshold: Any = param_cfg.get("default")

        for key in context_keys:
            if key in contexts:
                selected_context = key
                selected_threshold = contexts[key]
                break

        effective_spec_uri = f"{parse_norm_uri(entry.uri)['base_uri']}#{param_key}" if param_key else entry.uri
        requested_version = _to_text(parsed.get("version") or "").strip()
        resolved_version = _to_text(entry.version).strip()
        version_auto_upgraded = bool(
            (not requested_version and resolved_version)
            or (requested_version and resolved_version and requested_version != resolved_version)
        )

        return {
            "found": True,
            "spec_uri": _normalize_norm_uri(spec_uri),
            "effective_spec_uri": effective_spec_uri,
            "requested_version": requested_version,
            "resolved_version": resolved_version,
            "version_auto_upgraded": version_auto_upgraded,
            "context_key": selected_context,
            "context_matched": bool(selected_context),
            "param_key": param_key,
            "threshold": selected_threshold,
            "unit": _to_text(param_cfg.get("unit") or "").strip(),
            "operator": _to_text(param_cfg.get("operator") or "range").strip().lower(),
            "mode": _to_text(param_cfg.get("mode") or "absolute").strip().lower() or "absolute",
            "spec_excerpt": _to_text(entry.content).strip(),
            "version": _to_text(entry.version).strip(),
            "code": _to_text(entry.code).strip(),
            "title": _to_text(entry.title).strip(),
            "params_snapshot": json.loads(json.dumps(param_cfg, ensure_ascii=False, default=str)),
        }

    def evaluate(
        self,
        *,
        spec_uri: Any,
        context: Any,
        values: list[float],
        design_value: float | None = None,
    ) -> dict[str, Any]:
        threshold_pack = self.get_threshold(spec_uri, context)
        if not threshold_pack.get("found"):
            return {
                "matched": False,
                "threshold": threshold_pack,
                "result": "PENDING",
                "deviation_percent": None,
                "values_for_eval": list(values or []),
                "design_value": design_value,
            }

        vals = [float(v) for v in (values or [])]
        if not vals:
            return {
                "matched": True,
                "threshold": threshold_pack,
                "result": "PENDING",
                "deviation_percent": None,
                "values_for_eval": [],
                "design_value": design_value,
            }

        mode = _to_text(threshold_pack.get("mode") or "absolute").lower()
        eval_values = list(vals)
        if mode == "deviation_from_design" and design_value is not None:
            eval_values = [float(v) - float(design_value) for v in vals]

        raw_threshold = threshold_pack.get("threshold")
        operator = _to_text(threshold_pack.get("operator") or "range").strip().lower()

        result = "PENDING"
        deviation_percent: float | None = None
        lower: float | None = None
        upper: float | None = None
        center: float | None = None
        tolerance: float | None = None

        if isinstance(raw_threshold, (list, tuple)) and len(raw_threshold) >= 2:
            lo = _to_float(raw_threshold[0])
            hi = _to_float(raw_threshold[1])
            if lo is not None and hi is not None:
                lower, upper = min(lo, hi), max(lo, hi)
                center = round((lower + upper) / 2.0, 6)
                tolerance = round((upper - lower) / 2.0, 6)
                result = "PASS" if all(lower <= value <= upper for value in eval_values) else "FAIL"
                exceed = 0.0
                for value in eval_values:
                    if value < lower:
                        exceed = max(exceed, lower - value)
                    elif value > upper:
                        exceed = max(exceed, value - upper)
                base = max(abs(upper), abs(lower), 1.0)
                deviation_percent = round((exceed / base) * 100.0, 4)
        else:
            bound = _to_float(raw_threshold)
            if bound is not None:
                center = bound
                if operator in {"<=", "lt", "max"}:
                    result = "PASS" if all(value <= bound for value in eval_values) else "FAIL"
                    deviation_percent = round(((max(eval_values) - bound) / max(abs(bound), 1.0)) * 100.0, 4)
                elif operator in {">=", "gt", "min"}:
                    result = "PASS" if all(value >= bound for value in eval_values) else "FAIL"
                    deviation_percent = round(((bound - min(eval_values)) / max(abs(bound), 1.0)) * 100.0, 4)
                else:
                    result = "PASS" if all(abs(value - bound) < 1e-9 for value in eval_values) else "FAIL"
                    deviation_percent = round((abs(sum(eval_values) / len(eval_values) - bound) / max(abs(bound), 1.0)) * 100.0, 4)

        return {
            "matched": True,
            "threshold": threshold_pack,
            "result": result,
            "deviation_percent": deviation_percent,
            "values_for_eval": eval_values,
            "design_value": design_value,
            "lower": lower,
            "upper": upper,
            "center": center,
            "tolerance": tolerance,
        }


def resolve_normpeg_eval(
    *,
    spec_uri: Any,
    context: Any,
    values: list[float],
    design_value: float | None,
    sb: Any = None,
) -> dict[str, Any]:
    engine = NormPegEngine.from_sources(sb=sb)
    return engine.evaluate(
        spec_uri=spec_uri,
        context=context,
        values=values,
        design_value=design_value,
    )


def resolve_norm_rule(
    *,
    spec_uri: Any,
    context: Any = None,
    sb: Any = None,
) -> dict[str, Any]:
    """
    Context-routed NormPeg resolver entrypoint.
    Required by CoordOS / QCGate integration.
    """
    engine = NormPegEngine.from_sources(sb=sb)
    return engine.resolve_norm_rule(spec_uri, context)

