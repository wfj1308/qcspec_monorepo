"""
QCSpec DOCX engine for sovereign report rendering.
"""

from __future__ import annotations

import base64
import json
import io
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import qrcode
from docx import Document
from docx.shared import Mm, RGBColor
from docxtpl import DocxTemplate, InlineImage, Listing
from specir_engine import derive_spec_uri as specir_derive_spec_uri
from specir_engine import evaluate_measurements as specir_evaluate_measurements
from specir_engine import resolve_spec_rule as specir_resolve_spec_rule
from specir_engine import threshold_text as specir_threshold_text

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_BY_TYPE = {
    "inspection": "01_inspection_report.docx",
    "lab": "02_lab_report.docx",
    "monthly_summary": "03_monthly_summary.docx",
    "final_archive": "04_final_archive_cover.docx",
}

PASS_CN = "\u5408\u683c"
FAIL_CN = "\u4e0d\u5408\u683c"
OBSERVE_CN = "\u89c2\u5bdf"
PENDING_CN = "\u5f85\u5b9a"
CANCELLED_CN = "\u53d6\u6d88"
PENDING_ANCHOR_CN = "\u5f85\u951a\u5b9a"
REBAR_SPACING_CN = "\u94a2\u7b4b\u95f4\u8ddd"
REBAR_FRAME_CN = "\u94a2\u7b4b\u9aa8\u67b6\u5c3a\u5bf8"
COVER_THICKNESS_CN = "\u4fdd\u62a4\u5c42\u539a\u5ea6"
ROAD_FLATNESS_CN = "\u8def\u9762\u5e73\u6574\u5ea6"
SEPARATOR_CN = "\u3001"

SCHEMA_MODE_DESIGN_LIMIT = "design_limit"
SCHEMA_MODE_VALUE_STANDARD_MAX = "value_standard_max"
SCHEMA_MODE_VALUE_STANDARD_MIN = "value_standard_min"
SCHEMA_MODE_VALUE_STANDARD_EQ = "value_standard_eq"
STANDARD_OP_PLUS_MINUS = "±"
FAIL_RGB = RGBColor(0xDC, 0x26, 0x26)


