"""Cached NormRef resolver service."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

from services.api.core.base import BaseService
from services.api.core.docpeg.normref.ports import NormRefResolverPort


class NormRefResolverService(BaseService):
    _threshold_cache: dict[tuple[str, str], dict[str, Any]] = {}
    _spec_cache: dict[str, dict[str, Any]] = {}
    _protocol_cache: dict[str, dict[str, Any]] = {}

    def __init__(self, *, sb: Any | None = None, port: NormRefResolverPort) -> None:
        super().__init__(sb=sb)
        self._port = port

    def resolve_threshold(self, *, gate_id: str, context: Any = "") -> dict[str, Any]:
        cache_key = (str(gate_id).strip(), json.dumps(context, ensure_ascii=False, sort_keys=True, default=str))
        if cache_key not in self._threshold_cache:
            self._threshold_cache[cache_key] = self._port.resolve_threshold(
                sb=self.require_supabase(),
                gate_id=cache_key[0],
                context=context,
            )
        return self._threshold_cache[cache_key]

    def get_spec_dict(self, *, spec_dict_key: str) -> dict[str, Any]:
        key = str(spec_dict_key).strip()
        if key not in self._spec_cache:
            self._spec_cache[key] = self._port.get_spec_dict(sb=self.require_supabase(), spec_dict_key=key)
        return self._spec_cache[key]

    @staticmethod
    def _to_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]

    @staticmethod
    def _norm_header(value: Any) -> str:
        text = str(value or "").strip().lower()
        return re.sub(r"[\s_\-()\[\]{}:：]+", "", text)

    @classmethod
    def _pick_row(cls, row: dict[str, Any], aliases: list[str]) -> Any:
        normalized = {cls._norm_header(k): v for k, v in row.items()}
        for alias in aliases:
            value = normalized.get(cls._norm_header(alias))
            if cls._to_text(value).strip():
                return value
        return None

    @classmethod
    def _parse_threshold(cls, raw: Any) -> dict[str, Any]:
        text = cls._to_text(raw).strip().replace(" ", "")
        if not text:
            return {"value": "", "operator": "eq", "unit": ""}

        range_match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(?:~|～|至|-)\s*([-+]?\d+(?:\.\d+)?)", text)
        if range_match:
            left = float(range_match.group(1))
            right = float(range_match.group(2))
            if left > right:
                left, right = right, left
            return {"value": [left, right], "operator": "range", "unit": ""}

        lte = re.search(r"^(?:<=|≤|不大于|小于等于)([-+]?\d+(?:\.\d+)?)", text)
        if lte:
            return {"value": float(lte.group(1)), "operator": "lte", "unit": "%" if "%" in text else ""}

        gte = re.search(r"^(?:>=|≥|不小于|大于等于)([-+]?\d+(?:\.\d+)?)", text)
        if gte:
            return {"value": float(gte.group(1)), "operator": "gte", "unit": "%" if "%" in text else ""}

        pm = re.search(r"^(?:±|\+/-)(\d+(?:\.\d+)?)", text)
        if pm:
            return {"value": float(pm.group(1)), "operator": "lte", "unit": "%" if "%" in text else "", "symmetric": True}

        numeric = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if numeric:
            return {"value": float(numeric.group(0)), "operator": "eq", "unit": "%" if "%" in text else ""}
        return {"value": text, "operator": "eq", "unit": ""}

    @staticmethod
    def _normref_docs_root() -> Path:
        return (Path(__file__).resolve().parents[4] / "docs" / "normref").resolve()

    @classmethod
    def _uri_to_docs_paths(cls, uri: str) -> tuple[Path, Path]:
        normalized = cls._to_text(uri).strip().rstrip("/")
        root = cls._normref_docs_root()
        if not normalized.startswith("v://normref.com"):
            token = re.sub(r"[^0-9a-zA-Z._@/-]+", "-", normalized).strip("-") or "protocol"
            md_path = root / "misc" / f"{token}.md"
            return md_path, md_path.with_suffix(".json")
        rel = normalized[len("v://normref.com") :].lstrip("/")
        rel = rel or "index"
        md_path = root / f"{rel}.md"
        return md_path, md_path.with_suffix(".json")

    @classmethod
    def _to_float(cls, value: Any) -> float | None:
        text = cls._to_text(value).strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
            if not match:
                return None
            try:
                return float(match.group(0))
            except Exception:
                return None

    @classmethod
    def _pick_measurement(cls, data: dict[str, Any], check_id: str, label: str) -> Any:
        if check_id in data:
            return data.get(check_id)
        lowered = {cls._to_text(k).strip().lower(): v for k, v in data.items()}
        cid = check_id.strip().lower()
        if cid and cid in lowered:
            return lowered.get(cid)
        lname = label.strip().lower()
        if lname and lname in lowered:
            return lowered.get(lname)
        return None

    @classmethod
    def _evaluate_gate(
        cls,
        *,
        gate: dict[str, Any],
        actual_data: dict[str, Any],
        design_data: dict[str, Any],
    ) -> dict[str, Any]:
        check_id = cls._to_text(gate.get("check_id")).strip() or "gate"
        label = cls._to_text(gate.get("label")).strip() or check_id
        severity = cls._to_text(gate.get("severity") or "mandatory").strip().lower() or "mandatory"
        threshold = cls._as_dict(gate.get("threshold"))
        operator = cls._to_text(threshold.get("operator") or "eq").strip().lower() or "eq"
        threshold_value = threshold.get("value")
        unit = cls._to_text(threshold.get("unit")).strip()
        symmetric = bool(threshold.get("symmetric"))

        actual_value = cls._pick_measurement(actual_data, check_id, label)
        design_value = cls._pick_measurement(design_data, check_id, label)
        if actual_value is None:
            return {
                "check_id": check_id,
                "label": label,
                "severity": severity,
                "operator": operator,
                "threshold": threshold_value,
                "unit": unit,
                "actual_value": None,
                "design_value": design_value,
                "pass": False,
                "reason": "missing_actual_value",
            }

        actual_num = cls._to_float(actual_value)
        design_num = cls._to_float(design_value)
        pass_flag = False
        reason = ""

        if operator == "range":
            vals = threshold_value if isinstance(threshold_value, list) else []
            left = cls._to_float(vals[0]) if len(vals) >= 1 else None
            right = cls._to_float(vals[1]) if len(vals) >= 2 else None
            if actual_num is not None and left is not None and right is not None:
                pass_flag = left <= actual_num <= right
                reason = f"{left} <= {actual_num} <= {right}"
            else:
                reason = "range_operator_requires_numeric_actual_and_threshold"
        elif operator == "lte":
            limit = cls._to_float(threshold_value)
            if limit is None:
                reason = "lte_operator_requires_numeric_threshold"
            elif actual_num is None:
                reason = "lte_operator_requires_numeric_actual"
            else:
                if unit == "%" and limit > 1:
                    limit = limit / 100.0
                if (symmetric or unit == "%") and design_num is not None:
                    if design_num == 0:
                        delta = abs(actual_num - design_num)
                        pass_flag = delta <= limit
                        reason = f"abs(actual-design)={delta} <= {limit}"
                    else:
                        ratio = abs(actual_num - design_num) / abs(design_num)
                        pass_flag = ratio <= limit
                        reason = f"abs(actual-design)/design={ratio} <= {limit}"
                else:
                    pass_flag = actual_num <= limit
                    reason = f"{actual_num} <= {limit}"
        elif operator == "gte":
            limit = cls._to_float(threshold_value)
            if limit is None:
                reason = "gte_operator_requires_numeric_threshold"
            elif actual_num is None:
                reason = "gte_operator_requires_numeric_actual"
            else:
                pass_flag = actual_num >= limit
                reason = f"{actual_num} >= {limit}"
        else:
            limit_num = cls._to_float(threshold_value)
            if actual_num is not None and limit_num is not None:
                pass_flag = abs(actual_num - limit_num) <= 1e-9
                reason = f"{actual_num} == {limit_num}"
            else:
                pass_flag = cls._to_text(actual_value).strip() == cls._to_text(threshold_value).strip()
                reason = f"{actual_value} == {threshold_value}"

        return {
            "check_id": check_id,
            "label": label,
            "severity": severity,
            "operator": operator,
            "threshold": threshold_value,
            "unit": unit,
            "actual_value": actual_value,
            "design_value": design_value,
            "pass": bool(pass_flag),
            "reason": reason,
            "norm_ref": cls._to_text(gate.get("norm_ref")).strip(),
        }

    def resolve_protocol(self, *, uri: str) -> dict[str, Any]:
        normalized_uri = self._to_text(uri).strip()
        if not normalized_uri:
            return {"ok": False, "error": "uri_required"}
        cached = self._protocol_cache.get(normalized_uri)
        if cached is not None:
            return dict(cached)

        payload: dict[str, Any] = {}
        source = ""
        try:
            sb = self.require_supabase()
            rows = (
                sb.table("specir_objects")
                .select("uri,kind,version,title,content,content_hash,status,updated_at,created_at")
                .eq("uri", normalized_uri)
                .limit(1)
                .execute()
                .data
                or []
            )
            if rows:
                row = self._as_dict(rows[0])
                content = self._as_dict(row.get("content"))
                payload = dict(content) if content else {}
                if not self._to_text(payload.get("uri")).strip():
                    payload["uri"] = normalized_uri
                source = "specir_registry"
        except Exception:
            payload = {}

        if not payload:
            _md_path, json_path = self._uri_to_docs_paths(normalized_uri)
            if json_path.exists():
                try:
                    payload = self._as_dict(json.loads(json_path.read_text(encoding="utf-8")))
                    if not self._to_text(payload.get("uri")).strip():
                        payload["uri"] = normalized_uri
                    source = "docs_json"
                except Exception:
                    payload = {}

        if not payload:
            return {"ok": False, "error": "protocol_not_found", "uri": normalized_uri}

        out = {
            "ok": True,
            "uri": normalized_uri,
            "source": source or "unknown",
            "protocol": payload,
            "schema_uri": self._to_text(payload.get("schema_uri") or "").strip(),
            "version": self._to_text(payload.get("version") or "").strip(),
        }
        self._protocol_cache[normalized_uri] = dict(out)
        return out

    @classmethod
    def verify_against_protocol(
        cls,
        *,
        protocol: dict[str, Any],
        uri: str = "",
        actual_data: dict[str, Any] | None = None,
        design_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        gates = [g for g in cls._as_list(protocol.get("gates")) if isinstance(g, dict)]
        if not gates:
            return {"ok": False, "error": "protocol_has_no_gates"}

        actual = cls._as_dict(actual_data)
        design = cls._as_dict(design_data)
        checks = [cls._evaluate_gate(gate=gate, actual_data=actual, design_data=design) for gate in gates]

        failed_mandatory = [
            c for c in checks if (not bool(c.get("pass"))) and cls._to_text(c.get("severity")).lower() == "mandatory"
        ]
        failed_warning = [
            c for c in checks if (not bool(c.get("pass"))) and cls._to_text(c.get("severity")).lower() != "mandatory"
        ]

        result = "PASS"
        if failed_mandatory:
            result = "FAIL"
        elif failed_warning:
            result = "WARNING"

        explain = "all gates passed"
        if result == "FAIL":
            explain = f"{len(failed_mandatory)} mandatory gate(s) failed"
        elif result == "WARNING":
            explain = f"{len(failed_warning)} warning gate(s) failed"

        sealed_at = datetime.now(UTC).isoformat()
        proof_payload = {
            "uri": cls._to_text(uri or protocol.get("uri")).strip(),
            "actual_data": actual,
            "design_data": design,
            "context": cls._as_dict(context),
            "checks": checks,
            "result": result,
        }
        proof_hash = hashlib.sha256(
            json.dumps(proof_payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

        return {
            "ok": True,
            "uri": cls._to_text(uri or protocol.get("uri")).strip(),
            "result": result,
            "failed_gates": [cls._to_text(item.get("check_id")).strip() for item in (failed_mandatory + failed_warning)],
            "failed_mandatory": failed_mandatory,
            "failed_warning": failed_warning,
            "checks": checks,
            "proof_hash": proof_hash,
            "sealed_at": sealed_at,
            "explain": explain,
        }

    def verify_protocol(
        self,
        *,
        uri: str,
        actual_data: dict[str, Any] | None = None,
        design_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved = self.resolve_protocol(uri=uri)
        if not bool(resolved.get("ok")):
            return resolved
        protocol = self._as_dict(resolved.get("protocol"))
        out = self.verify_against_protocol(
            protocol=protocol,
            uri=self._to_text(resolved.get("uri")).strip(),
            actual_data=actual_data,
            design_data=design_data,
            context=context,
        )
        if bool(out.get("ok")):
            out["schema_uri"] = self._to_text(protocol.get("schema_uri") or resolved.get("schema_uri")).strip()
            out["protocol_version"] = self._to_text(protocol.get("version") or resolved.get("version")).strip()
        return out
    @classmethod
    def _derive_logic_inputs(cls, gates: list[dict[str, Any]], description: str = "") -> list[dict[str, str]]:
        text = " ".join(
            [
                f"{cls._to_text(g.get('label')).lower()} {cls._to_text(g.get('check_id')).lower()}"
                for g in gates
                if isinstance(g, dict)
            ]
        )
        text = f"{text} {cls._to_text(description).lower()}"
        out: list[dict[str, str]] = []

        def _append(name: str, hint: str, unit: str = "") -> None:
            if any(cls._to_text(item.get("name")).strip() == name for item in out):
                return
            out.append({"name": name, "hint": hint, "unit": unit})

        if "diameter" in text or "直径" in text:
            _append("design_diameter", "Design diameter from drawing", "mm")
            _append("measured_diameter", "Measured diameter from field", "mm")
        if "spacing" in text or "间距" in text:
            _append("measured_spacing", "Measured spacing from field", "mm")
        if "保护层" in text or "protection" in text:
            _append("measured_protection_layer", "Measured protection layer thickness", "mm")
        if "weld" in text or "焊" in text:
            _append("weld_quality_level", "Weld quality level (I/II/III)")
        if "raft" in text or "筏" in text:
            _append("design_thickness", "Design raft thickness from drawing", "mm")
            _append("measured_thickness", "Measured raft thickness from field", "mm")
            _append("measured_concrete_strength", "Measured concrete strength", "MPa")
            _append("measured_rebar_spacing", "Measured rebar spacing", "mm")
        if not out:
            _append("measured_value", "Measured value from field")
        return out

    @classmethod
    def _validate_five_layers(cls, layers: dict[str, Any]) -> list[str]:
        required_map: dict[str, list[str]] = {
            "header": ["doc_type", "doc_id", "v_uri", "project_ref", "version", "created_at", "jurisdiction"],
            "gate": ["pre_conditions", "entry_rules", "required_trip_roles"],
            "body": ["basic", "test_data", "relations"],
            "proof": ["data_hash", "proof_hash", "signatures", "witness_logs", "timestamps"],
            "state": ["lifecycle_stage", "state_matrix", "next_action", "valid_until"],
        }
        issues: list[str] = []
        for layer, fields in required_map.items():
            node = cls._as_dict(layers.get(layer))
            if not node:
                issues.append(f"missing_layer:{layer}")
                continue
            for field in fields:
                if field not in node:
                    issues.append(f"missing_field:{layer}.{field}")
        return issues

    @classmethod
    def generate_protocol(
        cls,
        *,
        table_content: str,
        protocol_uri: str = "",
        norm_code: str = "",
        boq_item_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """DocPeg Core API: generate protocol block from CSV text table content."""
        text = cls._to_text(table_content).strip()
        if not text:
            raise ValueError("table_content is required")

        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(r) for r in reader if isinstance(r, dict)]
        if not rows:
            raise ValueError("table_content does not contain parseable rows")

        gates: list[dict[str, Any]] = []
        for row in rows:
            label = cls._to_text(
                cls._pick_row(row, ["check_item", "检查项", "检查项目", "label", "name", "项目"])
            ).strip()
            threshold_raw = cls._pick_row(row, ["threshold", "允许偏差", "limit", "阈值", "标准值"])
            if not label and not cls._to_text(threshold_raw).strip():
                continue

            gates.append(
                {
                    "check_id": cls._to_text(cls._pick_row(row, ["check_id", "检查项编码", "id"])).strip()
                    or re.sub(r"[^0-9a-zA-Z_\-]", "-", label.lower()).strip("-")
                    or f"gate-{len(gates) + 1}",
                    "label": label or f"gate-{len(gates) + 1}",
                    "norm_ref": cls._to_text(
                        cls._pick_row(row, ["norm_ref", "规范", "规范条文", "标准引用", "norm"])
                    ).strip(),
                    "threshold": cls._parse_threshold(threshold_raw),
                    "severity": cls._to_text(
                        cls._pick_row(row, ["severity", "严重级别", "级别", "严重性"]) or "mandatory"
                    ).strip()
                    or "mandatory",
                }
            )

        if not gates:
            raise ValueError("no gates extracted from table_content")

        raft_hint = ("raft" in text.lower()) or ("筏" in text)
        uri = protocol_uri.strip() or (
            "v://normref.com/qc/raft-foundation@v1" if raft_hint else "v://normref.com/qc/generated@v1"
        )
        meta_norm = norm_code.strip() or cls._to_text(cls._pick_row(rows[0], ["norm_code", "规范号", "norm"])).strip()
        meta_boq = boq_item_id.strip() or cls._to_text(cls._pick_row(rows[0], ["boq_item_id", "清单编码", "code"])).strip()
        meta_desc = description.strip() or cls._to_text(cls._pick_row(rows[0], ["description", "描述", "name"])).strip()

        created_at = datetime.now(UTC).isoformat()
        data_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        doc_id = f"NINST-{data_hash[:8].upper()}"
        total_tables = len(gates)
        state_matrix = {
            "component_count": 0,
            "forms_per_component": 1,
            "expected_qc_table_count": total_tables,
            "generated_qc_table_count": 0,
            "signed_pass_table_count": 0,
            "pending_qc_table_count": total_tables,
            "total_qc_tables": total_tables,
            "total": total_tables,
            "generated": 0,
            "signed": 0,
            "pending": total_tables,
        }

        protocol = {
            "uri": uri,
            "schema_uri": "v://normref.com/schema/qc-v1",
            "version": "v1",
            "metadata": {
                "norm_code": meta_norm,
                "boq_item_id": meta_boq,
                "description": meta_desc,
                "domain": "construction/highway",
                "doc_id": doc_id,
            },
            "gates": gates,
            "logic_inputs": cls._derive_logic_inputs(gates, meta_desc),
            "state_matrix": state_matrix,
            "layers": {
                "header": {
                    "doc_type": "v://normref.com/doc-type/quality-inspection@v1",
                    "doc_id": doc_id,
                    "v_uri": uri,
                    "project_ref": "",
                    "version": "v1",
                    "created_at": created_at,
                    "jurisdiction": meta_norm,
                },
                "gate": {
                    "pre_conditions": [],
                    "entry_rules": [
                        {
                            "check_id": cls._to_text(gate.get("check_id")).strip(),
                            "label": cls._to_text(gate.get("label")).strip(),
                            "threshold": cls._as_dict(gate.get("threshold")),
                            "severity": cls._to_text(gate.get("severity")).strip() or "mandatory",
                        }
                        for gate in gates
                    ],
                    "required_trip_roles": ["quality.check", "supervisor.approve"],
                },
                "body": {
                    "basic": {
                        "boq_item_id": meta_boq,
                        "description": meta_desc,
                    },
                    "test_data": [],
                    "relations": [],
                },
                "proof": {
                    "data_hash": f"sha256:{data_hash}",
                    "proof_hash": "",
                    "signatures": [],
                    "witness_logs": [],
                    "timestamps": {"generated_at": created_at, "sealed_at": ""},
                },
                "state": {
                    "lifecycle_stage": "draft",
                    "state_matrix": state_matrix,
                    "next_action": "等待质量检查执行",
                    "valid_until": "",
                },
            },
            "verdict_logic": "For each gate: evaluate actual vs threshold; all mandatory PASS => PASS.",
            "output_schema": {
                "result": "PASS|FAIL|WARNING",
                "failed_gates": [],
                "explain": "",
                "proof_hash": "",
                "sealed_at": "",
            },
        }
        issues = cls._validate_five_layers(cls._as_dict(protocol.get("layers")))
        if issues:
            raise ValueError(f"generated protocol violates five-layer schema: {', '.join(issues)}")
        return protocol

    @classmethod
    def generateProtocol(cls, tableContent: str, **kwargs: Any) -> dict[str, Any]:  # noqa: N802 - keep API name
        """CamelCase alias for external integrations."""
        return cls.generate_protocol(table_content=tableContent, **kwargs)

