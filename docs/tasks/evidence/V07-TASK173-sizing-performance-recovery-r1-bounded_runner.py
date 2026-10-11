#!/usr/bin/env python3
"""Bounded subprocess entry for TASK173 performance benchmarks.

Does not alter solver acceptance; only enforces wall-clock budget and exit status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BENCHMARK = ROOT / "docs/tasks/evidence/V07-TASK173-sizing-performance-recovery-r1-benchmark.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs/tasks/evidence",
    )
    parser.add_argument("--label", type=str, default="baseline")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    output = args.output_dir / f"V07-TASK173-sizing-performance-recovery-r1-{args.label}-{stamp}.json"
    envelope = {
        "task_id": "V07_TASK173_SIZING_PERFORMANCE_RECOVERY_R1",
        "label": args.label,
        "timeout_s": args.timeout_s,
        "benchmark_script": str(BENCHMARK),
        "started_at_utc": stamp,
        "status": "RUNNING",
    }
    envelope_path = args.output_dir / f"V07-TASK173-sizing-performance-recovery-r1-{args.label}-{stamp}.envelope.json"
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        str(BENCHMARK),
        "--timeout-s",
        str(args.timeout_s),
        "--output",
        str(output),
    ]
    t0 = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            timeout=args.timeout_s + 30.0,
            check=False,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        envelope.update(
            {
                "status": "TIMEOUT",
                "wall_seconds": time.perf_counter() - t0,
                "raw_result_path": str(output),
            }
        )
        envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        return 124

    wall = time.perf_counter() - t0
    envelope["wall_seconds"] = wall
    envelope["returncode"] = completed.returncode
    envelope["raw_result_path"] = str(output)
    if output.is_file():
        envelope["raw_result_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    if completed.returncode == 0:
        envelope["status"] = "PASS"
    else:
        envelope["status"] = "FAIL"
        envelope["stderr_tail"] = completed.stderr[-4000:]
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    if completed.stdout.strip():
        print(completed.stdout.strip())
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
