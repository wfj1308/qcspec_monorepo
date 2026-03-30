"""
SMU lifecycle orchestration service.

Six-stage flow:
1) Genesis Trip (BOQ import -> hierarchical UTXO)
2) Governance & QCGate (dynamic form + threshold context)
3) Execution & SnapPeg (TripRole execution + evidence fingerprint)
4) OrdoSign & DID (multi-party sovereign sign)
5) DocPeg Execution (approved trigger -> report bundle context)
6) SMU Risk Audit & Freeze (validate_logic + freeze proof)
"""

from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import zipfile
from typing import Any, Callable

from fastapi import HTTPException

from services.api.boq_utxo_service import (
    BoqItem,
    initialize_boq_utxos,
)
from services.api.proof_utxo_engine import ProofUTXOEngine
from services.api.specdict_gate_service import resolve_dynamic_threshold
from services.api.triprole_engine import (
    build_docfinal_package_for_boq,
    execute_triprole_action,
)
from services.api.unit_merkle_service import build_unit_merkle_snapshot


ITEM_NO_PATTERN = re.compile(r"^\d{3}(?:-\d+)*$")


@dataclass(slots=True)
class RoleIdentity:
    executor_uri: str
    executor_did: str
    executor_role: str


@dataclass(slots=True)
class TripAction:
    name: str
    input_proof_id: str
    output_proof_id: str
    result: str


@dataclass(slots=True)
class ContainerState:
    status: str
    stage: str
    boq_item_uri: str
    smu_id: str


SPU_TEMPLATE_LIBRARY: dict[str, dict[str, Any]] = {
    "SPU_Reinforcement": {
        "label": "钢筋质检模板",
        "contexts": ["main_beam", "guardrail", "pier", "generic"],
        "form_schema": [
            {
                "field": "yield_strength",
                "label": "Yield Strength",
                "unit": "MPa",
                "operator": ">=",
                "default": "400",
                "source": "SpecDict",
            },
            {
                "field": "spacing_deviation",
                "label": "Spacing Deviation",
                "unit": "mm",
                "operator": "range",
                "default": "-10~10",
                "source": "SpecDict",
            },
            {
                "field": "cover_thickness",
                "label": "Cover Thickness",
                "unit": "mm",
                "operator": "range",
                "default": "20~60",
                "source": "SpecDict",
            },
        ],
    },
    "SPU_Concrete": {
        "label": "混凝土质检模板",
        "contexts": ["main_beam", "pier", "slab", "generic"],
        "form_schema": [
            {
                "field": "compressive_strength",
                "label": "Compressive Strength",
                "unit": "MPa",
                "operator": ">=",
                "default": "30",
                "source": "SpecDict",
            },
            {
                "field": "slump",
                "label": "Slump",
                "unit": "mm",
                "operator": "range",
                "default": "120~220",
                "source": "SpecDict",
            },
        ],
    },
    "SPU_Contract": {
        "label": "合同凭证模板",
        "contexts": ["generic"],
        "form_schema": [
            {
                "field": "voucher_ref",
                "label": "Contract Voucher Ref",
                "unit": "",
                "operator": "present",
                "default": "",
                "source": "Contract",
            },
            {
                "field": "claimed_amount",
                "label": "Claimed Amount",
                "unit": "CNY",
                "operator": "present",
                "default": "",
                "source": "Contract",
            },
        ],
    },
    "SPU_Generic400": {
        "label": "未绑定模板",
        "contexts": ["generic"],
        "form_schema": [
            {
                "field": "quality_index",
                "label": "Quality Index",
                "unit": "",
                "operator": ">=",
                "default": "1",
                "source": "SpecDict",
            },
        ],
    },
}


HEADER_ALIASES: dict[str, set[str]] = {
    'item_no': {
        '子目号',
        '子目號',
        '子目编号',
        '子目編號',
        '子目编码',
        '子目編碼',
        '细目号',
        '細目號',
        '细目编号',
        '細目編號',
        '清单编码',
        '清單編碼',
        '清单编号',
        '清單編號',
        '细目',
        '細目',
        '子目',
        'itemno',
        'item_no',
        'itemcode',
        'item',
    },
    'name': {
        '子目名称',
        '子目名稱',
        '细目名称',
        '細目名稱',
        '清单名称',
        '清單名稱',
        '名称',
        '名稱',
        '项目名称',
        '項目名稱',
        'itemname',
        'name',
    },
    'unit': {'单位', '單位', '计量单位', '計量單位', 'unit'},
    'division': {'分部工程', '分部', 'division'},
    'subdivision': {'分项工程', '分項工程', '子分项', '子分項', 'subdivision'},
    'hierarchy': {'所属分部分项层级', '所屬分部分項層級', '分部分项层级', '分部分項層級', '层级', '層級', 'hierarchy', 'wbs'},
    'design_quantity': {
        '设计数量',
        '設計數量',
        '设计工程量',
        '設計工程量',
        '设计量',
        '設計量',
        '施工图数量',
        '施工圖數量',
        '工程量',
        'designqty',
        'designquantity',
    },
    'unit_price': {'单价', '單價', '综合单价', '綜合單價', '价格', '價格', 'price', 'unitprice'},
    'approved_quantity': {
        '批复数量',
        '批復數量',
        '批准数量',
        '批准數量',
        '合同数量',
        '合同數量',
        '合同工程量',
        'approvedqty',
        'approvedquantity',
    },
    'remark': {'备注', '備註', 'remark'},
}



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
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_header(value: Any) -> str:
    text = _to_text(value).strip().lstrip("\ufeff").lower()
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("號", "号").replace("編", "编").replace("碼", "码")
    text = text.replace("稱", "称").replace("單", "单").replace("價", "价")
    text = re.sub(r"[\s\u3000]+", "", text)
    text = re.sub(r"[:：_/\\-]", "", text)
    return text


def _detect_header_map(rows: list[list[Any]]) -> tuple[int, dict[str, int]]:
    normalized_aliases: dict[str, set[str]] = {
        field: {_normalize_header(alias) for alias in aliases}
        for field, aliases in HEADER_ALIASES.items()
    }

    def _header_match(key: str, alias: str) -> bool:
        if not key or not alias:
            return False
        if key == alias:
            return True
        # Handle merged header text like "子目號(item_no)" or wrapped titles.
        if len(alias) >= 3 and alias in key:
            return True
        if len(key) >= 4 and key in alias:
            return True
        return False

    best_idx = -1
    best_score = -1
    best_map: dict[str, int] = {}
    best_found_fields: set[str] = set()
    for idx, row in enumerate(rows):
        mapping: dict[str, int] = {}
        score = 0
        for col_idx, cell in enumerate(row):
            key = _normalize_header(cell)
            if not key:
                continue
            for field, aliases in normalized_aliases.items():
                if field in mapping:
                    continue
                if any(_header_match(key, alias) for alias in aliases):
                    mapping[field] = col_idx
                    score += 1
        if score > best_score and "item_no" in mapping and "name" in mapping:
            best_idx = idx
            best_score = score
            best_map = mapping
            best_found_fields = set(mapping.keys())
    if best_idx < 0:
        found = ",".join(sorted(best_found_fields)) if best_found_fields else "none"
        raise HTTPException(
            400,
            f"Failed to detect BOQ header row from upload file. required=item_no,name found={found}",
        )
    return best_idx, best_map


