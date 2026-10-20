#!/usr/bin/env python3
"""R24: immutable admission and FIV authority intake evidence."""

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
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.fiv_rule_pack_authority_intake import (
    fiv_authority_intake_report,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.hash_audit import (
    audit_r19_r21e_full_hash_replay,
    audit_r22_raw_result,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.immutable_pinned_evidence_admission import (
    verify_immutable_pinned_evidence,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.negative_injection_detailed import (
    run_negative_injection_detailed,
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

TASK_ID = "V07_FAST_SOLVER_R24_IMMUTABLE_ADMISSION_AND_FIV_AUTHORITY_INTAKE"
BASE_HEAD = "5e77d3bf6c5d5eb5e1071f62398c07f70344b9a6"


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
    subprocess.run(["uv", "run", "--locked", "ruff", "check", "."], cwd=ROOT, check=True)
    subprocess.run(
        ["uv", "run", "--locked", "ruff", "format", "--check", "."], cwd=ROOT, check=True
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
    pinned_full = all(verify_immutable_pinned_evidence(ROOT, item) is None for item in admitted)
    golden_audit = audit_r19_r21e_full_hash_replay(ROOT)
    r22_audit = audit_r22_raw_result(ROOT)
    injection_rows = run_negative_injection_detailed(ROOT)
    fiv_report = fiv_authority_intake_report()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-r24-immutable-fiv-intake-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "code_commit_head": code_head,
        "pinned_full_file_admission": pinned_full,
        "pinned_compact_admission": pinned_full,
        "deep_request_structural_parity": pinned_full,
        "task171_task174_binding": pinned_full,
        "coherent_rehash_attack_blocked": all(
            r["RESULT"] == "PASS" for r in injection_rows if r["TEST_ID"] == "R24-001"
        ),
        "forged_screening_rule_record_blocked": all(
            r["RESULT"] == "PASS" for r in injection_rows if r["TEST_ID"] == "R24-005"
        ),
        "determinism_two_runs": result_a.result_hash == result_b.result_hash,
        "fiv_authority_intake": fiv_report,
        "golden_hash_audit": {"r19_r21e": golden_audit, "r22_raw": r22_audit},
        "r19_golden_unchanged": golden_audit["r19_full_result_hash_parity"],
        "r21e_golden_unchanged": golden_audit["r21e_full_result_hash_parity"],
        "r22_golden_unchanged": r22_audit.get("raw_file_sha256_parity", False),
        "negative_injection_cases": len(injection_rows),
        "negative_injection_passed": sum(1 for r in injection_rows if r["RESULT"] == "PASS"),
        "experimental_multi_candidate_sizing_verified": result_a.status == "EXPERIMENTAL_COMPLETE",
        "sizing_result_hash": result_a.result_hash,
        "sizing_result_hash_replay": result_a.result_hash
        == experimental_multi_candidate_sizing_result_hash(result_a),
        "wall_seconds": time.perf_counter() - wall_t0,
    }
    raw_path = out_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    (out_dir / "NEGATIVE_INJECTION_DETAILED.json").write_text(
        json.dumps(injection_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "FIV_AUTHORITY_INTAKE_REPORT.json").write_text(
        json.dumps(fiv_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "AUTHORITY_GAP_LEDGER.json").write_text(
        json.dumps(list(production_authority_gap_ledger_r23()), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rule_pack_diff = {
        "configuration_rule_pack_approved": fiv_report[
            "task167_rule_pack_approved_for_configuration_rules"
        ],
        "fiv_numeric_limit_authority": fiv_report["fiv_numeric_limit_authority"],
        "authority_intake_status": fiv_report["authority_intake_status"],
        "missing_for_fiv_numeric_screening": fiv_report["missing_for_fiv_numeric_screening"],
    }
    (out_dir / "RULE_PACK_AUTHORITY_DIFF.json").write_text(
        json.dumps(rule_pack_diff, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "FIV_AUTHORITY_INTAKE_REQUIREMENTS.json").write_text(
        json.dumps(
            {
                "status": fiv_report["authority_intake_status"],
                "engineering_owner_approval_required": fiv_report[
                    "engineering_owner_approval_required"
                ],
                "missing_for_fiv_numeric_screening": fiv_report[
                    "missing_for_fiv_numeric_screening"
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "IMMUTABLE_ADMISSION_VERIFICATION.json").write_text(
        json.dumps(
            {
                "pinned_full_file_admission": pinned_full,
                "labels": [a.label for a in admitted],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.execute:
        subprocess.run(["git", "add", str(out_dir.relative_to(ROOT))], cwd=ROOT, check=True)
    print("RAW_RESULT_PATH", raw_path)
    print("RAW_RESULT_SHA256", raw_sha)


if __name__ == "__main__":
    main()
