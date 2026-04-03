"""
ComponentUTXO gate runner.

This script provides a single entrypoint for local/CI gate checks:
1) core ComponentUTXO unit tests
2) settlement integration tests
3) Beam-L3 offline demo smoke
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print(f"[RUN] {' '.join(command)}")
    proc = subprocess.run(command, cwd=str(cwd), env=env)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="ComponentUTXO local/CI gate")
    parser.add_argument("--skip-demo", action="store_true", help="Skip offline Beam-L3 demo execution")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    existing_python_path = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = (
        str(repo_root)
        if not existing_python_path
        else str(repo_root) + os.pathsep + existing_python_path
    )

    _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "services/api/tests/test_triprole_component_utxo.py",
            "services/api/tests/test_triprole_action_settlement.py",
            "services/api/tests/test_component_utxo_beam_l3_demo_smoke.py",
            "-q",
        ],
        cwd=repo_root,
        env=env,
    )

    if not args.skip_demo:
        _run(
            [
                sys.executable,
                "tools/acceptance/component_utxo_beam_l3_demo.py",
                "--skip-docpeg",
                "--output-dir",
                "tools/acceptance/out/component_utxo_beam_l3_gate",
            ],
            cwd=repo_root,
            env=env,
        )

    print("[DONE] component_utxo_gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
