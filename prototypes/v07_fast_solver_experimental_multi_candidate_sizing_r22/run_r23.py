#!/usr/bin/env python3
"""R23: production authority pre-admission evidence runner."""

# ruff: noqa: E501, E402

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

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.production_authority_admission_report import (
    build_production_authority_admission_report,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.production_authority_gap_ledger_r23 import (
    production_authority_gap_ledger_r23,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    experimental_multi_candidate_sizing_result_hash,
)

TASK_ID = "V07_FAST_SOLVER_PRODUCTION_AUTHORITY_PRE_ADMISSION_R23"
BASE_HEAD = "40995df1202a29715fd11b992faf03c71c3ab105"
BRANCH = "cursor/v07-fast-solver-experimental-multi-candidate-sizing-r22-1201"


def _gates() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "pytest",
            "prototypes/v07_fast_solver_experimental_multi_candidate_sizing_r22/",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20a_fail_closed_injection.py",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r21a_gate_supplement.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["uv", "run", "--locked", "ruff", "check", "."],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        ["uv", "run", "--locked", "ruff", "format", "--check", "."],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    merge = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_HEAD, code_head],
        cwd=ROOT,
        check=False,
    )
    if merge.returncode != 0:
        print("BASE_HEAD_MISMATCH", code_head, BASE_HEAD)
        sys.exit(2)

    _gates()
    req = experimental_multi_candidate_sizing_requirement()
    result_a = experimental_multi_candidate_sizing(ROOT, req)
    result_b = experimental_multi_candidate_sizing(ROOT, req)
    admitted = (admit_candidate_b_live_rating(ROOT), admit_second_candidate_live_rating(ROOT))
    report = build_production_authority_admission_report(
        admitted,
        sizing_result_hash=result_a.result_hash,
        independent_consumer_verified=result_a.status == "EXPERIMENTAL_COMPLETE",
    )
    ledger = list(production_authority_gap_ledger_r23())
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-production-authority-pre-admission-r23-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    negative = {
        "task_id": TASK_ID,
        "suite": "test_r23_independent_consumer_injection.py",
        "status": "PYTEST_GREEN",
    }
    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "code_commit_head": code_head,
        "independent_consumer_fail_closed": result_a.status == "EXPERIMENTAL_COMPLETE",
        "determinism_test": result_a.result_hash == result_b.result_hash,
        "sizing_result_hash": result_a.result_hash,
        "sizing_result_hash_replay": result_a.result_hash
        == experimental_multi_candidate_sizing_result_hash(result_a),
        "production_authority_admission_report": report,
        "wall_seconds": time.perf_counter() - wall_t0,
    }
    raw_path = out_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    (out_dir / "NEGATIVE_INJECTION_DETAILED.json").write_text(
        json.dumps(negative, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "PRODUCTION_AUTHORITY_ADMISSION_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "AUTHORITY_GAP_LEDGER.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.execute:
        subprocess.run(["git", "add", str(out_dir.relative_to(ROOT))], cwd=ROOT, check=True)
    print("RAW_RESULT_PATH", raw_path)
    print("RAW_RESULT_SHA256", raw_sha)


if __name__ == "__main__":
    main()
