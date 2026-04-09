from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from services.api.domain.signpeg.flows import (
    add_org_member_flow,
    add_org_project_flow,
    add_executor_requires_flow,
    add_executor_certificate_flow,
    add_executor_skill_flow,
    check_executor_certificate_expiry_flow,
    get_org_branches_flow,
    get_org_members_flow,
    import_executors_flow,
    maintain_executor_flow,
    register_executorpeg_flow,
    search_executors_flow,
    use_executor_flow,
)
from services.api.domain.signpeg.runtime.signpeg import validate_executor
from services.api.domain.signpeg.models import (
    Certificate,
    CertificateAddRequest,
    ExecutorCreateRequest,
    ExecutorMaintainRequest,
    ExecutorImportRequest,
    ExecutorSearchRequest,
    ExecutorUseRequest,
    RequiresAddRequest,
    Skill,
    SkillAddRequest,
    ToolSpec,
    ReusableDetail,
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
            "san_executor_alerts": [],
        }

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(self, name)


def _cert(*, cert_id: str, days: int = 365) -> Certificate:
    return Certificate(
        cert_id=cert_id,
        cert_type="监理工程师证",
        cert_no=f"CERT-{cert_id}",
        issued_by="v://cn.住建部/",
        issued_date=date.today() - timedelta(days=30),
        valid_until=date.today() + timedelta(days=days),
        v_uri=f"v://cn.中北/cert/{cert_id}",
        status="active",
        scan_hash=f"sha256:{cert_id}",
    )


def _skill(uri: str) -> Skill:
    return Skill(
        skill_uri=uri,
        skill_name="桥梁监理",
        level=3,
        verified_by="v://normref.com/",
        valid_until=date.today() + timedelta(days=365),
        proof_uri="v://proof/skill/demo",
    )


def test_executorpeg_register_search_and_expiry() -> None:
    sb = _FakeSupabase()
    out = register_executorpeg_flow(
        sb=sb,
        body=ExecutorCreateRequest(
            name="张三",
            executor_type="human",
            org_uri="v://cn.中北/",
            certificates=[_cert(cert_id="a1", days=10)],
            skills=[_skill("v://normref.com/skill/bridge-inspection@v1")],
        ),
    )
    assert out["ok"] is True
    assert out["executor_uri"].startswith("v://cn.中北/executor/")
    assert str(out["registration_proof"]).startswith("PROOF-EXEC-")

    search = search_executors_flow(
        sb=sb,
        query=ExecutorSearchRequest(
            skill_uri="bridge-inspection",
            org_uri="v://cn.中北/",
            type="human",
            available=True,
        ),
    )
    assert search["ok"] is True
    assert len(search["items"]) == 1

    executor_id = str(out["executor_id"])
    add_cert = add_executor_certificate_flow(
        sb=sb,
        executor_id=executor_id,
        body=CertificateAddRequest(certificate=_cert(cert_id="b2", days=400)),
    )
    assert add_cert["ok"] is True
    assert len(add_cert["executor"]["certificates"]) == 2

    add_skill = add_executor_skill_flow(
        sb=sb,
        executor_id=executor_id,
        body=SkillAddRequest(skill=_skill("v://normref.com/skill/review@v1")),
    )
    assert add_skill["ok"] is True
    assert len(add_skill["executor"]["skills"]) == 2

    # Make one cert expired and run daily checker.
    sb._data["san_executors"][0]["certificates"][0]["valid_until"] = (date.today() - timedelta(days=1)).isoformat()
    check = check_executor_certificate_expiry_flow(sb=sb)
    assert check["ok"] is True
    assert len(check["suspended"]) == 1
    assert len(sb._data["san_executor_alerts"]) >= 1


def test_executorpeg_batch_import() -> None:
    sb = _FakeSupabase()
    out = import_executors_flow(
        sb=sb,
        body=ExecutorImportRequest(
            items=[
                ExecutorCreateRequest(
                    name="石玉山",
                    executor_type="human",
                    org_uri="v://cn.中北/",
                    certificates=[_cert(cert_id="s1", days=365)],
                    skills=[_skill("v://normref.com/skill/bridge-inspection@v1")],
                ),
                ExecutorCreateRequest(
                    name="桥梁AI引擎",
                    executor_type="ai",
                    org_uri="v://cn.中北/",
                    certificates=[_cert(cert_id="ai1", days=365)],
                    skills=[_skill("v://normref.com/skill/spec-interpretation@v1")],
                ),
            ]
        ),
    )
    assert out["ok"] is True
    assert out["count"] == 2
    assert len(sb._data["san_executors"]) == 2


