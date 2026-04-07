from __future__ import annotations

from typing import Any

from services.api.domain.documents.runtime.governance import register_document, search_documents
from services.api.domain.documents.runtime.specir_docpeg_v11 import (
    build_docpeg_specir_v11,
    project_docpeg_specir_v11_for_role,
)


def test_build_docpeg_specir_v11_includes_triprole_and_dtorole_fields() -> None:
    payload = build_docpeg_specir_v11(
        project_uri="v://cn.zhongbei/YADGS/",
        node_uri="v://cn.zhongbei/YADGS/docs/inspection/",
        source_utxo_id="GP-SRC-001",
        file_name="inspection-1.pdf",
        mime_type="application/pdf",
        storage_url="https://example.com/r.pdf",
        text_excerpt="rebar spacing check",
        ai_metadata={"doc_type": "quality-inspection", "summary": "quality check record"},
        tags=["inspection", "bridge"],
        trip_role="quality.check",
        dtorole_context="SUPERVISOR",
        required_trip_roles=["inspector.quality.check", "supervisor.approve"],
        dtorole_permissions={"SUPERVISOR": ["can_approve"]},
    )
    assert payload["schema_uri"] == "v://normref.com/schema/docpeg-specir-v1.1"
    assert payload["header"]["doc_type"] == "v://normref.com/doc-type/quality-inspection@v1"
    assert payload["header"]["trip_role"] == "quality.check"
    assert payload["header"]["dtorole_context"] == "SUPERVISOR"
    assert payload["gate"]["required_trip_roles"] == ["inspector.quality.check", "supervisor.approve"]
    assert "can_approve" in payload["gate"]["dtorole_permissions"]["SUPERVISOR"]
    assert payload["body"]["trip_context"]["trip_role"] == "quality.check"
    assert payload["proof"]["trip_proof_hash"]
    assert payload["state"]["current_trip_role"] == "quality.check"


def test_project_docpeg_specir_v11_for_public_filters_sensitive_fields() -> None:
    payload = build_docpeg_specir_v11(
        project_uri="v://cn.zhongbei/YADGS/",
        node_uri="v://cn.zhongbei/YADGS/docs/inspection/",
        source_utxo_id="GP-SRC-001",
        file_name="inspection-1.pdf",
        mime_type="application/pdf",
        storage_url="https://example.com/r.pdf",
        text_excerpt="rebar spacing check",
        ai_metadata={"doc_type": "quality-inspection", "summary": "quality check record"},
        trip_role="quality.check",
        dtorole_context="OWNER",
    )
    public = project_docpeg_specir_v11_for_role(spec=payload, dto_role="PUBLIC")
    assert "entry_rules" not in public["gate"]
    assert "items" not in public["body"]
    assert "signatures" not in public["proof"]
    assert public["state"]["lifecycle_stage"] == payload["state"]["lifecycle_stage"]


class _FakeTable:
    def __init__(self, name: str, store: dict[str, Any]) -> None:
        self._name = name
        self._store = store
        self._filters: list[tuple[str, Any]] = []

    def update(self, payload: dict[str, Any]) -> "_FakeTable":
        self._store.setdefault("updates", []).append((self._name, payload))
        return self

    def insert(self, payload: Any) -> "_FakeTable":
        self._store.setdefault("inserts", []).append((self._name, payload))
        return self

    def select(self, _expr: str) -> "_FakeTable":
        return self

    def eq(self, key: str, value: Any) -> "_FakeTable":
        self._filters.append((key, value))
        return self

    def in_(self, *_args: Any, **_kwargs: Any) -> "_FakeTable":
        return self

    def order(self, *_args: Any, **_kwargs: Any) -> "_FakeTable":
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_FakeTable":
        return self

    def execute(self) -> Any:
        class _R:
            data: list[dict[str, Any]]

        r = _R()
        if self._name == "proof_utxo":
            if any(k == "project_uri" for k, _ in self._filters):
                r.data = self._store.get("proof_rows", [])
            else:
                r.data = []
        else:
            r.data = []
        return r


class _FakeSB:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {"proof_rows": []}

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(name, self.store)


