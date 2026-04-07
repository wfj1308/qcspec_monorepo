from __future__ import annotations

from pathlib import Path
import re


_FORBIDDEN_FROM_PATTERN = re.compile(
    r"^\s*from\s+services\.api\.domain(?:\.|\s+import\s+)",
    re.MULTILINE,
)
_FORBIDDEN_IMPORT_PATTERN = re.compile(
    r"^\s*import\s+services\.api\.domain(?:\.|\b)",
    re.MULTILINE,
)

# Temporary exception to keep Step 1 non-breaking.
# Step 3 must remove this allowlist by decoupling NormRefResolverService.
_LEGACY_ALLOWLIST: set[str] = set()


def _core_py_files() -> list[Path]:
    core_root = Path(__file__).resolve().parents[1] / "core"
    return sorted(p for p in core_root.rglob("*.py") if "__pycache__" not in p.parts)


def test_core_modules_do_not_import_domain_modules_directly() -> None:
    offenders: list[str] = []
    for file_path in _core_py_files():
        rel = str(file_path.relative_to(file_path.parents[1]).as_posix())
        if not rel.startswith("core/"):
            continue
        rel_under_core = rel[len("core/") :]
        text = file_path.read_text(encoding="utf-8")
        has_forbidden = _FORBIDDEN_FROM_PATTERN.search(text) or _FORBIDDEN_IMPORT_PATTERN.search(text)
        if not has_forbidden:
            continue
        if rel_under_core in _LEGACY_ALLOWLIST:
            continue
        offenders.append(rel_under_core)

    assert not offenders, (
        "Core modules must not import services.api.domain.* directly. "
        "Use ports/adapters via dependencies injection.\n"
        f"Offenders:\n- " + "\n- ".join(offenders)
    )
