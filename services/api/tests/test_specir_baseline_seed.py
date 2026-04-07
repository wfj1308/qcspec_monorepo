from __future__ import annotations

from services.api.domain.specir import integrations


def test_seed_specir_baseline_aggregates_results(monkeypatch) -> None:
    monkeypatch.setattr(
        integrations,
        "seed_builtin_qcspec_specir_catalog",
        lambda **_kwargs: {"ok": True, "saved_count": 5, "error_count": 0},
    )
    monkeypatch.setattr(
        integrations,
        "seed_builtin_qcspec_full_spu_library",
        lambda **_kwargs: {"ok": True, "saved_count": 9, "error_count": 0},
    )
    out = integrations.seed_specir_baseline(sb=object(), overwrite=False, include_full_spu=True)
    assert out["ok"] is True
    assert out["saved_count"] == 14
    assert out["error_count"] == 0
    assert "base_catalog" in out["details"]
    assert "full_spu_library" in out["details"]


def test_seed_specir_baseline_can_skip_full_spu(monkeypatch) -> None:
    monkeypatch.setattr(
        integrations,
        "seed_builtin_qcspec_specir_catalog",
        lambda **_kwargs: {"ok": True, "saved_count": 5, "error_count": 0},
    )
    called = {"full": False}

    def _full(**_kwargs):
        called["full"] = True
        return {"ok": True, "saved_count": 9, "error_count": 0}

    monkeypatch.setattr(integrations, "seed_builtin_qcspec_full_spu_library", _full)
    out = integrations.seed_specir_baseline(sb=object(), overwrite=False, include_full_spu=False)
    assert out["ok"] is True
    assert out["saved_count"] == 5
    assert out["error_count"] == 0
    assert called["full"] is False