class DocxEngine:
    def _load(self, name: str) -> DocxTemplate:
        return DocxTemplate(str(TEMPLATE_DIR / name))

    def _qr(self, tpl: DocxTemplate, uri: str, size_mm: int = 22) -> InlineImage:
        """Generate QR code inline image for docxtpl."""
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return InlineImage(tpl, buf, width=Mm(size_mm))

    def _fmt_result(self, result: str) -> str:
        return {
            "PASS": PASS_CN,
            "FAIL": FAIL_CN,
            "OBSERVE": OBSERVE_CN,
            "PENDING": PENDING_CN,
        }.get(result, result)

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    def _now_seconds(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _verify_base_url(self) -> str:
        base = self._to_text(os.getenv("QCSPEC_VERIFY_BASE_URL") or "https://verify.qcspec.com").strip()
        return base.rstrip("/")

    @staticmethod
    def _to_text(value: Any, default: str = "") -> str:
        """
        Force every incoming value to UTF-8 safe text.
        - bytes: decode as utf-8 with replacement
        - str: round-trip through utf-8 to strip invalid surrogate payloads
        """
        if value is None:
            return default
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, str):
            return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        return str(value)

    def _normalize_payload(self, value: Any) -> Any:
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                out[self._to_text(k)] = self._normalize_payload(v)
            return out
        if isinstance(value, list):
            return [self._normalize_payload(x) for x in value]
        if isinstance(value, tuple):
            return tuple(self._normalize_payload(x) for x in value)
        if isinstance(value, (str, bytes)):
            return self._to_text(value)
        return value

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            text = str(value).strip()
            if not text:
                return None
            m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
            if not m:
                return None
            try:
                return float(m.group(0))
            except Exception:
                return None

    @staticmethod
    def _parse_limit(limit: Any) -> float | None:
        text = str(limit or "").strip()
        if not text:
            return None
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return abs(float(match.group(0)))
        except Exception:
            return None

    @staticmethod
    def _coerce_values(values_raw: Any, fallback_value: Any = None) -> list[float]:
        def _num(raw: Any) -> float | None:
            try:
                return float(raw)
            except Exception:
                text = str(raw or "").strip()
                if not text:
                    return None
                m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
                if not m:
                    return None
                try:
                    return float(m.group(0))
                except Exception:
                    return None

        values: list[float] = []
        if isinstance(values_raw, list):
            for item in values_raw:
                parsed = _num(item)
                if parsed is not None:
                    values.append(parsed)
        fallback_num: float | None = None
        if fallback_value is not None:
            fallback_num = _num(fallback_value)

        if values and fallback_num is not None:
            # Heal legacy payloads where `values` was defaulted to [0] while real
            # single-point value is stored in `value`.
            if len(values) == 1 and abs(values[0]) < 1e-9 and abs(fallback_num) >= 1e-9:
                return [fallback_num]
            return values

        if not values and fallback_num is not None:
            return [fallback_num]
        return values

    def _safe_label(self, label: Any, *, fallback: str) -> str:
        text = self._to_text(label).strip()
        return text or fallback

    def _safe_limit(self, limit_raw: Any) -> str:
        text = self._to_text(limit_raw).strip()
        if not text:
            return "-"
        if text.startswith("?") and len(text) > 1:
            return f"\u00b1{text[1:]}"
        return text

    def _extract_unit(self, state_data: dict[str, Any]) -> str:
        for key in ("unit", "value_unit", "standard_unit"):
            text = self._to_text(state_data.get(key)).strip()
            if text:
                return text

        for key in ("standard", "value"):
            raw = self._to_text(state_data.get(key)).strip()
            if not raw:
                continue
            m = re.match(r"^\s*[-+]?\d+(?:\.\d+)?\s*([^\d\s].*)$", raw)
            if m:
                unit = m.group(1).strip()
                if unit:
                    return unit
        return ""

    def _with_unit(self, value_text: str, unit: str, *, force_inline: bool = False) -> str:
        base = self._to_text(value_text).strip()
        u = self._to_text(unit).strip()
        if not base or base == "-" or not u:
            return base or "-"
        if not force_inline and u.lower() == "mm":
            return base
        return f"{base} {u}"

    @staticmethod
    def _format_num(value: float) -> str:
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"

    def _format_values_multiline(self, values: list[float], chunk: int = 10, unit: str = "", force_inline_unit: bool = False) -> str | Listing:
        if not values:
            return "-"
        pieces = [self._with_unit(self._format_num(v), unit, force_inline=force_inline_unit) for v in values]
        if len(pieces) <= chunk:
            return SEPARATOR_CN.join(pieces)
        lines = []
        for idx in range(0, len(pieces), chunk):
            lines.append(SEPARATOR_CN.join(pieces[idx : idx + chunk]))
        return Listing("\n".join(lines))

    def _resolve_test_type(self, state_data: dict[str, Any], *, fallback_type: str) -> tuple[str, str]:
        raw_type = self._to_text(state_data.get("test_type") or state_data.get("type") or "").strip()
        raw_name = self._to_text(
            state_data.get("test_name")
            or state_data.get("type_name")
            or state_data.get("inspection_item")
            or ""
        ).strip()

        if not raw_name and raw_type:
            raw_name = raw_type
        if not raw_type:
            raw_type = raw_name or fallback_type

        probe = {"type": raw_type, "type_name": raw_name or raw_type}
        if not raw_name:
            if self._is_flatness_like(probe):
                raw_name = ROAD_FLATNESS_CN
            elif raw_type == "rebar_spacing":
                raw_name = REBAR_SPACING_CN
            else:
                raw_name = raw_type

        return raw_type, raw_name

    def _extract_executor_name(self, signing: dict[str, Any], *, fallback_uri: str) -> str:
        name = self._to_text(
            signing.get("executor_name")
            or signing.get("name")
            or signing.get("signer_name")
            or signing.get("display_name")
            or ""
        ).strip()
        if name:
            return name
        uri = self._to_text(fallback_uri).strip().rstrip("/")
        if not uri:
            return "-"
        tail = uri.split("/")[-1].strip()
        return tail or "-"

    def _extract_executor_id(self, signing: dict[str, Any], *, fallback_uri: str, fallback_name: str) -> str:
        for key in ("executor_id", "executor_uid", "uid", "id"):
            val = self._to_text(signing.get(key)).strip()
            if val:
                return val
        uri = self._to_text(fallback_uri).strip().rstrip("/")
        if uri:
            return uri.split("/")[-1].strip() or self._to_text(fallback_name).strip() or "unknown"
        return self._to_text(fallback_name).strip() or "unknown"

    @staticmethod
    def _bool_env(name: str, default: bool = False) -> bool:
        raw = str(os.getenv(name) or "").strip().lower()
        if not raw:
            return default
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def _is_uri_like(value: str) -> bool:
        text = str(value or "").strip().lower()
        return text.startswith("http://") or text.startswith("https://")

    def _resolve_signature_url(self, executor_id: str) -> str:
        eid = self._to_text(executor_id).strip()
        if not eid:
            return ""

        raw_map = self._to_text(os.getenv("QCSPEC_SIGNATURE_URL_MAP") or "").strip()
        if raw_map:
            try:
                parsed = json.loads(raw_map)
                if isinstance(parsed, dict):
                    mapped = self._to_text(parsed.get(eid) or parsed.get(eid.lower()) or "").strip()
                    if mapped and self._is_uri_like(mapped):
                        return mapped
            except Exception:
                pass

        tpl = self._to_text(os.getenv("QCSPEC_SIGNATURE_URL_TEMPLATE") or "").strip()
        if tpl:
            try:
                url = tpl.format(executor_id=eid)
                if self._is_uri_like(url):
                    return url
            except Exception:
                pass

        base = self._to_text(os.getenv("QCSPEC_SIGNATURE_BASE_URL") or "").strip().rstrip("/")
        if base and self._is_uri_like(base):
            return f"{base}/{eid}.png"
        return ""

    def _decrypt_signature_blob(self, blob: bytes) -> bytes:
        """
        Optional lightweight decrypt step for encrypted signature payloads.
        Uses XOR with QCSPEC_SIGNATURE_XOR_KEY when configured.
        """
        key = self._to_text(os.getenv("QCSPEC_SIGNATURE_XOR_KEY") or "").encode("utf-8")
        if not key:
            return blob
        out = bytearray(len(blob))
        for idx, b in enumerate(blob):
            out[idx] = b ^ key[idx % len(key)]
        return bytes(out)

    def _fallback_signature_stamp(self, tpl: DocxTemplate, size_mm: int = 18) -> InlineImage | str:
        """
        Render a gray fallback stamp when no signature image is available.
        """
        try:
            from PIL import Image, ImageDraw
        except Exception:
            return "-"

        px = 180
        img = Image.new("RGBA", (px, px), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        border = (148, 163, 184, 255)
        fill = (241, 245, 249, 230)
        draw.rounded_rectangle([(2, 2), (px - 3, px - 3)], radius=14, fill=fill, outline=border, width=3)
        draw.ellipse([(26, 26), (px - 27, px - 27)], outline=border, width=3)
        text_color = (100, 116, 139, 255)
        draw.text((46, 74), "NO SIGN", fill=text_color)
        draw.text((40, 102), "UNAVAILABLE", fill=text_color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return InlineImage(tpl, buf, width=Mm(size_mm))

    def _fetch_signature_bytes(self, url: str) -> bytes | None:
        if not self._is_uri_like(url):
            return None
        headers: dict[str, str] = {}
        token = self._to_text(os.getenv("QCSPEC_SIGNATURE_AUTH_TOKEN") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            with httpx.Client(timeout=6.0, follow_redirects=True) as client:
                res = client.get(url, headers=headers)
                if res.status_code >= 400:
                    return None
                content_type = self._to_text(res.headers.get("content-type") or "").lower()
                if content_type.startswith("image/"):
                    return res.content
                # JSON envelope mode:
                # {"signature_b64":"..."} or {"encrypted_b64":"..."} or {"url":"https://..."}
                payload = res.json()
                if isinstance(payload, dict):
                    nested_url = self._to_text(payload.get("url") or payload.get("image_url") or "").strip()
                    if nested_url and nested_url != url:
                        return self._fetch_signature_bytes(nested_url)
                    b64 = self._to_text(
                        payload.get("signature_b64")
                        or payload.get("image_b64")
                        or payload.get("encrypted_b64")
                        or ""
                    ).strip()
                    if b64:
                        raw = base64.b64decode(b64)
                        return self._decrypt_signature_blob(raw)
        except Exception:
            return None
        return None

    def _insert_signature(
        self,
        executor_id: str,
        tpl: DocxTemplate | None = None,
        size_mm: int = 18,
    ) -> tuple[InlineImage | bytes | str, str]:
        """
        Mount e-signature image for the executor.
        Template placeholder suggestion: {{ signature_image }}
        """
        eid = self._to_text(executor_id).strip()
        if not eid:
            return "-", "none"
        url = self._resolve_signature_url(eid)
        if not url:
            if tpl is not None and self._bool_env("QCSPEC_SIGNATURE_FALLBACK_STAMP", default=True):
                fallback = self._fallback_signature_stamp(tpl, size_mm=size_mm)
                if fallback != "-":
                    return fallback, "fallback"
            return "-", "none"
        blob = self._fetch_signature_bytes(url)
        if not blob:
            if tpl is not None and self._bool_env("QCSPEC_SIGNATURE_FALLBACK_STAMP", default=True):
                fallback = self._fallback_signature_stamp(tpl, size_mm=size_mm)
                if fallback != "-":
                    return fallback, "fallback"
            return "-", "none"
        if tpl is None:
            return blob, "loaded"
        buf = io.BytesIO(blob)
        buf.seek(0)
        return InlineImage(tpl, buf, width=Mm(size_mm)), "loaded"

    def _build_v_uri_tree(
        self,
        *,
        project_uri: str,
        segment_uri: str,
        v_uri: str,
        proof_id: str,
        stake: str,
        verify_uri: str,
    ) -> dict[str, Any]:
        return {
            "project_uri": self._to_text(project_uri),
            "segment_uri": self._to_text(segment_uri),
            "v_uri": self._to_text(v_uri),
            "proof_id": self._to_text(proof_id),
            "stake": self._to_text(stake),
            "verify_uri": self._to_text(verify_uri),
            "nodes": [
                {"name": "project", "uri": self._to_text(project_uri)},
                {"name": "segment", "uri": self._to_text(segment_uri), "stake": self._to_text(stake)},
                {"name": "utxo", "uri": self._to_text(v_uri), "proof_id": self._to_text(proof_id)},
            ],
        }

    def _resolve_schema_mode(self, state_data: dict[str, Any], *, test_type: str, test_type_name: str) -> str:
        explicit = self._to_text(state_data.get("schema_mode") or state_data.get("mode")).strip().lower()
        if explicit in {
            SCHEMA_MODE_DESIGN_LIMIT,
            SCHEMA_MODE_VALUE_STANDARD_MAX,
            SCHEMA_MODE_VALUE_STANDARD_MIN,
            SCHEMA_MODE_VALUE_STANDARD_EQ,
        }:
            return explicit

        token = f"{test_type} {test_type_name}".strip().lower()
        if any(k in token for k in ("spacing", "cover", "frame", "\u95f4\u8ddd", "\u4fdd\u62a4\u5c42", "\u9aa8\u67b6")):
            return SCHEMA_MODE_DESIGN_LIMIT
        if any(k in token for k in ("flatness", "iri", "crack", "rut", "\u5e73\u6574\u5ea6", "\u88c2\u7f1d", "\u8f66\u8f99")):
            return SCHEMA_MODE_VALUE_STANDARD_MAX
        if any(k in token for k in ("compaction", "density", "\u538b\u5b9e\u5ea6", "\u538b\u5b9e")):
            return SCHEMA_MODE_VALUE_STANDARD_MIN
        return SCHEMA_MODE_VALUE_STANDARD_MAX

    @staticmethod
    def _mode_default_operator(mode: str) -> str:
        if mode == SCHEMA_MODE_VALUE_STANDARD_MIN:
            return ">="
        if mode == SCHEMA_MODE_VALUE_STANDARD_EQ:
            return "="
        return "<="

    def _format_display_time(self, value: Any) -> str:
        """
        Normalize timestamp for docx display:
        - trim microseconds
        - trim timezone offset display
        - output as YYYY-MM-DD HH:mm:ss
        """
        text = self._to_text(value).strip()
        if not text:
            return ""

        normalized = text
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"

        try:
            dt = datetime.fromisoformat(normalized)
            return dt.replace(tzinfo=None, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        cleaned = text.replace("T", " ").strip()
        cleaned = re.sub(r"\.\d+", "", cleaned)
        cleaned = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", cleaned).strip()
        sec_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", cleaned)
        if sec_match:
            return sec_match.group(1).replace("  ", " ")
        min_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$", cleaned)
        if min_match:
            return f"{min_match.group(1).replace('  ', ' ')}:00"
        return cleaned

    def _format_signed_at(self, value: Any) -> str:
        return self._format_display_time(value)

    @staticmethod
    def _is_flatness_like(state_data: dict[str, Any]) -> bool:
        type_token = str(state_data.get("type") or "").strip().lower()
        type_name = str(state_data.get("type_name") or "").strip().lower()
        token = f"{type_token} {type_name}"
        return any(k in token for k in ("flatness", "iri", "\u5e73\u6574\u5ea6", "\u8def\u9762"))

    @staticmethod
    def _is_compaction_like(state_data: dict[str, Any]) -> bool:
        type_token = str(state_data.get("type") or state_data.get("test_type") or "").strip().lower()
        type_name = str(state_data.get("type_name") or state_data.get("test_name") or "").strip().lower()
        token = f"{type_token} {type_name}"
        return any(k in token for k in ("compaction", "density", "\u538b\u5b9e\u5ea6", "\u538b\u5b9e"))

    def _normalize_standard_op(self, raw_op: Any) -> str:
        text = self._to_text(raw_op).strip().lower()
        if not text:
            return ""
        if text in {"+-", "+/-", "\u00b1", "±", "plusminus", "plus_minus"}:
            return STANDARD_OP_PLUS_MINUS
        if text in {"<=", "≤", "le", "lte", "max", "upper"}:
            return "<="
        if text in {">=", "≥", "ge", "gte", "min", "lower"}:
            return ">="
        if text in {"=", "==", "eq"}:
            return "="
        if text in {"<", ">"}:
            return text
        return ""

    def _extract_standard_from_text(self, raw: Any) -> tuple[float | None, float | None]:
        """
        Parse strings like:
        - "200±10"
        - "200+/-10"
        Returns (standard_value, tolerance_value).
        """
        text = self._to_text(raw).strip()
        if not text:
            return None, None
        m = re.search(r"([-+]?\d+(?:\.\d+)?)\s*(?:\u00b1|±|\+/-)\s*([-+]?\d+(?:\.\d+)?)", text)
        if not m:
            return None, None
        try:
            base = float(m.group(1))
            tol = abs(float(m.group(2)))
            return base, tol
        except Exception:
            return None, None

    def _resolve_standard_rule(
        self,
        *,
        state_data: dict[str, Any],
        test_type: str,
        test_type_name: str,
        schema_mode: str,
        design: float | None,
        standard: float | None,
    ) -> tuple[str, float | None, float | None]:
        """
        Resolve compliance rule from schema fields:
        - standard_op: <=, >=, =, ±
        - standard_value: numeric target
        - standard_tolerance: only for ± mode
        """
        raw_op = (
            state_data.get("standard_op")
            or state_data.get("standard_operator")
            or state_data.get("operator")
            or state_data.get("comparator")
            or state_data.get("compare")
            or ""
        )
        op = self._normalize_standard_op(raw_op)

        standard_raw = (
            state_data.get("standard_value")
            if state_data.get("standard_value") is not None
            else (
                state_data.get("standard")
                if state_data.get("standard") is not None
                else state_data.get("design")
            )
        )
        standard_value = self._to_float(standard_raw)
        parsed_base, parsed_tol = self._extract_standard_from_text(standard_raw)
        if standard_value is None and parsed_base is not None:
            standard_value = parsed_base
        if standard_value is None:
            standard_value = standard if standard is not None else design

        tol_raw = (
            state_data.get("standard_tolerance")
            if state_data.get("standard_tolerance") is not None
            else (
                state_data.get("tolerance")
                if state_data.get("tolerance") is not None
                else state_data.get("limit")
            )
        )
        tolerance = self._parse_limit(tol_raw)
        if tolerance is None and parsed_tol is not None:
            tolerance = parsed_tol

        if not op:
            # Infer default operator by schema / test semantics.
            probe = {"type": test_type, "type_name": test_type_name}
            if tolerance is not None and (standard_value is not None or design is not None):
                op = STANDARD_OP_PLUS_MINUS
            elif self._is_compaction_like(probe) or schema_mode == SCHEMA_MODE_VALUE_STANDARD_MIN:
                op = ">="
            elif schema_mode == SCHEMA_MODE_VALUE_STANDARD_EQ:
                op = "="
            else:
                op = "<="

        return op, standard_value, tolerance

    def _auto_result_from_state_data(
        self,
        *,
        state_data: dict[str, Any],
        values: list[float],
        standard_op: str,
        standard_value: float | None,
        tolerance: float | None,
        fallback: str,
    ) -> str:
        if standard_op == STANDARD_OP_PLUS_MINUS and standard_value is not None and tolerance is not None and values:
            lower = standard_value - tolerance
            upper = standard_value + tolerance
            return "FAIL" if any((v < lower or v > upper) for v in values) else "PASS"

        standard = standard_value if standard_value is not None else self._to_float(state_data.get("standard"))
        if standard is None or not values:
            return fallback

        op = self._normalize_standard_op(standard_op) or "<="
        if op == "<=":
            return "PASS" if all(v <= standard for v in values) else "FAIL"
        if op == ">=":
            return "PASS" if all(v >= standard for v in values) else "FAIL"
        if op == "=":
            return "PASS" if all(abs(v - standard) < 1e-9 for v in values) else "FAIL"
        if op == "<":
            return "PASS" if all(v < standard for v in values) else "FAIL"
        if op == ">":
            return "PASS" if all(v > standard for v in values) else "FAIL"
        return fallback

    @staticmethod
    def _first_signing(proof: dict[str, Any]) -> dict[str, Any]:
        signed = proof.get("signed_by")
        if isinstance(signed, list) and signed and isinstance(signed[0], dict):
            return signed[0]
        return {}

    @staticmethod
    def _normalize_report_type(report_type: Any) -> str:
        raw = str(report_type or "").strip().lower()
        alias = {
            "inspection_report": "inspection",
            "qcspec": "inspection",
            "quality": "inspection",
            "lab_report": "lab",
            "laboratory": "lab",
            "monthly": "monthly_summary",
            "summary": "monthly_summary",
            "archive": "final_archive",
            "final": "final_archive",
            "final_archive_cover": "final_archive",
        }
        return alias.get(raw, raw if raw in TEMPLATE_BY_TYPE else "inspection")

    def _pick_template_name(self, project_meta: dict[str, Any], report_type: str) -> str:
        explicit = str(project_meta.get("template_name") or "").strip()
        if explicit:
            return explicit
        normalized = self._normalize_report_type(report_type)
        return TEMPLATE_BY_TYPE.get(normalized, TEMPLATE_BY_TYPE["inspection"])

    def _result_cn(self, result_code: str) -> str:
        code = self._to_text(result_code).strip().upper()
        if code == "CANCELLED":
            return CANCELLED_CN
        return self._fmt_result(code)

    @staticmethod
    def _infer_item_key(row: dict[str, Any]) -> str | None:
        row_type = str(row.get("test_type") or row.get("type") or "").strip().lower()
        type_name = str(row.get("test_type_name") or row.get("type_name") or "").strip()
        token = f"{row_type} {type_name}".lower()
        if any(k in token for k in ["spacing", "\u95f4\u8ddd"]):
            return "main_rebar"
        if any(k in token for k in ["frame", "\u9aa8\u67b6"]):
            return "frame_size"
        if any(k in token for k in ["cover", "\u4fdd\u62a4\u5c42"]):
            return "cover_thickness"
        if any(k in token for k in ["flatness", "iri", "\u5e73\u6574\u5ea6", "\u8def\u9762"]):
            return "road_flatness"
        return None

    def _build_named_items(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        named: dict[str, Any] = {
            "main_rebar": {},
            "main_rebar_multi": {},
            "frame_size": {},
            "cover_thickness": {},
            "road_flatness": {},
        }

        spacing_rows: list[dict[str, Any]] = []
        flatness_rows: list[dict[str, Any]] = []
        for row in rows:
            row_type = str(row.get("test_type") or row.get("type") or "").strip()
            if row_type:
                named[row_type] = row

            inferred = self._infer_item_key(row)
            if inferred == "main_rebar":
                spacing_rows.append(row)
            elif inferred == "road_flatness":
                flatness_rows.append(row)
                named["road_flatness"] = row
            elif inferred:
                named[inferred] = row

        if spacing_rows:
            named["main_rebar"] = spacing_rows[0]
            named["main_rebar_multi"] = spacing_rows[1] if len(spacing_rows) > 1 else {}
        elif flatness_rows:
            # Inspection template is fixed to rebar slots. If no spacing rows exist,
            # map road-flatness into the first slot for backward compatibility.
            named["main_rebar"] = flatness_rows[0]
            named["main_rebar_multi"] = {}
        elif rows:
            # Backward fallback: keep first row visible when no spacing-like type is detected.
            named["main_rebar"] = rows[0]
            named["main_rebar_multi"] = {}
        return named

    def _normalize_inspection_proof(self, proof: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(proof, dict):
            return proof
        out = dict(proof)
        sd = out.get("state_data") if isinstance(out.get("state_data"), dict) else {}
        sd_out = dict(sd)
        test_type, test_type_name = self._resolve_test_type(sd_out, fallback_type="inspection")
        schema_mode = self._resolve_schema_mode(sd_out, test_type=test_type, test_type_name=test_type_name)
        sd_out.setdefault("test_type", test_type)
        sd_out.setdefault("type", test_type)
        sd_out.setdefault("test_name", test_type_name)
        sd_out.setdefault("type_name", test_type_name)
        sd_out.setdefault("schema_mode", schema_mode)
        if sd_out.get("standard_value") is None:
            if sd_out.get("standard") is not None:
                sd_out["standard_value"] = sd_out.get("standard")
            elif sd_out.get("design") is not None:
                sd_out["standard_value"] = sd_out.get("design")
        if not self._to_text(sd_out.get("standard_op")).strip():
            probe = {"type": test_type, "type_name": test_type_name}
            if sd_out.get("limit") not in (None, "", "-"):
                sd_out["standard_op"] = STANDARD_OP_PLUS_MINUS
            elif self._is_compaction_like(probe) or schema_mode == SCHEMA_MODE_VALUE_STANDARD_MIN:
                sd_out["standard_op"] = ">="
            else:
                sd_out["standard_op"] = "<="
        if sd_out.get("value") is None and isinstance(sd_out.get("values"), list) and len(sd_out["values"]) == 1:
            sd_out["value"] = sd_out["values"][0]
        out["state_data"] = sd_out
        return out

    def _values_single_line(self, row: dict[str, Any]) -> str:
        values = row.get("values")
        unit = self._to_text(row.get("unit") or "").strip()
        if unit == "-":
            unit = ""
        force_inline = bool(unit and "/" in unit)
        if isinstance(values, list) and values:
            pieces = [self._with_unit(self._format_num(float(v)), unit, force_inline=force_inline) for v in values]
            return SEPARATOR_CN.join(pieces)
        value = self._to_text(row.get("value") or "").strip()
        return value or "-"

    def _resolve_table_headers(self, project_meta: dict[str, Any]) -> list[str]:
        defaults = ["检查项目", "检查项目", "规范要求", "设计值", "实测值", "判定"]
        raw = project_meta.get("table_headers")
        if isinstance(raw, list):
            vals = [self._to_text(x).strip() for x in raw]
            if len(vals) >= 6:
                return [vals[i] or defaults[i] for i in range(6)]
            return defaults
        if isinstance(raw, dict):
            return [
                self._to_text(raw.get("item")).strip() or defaults[0],
                self._to_text(raw.get("sub_item")).strip() or defaults[1],
                self._to_text(raw.get("limit")).strip() or defaults[2],
                self._to_text(raw.get("standard")).strip() or defaults[3],
                self._to_text(raw.get("value")).strip() or defaults[4],
                self._to_text(raw.get("result")).strip() or defaults[5],
            ]
        return defaults

    @staticmethod
    def _set_cell_text(cell: Any, text: str, *, color: RGBColor | None = None) -> None:
        cell.text = ""
        paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
        run = paragraph.add_run(text or "-")
        if color is not None:
            run.font.color.rgb = color

    def _rewrite_inspection_table_rows(
        self,
        doc_bytes: bytes,
        rows: list[dict[str, Any]],
        *,
        header_labels: list[str] | None = None,
    ) -> bytes:
        """
        Rewrite inspection detail table rows so exported table is 1:1 with records.
        Avoid legacy static rows (e.g. fixed rebar placeholders / ??? cell).
        """
        if not rows:
            return doc_bytes
        src = io.BytesIO(doc_bytes)
        doc = Document(src)
        if len(doc.tables) < 2:
            return doc_bytes

        table = doc.tables[1]
        if len(table.rows) < 1:
            return doc_bytes

        labels = (header_labels or ["检查项目", "检查项目", "规范要求", "设计值", "实测值", "判定"])[:6]
        for idx in range(min(len(table.rows[0].cells), 6)):
            table.rows[0].cells[idx].text = labels[idx]

        # Keep header only, drop all template body rows.
        while len(table.rows) > 1:
            table._tbl.remove(table.rows[-1]._tr)

        for row in rows:
            cells = table.add_row().cells
            test_name = self._to_text(row.get("test_type_name") or row.get("test_type") or "-")
            unit = self._to_text(row.get("unit") or "").strip()
            test_label = f"{test_name} ({unit})" if unit and unit != "-" else test_name
            sub_item = self._to_text(row.get("stake") or row.get("location") or "-")
            limit = self._to_text(row.get("norm_requirement") or row.get("limit") or "-")
            standard = self._to_text(row.get("standard") or row.get("design") or "-")
            measured = self._values_single_line(row)
            result_cn = self._to_text(row.get("result_cn") or "-")
            raw_result_code = self._to_text(row.get("result") or "").upper()
            proof_hash = self._to_text(row.get("proof_hash") or "")
            if proof_hash:
                measured = f"{measured}\nPF:{proof_hash[:20]}..."
            deviation_pct = row.get("deviation_percent")
            if deviation_pct is not None:
                try:
                    deviation_text = f"{float(deviation_pct):+0.2f}%"
                    result_cn = f"{result_cn} ({deviation_text})"
                except Exception:
                    pass
            is_fail = raw_result_code == "FAIL" or self._to_text(row.get("result_cn") or "") == FAIL_CN

            self._set_cell_text(cells[0], test_label or "-")
            self._set_cell_text(cells[1], sub_item or "-")
            self._set_cell_text(cells[2], limit or "-")
            self._set_cell_text(cells[3], standard or "-")
            self._set_cell_text(cells[4], measured or "-", color=FAIL_RGB if is_fail else None)
            self._set_cell_text(cells[5], result_cn or "-", color=FAIL_RGB if is_fail else None)

        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()

    def render_docpeg_report(
        self,
        proofs: list[dict[str, Any]],
        project_meta: dict[str, Any],
        *,
        report_type: str = "inspection",
    ) -> bytes:
        """
        Generic sovereign export engine for QCSpec report templates.
        """
        project_meta = self._normalize_payload(project_meta)
        proofs = self._normalize_payload(proofs)

        normalized_type = self._normalize_report_type(report_type)
        template_name = self._pick_template_name(project_meta, normalized_type)
        tpl = self._load(template_name)

        rows: list[dict[str, Any]] = []
        any_fail = False
        sorted_proofs = sorted(
            [p for p in proofs if isinstance(p, dict)],
            key=lambda item: self._to_text(item.get("created_at")),
        )

        for idx, proof in enumerate(sorted_proofs, start=1):
            sd = proof.get("state_data") if isinstance(proof.get("state_data"), dict) else {}
            signing = self._first_signing(proof)
            test_type, test_type_name = self._resolve_test_type(sd, fallback_type=normalized_type)
            schema_mode = self._resolve_schema_mode(sd, test_type=test_type, test_type_name=test_type_name)
            unit_text = self._extract_unit(sd)
            inline_unit = bool(unit_text and ("/" in unit_text or self._is_flatness_like({"type": test_type, "type_name": test_type_name})))

            design = self._to_float(sd.get("design"))
            standard_num = self._to_float(sd.get("standard"))
            if design is None and schema_mode == SCHEMA_MODE_DESIGN_LIMIT and standard_num is not None:
                design = standard_num

            spec_uri = specir_derive_spec_uri(
                sd,
                row_norm_uri=proof.get("norm_uri"),
                fallback_norm_ref=project_meta.get("norm_ref"),
            )
            resolved_spec = specir_resolve_spec_rule(
                spec_uri=spec_uri,
                metric=test_type_name or test_type,
                test_type=test_type,
                test_name=test_type_name,
                context={
                    "component_type": sd.get("component_type") or sd.get("structure_type"),
                    "stake": sd.get("stake") or sd.get("location"),
                },
                sb=None,
            )
            rule_op, rule_standard, rule_tolerance = self._resolve_standard_rule(
                state_data=sd,
                test_type=test_type,
                test_type_name=test_type_name,
                schema_mode=schema_mode,
                design=design,
                standard=standard_num,
            )
            if resolved_spec.get("operator"):
                rule_op = self._normalize_standard_op(resolved_spec.get("operator")) or rule_op
            if resolved_spec.get("threshold") is not None:
                rule_standard = self._to_float(resolved_spec.get("threshold"))
            if resolved_spec.get("tolerance") is not None:
                rule_tolerance = self._to_float(resolved_spec.get("tolerance"))
            if not unit_text:
                unit_text = self._to_text(resolved_spec.get("unit") or "").strip()
            values = self._coerce_values(sd.get("values"), fallback_value=sd.get("value"))

            lower = None
            upper = None
            if rule_op == STANDARD_OP_PLUS_MINUS and rule_standard is not None and rule_tolerance is not None and values:
                lower = rule_standard - rule_tolerance
                upper = rule_standard + rule_tolerance

            proof_result = self._to_text(proof.get("result") or sd.get("result") or "PENDING").upper()
            evaluated = specir_evaluate_measurements(
                values=values,
                operator=rule_op,
                threshold=rule_standard,
                tolerance=rule_tolerance,
                fallback_result=proof_result,
            )
            result_code = self._to_text(evaluated.get("result") or proof_result).upper()
            result_cn = self._result_cn(result_code)
            any_fail = any_fail or (result_code == "FAIL")

            project_uri = self._to_text(proof.get("project_uri") or project_meta.get("project_uri") or "")
            location_text = self._to_text(sd.get("location") or sd.get("stake") or "-")
            segment_uri = self._to_text(proof.get("segment_uri") or sd.get("segment_uri") or "")
            if not segment_uri and project_uri and location_text and location_text != "-":
                segment_uri = f"{project_uri.rstrip('/')}/segment/{location_text}/"
            proof_id = self._to_text(proof.get("proof_id") or "")
            v_uri = self._to_text(sd.get("v_uri") or proof.get("v_uri") or "")
            if not v_uri and project_uri and proof_id:
                v_uri = f"{project_uri.rstrip('/')}/{normalized_type}/{proof_id}/"

            executor_uri = self._to_text(
                signing.get("executor_uri")
                or signing.get("uri")
                or proof.get("owner_uri")
                or project_meta.get("executor_uri")
                or "-"
            )
            ordosign_hash = self._to_text(signing.get("ordosign_hash") or project_meta.get("ordosign_hash") or "-")
            executor_name = self._extract_executor_name(signing, fallback_uri=executor_uri)
            executor_id = self._extract_executor_id(signing, fallback_uri=executor_uri, fallback_name=executor_name)
            created_at_text = self._format_display_time(proof.get("created_at") or "")
            signed_at = self._format_signed_at(signing.get("ts") or proof.get("created_at") or "")
            norm_ref = self._to_text(
                resolved_spec.get("effective_spec_uri")
                or spec_uri
                or sd.get("norm_ref")
                or proof.get("norm_uri")
                or project_meta.get("norm_ref")
                or "-"
            )
            value_num = self._to_float(sd.get("value"))
            if value_num is None and values:
                value_num = values[0] if len(values) == 1 else round(sum(values) / len(values), 4)
            standard_text = self._format_num(rule_standard) if rule_standard is not None else "-"
            value_text = self._format_num(value_num) if value_num is not None else "-"
            norm_requirement = specir_threshold_text(
                rule_op,
                rule_standard,
                rule_tolerance,
                unit_text,
            )
            limit_text = (
                f"{STANDARD_OP_PLUS_MINUS}{self._format_num(rule_tolerance)}"
                if rule_op == STANDARD_OP_PLUS_MINUS and rule_tolerance is not None
                else "-"
            )

            row = {
                "index": idx,
                "proof_id": proof_id,
                "proof_hash": self._to_text(proof.get("proof_hash") or ""),
                "gitpeg_anchor": self._to_text(proof.get("gitpeg_anchor") or PENDING_ANCHOR_CN),
                "project_uri": project_uri,
                "segment_uri": segment_uri,
                "v_uri": v_uri,
                "location": location_text,
                "stake": location_text,
                "test_type": self._to_text(test_type),
                "test_type_name": self._to_text(test_type_name),
                "schema_mode": schema_mode,
                "standard_op": rule_op,
                "type": self._to_text(test_type),
                "type_name": self._to_text(test_type_name),
                "unit": unit_text or "-",
                "design": self._with_unit(standard_text, unit_text, force_inline=inline_unit),
                "design_raw": standard_text,
                "standard": self._with_unit(standard_text, unit_text, force_inline=inline_unit),
                "standard_raw": standard_text,
                "standard_value": self._with_unit(standard_text, unit_text, force_inline=inline_unit),
                "limit": limit_text,
                "norm_requirement": norm_requirement,
                "limit_num": self._format_num(rule_tolerance) if rule_tolerance is not None else "-",
                "value": self._with_unit(value_text, unit_text, force_inline=inline_unit),
                "value_raw": value_text,
                "values": values,
                "val_str": self._format_values_multiline(values, chunk=10, unit=unit_text, force_inline_unit=inline_unit),
                "range_str": (
                    f"[{self._format_num(lower)}, {self._format_num(upper)}]"
                    if lower is not None and upper is not None
                    else "-"
                ),
                "result": result_code,
                "result_cn": result_cn,
                "deviation_percent": evaluated.get("deviation_percent"),
                "executor_uri": executor_uri,
                "ordosign_hash": ordosign_hash,
                "signed_by": executor_name,
                "executor_name": executor_name,
                "executor_id": executor_id,
                "signed_at": signed_at,
                "norm_ref": norm_ref,
                "spec_excerpt": self._to_text(resolved_spec.get("excerpt") or ""),
                "spec_version": self._to_text(resolved_spec.get("version") or ""),
                "created_at": created_at_text,
                "remark": self._to_text(sd.get("remark") or ""),
            }
            rows.append(row)

        latest = rows[-1] if rows else {}
        primary = latest if rows else {}
        verify_uri = (
            f"{self._verify_base_url()}/v/{latest.get('proof_id')}?trace=true"
            if latest.get("proof_id")
            else ""
        )
        signed_at_key = self._format_signed_at(
            latest.get("signed_at") or latest.get("created_at") or self._now_seconds()
        )
        v_uri_tree = self._build_v_uri_tree(
            project_uri=self._to_text(latest.get("project_uri") or project_meta.get("project_uri") or ""),
            segment_uri=self._to_text(latest.get("segment_uri") or ""),
            v_uri=self._to_text(latest.get("v_uri") or ""),
            proof_id=self._to_text(latest.get("proof_id") or ""),
            stake=self._to_text(latest.get("stake") or latest.get("location") or project_meta.get("stake_range") or "-"),
            verify_uri=verify_uri,
        )
        summary_result_cn = FAIL_CN if any_fail else PASS_CN
        named_items = self._build_named_items(rows)

        context = {
            "report_type": normalized_type,
            "construction_unit": self._to_text(
                project_meta.get("construction_unit")
                or project_meta.get("enterprise_name")
                or project_meta.get("org_name")
                or "-"
            ),
            "project_name": self._to_text(project_meta.get("name") or project_meta.get("project_name") or ""),
            "project_uri": self._to_text(project_meta.get("project_uri") or latest.get("project_uri") or ""),
            "contract_no": self._to_text(project_meta.get("contract_no") or "-"),
            "stake_range": self._to_text(project_meta.get("stake_range") or project_meta.get("location") or "-"),
            "check_date": self._to_text(project_meta.get("check_date") or self._now()[:10]),
            "inspector": self._to_text(project_meta.get("inspector") or project_meta.get("operator") or "-"),
            "tech_leader": self._to_text(project_meta.get("tech_leader") or "-"),
            "generated_at": self._now(),
            "records": rows,
            "rows": rows,
            "items": named_items,
            "test": {
                "name": self._to_text(primary.get("test_type_name") or primary.get("test_type") or ""),
                "val_str": self._to_text(primary.get("val_str") or "-"),
                "value": self._to_text(primary.get("value") or "-"),
                "unit": self._to_text(primary.get("unit") or "-"),
                "standard": self._to_text(primary.get("standard") or "-"),
                "standard_value": self._to_text(primary.get("standard_value") or primary.get("standard") or "-"),
                "standard_op": self._to_text(primary.get("standard_op") or "-"),
                "limit": self._to_text(primary.get("norm_requirement") or primary.get("limit") or "-"),
                "stake": self._to_text(primary.get("stake") or primary.get("location") or "-"),
                "result_cn": self._to_text(primary.get("result_cn") or "-"),
            },
            "total_count": len(rows),
            "pass_count": sum(1 for x in rows if x.get("result") == "PASS"),
            "fail_count": sum(1 for x in rows if x.get("result") == "FAIL"),
            "summary_result_cn": summary_result_cn,
            "conclusion": summary_result_cn,
            "proof_id": self._to_text(latest.get("proof_id") or ""),
            "proof_hash": self._to_text(latest.get("proof_hash") or ""),
            "gitpeg_anchor": self._to_text(latest.get("gitpeg_anchor") or PENDING_ANCHOR_CN),
            "v_uri": self._to_text(latest.get("v_uri") or ""),
            "segment_uri": self._to_text(latest.get("segment_uri") or ""),
            "stake": self._to_text(latest.get("stake") or latest.get("location") or project_meta.get("stake_range") or "-"),
            "executor_uri": self._to_text(latest.get("executor_uri") or project_meta.get("executor_uri") or "-"),
            "executor_id": self._to_text(latest.get("executor_id") or ""),
            "ordosign_hash": self._to_text(latest.get("ordosign_hash") or project_meta.get("ordosign_hash") or "-"),
            "signed_by": self._to_text(latest.get("signed_by") or latest.get("executor_uri") or "-"),
            "executor_name": self._to_text(latest.get("executor_name") or latest.get("signed_by") or "-"),
            "signed_at": signed_at_key,
            "time_primary_key": signed_at_key,
            "created_at": self._format_display_time(latest.get("created_at") or ""),
            "norm_ref": self._to_text(latest.get("norm_ref") or project_meta.get("norm_ref") or "-"),
            "verify_uri": verify_uri,
            "v_uri_tree": v_uri_tree,
            "v_uri_nodes": v_uri_tree.get("nodes", []),
            "utxo_locator": {
                "proof_id": self._to_text(latest.get("proof_id") or ""),
                "stake": self._to_text(latest.get("stake") or latest.get("location") or "-"),
                "segment_uri": self._to_text(latest.get("segment_uri") or ""),
                "v_uri": self._to_text(latest.get("v_uri") or ""),
                "verify_uri": verify_uri,
            },
        }
        if verify_uri:
            qr = self._qr(tpl, verify_uri, size_mm=25)
            context["verify_qr"] = qr
            context["qr_image"] = qr
        signature_image, signature_status = self._insert_signature(
            self._to_text(latest.get("executor_id") or latest.get("signed_by") or ""),
            tpl=tpl,
        )
        context["signature_image"] = signature_image
        context["signature_loaded"] = signature_status == "loaded"
        context["signature_status"] = signature_status

        # Keep plain string substitution so rendered text inherits template run font.
        tpl.render(context, autoescape=False)
        buf = io.BytesIO()
        tpl.save(buf)
        rendered = buf.getvalue()
        if normalized_type == "inspection":
            return self._rewrite_inspection_table_rows(
                rendered,
                rows,
                header_labels=self._resolve_table_headers(project_meta),
            )
        return rendered

    def render_rebar_live_report(self, proofs: list, project_meta: dict) -> bytes:
        """
        Backward-compatible rebar report entry point.
        """
        return self.render_inspection_report(proofs, project_meta)

    def render_mode_driven_inspection_report(
        self,
        proofs: list[dict[str, Any]],
        project_meta: dict[str, Any],
    ) -> bytes:
        """
        Mode-driven generic inspection renderer.
        Supported schema modes:
        - design_limit: design + limit (+/-) + values
        - value_standard_max: value <= standard
        - value_standard_min: value >= standard
        - value_standard_eq: value == standard
        """
        normalized = [self._normalize_inspection_proof(p) for p in (proofs or []) if isinstance(p, dict)]
        return self.render_docpeg_report(normalized, project_meta, report_type="inspection")

    def render_universal_report(
        self,
        proofs: list[dict[str, Any]],
        project_meta: dict[str, Any],
        *,
        report_type: str = "inspection",
    ) -> bytes:
        """
        Universal schema-driven renderer for DocPeg.
        - Dynamically adapts test_type/value/unit/standard from proof.state_data
        - Produces atomic sovereignty variables for Word template binding
        - Keeps timestamp display at second precision (YYYY-MM-DD HH:mm:ss)
        """
        normalized_type = self._normalize_report_type(report_type)
        if normalized_type == "inspection":
            return self.render_mode_driven_inspection_report(proofs, project_meta)
        return self.render_docpeg_report(proofs, project_meta, report_type=normalized_type)

    def render_inspection_report(self, proofs: list[dict[str, Any]], project_meta: dict[str, Any]) -> bytes:
        """
        Explicit entrypoint for inspection report rendering.
        Handles dynamic inspection schema fields such as:
        - rebar_spacing (design/limit/values)
        - flatness-like tests (value/standard/unit)
        """
        return self.render_universal_report(proofs, project_meta, report_type="inspection")


def build_rebar_live_mock_case() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Mock data compatible with ProofUTXOEngine rows.
    """
    project_meta = {
        "name": "\u6210\u5ce8\u9ad8\u901f",
        "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
        "contract_no": "CEGS-TJ01",
        "stake_range": "K22+500~K22+800",
        "check_date": "2026-03-26",
        "inspector": "\u738b\u8d28\u68c0",
        "tech_leader": "\u674e\u5de5",
        "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
        "construction_unit": "\u56db\u5ddd\u6210\u5ce8\u9ad8\u901f\u603b\u627f\u5305\u90e8",
        "template_name": "01_inspection_report.docx",
        "norm_ref": "JTG F80/1-2017",
    }
    proofs = [
        {
            "proof_id": "GP-PROOF-A1B2C3D4E5F60708",
            "proof_hash": "8fdce5686af2d6516c3e2fdf3f31d801cfd09e61a01f93838ec74ec31da43f4b",
            "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
            "segment_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/segment/K22+500/",
            "proof_type": "inspection",
            "result": "PASS",
            "gitpeg_anchor": "GitPeg#72d88d93",
            "signed_by": [
                {
                    "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
                    "role": "AI",
                    "ordosign_hash": "d0e8da4d4435630ee35f35ef",
                    "ts": "2026-03-26T10:10:00Z",
                }
            ],
            "created_at": "2026-03-26T10:10:00Z",
            "state_data": {
                "inspection_id": "24db30d4-b573-4ff8-b5ec-59f6e5f4df22",
                "v_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/inspection/24db30d4/",
                "location": "K22+500",
                "type": "rebar_spacing",
                "type_name": "\u53d7\u529b\u94a2\u7b4b\u95f4\u8ddd\uff08\u540c\u6392\uff09",
                "design": 300,
                "limit": "\u00b110",
                "values": [304, 299, 303, 301, 297, 296, 297, 300, 302, 297, 304, 299],
                "remark": "\u73b0\u573a\u62bd\u68c012\u70b9",
                "norm_ref": "JTG F80/1-2017",
            },
        },
        {
            "proof_id": "GP-PROOF-B1C2D3E4F5060708",
            "proof_hash": "21f51f453f248e73f3a6f11f91a79f7f17cd5c66f2269a205ca45d84f8f1732f",
            "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
            "segment_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/segment/K22+500/",
            "proof_type": "inspection",
            "result": "PASS",
            "gitpeg_anchor": "GitPeg#72d88d93",
            "signed_by": [
                {
                    "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
                    "role": "AI",
                    "ordosign_hash": "c3f8c4b76d90da7d5b08725d",
                    "ts": "2026-03-26T10:12:00Z",
                }
            ],
            "created_at": "2026-03-26T10:12:00Z",
            "state_data": {
                "inspection_id": "8f26d77c-6721-4ff3-a2ef-90d53ca2ecf0",
                "v_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/inspection/8f26d77c/",
                "location": "K22+500",
                "type": "rebar_spacing",
                "type_name": "\u53d7\u529b\u94a2\u7b4b\u95f4\u8ddd\uff08\u4e24\u6392\u4ee5\u4e0a\u6392\u8ddd\uff09",
                "design": 300,
                "limit": "\u00b110",
                "values": [304, 299, 303, 301, 297, 296, 297, 300, 302, 297],
                "remark": "\u73b0\u573a\u62bd\u68c010\u70b9",
                "norm_ref": "JTG F80/1-2017",
            },
        },
        {
            "proof_id": "GP-PROOF-C1D2E3F405060708",
            "proof_hash": "9b005bc4ef9d0f35a3945a502f6b29e6c867651fcd965dff1f4f9ea14303497e",
            "project_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/",
            "segment_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/segment/K22+500/",
            "proof_type": "inspection",
            "result": "PASS",
            "gitpeg_anchor": "GitPeg#72d88d93",
            "signed_by": [
                {
                    "executor_uri": "v://cn/gitpeg/executor/\u738b\u8d28\u68c0/",
                    "role": "AI",
                    "ordosign_hash": "2a20f39d3847c2921b5826fc",
                    "ts": "2026-03-26T10:14:00Z",
                }
            ],
            "created_at": "2026-03-26T10:14:00Z",
            "state_data": {
                "inspection_id": "b6ce12a3-e2a5-4797-a5d8-1017bbd33434",
                "v_uri": "v://cn/gitpeg/highway/\u6210\u5ce8\u9ad8\u901f/inspection/b6ce12a3/",
                "location": "K22+500",
                "type": "cover_thickness",
                "type_name": "\u4fdd\u62a4\u5c42\u539a\u5ea6",
                "design": 30,
                "limit": "\u00b15",
                "values": [33, 29, 30, 31, 26, 33],
                "remark": "\u73b0\u573a\u62bd\u68c06\u70b9",
                "norm_ref": "JTG F80/1-2017",
            },
        },
    ]
    return proofs, project_meta
