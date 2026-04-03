"""Backward-compatible router shim; use services.api.routers.finance."""

from __future__ import annotations

from .finance import *  # noqa: F401,F403
