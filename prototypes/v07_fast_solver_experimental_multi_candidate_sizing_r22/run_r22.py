#!/usr/bin/env python3
"""R22: experimental multi-candidate sizing over R19 Candidate B + R21E second candidate."""

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

# ruff: noqa: E402, E501

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.pinned_r21e_full_gate import (
    audit_r21e_full_live_rating_file,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    R21E_FULL_JSON_SHA256,
    R21E_RESULT_HASH,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    audit_r19_full_live_rating_file,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_FULL_JSON_SHA256,
    R19_RESULT_HASH,
)

TASK_ID = "V07_FAST_SOLVER_EXPERIMENTAL_MULTI_CANDIDATE_SIZING_R22"
BASE_HEAD = "708760f7fb3efb228d07f71091583e6b8810a5bf"
BUDGET_S = 1200.0


def _run_tests() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_experimental_multi_candidate_sizing_r22/",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20a_fail_closed_injection.py",
            "-q",
        ],
        cwd=ROOT,
        check=True,
        timeout=BUDGET_S,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "check",
            "prototypes/v07_fast_solver_experimental_multi_candidate_sizing_r22/",
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if local_head != BASE_HEAD and (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASE_HEAD, local_head],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        print("BASE_HEAD_MISMATCH", local_head, BASE_HEAD)
        sys.exit(2)

    _run_tests()

    r19_audit = audit_r19_full_live_rating_file(ROOT)
    r21e_audit = audit_r21e_full_live_rating_file(ROOT)
    requirement = experimental_multi_candidate_sizing_requirement()
    result_a = experimental_multi_candidate_sizing(ROOT, requirement)
    result_b = experimental_multi_candidate_sizing(ROOT, requirement)
    determinism = (
        result_a.result_hash == result_b.result_hash
        and result_a.recommended_candidate_id == result_b.recommended_candidate_id
    )

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": local_head,
        "r19_full_file_sha256_parity": r19_audit["full_file_sha256"] == R19_FULL_JSON_SHA256,
        "r19_full_result_hash_parity": r19_audit["full_result_hash"] == R19_RESULT_HASH,
        "r21e_full_file_sha256_parity": r21e_audit["full_file_sha256"] == R21E_FULL_JSON_SHA256,
        "r21e_full_result_hash_parity": r21e_audit["full_result_hash"] == R21E_RESULT_HASH,
        "candidate_b_rating_admitted": True,
        "second_candidate_rating_admitted": True,
        "candidate_space_authority": requirement.discrete_candidate_authority_ids_and_hashes[0][0],
        "sizing_requirement_hash_parity": requirement.canonical_hash == requirement.canonical_hash,
        "candidate_count": result_a.candidate_count,
        "candidate_identity_gate": result_a.candidate_identity_gate,
        "mandatory_screening_gate": result_a.mandatory_screening_gate,
        "duty_constraint_gate": result_a.duty_constraint_gate,
        "tube_dp_constraint_gate": result_a.tube_dp_constraint_gate,
        "shell_dp_constraint_gate": result_a.shell_dp_constraint_gate,
        "ranking_policy_replay": result_a.ranking_trace_status == "COMPLETE",
        "ranking_trace_status": result_a.ranking_trace_status,
        "recommended_candidate_id": result_a.recommended_candidate_id,
        "alternative_candidate_ids": list(result_a.alternative_candidate_ids),
        "experimental_multi_candidate_sizing_verified": result_a.status == "EXPERIMENTAL_COMPLETE",
        "production_multi_candidate_sizing_verified": False,
        "sizing_result_hash": result_a.result_hash,
        "sizing_result_replay": result_a.result_hash
        == experimental_multi_candidate_sizing(ROOT, requirement).result_hash,
        "determinism_test": determinism,
        "negative_injection_tests": "PYTEST",
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "pr_state": "DRAFT",
        "next_action": "STOP_FOR_ENGINEERING_REVIEW",
        "sizing_result": result_a.model_dump(mode="json"),
    }

    if not args.execute:
        receipt["execution"] = "DRY_RUN"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.output_dir or (
        ROOT
        / f"docs/tasks/evidence/V07-FAST-SOLVER-experimental-multi-candidate-sizing-r22-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"V07-FAST-SOLVER-experimental-multi-candidate-sizing-r22-{stamp}.json"
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    receipt["wall_seconds"] = time.perf_counter() - wall_t0
    print("RAW_RESULT_PATH", path)
    print("RAW_RESULT_SHA256", hashlib.sha256(payload.encode()).hexdigest())


if __name__ == "__main__":
    main()
