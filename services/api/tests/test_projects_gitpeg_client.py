from __future__ import annotations

from services.api.domain.projects.gitpeg_client import (
    _append_query_params,
    _gitpeg_registrar_config,
    _gitpeg_registrar_ready,
    _normalize_registration_mode,
    _timeout_seconds,
    _to_bool,
)


def test_to_bool_supports_common_truthy_values() -> None:
    assert _to_bool(True) is True
    assert _to_bool("1") is True
    assert _to_bool("YES") is True
    assert _to_bool("on") is True
    assert _to_bool("false") is False
    assert _to_bool("") is False


def test_normalize_registration_mode_defaults_to_domain() -> None:
    assert _normalize_registration_mode("DOMAIN") == "DOMAIN"
    assert _normalize_registration_mode("shell") == "SHELL"
    assert _normalize_registration_mode("unknown") == "DOMAIN"


def test_append_query_params_preserves_existing_values() -> None:
    url = "https://example.com/callback?a=1"
    out = _append_query_params(url, {"a": "new", "b": "2"})
    assert "a=1" in out
    assert "b=2" in out


def test_gitpeg_registrar_config_uses_custom_values() -> None:
    cfg = _gitpeg_registrar_config(
        {
            "gitpeg_enabled": "true",
            "gitpeg_partner_code": "p1",
            "gitpeg_industry_code": "i1",
            "gitpeg_client_id": "cid",
            "gitpeg_client_secret": "sec",
            "gitpeg_module_candidates_csv": "proof,utrip",
            "gitpeg_registration_mode": "shell",
        }
    )
    assert cfg["enabled"] is True
    assert cfg["registration_mode"] == "SHELL"
    assert cfg["modules"] == ["proof", "utrip"]


def test_gitpeg_registrar_ready_requires_all_core_fields() -> None:
    ready = _gitpeg_registrar_ready(
        {
            "base_url": "https://gitpeg.cn",
            "partner_code": "p1",
            "industry_code": "i1",
            "client_id": "cid",
            "client_secret": "sec",
        }
    )
    not_ready = _gitpeg_registrar_ready(
        {
            "base_url": "https://gitpeg.cn",
            "partner_code": "",
            "industry_code": "i1",
            "client_id": "cid",
            "client_secret": "sec",
        }
    )
    assert ready is True
    assert not_ready is False


def test_timeout_seconds_clamps_to_safe_range() -> None:
    assert _timeout_seconds(None, default=15.0) == 15.0
    assert _timeout_seconds("bad", default=10.0) == 10.0
    assert _timeout_seconds(0.2, default=10.0) == 2.0
    assert _timeout_seconds(99, default=10.0) == 30.0