def test_executorpeg_requires_use_and_maintain() -> None:
    sb = _FakeSupabase()
    tool = register_executorpeg_flow(
        sb=sb,
        body=ExecutorCreateRequest(
            name="Miller03",
            executor_type="tool",
            org_uri="v://cn.涓寳/",
            certificates=[_cert(cert_id="tool1", days=365)],
            skills=[],
            tool_spec=ToolSpec(
                tool_category="reusable",
                reusable=ReusableDetail(
                    purchase_price=45000,
                    expected_life=200,
                    current_uses=0,
                    remaining_uses=200,
                    maintenance_cycle=50,
                    next_maintenance_at=50,
                    depreciation_per_use=225.0,
                ),
            ),
        ),
    )
    human = register_executorpeg_flow(
        sb=sb,
        body=ExecutorCreateRequest(
            name="寮犱笁",
            executor_type="human",
            org_uri="v://cn.涓寳/",
            certificates=[_cert(cert_id="human1", days=365)],
            skills=[_skill("v://normref.com/skill/welding@v1")],
        ),
    )

    bind = add_executor_requires_flow(
        sb=sb,
        executor_id=str(human["executor_id"]),
        body=RequiresAddRequest(tool_executor_uris=[str(tool["executor_uri"])]),
    )
    assert bind["ok"] is True
    assert str(tool["executor_uri"]) in bind["executor"]["requires"]

    used = use_executor_flow(
        sb=sb,
        executor_id=str(tool["executor_id"]),
        body=ExecutorUseRequest(trip_id="TRIP-001", shifts=1, trip_role="construction.welding"),
    )
    assert used["ok"] is True
    assert used["executor"]["tool_spec"]["reusable"]["current_uses"] == 1

    maintained = maintain_executor_flow(
        sb=sb,
        executor_id=str(tool["executor_id"]),
        body=ExecutorMaintainRequest(note="routine"),
    )
    assert maintained["ok"] is True
    assert str(maintained["maintenance_proof"]).startswith("PROOF-EXEC-MAINT-")


def test_org_executor_registration_hierarchy_and_gate() -> None:
    sb = _FakeSupabase()
    org = register_executorpeg_flow(
        sb=sb,
        body=ExecutorCreateRequest(
            name="中北工程设计咨询有限公司",
            executor_type="org",
            org_uri="",
            certificates=[_cert(cert_id="org1", days=365)],
            skills=[],
            org_spec={
                "org_type": "designer",
                "business_license": "91610000XXXXXXXX",
                "qualification_summary": {
                    "工程设计综合": "甲级",
                    "工程勘察综合": "甲级",
                    "工程监理": "甲级",
                    "工程咨询": "甲级",
                    "城乡规划编制": "甲级",
                },
                "branch_count": 50,
            },
            business_license_file="mock-license-file-content",
        ),
    )
    assert org["ok"] is True
    assert str(org["executor"]["executor_type"]) == "org"
    assert str(org["executor_uri"]).startswith("v://cn.")
    assert int(org["executor"]["org_spec"]["branch_count"]) == 50
    assert len(org["executor"]["org_spec"]["branches"]) == 50
    assert str(org["executor"]["org_spec"]["business_license_scan_hash"]).startswith("sha256:")

    member = register_executorpeg_flow(
        sb=sb,
        body=ExecutorCreateRequest(
            name="王治",
            executor_type="human",
            org_uri=str(org["executor_uri"]),
            certificates=[_cert(cert_id="m1", days=365)],
            skills=[_skill("v://normref.com/skill/bridge-inspection@v1")],
        ),
    )
    add_member = add_org_member_flow(
        sb=sb,
        org_uri=str(org["executor_uri"]),
        body={"member_executor_uri": str(member["executor_uri"])},
    )
    assert add_member["ok"] is True

    members = get_org_members_flow(sb=sb, org_uri=str(org["executor_uri"]))
    branches = get_org_branches_flow(sb=sb, org_uri=str(org["executor_uri"]))
    add_project = add_org_project_flow(
        sb=sb,
        org_uri=str(org["executor_uri"]),
        body={"project_uri": "v://cn.大锦/DJGS"},
    )
    assert members["ok"] is True and len(members["members"]) >= 1
    assert branches["ok"] is True and int(branches["branch_count"]) == 50
    assert add_project["ok"] is True and "v://cn.大锦/DJGS" in add_project["project_uris"]

    gate_before = validate_executor(
        sb,
        executor_uri=str(member["executor_uri"]),
        required_skill="bridge-inspection",
        trip_role="supervisor.approve",
    )
    assert gate_before["passed"] is True

    for row in sb._data["san_executors"]:
        if row.get("executor_uri") == str(org["executor_uri"]):
            row["certificates"][0]["valid_until"] = (date.today() - timedelta(days=1)).isoformat()
            row["certificates"][0]["status"] = "revoked"
            break
    gate_after = validate_executor(
        sb,
        executor_uri=str(member["executor_uri"]),
        required_skill="bridge-inspection",
        trip_role="supervisor.approve",
    )
    assert gate_after["passed"] is False
