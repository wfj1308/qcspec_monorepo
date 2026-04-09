from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from services.api.domain.signpeg.flows import (
    sign_acceptance_condition_flow,
    submit_acceptance_flow,
    register_executor_flow,
)
from services.api.domain.signpeg.models import (
    AcceptanceConditionSignRequest,
    AcceptanceConclusion,
    AcceptanceOnApproved,
    AcceptanceSubmitRequest,
    CapacityProfile,
    EnergyProfile,
    ExecutorRegisterRequest,
    Skill,
)


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

    def select(self, _cols: str = "*"):
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
            inserted = [deepcopy(dict(row)) for row in rows]
            table_rows.extend(inserted)
            return SimpleNamespace(data=inserted)

        if self._op.kind == "upsert":
            op = dict(self._op.payload or {})
            row = deepcopy(dict(op.get("row") or {}))
            keys = [key.strip() for key in str(op.get("on_conflict") or "").split(",") if key.strip()]
            if not keys:
                table_rows.append(row)
                return SimpleNamespace(data=[row])
            hit = -1
            for idx, item in enumerate(table_rows):
                if all(item.get(key) == row.get(key) for key in keys):
                    hit = idx
                    break
            if hit >= 0:
                merged = {**table_rows[hit], **row}
                table_rows[hit] = merged
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
            "docpeg_acceptances": [],
            "docpeg_acceptance_conditions": [],
            "docpeg_component_locks": [],
            "docfinal_archives": [],
            "docpeg_boq_status": [],
            "docpeg_rectification_notices": [],
        }

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


def _skill(token: str) -> Skill:
    return Skill(
        skill_uri=f"v://normref.com/skill/{token}@v1",
        cert_no=f"CERT-{token}",
        issued_by="v://cn.mohurd/",
        valid_until=date.today() + timedelta(days=365),
        scope=[token],
        level="senior",
    )


def _register_supervisor(sb: _FakeSupabase, uri: str = "v://cn.中北/executor/zhang-san") -> None:
    register_executor_flow(
        sb=sb,
        body=ExecutorRegisterRequest(
            executor_uri=uri,
            name="监理执行体",
            org_uri="v://cn.中北/",
            skills=[_skill("bridge-inspection")],
            energy=EnergyProfile(time_cost=0.5, fee_rate=200.0, credit_limit=100, consumed=0),
            capacity=CapacityProfile(max_concurrent=10, current_load=0, overload_policy="reject"),
            holder_name="张三",
            holder_id="u-zhangsan",
            holder_since=datetime.now(UTC) - timedelta(days=30),
        ),
    )


def _seed_pre_approved_states(sb: _FakeSupabase, doc_ids: list[str]) -> None:
    for doc_id in doc_ids:
        sb.table("docpeg_states").upsert(
            {
                "doc_id": doc_id,
                "lifecycle_stage": "approved",
                "all_signed": True,
                "state_data": {"seed": True},
                "updated_at": datetime.now(UTC).isoformat(),
            },
            on_conflict="doc_id",
        ).execute()
        sb.table("gate_trips").insert(
            {
                "trip_uri": f"v://cn.大锦/DJGS/trip/seed/{doc_id}",
                "doc_id": doc_id,
                "verified": True,
            }
        ).execute()


def test_acceptance_qualified_triggers_finalproof_payment_archive_and_lock() -> None:
    sb = _FakeSupabase()
    _register_supervisor(sb)
    pre_docs = ["BR2-001", "BR7-001", "BR11-001", "BR9-001", "BR13-001"]
    _seed_pre_approved_states(sb, pre_docs)

    out = submit_acceptance_flow(
        sb=sb,
        body=AcceptanceSubmitRequest(
            acceptance_id="ACC-64-001",
            component_uri="v://cn.大锦/DJGS/pile/K12+340-桩基1#",
            doc_id="BR64-001",
            body_hash="sha256:acc64-qualified",
            executor_uri="v://cn.中北/executor/zhang-san",
            dto_role="supervisor",
            trip_role="acceptance.approve",
            action="approve",
            pre_doc_ids=pre_docs,
            conclusion=AcceptanceConclusion(result="qualified", conditions=[], remarks="ok"),
            on_approved=AcceptanceOnApproved(
                generate_final_proof=True,
                update_boq="403-1-2",
                trigger_railpact=True,
                archive_to_docfinal=True,
                lock_component_uri=True,
            ),
            payment_amount=88000.0,
            ca_provider="fadada",
            ca_signature_id="fd-sign-acc64-001",
        ),
    )
    assert out["ok"] is True
    assert out["result"] == "qualified"
    assert str(out["trip_uri"]).startswith("v://")
    assert str(out["final_proof_uri"]).startswith("v://")
    assert out["boq_status"] == "PROOF_VERIFIED"
    assert out["railpact_triggered"] is True
    assert out["archived_to_docfinal"] is True
    assert out["component_locked"] is True

    state = sb._data["docpeg_states"][-1]
    assert state["doc_id"] == "BR64-001"
    assert state["lifecycle_stage"] == "approved"
    assert state["all_signed"] is True
    assert len(sb._data["docfinal_archives"]) == 1
    assert len(sb._data["docpeg_component_locks"]) == 1
    assert len(sb._data["railpact_settlements"]) == 1


