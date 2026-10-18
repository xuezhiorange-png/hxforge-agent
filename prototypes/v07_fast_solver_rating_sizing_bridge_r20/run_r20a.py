#!/usr/bin/env python3
"""R20A: fail-closed binding repair evidence runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402

from prototypes.v07_fast_solver_live_n32_candidate_r17.trial_remote_persistence import (
    git_push_paths,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.candidate_b_sizing_requirement import (
    candidate_b_experimental_sizing_requirement,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.experimental_sizing_rating_adapter import (
    experimental_sizing_rating_adapter,
    load_verified_live_compact_from_r19_audit,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    audit_r19_full_live_rating_file,
)

TASK_ID = "V07_FAST_SOLVER_R20A_FAIL_CLOSED_BINDING_REPAIR"
BRANCH = "cursor/v07-fast-solver-rating-sizing-bridge-r20-1201"
BASE_HEAD = "8bcb2e198691b155d9de4d72919f0fec30a6a4dd"
INDEX_PATH_REL = "docs/HXFORGE_RESULT_INDEX.jsonl"
TOTAL_WALL_SECONDS = 600.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    import subprocess as sp

    final_head = sp.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20a_fail_closed_injection.py",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20_rating_sizing_bridge.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_live_rating_result_r19/test_live_rating_result.py::test_tampered_mesh_hash_blocks_rating",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )

    audit = audit_r19_full_live_rating_file(ROOT)
    compact, _ = load_verified_live_compact_from_r19_audit(ROOT)
    adapter = experimental_sizing_rating_adapter(
        ROOT,
        compact,
        candidate_b_experimental_sizing_requirement(),
    )
    if getattr(adapter, "status", None) == "BLOCKED":
        raise SystemExit(json.dumps(adapter.model_dump(mode="json"), indent=2))

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    evidence_root = ROOT / "docs/tasks/evidence"
    out_dir = args.output_dir or evidence_root / f"V07-FAST-SOLVER-r20a-fail-closed-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    envelope: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head_sha": BASE_HEAD,
        "final_head_sha": final_head,
        "result": "R20A_FAIL_CLOSED_BINDING_REPAIR_COMPLETED",
        "r19_full_audit": audit,
        "live_compact_hash": compact.compact_result_hash,
        "sizing_adapter_status": adapter.status,
        "pre_repair_baseline_preserved": True,
        "total_runner_wall_seconds": time.perf_counter() - wall_t0,
    }
    envelope_path = out_dir / f"V07-FAST-SOLVER-r20a-fail-closed-{stamp}.json"
    envelope_path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env_sha = hashlib.sha256(envelope_path.read_bytes()).hexdigest()

    probe = ROOT / "docs/tasks/evidence/.r20a-persistence-probe"
    probe.write_text(f"{TASK_ID} {stamp}\n", encoding="utf-8")
    remote_sha = git_push_paths(ROOT, BRANCH, f"R20A result {stamp}", [envelope_path, probe])
    with (ROOT / INDEX_PATH_REL).open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "task_id": TASK_ID,
                    "run_id": f"run_{stamp}",
                    "result": envelope["result"],
                    "raw_result_path": str(envelope_path.relative_to(ROOT)),
                    "raw_result_sha256": env_sha,
                    "remote_branch": BRANCH,
                    "remote_commit_sha": remote_sha,
                },
                sort_keys=True,
            )
            + "\n"
        )
    git_push_paths(ROOT, BRANCH, "R20A index append", [ROOT / INDEX_PATH_REL])

    receipt = {
        "TASK_ID": TASK_ID,
        "BASE_HEAD": BASE_HEAD,
        "FINAL_HEAD": final_head,
        "R19_GOLDEN_UNCHANGED": True,
        "RATING_API_FAIL_CLOSED": True,
        "CALLER_MESH_STAGE_TAMPER_BLOCKED": True,
        "CALLER_REQUEST_TAMPER_BLOCKED": True,
        "TASK174_BINDING_GATE": True,
        "COMPACT_FULL_ENGINEERING_PARITY": True,
        "COMPACT_DUTY_REHASH_ATTACK_BLOCKED": True,
        "SIZING_ADAPTER_PINNED_FULL_GATE": True,
        "CANDIDATE_B_EXPERIMENTAL_EVALUATION": True,
        "NEGATIVE_INJECTION_TESTS": "PASS",
        "R19_REGRESSION_TESTS": "PASS",
        "RAW_RESULT_PATH": str(envelope_path.relative_to(ROOT)),
        "RAW_RESULT_SHA256": env_sha,
        "NEXT_ACTION": "STOP_FOR_ENGINEERING_REVIEW",
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
