#!/usr/bin/env python3
"""R25: R2A certificate authority qualification evidence runner."""

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
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.hash_audit import (
    audit_r19_r21e_full_hash_replay,
    audit_r22_raw_result,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    admit_candidate_b_live_rating,
    admit_second_candidate_live_rating,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.frozen_candidate_qualification import (
    qualify_all_frozen_candidates,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.minimum_qualification_requirements import (
    minimum_r2a_qualification_requirements,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.negative_injection_r25 import (
    run_negative_injection_r25,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    production_r2a_contract_payload,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.task167_rule_pack_claim_audit import (
    audit_both_candidates,
)

TASK_ID = "V07_FAST_SOLVER_R25_R2A_CERTIFICATE_AUTHORITY_QUALIFICATION"
BASE_HEAD = "e29c67ebf8b6d5068d0f33fd3e97750ace5be11d"


def _gates() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "pytest",
            "prototypes/v07_fast_solver_r2a_authority_qualification_r25/",
            "prototypes/v07_fast_solver_experimental_multi_candidate_sizing_r22/test_r24_immutable_and_screening.py",
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
    contract = production_r2a_contract_payload()
    candidate_b = admit_candidate_b_live_rating(ROOT)
    second = admit_second_candidate_live_rating(ROOT)
    ledger = qualify_all_frozen_candidates(ROOT)
    task167_audit = audit_both_candidates(candidate_b, second)
    injection = run_negative_injection_r25()
    min_req = minimum_r2a_qualification_requirements(ledger)
    sizing = experimental_multi_candidate_sizing(
        ROOT, experimental_multi_candidate_sizing_requirement()
    )
    golden = {
        "r19_r21e": audit_r19_r21e_full_hash_replay(ROOT),
        "r22_raw": audit_r22_raw_result(ROOT),
    }
    ledger_repeat = qualify_all_frozen_candidates(ROOT)
    determinism_hash_a = hashlib.sha256(
        json.dumps(ledger, sort_keys=True).encode("utf-8")
    ).hexdigest()
    determinism_hash_b = hashlib.sha256(
        json.dumps(ledger_repeat, sort_keys=True).encode("utf-8")
    ).hexdigest()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-r25-r2a-certificate-qualification-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    admission_summary = {
        "schema_version": "task173.r2a-certificate-admission-result.v1",
        "candidate_b": [r for r in ledger if r.get("label") == "CANDIDATE_B_R19"],
        "second_candidate": [r for r in ledger if r.get("label") == "SECOND_CANDIDATE_R21E"],
        "production_r2a_contract_review": True,
        "r2a_certificate_chain_complete": all(
            r.get("production_r2a_certificate_replay") == "CERTIFICATE_PRESENT_VERIFIED"
            for r in ledger
        ),
    }

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "code_commit_head": code_head,
        "production_r2a_contract_review": True,
        "experimental_multi_candidate_sizing_verified": sizing.status == "EXPERIMENTAL_COMPLETE",
        "golden_hash_audit": golden,
        "negative_injection_count": len(injection),
        "negative_injection_pass": sum(1 for r in injection if r["PASS"] == "true"),
        "determinism_test": determinism_hash_a == determinism_hash_b,
        "task167_configuration_rule_pack_approval": task167_audit[
            "task167_configuration_rule_pack_approval"
        ],
        "fiv_numeric_limit_authority": "MISSING",
        "mandatory_screening_complete": False,
        "wall_seconds": time.perf_counter() - wall_t0,
    }

    (out_dir / "R2A_AUTHORITY_CONTRACT.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "R2A_CERTIFICATE_ADMISSION_RESULT.json").write_text(
        json.dumps(admission_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "CANDIDATE_CERTIFICATE_LEDGER.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "TASK167_RULE_PACK_CLAIM_AUDIT.json").write_text(
        json.dumps(task167_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "NEGATIVE_INJECTION_DETAILED.json").write_text(
        json.dumps(injection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "MINIMUM_ADDITIONAL_QUALIFICATION_REQUIREMENTS.json").write_text(
        json.dumps(min_req, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raw_path = out_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    if args.execute:
        subprocess.run(["git", "add", str(out_dir.relative_to(ROOT))], cwd=ROOT, check=True)
    print("RAW_RESULT_PATH", raw_path)
    print("RAW_RESULT_SHA256", raw_sha)


if __name__ == "__main__":
    main()
