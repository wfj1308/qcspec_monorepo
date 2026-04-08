from __future__ import annotations

import base64
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.infrastructure.http.app_factory import create_app


@dataclass
class CheckResult:
    ok: bool
    name: str
    detail: str


def run_mobile_flow(
    *,
    component_code: str = "K12-340-4C",
    expected_current_step_key: str = "rebar_install",
    expected_next_step_key: str = "concrete_pour",
) -> list[CheckResult]:
    client = TestClient(create_app())
    v_uri = f"v://cn.dajing/djgs/bridge/{component_code}"

    checks: list[CheckResult] = []

    # 0) chain status
    chain_resp = client.get("/api/v1/mobile/chain-status")
    chain_ok = chain_resp.status_code == 200
    chain_json = chain_resp.json() if chain_ok else {}
    checks.append(
        CheckResult(
            ok=chain_ok and bool(chain_json.get("mode")),
            name="主链状态接口可用",
            detail=f"status={chain_resp.status_code}, mode={chain_json.get('mode')}, reason={chain_json.get('reason')}",
        )
    )

    # 1) current-step
    current_resp = client.get(f"/api/v1/mobile/component/{v_uri}/current-step")
    current_ok = current_resp.status_code == 200
    current_json = current_resp.json() if current_ok else {}
    steps = list(current_json.get("steps") or [])
    current_step = next((item for item in steps if str(item.get("status")) == "current"), {})
    checks.append(
        CheckResult(
            ok=current_ok and bool(steps),
            name="current-step 可用",
            detail=f"status={current_resp.status_code}, steps={len(steps)}",
        )
    )
    checks.append(
        CheckResult(
            ok=str(current_step.get("key") or "") == expected_current_step_key,
            name="扫码命中当前工序",
            detail=f"current={current_step.get('key')}, expected={expected_current_step_key}",
        )
    )

    # 2) qrcode
    qr_resp = client.get(f"/api/v1/mobile/qrcode/{v_uri}")
    checks.append(
        CheckResult(
            ok=qr_resp.status_code == 200 and (qr_resp.headers.get("content-type") or "").startswith("image/png"),
            name="二维码接口可用",
            detail=f"status={qr_resp.status_code}, content-type={qr_resp.headers.get('content-type')}",
        )
    )

    # 3) snappeg anchor
    photo_bytes = b"mobile-qcspec-anchor-smoke"
    photo_b64 = base64.b64encode(photo_bytes).decode("ascii")
    photo_hash = hashlib.sha256(photo_bytes).hexdigest()
    anchor_resp = client.post(
        "/api/v1/mobile/snappeg/anchor",
        json={
            "photo": photo_b64,
            "hash": photo_hash,
            "trip_id": component_code,
            "location": {"lat": 31.2, "lng": 121.5},
        },
    )
    anchor_json = anchor_resp.json() if anchor_resp.status_code == 200 else {}
    checks.append(
        CheckResult(
            ok=anchor_resp.status_code == 200 and bool(anchor_json.get("anchor_id")),
            name="拍照锚定可用",
            detail=f"status={anchor_resp.status_code}, anchor_id={anchor_json.get('anchor_id')}",
        )
    )

    # 4) submit-mobile
    submit_resp = client.post(
        "/api/v1/mobile/trips/submit-mobile",
        json={
            "v_uri": v_uri,
            "component_code": component_code,
            "step_key": expected_current_step_key,
            "result": "合格",
            "form_data": {"steel_spec": "HRB400", "install_count": "24", "checked_at": "2026-04-08T08:00:00Z"},
            "evidence": [{"hash": photo_hash, "timestamp": "2026-04-08T08:00:00Z"}],
            "signature": {"type": "password", "data": "password-confirmed"},
            "executor_uri": "v://mobile/executor/施工单位",
        },
    )
    submit_json = submit_resp.json() if submit_resp.status_code == 200 else {}
    proof_id = str(submit_json.get("proof_id") or "")
    triprole_sync = submit_json.get("triprole_sync") or {}
    checks.append(
        CheckResult(
            ok=submit_resp.status_code == 200 and bool(proof_id),
            name="移动端提交流程成功",
            detail=f"status={submit_resp.status_code}, proof_id={proof_id}",
        )
    )
    checks.append(
        CheckResult(
            ok="ok" in dict(triprole_sync),
            name="TripRole 同步字段返回",
            detail=f"triprole_sync={json.dumps(triprole_sync, ensure_ascii=False)}",
        )
    )

    # 5) step advanced
    next_resp = client.get(f"/api/v1/mobile/component/{v_uri}/current-step")
    next_json = next_resp.json() if next_resp.status_code == 200 else {}
    next_steps = list(next_json.get("steps") or [])
    next_step = next((item for item in next_steps if str(item.get("status")) == "current"), {})
    checks.append(
        CheckResult(
            ok=next_resp.status_code == 200 and str(next_step.get("key") or "") == expected_next_step_key,
            name="工序自动推进",
            detail=f"current={next_step.get('key')}, expected={expected_next_step_key}",
        )
    )

    return checks


def main() -> None:
    checks = run_mobile_flow()
    failed = [item for item in checks if not item.ok]

    print("=== QCSpec Mobile Flow Acceptance ===")
    for item in checks:
        print(f"[{'PASS' if item.ok else 'FAIL'}] {item.name} -> {item.detail}")

    if failed:
        print(f"\nRESULT: FAILED ({len(failed)}/{len(checks)} failed)")
        raise SystemExit(1)
    print(f"\nRESULT: PASSED ({len(checks)}/{len(checks)} checks)")


if __name__ == "__main__":
    main()
