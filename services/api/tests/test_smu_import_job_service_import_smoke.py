from __future__ import annotations

import importlib


def test_smu_import_job_service_importable() -> None:
    module = importlib.import_module("services.api.smu_import_job_service")
    assert hasattr(module, "start_smu_import_job")
