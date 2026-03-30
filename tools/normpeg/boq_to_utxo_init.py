"""
Import BOQ Excel and initialize INITIAL UTXO rows for each BOQ line item.

Examples:
  python tools/normpeg/boq_to_utxo_init.py \
    --xlsx "C:/Users/xm_91/Desktop/400章(1).xlsx" \
    --project-uri "v://project/demo/highway/JK-C08/" \
    --project-id "<uuid>" \
    --boq-root-uri "v://project/boq" \
    --norm-context-root-uri "v://project/normContext"

  python tools/normpeg/boq_to_utxo_init.py ... --commit
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.boq_utxo_service import (  # noqa: E402
    boq_item_to_dict,
    initialize_boq_utxos,
    parse_boq_hierarchy,
    parse_boq_excel,
)
from services.api.supabase_provider import get_supabase_client  # noqa: E402


def _auto_find_boq_xlsx() -> Path | None:
    candidates = []
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        candidates.extend(desktop.glob("400*.xlsx"))
        candidates.extend(desktop.glob("*.xlsx"))
    for path in candidates:
        if path.name.startswith("~$"):
            continue
        if path.suffix.lower() == ".xlsx":
            return path
    return None


def _print_summary(result: dict[str, Any]) -> None:
    print("[BOQ->UTXO] Summary")
    print(f"  commit: {result.get('commit')}")
    print(f"  total_items: {result.get('total_items')}")
    print(f"  success_count: {result.get('success_count')}")
    print(f"  errors: {len(result.get('errors') or [])}")
    if result.get("errors"):
        first = (result.get("errors") or [])[0]
        print(f"  first_error: {first}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BOQ Excel -> INITIAL UTXO importer")
    parser.add_argument("--xlsx", default="", help="Path to BOQ xlsx file. Default: auto-find from Desktop")
    parser.add_argument("--sheet", default="", help="Optional sheet name")
    parser.add_argument("--project-uri", required=True, help="Project sovereign URI")
    parser.add_argument("--project-id", default="", help="Project UUID (optional)")
    parser.add_argument("--owner-uri", default="", help="Owner URI for genesis UTXO")
    parser.add_argument("--boq-root-uri", default="v://project/boq", help="Root URI for BOQ items")
    parser.add_argument("--norm-context-root-uri", default="v://project/normContext", help="Root URI for Norm context")
    parser.add_argument("--all-items", action="store_true", help="Include non-leaf/group rows")
    parser.add_argument("--commit", action="store_true", help="Persist into proof_utxo table")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    xlsx_path = Path(args.xlsx).expanduser() if args.xlsx else _auto_find_boq_xlsx()
    if not xlsx_path:
        print("[ERROR] Unable to locate BOQ xlsx file. Please pass --xlsx.")
        return 2
    if not xlsx_path.exists():
        print(f"[ERROR] BOQ file not found: {xlsx_path}")
        return 2

    boq_items = parse_boq_excel(
        xlsx_path,
        sheet_name=(args.sheet or None),
        leaf_only=not bool(args.all_items),
    )

    if not boq_items:
        print("[ERROR] No BOQ items parsed from file.")
        return 2

    sb = None
    if args.commit:
        try:
            sb = get_supabase_client()
        except Exception as exc:
            print(f"[ERROR] Supabase client init failed: {exc}")
            return 2

    result = initialize_boq_utxos(
        sb=sb,
        project_uri=args.project_uri,
        project_id=(args.project_id or None),
        boq_items=boq_items,
        boq_root_uri=args.boq_root_uri,
        norm_context_root_uri=args.norm_context_root_uri,
        owner_uri=(args.owner_uri or None),
        source_file=str(xlsx_path),
        commit=bool(args.commit),
    )

    preview_rows = [boq_item_to_dict(item) for item in boq_items]
    hierarchy = parse_boq_hierarchy(
        xlsx_path,
        sheet_name=(args.sheet or None),
        boq_root_uri=args.boq_root_uri,
        norm_context_root_uri=args.norm_context_root_uri,
    )
    payload = {
        "parsed_items": preview_rows,
        "hierarchy": {
            "node_count": hierarchy.get("node_count"),
            "root_codes": hierarchy.get("root_codes") or [],
            "nodes": hierarchy.get("nodes") or [],
        },
        "result": result,
    }

    out_path = Path(args.out).expanduser() if args.out else (ROOT / "tmp" / "boq_utxo_init_preview.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    _print_summary(result)
    print(f"[BOQ->UTXO] output_json: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

