from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.domain.specir.runtime.normref_ingest import NormRefIngestEngine


@dataclass
class SpecInput:
    path: Path
    std_code: str
    title: str
    level: str = "industry"


DEFAULT_SPECS: list[SpecInput] = [
    SpecInput(
        path=Path(r"C:\Users\xm_91\Downloads\《公路工程质量检验评定标准 第一册 土建工程》（JTG F801—2017）.pdf"),
        std_code="JTG-F80-1-2017",
        title="公路工程质量检验评定标准 第一册 土建工程",
    ),
    SpecInput(
        path=Path(r"C:\Users\xm_91\Downloads\《公路养护工程质量检验评定标准 第一册 土建工程》（JTG 5220—2020）.pdf"),
        std_code="JTG-5220-2020",
        title="公路养护工程质量检验评定标准 第一册 土建工程",
    ),
    SpecInput(
        path=Path(r"C:\Users\xm_91\Downloads\公路工程质量检验评定标准 第二册 机电工程（JTG 2182-2020）.pdf"),
        std_code="JTG-2182-2020",
        title="公路工程质量检验评定标准 第二册 机电工程",
    ),
]


def parse_spec_arg(value: str) -> SpecInput:
    # format: path|std_code|title|level
    parts = [x.strip() for x in value.split("|")]
    if len(parts) < 3:
        raise ValueError("--spec format must be: path|std_code|title|level(optional)")
    path = Path(parts[0])
    std_code = parts[1]
    title = parts[2]
    level = parts[3] if len(parts) >= 4 and parts[3] else "industry"
    return SpecInput(path=path, std_code=std_code, title=title, level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch ingest NormRef standards into candidate rules.")
    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help="Custom spec input: path|std_code|title|level(optional). Repeatable.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish approved candidates after ingestion.",
    )
    parser.add_argument(
        "--write-to-docs",
        action="store_true",
        help="When publish=true, write rules into docs/normref/rule/imported/**.",
    )
    parser.add_argument("--version-tag", default="2026-04", help="Publish version tag.")
    parser.add_argument(
        "--approve-threshold",
        type=float,
        default=0.75,
        help="Auto approve candidates with confidence >= threshold before publish.",
    )
    parser.add_argument(
        "--report-out",
        default=str(REPO_ROOT / "docs" / "normref" / "std" / "ingest-report-latest.json"),
        help="Output report json path.",
    )
    parser.add_argument(
        "--ocr-max-pages",
        type=int,
        default=20,
        help="OCR max pages per PDF (for scanned files).",
    )
    return parser.parse_args()


def load_specs(args: argparse.Namespace) -> list[SpecInput]:
    if not args.spec:
        return list(DEFAULT_SPECS)
    return [parse_spec_arg(item) for item in args.spec]


def summarize_job(job: dict[str, Any]) -> dict[str, Any]:
    candidates = list(job.get("candidates") or [])
    statuses: dict[str, int] = {"pending": 0, "approved": 0, "rejected": 0}
    for row in candidates:
        key = str(row.get("status") or "pending")
        statuses[key] = statuses.get(key, 0) + 1
    return {
        "job_id": job.get("job_id"),
        "std_code": job.get("std_code"),
        "status": job.get("status"),
        "candidate_count": len(candidates),
        "status_summary": statuses,
        "warnings": job.get("warnings") or [],
    }


def main() -> int:
    args = parse_args()
    specs = load_specs(args)
    engine = NormRefIngestEngine(ocr_max_pages=int(args.ocr_max_pages))

    run_at = datetime.now().isoformat()
    report: dict[str, Any] = {
        "run_at": run_at,
        "publish": bool(args.publish),
        "write_to_docs": bool(args.write_to_docs),
        "version_tag": args.version_tag,
        "approve_threshold": float(args.approve_threshold),
        "ocr_max_pages": int(args.ocr_max_pages),
        "jobs": [],
        "published": [],
    }

    for spec in specs:
        if not spec.path.exists():
            report["jobs"].append(
                {
                    "std_code": spec.std_code,
                    "file": str(spec.path),
                    "ok": False,
                    "error": "file_not_found",
                }
            )
            continue

        content = spec.path.read_bytes()
        created = engine.create_job(
            file_name=spec.path.name,
            content=content,
            std_code=spec.std_code,
            title=spec.title,
            level=spec.level,
        )
        if not created.get("ok"):
            report["jobs"].append(
                {
                    "std_code": spec.std_code,
                    "file": str(spec.path),
                    "ok": False,
                    "error": created.get("error") or "create_job_failed",
                }
            )
            continue

        job = created["job"]
        job_id = str(job.get("job_id"))

        # auto approve by confidence threshold
        approved_ids: list[str] = []
        for cand in list(job.get("candidates") or []):
            confidence = float(cand.get("confidence") or 0)
            cid = str(cand.get("candidate_id") or "")
            if cid and confidence >= float(args.approve_threshold):
                engine.update_candidate_status(job_id=job_id, candidate_id=cid, status="approved")
                approved_ids.append(cid)

        refreshed = engine.get_job(job_id=job_id)
        latest_job = dict(refreshed.get("job") or {}) if refreshed.get("ok") else job
        item = {
            "ok": True,
            "file": str(spec.path),
            **summarize_job(latest_job),
            "auto_approved_count": len(approved_ids),
        }
        report["jobs"].append(item)

        if args.publish and approved_ids:
            published = engine.publish(
                job_id=job_id,
                candidate_ids=approved_ids,
                version_tag=args.version_tag,
                write_to_docs=bool(args.write_to_docs),
            )
            report["published"].append(
                {
                    "job_id": job_id,
                    "ok": bool(published.get("ok")),
                    "published_count": int(published.get("published_count") or 0),
                    "snapshot_hash": str(published.get("snapshot_hash") or ""),
                }
            )

    out_path = Path(args.report_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[normref-ingest] report written: {out_path}")
    for row in report["jobs"]:
        if not row.get("ok"):
            print(f"  - {row.get('std_code')}: FAILED ({row.get('error')})")
            continue
        print(
            f"  - {row.get('std_code')}: candidates={row.get('candidate_count')} "
            f"approved={row.get('status_summary', {}).get('approved', 0)} "
            f"warnings={len(row.get('warnings') or [])}"
        )
    if args.publish:
        total = sum(int(x.get("published_count") or 0) for x in report["published"])
        print(f"[normref-ingest] published rules: {total}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
