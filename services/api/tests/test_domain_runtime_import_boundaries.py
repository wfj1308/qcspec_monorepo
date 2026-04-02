from __future__ import annotations

from pathlib import Path
import re


_FORBIDDEN_ROOT_FROM_PATTERN = re.compile(
    r"^\s*from\s+services\.api\.([A-Za-z0-9_]+)\s+import\s+",
    re.MULTILINE,
)
_FORBIDDEN_ROOT_IMPORT_PATTERN = re.compile(
    r"^\s*import\s+services\.api\.([A-Za-z0-9_]+)\b",
    re.MULTILINE,
)


def _runtime_py_files() -> list[Path]:
    domain_root = Path(__file__).resolve().parents[1] / "domain"
    return sorted(p for p in domain_root.rglob("*.py") if "runtime" in p.parts)


def test_domain_runtime_modules_do_not_import_root_api_modules_directly() -> None:
    offenders: list[str] = []
    for file_path in _runtime_py_files():
        text = file_path.read_text(encoding="utf-8")
        if _FORBIDDEN_ROOT_FROM_PATTERN.search(text) or _FORBIDDEN_ROOT_IMPORT_PATTERN.search(text):
            offenders.append(str(file_path))

    assert not offenders, (
        "Domain runtime modules must not import services.api.<root_module> directly. "
        "Use domain-local integrations.py or infrastructure modules instead.\n"
        f"Offenders:\n- " + "\n- ".join(offenders)
    )