def _rows_from_csv_bytes(content: bytes) -> list[list[Any]]:
    if not content:
        return []
    text = ""
    for enc in ("utf-8-sig", "gb18030", "gbk"):
        try:
            text = content.decode(enc)
            break
        except Exception:
            continue
    if not text:
        text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    return [list(row) for row in reader]


def _rows_from_xlsx_bytes(content: bytes) -> tuple[list[list[Any]], str]:
    try:
        import openpyxl
    except Exception as exc:
        raise HTTPException(500, f"openpyxl not available: {exc}") from exc
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except zipfile.BadZipFile:
        if content[:4] == b"\xD0\xCF\x11\xE0":
            # Fallback to legacy .xls parser when file is mis-labeled as .xlsx
            return _rows_from_xls_bytes(content)
        raise HTTPException(400, "Invalid .xlsx file. Please re-save as .xlsx or .csv.")
    except Exception as exc:
        raise HTTPException(400, f"Failed to read .xlsx file: {exc}")
    best_rows: list[list[Any]] = []
    best_sheet = wb.sheetnames[0]
    best_score = -1

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows: list[list[Any]] = []
        for row in ws.iter_rows(values_only=True):
            rows.append(list(row))
            if len(rows) >= 300000:
                break
        if not rows:
            continue
        score = -1
        try:
            _, colmap = _detect_header_map(rows[:120])
            score = len(colmap)
        except HTTPException:
            score = -1
        if score > best_score:
            best_rows = rows
            best_sheet = sheet_name
            best_score = score
    if not best_rows:
        return [], best_sheet
    return best_rows, best_sheet


def _rows_from_xls_bytes(content: bytes) -> tuple[list[list[Any]], str]:
    try:
        import xlrd  # type: ignore
    except Exception as exc:
        raise HTTPException(
            400,
            f".xls parser missing (xlrd). Please convert to CSV/XLSX or install xlrd in services/api env. detail={exc}",
        ) from exc
    wb = xlrd.open_workbook(file_contents=content)
    best_rows: list[list[Any]] = []
    best_sheet = wb.sheet_by_index(0).name if wb.nsheets > 0 else "sheet0"
    best_score = -1

    for i in range(wb.nsheets):
        sheet = wb.sheet_by_index(i)
        rows: list[list[Any]] = []
        for r in range(sheet.nrows):
            rows.append([sheet.cell_value(r, c) for c in range(sheet.ncols)])
            if len(rows) >= 300000:
                break
        if not rows:
            continue
        score = -1
        try:
            _, colmap = _detect_header_map(rows[:120])
            score = len(colmap)
        except HTTPException:
            score = -1
        if score > best_score:
            best_rows = rows
            best_sheet = _to_text(getattr(sheet, "name", "")).strip() or best_sheet
            best_score = score
    if not best_rows:
        return [], best_sheet
    return best_rows, best_sheet


def _parse_boq_upload(file_name: str, content: bytes) -> list[BoqItem]:
    name = _to_text(file_name).strip()
    lower = name.lower()
    header_sig = content[:4] if content else b""
    is_ole2 = header_sig == b"\xD0\xCF\x11\xE0"
    is_zip = header_sig == b"\x50\x4B\x03\x04"

    if lower.endswith(".csv"):
        rows = _rows_from_csv_bytes(content)
        source_sheet = "csv"
    elif lower.endswith(".xlsx"):
        if is_ole2:
            rows, source_sheet = _rows_from_xls_bytes(content)
        else:
            rows, source_sheet = _rows_from_xlsx_bytes(content)
        source_sheet = _to_text(source_sheet).strip() or "xlsx"
    elif lower.endswith(".xls"):
        rows, source_sheet = _rows_from_xls_bytes(content)
        source_sheet = _to_text(source_sheet).strip() or "xls"
    elif is_ole2:
        rows, source_sheet = _rows_from_xls_bytes(content)
        source_sheet = _to_text(source_sheet).strip() or "xls"
    elif is_zip:
        rows, source_sheet = _rows_from_xlsx_bytes(content)
        source_sheet = _to_text(source_sheet).strip() or "xlsx"
    else:
        rows = _rows_from_csv_bytes(content)
        source_sheet = "unknown"

    if not rows:
        raise HTTPException(400, "Upload file is empty.")

    probe = rows[:120]
    header_row, colmap = _detect_header_map(probe)

    out: list[BoqItem] = []
    for row_idx in range(header_row + 1, len(rows)):
        row = rows[row_idx]
        item_no = _to_text(row[colmap["item_no"]] if colmap["item_no"] < len(row) else "").strip()
        if not item_no or not ITEM_NO_PATTERN.match(item_no):
            continue
        name = _to_text(row[colmap["name"]] if colmap["name"] < len(row) else "").strip()
        unit = _to_text(row[colmap.get("unit", -1)] if colmap.get("unit", -1) < len(row) and colmap.get("unit", -1) >= 0 else "").strip()
        division = _to_text(row[colmap.get("division", -1)] if colmap.get("division", -1) < len(row) and colmap.get("division", -1) >= 0 else "").strip()
        subdivision = _to_text(row[colmap.get("subdivision", -1)] if colmap.get("subdivision", -1) < len(row) and colmap.get("subdivision", -1) >= 0 else "").strip()
        hierarchy_raw = _to_text(row[colmap.get("hierarchy", -1)] if colmap.get("hierarchy", -1) < len(row) and colmap.get("hierarchy", -1) >= 0 else "").strip()

        dq_raw = _to_text(row[colmap.get("design_quantity", -1)] if colmap.get("design_quantity", -1) < len(row) and colmap.get("design_quantity", -1) >= 0 else "").strip()
        up_raw = _to_text(row[colmap.get("unit_price", -1)] if colmap.get("unit_price", -1) < len(row) and colmap.get("unit_price", -1) >= 0 else "").strip()
        aq_raw = _to_text(row[colmap.get("approved_quantity", -1)] if colmap.get("approved_quantity", -1) < len(row) and colmap.get("approved_quantity", -1) >= 0 else "").strip()
        remark = _to_text(row[colmap.get("remark", -1)] if colmap.get("remark", -1) < len(row) and colmap.get("remark", -1) >= 0 else "").strip()

        out.append(
            BoqItem(
                item_no=item_no,
                name=name,
                unit=unit,
                division=division,
                subdivision=subdivision,
                hierarchy_raw=hierarchy_raw,
                design_quantity=_to_float(dq_raw),
                design_quantity_raw=dq_raw,
                unit_price=_to_float(up_raw),
                unit_price_raw=up_raw,
                approved_quantity=_to_float(aq_raw),
                approved_quantity_raw=aq_raw,
                remark=remark,
                row_index=row_idx + 1,
                sheet_name=source_sheet,
            )
        )
    if not out:
        raise HTTPException(400, "No BOQ item rows parsed from upload file.")
    return out


