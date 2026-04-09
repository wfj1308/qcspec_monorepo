from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from services.api.dependencies import (
    get_boqpeg_service,
    get_docpeg_execution_gate_service,
    get_smu_service,
    require_auth_identity,
)
from services.api.infrastructure.http.app_factory import create_app


class _FakeBOQPegService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def product_manifest(self) -> dict[str, Any]:
        self.calls.append(("product-manifest", {}))
        return {
            "ok": True,
            "product": {"name": "BOQPeg"},
            "mvp": {"phase1": {"done": True}},
        }

    async def phase1_bridge_report(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("phase1-bridge-report", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "report_uri": "v://project/demo/boqpeg/reports/bridge-pile/yk0-500-main",
            "proof": {"proof_id": "GP-BOQPEG-RPT-1", "proof_hash": "hash-demo", "committed": bool(commit)},
            "summary": {"full_line_piles": 5, "bridge_piles": 2, "delta_piles": 3},
        }

    async def normref_logic_scaffold(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("normref-logic-scaffold", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "levels": {
                "l0": "v://normref.com/core",
                "l1": "v://normref.com/construction/highway",
                "l2": "v://normref.com/qc/rebar-processing@v1",
            },
            "proof": {"proof_id": "GP-NORMREF-SCAFFOLD-1", "proof_hash": "hash-scaffold", "committed": bool(commit)},
        }

    async def tab_to_peg(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("normref-tab-to-peg", dict(kwargs)))
        return {
            "ok": True,
            "summary": {"gate_count": 2, "protocol_uri": "v://normref.com/qc/rebar-processing@v1"},
            "proof": {"proof_id": "GP-TAB-TO-PEG-1", "proof_hash": "hash-tab", "committed": bool(kwargs.get("commit"))},
        }

    async def import_upload(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("import", dict(kwargs)))
        return {
            "ok": True,
            "mode": "import",
            "commit": bool(kwargs.get("commit")),
            "project_uri": str(kwargs.get("project_uri") or ""),
            "filename": str(getattr(kwargs.get("file"), "filename", "")),
        }

    async def preview_upload(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("preview", dict(kwargs)))
        return {
            "ok": True,
            "mode": "preview",
            "project_uri": str(kwargs.get("project_uri") or ""),
            "filename": str(getattr(kwargs.get("file"), "filename", "")),
        }

    async def import_upload_async(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("import-async", dict(kwargs)))
        return {
            "ok": True,
            "mode": "import-async",
            "project_uri": str(kwargs.get("project_uri") or ""),
            "filename": str(getattr(kwargs.get("file"), "filename", "")),
        }

    async def get_import_job(self, *, job_id: str) -> dict[str, Any]:
        self.calls.append(("job", {"job_id": job_id}))
        return {"ok": True, "job_id": job_id, "state": "running", "progress": 42}

    async def get_active_import_job(self, *, project_uri: str) -> dict[str, Any]:
        self.calls.append(("active-job", {"project_uri": project_uri}))
        return {"ok": True, "active": True, "project_uri": project_uri, "job_id": "smu-import-1"}

    async def engine_parse(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("engine-parse", dict(kwargs)))
        return {
            "ok": True,
            "count": 1,
            "rows": [
                {
                    "code": "403-1-2",
                    "description": "Rebar processing and install",
                    "unit": "t",
                    "quantity": 9.8,
                    "unit_price": 100.0,
                    "amount": 980.0,
                }
            ],
        }

    async def forward_bom(self, *, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("forward-bom", {"body": body}))
        return {"ok": True, "engine": "forward-bom", "node_uri": body.get("node_uri")}

    async def reverse_conservation(self, *, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("reverse-conservation", {"body": body}))
        return {"ok": True, "engine": "reverse-conservation", "node_uri": body.get("node_uri")}

    async def progress_payment(self, *, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("payment-progress", {"body": body}))
        return {"ok": True, "engine": "payment-progress", "node_uri": body.get("node_uri")}

    async def unified_alignment(self, *, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("unified-align", {"body": body}))
        return {"ok": True, "engine": "unified-align", "node_uri": body.get("node_uri")}

    async def parse_design_manifest(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("design-parse", dict(kwargs)))
        return {
            "ok": True,
            "manifest": {
                "manifest_uri": "v://project/demo/design/manifest/m1",
                "components": [
                    {
                        "component_uri": "v://project/demo/design/component/pile-1",
                        "component_id": "pile-1",
                        "component_type": "pile",
                        "geometry": {"quantity": 10},
                    }
                ],
            },
        }

    async def match_design_boq(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("design-boq-match", dict(kwargs)))
        return {
            "ok": True,
            "summary": {"matched_rows": 1, "deviation_rows": 0},
            "matches": [
                {
                    "boq_code": "403-1-2",
                    "component_uri": "v://project/demo/design/component/pile-1",
                    "status": "consistent",
                }
            ],
        }

    async def bidirectional_closure(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("design-boq-closure", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "node_uri": body.get("node_uri"),
            "change_source": body.get("change_source"),
            "forward_actions": [{"action": "propose_boq_update"}],
            "reverse_actions": [{"action": "open_trip_review"}],
        }

    async def create_bridge_entity(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("bridge-entity-create", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "bridge_uri": "v://project/demo/bridge/yk0-500-main",
            "entity": {
                "bridge_name": body.get("bridge_name"),
                "total_piles": 0,
            },
        }

    async def bind_bridge_items(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("bridge-bind-sub-items", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "bridge_uri": "v://project/demo/bridge/yk0-500-main",
            "entity": {
                "bridge_name": body.get("bridge_name"),
                "total_piles": 2,
                "sub_items": body.get("sub_items") or [],
            },
        }

    async def create_pile_entity(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("pile-entity-create", {"body": body, "commit": commit}))
        project_uri = body.get("project_uri", "v://project/demo")
        bridge_name = body.get("bridge_name", "YK0+500-main")
        pile_id = body.get("pile_id", "P1")
        return {
            "ok": True,
            "project_uri": project_uri,
            "bridge_uri": f"{project_uri}/bridge/{bridge_name}",
            "pile_uri": f"{project_uri}/bridge/{bridge_name}/pile/{pile_id}",
            "pile_entity": {"pile_id": pile_id, "state_matrix": {"total_qc_tables": 2, "generated": 0, "signed": 0, "pending": 2}},
        }

    async def update_pile_state(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("pile-state-update", {"body": body, "commit": commit}))
        project_uri = body.get("project_uri", "v://project/demo")
        bridge_name = body.get("bridge_name", "YK0+500-main")
        pile_id = body.get("pile_id", "P1")
        return {
            "ok": True,
            "project_uri": project_uri,
            "bridge_uri": f"{project_uri}/bridge/{bridge_name}",
            "pile_uri": f"{project_uri}/bridge/{bridge_name}/pile/{pile_id}",
            "pile_entity": {"pile_id": pile_id, "state_matrix": {"total_qc_tables": 2, "generated": 2, "signed": 2, "pending": 0}},
        }

    async def get_pile_entity(self, *, project_uri: str, bridge_name: str, pile_id: str) -> dict[str, Any]:
        self.calls.append(("pile-entity-get", {"project_uri": project_uri, "bridge_name": bridge_name, "pile_id": pile_id}))
        return {
            "ok": True,
            "project_uri": project_uri,
            "bridge_uri": f"{project_uri}/bridge/{bridge_name}",
            "pile_uri": f"{project_uri}/bridge/{bridge_name}/pile/{pile_id}",
            "pile_entity": {"pile_id": pile_id, "state_matrix": {"total_qc_tables": 2, "generated": 2, "signed": 2, "pending": 0}},
        }

    async def full_line_piles(self, *, project_uri: str) -> dict[str, Any]:
        self.calls.append(("bridge-full-line-piles", {"project_uri": project_uri}))
        return {
            "ok": True,
            "project_uri": project_uri,
            "full_line_uri": f"{project_uri}/full-line",
            "pile_total": 5,
        }

    async def bridge_piles(self, *, project_uri: str, bridge_name: str) -> dict[str, Any]:
        self.calls.append(("bridge-piles", {"project_uri": project_uri, "bridge_name": bridge_name}))
        return {
            "ok": True,
            "project_uri": project_uri,
            "bridge_name": bridge_name,
            "total_piles": 2,
            "pile_items": [
                {"component_uri": f"{project_uri}/bridge/{bridge_name}/pile/1"},
                {"component_uri": f"{project_uri}/bridge/{bridge_name}/pile/2"},
            ],
        }

    async def create_bridge_schedule(
        self,
        *,
        project_uri: str,
        bridge_name: str,
        body: dict[str, Any],
        commit: bool = False,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "bridge-schedule-create",
                {
                    "project_uri": project_uri,
                    "bridge_name": bridge_name,
                    "body": body,
                    "commit": commit,
                },
            )
        )
        return {
            "ok": True,
            "bridge_uri": f"{project_uri}/bridge/{bridge_name}",
            "schedule_uri": f"{project_uri}/bridge/{bridge_name}/schedule/main",
            "schedule": {"current_progress": 0.0, "tasks": body.get("tasks") or []},
        }

    async def get_bridge_schedule(self, *, project_uri: str, bridge_name: str) -> dict[str, Any]:
        self.calls.append(("bridge-schedule-get", {"project_uri": project_uri, "bridge_name": bridge_name}))
        return {
            "ok": True,
            "bridge_uri": f"{project_uri}/bridge/{bridge_name}",
            "schedule_uri": f"{project_uri}/bridge/{bridge_name}/schedule/main",
            "schedule": {"current_progress": 40.0, "task_count": 5},
        }

    async def sync_bridge_schedule(
        self,
        *,
        project_uri: str,
        bridge_name: str,
        body: dict[str, Any],
        commit: bool = False,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "bridge-schedule-sync",
                {
                    "project_uri": project_uri,
                    "bridge_name": bridge_name,
                    "body": body,
                    "commit": commit,
                },
            )
        )
        return {
            "ok": True,
            "bridge_uri": f"{project_uri}/bridge/{bridge_name}",
            "schedule_uri": f"{project_uri}/bridge/{bridge_name}/schedule/main",
            "schedule": {"current_progress": 66.7},
            "proofs": {"sync_proof": {"proof_id": "GP-SYNC-1"}},
        }

    async def full_line_schedule(self, *, project_uri: str) -> dict[str, Any]:
        self.calls.append(("bridge-full-line-schedule", {"project_uri": project_uri}))
        return {
            "ok": True,
            "project_uri": project_uri,
            "full_line_schedule_uri": f"{project_uri}/full-line/schedule",
            "project_progress": 52.5,
        }

    async def create_process_chain(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("process-chain-create", {"body": body, "commit": commit}))
        project_uri = body.get("project_uri", "v://project/demo")
        bridge_name = body.get("bridge_name", "YK0+500-main")
        pile_id = body.get("pile_id", "P3")
        component_uri = body.get("component_uri", f"{project_uri}/bridge/{bridge_name}/pile/{pile_id}")
        return {
            "ok": True,
            "project_uri": project_uri,
            "component_uri": component_uri,
            "chain_uri": f"{component_uri}/process-chain/main",
            "chain": {"current_step": "pile-prepare-01", "state_matrix": {"total_steps": 6, "completed_steps": 0}},
        }

    async def get_process_chain(self, *, project_uri: str, component_uri: str) -> dict[str, Any]:
        self.calls.append(("process-chain-get", {"project_uri": project_uri, "component_uri": component_uri}))
        return {
            "ok": True,
            "project_uri": project_uri,
            "component_uri": component_uri,
            "chain_uri": f"{component_uri}/process-chain/main",
            "chain": {"current_step": "pile-hole-02", "state_matrix": {"total_steps": 6, "completed_steps": 1}},
        }

    async def submit_process_table(self, *, body: dict[str, Any], commit: bool = False) -> dict[str, Any]:
        self.calls.append(("process-chain-submit-table", {"body": body, "commit": commit}))
        project_uri = body.get("project_uri", "v://project/demo")
        bridge_name = body.get("bridge_name", "YK0+500-main")
        pile_id = body.get("pile_id", "P3")
        component_uri = body.get("component_uri", f"{project_uri}/bridge/{bridge_name}/pile/{pile_id}")
        return {
            "ok": True,
            "project_uri": project_uri,
            "component_uri": component_uri,
            "chain": {"current_step": "pile-rebar-03", "state_matrix": {"total_steps": 6, "completed_steps": 2}},
            "submission": {"table_name": body.get("table_name"), "result": body.get("result", "PASS")},
            "proofs": {"table_submission_proof": {"proof_id": "GP-PROCESS-TABLE-1"}},
        }

    async def get_process_materials(self, *, project_uri: str, component_uri: str) -> dict[str, Any]:
        self.calls.append(("process-materials-get", {"project_uri": project_uri, "component_uri": component_uri}))
        return {
            "ok": True,
            "project_uri": project_uri,
            "component_uri": component_uri,
            "materials": [
                {
                    "step_id": "pile-pour-04",
                    "step_name": "混凝土灌注",
                    "materials": [
                        {
                            "material_code": "concrete-c50",
                            "material_name": "C50混凝土",
                            "required": True,
                            "status": "pending",
                        }
                    ],
                }
            ],
            "summary": {"total_required": 1, "approved": 0, "pending": 1},
        }

    async def submit_iqc(self, *, body: dict[str, Any], commit: bool = True) -> dict[str, Any]:
        self.calls.append(("iqc-submit", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "iqc": {
                "material_code": body.get("material_code"),
                "batch_no": body.get("batch_no"),
                "status": body.get("status", "approved"),
                "iqc_uri": "v://cost/iqc/concrete-c50-batch001",
                "committed": bool(commit),
            },
        }

    async def create_inspection_batch(self, *, body: dict[str, Any], commit: bool = True) -> dict[str, Any]:
        self.calls.append(("inspection-batch-create", {"body": body, "commit": commit}))
        return {
            "ok": True,
            "inspection_batch": {
                "iqc_uri": body.get("iqc_uri"),
                "component_uri": body.get("component_uri"),
                "process_step": body.get("process_step"),
                "quantity": body.get("quantity"),
                "unit": body.get("unit", "m3"),
                "total_qty": 200,
                "used_qty": 28,
                "remaining": 172,
                "material_code": "concrete-c50",
                "inspection_batch_no": body.get("inspection_batch_no") or "JYP-2026-0405-001",
                "inspection_uri": "v://cost/inspection-batch/jyp-2026-0405-001",
                "inspection_result": body.get("inspection_result", "approved"),
                "committed": bool(commit),
                "utxo": {
                    "utxo_id": "UTXO-001",
                    "material_code": "concrete-c50",
                },
            },
        }

    async def get_material_utxo_by_iqc(self, *, iqc_uri: str) -> dict[str, Any]:
        self.calls.append(("material-utxo-by-iqc", {"iqc_uri": iqc_uri}))
        return {
            "ok": True,
            "scope": "iqc",
            "key": iqc_uri,
            "records": [{"utxo_id": "UTXO-001", "material_code": "concrete-c50"}],
            "summary": {"total_qty": 200, "used_qty": 28, "remaining": 172},
        }

    async def get_material_utxo_by_component(self, *, component_uri: str) -> dict[str, Any]:
        self.calls.append(("material-utxo-by-component", {"component_uri": component_uri}))
        return {
            "ok": True,
            "scope": "component",
            "key": component_uri,
            "records": [{"utxo_id": "UTXO-001", "material_code": "concrete-c50"}],
            "summary": {"total_cost": 16240},
        }


def _fake_auth_identity() -> dict[str, Any]:
    return {"user_id": "test-user", "roles": ["admin"], "v_uri": "v://project/demo/executor/test-user"}


class _FakeDocPegExecutionGate:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def enforce_execution(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        return {"ok": True, "operation": kwargs.get("operation")}


def _build_client(fake_service: _FakeBOQPegService) -> TestClient:
    app = create_app()
    fake_gate = _FakeDocPegExecutionGate()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_boqpeg_service] = lambda: fake_service
    app.dependency_overrides[get_docpeg_execution_gate_service] = lambda: fake_gate
    return TestClient(app)


def _build_client_asserting_no_smu_dependency(fake_service: _FakeBOQPegService) -> TestClient:
    app = create_app()
    fake_gate = _FakeDocPegExecutionGate()
    app.dependency_overrides[require_auth_identity] = _fake_auth_identity
    app.dependency_overrides[get_boqpeg_service] = lambda: fake_service
    app.dependency_overrides[get_docpeg_execution_gate_service] = lambda: fake_gate

    def _unexpected_smu_dependency() -> None:
        raise AssertionError("legacy genesis routes must not resolve SMUService dependency")

    app.dependency_overrides[get_smu_service] = _unexpected_smu_dependency
    return TestClient(app)


def test_boqpeg_api_preview_on_new_prefix(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        response = client.post(
            "/v1/qcspec/boqpeg/preview",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "P-1",
                "boq_root_uri": "v://project/demo/boq/400",
                "norm_context_root_uri": "v://project/demo/normContext",
                "owner_uri": "v://project/demo/role/system/",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["mode"] == "preview"
    assert payload["project_uri"] == "v://project/demo"
    assert payload["filename"] == "boq.csv"
    assert fake.calls and fake.calls[0][0] == "preview"


def test_boqpeg_product_manifest_and_phase1_report_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        manifest_res = client.get(
            "/v1/boqpeg/product/manifest",
            headers={"Authorization": "Bearer test-token"},
        )
        report_res = client.post(
            "/v1/listpeg/product/mvp/phase1/bridge-pile-report?commit=true",
            json={
                "project_uri": "v://project/demo",
                "bridge_name": "YK0+500-main",
                "node_uri": "v://project/demo/bridge/YK0+500-main",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert manifest_res.status_code == 200
    assert manifest_res.json()["product"]["name"] == "BOQPeg"
    assert report_res.status_code == 200
    assert report_res.json()["proof"]["committed"] is True

    call_names = [name for name, _ in fake.calls]
    assert "product-manifest" in call_names
    assert "phase1-bridge-report" in call_names


def test_boqpeg_normref_scaffold_and_tab_to_peg_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        scaffold_res = client.post(
            "/v1/boqpeg/product/normref/logic-scaffold?commit=true",
            json={"owner_uri": "v://normref.com/executor/system/"},
            headers={"Authorization": "Bearer test-token"},
        )
        tab_res = client.post(
            "/v1/listpeg/product/normref/tab-to-peg",
            files={"file": ("qc.csv", b"\xe6\xa3\x80\xe6\x9f\xa5\xe9\xa1\xb9,\xe5\x85\x81\xe8\xae\xb8\xe5\x81\x8f\xe5\xb7\xae,\xe8\xa7\x84\xe8\x8c\x83\n\xe7\x9b\xb4\xe5\xbe\x84\xe5\x81\x8f\xe5\xb7\xae,\xe2\x89\xa4 2%,GB50204-2015 5.3.2\n", "text/csv")},
            data={
                "protocol_uri": "v://normref.com/qc/rebar-processing@v1",
                "topology_component_count": "52",
                "forms_per_component": "2",
                "generated_qc_table_count": "3",
                "signed_pass_table_count": "0",
                "owner_uri": "v://normref.com/executor/system/",
                "commit": "true",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert scaffold_res.status_code == 200
    assert scaffold_res.json()["ok"] is True
    assert tab_res.status_code == 200
    assert tab_res.json()["summary"]["gate_count"] == 2

    call_names = [name for name, _ in fake.calls]
    assert "normref-logic-scaffold" in call_names
    assert "normref-tab-to-peg" in call_names
    tab_call = next((payload for name, payload in fake.calls if name == "normref-tab-to-peg"), {})
    assert int(tab_call.get("topology_component_count") or 0) == 52


def test_boqpeg_api_import_on_legacy_prefix(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        response = client.post(
            "/v1/proof/boqpeg/import",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "",
                "boq_root_uri": "",
                "norm_context_root_uri": "",
                "owner_uri": "",
                "commit": "true",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["mode"] == "import"
    assert payload["commit"] is True
    assert payload["project_uri"] == "v://project/demo"
    assert payload["filename"] == "boq.csv"
    assert fake.calls and fake.calls[0][0] == "import"


def test_boqpeg_import_accepts_bridge_mappings_json(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        response = client.post(
            "/v1/boqpeg/boqpeg/import",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "bridge_mappings_json": "{\"403-1-2\": \"YK0+500-main\"}",
                "commit": "false",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200
    import_call = next((payload for name, payload in fake.calls if name == "import"), {})
    assert isinstance(import_call.get("bridge_mappings"), dict)
    assert import_call.get("bridge_mappings", {}).get("403-1-2") == "YK0+500-main"


def test_boqpeg_api_async_and_job_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        async_res = client.post(
            "/v1/qcspec/boqpeg/import-async",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "P-1",
                "commit": "true",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        job_res = client.get(
            "/v1/qcspec/boqpeg/import-job/smu-import-xyz",
            headers={"Authorization": "Bearer test-token"},
        )
        active_res = client.get(
            "/v1/qcspec/boqpeg/import-job-active?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )
        job_public_res = client.get("/v1/qcspec/boqpeg/import-job-public/smu-import-xyz")
        active_public_res = client.get("/v1/qcspec/boqpeg/import-job-active-public?project_uri=v://project/demo")

    assert async_res.status_code == 200
    assert async_res.json()["mode"] == "import-async"
    assert job_res.status_code == 200
    assert job_res.json()["job_id"] == "smu-import-xyz"
    assert active_res.status_code == 200
    assert active_res.json()["active"] is True
    assert job_public_res.status_code == 200
    assert active_public_res.status_code == 200
    call_names = [name for name, _ in fake.calls]
    assert "import-async" in call_names
    assert "job" in call_names
    assert "active-job" in call_names


def test_legacy_smu_genesis_routes_proxy_to_boqpeg_service(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        import_res = client.post(
            "/v1/proof/smu/genesis/import",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "P-1",
                "commit": "true",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        async_res = client.post(
            "/v1/proof/smu/genesis/import-async",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "P-1",
                "commit": "true",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        job_res = client.get(
            "/v1/proof/smu/genesis/import-job/smu-import-legacy",
            headers={"Authorization": "Bearer test-token"},
        )
        job_public_res = client.get("/v1/proof/smu/genesis/import-job-public/smu-import-legacy")

    assert import_res.status_code == 200
    assert import_res.json()["mode"] == "import"
    assert async_res.status_code == 200
    assert async_res.json()["mode"] == "import-async"
    assert job_res.status_code == 200
    assert job_res.json()["job_id"] == "smu-import-legacy"
    assert job_public_res.status_code == 200

    call_names = [name for name, _ in fake.calls]
    assert "import" in call_names
    assert "import-async" in call_names
    assert "job" in call_names


def test_docpeg_prefixed_smu_genesis_routes_proxy_to_boqpeg_service(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        preview_res = client.post(
            "/v1/docpeg/smu/genesis/preview",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "P-1",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        active_res = client.get(
            "/v1/docpeg/smu/genesis/import-job-active?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )
        active_public_res = client.get("/v1/docpeg/smu/genesis/import-job-active-public?project_uri=v://project/demo")

    assert preview_res.status_code == 200
    assert preview_res.json()["mode"] == "preview"
    assert active_res.status_code == 200
    assert active_res.json()["active"] is True
    assert active_public_res.status_code == 200

    call_names = [name for name, _ in fake.calls]
    assert "preview" in call_names
    assert "active-job" in call_names


def test_legacy_genesis_aliases_never_resolve_smu_service(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client_asserting_no_smu_dependency(fake) as client:
        import_res = client.post(
            "/v1/proof/smu/genesis/import",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "project_id": "P-1",
                "commit": "true",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        preview_res = client.post(
            "/v1/docpeg/smu/genesis/preview",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={"project_uri": "v://project/demo"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert import_res.status_code == 200
    assert import_res.json()["mode"] == "import"
    assert preview_res.status_code == 200
    assert preview_res.json()["mode"] == "preview"


def test_boqpeg_engine_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        parse_res = client.post(
            "/v1/qcspec/boqpeg/engine/parse",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            headers={"Authorization": "Bearer test-token"},
        )
        forward_res = client.post(
            "/v1/qcspec/boqpeg/engine/forward-bom",
            json={"node_uri": "v://tz.nest-dam/bill28/spillway/concrete/"},
            headers={"Authorization": "Bearer test-token"},
        )
        reverse_res = client.post(
            "/v1/qcspec/boqpeg/engine/reverse-conservation",
            json={"node_uri": "v://tz.nest-dam/bill28/spillway/concrete/"},
            headers={"Authorization": "Bearer test-token"},
        )
        payment_res = client.post(
            "/v1/qcspec/boqpeg/engine/payment-progress",
            json={"node_uri": "v://tz.nest-dam/bill28/spillway/concrete/"},
            headers={"Authorization": "Bearer test-token"},
        )
        unified_res = client.post(
            "/v1/qcspec/boqpeg/engine/unified-align",
            json={"node_uri": "v://tz.nest-dam/bill28/spillway/concrete/"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert parse_res.status_code == 200
    assert parse_res.json()["count"] == 1
    assert forward_res.status_code == 200
    assert forward_res.json()["engine"] == "forward-bom"
    assert reverse_res.status_code == 200
    assert reverse_res.json()["engine"] == "reverse-conservation"
    assert payment_res.status_code == 200
    assert payment_res.json()["engine"] == "payment-progress"
    assert unified_res.status_code == 200
    assert unified_res.json()["engine"] == "unified-align"

    call_names = [name for name, _ in fake.calls]
    assert "engine-parse" in call_names
    assert "forward-bom" in call_names
    assert "reverse-conservation" in call_names
    assert "payment-progress" in call_names
    assert "unified-align" in call_names


def test_boqpeg_design_linkage_engine_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        design_parse_res = client.post(
            "/v1/qcspec/boqpeg/engine/design/parse",
            files={"file": ("drawing.pdf", b"Pile P-1 C30 YK0+500 Qty 10", "application/pdf")},
            data={"project_uri": "v://project/demo"},
            headers={"Authorization": "Bearer test-token"},
        )
        design_match_res = client.post(
            "/v1/qcspec/boqpeg/engine/design-boq/match",
            files={"file": ("boq.csv", b"item_no,name\n403-1-2,Rebar\n", "text/csv")},
            data={
                "project_uri": "v://project/demo",
                "design_manifest_json": "{\"manifest\": {\"components\": []}}",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        closure_res = client.post(
            "/v1/qcspec/boqpeg/engine/design-boq/closure?commit=true",
            json={
                "project_uri": "v://project/demo",
                "node_uri": "v://tz.nest-dam/bill28/spillway/concrete/",
                "change_source": "design",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert design_parse_res.status_code == 200
    assert design_parse_res.json()["ok"] is True
    assert design_match_res.status_code == 200
    assert design_match_res.json()["summary"]["matched_rows"] == 1
    assert closure_res.status_code == 200
    assert closure_res.json()["change_source"] == "design"

    call_names = [name for name, _ in fake.calls]
    assert "design-parse" in call_names
    assert "design-boq-match" in call_names
    assert "design-boq-closure" in call_names


def test_boqpeg_bridge_entity_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        create_res = client.post(
            "/v1/qcspec/boqpeg/bridge/entity?commit=true",
            json={
                "project_uri": "v://project/demo",
                "bridge_name": "YK0+500-main",
                "parent_section": "K0~K20",
                "boq_chapter": "403-1-2",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        bind_res = client.post(
            "/v1/qcspec/boqpeg/bridge/bind-sub-items?commit=true",
            json={
                "project_uri": "v://project/demo",
                "bridge_name": "YK0+500-main",
                "sub_items": [
                    {"component_uri": "v://project/demo/bridge/YK0+500-main/pile/1", "component_type": "pile"},
                    {"component_uri": "v://project/demo/bridge/YK0+500-main/pile/2", "component_type": "pile"},
                ],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        full_line_res = client.get(
            "/v1/qcspec/boqpeg/project/full-line/piles?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )
        bridge_res = client.get(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/piles?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )

    assert create_res.status_code == 200
    assert create_res.json()["ok"] is True
    assert bind_res.status_code == 200
    assert bind_res.json()["entity"]["total_piles"] == 2
    assert full_line_res.status_code == 200
    assert full_line_res.json()["pile_total"] == 5
    assert bridge_res.status_code == 200
    assert bridge_res.json()["total_piles"] == 2

    call_names = [name for name, _ in fake.calls]
    assert "bridge-entity-create" in call_names
    assert "bridge-bind-sub-items" in call_names
    assert "bridge-full-line-piles" in call_names
    assert "bridge-piles" in call_names


def test_boqpeg_pile_entity_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        create_res = client.post(
            "/v1/qcspec/boqpeg/pile/entity?commit=true",
            json={
                "project_uri": "v://project/demo",
                "bridge_name": "YK0+500-main",
                "pile_id": "P3",
                "pile_type": "bored-pile",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        update_res = client.post(
            "/v1/qcspec/boqpeg/pile/state?commit=true",
            json={
                "project_uri": "v://project/demo",
                "bridge_name": "YK0+500-main",
                "pile_id": "P3",
                "updates": {"total_qc_tables": 2, "generated": 2, "signed": 2, "pending": 0},
            },
            headers={"Authorization": "Bearer test-token"},
        )
        get_res = client.get(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/pile/P3?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )

    assert create_res.status_code == 200
    assert create_res.json()["pile_entity"]["pile_id"] == "P3"
    assert update_res.status_code == 200
    assert update_res.json()["pile_entity"]["state_matrix"]["pending"] == 0
    assert get_res.status_code == 200
    assert get_res.json()["pile_uri"].endswith("/pile/P3")

    call_names = [name for name, _ in fake.calls]
    assert "pile-entity-create" in call_names
    assert "pile-state-update" in call_names
    assert "pile-entity-get" in call_names


def test_boqpeg_bridge_schedule_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        create_res = client.post(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/schedule?commit=true",
            json={
                "project_uri": "v://project/demo",
                "baseline_start": "2026-04-01",
                "baseline_end": "2026-08-30",
                "tasks": [{"task_name": "pile foundation", "duration_days": 30}],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        get_res = client.get(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/schedule?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )
        sync_res = client.post(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/schedule/sync?commit=true",
            json={
                "project_uri": "v://project/demo",
                "completed_trip_ids": ["TRIP-001"],
                "task_progress_updates": {"TSK-1": 100},
            },
            headers={"Authorization": "Bearer test-token"},
        )
        full_line_res = client.get(
            "/v1/qcspec/boqpeg/project/full-line/schedule?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )

    assert create_res.status_code == 200
    assert create_res.json()["ok"] is True
    assert get_res.status_code == 200
    assert get_res.json()["schedule"]["current_progress"] == 40.0
    assert sync_res.status_code == 200
    assert sync_res.json()["schedule"]["current_progress"] == 66.7
    assert full_line_res.status_code == 200
    assert full_line_res.json()["project_progress"] == 52.5

    call_names = [name for name, _ in fake.calls]
    assert "bridge-schedule-create" in call_names
    assert "bridge-schedule-get" in call_names
    assert "bridge-schedule-sync" in call_names
    assert "bridge-full-line-schedule" in call_names


def test_boqpeg_process_chain_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    with _build_client(fake) as client:
        create_res = client.post(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/pile/P3/process-chain?commit=true",
            json={
                "project_uri": "v://project/demo",
                "chain_kind": "drilled_pile",
                "boq_item_ref": "v://project/demo/boq/403-1-2",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        get_res = client.get(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/pile/P3/process-chain?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )
        submit_res = client.post(
            "/v1/qcspec/boqpeg/bridge/YK0+500-main/pile/P3/process-chain/submit-table?commit=true",
            json={
                "project_uri": "v://project/demo",
                "table_name": "桥施7表",
                "proof_hash": "proof-bridge7",
                "result": "PASS",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert create_res.status_code == 200
    assert create_res.json()["chain"]["current_step"] == "pile-prepare-01"
    assert get_res.status_code == 200
    assert get_res.json()["chain"]["state_matrix"]["completed_steps"] == 1
    assert submit_res.status_code == 200
    assert submit_res.json()["submission"]["table_name"] == "桥施7表"

    call_names = [name for name, _ in fake.calls]
    assert "process-chain-create" in call_names
    assert "process-chain-get" in call_names
    assert "process-chain-submit-table" in call_names


def test_process_materials_and_iqc_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    component_uri = "v://project/demo/bridge/YK0+500-main/pile/P3"
    with _build_client(fake) as client:
        materials_res = client.get(
            f"/api/v1/process/{component_uri}/materials?project_uri=v://project/demo",
            headers={"Authorization": "Bearer test-token"},
        )
        iqc_res = client.post(
            "/api/v1/iqc/submit?commit=true",
            json={
                "project_uri": "v://project/demo",
                "component_uri": component_uri,
                "step_id": "pile-pour-04",
                "material_code": "concrete-c50",
                "material_name": "C50混凝土",
                "iqc_form_code": "试验施工表-混凝土检验",
                "batch_no": "batch001",
                "test_results": {"slump": 180, "strength": "C50"},
                "executor_uri": "v://project/demo/executor/inspector-a",
                "status": "approved",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert materials_res.status_code == 200
    assert materials_res.json()["summary"]["pending"] == 1
    assert iqc_res.status_code == 200
    assert iqc_res.json()["iqc"]["material_code"] == "concrete-c50"
    assert iqc_res.json()["iqc"]["committed"] is True

    call_names = [name for name, _ in fake.calls]
    assert "process-materials-get" in call_names
    assert "iqc-submit" in call_names


def test_inspection_batch_and_material_utxo_routes(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_GITPEG_WORKER_ENABLED", "0")
    monkeypatch.setenv("ERPNEXT_PUSH_WORKER_ENABLED", "0")
    fake = _FakeBOQPegService()
    component_uri = "v://project/demo/bridge/YK0+500-main/pile/P3"
    iqc_uri = "v://cost/iqc/concrete-c50-batch001"
    with _build_client(fake) as client:
        create_res = client.post(
            "/api/v1/inspection-batch/create?commit=true",
            json={
                "project_uri": "v://project/demo",
                "iqc_uri": iqc_uri,
                "component_uri": component_uri,
                "process_step": "pile-pour-04",
                "quantity": 28,
                "unit": "m3",
                "inspection_form": "bridge9",
                "inspection_batch_no": "JYP-2026-0405-001",
                "inspection_result": "approved",
                "executor_uri": "v://project/demo/executor/inspector-a",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        by_iqc_res = client.get(
            f"/api/v1/material-utxo/{iqc_uri}",
            headers={"Authorization": "Bearer test-token"},
        )
        by_component_res = client.get(
            f"/api/v1/material-utxo/component/{component_uri}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert create_res.status_code == 200
    assert create_res.json()["inspection_batch"]["remaining"] == 172
    assert by_iqc_res.status_code == 200
    assert by_iqc_res.json()["scope"] == "iqc"
    assert by_component_res.status_code == 200
    assert by_component_res.json()["scope"] == "component"

    call_names = [name for name, _ in fake.calls]
    assert "inspection-batch-create" in call_names
    assert "material-utxo-by-iqc" in call_names
    assert "material-utxo-by-component" in call_names
