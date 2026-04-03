from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_component_utxo_beam_l3_demo_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "tools" / "acceptance" / "component_utxo_beam_l3_demo.py"
    payload_file = repo_root / "tools" / "acceptance" / "config" / "component_utxo_beam_l3.sample.json"
    out_dir = tmp_path / "component_utxo_beam_l3"
    env = dict(os.environ)
    existing_python_path = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = (
        str(repo_root)
        if not existing_python_path
        else str(repo_root) + os.pathsep + existing_python_path
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--payload-file",
            str(payload_file),
            "--skip-docpeg",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
    assert "[DONE] component_utxo_beam_l3_demo passed" in proc.stdout

    summary_path = out_dir / "beam_l3_component_demo_summary.json"
    assert summary_path.exists(), "summary JSON was not generated"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["passed"] is True
    assert str(summary["proof_hash"]).startswith("COMP-")
    assert int(summary["material_count"]) == 2
