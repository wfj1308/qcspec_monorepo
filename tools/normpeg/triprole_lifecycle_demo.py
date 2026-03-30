"""
Run TripRole lifecycle for one BOQ item URI.

Examples:
  python tools/normpeg/triprole_lifecycle_demo.py \
    --boq-item-uri "v://project/boq/403-1-2" \
    --executor-uri "v://user/qc_manager"

  # fail + variation compensation path
  python tools/normpeg/triprole_lifecycle_demo.py \
    --boq-item-uri "v://project/boq/403-1-2" \
    --quality-result FAIL \
    --use-variation
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "services" / "api" / ".env", override=False)

from services.api.supabase_provider import get_supabase_client  # noqa: E402
from services.api.triprole_engine import aggregate_provenance_chain, execute_triprole_action  # noqa: E402


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _find_initial_utxo(sb: Any, boq_item_uri: str) -> dict[str, Any] | None:
    try:
        res = (
            sb.table("proof_utxo")
            .select("*")
            .eq("spent", False)
            .filter("state_data->>boq_item_uri", "eq", boq_item_uri)
            .order("created_at", desc=False)
            .limit(200)
            .execute()
        )
        rows = [x for x in (res.data or []) if isinstance(x, dict)]
    except Exception:
        rows = []

    for row in rows:
        sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
        status = _to_text(sd.get("status") or sd.get("lifecycle_stage") or "").strip().upper()
        if status == "INITIAL":
            return row

    for row in rows:
        if _to_text(row.get("proof_type")).strip().lower() == "zero_ledger":
            return row

    if rows:
        return rows[0]

    try:
        scan = sb.table("proof_utxo").select("*").eq("spent", False).order("created_at", desc=False).limit(3000).execute()
        for row in scan.data or []:
            if not isinstance(row, dict):
                continue
            sd = row.get("state_data") if isinstance(row.get("state_data"), dict) else {}
            if _to_text(sd.get("boq_item_uri") or "").strip() == boq_item_uri:
                return row
    except Exception:
        return None

    return None


def _run_action(
    sb: Any,
    *,
    action: str,
    input_proof_id: str,
    executor_uri: str,
    executor_did: str,
    payload: dict[str, Any],
    result: str | None = None,
) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    body = {
        "action": action,
        "input_proof_id": input_proof_id,
        "executor_uri": executor_uri,
        "executor_did": executor_did,
        "executor_role": "TRIPROLE",
        "result": result,
        "payload": payload,
        "credentials_vc": [
            {
                "credential_id": "vc-demo-rebar-special-operator",
                "holder_did": executor_did,
                "credential_role": "rebar_special_operator",
                "credential_type": "special_operation_license",
                "status": "active",
                "valid_from": "2024-01-01T00:00:00+00:00",
                "valid_to": "2030-12-31T23:59:59+00:00",
                "scope": {
                    "boq_patterns": ["v://project/boq/403-*"],
                },
            }
        ],
        "geo_location": {
            "lat": 30.5728,
            "lng": 104.0668,
            "accuracy_m": 5.0,
            "provider": "gps",
            "captured_at": now_iso,
        },
        "server_timestamp_proof": {
            "ntp_server": "ntp.aliyun.com",
            "client_timestamp": now_iso,
            "ntp_offset_ms": 12.0,
            "ntp_round_trip_ms": 36.0,
            "ntp_sample_id": "demo-local",
        },
    }
    return execute_triprole_action(sb=sb, body=body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TripRole lifecycle demo runner")
    parser.add_argument("--boq-item-uri", required=True)
    parser.add_argument("--executor-uri", default="v://user/triprole/demo")
    parser.add_argument("--executor-did", default="did:coordos:person:triprole-demo")
    parser.add_argument("--quality-result", default="AUTO", choices=["AUTO", "PASS", "FAIL"])
    parser.add_argument("--use-variation", action="store_true", help="When quality FAIL, add variation.record compensation")
    parser.add_argument("--stake", default="K50+200")
    parser.add_argument("--part", default="main_beam")
    parser.add_argument("--spec-uri", default="v://norm/GB50204/5.3.2#diameter_tolerance")
    parser.add_argument("--design", type=float, default=20.0)
    parser.add_argument("--value", type=float, default=19.8)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    sb = get_supabase_client()

    seed = _find_initial_utxo(sb, args.boq_item_uri)
    if not seed:
        print("[ERROR] no unspent UTXO found for boq_item_uri")
        return 2

    current_proof_id = _to_text(seed.get("proof_id") or "").strip()
    if not current_proof_id:
        print("[ERROR] invalid seed proof")
        return 2

    print(f"[seed] {current_proof_id}")

    quality = _run_action(
        sb,
        action="quality.check",
        input_proof_id=current_proof_id,
        executor_uri=args.executor_uri,
        executor_did=args.executor_did,
        result=(None if _to_text(args.quality_result).upper() == "AUTO" else args.quality_result),
        payload={
            "check_type": "material_entry",
            "inspector": args.executor_uri,
            "remark": "triprole lifecycle demo",
            "spec_uri": args.spec_uri,
            "context": args.part,
            "component_type": args.part,
            "design": args.design,
            "value": args.value,
        },
    )
    current_proof_id = _to_text(quality.get("output_proof_id") or "").strip()
    print(f"[quality.check] -> {current_proof_id} ({quality.get('result')})")

    if _to_text(args.quality_result).upper() == "FAIL":
        if not args.use_variation:
            print("[STOP] quality FAIL done. rerun with --use-variation for compensation path")
            return 0
        variation = _run_action(
            sb,
            action="variation.record",
            input_proof_id=current_proof_id,
            executor_uri=args.executor_uri,
            executor_did=args.executor_did,
            payload={
                "reason": "quality remediation",
                "method": "replacement + recheck",
            },
            result="PASS",
        )
        current_proof_id = _to_text(variation.get("output_proof_id") or "").strip()
        print(f"[variation.record] -> {current_proof_id} ({variation.get('result')})")

    measure = _run_action(
        sb,
        action="measure.record",
        input_proof_id=current_proof_id,
        executor_uri=args.executor_uri,
        executor_did=args.executor_did,
        payload={
            "stake": args.stake,
            "part": args.part,
            "values": [198.0, 203.0, 201.0],
            "design": 200.0,
            "unit": "mm",
        },
        result="PASS",
    )
    current_proof_id = _to_text(measure.get("output_proof_id") or "").strip()
    print(f"[measure.record] -> {current_proof_id} ({measure.get('result')})")

    settle = _run_action(
        sb,
        action="settlement.confirm",
        input_proof_id=current_proof_id,
        executor_uri=args.executor_uri,
        executor_did=args.executor_did,
        payload={
            "settlement_no": "SETTLE-DEMO-001",
            "amount": 1000,
            "currency": "CNY",
        },
        result="PASS",
    )
    final_proof_id = _to_text(settle.get("output_proof_id") or "").strip()
    print(f"[settlement.confirm] -> {final_proof_id} ({settle.get('result')})")

    agg = aggregate_provenance_chain(final_proof_id, sb)
    print("[provenance]")
    print(json.dumps({
        "final_proof_id": final_proof_id,
        "total_proof_hash": agg.get("total_proof_hash"),
        "chain_depth": agg.get("chain_depth"),
        "gate": agg.get("gate"),
        "artifact_uri": agg.get("artifact_uri"),
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