def test_acceptance_rejected_keeps_history_and_reaccept_works() -> None:
    sb = _FakeSupabase()
    _register_supervisor(sb)
    pre_docs = ["BR2-002", "BR7-002", "BR11-002", "BR9-002", "BR13-002"]
    _seed_pre_approved_states(sb, pre_docs)

    reject_out = submit_acceptance_flow(
        sb=sb,
        body=AcceptanceSubmitRequest(
            acceptance_id="ACC-64-002",
            component_uri="v://cn.大锦/DJGS/pile/K12+341-桩基2#",
            doc_id="BR64-002",
            body_hash="sha256:acc64-reject",
            executor_uri="v://cn.中北/executor/zhang-san",
            action="reject",
            trip_role="acceptance.reject",
            pre_doc_ids=pre_docs,
            conclusion=AcceptanceConclusion(
                result="rejected",
                conditions=[],
                remarks="桩身混凝土强度不足，实测28MPa < 设计C30",
            ),
            ca_provider="fadada",
            ca_signature_id="fd-sign-acc64-002-reject",
        ),
    )
    assert reject_out["result"] == "rejected"
    reject_trip = str(reject_out["trip_uri"])
    assert len(sb._data["docpeg_rectification_notices"]) == 1
    for doc_id in pre_docs:
        rows = [row for row in sb._data["docpeg_states"] if row["doc_id"] == doc_id]
        assert rows[-1]["lifecycle_stage"] == "draft"

    _seed_pre_approved_states(sb, pre_docs)
    approve_out = submit_acceptance_flow(
        sb=sb,
        body=AcceptanceSubmitRequest(
            acceptance_id="ACC-64-002",
            component_uri="v://cn.大锦/DJGS/pile/K12+341-桩基2#",
            doc_id="BR64-002",
            body_hash="sha256:acc64-reapprove",
            executor_uri="v://cn.中北/executor/zhang-san",
            action="approve",
            trip_role="acceptance.approve",
            pre_doc_ids=pre_docs,
            pre_rejection_trip_uri=reject_trip,
            conclusion=AcceptanceConclusion(result="qualified", remarks="整改后复验通过"),
            ca_provider="fadada",
            ca_signature_id="fd-sign-acc64-002-approve",
        ),
    )
    assert approve_out["result"] == "qualified"
    acceptance_rows = [row for row in sb._data["docpeg_acceptances"] if row["acceptance_id"] == "ACC-64-002"]
    assert len(acceptance_rows) == 1
    latest = acceptance_rows[0]
    assert latest["status"] == "qualified"
    assert latest["pre_rejection_trip_uri"] == reject_trip
    actions = [str(row.get("action")) for row in sb._data["gate_trips"] if row.get("doc_id") == "BR64-002"]
    assert "acceptance.reject" in actions
    assert "acceptance.approve" in actions


def test_conditional_acceptance_promotes_to_qualified_after_all_conditions_signed() -> None:
    sb = _FakeSupabase()
    _register_supervisor(sb)
    pre_docs = ["BR2-003", "BR7-003", "BR11-003", "BR9-003", "BR13-003"]
    _seed_pre_approved_states(sb, pre_docs)

    conditional = submit_acceptance_flow(
        sb=sb,
        body=AcceptanceSubmitRequest(
            acceptance_id="ACC-64-003",
            component_uri="v://cn.大锦/DJGS/pile/K12+342-桩基3#",
            doc_id="BR64-003",
            body_hash="sha256:acc64-conditional",
            executor_uri="v://cn.中北/executor/zhang-san",
            action="conditional_approve",
            trip_role="acceptance.conditional_approve",
            pre_doc_ids=pre_docs,
            conclusion=AcceptanceConclusion(
                result="conditional",
                conditions=["补齐外观复测照片", "复核资料签章页"],
                remarks="有条件合格",
            ),
            on_approved=AcceptanceOnApproved(update_boq="403-1-2"),
            ca_provider="fadada",
            ca_signature_id="fd-sign-acc64-003-conditional",
        ),
    )
    assert conditional["result"] == "conditional"
    assert len(sb._data["docpeg_acceptance_conditions"]) == 2

    cond1 = sign_acceptance_condition_flow(
        sb=sb,
        body=AcceptanceConditionSignRequest(
            acceptance_id="ACC-64-003",
            condition_id="COND-001",
            executor_uri="v://cn.中北/executor/zhang-san",
            body_hash="sha256:cond1",
            ca_provider="fadada",
            ca_signature_id="fd-sign-cond-001",
        ),
    )
    assert cond1["signed"] is True
    assert cond1["acceptance_promoted"] is False

    cond2 = sign_acceptance_condition_flow(
        sb=sb,
        body=AcceptanceConditionSignRequest(
            acceptance_id="ACC-64-003",
            condition_id="COND-002",
            executor_uri="v://cn.中北/executor/zhang-san",
            body_hash="sha256:cond2",
            ca_provider="fadada",
            ca_signature_id="fd-sign-cond-002",
        ),
    )
    assert cond2["signed"] is True
    assert cond2["acceptance_promoted"] is True
    assert str(cond2["final_proof_uri"]).startswith("v://")

    acceptance_rows = [row for row in sb._data["docpeg_acceptances"] if row["acceptance_id"] == "ACC-64-003"]
    assert acceptance_rows[0]["status"] == "qualified"
    state_rows = [row for row in sb._data["docpeg_states"] if row["doc_id"] == "BR64-003"]
    assert state_rows[-1]["lifecycle_stage"] == "approved"
    assert state_rows[-1]["all_signed"] is True
