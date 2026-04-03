from __future__ import annotations

from pathlib import Path


def test_api_root_has_no_legacy_service_files() -> None:
    api_root = Path(__file__).resolve().parents[1]
    forbidden = sorted(api_root.glob("*_service.py"))
    forbidden += sorted(api_root.glob("*_flow_service.py"))

    assert not forbidden, (
        "services/api root must stay thin; move runtime helpers into "
        "services/api/domain/*/runtime or infrastructure modules.\n"
        f"Found:\n- " + "\n- ".join(str(path) for path in forbidden)
    )


def test_api_root_python_files_stay_thin_allowlist() -> None:
    api_root = Path(__file__).resolve().parents[1]
    current = {p.name for p in api_root.glob("*.py")}
    allowed = {
        "dependencies.py",
        "main.py",
    }

    unexpected = sorted(current - allowed)
    assert not unexpected, (
        "services/api root should only contain core entry/schema modules. "
        "Move business/runtime helpers to domain/*/runtime or infrastructure/*.\n"
        f"Unexpected:\n- " + "\n- ".join(unexpected)
    )
