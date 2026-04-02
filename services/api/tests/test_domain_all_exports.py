from __future__ import annotations

import ast
from pathlib import Path


def _collect_defined_symbols(tree: ast.Module) -> set[str]:
    symbols: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
            continue
        if isinstance(node, ast.Import):
            for alias in node.names:
                symbols.add(alias.asname or alias.name.split(".")[-1])
            continue
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    symbols.add(alias.asname or alias.name)
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)
    return symbols


def _extract_all_names(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != "__all__":
                continue
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                return None
            if isinstance(value, (list, tuple)):
                return [item for item in value if isinstance(item, str)]
            return None
    return None


def test_domain_modules_all_exports_are_defined() -> None:
    domain_root = Path(__file__).resolve().parents[1] / "domain"
    offenders: list[str] = []
    for path in sorted(domain_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        all_names = _extract_all_names(tree)
        if not all_names:
            continue
        defined = _collect_defined_symbols(tree)
        missing = [name for name in all_names if name not in defined]
        if missing:
            offenders.append(f"{path}: {', '.join(missing)}")

    assert not offenders, (
        "Domain module __all__ contains names that are not defined/imported in the same module.\n"
        "Offenders:\n- " + "\n- ".join(offenders)
    )
