from __future__ import annotations

from services.api.domain.reporting.runtime import reports_generation


def test_generate_report_task_bootstraps_supabase_client(monkeypatch) -> None:
    called: dict[str, tuple[str, str]] = {}

    def fake_create_client(url: str, key: str):
        called["args"] = (url, key)
        raise RuntimeError("stop after bootstrap")

    monkeypatch.setattr(reports_generation, "create_client", fake_create_client)

    reports_generation._generate_report_task(
        project_id="p",
        ent_id="e",
        location=None,
        date_from=None,
        date_to=None,
        supabase_url="https://example.supabase.co",
        supabase_key="service-role-key",
    )

    assert called["args"] == ("https://example.supabase.co", "service-role-key")
