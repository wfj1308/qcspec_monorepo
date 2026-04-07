from __future__ import annotations

from typing import Any

from services.api.domain.boqpeg import import_boq_upload_chain
from services.api.domain.boq.runtime import utxo as boq_utxo_runtime


def _sample_csv_bytes() -> bytes:
    csv_text = (
        "item_no,name,unit,division,subdivision,hierarchy,design_quantity,unit_price,approved_quantity\n"
        "403-1-2,Rebar processing and install,t,Bridge,Rebar,Bridge/Rebar,10,100,9.8\n"
    )
    return csv_text.encode("utf-8")


def test_boqpeg_import_commit_mode_writes_created_rows(monkeypatch) -> None:
    created_calls: list[dict[str, Any]] = []

    class _FakeEngine:
        def __init__(self, _sb: Any) -> None:
            pass

        def create(self, **kwargs: Any) -> dict[str, Any]:
            created_calls.append(dict(kwargs))
            return {
                "proof_id": kwargs.get("proof_id", ""),
                "proof_type": kwargs.get("proof_type", ""),
                "segment_uri": kwargs.get("segment_uri", ""),
                "state_data": kwargs.get("state_data", {}) or {},
            }

    monkeypatch.setattr(boq_utxo_runtime, "ProofUTXOEngine", _FakeEngine)

    result = import_boq_upload_chain(
        sb=None,
        project_uri="v://project/demo",
        project_id=None,
        upload_file_name="boq.csv",
        upload_content=_sample_csv_bytes(),
        boq_root_uri="v://project/demo/boq/400",
        norm_context_root_uri="v://project/demo/normContext",
        owner_uri="v://project/demo/role/system/",
        commit=True,
    )

    chain = result["chain"]
    assert result["ok"] is True
    assert int(chain.get("success_count") or 0) > 0
    assert len(chain.get("created") or []) > 0
    assert len(created_calls) == len(chain.get("created") or [])
    assert all(str(call.get("proof_type") or "") == "zero_ledger" for call in created_calls)
    assert str((chain.get("scan_complete_proof") or {}).get("proof_id") or "").startswith("GP-BOQ-SCAN-")
