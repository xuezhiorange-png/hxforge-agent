"""Capture complete native Task172 identities for the frozen H2 hole trial.

This is an evidence-only diagnostic. It replays the already-qualified H2 outer
trial at its frozen iteration and shooting enthalpy; it does not alter the
production solver or the R2 authority.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating

ROOT = Path.cwd()

QUALIFICATION_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2.json"
)
QUALIFICATION_RUNNER_PATH = Path(
    "docs/tasks/evidence/"
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-qualification.py"
)
REPLAY_RUNNER_PATH = Path(
    "docs/tasks/evidence/"
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-replay.py"
)
OUTPUT_PATH = Path(
    "docs/tasks/evidence/"
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole.json"
)
RUNTIME_HEAD = "b1b9d676c693e09d740c47b642198b5e4f543409"
RUNTIME_TREE = "b0cfbdb7c4a9c3136fda317723fb5eab30c40e1e"
H2_CANDIDATE_ID = "aa70248a-9f76-542d-bc77-1e935b9c32d4"
H2_CANDIDATE_HASH = "a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5"
H2_ITERATION = 11


def _load_qualification_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "task173_r2_qualification_for_h2_hole_capture", ROOT / QUALIFICATION_RUNNER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("QUALIFICATION_RUNNER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _dump_model(model: Any, fallback: Any) -> dict[str, Any]:
    return model.model_dump(mode="json", fallback=fallback)


def _result_identity(result: Any) -> tuple[str, str, str]:
    if type(result) is rating.Task172LocalResult:
        result_hash = rating.recompute_task172_result_hash(result)
        if result_hash != result.result_hash:
            raise RuntimeError("VALID_TASK172_RESULT_HASH_REPLAY_FAILED")
        return "VALID", result_hash, result_hash
    if type(result) is rating.Task172BlockedResult:
        result_hash = rating.recompute_task172_blocked_result_hash(result)
        if result_hash != result.blocked_result_hash:
            raise RuntimeError("BLOCKED_TASK172_RESULT_HASH_REPLAY_FAILED")
        return "BLOCKED", result_hash, result_hash
    raise RuntimeError(f"UNEXPECTED_TASK172_RESULT_TYPE:{type(result).__name__}")


def _main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
    if (head, tree) != (RUNTIME_HEAD, RUNTIME_TREE):
        raise RuntimeError(f"RUNTIME_BASELINE_MISMATCH:{head}:{tree}")
    subprocess.run(["git", "diff", "--exit-code", "HEAD"], check=True)

    evidence = json.loads(QUALIFICATION_PATH.read_text())
    qualification = evidence["qualification"]
    h2_rows = [row for row in qualification["cases"] if row["label"] == "H2"]
    if len(h2_rows) != 1:
        raise RuntimeError("FROZEN_H2_CASE_NOT_UNIQUE")
    h2 = h2_rows[0]
    if (h2["candidate_id"], h2["candidate_hash"], h2["cut"]) != (
        H2_CANDIDATE_ID,
        H2_CANDIDATE_HASH,
        "0.275",
    ):
        raise RuntimeError("FROZEN_H2_IDENTITY_MISMATCH")
    trial_rows = [row for row in h2["outer_search"]["trials"] if row["iteration"] == H2_ITERATION]
    if len(trial_rows) != 1:
        raise RuntimeError("FROZEN_H2_HOLE_TRIAL_NOT_UNIQUE")
    frozen_trial = trial_rows[0]
    if frozen_trial["enclosure_used"]:
        raise RuntimeError("H2_HOLE_TRIAL_UNEXPECTEDLY_USES_ENCLOSURE")
    expected_branch = frozen_trial["left_branch"]
    neighborhoods = expected_branch["observables"]["task172_numerical_hole_neighborhoods"]
    if len(neighborhoods) != 1:
        raise RuntimeError("FROZEN_H2_HOLE_NEIGHBORHOOD_NOT_UNIQUE")
    neighborhood = neighborhoods[0]
    if neighborhood["failure_code"] != "BLOCKED_RESIDUAL_ACCEPTANCE":
        raise RuntimeError("H2_HOLE_FAILURE_CODE_MISMATCH")

    qrunner = _load_qualification_runner()
    qrunner._check_committed_runtime()
    candidate, bundle, topology, task174_result, request, candidate_space_hash = (
        qrunner._build_candidate("H2")
    )
    if (candidate.candidate_id, candidate.candidate_hash) != (
        H2_CANDIDATE_ID,
        H2_CANDIDATE_HASH,
    ):
        raise RuntimeError("REBUILT_H2_IDENTITY_MISMATCH")

    captured: list[dict[str, Any]] = []
    current_q: float | None = None
    original_cell_evaluation = rating._cell_evaluation
    original_candidate_validate = rating.task172_validate_candidate
    original_reference_validate = rating.task172_validate

    def traced_cell_evaluation(q_w: float, **kwargs: Any) -> Any:
        nonlocal current_q
        previous_q = current_q
        current_q = q_w
        try:
            return original_cell_evaluation(q_w, **kwargs)
        finally:
            current_q = previous_q

    def capture_validation(validator: Any, task172_request: Any, provider: Any) -> Any:
        result = validator(task172_request, provider)
        if current_q is None:
            raise RuntimeError("TASK172_CALL_WITHOUT_CELL_Q_COORDINATE")
        status, computed_hash, result_identity = _result_identity(result)
        captured.append(
            {
                "q_trial_w": repr(current_q),
                "physical_segment_id": task172_request.support.physical_segment_id,
                "task172_support_identity": rating.recompute_task172_support_id(task172_request),
                "request_projection": _dump_model(task172_request, qrunner._pair_fallback),
                "request_hash": rating.recompute_task172_request_hash(task172_request),
                "result_type": type(result).__name__,
                "result_status": status,
                "result_projection": _dump_model(result, qrunner._pair_fallback),
                "result_hash": computed_hash,
                "result_identity": result_identity,
            }
        )
        return result

    def capture_candidate(task172_request: Any, provider: Any) -> Any:
        return capture_validation(original_candidate_validate, task172_request, provider)

    def capture_reference(task172_request: Any, provider: Any) -> Any:
        return capture_validation(original_reference_validate, task172_request, provider)

    rating._cell_evaluation = traced_cell_evaluation
    rating.task172_validate_candidate = capture_candidate
    rating.task172_validate = capture_reference
    try:
        branch = qrunner._run_branch(
            "H2",
            request,
            "LEFT_BRANCH",
            Decimal(frozen_trial["enthalpy_j_kg"]),
            H2_ITERATION,
        )
    finally:
        rating._cell_evaluation = original_cell_evaluation
        rating.task172_validate_candidate = original_candidate_validate
        rating.task172_validate = original_reference_validate

    branch_without_mesh = {key: value for key, value in branch.items() if key != "mesh_run"}
    if branch_without_mesh != expected_branch:
        raise RuntimeError("H2_FROZEN_OUTER_TRIAL_REPLAY_MISMATCH")
    mesh_run = branch.get("mesh_run")
    if mesh_run is None:
        raise RuntimeError("H2_REPLAY_MESH_PAYLOAD_MISSING")

    target_points = [
        ("HOLE_BLOCKED", neighborhood["hole_q_trial_w"]),
        ("LEFT_VALID_NEIGHBOR", neighborhood["left_valid_q_w"]),
        ("RIGHT_VALID_NEIGHBOR", neighborhood["right_valid_q_w"]),
    ]
    support_id = neighborhood["physical_support_id"]
    selected: list[dict[str, Any]] = []
    for role, q_text in target_points:
        matches = [
            row
            for row in captured
            if float(row["q_trial_w"]) == float(q_text) and row["physical_segment_id"] == support_id
        ]
        if len(matches) != 1:
            raise RuntimeError(f"H2_{role}_CAPTURE_NOT_UNIQUE:{len(matches)}")
        row = matches[0]
        row["role"] = role
        if role == "HOLE_BLOCKED" and row["result_status"] != "BLOCKED":
            raise RuntimeError("H2_HOLE_RESULT_NOT_BLOCKED")
        if role != "HOLE_BLOCKED" and row["result_status"] != "VALID":
            raise RuntimeError(f"H2_{role}_RESULT_NOT_VALID")
        selected.append(row)

    recorded_holes = [
        row
        for row in mesh_run["numerical_hole_receipts"]
        if row["physical_support_id"] == support_id
        and float(row["q_trial_w"]) == float(neighborhood["hole_q_trial_w"])
    ]
    if len(recorded_holes) != 1:
        raise RuntimeError(
            "H2_RECORDED_HOLE_NOT_UNIQUE:" + json.dumps(recorded_holes, sort_keys=True)
        )
    blocked_capture = next(row for row in selected if row["role"] == "HOLE_BLOCKED")
    if (
        recorded_holes[0]["failure_code"] != "BLOCKED_RESIDUAL_ACCEPTANCE"
        or blocked_capture["result_projection"].get("request_hash")
        != blocked_capture["request_hash"]
        or blocked_capture["result_projection"].get("blocked_result_hash")
        != blocked_capture["result_hash"]
    ):
        raise RuntimeError("H2_BLOCKED_TRIAL_IDENTITY_REPLAY_MISMATCH")
    blocked_receipt = {
        "q_trial_w": blocked_capture["q_trial_w"],
        "physical_segment_id": support_id,
        "task172_support_identity": blocked_capture["task172_support_identity"],
        "failure_code": recorded_holes[0]["failure_code"],
        "task172_request_hash": blocked_capture["request_hash"],
        "blocked_result_hash": blocked_capture["result_hash"],
        "blocked_request_hash_replay_passed": True,
        "blocked_result_hash_replay_passed": True,
        "exact_blocked_result_type": True,
        "receipt_source": "EVIDENCE_ONLY_REPLAY_OF_NATIVE_TASK172_CALL",
    }

    neighbor_by_role = {row["role"]: row for row in selected}
    for role, result_key, f_key in (
        ("LEFT_VALID_NEIGHBOR", "left_task172_result_hash", "left_f_q_w"),
        ("RIGHT_VALID_NEIGHBOR", "right_task172_result_hash", "right_f_q_w"),
    ):
        row = neighbor_by_role[role]
        if row["result_hash"] != neighborhood[result_key]:
            raise RuntimeError(f"H2_{role}_RESULT_IDENTITY_MISMATCH")
        if not row["result_projection"].get("result_hash"):
            raise RuntimeError(f"H2_{role}_RESULT_PROJECTION_INCOMPLETE")
        row["f_q_w"] = neighborhood[f_key]

    projection = {
        "schema_version": "task173.r2.h2-hole-task172-identity-capture.v1",
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": RUNTIME_TREE,
        "runtime_source_dirty": False,
        "parent_qualification_path": str(QUALIFICATION_PATH),
        "parent_qualification_sha256": hashlib.sha256(QUALIFICATION_PATH.read_bytes()).hexdigest(),
        "parent_qualification_matrix_hash": qualification["qualification_matrix_hash"],
        "case": {
            "label": "H2",
            "cut": h2["cut"],
            "candidate_id": candidate.candidate_id,
            "candidate_hash": candidate.candidate_hash,
            "candidate_hash_replay": qrunner.recompute_candidate_hash(candidate),
            "candidate_space_hash": candidate_space_hash,
            "task171_result_hash": topology.result_hash,
            "task174_result_hash": qrunner.recompute_task174_result_hash(task174_result),
        },
        "outer_trial": {
            "iteration": H2_ITERATION,
            "shooting_enthalpy_j_kg": frozen_trial["enthalpy_j_kg"],
            "classification": expected_branch["classification"],
            "mesh_result_hash": expected_branch["mesh_result_hash"],
            "continuation_hash": expected_branch["continuation_hash"],
            "enclosure_used": False,
        },
        "hole_neighborhood": neighborhood,
        "blocked_cell_trial_receipt": blocked_receipt,
        "task172_evaluations": sorted(
            selected,
            key=lambda row: [
                "LEFT_VALID_NEIGHBOR",
                "HOLE_BLOCKED",
                "RIGHT_VALID_NEIGHBOR",
            ].index(row["role"]),
        ),
        "captured_task172_evaluation_count_in_replayed_trial": len(captured),
        "endpoint_identity_replay": "PASS",
        "blocked_identity_replay": "PASS",
        "production_code_changed": False,
        "task172_acceptance_changed": False,
        "cell_root_policy_changed": False,
        "hash_contract": "repository canonical_sha256(projection excluding evidence_hash)",
    }
    document = dict(projection)
    document["evidence_hash"] = canonical_sha256(projection)
    OUTPUT_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(f"H2_HOLE_EVIDENCE_HASH={document['evidence_hash']}")
    print(f"H2_HOLE_CAPTURED_TASK172_EVALUATION_COUNT={len(selected)}")
    print(f"H2_REPLAYED_OUTER_TRIAL_EVALUATION_COUNT={len(captured)}")
    print("H2_BLOCKED_AND_NEIGHBOR_IDENTITIES_REPLAY=PASS")
    print("H2_FROZEN_OUTER_TRIAL_REPLAY=PASS")
    print(f"H2_HOLE_EVIDENCE_PATH={OUTPUT_PATH}")


if __name__ == "__main__":
    _main()
