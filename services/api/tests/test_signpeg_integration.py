from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from urllib.parse import quote

import pytest
from fastapi import HTTPException

from services.api.domain.signpeg.flows import (
    delegate_flow,
    get_executor_flow,
    register_executor_flow,
    sign_flow,
    status_flow,
    update_executor_holder_flow,
    verify_flow,
)
from services.api.domain.signpeg.models import (
    CapacityProfile,
    DelegationRequest,
    EnergyProfile,
    ExecutorRegisterRequest,
    HolderChangeRequest,
    SignPegRequest,
    Skill,
    VerifyRequest,
)
from services.api.domain.signpeg.runtime.scheduler import ExecutorScheduler


@dataclass
class _Op:
    kind: str
    payload: Any = None


class _FakeTable:
    def __init__(self, sb: "_FakeSupabase", name: str) -> None:
        self._sb = sb
        self._name = name
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._order_field: str | None = None
        self._order_desc: bool = False
        self._op = _Op(kind="select")
        self._select_cols = "*"

    def select(self, cols: str = "*"):
        self._select_cols = cols
        self._op = _Op(kind="select")
        return self

    def eq(self, field: str, value: Any):
        self._filters.append((field, value))
        return self

    def limit(self, value: int):
        self._limit = int(value)
        return self

    def order(self, field: str, desc: bool = False):
        self._order_field = field
        self._order_desc = bool(desc)
        return self

    def insert(self, payload: Any):
        self._op = _Op(kind="insert", payload=payload)
        return self

    def upsert(self, payload: Any, on_conflict: str = ""):
        self._op = _Op(kind="upsert", payload={"row": payload, "on_conflict": on_conflict})
        return self

    def update(self, payload: Any):
        self._op = _Op(kind="update", payload=payload)
        return self

    def _apply_filters(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = rows
        for field, value in self._filters:
            out = [row for row in out if row.get(field) == value]
        return out

    def execute(self):
        table_rows = self._sb._data.setdefault(self._name, [])
        if self._op.kind == "insert":
            payload = self._op.payload
            rows = payload if isinstance(payload, list) else [payload]
            to_insert = [deepcopy(dict(row)) for row in rows]
            table_rows.extend(to_insert)
            return SimpleNamespace(data=to_insert)

        if self._op.kind == "upsert":
            op = dict(self._op.payload or {})
            row = deepcopy(dict(op.get("row") or {}))
            on_conflict = str(op.get("on_conflict") or "").strip()
            keys = [k.strip() for k in on_conflict.split(",") if k.strip()]
            if not keys:
                table_rows.append(row)
                return SimpleNamespace(data=[row])
            hit_index = -1
            for idx, item in enumerate(table_rows):
                if all(item.get(key) == row.get(key) for key in keys):
                    hit_index = idx
                    break
            if hit_index >= 0:
                merged = {**table_rows[hit_index], **row}
                table_rows[hit_index] = merged
                return SimpleNamespace(data=[merged])
            table_rows.append(row)
            return SimpleNamespace(data=[row])

        if self._op.kind == "update":
            payload = dict(self._op.payload or {})
            matched = self._apply_filters(table_rows)
            out: list[dict[str, Any]] = []
            for row in matched:
                row.update(payload)
                out.append(deepcopy(row))
            return SimpleNamespace(data=out)

        rows = self._apply_filters([deepcopy(row) for row in table_rows])
        if self._order_field:
            rows = sorted(rows, key=lambda row: row.get(self._order_field), reverse=self._order_desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self) -> None:
        self._data: dict[str, list[dict[str, Any]]] = {
            "san_executors": [],
            "san_executor_holders": [],
            "san_delegations": [],
            "gate_trips": [],
            "docpeg_states": [],
            "railpact_settlements": [],
        }

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


def _skill(token: str) -> Skill:
    return Skill(
        skill_uri=f"v://normref.com/skill/{token}@v1",
        cert_no=f"CERT-{token}",
        issued_by="v://cn.浣忓缓閮?",
        valid_until=date.today() + timedelta(days=365),
        scope=[token],
        level="senior",
    )


def _register(
    sb: _FakeSupabase,
    *,
    uri: str,
    role_token: str,
    name: str,
    holder: str,
    current_load: int = 0,
    consumed: int = 0,
) -> None:
    org_uri = "v://cn.涓寳/"
    if not any(str(row.get("executor_uri") or "").rstrip("/") == org_uri.rstrip("/") for row in sb._data["san_executors"]):
        register_executor_flow(
            sb=sb,
            body=ExecutorRegisterRequest(
                executor_uri=org_uri,
                executor_type="org",
                name="涓寳宸ョ▼",
                org_uri=org_uri,
                skills=[_skill("organization-qualification")],
                org_spec={
                    "org_type": "designer",
                    "business_license": "91610000XXXXXXXX",
                    "branch_count": 50,
                },
                business_license_file="mock-org-license-file",
                holder_name="涓寳宸ョ▼",
                holder_id="org-zhongbei",
                holder_since=datetime.now(UTC) - timedelta(days=365),
            ),
        )
    body = ExecutorRegisterRequest(
        executor_uri=uri,
        name=name,
        org_uri=org_uri,
        skills=[_skill(role_token)],
        energy=EnergyProfile(time_cost=0.5, fee_rate=200.0, credit_limit=100, consumed=consumed),
        capacity=CapacityProfile(max_concurrent=10, current_load=current_load, overload_policy="reject"),
        holder_name=holder,
        holder_id=f"holder-{holder}",
        holder_since=datetime.now(UTC) - timedelta(days=30),
    )
    register_executor_flow(sb=sb, body=body)


def test_signpeg_normal_full_signature_flow() -> None:
    sb = _FakeSupabase()
    _register(sb, uri="v://cn.涓寳/executor/inspector-a", role_token="inspection", name="妫€鏌ュ憳A", holder="寮犱笁")
    _register(sb, uri="v://cn.涓寳/executor/recorder-a", role_token="record", name="璁板綍鍛楢", holder="鏉庡洓")
    _register(sb, uri="v://cn.涓寳/executor/reviewer-a", role_token="review", name="澶嶆牳鍛楢", holder="鐜嬩簲")
    _register(sb, uri="v://cn.涓寳/executor/constructor-a", role_token="construction", name="鏂藉伐鍛楢", holder="璧靛叚")
    _register(sb, uri="v://cn.涓寳/executor/supervisor-a", role_token="bridge-inspection", name="鐩戠悊A", holder="閽变竷")

    doc_id = "NINST-90219204"
    body_hash = "sha256:abc001"
    steps = [
        ("inspector", "inspector.submit", "submit", "v://cn.涓寳/executor/inspector-a"),
        ("recorder", "recorder.sign", "sign", "v://cn.涓寳/executor/recorder-a"),
        ("reviewer", "reviewer.review", "approve", "v://cn.涓寳/executor/reviewer-a"),
        ("constructor", "constructor.sign", "sign", "v://cn.涓寳/executor/constructor-a"),
        ("supervisor", "supervisor.approve", "approve", "v://cn.涓寳/executor/supervisor-a"),
    ]
    trip_uris: set[str] = set()
    for dto_role, trip_role, action, executor_uri in steps:
        out = sign_flow(
            sb=sb,
            body=SignPegRequest(
                doc_id=doc_id,
                body_hash=body_hash,
                executor_uri=executor_uri,
                dto_role=dto_role,
                trip_role=trip_role,
                action=action,
            ),
        )
        assert out["ok"] is True
        trip_uris.add(str(out["trip_uri"]))

    assert len(trip_uris) == 5
    assert len(sb._data["gate_trips"]) == 5
    state_row = sb._data["docpeg_states"][0]
    assert state_row["doc_id"] == doc_id
    assert state_row["lifecycle_stage"] == "approved"
    assert state_row["all_signed"] is True

    status = status_flow(sb=sb, doc_id=doc_id)
    assert status["all_signed"] is True
    assert status["next_required"] == ""
    assert len(status["signatures"]) == 5
    assert int(status["current_slot"]) == 5
    assert int(status["next_slot"]) == 0
    assert status["blocked_reason"] == ""


def test_executor_uri_stable_holder_change_signatures_remain_valid() -> None:
    sb = _FakeSupabase()
    uri = "v://cn.涓寳/executor/zhang-san"
    _register(sb, uri=uri, role_token="bridge-inspection", name="supervisor-executor", holder="zhangsan")

    first = sign_flow(
        sb=sb,
        body=SignPegRequest(
            doc_id="NINST-1",
            body_hash="sha256:doc-v1",
            executor_uri=uri,
            dto_role="supervisor",
            trip_role="supervisor.approve",
            action="approve",
        ),
    )
    verify_first = verify_flow(
        sb=sb,
        body=VerifyRequest(
            sig_data=first["sig_data"],
            doc_id="NINST-1",
            body_hash="sha256:doc-v1",
            executor_uri=uri,
            dto_role="supervisor",
            trip_role="supervisor.approve",
            signed_at=datetime.fromisoformat(first["signed_at"]),
        ),
    )
    assert verify_first["verified"] is True

    update_executor_holder_flow(
        sb=sb,
        executor_uri=quote(uri, safe=""),
        body=HolderChangeRequest(holder_name="鏉庡洓", holder_id="u-lisi"),
    )
    record = get_executor_flow(sb=sb, executor_uri=uri)
    assert record["executor"]["executor_uri"] == uri
    assert record["executor"]["holder_name"] == "鏉庡洓"
    assert len(record["holder_history"]) >= 2

    second = sign_flow(
        sb=sb,
        body=SignPegRequest(
            doc_id="NINST-2",
            body_hash="sha256:doc-v2",
            executor_uri=uri,
            dto_role="supervisor",
            trip_role="supervisor.approve",
            action="approve",
        ),
    )
    verify_second = verify_flow(
        sb=sb,
        body=VerifyRequest(
            sig_data=second["sig_data"],
            doc_id="NINST-2",
            body_hash="sha256:doc-v2",
            executor_uri=uri,
            dto_role="supervisor",
            trip_role="supervisor.approve",
            signed_at=datetime.fromisoformat(second["signed_at"]),
        ),
    )
    assert verify_second["verified"] is True


def test_scheduler_skips_full_executor_and_assigns_idle_one() -> None:
    sb = _FakeSupabase()
    _register(
        sb,
        uri="v://cn.涓寳/executor/zhang-san",
        role_token="bridge-inspection",
        name="鐩戠潱鎵ц浣?寮犱笁",
        holder="寮犱笁",
        current_load=10,
    )
    _register(
        sb,
        uri="v://cn.涓寳/executor/li-si",
        role_token="bridge-inspection",
        name="鐩戠潱鎵ц浣?鏉庡洓",
        holder="鏉庡洓",
        current_load=3,
    )
    scheduler = ExecutorScheduler(sb=sb)
    picked = asyncio.run(
        scheduler.assign(
            dto_role="supervisor",
            required_skill="bridge-inspection",
            doc_id="NINST-NEW-1",
        )
    )
    assert picked.executor_uri == "v://cn.涓寳/executor/li-si"


def test_tamper_detection_fails_verify_when_body_hash_changes() -> None:
    sb = _FakeSupabase()
    uri = "v://cn.涓寳/executor/inspector-a"
    _register(sb, uri=uri, role_token="inspection", name="inspector-executor", holder="zhangsan")
    signed = sign_flow(
        sb=sb,
        body=SignPegRequest(
            doc_id="NINST-TAMPER",
            body_hash="sha256:original",
            executor_uri=uri,
            dto_role="inspector",
            trip_role="inspector.submit",
            action="submit",
        ),
    )
    verify_out = verify_flow(
        sb=sb,
        body=VerifyRequest(
            sig_data=signed["sig_data"],
            doc_id="NINST-TAMPER",
            body_hash="sha256:modified",
            executor_uri=uri,
            dto_role="inspector",
            trip_role="inspector.submit",
            signed_at=datetime.fromisoformat(signed["signed_at"]),
        ),
    )
    assert verify_out["verified"] is False


def test_delegation_signing_within_window() -> None:
    sb = _FakeSupabase()
    principal = "v://cn.涓寳/executor/zhang-san"
    delegatee = "v://cn.涓寳/executor/li-si"
    _register(sb, uri=principal, role_token="bridge-inspection", name="principal-executor", holder="zhangsan")
    _register(sb, uri=delegatee, role_token="bridge-inspection", name="delegatee-executor", holder="lisi")

    now = datetime.now(UTC)
    delegation = asyncio.run(
        delegate_flow(
            sb=sb,
            body=DelegationRequest(
                from_executor_uri=principal,
                to_executor_uri=delegatee,
                scope=["sign", "approve"],
                valid_from=now - timedelta(hours=1),
                valid_until=now + timedelta(days=3),
                proof_doc="sha256:delegation-proof",
            ),
        )
    )
    delegation_uri = delegation["delegation"]["delegation_uri"]
    signed = sign_flow(
        sb=sb,
        body=SignPegRequest(
            doc_id="NINST-DELEGATE",
            body_hash="sha256:delegate-body",
            executor_uri=principal,
            actor_executor_uri=delegatee,
            delegation_uri=delegation_uri,
            dto_role="supervisor",
            trip_role="supervisor.approve",
            action="approve",
        ),
    )
    assert signed["verified"] is True
    assert signed["delegation_uri"] == delegation_uri


def test_energy_consumption_and_railpact_ledger_entries() -> None:
    sb = _FakeSupabase()
    uri = "v://cn.涓寳/executor/energy-a"
    _register(sb, uri=uri, role_token="inspection", name="鑳借€楁墽琛屼綋", holder="寮犱笁")

    for idx in range(5):
        out = sign_flow(
            sb=sb,
            body=SignPegRequest(
                doc_id=f"NINST-ENERGY-{idx}",
                body_hash=f"sha256:energy-{idx}",
                executor_uri=uri,
                dto_role="inspector",
                trip_role="inspector.submit",
                action="submit",
            ),
        )
        assert out["ok"] is True

    record = get_executor_flow(sb=sb, executor_uri=uri)
    assert record["executor"]["energy"]["consumed"] == 5
    assert len(sb._data["railpact_settlements"]) == 5
    for row in sb._data["railpact_settlements"]:
        assert float(row["amount"]) == 100.0
        assert str(row["trip_uri"]).startswith("v://")


def test_archive_signature_requires_ca_attestation() -> None:
    sb = _FakeSupabase()
    uri = "v://cn.涓寳/executor/archive-a"
    _register(sb, uri=uri, role_token="bridge-inspection", name="archive-executor", holder="zhangsan")

    with pytest.raises(HTTPException) as exc:
        sign_flow(
            sb=sb,
            body=SignPegRequest(
                doc_id="NINST-ARCHIVE-1",
                body_hash="sha256:archive-1",
                executor_uri=uri,
                dto_role="supervisor",
                trip_role="supervisor.approve",
                action="approve",
                signature_mode="archive",
            ),
        )
    assert exc.value.status_code == 422
    assert "ca_provider_required_for_archive" in str(exc.value.detail)

    out = sign_flow(
        sb=sb,
        body=SignPegRequest(
            doc_id="NINST-ARCHIVE-1",
            body_hash="sha256:archive-1",
            executor_uri=uri,
            dto_role="supervisor",
            trip_role="supervisor.approve",
            action="approve",
            signature_mode="archive",
            ca_provider="fadada",
            ca_signature_id="fd-sign-archive-1",
        ),
    )
    assert out["ok"] is True
    assert out["signature_mode"] == "archive"
    assert out["ca_provider"] == "fadada"
    assert out["ca_signature_id"] == "fd-sign-archive-1"

