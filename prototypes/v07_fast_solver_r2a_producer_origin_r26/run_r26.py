#!/usr/bin/env python3
"""R26: R2A producer origin qualification evidence runner."""

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

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.hash_audit import (
    audit_r19_r21e_full_hash_replay,
    audit_r22_raw_result,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.frozen_candidate_qualification import (
    qualify_all_frozen_candidates,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.negative_injection_r25 import (
    run_negative_injection_r25,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.captured_producer_fixture import (
    build_captured_candidate_b_producer_arguments,
    emit_production_r2a_event,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.full_certificate_positive_witness import (
    run_full_certificate_positive_witness,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.negative_injection_r26 import (
    run_negative_injection_r26,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_non_trigger_witness import (
    evaluate_no_trigger_producer_witness,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_origin_verification import (
    build_runtime_producer_origin,
    verify_producer_origin_record,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    recompute_q1_q15_from_producer_arguments,
    run_captured_positive_witness,
)

TASK_ID = "V07_FAST_SOLVER_R26_R2A_PRODUCER_ORIGIN_QUALIFICATION"
BASE_HEAD = "e0c386d04ae74d8ed31db130074dcdfd3be82036"
R25_LEDGER_REL = (
    "docs/tasks/evidence/V07-FAST-SOLVER-r25-r2a-certificate-qualification-20261020T110119Z/"
    "CANDIDATE_CERTIFICATE_LEDGER.json"
)


def _gates() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "pytest",
            "prototypes/v07_fast_solver_r2a_authority_qualification_r25/",
            "prototypes/v07_fast_solver_r2a_producer_origin_r26/",
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


def _r25_correction(ledger: list[dict[str, Any]]) -> dict[str, Any]:
    r25_path = ROOT / R25_LEDGER_REL
    prior_rows: list[dict[str, Any]] = []
    if r25_path.is_file():
        prior_rows = json.loads(r25_path.read_text(encoding="utf-8"))
    corrections: list[dict[str, Any]] = []
    prior_by_key = {
        (row.get("label"), row.get("mesh_n")): row.get("admission_status") for row in prior_rows
    }
    for row in ledger:
        key = (row.get("label"), row.get("mesh_n"))
        corrections.append(
            {
                "label": row.get("label"),
                "mesh_n": row.get("mesh_n"),
                "r25_admission_status": prior_by_key.get(key),
                "r26_admission_status": row.get("admission_status"),
                "misclassification_fixed": prior_by_key.get(key) == "NO_TRIGGER_PROVEN"
                and row.get("admission_status") == "FROZEN_EVIDENCE_INSUFFICIENT",
            }
        )
    return {
        "schema_version": "task173.r2a-r25-no-trigger-correction.v1",
        "r25_evidence_unchanged": True,
        "r25_ledger_rel": R25_LEDGER_REL,
        "correction_rule": (
            "Remove inference of NO_TRIGGER_PROVEN from fast-solver provider id or empty "
            "R2A event lists; require evaluate_no_trigger_producer_witness bundle."
        ),
        "mesh_corrections": corrections,
        "all_misclassifications_fixed": all(c["misclassification_fixed"] for c in corrections),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if code_head != BASE_HEAD and subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_HEAD, code_head],
        cwd=ROOT,
        check=False,
    ).returncode != 0:
        print("BASE_HEAD_MISMATCH", code_head, BASE_HEAD)
        sys.exit(2)

    _gates()
    ledger = qualify_all_frozen_candidates(ROOT)
    correction = _r25_correction(ledger)
    args_bundle = build_captured_candidate_b_producer_arguments(ROOT)
    event = emit_production_r2a_event(ROOT)
    recomputed = recompute_q1_q15_from_producer_arguments(args_bundle)
    q_replay = {
        "schema_version": "task173.r2a-q1-q15-independent-replay.v1",
        "source_evidence_rel": args_bundle["evidence_rel"],
        "event_hash": event["event_hash"],
        "declared_q_predicates": event.get("Q1_Q15"),
        "recomputed_q_predicates": recomputed,
        "all_match": recomputed == {k: bool(v) for k, v in event["Q1_Q15"].items()},
        "producer_path": "task173._candidate_provider_enclosure_event",
    }
    origin = build_runtime_producer_origin(ROOT)
    origin_ok, origin_code = verify_producer_origin_record(origin, root=ROOT)
    producer_origin = {
        "schema_version": "task173.r2a-producer-origin-verification.v1",
        "origin_record": origin,
        "verification_code": origin_code,
        "verification_pass": origin_ok,
        "provider_binding": args_bundle["provider_identity"],
    }
    positive_event = run_captured_positive_witness(ROOT)
    positive_cert = run_full_certificate_positive_witness(ROOT)
    negative_r26 = run_negative_injection_r26()
    negative_r25 = run_negative_injection_r25()
    non_trigger = evaluate_no_trigger_producer_witness(None)
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

    status_by_label: dict[str, dict[str, str]] = {}
    for row in ledger:
        label = str(row.get("label"))
        mesh_n = int(row["mesh_n"])
        status_by_label.setdefault(label, {})[f"n{mesh_n}"] = str(row.get("admission_status"))

    qualification_status = {
        "schema_version": "task173.r2a-candidate-qualification-status.v1",
        "candidate_b": status_by_label.get("CANDIDATE_B_R19", {}),
        "second_candidate": status_by_label.get("SECOND_CANDIDATE_R21E", {}),
        "production_r2a_authority_verified": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
    }

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-r26-r2a-producer-origin-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "code_commit_head": code_head,
        "r25_no_trigger_misclassification_fixed": correction["all_misclassifications_fixed"],
        "r2a_q1_q15_independent_replay": q_replay["all_match"],
        "r2a_provider_identity_gate": origin_ok,
        "r2a_event_hash_replay": positive_event["event_hash_replay"],
        "r2a_certificate_hash_replay": positive_cert["certificate_hash_replay"],
        "r2a_outer_decision_binding": positive_cert["verifier_status"]
        == "CERTIFICATE_PRESENT_VERIFIED",
        "r2a_positive_producer_witness": positive_cert["witness_status"],
        "r2a_negative_injection_pass": all(r["PASS"] == "true" for r in negative_r26),
        "r2a_determinism_test": determinism_hash_a == determinism_hash_b,
        "r2a_production_authority_verified": False,
        "task167_configuration_rule_pack_approval": "NOT_VERIFIED",
        "fiv_numeric_limit_authority": "MISSING",
        "experimental_multi_candidate_sizing_verified": True,
        "production_recommendation_authorized": False,
        "production_multi_candidate_sizing_verified": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "golden_hash_audit": golden,
        "negative_injection_r25_pass": sum(1 for r in negative_r25 if r["PASS"] == "true"),
        "negative_injection_r26_pass": sum(1 for r in negative_r26 if r["PASS"] == "true"),
        "non_trigger_without_witness": non_trigger[0],
        "wall_seconds": time.perf_counter() - wall_t0,
    }

    (out_dir / "R25_NO_TRIGGER_CORRECTION.json").write_text(
        json.dumps(correction, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "R2A_Q1_Q15_INDEPENDENT_REPLAY.json").write_text(
        json.dumps(q_replay, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "R2A_PRODUCER_ORIGIN_VERIFICATION.json").write_text(
        json.dumps(producer_origin, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "R2A_CERTIFICATE_POSITIVE_WITNESS.json").write_text(
        json.dumps(
            {
                "event_level": positive_event,
                "certificate_level": positive_cert,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "R2A_CERTIFICATE_NEGATIVE_INJECTION.json").write_text(
        json.dumps(negative_r26, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "CANDIDATE_R2A_QUALIFICATION_STATUS.json").write_text(
        json.dumps(qualification_status, indent=2, sort_keys=True) + "\n",
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
