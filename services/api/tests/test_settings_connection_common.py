from __future__ import annotations

from services.api.domain.settings.connection_common import (
    body_field,
    body_text,
    clamp_timeout_seconds,
)


class _Obj:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_body_field_supports_dict_and_object() -> None:
    assert body_field({"token": "abc"}, "token", "x") == "abc"
    assert body_field(_Obj(token="abc"), "token", "x") == "abc"
    assert body_field({}, "missing", "fallback") == "fallback"
    assert body_field(_Obj(), "missing", "fallback") == "fallback"


def test_body_text_trims_values_and_applies_default() -> None:
    assert body_text({"name": "  qc  "}, "name") == "qc"
    assert body_text(_Obj(name="  qc  "), "name") == "qc"
    assert body_text({}, "name", "  default  ") == "default"


def test_clamp_timeout_seconds_handles_invalid_and_bounds() -> None:
    assert clamp_timeout_seconds(None, default_ms=15000) == 15.0
    assert clamp_timeout_seconds("bad", default_ms=5000) == 5.0
    assert clamp_timeout_seconds(1, default_ms=5000) == 2.0
    assert clamp_timeout_seconds(60000, default_ms=5000) == 30.0
