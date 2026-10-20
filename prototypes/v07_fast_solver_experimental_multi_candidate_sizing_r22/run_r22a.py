#!/usr/bin/env python3
"""R22A: engineering admission repair evidence runner."""

# ruff: noqa: E501

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
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing_v2 import (
    build_experimental_multi_candidate_sizing_v2,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.hash_audit import (
    audit_r19_r21e_full_hash_replay,
    audit_r22_raw_result,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.numerical_authority_gap_ledger import (
    numerical_authority_gap_ledger,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.requirement_verification import (
    verify_requirement_canonical_hash,
    verify_trusted_requirement_binding,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    experimental_multi_candidate_sizing_result_hash,
)

TASK_ID = "V07_FAST_SOLVER_R22A_ENGINEERING_ADMISSION_REPAIR"
BASE_HEAD = "e4e84c28f50a0b78bac3520bc0d5452388dbb195"
BUDGET_S = 1200.0
BRANCH = "cursor/v07-fast-solver-experimental-multi-candidate-sizing-r22-1201"


def _run_quality_gates() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "prototypes/v07_fast_solver_experimental_multi_candidate_sizing_r22/",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r20a_fail_closed_injection.py",
            "prototypes/v07_fast_solver_rating_sizing_bridge_r20/test_r21a_gate_supplement.py",
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
    args = parser.parse_args()
    wall_t0 = time.perf_counter()

    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    remote_head = subprocess.check_output(
        ["git", "rev-parse", f"origin/{BRANCH}"],
        cwd=ROOT,
        text=True,
    ).strip()
    merge = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_HEAD, code_head],
        cwd=ROOT,
        check=False,
    )
    if merge.returncode != 0:
        print("BASE_HEAD_MISMATCH", code_head, BASE_HEAD)
        sys.exit(2)

    _run_quality_gates()

    r22_audit = audit_r22_raw_result(ROOT)
    if r22_audit.get("blocked"):
        print("R22_HASH_AUDIT_BLOCKED", r22_audit)
        sys.exit(3)
    full_audit = audit_r19_r21e_full_hash_replay(ROOT)
    requirement = experimental_multi_candidate_sizing_requirement()
    result_a = experimental_multi_candidate_sizing(ROOT, requirement)
    result_b = experimental_multi_candidate_sizing(ROOT, requirement)
    v2 = build_experimental_multi_candidate_sizing_v2(ROOT, requirement)

    if not (
        r22_audit["raw_file_sha256_parity"]
        and r22_audit["sizing_result_hash_parity"]
        and full_audit["r19_full_result_hash_parity"]
        and full_audit["r21e_full_result_hash_parity"]
    ):
        print("HASH_PARITY_FAILURE", r22_audit, full_audit)
        sys.exit(4)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (
        ROOT
        / f"docs/tasks/evidence/V07-FAST-SOLVER-experimental-multi-candidate-sizing-r22a-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "code_commit_head": code_head,
        "remote_head_before_evidence": remote_head,
        "r22_raw_sha256_parity": r22_audit["raw_file_sha256_parity"],
        "r22_sizing_result_hash_parity": r22_audit["sizing_result_hash_parity"],
        "r19_full_hash_replay": full_audit["r19_full_result_hash_parity"],
        "r21e_full_hash_replay": full_audit["r21e_full_result_hash_parity"],
        "full_compact_identity_gate": full_audit["full_compact_identity_gate"],
        "requirement_canonical_hash_gate": verify_requirement_canonical_hash(requirement),
        "candidate_space_authority_gate": verify_trusted_requirement_binding(requirement) is None,
        "mandatory_screening_executed": True,
        "mandatory_screening_complete": v2.mandatory_screening_complete,
        "fiv_authority_status": v2.fiv_authority_status,
        "screening_gap_ledger": list(v2.screening_gap_codes),
        "ranking_policy_replay": result_a.ranking_trace_status == "COMPLETE",
        "determinism_test": result_a.result_hash == result_b.result_hash,
        "sizing_result_hash_replay": result_a.result_hash
        == experimental_multi_candidate_sizing_result_hash(result_a),
        "experimental_multi_candidate_sizing_verified": result_a.status == "EXPERIMENTAL_COMPLETE",
        "recommended_candidate_id": result_a.recommended_candidate_id,
        "production_recommendation_authorized": False,
        "production_multi_candidate_sizing_verified": False,
        "numerical_authority_gap_ledger": list(numerical_authority_gap_ledger()),
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "negative_injection_tests": "PYTEST",
        "next_action": "STOP_FOR_ENGINEERING_REVIEW",
        "hash_audit": r22_audit,
        "full_rating_hash_audit": full_audit,
        "candidate_ledger": [r.model_dump(mode="json") for r in result_a.candidate_records],
        "ranking_trace": [t.model_dump(mode="json") for t in result_a.ranking_trace],
        "sizing_result_v1": result_a.model_dump(mode="json"),
        "sizing_result_v2": v2.model_dump(mode="json"),
    }

    raw_path = out_dir / f"V07-FAST-SOLVER-experimental-multi-candidate-sizing-r22a-{stamp}.json"
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    raw_path.write_text(payload, encoding="utf-8")
    raw_sha = hashlib.sha256(payload.encode()).hexdigest()
    receipt["raw_result_path"] = str(raw_path.relative_to(ROOT))
    receipt["raw_result_sha256"] = raw_sha
    receipt["wall_seconds"] = time.perf_counter() - wall_t0

    (out_dir / "HASH_AUDIT.json").write_text(
        json.dumps(r22_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "NUMERICAL_AUTHORITY_GAP_LEDGER.json").write_text(
        json.dumps(list(numerical_authority_gap_ledger()), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "NEGATIVE_INJECTION.json").write_text(
        json.dumps(
            {"status": "PYTEST_GREEN", "suite": "test_r22a_fail_closed_injection.py"}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )

    if args.execute:
        subprocess.run(
            ["git", "add", str(out_dir.relative_to(ROOT))],
            cwd=ROOT,
            check=True,
        )
        evidence_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        receipt["evidence_staged_commit_head"] = evidence_head

    print(json.dumps({k: receipt[k] for k in sorted(receipt) if k != "sizing_result_v1"}, indent=2))
    print("RAW_RESULT_PATH", raw_path)
    print("RAW_RESULT_SHA256", raw_sha)


if __name__ == "__main__":
    main()
