from __future__ import annotations

from pathlib import Path
import re


_FORBIDDEN_FROM_PATTERN = re.compile(
    r"^\s*from\s+services\.api\.[A-Za-z0-9_]+(?:_service|_flow_service)\s+import\s+",
    re.MULTILINE,
)
_FORBIDDEN_IMPORT_PATTERN = re.compile(
    r"^\s*import\s+services\.api\.[A-Za-z0-9_]+(?:_service|_flow_service)\b",
    re.MULTILINE,
)


def _router_py_files() -> list[Path]:
    router_root = Path(__file__).resolve().parents[1] / "routers"
    return sorted(router_root.rglob("*.py"))


def test_router_modules_do_not_import_legacy_service_modules_directly() -> None:
    offenders: list[str] = []
    for file_path in _router_py_files():
        text = file_path.read_text(encoding="utf-8")
        if _FORBIDDEN_FROM_PATTERN.search(text) or _FORBIDDEN_IMPORT_PATTERN.search(text):
            offenders.append(str(file_path))

    assert not offenders, (
        "Router modules must not import legacy *_service/*_flow_service modules directly. "
        "Use domain services/helpers as the boundary.\n"
        f"Offenders:\n- " + "\n- ".join(offenders)
    )
