"""Smoke tests for backend module bootstrap imports."""

from __future__ import annotations

import importlib


def test_main_module_importable() -> None:
    module = importlib.import_module("services.api.main")
    assert getattr(module, "app", None) is not None
