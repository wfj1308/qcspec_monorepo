"""
Run a full BOQ aggregation smoke and export a sovereign ledger package snapshot.

Example:
  python tools/normpeg/docfinal_full_aggregate.py \
    --project-uri "v://project/demo/highway/JK-C08/" \
    --project-name "JK-C08 Demo" \
    --out-dir "tmp/docfinal_full_aggregate"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.supabase_provider import get_supabase_client  # noqa: E402
from services.api.triprole_engine import build_docfinal_package_for_boq, get_boq_realtime_status  # noqa: E402


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _pick_focus_item(items: list[dict[str, Any]], explicit_uri: str) -> str:
    candidate = _to_text(explicit_uri).strip()
    if candidate:
        return candidate
    settled = [x for x in items if int(x.get("settlement_count") or 0) > 0]
    if settled:
        return _to_text(settled[0].get("boq_item_uri") or "").strip()
    if items:
        return _to_text(items[0].get("boq_item_uri") or "").strip()
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DocFinal full aggregation smoke script")
    parser.add_argument("--project-uri", required=True, help="Project sovereign URI")
    parser.add_argument("--project-name", default="", help="Optional display name")
    parser.add_argument("--boq-item-uri", default="", help="Optional focus boq_item_uri")
    parser.add_argument("--verify-base-url", default="https://verify.qcspec.com")
    parser.add_argument("--aggregate-anchor-code", default="", help="Hierarchy anchor code, e.g. 403 or 403-1-2")
    parser.add_argument("--aggregate-direction", default="all", help="all|up|down|both")
    parser.add_argument("--aggregate-level", default="all", help="all|chapter|section|item|detail|leaf|group")
    parser.add_argument("--snapshot-limit", type=int, default=120, help="Max records/rows saved into snapshot json")
    parser.add_argument("--out-dir", default=str(ROOT / "tmp" / "docfinal_full_aggregate"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sb = get_supabase_client()
    status = get_boq_realtime_status(sb=sb, project_uri=args.project_uri, limit=10000)
    items = [x for x in (status.get("items") or []) if isinstance(x, dict)]
    focus_uri = _pick_focus_item(items, args.boq_item_uri)
    if not focus_uri:
        print("[ERROR] no BOQ items found in project.")
        return 2

    package = build_docfinal_package_for_boq(
        boq_item_uri=focus_uri,
        sb=sb,
        project_meta={
            "project_name": _to_text(args.project_name).strip(),
            "project_uri": _to_text(args.project_uri).strip(),
        },
        verify_base_url=_to_text(args.verify_base_url).strip() or "https://verify.qcspec.com",
        aggregate_anchor_code=_to_text(args.aggregate_anchor_code).strip(),
        aggregate_direction=_to_text(args.aggregate_direction).strip() or "all",
        aggregate_level=_to_text(args.aggregate_level).strip() or "all",
    )

    context = package.get("context") if isinstance(package.get("context"), dict) else {}
    record_rows = [x for x in (context.get("record_rows") or []) if isinstance(x, dict)]
    summary_rows = [x for x in (context.get("hierarchy_summary_rows") or []) if isinstance(x, dict)]
    chapter_rows = [x for x in summary_rows if _to_text(x.get("node_type") or "").strip().lower() == "chapter"]
    snapshot_limit = max(1, int(args.snapshot_limit))

    base = re.sub(r"[^\w\-]+", "_", focus_uri, flags=re.ASCII)[:120] or "docfinal"
    zip_path = out_dir / f"DOCFINAL-{base}.zip"
    context_path = out_dir / f"DOCFINAL-{base}.context.json"

    zip_path.write_bytes(package.get("zip_bytes") or b"")
    context_payload = {
        "project_uri": _to_text(args.project_uri).strip(),
        "focus_boq_item_uri": focus_uri,
        "chain_count": len(package.get("proof_chain") or []),
        "detail_record_count": len(record_rows),
        "hierarchy_summary_count": len(summary_rows),
        "chapter_summary_count": len(chapter_rows),
        "hierarchy_root_hash": _to_text(context.get("hierarchy_root_hash") or "").strip(),
        "hierarchy_filtered_root_hash": _to_text(context.get("hierarchy_filtered_root_hash") or "").strip(),
        "hierarchy_filter": context.get("hierarchy_filter") if isinstance(context.get("hierarchy_filter"), dict) else {},
        "record_rows": record_rows[:snapshot_limit],
        "hierarchy_summary_rows": summary_rows[:snapshot_limit],
    }
    context_path.write_text(json.dumps(context_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print("[DOCFINAL FULL AGGREGATE] OK")
    print(f"  project_uri: {args.project_uri}")
    print(f"  focus_boq_item_uri: {focus_uri}")
    print(f"  detail_record_count: {len(record_rows)}")
    print(f"  hierarchy_summary_count: {len(summary_rows)}")
    print(f"  chapter_summary_count: {len(chapter_rows)}")
    print(f"  zip: {zip_path}")
    print(f"  context_snapshot: {context_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

