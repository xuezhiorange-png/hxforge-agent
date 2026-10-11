#!/usr/bin/env python3
"""Subprocess wrapper for R2 realpath diagnostics (wall-clock budget only)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DIAG = ROOT / "docs/tasks/evidence/V07-TASK173-realpath-performance-r2-diagnostic.py"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--total-budget-s", type=float, default=180.0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/tasks/evidence")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    output = args.output_dir / f"V07-TASK173-realpath-performance-r2-{stamp}.json"
    cmd = [
        sys.executable,
        str(DIAG),
        "--total-budget-s",
        str(args.total_budget_s),
        "--output",
        str(output),
    ]
    t0 = time.perf_counter()
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        timeout=args.total_budget_s + 45.0,
        check=False,
        capture_output=True,
        text=True,
    )
    envelope = {
        "task_id": "V07_TASK173_REALPATH_PERFORMANCE_R2",
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "returncode": completed.returncode,
        "wall_seconds": time.perf_counter() - t0,
        "raw_result_path": str(output),
        "raw_result_sha256": (
            hashlib.sha256(output.read_bytes()).hexdigest() if output.is_file() else None
        ),
    }
    env_path = args.output_dir / f"V07-TASK173-realpath-performance-r2-{stamp}.envelope.json"
    env_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    if completed.stdout.strip():
        print(completed.stdout.strip())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