def _resolve_spu_template(item_no: str, item_name: str) -> dict[str, Any]:
    code = _to_text(item_no).strip()
    name = _to_text(item_name).strip()
    lower_name = name.lower()

    template_id = "SPU_Generic400"
    if any(token in name for token in ("费", "协调", "管理", "监测", "监控", "咨询", "勘察", "保险", "交通", "保通", "征迁", "补偿", "迁改", "拆除", "临时", "安全", "试验", "检验")):
        template_id = "SPU_Contract"
    if code.startswith("403") or ("钢筋" in name) or ("rebar" in lower_name):
        template_id = "SPU_Reinforcement"
    elif ("混凝土" in name) or ("concrete" in lower_name):
        template_id = "SPU_Concrete"

    template = _as_dict(SPU_TEMPLATE_LIBRARY.get(template_id))
    return {
        "spu_template_id": template_id,
        "spu_template_label": _to_text(template.get("label") or template_id).strip(),
        "spu_form_schema": _as_list(template.get("form_schema")),
        "supported_contexts": _as_list(template.get("contexts")),
    }


def _resolve_bridge_table_template_path() -> str:
    candidates = [
        _to_text(os.getenv("QCSPEC_BRIDGE_TABLE_DOCX") or "").strip(),
        r"C:\Users\xm_91\Desktop\3、桥施表.docx",
    ]
    for raw in candidates:
        if not raw:
            continue
        try:
            p = Path(raw).expanduser()
            if p.exists() and p.is_file():
                return str(p.resolve())
        except Exception:
            continue
    return ""


def _resolve_docpeg_template(item_no: str, item_name: str) -> dict[str, Any]:
    code = _to_text(item_no).strip()
    name = _to_text(item_name).strip()
    bridge_docx_path = _resolve_bridge_table_template_path()

    # Rule-based binding: 403 steel/rebar defaults to bridge form 11.
    if code.startswith("403") or ("钢筋" in name):
        return {
            "template_group": "桥施表",
            "template_code": "桥施11表",
            "template_name": "钢筋安装检查表",
            "binding_rule": "item_no startswith 403",
            "template_path": bridge_docx_path,
            "fallback_template": "rebar_inspection_table.docx",
            "is_auto_bound": True,
        }
    if code.startswith("402") or ("混凝土" in name):
        return {
            "template_group": "桥施表",
            "template_code": "桥施63表",
            "template_name": "混凝土施工质量检查表",
            "binding_rule": "item_no startswith 402 or item_name contains 混凝土",
            "template_path": bridge_docx_path,
            "fallback_template": "01_inspection_report.docx",
            "is_auto_bound": True,
        }
    return {
        "template_group": "未绑定",
        "template_code": "",
        "template_name": "",
        "binding_rule": "unbound",
        "template_path": bridge_docx_path,
        "fallback_template": "rebar_inspection_table.docx",
        "is_auto_bound": False,
    }


