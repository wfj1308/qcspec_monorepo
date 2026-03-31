"""Cached NormRef resolver service."""

from __future__ import annotations

import json
from typing import Any

from services.api.core.base import BaseService
from services.api.specdict_gate_service import get_spec_dict, resolve_dynamic_threshold


class NormRefResolverService(BaseService):
    _threshold_cache: dict[tuple[str, str], dict[str, Any]] = {}
    _spec_cache: dict[str, dict[str, Any]] = {}

    def resolve_threshold(self, *, gate_id: str, context: Any = "") -> dict[str, Any]:
        cache_key = (str(gate_id).strip(), json.dumps(context, ensure_ascii=False, sort_keys=True, default=str))
        if cache_key not in self._threshold_cache:
            self._threshold_cache[cache_key] = resolve_dynamic_threshold(
                sb=self.require_supabase(),
                gate_id=cache_key[0],
                context=context,
            )
        return self._threshold_cache[cache_key]

    def get_spec_dict(self, *, spec_dict_key: str) -> dict[str, Any]:
        key = str(spec_dict_key).strip()
        if key not in self._spec_cache:
            self._spec_cache[key] = get_spec_dict(sb=self.require_supabase(), spec_dict_key=key)
        return self._spec_cache[key]
