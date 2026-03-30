"""
Generate BOQ-linked DocPeg report and DSP zip package.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.docpeg_proof_chain_service import (  # noqa: E402
    build_dsp_zip_package,
    build_rebar_report_context,
    get_proof_chain,
    render_rebar_inspection_docx,
    render_rebar_inspection_pdf,
)
from services.api.supabase_provider import get_supabase_client  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DocPeg BOQ proof-chain report builder")
    parser.add_argument("--boq-item-uri", required=True, help="BOQ line URI, e.g. v://project/boq/403-1-2")
    parser.add_argument("--template", default="", help="docxtpl template path (rebar_inspection_table.docx)")
    parser.add_argument("--verify-base-url", default="https://verify.qcspec.com")
    parser.add_argument("--project-meta", default="", help="JSON text for project metadata")
    parser.add_argument("--out-dir", default="tmp/docpeg_out", help="Output directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    sb = get_supabase_client()

    chain = get_proof_chain(args.boq_item_uri, sb)
    if not chain:
        print("[ERROR] No proof chain found for this boq_item_uri.")
        return 2

    project_meta = {}
    if args.project_meta:
        project_meta = json.loads(args.project_meta)

    context = build_rebar_report_context(
        boq_item_uri=args.boq_item_uri,
        chain_rows=chain,
        project_meta=project_meta,
        verify_base_url=args.verify_base_url,
    )

    template_path = Path(args.template).expanduser() if args.template else (ROOT / "services" / "api" / "templates" / "01_inspection_report.docx")
    docx_bytes = render_rebar_inspection_docx(template_path=template_path, context=context)
    pdf_bytes = render_rebar_inspection_pdf(docx_bytes=docx_bytes, context=context)
    dsp_bytes = build_dsp_zip_package(
        report_pdf_bytes=pdf_bytes,
        docx_bytes=docx_bytes,
        proof_chain=chain,
        context=context,
        evidence_items=[],
    )

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    base = re.sub(r"[^\w\-]+", "_", args.boq_item_uri.strip())[:120]
    docx_path = out_dir / f"{base}.docx"
    pdf_path = out_dir / f"{base}.pdf"
    zip_path = out_dir / f"{base}.zip"
    context_path = out_dir / f"{base}.context.json"

    docx_path.write_bytes(docx_bytes)
    pdf_path.write_bytes(pdf_bytes)
    zip_path.write_bytes(dsp_bytes)
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(f"[OK] chain_nodes: {len(chain)}")
    print(f"[OK] docx: {docx_path}")
    print(f"[OK] pdf:  {pdf_path}")
    print(f"[OK] zip:  {zip_path}")
    print(f"[OK] context: {context_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

