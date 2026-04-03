"""
ComponentUTXO Beam-L3 demo (offline, no external dependency).

Flow:
1) Build ComponentUTXO payload (multi-BOQ + multi-material UTXO inputs)
2) Run quality.check immutable transition
3) Validate per-material conservation
4) Build DocPeg component bundle (docx + verify_uri + proof hash)
5) Emit summary JSON for acceptance archiving
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.domain.execution.triprole_component_utxo import (
    build_component_utxo_verification,
)


def _print(message: str) -> None:
    print(message)


def _payload_beam_l3(project_uri: str) -> dict[str, Any]:
    base = project_uri.rstrip("/")
    return {
        "component_id": "MAIN-BEAM-L3",
        "component_uri": f"{base}/component/MAIN-BEAM-L3",
        "project_uri": base,
        "kind": "precast_beam",
        "boq_items": [
            {
                "item_id": "403-1-2",
                "description": "Rebar fabrication and installation",
                "unit": "kg",
                "qty": 1885,
                "unit_price": 5.8,
                "spec_uri": "v://norm/JTG/bridge/rebar_installation",
            },
            {
                "item_id": "404-2-1",
                "description": "Concrete casting",
                "unit": "m3",
                "qty": 23.6,
                "unit_price": 460.0,
                "spec_uri": "v://norm/JTG/bridge/concrete_casting",
            },
        ],
        "bom": [
            {"material_role": "steel", "qty": 1885, "tolerance_ratio": 0.03},
            {"material_role": "concrete", "qty": 23.6, "tolerance_ratio": 0.03},
        ],
        "material_inputs": [
            {
                "utxo_id": "UTXO-STEEL-HRB400-PHI20-001",
                "material_role": "steel",
                "qty": 1200,
                "proof_hash": "a" * 64,
                "boq_item_id": "403-1-2",
            },
            {
                "utxo_id": "UTXO-STEEL-HRB400-PHI16-001",
                "material_role": "steel",
                "qty": 685,
                "proof_hash": "b" * 64,
                "boq_item_id": "403-1-2",
            },
            {
                "utxo_id": "UTXO-CONCRETE-C40-001",
                "material_role": "concrete",
                "qty": 23.6,
                "proof_hash": "c" * 64,
                "boq_item_id": "404-2-1",
            },
        ],
        "trip_id": "TRIP-BEAM-L3-QC-001",
        "trip_action": "quality.check",
        "trip_executor_uri": f"{base}/role/supervisor/mobile/inspector-li/",
    }


def _load_payload_from_file(path: str | Path) -> dict[str, Any]:
    payload_path = Path(path).expanduser().resolve()
    data = json.loads(payload_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"payload file must be a JSON object: {payload_path}")
    return data


def _resolve_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload_file:
        payload = _load_payload_from_file(args.payload_file)
        if "project_uri" not in payload or not str(payload.get("project_uri") or "").strip():
            payload["project_uri"] = args.project_uri
        return payload
    return _payload_beam_l3(args.project_uri)


def _required_payload(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"payload missing required field: {key}")
    return value


def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = _resolve_payload(args)

    verification = build_component_utxo_verification(
        sb=object(),
        component_id=str(_required_payload(payload, "component_id")),
        component_uri=str(_required_payload(payload, "component_uri")),
        project_uri=str(_required_payload(payload, "project_uri")),
        kind=str(payload.get("kind") or "component"),
        boq_items=list(payload.get("boq_items") or []),
        bom=payload.get("bom"),
        material_inputs=list(payload.get("material_inputs") or []),
        trip_id=str(payload.get("trip_id") or ""),
        trip_action=str(payload.get("trip_action") or ""),
        trip_executor_uri=str(payload.get("trip_executor_uri") or ""),
        render_docpeg=not args.skip_docpeg,
        include_docx_base64=not args.skip_docpeg,
        verify_base_url=args.verify_base_url,
    )

    docx_path = ""
    docpeg = verification.get("docpeg_bundle") if isinstance(verification.get("docpeg_bundle"), dict) else {}
    context = docpeg.get("context") if isinstance(docpeg.get("context"), dict) else {}
    verify_uri = str(context.get("verify_uri") or "")

    if not args.skip_docpeg:
        docx_b64 = str(docpeg.get("docx_base64") or "")
        if docx_b64:
            name = str(docpeg.get("file_name") or "beam_l3_component_report.docx")
            path = output_dir / name
            path.write_bytes(base64.b64decode(docx_b64))
            docx_path = str(path)

    summary = {
        "ok": bool(verification.get("ok")),
        "component_id": verification.get("component_id"),
        "component_uri": verification.get("component_uri"),
        "status": verification.get("status"),
        "passed": bool(verification.get("passed")),
        "proof_hash": verification.get("proof_hash"),
        "material_count": len(verification.get("materials") or []),
        "verify_uri": verify_uri,
        "docx_path": docx_path,
        "final_proof_factors": verification.get("proof_factors") or {},
    }
    (output_dir / "beam_l3_component_demo_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _print("[SUMMARY] " + json.dumps(summary, ensure_ascii=False))
    _print("[DONE] component_utxo_beam_l3_demo passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ComponentUTXO Beam-L3 demo runner")
    parser.add_argument("--project-uri", default="v://cn.yanan/east-ring-expressway")
    parser.add_argument(
        "--payload-file",
        default="tools/acceptance/config/component_utxo_beam_l3.sample.json",
        help="Path to payload JSON. If omitted or empty, use built-in Beam-L3 payload.",
    )
    parser.add_argument("--verify-base-url", default="https://verify.qcspec.com")
    parser.add_argument("--output-dir", default="tools/acceptance/out/component_utxo_beam_l3")
    parser.add_argument("--skip-docpeg", action="store_true")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    sys.exit(run(args))
