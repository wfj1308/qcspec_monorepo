"""Compile SpecIR norm definitions into process-chain step configs."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from services.api.domain.specir.runtime.registry import specir_is_ready


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _normalize_token(value: Any) -> str:
    token = _to_text(value).strip().lower()
    token = token.replace("-", "_").replace("/", "_")
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"[^0-9a-z_]+", "", token)
    return token


def _canonical_component_type(component_type: str, chain_kind: str = "") -> str:
    aliases = {
        "drilled_pile": "drilled_pile",
        "drilledpile": "drilled_pile",
        "drilled_pile_chain": "drilled_pile",
        "drilledpiles": "drilled_pile",
        "pile": "drilled_pile",
        "pilefoundation": "drilled_pile",
        "prestressed_beam": "prestressed_beam",
        "prestressedbeam": "prestressed_beam",
        "beam": "prestressed_beam",
        "subgrade": "subgrade",
        "roadbed": "subgrade",
        "tunnel_lining": "tunnel_lining",
        "tunnellining": "tunnel_lining",
        "tunnel": "tunnel_lining",
        "pavement": "pavement",
    }
    for raw in (component_type, chain_kind):
        token = _normalize_token(raw)
        if token in aliases:
            return aliases[token]
    return "drilled_pile"


@dataclass(slots=True, frozen=True)
class _StepDef:
    order: int
    step_id: str
    name: str
    table_code: str
    section_code: str
    form_uri: str
    normref_uri: str


@dataclass(slots=True, frozen=True)
class _ChainDef:
    component_type: str
    spec_uri: str
    chapter: str
    steps: tuple[_StepDef, ...]


_BUILTIN_CHAIN_DEFS: dict[str, _ChainDef] = {
    "drilled_pile": _ChainDef(
        component_type="drilled_pile",
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        chapter="第7章 桩基础工程",
        steps=(
            _StepDef(1, "pile-prepare-01", "护筒埋设（桥施2表）", "桥施2表", "7.1.1", "v://normref.com/doc-type/bridge/pile-casing-check@v1", "v://normref.com/qc/pile-foundation@v1"),
            _StepDef(2, "pile-hole-02", "成孔检查（桥施7表）", "桥施7表", "7.1.2", "v://normref.com/doc-type/bridge/pile-hole-check@v1", "v://normref.com/qc/pile-foundation@v1"),
            _StepDef(3, "pile-rebar-03", "钢筋笼安装（桥施11表）", "桥施11表", "7.1.3", "v://normref.com/doc-type/bridge/rebar-cage-install@v1", "v://normref.com/qc/rebar-processing@v1"),
            _StepDef(4, "pile-pour-04", "水下混凝土灌注（桥施9表）", "桥施9表", "7.1.4", "v://normref.com/doc-type/bridge/concrete-pour@v1", "v://normref.com/qc/concrete-compressive-test@v1"),
            _StepDef(5, "pile-acceptance-05", "成桩验收（桥施13表）", "桥施13表", "7.1.5", "v://normref.com/doc-type/bridge/pile-acceptance@v1", "v://normref.com/qc/pile-foundation@v1"),
            _StepDef(6, "pile-subitem-06", "成品验收（桥施64表）", "桥施64表", "7.1.6", "v://normref.com/doc-type/bridge/final-acceptance@v1", "v://normref.com/schema/qc-v1"),
        ),
    ),
    "prestressed_beam": _ChainDef(
        component_type="prestressed_beam",
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        chapter="第8章 预应力混凝土梁",
        steps=(
            _StepDef(1, "beam-formwork-01", "模板与支架检查", "梁施1表", "8.1.1", "v://normref.com/doc-type/bridge/beam-formwork-check@v1", "v://normref.com/qc/beam-construction@v1"),
            _StepDef(2, "beam-rebar-02", "钢筋安装检查", "梁施2表", "8.1.2", "v://normref.com/doc-type/bridge/beam-rebar-check@v1", "v://normref.com/qc/rebar-processing@v1"),
            _StepDef(3, "beam-duct-03", "预应力孔道检查", "梁施3表", "8.1.3", "v://normref.com/doc-type/bridge/beam-duct-check@v1", "v://normref.com/qc/beam-construction@v1"),
            _StepDef(4, "beam-concrete-04", "混凝土浇筑检查", "梁施4表", "8.1.4", "v://normref.com/doc-type/bridge/beam-concrete-check@v1", "v://normref.com/qc/concrete-compressive-test@v1"),
            _StepDef(5, "beam-curing-05", "养护与拆模检查", "梁施5表", "8.1.5", "v://normref.com/doc-type/bridge/beam-curing-check@v1", "v://normref.com/qc/beam-construction@v1"),
            _StepDef(6, "beam-tension-06", "张拉与压浆检查", "梁施6表", "8.1.6", "v://normref.com/doc-type/bridge/beam-tension-check@v1", "v://normref.com/qc/beam-construction@v1"),
            _StepDef(7, "beam-erect-07", "架设安装检查", "梁施7表", "8.1.7", "v://normref.com/doc-type/bridge/beam-erection-check@v1", "v://normref.com/qc/bridge-installation@v1"),
            _StepDef(8, "beam-final-08", "分项验收", "梁施8表", "8.1.8", "v://normref.com/doc-type/bridge/beam-final-acceptance@v1", "v://normref.com/schema/qc-v1"),
        ),
    ),
    "subgrade": _ChainDef(
        component_type="subgrade",
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        chapter="第3章 路基工程",
        steps=(
            _StepDef(1, "subgrade-foundation-01", "地基处理检查", "路基1表", "3.1.1", "v://normref.com/doc-type/highway/subgrade-foundation-check@v1", "v://normref.com/qc/subgrade@v1"),
            _StepDef(2, "subgrade-fill-02", "填筑材料检查", "路基2表", "3.1.2", "v://normref.com/doc-type/highway/subgrade-fill-check@v1", "v://normref.com/qc/subgrade@v1"),
            _StepDef(3, "subgrade-compaction-03", "压实度检查", "路基3表", "3.1.3", "v://normref.com/doc-type/highway/subgrade-compaction-check@v1", "v://normref.com/qc/subgrade@v1"),
            _StepDef(4, "subgrade-shape-04", "线形与高程检查", "路基4表", "3.1.4", "v://normref.com/doc-type/highway/subgrade-shape-check@v1", "v://normref.com/qc/subgrade@v1"),
            _StepDef(5, "subgrade-acceptance-05", "路基分项验收", "路基5表", "3.1.5", "v://normref.com/doc-type/highway/subgrade-acceptance@v1", "v://normref.com/schema/qc-v1"),
        ),
    ),
    "tunnel_lining": _ChainDef(
        component_type="tunnel_lining",
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        chapter="第11章 隧道工程",
        steps=(
            _StepDef(1, "tunnel-excavation-01", "开挖断面检查", "隧施1表", "11.1.1", "v://normref.com/doc-type/tunnel/excavation-check@v1", "v://normref.com/qc/tunnel@v1"),
            _StepDef(2, "tunnel-support-02", "初期支护检查", "隧施2表", "11.1.2", "v://normref.com/doc-type/tunnel/support-check@v1", "v://normref.com/qc/tunnel@v1"),
            _StepDef(3, "tunnel-waterproof-03", "防水层检查", "隧施3表", "11.1.3", "v://normref.com/doc-type/tunnel/waterproof-check@v1", "v://normref.com/qc/tunnel@v1"),
            _StepDef(4, "tunnel-rebar-04", "衬砌钢筋检查", "隧施4表", "11.1.4", "v://normref.com/doc-type/tunnel/rebar-check@v1", "v://normref.com/qc/rebar-processing@v1"),
            _StepDef(5, "tunnel-concrete-05", "二衬浇筑检查", "隧施5表", "11.1.5", "v://normref.com/doc-type/tunnel/concrete-check@v1", "v://normref.com/qc/concrete-compressive-test@v1"),
            _StepDef(6, "tunnel-quality-06", "衬砌质量评定", "隧施6表", "11.1.6", "v://normref.com/doc-type/tunnel/quality-eval@v1", "v://normref.com/qc/tunnel@v1"),
            _StepDef(7, "tunnel-acceptance-07", "隧道分项验收", "隧施7表", "11.1.7", "v://normref.com/doc-type/tunnel/acceptance@v1", "v://normref.com/schema/qc-v1"),
        ),
    ),
    "pavement": _ChainDef(
        component_type="pavement",
        spec_uri="v://normref.com/std/JTG-F80-1-2017",
        chapter="第10章 路面工程",
        steps=(
            _StepDef(1, "pavement-base-01", "基层验收", "路面1表", "10.1.1", "v://normref.com/doc-type/highway/pavement-base-check@v1", "v://normref.com/qc/pavement@v1"),
            _StepDef(2, "pavement-prime-02", "透层粘层检查", "路面2表", "10.1.2", "v://normref.com/doc-type/highway/pavement-prime-check@v1", "v://normref.com/qc/pavement@v1"),
            _StepDef(3, "pavement-mix-03", "混合料生产检查", "路面3表", "10.1.3", "v://normref.com/doc-type/highway/pavement-mix-check@v1", "v://normref.com/qc/pavement@v1"),
            _StepDef(4, "pavement-lay-04", "摊铺碾压检查", "路面4表", "10.1.4", "v://normref.com/doc-type/highway/pavement-lay-check@v1", "v://normref.com/qc/pavement@v1"),
            _StepDef(5, "pavement-index-05", "平整度与压实度检查", "路面5表", "10.1.5", "v://normref.com/doc-type/highway/pavement-index-check@v1", "v://normref.com/qc/pavement@v1"),
            _StepDef(6, "pavement-acceptance-06", "路面分项验收", "路面6表", "10.1.6", "v://normref.com/doc-type/highway/pavement-acceptance@v1", "v://normref.com/schema/qc-v1"),
        ),
    ),
}


def _default_chain_def(*, component_type: str) -> _ChainDef:
    return _BUILTIN_CHAIN_DEFS.get(component_type) or _BUILTIN_CHAIN_DEFS["drilled_pile"]


def _build_steps_from_chain_def(
    chain_def: _ChainDef,
    *,
    component_uri: str = "",
    boq_item_ref: str = "",
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    previous_table = ""
    for row in chain_def.steps:
        pre_conditions = [previous_table] if previous_table else []
        step = {
            "step_id": row.step_id,
            "order": row.order,
            "name": row.name,
            "required_tables": [row.table_code],
            "pre_conditions": pre_conditions,
            "normref_uris": [row.normref_uri, row.form_uri],
            "next_steps": [],
            "boq_item_ref": boq_item_ref,
            "component_uri": component_uri,
            "section_code": row.section_code,
            "source_spec": chain_def.spec_uri,
            "chapter": chain_def.chapter,
            "auto_generated": True,
        }
        steps.append(step)
        previous_table = row.table_code
    for idx in range(0, len(steps) - 1):
        steps[idx]["next_steps"] = [steps[idx + 1]["step_id"]]
    return steps


def _load_registry_process_steps(
    *,
    sb: Any,
    spec_uri: str,
    chapter: str,
    component_type: str,
) -> list[dict[str, Any]]:
    if sb is None or not specir_is_ready(sb=sb):
        return []
    try:
        rows = (
            sb.table("specir_objects")
            .select("uri,kind,title,content,metadata,status")
            .in_("kind", ["process_step", "norm_form", "doc_form", "qc_form", "form"])
            .eq("status", "active")
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        return []

    wanted_spec = _to_text(spec_uri).strip().lower()
    wanted_chapter = _to_text(chapter).strip().lower()
    wanted_component = _canonical_component_type(component_type)

    parsed: list[dict[str, Any]] = []
    for raw in rows:
        row = _as_dict(raw)
        content = _as_dict(row.get("content"))
        metadata = _as_dict(row.get("metadata"))
        merged = {**metadata, **content}

        row_spec = _to_text(merged.get("spec_uri") or merged.get("source_spec") or "").strip().lower()
        if wanted_spec and row_spec and row_spec != wanted_spec:
            continue
        row_component = _canonical_component_type(
            _to_text(merged.get("component_type") or merged.get("chain_kind") or ""),
            _to_text(merged.get("chain_kind") or ""),
        )
        if row_component != wanted_component:
            continue
        row_chapter = _to_text(merged.get("chapter") or "").strip().lower()
        if wanted_chapter and row_chapter and row_chapter != wanted_chapter:
            continue

        required_tables = [
            _to_text(x).strip()
            for x in _as_list(merged.get("required_tables") or merged.get("tables") or merged.get("table_codes"))
            if _to_text(x).strip()
        ]
        if not required_tables:
            candidate = _to_text(merged.get("table_code") or merged.get("form_code") or merged.get("table") or "").strip()
            if candidate:
                required_tables = [candidate]
        if not required_tables:
            continue

        order_raw = merged.get("order")
        try:
            order = int(order_raw)
        except Exception:
            order = 0

        parsed.append(
            {
                "step_id": _to_text(merged.get("step_id") or "").strip(),
                "order": order,
                "name": _to_text(merged.get("name") or row.get("title") or "").strip(),
                "required_tables": required_tables,
                "normref_uris": [
                    _to_text(x).strip()
                    for x in _as_list(merged.get("normref_uris") or merged.get("norm_refs") or [row.get("uri")])
                    if _to_text(x).strip()
                ],
                "section_code": _to_text(merged.get("section_code") or "").strip(),
            }
        )

    if not parsed:
        return []

    parsed.sort(key=lambda item: (int(item.get("order") or 0), _to_text(item.get("section_code") or ""), _to_text(item.get("step_id") or "")))

    steps: list[dict[str, Any]] = []
    previous_table = ""
    for idx, item in enumerate(parsed, start=1):
        step_id = _to_text(item.get("step_id")).strip() or f"{wanted_component}-step-{idx:02d}"
        name = _to_text(item.get("name")).strip() or f"Step {idx}"
        required_tables = [
            _to_text(x).strip() for x in _as_list(item.get("required_tables")) if _to_text(x).strip()
        ]
        if not required_tables:
            continue
        pre_conditions = [previous_table] if previous_table else []
        steps.append(
            {
                "step_id": step_id,
                "order": idx,
                "name": name,
                "required_tables": required_tables,
                "pre_conditions": pre_conditions,
                "normref_uris": [
                    _to_text(x).strip() for x in _as_list(item.get("normref_uris")) if _to_text(x).strip()
                ],
                "next_steps": [],
                "section_code": _to_text(item.get("section_code") or "").strip(),
                "source_spec": spec_uri,
                "chapter": chapter,
                "auto_generated": True,
            }
        )
        previous_table = required_tables[0]
    for idx in range(0, len(steps) - 1):
        steps[idx]["next_steps"] = [steps[idx + 1]["step_id"]]
    return steps


class SpecIRCompiler:
    """Compile spec chapter sequences into executable process-chain steps."""

    def __init__(self, *, sb: Any | None = None) -> None:
        self._sb = sb

    def compile_to_process_chain(
        self,
        *,
        spec_uri: str,
        component_type: str,
        chapter: str = "",
        chain_kind: str = "",
        component_uri: str = "",
        boq_item_ref: str = "",
    ) -> dict[str, Any]:
        canonical = _canonical_component_type(component_type, chain_kind)
        chain_def = _default_chain_def(component_type=canonical)
        normalized_spec_uri = _to_text(spec_uri).strip() or chain_def.spec_uri
        normalized_chapter = _to_text(chapter).strip() or chain_def.chapter

        registry_steps = _load_registry_process_steps(
            sb=self._sb,
            spec_uri=normalized_spec_uri,
            chapter=normalized_chapter,
            component_type=canonical,
        )
        if registry_steps:
            steps = [
                {
                    **row,
                    "component_uri": component_uri,
                    "boq_item_ref": boq_item_ref,
                }
                for row in registry_steps
            ]
            source = "registry"
        else:
            steps = _build_steps_from_chain_def(
                chain_def,
                component_uri=component_uri,
                boq_item_ref=boq_item_ref,
            )
            source = "builtin"

        return {
            "ok": True,
            "source": source,
            "spec_uri": normalized_spec_uri,
            "chapter": normalized_chapter,
            "component_type": canonical,
            "chain_kind": _to_text(chain_kind).strip() or canonical,
            "auto_generated": True,
            "steps": steps,
        }


def compile_specir_process_chain(
    *,
    sb: Any | None,
    spec_uri: str,
    component_type: str,
    chapter: str = "",
    chain_kind: str = "",
    component_uri: str = "",
    boq_item_ref: str = "",
) -> dict[str, Any]:
    return SpecIRCompiler(sb=sb).compile_to_process_chain(
        spec_uri=spec_uri,
        component_type=component_type,
        chapter=chapter,
        chain_kind=chain_kind,
        component_uri=component_uri,
        boq_item_ref=boq_item_ref,
    )


__all__ = ["SpecIRCompiler", "compile_specir_process_chain"]
