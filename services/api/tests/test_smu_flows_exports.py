from __future__ import annotations

from services.api.domain.smu import flows


def test_smu_flows_export_import_job_functions() -> None:
    assert callable(flows.start_smu_import_job)
    assert callable(flows.get_smu_import_job)
    assert callable(flows.get_active_smu_import_job)