def test_register_document_embeds_spec_and_role_view(monkeypatch: Any) -> None:
    fake_sb = _FakeSB()
    captured: dict[str, Any] = {}

    class _FakeProofEngine:
        def __init__(self, _sb: Any) -> None:
            pass

        def get_by_id(self, _proof_id: str) -> dict[str, Any]:
            return {
                "project_uri": "v://cn.zhongbei/YADGS/",
                "segment_uri": "v://cn.zhongbei/YADGS/boq/403-1-2",
                "state_data": {"boq_item_uri": "v://cn.zhongbei/YADGS/boq/403-1-2"},
            }

        def create(self, *, proof_type: str, **kwargs: Any) -> dict[str, Any]:
            captured["proof_type"] = proof_type
            captured["create_kwargs"] = kwargs
            row = {"proof_id": kwargs.get("proof_id"), "proof_hash": "ROW-HASH-001", "state_data": kwargs.get("state_data", {})}
            fake_sb.store["proof_rows"] = [row]
            return row

    monkeypatch.setattr(
        "services.api.domain.documents.runtime.governance.ProofUTXOEngine",
        _FakeProofEngine,
    )
    monkeypatch.setattr(
        "services.api.domain.documents.runtime.governance._project_by_uri",
        lambda _sb, _uri: {"id": "P-1"},
    )

    out = register_document(
        sb=fake_sb,
        project_uri="v://cn.zhongbei/YADGS/",
        node_uri="v://cn.zhongbei/YADGS/docs/inspection/",
        source_utxo_id="GP-SRC-001",
        file_name="inspection-1.pdf",
        file_size=1024,
        mime_type="application/pdf",
        storage_path="p/docs/inspection-1.pdf",
        storage_url="https://example.com/inspection-1.pdf",
        text_excerpt="rebar test",
        ai_metadata={"doc_type": "quality-inspection", "summary": "quality check"},
        custom_metadata={},
        tags=["inspection"],
        executor_uri="v://executor/system/",
        trip_action="quality.check",
        dtorole_context="SUPERVISOR",
        doc_spec={"state": {"next_action": "start_review"}},
    )

    assert out["ok"] is True
    spec = out["docpeg_specir_v1_1"]
    assert spec["header"]["trip_role"] == "quality.check"
    assert spec["header"]["dtorole_context"] == "SUPERVISOR"
    assert spec["state"]["next_action"] == "start_review"
    assert spec["proof"]["proof_hash"] == "ROW-HASH-001"
    assert out["docpeg_specir_v1_1_view"]["header"]["dtorole_context"] == "SUPERVISOR"
    assert captured["proof_type"] in {"document", "archive"}


def test_search_documents_returns_role_projected_view(monkeypatch: Any) -> None:
    fake_sb = _FakeSB()
    spec = build_docpeg_specir_v11(
        project_uri="v://cn.zhongbei/YADGS/",
        node_uri="v://cn.zhongbei/YADGS/docs/inspection/",
        source_utxo_id="GP-SRC-001",
        file_name="inspection-1.pdf",
        mime_type="application/pdf",
        storage_url="https://example.com/r.pdf",
        text_excerpt="rebar spacing check",
        ai_metadata={"doc_type": "quality-inspection", "summary": "quality check record"},
        trip_role="quality.check",
    )
    fake_sb.store["proof_rows"] = [
        {
            "proof_id": "GP-DOC-1",
            "proof_hash": "HASH-1",
            "proof_type": "document",
            "project_uri": "v://cn.zhongbei/YADGS/",
            "segment_uri": "v://cn.zhongbei/YADGS/docs/inspection/",
            "created_at": "2026-04-07T00:00:00Z",
            "state_data": {
                "node_uri": "v://cn.zhongbei/YADGS/docs/inspection/",
                "file_name": "inspection-1.pdf",
                "mime_type": "application/pdf",
                "file_size": 123,
                "storage_url": "https://example.com/r.pdf",
                "doc_type": "quality-inspection",
                "discipline": "quality",
                "summary": "quality check",
                "tags": ["inspection"],
                "docpeg_specir_v1_1": spec,
                "doc_registry": True,
                "artifact_type": "governance_document",
            },
        }
    ]
    out = search_documents(
        sb=fake_sb,
        project_uri="v://cn.zhongbei/YADGS/",
        node_uri="v://cn.zhongbei/YADGS/docs/inspection/",
        dto_role="PUBLIC",
    )
    assert out["ok"] is True
    assert out["dto_role"] == "PUBLIC"
    assert out["count"] == 1
    view = out["cards"][0]["docpeg_specir_v1_1_view"]
    assert "entry_rules" not in view["gate"]
    assert "items" not in view["body"]

