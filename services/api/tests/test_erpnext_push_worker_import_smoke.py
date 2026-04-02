from __future__ import annotations

import importlib


def test_erpnext_push_worker_module_importable() -> None:
    module = importlib.import_module("services.api.workers.erpnext_push_worker")
    assert hasattr(module, "ERPNextPushWorker")


def test_erpnext_push_worker_push_once_without_supabase(monkeypatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    module = importlib.import_module("services.api.workers.erpnext_push_worker")
    worker = module.ERPNextPushWorker()
    result = worker.push_once()
    assert result.get("ok") is False
    assert result.get("reason") == "supabase_not_configured"
