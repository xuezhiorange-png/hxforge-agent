#!/usr/bin/env python3
"""R27: production certificate origin fail-closed evidence runner."""

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
from prototypes.v07_fast_solver_r2a_producer_origin_r26.captured_producer_fixture import (
    build_captured_candidate_b_producer_arguments,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.full_certificate_positive_witness import (
    run_full_certificate_positive_witness,
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
from prototypes.v07_fast_solver_r2a_production_origin_r27.negative_injection_r27 import (
    run_negative_injection_r27,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.outer_decision_replay import (
    verify_outer_decision_certificate_replay,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.production_origin_gate import (
    audit_production_certificate_origin,
    run_true_production_certificate_witness,
)

TASK_ID = "V07_FAST_SOLVER_R27_PRODUCTION_CERTIFICATE_ORIGIN_FAIL_CLOSED"
BASE_HEAD = "bbefedbfadda31b4c64df7032b87d33e502f3b13"


def _gates() -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "pytest",
            "prototypes/v07_fast_solver_r2a_authority_qualification_r25/",
            "prototypes/v07_fast_solver_r2a_producer_origin_r26/",
            "prototypes/v07_fast_solver_r2a_production_origin_r27/",
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


def _r26_classification_correction() -> dict[str, Any]:
    return {
        "schema_version": "task173.r2a-r26-positive-witness-classification-correction.v1",
        "prior_r26_status": "CERTIFICATE_PRESENT_VERIFIED",
        "corrected_status": "CONTRACT_FIXTURE_PASS",
        "rule": (
            "build_contract_fixture_certificate_from_captured_event() is test reconstruction; "
            "must not admit PRODUCTION_CERTIFICATE_VERIFIED without immutable producer bundle."
        ),
        "production_certificate_origin_when_fixture_only": "EVIDENCE_MISSING",
        "true_production_witness": "BLOCKED_EVIDENCE_MISSING",
    }


def _outer_decision_replay_report(root: Path) -> dict[str, Any]:
    audit = audit_production_certificate_origin(root)
    from prototypes.v07_fast_solver_r2a_production_origin_r27.immutable_production_evidence_loader import (
        load_immutable_production_bundle,
    )

    pinned_bundle = load_immutable_production_bundle(root)
    replays: list[dict[str, Any]] = []
    for cert in pinned_bundle.get("certificates", []):
        ok, code = verify_outer_decision_certificate_replay(
            cert,
            outer_trial_provenance=pinned_bundle.get("outer_trial_provenance"),
        )
        replays.append(
            {
                "certificate_hash": cert.get("certificate_hash"),
                "replay_pass": ok,
                "replay_code": code,
                "event_projections_present": pinned_bundle.get("event_projection_status")
                == "PRESENT",
            }
        )
    return {
        "schema_version": "task173.r2a-true-outer-decision-replay.v1",
        "production_certificate_origin": audit.get("production_certificate_origin"),
        "event_projection_status": pinned_bundle.get("event_projection_status"),
        "certificate_replays": replays,
        "full_production_replay_blocked": pinned_bundle.get("event_projection_status") != "PRESENT",
    }


def _no_trigger_origin_gate(root: Path) -> dict[str, Any]:
    none_status = evaluate_no_trigger_producer_witness(None, root=root)
    return {
        "schema_version": "task173.r2a-no-trigger-origin-gate.v1",
        "without_immutable_producer_trace": {
            "status": none_status[0],
            "detail": none_status[1],
        },
        "gate_rule": (
            "NO_TRIGGER_PROVEN requires trusted producer raw evidence, trial coverage, "
            "trigger detection proof, and SHA256/git binding; self-recomputed witness hashes rejected."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    wall_t0 = time.perf_counter()
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if code_head != BASE_HEAD:
        ancestor_ok = (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", BASE_HEAD, code_head],
                cwd=ROOT,
                check=False,
            ).returncode
            == 0
        )
        if not ancestor_ok:
            print("BASE_HEAD_MISMATCH", code_head, BASE_HEAD)
            sys.exit(2)

    _gates()
    origin_audit = audit_production_certificate_origin(ROOT)
    classification = _r26_classification_correction()
    outer_replay = _outer_decision_replay_report(ROOT)
    no_trigger_gate = _no_trigger_origin_gate(ROOT)
    negative_r27 = run_negative_injection_r27()
    fixture_witness = run_full_certificate_positive_witness(ROOT)
    true_witness = run_true_production_certificate_witness(ROOT)
    args_bundle = build_captured_candidate_b_producer_arguments(ROOT)
    positive_event = run_captured_positive_witness(ROOT)
    recomputed = recompute_q1_q15_from_producer_arguments(args_bundle)
    declared = positive_event.get("declared_q_predicates") or positive_event.get("Q1_Q15") or {}
    q_replay = {
        "all_match": recomputed == {k: bool(v) for k, v in declared.items()},
    }
    origin = build_runtime_producer_origin(ROOT)
    origin_ok, origin_code = verify_producer_origin_record(origin, root=ROOT)
    ledger = qualify_all_frozen_candidates(ROOT)
    ledger_repeat = qualify_all_frozen_candidates(ROOT)
    determinism_hash_a = hashlib.sha256(
        json.dumps(ledger, sort_keys=True).encode("utf-8")
    ).hexdigest()
    determinism_hash_b = hashlib.sha256(
        json.dumps(ledger_repeat, sort_keys=True).encode("utf-8")
    ).hexdigest()
    golden = {
        "r19_r21e": audit_r19_r21e_full_hash_replay(ROOT),
        "r22_raw": audit_r22_raw_result(ROOT),
    }

    status_by_label: dict[str, dict[str, str]] = {}
    for row in ledger:
        label = str(row.get("label"))
        mesh_n = int(row["mesh_n"])
        status_by_label.setdefault(label, {})[f"n{mesh_n}"] = str(row.get("admission_status"))

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (
        ROOT / f"docs/tasks/evidence/V07-FAST-SOLVER-r27-production-certificate-origin-{stamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "task_id": TASK_ID,
        "base_head": BASE_HEAD,
        "final_head": code_head,
        "completion_status": "PARTIAL_EVIDENCE_BLOCKED",
        "pr_number": 306,
        "pr_state": "DRAFT",
        "r26_fixture_classification_corrected": True,
        "producer_source_commit_verified": origin_ok,
        "producer_source_commit_code": origin_code,
        "provider_runtime_identity_verified": origin_ok,
        "production_certificate_origin": origin_audit.get("production_certificate_origin"),
        "production_outer_decision_replay": "BLOCKED_EVENT_PROJECTIONS_MISSING",
        "q1_q15_replay": q_replay["all_match"],
        "r2a_contract_fixture": "PASS"
        if fixture_witness["verifier_status"] == "CONTRACT_FIXTURE_PASS"
        else "BLOCKED",
        "r2a_true_production_certificate_witness": true_witness["witness_status"],
        "no_trigger_origin_gate": no_trigger_gate["without_immutable_producer_trace"]["status"],
        "forged_certificate_rehash_blocked": all(
            r["PASS"] == "true"
            for r in negative_r27
            if r["TAMPER_TYPE"]
            in {
                "CALLER_REHASHED_CERTIFICATE",
                "JOINT_CERTIFICATE_REHASH_TAMPER",
                "FORGED_CONTINUATION_HASH",
            }
        ),
        "candidate_b_r2a_status": status_by_label.get("CANDIDATE_B_R19", {}),
        "second_candidate_r2a_status": status_by_label.get("SECOND_CANDIDATE_R21E", {}),
        "r2a_production_authority_verified": False,
        "negative_injection_count": len(negative_r27),
        "negative_injection_pass": sum(1 for r in negative_r27 if r["PASS"] == "true"),
        "determinism_test": determinism_hash_a == determinism_hash_b,
        "fiv_numeric_limit_authority": "MISSING",
        "task167_configuration_rule_pack_approval": "NOT_VERIFIED",
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "production_recommendation_authorized": False,
        "production_multi_candidate_sizing_verified": False,
        "historical_golden_unchanged": golden,
        "next_action": "STOP_FOR_ENGINEERING_REVIEW",
        "wall_seconds": time.perf_counter() - wall_t0,
    }

    (out_dir / "PRODUCTION_CERTIFICATE_ORIGIN_AUDIT.json").write_text(
        json.dumps(origin_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "R26_POSITIVE_WITNESS_CLASSIFICATION_CORRECTION.json").write_text(
        json.dumps(classification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "TRUE_OUTER_DECISION_REPLAY.json").write_text(
        json.dumps(outer_replay, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "NO_TRIGGER_ORIGIN_GATE.json").write_text(
        json.dumps(no_trigger_gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "NEGATIVE_INJECTION_DETAILED.json").write_text(
        json.dumps(negative_r27, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    raw_path = out_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    receipt["raw_result_path"] = str(raw_path.relative_to(ROOT))
    receipt["raw_result_sha256"] = raw_sha
    raw_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    if args.execute:
        subprocess.run(["git", "add", str(out_dir.relative_to(ROOT))], cwd=ROOT, check=True)
    print("RAW_RESULT_PATH", raw_path)
    print("RAW_RESULT_SHA256", raw_sha)


if __name__ == "__main__":
    main()
