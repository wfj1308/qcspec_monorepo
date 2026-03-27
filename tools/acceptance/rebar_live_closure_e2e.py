"""
Rebar live-table closure E2E acceptance script.

Flow:
1) login
2) create rebar inspection (design/limit/values)
3) verify inspection proof sovereignty fields in proof_utxo
4) trigger report generation
5) poll report list and verify report proof
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from typing import Any

import httpx


def _fail(message: str, code: int = 2) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(code)


def _ok(message: str) -> None:
    print(f"[OK]   {message}")


def _step(title: str, detail: str = "") -> None:
    print(f"[STEP] {title}")
    if detail:
        print(f"       {detail}")


def _json_or_text(res: httpx.Response) -> Any:
    try:
        return res.json()
    except Exception:
        return (res.text or "").strip()


def _ensure_status(res: httpx.Response, expected: int | tuple[int, ...], label: str) -> Any:
    expected_set = {expected} if isinstance(expected, int) else set(expected)
    if res.status_code not in expected_set:
        _fail(f"{label} status={res.status_code}, body={_json_or_text(res)}")
    return _json_or_text(res)


def _find_project_id(client: httpx.Client, api_base: str, token: str, enterprise_id: str) -> str:
    _step("Find project", f"enterprise_id={enterprise_id}")
    res = client.get(
        f"{api_base}/v1/projects/",
        params={"enterprise_id": enterprise_id, "limit": 20},
        headers={"Authorization": f"Bearer {token}"},
    )
    body = _ensure_status(res, 200, "list projects")
    data = body.get("data") if isinstance(body, dict) else body
    if isinstance(data, dict):
        rows = data.get("data") if isinstance(data.get("data"), list) else []
    else:
        rows = data if isinstance(data, list) else []
    if not rows:
        _fail("no project found; please create a project first or pass --project-id")
    project_id = str(rows[0].get("id") or "").strip()
    if not project_id:
        _fail("project id missing from list response")
    _ok(f"Using project: {project_id}")
    return project_id


def _verify_inspection_proof(utxo: dict[str, Any]) -> None:
    sd = utxo.get("state_data") if isinstance(utxo.get("state_data"), dict) else {}
    signed_by = utxo.get("signed_by") if isinstance(utxo.get("signed_by"), list) else []
    first_sign = signed_by[0] if signed_by and isinstance(signed_by[0], dict) else {}

    missing = []
    for key in ("proof_hash", "project_uri"):
        if not str(utxo.get(key) or "").strip():
            missing.append(key)
    if not str(sd.get("v_uri") or "").strip():
        missing.append("state_data.v_uri")
    if not str(first_sign.get("executor_uri") or "").strip():
        missing.append("signed_by[0].executor_uri")
    if not str(first_sign.get("ordosign_hash") or "").strip():
        missing.append("signed_by[0].ordosign_hash")
    for key in ("design", "limit", "values"):
        if sd.get(key) is None:
            missing.append(f"state_data.{key}")
    if missing:
        _fail("inspection proof missing fields: " + ", ".join(missing))
    _ok("Inspection proof sovereignty fields verified")


def _verify_report_proof(utxo: dict[str, Any]) -> None:
    sd = utxo.get("state_data") if isinstance(utxo.get("state_data"), dict) else {}
    missing = []
    for key in ("proof_hash", "project_uri"):
        if not str(utxo.get(key) or "").strip():
            missing.append(key)
    for key in ("report_no", "report_uri"):
        if not str(sd.get(key) or "").strip():
            missing.append(f"state_data.{key}")
    if missing:
        _fail("report proof missing fields: " + ", ".join(missing))
    _ok("Report proof sovereignty fields verified")


def run(args: argparse.Namespace) -> int:
    api_base = str(args.api_base).rstrip("/")
    today = str(date.today())

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        _step("Login", args.email)
        login_res = client.post(
            f"{api_base}/v1/auth/login",
            json={"email": args.email, "password": args.password},
        )
        login = _ensure_status(login_res, 200, "login")
        token = str(login.get("access_token") or "").strip()
        enterprise_id = str(login.get("enterprise_id") or "").strip()
        if not token or not enterprise_id:
            _fail("login response missing token or enterprise_id")
        _ok("Token acquired")

        project_id = str(args.project_id or "").strip() or _find_project_id(
            client, api_base, token, enterprise_id
        )

        before_report_ids: set[str] = set()
        _step("Snapshot existing reports")
        before_reports_res = client.get(
            f"{api_base}/v1/reports/",
            params={"project_id": project_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        before_reports = _ensure_status(before_reports_res, 200, "list reports before")
        if isinstance(before_reports, dict) and isinstance(before_reports.get("data"), list):
            for row in before_reports["data"]:
                rid = str((row or {}).get("id") or "").strip()
                if rid:
                    before_report_ids.add(rid)

        _step("Create rebar inspection", f"project_id={project_id}")
        inspection_payload = {
            "project_id": project_id,
            "location": args.location,
            "type": "rebar_spacing",
            "type_name": "钢筋间距",
            "value": args.value,
            "standard": args.design,
            "unit": "mm",
            "result": "pass",
            "person": args.person,
            "remark": "rebar live-table acceptance",
            "design": args.design,
            "limit": args.limit,
            "values": args.values,
        }
        create_res = client.post(
            f"{api_base}/v1/inspections/",
            headers={"Authorization": f"Bearer {token}"},
            json=inspection_payload,
        )
        created = _ensure_status(create_res, 201, "create inspection")
        inspection_proof_id = str(created.get("proof_id") or "").strip()
        result_source = str(created.get("result_source") or "").strip()
        if not inspection_proof_id:
            _fail("create inspection response missing proof_id")
        if result_source not in {"auto_design_limit", "manual"}:
            _fail(f"unexpected result_source: {result_source}")
        _ok(f"Inspection created, proof={inspection_proof_id}, source={result_source}")

        _step("Verify inspection proof_utxo")
        insp_utxo_res = client.get(
            f"{api_base}/v1/proof/utxo/{inspection_proof_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        insp_utxo = _ensure_status(insp_utxo_res, 200, "get inspection proof_utxo")
        if not isinstance(insp_utxo, dict):
            _fail("inspection proof_utxo payload invalid")
        _verify_inspection_proof(insp_utxo)

        _step("Trigger report generation")
        gen_res = client.post(
            f"{api_base}/v1/reports/generate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": project_id,
                "enterprise_id": enterprise_id,
                "location": args.location,
                "date_from": today,
                "date_to": today,
            },
        )
        gen = _ensure_status(gen_res, 202, "generate report")
        if not bool(gen.get("accepted")):
            _fail("report generate not accepted")
        _ok("Report generation accepted")

        _step("Poll new report")
        report_row: dict[str, Any] | None = None
        for _ in range(max(1, args.poll_count)):
            list_res = client.get(
                f"{api_base}/v1/reports/",
                params={"project_id": project_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            rows_pack = _ensure_status(list_res, 200, "list reports poll")
            rows = rows_pack.get("data") if isinstance(rows_pack, dict) else []
            if not isinstance(rows, list):
                rows = []
            for row in rows:
                rid = str((row or {}).get("id") or "").strip()
                if rid and rid not in before_report_ids:
                    report_row = row
                    break
            if report_row:
                break
            time.sleep(args.poll_interval_s)
        if not report_row:
            _fail("new report not found in polling window")

        report_id = str(report_row.get("id") or "").strip()
        report_proof_id = str(report_row.get("proof_id") or "").strip()
        if not report_id or not report_proof_id:
            _fail("new report missing id or proof_id")
        _ok(f"New report found: {report_id}")

        _step("Load report detail", report_id)
        detail_res = client.get(
            f"{api_base}/v1/reports/{report_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        detail = _ensure_status(detail_res, 200, "get report")
        if not isinstance(detail, dict):
            _fail("report detail payload invalid")

        if args.require_file and not str(detail.get("file_url") or "").strip():
            _fail("report file_url missing (set --require-file false to skip this hard check)")

        _step("Verify report proof_utxo", report_proof_id)
        rpt_utxo_res = client.get(
            f"{api_base}/v1/proof/utxo/{report_proof_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        rpt_utxo = _ensure_status(rpt_utxo_res, 200, "get report proof_utxo")
        if not isinstance(rpt_utxo, dict):
            _fail("report proof_utxo payload invalid")
        _verify_report_proof(rpt_utxo)

        _step("Verify proof API")
        verify_res = client.get(
            f"{api_base}/v1/proof/verify/{report_proof_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        verify = _ensure_status(verify_res, 200, "verify report proof")
        if not bool(verify.get("valid")):
            _fail(f"report proof verify failed: {verify}")
        _ok("Proof verification passed")

        summary = {
            "project_id": project_id,
            "inspection_id": created.get("inspection_id"),
            "inspection_proof_id": inspection_proof_id,
            "inspection_result": created.get("result"),
            "report_id": report_id,
            "report_no": detail.get("report_no"),
            "report_proof_id": report_proof_id,
            "report_file_url": detail.get("file_url"),
            "gitpeg_anchor": rpt_utxo.get("gitpeg_anchor"),
        }
        print("[SUMMARY] " + json.dumps(summary, ensure_ascii=False))
        print("[DONE] rebar live-table closure e2e passed")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QCSpec rebar live-table closure E2E")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--project-id", default="")
    parser.add_argument("--location", default="K30+100")
    parser.add_argument("--person", default="王质检")
    parser.add_argument("--design", type=float, default=200.0)
    parser.add_argument("--limit", default="±10")
    parser.add_argument("--value", type=float, default=200.0)
    parser.add_argument(
        "--values",
        type=float,
        nargs="+",
        default=[198, 203, 201, 196, 207, 202, 199, 204, 198, 200, 201, 199],
    )
    parser.add_argument("--poll-count", type=int, default=20)
    parser.add_argument("--poll-interval-s", type=float, default=1.0)
    parser.add_argument("--require-file", action="store_true")
    return parser


if __name__ == "__main__":
    ns = build_parser().parse_args()
    sys.exit(run(ns))

