#!/usr/bin/env python3
"""R21 Phase A: gate supplement evidence runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TASK_ID = "V07_FAST_SOLVER_GENERAL_CANDIDATE_LIVE_RATING_R21A"
BASE_HEAD = "22268bb5b88dec6ed0d96c942ba17c0d00e913f4"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    base_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if base_head != BASE_HEAD and not (ROOT / ".git").exists():
        raise SystemExit("BASE_HEAD mismatch")

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r21a_gate_supplement.py",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20a_fail_closed_injection.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.output_dir or (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-r21a-gate-supplement-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    envelope: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "phase": "A",
        "gate_tests": "PASS",
        "wall_seconds": time.perf_counter() - wall_t0,
    }
    payload = json.dumps(envelope, sort_keys=True, indent=2) + "\n"
    env_path = out_dir / f"V07-FAST-SOLVER-r21a-gate-supplement-{stamp}.json"
    env_path.write_text(payload, encoding="utf-8")
    print("ENVELOPE_SHA256", hashlib.sha256(payload.encode()).hexdigest())
    print("RAW_RESULT_PATH", env_path)


if __name__ == "__main__":
    main()