def _resolve_lab_status(*, sb: Any, project_uri: str, boq_item_uri: str) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    b_uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not p_uri or not b_uri:
        return {"ok": False, "status": "MISSING", "total": 0, "pass": 0}
    try:
        rows = (
            sb.table("proof_utxo")
            .select("proof_id, result, proof_type, state_data, segment_uri, created_at")
            .eq("project_uri", p_uri)
            .eq("proof_type", "lab")
            .order("created_at", desc=False)
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        return {"ok": False, "status": "UNAVAILABLE", "total": 0, "pass": 0, "error": f"{exc.__class__.__name__}"}

    matched: list[dict[str, Any]] = []
    for row in rows:
        sd = _as_dict(row.get("state_data"))
        uri = _to_text(sd.get("boq_item_uri") or row.get("segment_uri") or "").strip().rstrip("/")
        if uri == b_uri:
            matched.append(row)

    if not matched:
        return {"ok": True, "status": "MISSING", "total": 0, "pass": 0}

    lab_pass = [x for x in matched if _to_text(x.get("result") or "").strip().upper() == "PASS"]
    latest = matched[-1]
    latest_pass = lab_pass[-1] if lab_pass else None
    status = "PASS" if lab_pass else "FAIL"
    return {
        "ok": True,
        "status": status,
        "total": len(matched),
        "pass": len(lab_pass),
        "latest_proof_id": _to_text((latest or {}).get("proof_id") or "").strip(),
        "latest_pass_proof_id": _to_text((latest_pass or {}).get("proof_id") or "").strip(),
    }


def _patch_state_data(sb: Any, proof_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    rows = (
        sb.table("proof_utxo")
        .select("state_data")
        .eq("proof_id", proof_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return {}
    sd = _as_dict(rows[0].get("state_data"))
    sd.update(patch)
    sb.table("proof_utxo").update({"state_data": sd}).eq("proof_id", proof_id).execute()
    return sd


def _boq_rows(
    sb: Any,
    *,
    project_uri: str,
    boq_item_uri: str = "",
    only_unspent: bool = False,
    limit: int = 50000,
) -> list[dict[str, Any]]:
    q = (
        sb.table("proof_utxo")
        .select("*")
        .eq("project_uri", project_uri)
        .order("created_at", desc=False)
        .limit(max(1, min(limit, 50000)))
    )
    if only_unspent:
        q = q.eq("spent", False)
    rows = q.execute().data or []
    if boq_item_uri:
        uri = boq_item_uri.rstrip("/")
        out: list[dict[str, Any]] = []
        for row in rows:
            seg = _to_text(row.get("segment_uri") or "").strip().rstrip("/")
            sd = _as_dict(row.get("state_data"))
            item_uri = _to_text(sd.get("boq_item_uri") or seg).strip().rstrip("/")
            if item_uri == uri or seg == uri:
                out.append(row)
        rows = out
    return [x for x in rows if isinstance(x, dict)]


def _latest_unspent_leaf(sb: Any, *, project_uri: str, boq_item_uri: str) -> dict[str, Any]:
    rows = _boq_rows(sb, project_uri=project_uri, boq_item_uri=boq_item_uri, only_unspent=True, limit=20000)
    if not rows:
        return {}
    rows.sort(key=lambda r: _to_text(r.get("created_at") or ""))
    return rows[-1]


def _container_status_from_stage(stage: str, result: str) -> str:
    s = _to_text(stage).strip().upper()
    r = _to_text(result).strip().upper()
    if s in {"INITIAL", "PRECHECK"}:
        return "Unspent"
    if s in {"ENTRY", "INSTALLATION", "VARIATION"}:
        return "Reviewing"
    if s in {"SETTLEMENT"} and r == "PASS":
        return "Approved"
    if r == "FAIL":
        return "Failed"
    return "Reviewing"


def _eval_threshold(operator: str, threshold: Any, measured_value: float | None) -> dict[str, Any]:
    op = _to_text(operator).strip().lower()
    val = measured_value
    if val is None:
        return {"status": "PENDING", "ok": False}
    if isinstance(threshold, list) and len(threshold) >= 2:
        lo = _to_float(threshold[0])
        hi = _to_float(threshold[1])
        if lo is None or hi is None:
            return {"status": "PENDING", "ok": False}
        ok = (val >= min(lo, hi)) and (val <= max(lo, hi))
        return {"status": "SUCCESS" if ok else "FAIL", "ok": ok, "normalized_operator": "range", "threshold": [min(lo, hi), max(lo, hi)]}
    t = _to_float(threshold)
    if t is None:
        return {"status": "PENDING", "ok": False}
    if op in {">=", "gte"}:
        ok = val >= t
    elif op in {"<=", "lte"}:
        ok = val <= t
    elif op == ">":
        ok = val > t
    elif op == "<":
        ok = val < t
    else:
        ok = val == t
    return {"status": "SUCCESS" if ok else "FAIL", "ok": ok, "normalized_operator": op or "=", "threshold": t}


def _derive_display_metadata(sd: dict[str, Any], *, item_no: str, item_name: str) -> dict[str, str]:
    raw_meta = _as_dict(sd.get("metadata"))
    hierarchy = _as_dict(sd.get("hierarchy"))
    chapter_code = _to_text(hierarchy.get("chapter_code") or "").strip()
    section_code = _to_text(hierarchy.get("section_code") or "").strip()
    subgroup_code = _to_text(hierarchy.get("subgroup_code") or "").strip()
    wbs_path = _to_text(raw_meta.get("wbs_path") or hierarchy.get("wbs_path") or "").strip()

    unit_project = _to_text(raw_meta.get("unit_project") or sd.get("division") or "").strip()
    if not unit_project:
        if chapter_code:
            unit_project = f"{chapter_code}章"
        else:
            head = _to_text(item_no).strip().split("-")[0] if _to_text(item_no).strip() else ""
            unit_project = f"{head}章" if head else "单位工程未命名"

    subdivision_project = _to_text(raw_meta.get("subdivision_project") or sd.get("subdivision") or "").strip()
    if not subdivision_project:
        if section_code and subgroup_code and section_code != subgroup_code:
            subdivision_project = f"{section_code}节 / {subgroup_code}"
        elif subgroup_code:
            subdivision_project = subgroup_code
        elif section_code:
            subdivision_project = section_code
        elif _to_text(item_no).strip():
            subdivision_project = _to_text(item_no).strip()
    if _to_text(item_name).strip():
        subdivision_project = f"{subdivision_project} {item_name}".strip() if subdivision_project else _to_text(item_name).strip()

    return {
        "unit_project": unit_project,
        "subdivision_project": subdivision_project,
        "wbs_path": wbs_path,
    }


def import_genesis_trip(
    *,
    sb: Any,
    project_uri: str,
    project_id: str = "",
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str = "",
    norm_context_root_uri: str = "",
    owner_uri: str = "",
    commit: bool = True,
    progress_hook: Callable[[str, int, str], None] | None = None,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    if progress_hook:
        progress_hook("parsing", 12, "解析上传文件")
    items = _parse_boq_upload(upload_file_name, upload_content)
    if progress_hook:
        progress_hook("parsed", 22, f"解析完成：识别细目 {len(items)} 条")
    root_uri = _to_text(boq_root_uri).strip() or f"{p_uri.rstrip('/')}/boq/400"
    norm_root = _to_text(norm_context_root_uri).strip() or f"{p_uri.rstrip('/')}/normContext"
    if progress_hook:
        progress_hook("writing_chain", 38, "初始化主权树并写链")
    result = initialize_boq_utxos(
        sb=sb,
        project_uri=p_uri,
        project_id=_to_text(project_id).strip() or None,
        boq_items=items,
        boq_root_uri=root_uri,
        norm_context_root_uri=norm_root,
        owner_uri=_to_text(owner_uri).strip() or f"{p_uri.rstrip('/')}/role/system/",
        source_file=upload_file_name,
        commit=bool(commit),
    )
    if progress_hook:
        total_nodes = int(result.get("total_nodes") or 0)
        progress_hook("chain_written", 78, f"写链完成：节点 {total_nodes}")

    if progress_hook:
        progress_hook("enriching_preview", 84, "补充 SPU 与模板绑定")
    for row in _as_list(result.get("preview")):
        sd = _as_dict(row.get("state_data"))
        code = _to_text(sd.get("item_no") or "").strip()
        name = _to_text(sd.get("item_name") or "").strip()
        spu = _resolve_spu_template(code, name)
        docpeg_template = _resolve_docpeg_template(code, name)
        patch = {
            **spu,
            "docpeg_template": docpeg_template,
            "genesis_amount": _to_float(sd.get("design_quantity")),
            "container": {
                "status": "Unspent",
                "stage": "Genesis Trip",
                "smu_id": code.split("-")[0] if code else "",
            },
            "trip": {
                "phase": "Genesis Trip",
                "source_file": upload_file_name,
            },
            "role": {
                "identity_mode": "Role-Trip-Container",
                "owner_uri": _to_text(result.get("owner_uri") or "").strip(),
            },
            "metadata": {
                "unit_project": _to_text(sd.get("division") or "").strip(),
                "subdivision_project": _to_text(sd.get("subdivision") or "").strip(),
                "wbs_path": _to_text(_as_dict(sd.get("hierarchy")).get("wbs_path") or "").strip(),
            },
        }
        sd.update(patch)
        row["state_data"] = sd

    enrichment_warnings: list[dict[str, Any]] = []
    if bool(commit):
        # NOTE:
        # Genesis insertion is already completed in initialize_boq_utxos(commit=True).
        # The patch below is metadata enrichment only. It must be best-effort and must not
        # fail the entire import when a downstream HTTP connection is temporarily closed.
        persist_failed_streak = 0
        for created in _as_list(result.get("created")):
            pid = _to_text(created.get("proof_id") or "").strip()
            sd = _as_dict(created.get("state_data"))
            code = _to_text(sd.get("item_no") or "").strip()
            name = _to_text(sd.get("item_name") or "").strip()
            spu = _resolve_spu_template(code, name)
            docpeg_template = _resolve_docpeg_template(code, name)
            patch = {
                **spu,
                "docpeg_template": docpeg_template,
                "genesis_amount": _to_float(sd.get("design_quantity")),
                "container": {
                    "status": "Unspent",
                    "stage": "Genesis Trip",
                    "smu_id": code.split("-")[0] if code else "",
                },
                "trip": {
                    "phase": "Genesis Trip",
                    "source_file": upload_file_name,
                },
                "role": {
                    "identity_mode": "Role-Trip-Container",
                    "owner_uri": _to_text(result.get("owner_uri") or "").strip(),
                },
                "metadata": {
                    "unit_project": _to_text(sd.get("division") or "").strip(),
                    "subdivision_project": _to_text(sd.get("subdivision") or "").strip(),
                    "wbs_path": _to_text(_as_dict(sd.get("hierarchy")).get("wbs_path") or "").strip(),
                },
            }
            # Keep response payload enriched even if persistence fails.
            merged_state = dict(sd)
            merged_state.update(patch)
            created["state_data"] = merged_state
            if not pid:
                continue
            if persist_failed_streak >= 3:
                enrichment_warnings.append(
                    {
                        "proof_id": pid,
                        "item_no": code,
                        "error": "persistence skipped after repeated connection failures",
                    }
                )
                continue
            try:
                _patch_state_data(sb, pid, patch)
                persist_failed_streak = 0
            except Exception as exc:
                persist_failed_streak += 1
                enrichment_warnings.append(
                    {
                        "proof_id": pid,
                        "item_no": code,
                        "error": f"{exc.__class__.__name__}: {exc}",
                    }
                )
        if progress_hook:
            progress_hook("enriched", 96, "后处理完成")

    if progress_hook:
        progress_hook("finalizing", 99, "正在整理导入结果")

    return {
        "ok": True,
        "phase": "Genesis Trip",
        "role": {
            "identity_mode": "Role-Trip-Container",
            "executor_role": "SYSTEM",
        },
        "trip": {
            "name": "asset_initialization",
            "source_file": upload_file_name,
            "item_count": len(items),
            "commit": bool(commit),
        },
        "container": {
            "boq_root_uri": root_uri,
            "norm_context_root_uri": norm_root,
            "hierarchy_root_hash": _to_text(result.get("hierarchy_root_hash") or "").strip(),
        },
        "enrichment_warnings": enrichment_warnings[:20],
        "result": result,
    }


def preview_genesis_tree(
    *,
    sb: Any,
    project_uri: str,
    project_id: str = "",
    upload_file_name: str,
    upload_content: bytes,
    boq_root_uri: str = "",
    norm_context_root_uri: str = "",
    owner_uri: str = "",
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    if not p_uri:
        raise HTTPException(400, "project_uri is required")
    items = _parse_boq_upload(upload_file_name, upload_content)
    root_uri = _to_text(boq_root_uri).strip() or f"{p_uri.rstrip('/')}/boq/400"
    norm_root = _to_text(norm_context_root_uri).strip() or f"{p_uri.rstrip('/')}/normContext"
    result = initialize_boq_utxos(
        sb=sb,
        project_uri=p_uri,
        project_id=_to_text(project_id).strip() or None,
        boq_items=items,
        boq_root_uri=root_uri,
        norm_context_root_uri=norm_root,
        owner_uri=_to_text(owner_uri).strip() or f"{p_uri.rstrip('/')}/role/system/",
        source_file=upload_file_name,
        commit=False,
    )
    preview_items: list[dict[str, Any]] = []
    for row in _as_list(result.get("preview")):
        sd = _as_dict(row.get("state_data"))
        if not bool(sd.get("is_leaf")):
            continue
        preview_items.append(
            {
                "boq_item_uri": _to_text(sd.get("boq_item_uri") or "").strip(),
                "item_no": _to_text(sd.get("item_no") or "").strip(),
                "item_name": _to_text(sd.get("item_name") or "").strip(),
                "unit": _to_text(sd.get("unit") or "").strip(),
                "design_quantity": _to_float(sd.get("design_quantity")),
                "approved_quantity": _to_float(sd.get("approved_quantity")),
                "settled_quantity": 0.0,
            }
        )
    return {
        "ok": True,
        "phase": "Genesis Preview",
        "project_uri": p_uri,
        "boq_root_uri": root_uri,
        "norm_context_root_uri": norm_root,
        "total_items": len(items),
        "total_nodes": int(result.get("total_nodes") or 0),
        "leaf_nodes": int(result.get("leaf_nodes") or 0),
        "hierarchy_root_hash": _to_text(result.get("hierarchy_root_hash") or "").strip(),
        "preview_items": preview_items,
    }


def get_governance_context(
    *,
    sb: Any,
    project_uri: str,
    boq_item_uri: str,
    component_type: str = "generic",
    measured_value: float | None = None,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    b_uri = _to_text(boq_item_uri).strip().rstrip("/")
    if not p_uri or not b_uri:
        raise HTTPException(400, "project_uri and boq_item_uri are required")
    row = _latest_unspent_leaf(sb, project_uri=p_uri, boq_item_uri=b_uri)
    if not row:
        raise HTTPException(404, "No unspent UTXO found for boq_item_uri")

    sd = _as_dict(row.get("state_data"))
    item_no = _to_text(sd.get("item_no") or b_uri.split("/")[-1]).strip()
    item_name = _to_text(sd.get("item_name") or "").strip()
    spu = _resolve_spu_template(item_no, item_name)
    docpeg_template = _as_dict(sd.get("docpeg_template"))
    if not docpeg_template:
        docpeg_template = _resolve_docpeg_template(item_no, item_name)
    gate_id = _to_text(sd.get("linked_gate_id") or "").strip()
    threshold_pack = {}
    if gate_id:
        try:
            threshold_pack = resolve_dynamic_threshold(sb=sb, gate_id=gate_id, context={"context": component_type})
        except Exception:
            threshold_pack = {}
    threshold_eval = _eval_threshold(
        _to_text(_as_dict(threshold_pack).get("operator") or "").strip(),
        _as_dict(threshold_pack).get("threshold"),
        measured_value,
    )

    stage = _to_text(sd.get("lifecycle_stage") or sd.get("status") or "").strip().upper()
    container = ContainerState(
        status=_container_status_from_stage(stage, _to_text(row.get("result") or "").strip()),
        stage=stage or "INITIAL",
        boq_item_uri=b_uri,
        smu_id=item_no.split("-")[0] if item_no else "",
    )

    display_metadata = _derive_display_metadata(sd, item_no=item_no, item_name=item_name)
    lab_status = _resolve_lab_status(sb=sb, project_uri=p_uri, boq_item_uri=b_uri)

    return {
        "ok": True,
        "phase": "Governance & QCGate",
        "role": {
            "executor_role": "CHIEF_ENGINEER",
            "did_gate_required": True,
        },
        "trip": {
            "name": "governance_context",
            "input_proof_id": _to_text(row.get("proof_id") or "").strip(),
        },
        "container": {
            "status": container.status,
            "stage": container.stage,
            "boq_item_uri": container.boq_item_uri,
            "smu_id": container.smu_id,
        },
        "node": {
            "proof_id": _to_text(row.get("proof_id") or "").strip(),
            "proof_type": _to_text(row.get("proof_type") or "").strip(),
            "result": _to_text(row.get("result") or "").strip(),
            "item_no": item_no,
            "item_name": item_name,
            "unit": _to_text(sd.get("unit") or "").strip(),
            "design_quantity": _to_float(sd.get("design_quantity")),
            "approved_quantity": _to_float(sd.get("approved_quantity")),
            "linked_gate_id": gate_id,
            "linked_spec_uri": _to_text(sd.get("linked_spec_uri") or "").strip(),
            "docpeg_template": docpeg_template,
            "metadata": display_metadata,
            "lab_status": lab_status,
        },
        "spu": spu,
        "threshold": {
            "component_type": component_type,
            **_as_dict(threshold_pack),
            "evaluation": threshold_eval,
        },
    }


def execute_smu_trip(
    *,
    sb: Any,
    project_uri: str,
    input_proof_id: str,
    executor_uri: str,
    executor_did: str,
    executor_role: str,
    component_type: str,
    measurement: dict[str, Any],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    evidence_hashes: list[str],
    credentials_vc: list[dict[str, Any]],
    force_reject: bool = False,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    in_id = _to_text(input_proof_id).strip()
    if not p_uri or not in_id:
        raise HTTPException(400, "project_uri and input_proof_id are required")

    input_row = ProofUTXOEngine(sb).get_by_id(in_id)
    if not input_row:
        raise HTTPException(404, "input_proof_id not found")
    item_uri = _to_text(_as_dict(input_row.get("state_data")).get("boq_item_uri") or input_row.get("segment_uri") or "").strip()
    if not item_uri:
        raise HTTPException(409, "input proof has no boq_item_uri")

    snappeg_payload = {
        "project_uri": p_uri,
        "input_proof_id": in_id,
        "boq_item_uri": item_uri,
        "measurement": measurement,
        "geo_location": geo_location,
        "server_timestamp_proof": server_timestamp_proof,
        "executor_did": executor_did,
        "evidence_hashes": evidence_hashes,
    }
    snappeg_hash = _sha(snappeg_payload)

    override_result = "FAIL" if bool(force_reject) else ""
    qc = execute_triprole_action(
        sb=sb,
        body={
            "action": "quality.check",
            "input_proof_id": in_id,
            "executor_uri": executor_uri,
            "executor_did": executor_did,
            "executor_role": executor_role,
            "boq_item_uri": item_uri,
            **({"result": override_result} if override_result else {}),
            "payload": {
                "component_type": component_type,
                "measurement": measurement,
                "snappeg_payload_hash": snappeg_hash,
            },
            "credentials_vc": credentials_vc,
            "geo_location": geo_location,
            "server_timestamp_proof": server_timestamp_proof,
        },
    )

    current = dict(qc)
    if (not force_reject) and _to_text(qc.get("result") or "").strip().upper() == "PASS":
        current = execute_triprole_action(
            sb=sb,
            body={
                "action": "measure.record",
                "input_proof_id": _to_text(qc.get("output_proof_id") or "").strip(),
                "executor_uri": executor_uri,
                "executor_did": executor_did,
                "executor_role": executor_role,
                "boq_item_uri": item_uri,
                "payload": {
                    "component_type": component_type,
                    "measurement": measurement,
                    "snappeg_payload_hash": snappeg_hash,
                },
                "credentials_vc": credentials_vc,
                "geo_location": geo_location,
                "server_timestamp_proof": server_timestamp_proof,
            },
        )

    out_id = _to_text(current.get("output_proof_id") or "").strip()
    if out_id:
        patched = _patch_state_data(
            sb,
            out_id,
            {
                "snappeg": {
                    "hash": snappeg_hash,
                    "evidence_hashes": evidence_hashes,
                    "geo_location": geo_location,
                    "server_timestamp_proof": server_timestamp_proof,
                    "executor_did": executor_did,
                    "captured_at": _utc_iso(),
                },
                "container": {
                    "status": "Reviewing",
                    "stage": "Execution & SnapPeg",
                    "boq_item_uri": item_uri,
                    "smu_id": item_uri.rstrip("/").split("/")[-1].split("-")[0],
                },
                "trip": {
                    "phase": "Execution & SnapPeg",
                    "measurement": measurement,
                },
            },
        )
        if patched:
            current["state_data"] = patched

    return {
        "ok": True,
        "phase": "Execution & SnapPeg",
        "role": {
            "executor_uri": executor_uri,
            "executor_did": executor_did,
            "executor_role": executor_role,
        },
        "trip": {
            "name": "execution_submit",
            "quality_check_output_proof_id": _to_text(qc.get("output_proof_id") or "").strip(),
            "output_proof_id": out_id,
            "result": _to_text(current.get("result") or "").strip(),
            "snappeg_hash": snappeg_hash,
            "force_reject": bool(force_reject),
        },
        "container": {
            "status": "Reviewing",
            "stage": "Execution & SnapPeg",
            "boq_item_uri": item_uri,
            "smu_id": item_uri.rstrip("/").split("/")[-1].split("-")[0],
        },
        "raw": current,
    }


def sign_smu_approval(
    *,
    sb: Any,
    input_proof_id: str,
    boq_item_uri: str,
    supervisor_executor_uri: str,
    supervisor_did: str,
    contractor_did: str,
    owner_did: str,
    signer_metadata: dict[str, Any],
    geo_location: dict[str, Any],
    server_timestamp_proof: dict[str, Any],
    auto_docpeg: bool = True,
    verify_base_url: str = "https://verify.qcspec.com",
    template_path: str = "",
) -> dict[str, Any]:
    in_id = _to_text(input_proof_id).strip()
    item_uri = _to_text(boq_item_uri).strip()
    if not in_id or not item_uri:
        raise HTTPException(400, "input_proof_id and boq_item_uri are required")
    now = _utc_iso()
    input_row = ProofUTXOEngine(sb).get_by_id(in_id) or {}
    input_sd = _as_dict(_as_dict(input_row).get("state_data"))
    input_item_no = _to_text(input_sd.get("item_no") or item_uri.rstrip("/").split("/")[-1]).strip()
    input_item_name = _to_text(input_sd.get("item_name") or "").strip()
    template_binding = _as_dict(input_sd.get("docpeg_template"))
    if not template_binding:
        template_binding = _resolve_docpeg_template(input_item_no, input_item_name)
    auto_template_path = _to_text(template_binding.get("template_path") or "").strip()
    selected_template_path = _to_text(template_path).strip() or auto_template_path

    signatures: list[dict[str, Any]] = []
    for role, did in (
        ("contractor", contractor_did),
        ("supervisor", supervisor_did),
        ("owner", owner_did),
    ):
        normalized_did = _to_text(did).strip()
        if not normalized_did.startswith("did:"):
            raise HTTPException(400, f"{role}_did must start with did:")
        sig = hashlib.sha256(f"{in_id}|{normalized_did}|{role}|{now}".encode("utf-8")).hexdigest()
        signatures.append({"role": role, "did": normalized_did, "signature_hash": sig, "signed_at": now})

    biometric = _as_dict(signer_metadata)
    if not biometric:
        biometric = {
            "mode": "liveness",
            "passed": True,
            "checked_at": now,
            "device": "mobile",
            "signers": [
                {"role": "contractor", "did": contractor_did, "biometric_ok": True},
                {"role": "supervisor", "did": supervisor_did, "biometric_ok": True},
                {"role": "owner", "did": owner_did, "biometric_ok": True},
            ],
        }

    settle = execute_triprole_action(
        sb=sb,
        body={
            "action": "settlement.confirm",
            "input_proof_id": in_id,
            "executor_uri": supervisor_executor_uri,
            "executor_did": supervisor_did,
            "executor_role": "SUPERVISOR",
            "boq_item_uri": item_uri,
            "result": "PASS",
            "signatures": signatures,
            "consensus_signatures": signatures,
            "signer_metadata": biometric,
            "payload": {
                "approved_from": "SMU_APPROVAL_PANEL",
                "status_target": "Approved",
            },
            "geo_location": geo_location,
            "server_timestamp_proof": server_timestamp_proof,
        },
    )
    out_id = _to_text(settle.get("output_proof_id") or "").strip()
    lineage_total_hash = _to_text(_as_dict(settle.get("provenance")).get("total_proof_hash") or "").strip()

    docpeg: dict[str, Any] = {}
    if auto_docpeg and _to_text(settle.get("result") or "").strip().upper() == "PASS":
        package = build_docfinal_package_for_boq(
            boq_item_uri=item_uri,
            sb=sb,
            project_meta={},
            verify_base_url=verify_base_url,
            template_path=selected_template_path or None,
            apply_asset_transfer=False,
        )
        pdf_bytes = package.get("pdf_bytes") or b""
        preview_bytes = bytes(pdf_bytes[:1_800_000])
        docpeg = {
            "verify_uri": _to_text(_as_dict(package.get("context")).get("verify_uri") or "").strip(),
            "artifact_uri": _to_text(_as_dict(package.get("context")).get("artifact_uri") or "").strip(),
            "gitpeg_anchor": _to_text(_as_dict(package.get("context")).get("gitpeg_anchor") or "").strip(),
            "pdf_preview_b64": base64.b64encode(preview_bytes).decode("ascii") if preview_bytes else "",
            "pdf_preview_truncated": len(preview_bytes) < len(pdf_bytes),
            "template_binding": template_binding,
            "selected_template_path": selected_template_path or _to_text(template_binding.get("fallback_template") or "").strip(),
            "context": package.get("context") or {},
        }

    if out_id:
        _patch_state_data(
            sb,
            out_id,
            {
                "container": {
                    "status": "Approved",
                    "stage": "OrdoSign & DID",
                    "boq_item_uri": item_uri,
                    "smu_id": item_uri.rstrip("/").split("/")[-1].split("-")[0],
                },
                "trip": {
                    "phase": "OrdoSign & DID",
                    "consensus": "complete",
                },
                "total_proof_hash": lineage_total_hash,
            },
        )

    return {
        "ok": True,
        "phase": "OrdoSign & DID",
        "role": {
            "executor_uri": supervisor_executor_uri,
            "executor_did": supervisor_did,
            "executor_role": "SUPERVISOR",
        },
        "trip": {
            "name": "approval_signature",
            "input_proof_id": in_id,
            "output_proof_id": out_id,
            "result": _to_text(settle.get("result") or "").strip(),
            "total_proof_hash": lineage_total_hash,
        },
        "container": {
            "status": "Approved",
            "stage": "OrdoSign & DID",
            "boq_item_uri": item_uri,
            "smu_id": item_uri.rstrip("/").split("/")[-1].split("-")[0],
        },
        "docpeg": docpeg,
        "raw": settle,
    }


def validate_logic(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    s_id = _to_text(smu_id).strip()
    if not p_uri or not s_id:
        raise HTTPException(400, "project_uri and smu_id are required")
    rows = _boq_rows(sb, project_uri=p_uri, boq_item_uri="", only_unspent=False, limit=50000)
    scoped: list[dict[str, Any]] = []
    for row in rows:
        seg = _to_text(row.get("segment_uri") or "").strip()
        if f"/boq/" not in seg:
            continue
        code = seg.rstrip("/").split("/")[-1]
        if code.startswith(s_id):
            scoped.append(row)
    if not scoped:
        raise HTTPException(404, f"No proof rows found under smu_id={s_id}")

    missing_geo = 0
    missing_ntp = 0
    fail_count = 0
    low_trust = 0
    issues: list[dict[str, Any]] = []
    for row in scoped:
        pid = _to_text(row.get("proof_id") or "").strip()
        result = _to_text(row.get("result") or "").strip().upper()
        sd = _as_dict(row.get("state_data"))
        geo = _as_dict(sd.get("geo_location"))
        ntp = _as_dict(sd.get("server_timestamp_proof"))
        if not geo or (_to_float(geo.get("lat")) is None or _to_float(geo.get("lng")) is None):
            missing_geo += 1
            issues.append({"proof_id": pid, "severity": "medium", "issue": "missing_geo_location"})
        if not ntp or not _to_text(ntp.get("ntp_server") or ntp.get("proof_hash") or "").strip():
            missing_ntp += 1
            issues.append({"proof_id": pid, "severity": "medium", "issue": "missing_ntp_proof"})
        if result == "FAIL":
            fail_count += 1
            issues.append({"proof_id": pid, "severity": "high", "issue": "fail_result_in_chain"})
        trust = _to_text(_as_dict(sd.get("geo_compliance")).get("trust_level") or "").strip().upper()
        if trust in {"LOW", "OUTSIDE"}:
            low_trust += 1
            issues.append({"proof_id": pid, "severity": "high", "issue": "low_geo_trust"})

    total = len(scoped)
    risk_score = 100.0
    if total > 0:
        risk_score -= 35.0 * (fail_count / total)
        risk_score -= 25.0 * (low_trust / total)
        risk_score -= 20.0 * (missing_geo / total)
        risk_score -= 20.0 * (missing_ntp / total)
    risk_score = max(0.0, min(100.0, round(risk_score, 2)))

    return {
        "ok": True,
        "phase": "SMU & Risk Audit",
        "smu_id": s_id,
        "project_uri": p_uri,
        "summary": {
            "total_proofs": total,
            "missing_geo": missing_geo,
            "missing_ntp": missing_ntp,
            "fail_count": fail_count,
            "low_trust_count": low_trust,
            "risk_score": risk_score,
        },
        "issues": issues[:500],
        "logic_hash": _sha(
            {
                "project_uri": p_uri,
                "smu_id": s_id,
                "summary": {
                    "total_proofs": total,
                    "missing_geo": missing_geo,
                    "missing_ntp": missing_ntp,
                    "fail_count": fail_count,
                    "low_trust_count": low_trust,
                    "risk_score": risk_score,
                },
            }
        ),
    }


def freeze_smu(
    *,
    sb: Any,
    project_uri: str,
    smu_id: str,
    executor_uri: str,
    min_risk_score: float = 60.0,
) -> dict[str, Any]:
    p_uri = _to_text(project_uri).strip()
    s_id = _to_text(smu_id).strip()
    if not p_uri or not s_id:
        raise HTTPException(400, "project_uri and smu_id are required")
    audit = validate_logic(sb=sb, project_uri=p_uri, smu_id=s_id)
    risk_score = _to_float(_as_dict(audit.get("summary")).get("risk_score")) or 0.0
    merkle = build_unit_merkle_snapshot(
        sb=sb,
        project_uri=p_uri,
        unit_code=s_id,
        proof_id="",
        max_rows=50000,
    )
    total_proof_hash = _to_text(merkle.get("unit_root_hash") or "").strip()
    if not total_proof_hash:
        raise HTTPException(409, "unit_root_hash is empty, cannot freeze")
    status = "PASS" if risk_score >= float(min_risk_score) else "FAIL"
    freeze_seed = _sha({"project_uri": p_uri, "smu_id": s_id, "root": total_proof_hash, "ts": _utc_iso()})[:18].upper()
    freeze_proof_id = f"GP-SMU-{freeze_seed}"
    state_data = {
        "asset_type": "smu_freeze",
        "status": "SMU_FROZEN" if status == "PASS" else "SMU_FREEZE_REJECTED",
        "lifecycle_stage": "SMU_FREEZE",
        "smu_id": s_id,
        "risk_score": risk_score,
        "risk_logic_hash": _to_text(audit.get("logic_hash") or "").strip(),
        "audit_summary": audit.get("summary") or {},
        "unit_merkle_root": total_proof_hash,
        "project_root_hash": _to_text(merkle.get("project_root_hash") or merkle.get("global_project_fingerprint") or "").strip(),
        "leaf_count": merkle.get("leaf_count"),
        "total_proof_hash": total_proof_hash,
        "container": {
            "status": "Frozen" if status == "PASS" else "Blocked",
            "stage": "SMU & Risk Audit",
            "boq_item_uri": "",
            "smu_id": s_id,
        },
        "trip": {
            "phase": "SMU.freeze",
            "pushed_to_settlement_dashboard": status == "PASS",
        },
        "role": {
            "executor_uri": executor_uri,
            "executor_role": "OWNER",
        },
        "settlement_packet": {
            "smu_id": s_id,
            "project_uri": p_uri,
            "total_proof_hash": total_proof_hash,
            "risk_score": risk_score,
            "status": status,
            "created_at": _utc_iso(),
        },
    }
    row = ProofUTXOEngine(sb).create(
        proof_id=freeze_proof_id,
        owner_uri=_to_text(executor_uri).strip() or "v://executor/owner/system/",
        project_uri=p_uri,
        project_id=None,
        segment_uri=f"{p_uri.rstrip('/')}/smu/{s_id}",
        proof_type="smu_freeze",
        result=status,
        state_data=state_data,
        conditions=[],
        parent_proof_id=None,
        norm_uri="v://norm/CoordOS/SMU/1.0#freeze",
        signer_uri=_to_text(executor_uri).strip() or "v://executor/owner/system/",
        signer_role="OWNER",
        gitpeg_anchor=None,
        anchor_config=None,
    )
    return {
        "ok": True,
        "phase": "SMU & Risk Audit",
        "role": {
            "executor_uri": executor_uri,
            "executor_role": "OWNER",
        },
        "trip": {
            "name": "SMU.freeze()",
            "result": status,
            "risk_score": risk_score,
            "min_risk_score": min_risk_score,
        },
        "container": {
            "status": "Frozen" if status == "PASS" else "Blocked",
            "stage": "SMU & Risk Audit",
            "smu_id": s_id,
        },
        "freeze_proof_id": _to_text(row.get("proof_id") or "").strip(),
        "total_proof_hash": total_proof_hash,
        "audit": audit,
        "merkle": {
            "unit_root_hash": _to_text(merkle.get("unit_root_hash") or "").strip(),
            "project_root_hash": _to_text(merkle.get("project_root_hash") or merkle.get("global_project_fingerprint") or "").strip(),
            "leaf_count": merkle.get("leaf_count"),
        },
        "settlement_packet": _as_dict(state_data.get("settlement_packet")),
    }
