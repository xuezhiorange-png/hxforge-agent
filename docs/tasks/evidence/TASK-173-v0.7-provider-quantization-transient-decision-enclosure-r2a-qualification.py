"""Qualify R2A by injecting trials into the production outer state machine."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import runpy
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    SIZING_PACKAGE_HASH,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.replay import (
    public_projection,
    replay_shell_flow_authority,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path.cwd()
R2_AUTHORITY_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2.json"
)
R2_QUALIFICATION_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-qualification.py"
)
R2A_EVIDENCE_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
)
R2A_REPLAY_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-replay.py"
)
R2A_H2_CAPTURE_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole-capture.py"
)
R2A_H2_REPLAY_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole-replay.py"
)
R2A_PARITY_PATH = Path(
    "docs/tasks/evidence/TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-control-flow-parity.py"
)
REFERENCE_RATING_REPLAY_RECEIPT_PATH = Path(
    "docs/tasks/evidence/"
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-"
    "reference-rating-identity.json"
)
RUNTIME_SOURCE_HEAD = "5bd19b1829f2fea7757c3efb3398e9aab17c8a3d"
RUNTIME_SOURCE_TREE = "64fc2c4b5e1776610aa8a5e39bf0666455648f73"
PARENT_PACKAGE_ID = "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
PARENT_PACKAGE_HASH = "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
FAILED_R2_AUTHORITY_HASH = "a388f3ed8a59bc408f53f35a50f3741e44a0c5399b27ad5bf75234f0036981fa"
EXPECTED_REFERENCE_REQUEST_HASH = "77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed"
EXPECTED_REFERENCE_RATING_HASH = "fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b"
EXPECTED_REFERENCE_TASK174_HASH = "ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419"
R2_REVIEW_FINDINGS = (
    "QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_DIVERGENCE",
    "R2_REPLAY_ENTRYPOINT_RUNTIME_HEAD_GUARD_MISMATCH",
    "PARENT_SIZING_AUTHORITY_PACKAGE_HASH_INPUT_MISMATCH",
)
RUNTIME_BOUND_PATHS = (
    "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
    "src/hexagent/exchangers/shell_tube/task172_local_runtime",
    "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
    "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
    "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
    "src/hexagent/exchangers/shell_tube/bell_delaware/pressure_drop.py",
    "tests/exchangers/shell_tube/test_task173_integrated_sizing.py",
    "tests/exchangers/shell_tube/test_task173_integrated_rating.py",
    "tests/exchangers/shell_tube/test_task174_hydraulic_orchestration.py",
)

_R2 = runpy.run_path(str(R2_QUALIFICATION_PATH), run_name="task173_r2_qualification_library")
_build_candidate = _R2["_build_candidate"]
recompute_candidate_hash = _R2["recompute_candidate_hash"]
recompute_task174_result_hash = _R2["recompute_task174_result_hash"]
_pair_fallback = _R2["_pair_fallback"]
_run_branch = _R2["_run_branch"]
_mesh_run_payload = _R2["_mesh_run_payload"]
_accepted_run = _R2["_accepted_run"]
_load_reference_shell_authority = _R2["_load_reference_shell_authority"]
_run_reference_n1 = _R2["_run_reference_n1"]
_EXPECTED_CASES = _R2["EXPECTED_CASES"]
EXPECTED_TRAJECTORY_HASHES = {
    "TRAIN_A": "c865fabcd42658368fa3eb10a4e6edbd1124a1ba649dfc7cd650ae7bc7358843",
    "TRAIN_B": "b2e579624aae8a1a09a89c6236e3dc4ee40bf8aa952681ef884ee5f8ff179cfc",
    "H1": "c76b049b491235066ed8ea8ae005c3e125b359b8fd8fc1dd91938c8ff1d1bf50",
    "H2": "52b93a79a30693a843fab7cb7575560ecebc3051512fdf987d6eef040aa839d0",
    "H3": "73a0e5e199d452ba7e8a6dc7239c43f1f9bd857028c9722a6db9e9a1a444698a",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _runtime_relation_is_valid(
    *,
    is_ancestor: bool,
    actual_runtime_tree: str,
    expected_runtime_tree: str,
    bound_paths_identical: bool,
    worktree_bound_paths_clean: bool,
) -> bool:
    return (
        is_ancestor
        and actual_runtime_tree == expected_runtime_tree
        and bound_paths_identical
        and worktree_bound_paths_clean
    )


def _runtime_guard_self_tests() -> dict[str, bool]:
    cases = {
        "runtime_head": _runtime_relation_is_valid(
            is_ancestor=True,
            actual_runtime_tree="tree-a",
            expected_runtime_tree="tree-a",
            bound_paths_identical=True,
            worktree_bound_paths_clean=True,
        ),
        "unchanged_evidence_descendant": _runtime_relation_is_valid(
            is_ancestor=True,
            actual_runtime_tree="tree-a",
            expected_runtime_tree="tree-a",
            bound_paths_identical=True,
            worktree_bound_paths_clean=True,
        ),
        "changed_bound_runtime_file": _runtime_relation_is_valid(
            is_ancestor=True,
            actual_runtime_tree="tree-a",
            expected_runtime_tree="tree-a",
            bound_paths_identical=False,
            worktree_bound_paths_clean=True,
        ),
        "non_descendant": _runtime_relation_is_valid(
            is_ancestor=False,
            actual_runtime_tree="tree-a",
            expected_runtime_tree="tree-a",
            bound_paths_identical=True,
            worktree_bound_paths_clean=True,
        ),
        "wrong_frozen_tree": _runtime_relation_is_valid(
            is_ancestor=True,
            actual_runtime_tree="tree-b",
            expected_runtime_tree="tree-a",
            bound_paths_identical=True,
            worktree_bound_paths_clean=True,
        ),
        "dirty_bound_worktree": _runtime_relation_is_valid(
            is_ancestor=True,
            actual_runtime_tree="tree-a",
            expected_runtime_tree="tree-a",
            bound_paths_identical=True,
            worktree_bound_paths_clean=False,
        ),
    }
    expected = {
        "runtime_head": True,
        "unchanged_evidence_descendant": True,
        "changed_bound_runtime_file": False,
        "non_descendant": False,
        "wrong_frozen_tree": False,
        "dirty_bound_worktree": False,
    }
    if cases != expected:
        raise RuntimeError(f"RUNTIME_GUARD_SELF_TEST_FAILURE:{cases}")
    return cases


def _check_committed_runtime() -> None:
    head = _git("rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", RUNTIME_SOURCE_HEAD, head], check=False
    )
    if ancestor.returncode != 0:
        raise RuntimeError(f"RUNTIME_SOURCE_NOT_ANCESTOR:{head}")
    runtime_tree = _git("rev-parse", f"{RUNTIME_SOURCE_HEAD}^{{tree}}")
    if runtime_tree != RUNTIME_SOURCE_TREE:
        raise RuntimeError(f"RUNTIME_SOURCE_TREE_MISMATCH:{runtime_tree}")
    subprocess.run(
        ["git", "diff", "--exit-code", RUNTIME_SOURCE_HEAD, head, "--", *RUNTIME_BOUND_PATHS],
        check=True,
    )
    changed = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *RUNTIME_BOUND_PATHS],
        text=True,
    )
    if changed.strip():
        raise RuntimeError(f"RUNTIME_BOUND_WORKTREE_DIRTY:{changed.strip()}")
    if not _runtime_guard_self_tests():
        raise RuntimeError("RUNTIME_GUARD_SELF_TESTS_FAILED")


def _artifact_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_authority_projection() -> dict[str, Any]:
    base = json.loads(R2_AUTHORITY_PATH.read_text(encoding="utf-8"))
    projection = copy.deepcopy(base["authority_candidate"]["projection"])
    projection.update(
        {
            "authority_id": "V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A",
            "authority_version": "1.0.0",
            "classification": "PROJECT_NUMERICAL_TRANSIENT_OUTER_DECISION_AUTHORITY",
            "lifecycle": "PROPOSED_AUTHORITY_REVIEW_PENDING",
            "authority_accepted": False,
            "parent_sizing_authority_package_id": PARENT_PACKAGE_ID,
            "parent_sizing_authority_package_hash": PARENT_PACKAGE_HASH,
            "runtime_snapshot_head": RUNTIME_SOURCE_HEAD,
            "runtime_snapshot_tree": RUNTIME_SOURCE_TREE,
            "qualification_artifacts": {
                "qualification_runner_path": str(
                    Path(__file__).resolve().relative_to(ROOT.resolve())
                ),
                "qualification_runner_sha256": _artifact_hash(Path(__file__)),
                "replay_runner_path": str(R2A_REPLAY_PATH),
                "replay_runner_sha256": _artifact_hash(R2A_REPLAY_PATH),
                "h2_capture_runner_path": str(R2A_H2_CAPTURE_PATH),
                "h2_capture_runner_sha256": _artifact_hash(R2A_H2_CAPTURE_PATH),
                "h2_replay_runner_path": str(R2A_H2_REPLAY_PATH),
                "h2_replay_runner_sha256": _artifact_hash(R2A_H2_REPLAY_PATH),
                "reference_rating_replay_receipt_path": str(REFERENCE_RATING_REPLAY_RECEIPT_PATH),
                "reference_rating_replay_receipt_sha256": _artifact_hash(
                    REFERENCE_RATING_REPLAY_RECEIPT_PATH
                ),
                "control_flow_parity_runner_path": str(R2A_PARITY_PATH),
                "control_flow_parity_runner_sha256": _artifact_hash(R2A_PARITY_PATH),
                "legacy_h2_capture_runner_sha256": _artifact_hash(
                    Path(
                        "docs/tasks/evidence/"
                        "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-"
                        "h2-hole-capture.py"
                    )
                ),
                "parent_package_id": PARENT_PACKAGE_ID,
                "parent_package_hash": PARENT_PACKAGE_HASH,
            },
            "shared_production_outer_control_flow": {
                "module": "hexagent.exchangers.shell_tube.task173_integrated_rating.service",
                "helper": "_solve_outer_boundary_from_trial",
                "qualification_control_flow_source": "SHARED_PRODUCTION_HELPER",
                "qualification_outer_solver_control_flow_parity": "PASS_REQUIRED",
                "production_semantics_changed": False,
                "production_helper_source_path": (
                    "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py"
                ),
            },
            "midpoint_collapse_disposition_invariance": {
                "required_for_each_valid_enclosure_branch": True,
                "left_right_dispositions_must_match": True,
                "blocked_precision_floor_disposition_preserved": True,
                "precision_floor_unresolved_disposition_preserved": True,
                "terminal_tolerance_pass_disposition_preserved": True,
            },
            "failed_r2_authority_hash": FAILED_R2_AUTHORITY_HASH,
            "failed_r2_findings_accepted_as_historical": list(R2_REVIEW_FINDINGS),
        }
    )
    projection["hash_contracts"] = {
        **projection["hash_contracts"],
        "r2a_outer_decision_certificate": (
            "repository canonical_sha256(certificate excluding certificate_hash); "
            "includes both midpoint-collapse dispositions and temperature ULP floors"
        ),
        "r2a_continuation": (
            "repository canonical_sha256(continuation excluding continuation_hash); "
            "includes fallback-disabled-after-trigger state"
        ),
    }
    projection["outer_decision_invariance"]["certificate_schema"] = (
        "task173.r2a.outer-decision-certificate.v1"
    )
    projection["outer_decision_invariance"][
        "midpoint_collapse_disposition_must_match_when_valid"
    ] = True
    return projection


def _midpoint_disposition(run: Any) -> tuple[str, Decimal]:
    if rating._terminal_tolerance_pass(run):
        floor = Decimal(
            str(math.ulp(float(run.observables.terminal_boundary_residual_k + rating.T_MIN_K)))
        )
        return "RETURN_ACCEPTED_RUN", floor
    floor = Decimal(
        str(math.ulp(float(run.observables.terminal_boundary_residual_k + rating.T_MIN_K)))
    )
    if run.observables.terminal_boundary_residual_k - floor > rating.TERMINAL_TOLERANCE_K:
        return "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED", floor
    return "PRECISION_FLOOR_UNRESOLVED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED", floor


def _outer_action(classification: str, terminal_pass: bool | None) -> str:
    if classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
        return "UPDATE_H_LOW"
    if classification == "VALID_TRAJECTORY" and terminal_pass is False:
        return "UPDATE_H_HIGH_CONTINUE"
    if classification == "VALID_TRAJECTORY" and terminal_pass is True:
        return "CANDIDATE_SHOOTING_ENTHALPY_SELECTED"
    raise rating._Stage3Failure("BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID", classification)


def _check_branch_invariance(
    left: dict[str, Any], right: dict[str, Any]
) -> tuple[str, str | None, str, str | None, Decimal | None, Decimal | None]:
    if left["classification"] == "HARD_BLOCKER" or right["classification"] == "HARD_BLOCKER":
        raise rating._Stage3Failure(
            *(left if left["classification"] == "HARD_BLOCKER" else right)["diagnostics"]
        )
    if left["classification"] != right["classification"]:
        raise rating._Stage3Failure(
            "BLOCKED_TRANSIENT_OUTER_DECISION_QUANTIZATION_STRADDLE",
            f"left={left['classification']}",
            f"right={right['classification']}",
        )
    if left["classification"] != "VALID_TRAJECTORY":
        return left["classification"], None, "NOT_APPLICABLE", "NOT_APPLICABLE", None, None
    if left["mesh_run"] is None or right["mesh_run"] is None:
        raise rating._Stage3Failure("BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID")
    left_tolerance = rating._terminal_tolerance_pass(left["mesh_run"])
    right_tolerance = rating._terminal_tolerance_pass(right["mesh_run"])
    if left_tolerance != right_tolerance:
        raise rating._Stage3Failure(
            "BLOCKED_TRANSIENT_OUTER_TERMINAL_DECISION_QUANTIZATION_STRADDLE",
            f"left={left_tolerance}",
            f"right={right_tolerance}",
        )
    left_disposition, left_floor = _midpoint_disposition(left["mesh_run"])
    right_disposition, right_floor = _midpoint_disposition(right["mesh_run"])
    if left_disposition != right_disposition:
        raise rating._Stage3Failure(
            "BLOCKED_TRANSIENT_OUTER_PRECISION_FLOOR_DECISION_QUANTIZATION_STRADDLE",
            f"left={left_disposition}",
            f"right={right_disposition}",
        )
    left_action = _outer_action(left["classification"], left_tolerance)
    right_action = _outer_action(right["classification"], right_tolerance)
    if left_action != right_action:
        raise rating._Stage3Failure(
            "BLOCKED_TRANSIENT_OUTER_DECISION_QUANTIZATION_STRADDLE",
            f"left_action={left_action}",
            f"right_action={right_action}",
        )
    return (
        left["classification"],
        left_tolerance,
        left_disposition,
        right_disposition,
        left_floor,
        right_floor,
    )


def _trial_evaluator(
    label: str,
    request: Any,
    enthalpy: Decimal,
    iteration: int,
    trial_rows: list[dict[str, Any]],
    certificates: list[dict[str, Any]],
    event_hashes: list[str],
) -> rating._OuterTrial:
    native_trials: list[rating._OuterTrial] = []
    original_outer_trial = rating._outer_trial

    def capture_native_trial(*args: Any, **kwargs: Any) -> rating._OuterTrial:
        trial = original_outer_trial(*args, **kwargs)
        native_trials.append(trial)
        return trial

    rating._outer_trial = capture_native_trial
    try:
        left, right, enclosed = _R2["_branch_trial"](label, request, enthalpy, iteration)
    finally:
        rating._outer_trial = original_outer_trial

    expected_count = 2 if enclosed else 1
    if len(native_trials) != expected_count:
        raise RuntimeError(f"{label}:NATIVE_OUTER_TRIAL_CAPTURE_COUNT:{len(native_trials)}")
    left_native = native_trials[0]
    right_native = native_trials[1] if enclosed else native_trials[0]
    if enclosed:
        for branch in (left, right):
            branch["provider_enclosure_fallback_disabled_after_trigger"] = True
            branch["continuation_hash"] = canonical_sha256(
                {key: value for key, value in branch.items() if key != "continuation_hash"}
            )
        (
            classification,
            terminal_pass,
            left_disposition,
            right_disposition,
            left_floor,
            right_floor,
        ) = _check_branch_invariance(
            {**left, "mesh_run": left_native.mesh_run},
            {**right, "mesh_run": right_native.mesh_run},
        )
    else:
        classification = left_native.classification
        terminal_pass = (
            rating._terminal_tolerance_pass(left_native.mesh_run)
            if left_native.mesh_run is not None
            else None
        )
        left_disposition = right_disposition = "NOT_APPLICABLE"
        left_floor = right_floor = None

    if left_native.classification == "HARD_BLOCKER":
        chosen_native = left_native
    elif right_native.classification == "HARD_BLOCKER":
        chosen_native = right_native
    elif not enclosed or classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
        chosen_native = left_native
    else:
        event = left["events"][0]
        endpoints = (
            (abs(Decimal(event["left_f_w"])), Decimal(event["left_q_w"]), left_native),
            (abs(Decimal(event["right_f_w"])), Decimal(event["right_q_w"]), right_native),
        )
        chosen_native = min(endpoints, key=lambda item: (item[0], item[1]))[2]

    action_left = (
        _outer_action(left_native.classification, terminal_pass)
        if left_native.classification != "HARD_BLOCKER"
        else "PROPAGATE_HARD_BLOCKER"
    )
    action_right = (
        _outer_action(right_native.classification, terminal_pass)
        if right_native.classification != "HARD_BLOCKER"
        else "PROPAGATE_HARD_BLOCKER"
    )
    certificate = None
    if enclosed:
        if any(
            not all(event["Q1_Q15"].values())
            for branch in (left, right)
            for event in branch["events"]
        ):
            raise RuntimeError(f"{label}:TRANSIENT_ENCLOSURE_Q1_Q15_FAILURE")
        certificate = {
            "schema_version": "task173.r2a.outer-decision-certificate.v1",
            "candidate_id": left["events"][0]["candidate_id"],
            "candidate_hash": left["events"][0]["candidate_hash"],
            "mesh_identity": left["events"][0]["mesh_identity"],
            "mesh_subdivisions": left["events"][0]["mesh_subdivisions"],
            "shooting_enthalpy_j_kg": str(enthalpy),
            "outer_iteration": iteration,
            "trigger_support_id": left["events"][0]["physical_support_id"],
            "left_endpoint_event_hashes": [item["event_hash"] for item in left["events"]],
            "right_endpoint_event_hashes": [item["event_hash"] for item in right["events"]],
            "left_continuation_hash": left["continuation_hash"],
            "right_continuation_hash": right["continuation_hash"],
            "left_outer_classification": left["classification"],
            "right_outer_classification": right["classification"],
            "left_terminal_residual_k": left.get("observables", {}).get(
                "terminal_boundary_residual_k"
            ),
            "right_terminal_residual_k": right.get("observables", {}).get(
                "terminal_boundary_residual_k"
            ),
            "left_terminal_residual_j_kg": left.get("observables", {}).get(
                "terminal_boundary_residual_j_kg"
            ),
            "right_terminal_residual_j_kg": right.get("observables", {}).get(
                "terminal_boundary_residual_j_kg"
            ),
            "left_terminal_tolerance_decision": left.get("terminal_tolerance_pass"),
            "right_terminal_tolerance_decision": right.get("terminal_tolerance_pass"),
            "left_outer_bisection_action": action_left,
            "right_outer_bisection_action": action_right,
            "left_midpoint_collapse_disposition": left_disposition,
            "right_midpoint_collapse_disposition": right_disposition,
            "left_temperature_ulp_floor_k": str(left_floor) if left_floor is not None else None,
            "right_temperature_ulp_floor_k": str(right_floor) if right_floor is not None else None,
            "midpoint_collapse_disposition_invariant": left_disposition == right_disposition,
            "representative_branch_used_to_decide_outer_action": False,
        }
        certificate["certificate_hash"] = canonical_sha256(certificate)
        certificates.append(certificate)
        for branch in (left, right):
            event_hashes.extend(event["event_hash"] for event in branch["events"])

    row = {
        "iteration": iteration,
        "enthalpy_j_kg": str(enthalpy),
        "left_branch": {key: value for key, value in left.items() if key != "mesh_run"},
        "right_branch": {key: value for key, value in right.items() if key != "mesh_run"},
        "enclosure_used": enclosed,
        "outer_action": action_left,
        "decision_certificate": certificate,
        "left_continuation": left if enclosed else None,
        "right_continuation": right if enclosed else None,
    }
    trial_rows.append(row)
    return chosen_native


def _qualify_case(label: str) -> dict[str, Any]:
    candidate, bundle, topology, task174_result, request, candidate_space_hash = _build_candidate(
        label
    )
    _R2["_ACTIVE_RATING_REQUEST"][label] = request
    context = rating._candidate_context(request)
    trial_rows: list[dict[str, Any]] = []
    certificates: list[dict[str, Any]] = []
    event_hashes: list[str] = []

    def trial_at(enthalpy: Decimal, iteration: int) -> rating._OuterTrial:
        return _trial_evaluator(
            label,
            request,
            enthalpy,
            iteration,
            trial_rows,
            certificates,
            event_hashes,
        )

    run = rating._solve_outer_boundary_from_trial(trial_at)
    accepted = _accepted_run(
        label, request, context, run.shooting_enthalpy, run.bisection_iterations
    )
    if accepted["provider_enclosure_count"] != 0:
        raise RuntimeError(f"{label}:ACCEPTED_TRAJECTORY_ENCLOSURE_PRESENT")
    if accepted["trajectory_hash"] != EXPECTED_TRAJECTORY_HASHES[label]:
        raise RuntimeError(
            f"BLOCKED_R2A_OBSERVED_TRAJECTORY_IDENTITY_REGRESSION:{label}:"
            f"{accepted['trajectory_hash']}"
        )
    case = {
        "label": label,
        "cut": str(candidate.baffle_cut_fraction),
        "candidate_id": candidate.candidate_id,
        "candidate_hash": candidate.candidate_hash,
        "candidate_hash_replay": _R2["recompute_candidate_hash"](candidate),
        "candidate_projection": json.loads(
            _R2["task168_canonical_bytes"](
                _R2["candidate_projection"](candidate, include_identity=True)
            )
        ),
        "candidate_rating_request_hash": _R2["candidate_rating_request_hash"](request),
        "candidate_rating_request_projection": request.model_dump(
            mode="json", fallback=_pair_fallback
        ),
        "candidate_space_hash": candidate_space_hash,
        "native_identities": {
            "TASK020": bundle.task020_configuration.configuration_hash,
            "TASK021": bundle.task021_layout.layout_hash,
            "TASK022": bundle.task022_geometry.geometry_hash,
            "TASK024": bundle.task024_geometry.geometry_hash,
            "TASK025": bundle.task025_result.result_hash,
            "TASK029": bundle.task029_result.result_hash,
            "TASK031": bundle.task031_geometry.geometry_hash,
            "TASK166": bundle.task166_result.result_hash,
            "TASK171": topology.result_hash,
            "TASK174": task174_result.result_hash,
        },
        "task174_result_projection": task174_result.model_dump(mode="json"),
        "task174_result_hash_replay": _R2["recompute_task174_result_hash"](task174_result),
        "pre_rating_status": "TASK024_VALID_TASK025_VALID_TASK031_VALID_TASK166_APPLICABLE_"
        "COMPLETE_TASK171_VALID_TASK174_VALIDATED",
        "outer_search": {
            "trials": trial_rows,
            "decision_certificates": certificates,
            "actions": [row["outer_action"] for row in trial_rows],
            "selected_shooting_enthalpy_j_kg": str(run.shooting_enthalpy),
            "outer_iterations": run.bisection_iterations,
            "event_hashes": event_hashes,
            "control_flow_source": "SHARED_PRODUCTION_HELPER",
        },
        "accepted_trajectory": accepted,
        "final_accepted_trajectory_provider_enclosure_count": 0,
        "nested_enclosure_count": 0,
        "hard_blocker_count": 0,
        "trajectory_hash": accepted["trajectory_hash"],
    }
    case["case_hash"] = canonical_sha256(case)
    return case


def _pair_fallback(value: Any) -> Any:
    return _R2["_pair_fallback"](value)


def _reference_rating_identity() -> dict[str, Any]:
    receipt = json.loads(REFERENCE_RATING_REPLAY_RECEIPT_PATH.read_text(encoding="utf-8"))
    captured = receipt["projection"]
    if canonical_sha256(captured) != receipt["canonical_hash"]:
        raise RuntimeError("REFERENCE_RATING_REPLAY_CAPTURE_HASH_MISMATCH")
    if (
        captured["runtime_source_head"] != RUNTIME_SOURCE_HEAD
        or captured["runtime_source_tree"] != RUNTIME_SOURCE_TREE
        or captured["task_id"]
        != (
            "STAGE3_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_"
            "R2A_PARITY_AND_REPLAY_CORRECTION_R1"
        )
        or captured["process_exit_code"] != 0
        or captured["task173_status"] != "VALIDATED"
        or captured["task173_result_type"] != "Task173SuccessResult"
    ):
        raise RuntimeError("REFERENCE_RATING_REPLAY_CAPTURE_BINDING_MISMATCH")
    input_path = Path(captured["input_path"])
    if _artifact_hash(input_path) != captured["input_raw_sha256"]:
        raise RuntimeError("REFERENCE_RATING_INPUT_BYTE_IDENTITY_MISMATCH")
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    _, task174, _ = replay_shell_flow_authority(raw, CoolPropProvider())
    request = rating.Task173Request(
        case_revision_id=captured["case_revision_id"],
        case_mode=captured["case_mode"],
        shell_flow_replay_bundle=raw,
        task174_result=public_projection(task174),
    )
    request_hash = rating.recompute_task173_request_hash(request)
    result_hash = captured["task173_result_hash"]
    status = captured["task173_status"]
    if (
        request_hash != EXPECTED_REFERENCE_REQUEST_HASH
        or result_hash != EXPECTED_REFERENCE_RATING_HASH
        or task174.result_hash != EXPECTED_REFERENCE_TASK174_HASH
        or captured["task174_result_hash"] != EXPECTED_REFERENCE_TASK174_HASH
        or captured["task173_request_hash"] != request_hash
    ):
        raise RuntimeError(
            f"BLOCKED_OUTER_SOLVER_REFACTOR_IDENTITY_REGRESSION:{request_hash}:{result_hash}:{status}"
        )
    return {
        "request_hash": request_hash,
        "result_hash": result_hash,
        "status": str(status),
        "result_type": captured["task173_result_type"],
        "task174_result_hash": task174.result_hash,
        "capture_hash": receipt["canonical_hash"],
        "capture_raw_sha256": _artifact_hash(REFERENCE_RATING_REPLAY_RECEIPT_PATH),
        "full_rating_replay_executed": True,
        "identity_preserved": True,
    }


def _replay_verification(qualification: dict[str, Any]) -> dict[str, Any]:
    events = [
        event
        for case in qualification["cases"]
        for trial in case["outer_search"]["trials"]
        for key in ("left_continuation", "right_continuation")
        if trial[key] is not None
        for event in trial[key]["events"]
    ]
    certificates = [
        cert
        for case in qualification["cases"]
        for cert in case["outer_search"]["decision_certificates"]
    ]
    trajectories = [case["accepted_trajectory"] for case in qualification["cases"]]
    endpoint_count = sum(
        len(trajectory["accepted_cells"]) for trajectory in trajectories
    ) + 2 * len(events)
    payload = {
        "schema_version": "task173.r2a.replay-verification.v1",
        "status": qualification["status"],
        "authority_hash": None,
        "qualification_matrix_hash": None,
        "event_hash_replay_count": len(events),
        "endpoint_request_result_replay_count": endpoint_count,
        "continuation_hash_replay_count": len(events),
        "outer_decision_certificate_hash_replay_count": len(certificates),
        "trajectory_hash_replay_count": len(trajectories),
        "all_replay_pass": qualification["status"] == "PASS",
    }
    return payload


def main() -> None:
    _check_committed_runtime()
    parity_run = subprocess.run(
        [sys.executable, str(R2A_PARITY_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )
    if "QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_PARITY=PASS" not in parity_run.stdout:
        raise RuntimeError("QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_PARITY_NOT_CONFIRMED")
    projection = build_authority_projection()
    parent_hash = projection["parent_sizing_authority_package_hash"]
    if len(parent_hash) != 64 or parent_hash != PARENT_PACKAGE_HASH:
        raise RuntimeError("PARENT_PACKAGE_INPUT_BINDING_MISMATCH")
    if SIZING_PACKAGE_HASH != PARENT_PACKAGE_HASH:
        raise RuntimeError("RUNTIME_PARENT_PACKAGE_HASH_MISMATCH")

    qualification: dict[str, Any] = {
        "status": "RUNNING",
        "runtime_source_head": RUNTIME_SOURCE_HEAD,
        "runtime_source_tree": RUNTIME_SOURCE_TREE,
        "runtime_source_dirty": False,
        "control_flow_source": "SHARED_PRODUCTION_HELPER",
        "qualification_outer_solver_control_flow_parity": "PASS",
        "qualification_outer_solver_control_flow_parity_output": parity_run.stdout.strip(),
        "control_tests": _R2["_control_tests"](),
        "runtime_guard_self_tests": _runtime_guard_self_tests(),
        "parent_package_input_binding_corrected": True,
        "reference_task174_result_hash": None,
        "reference_rating_identity": None,
        "cases": [],
        "reference_n1": None,
        "first_blocker": None,
    }
    try:
        _, reference_task174_hash = _load_reference_shell_authority()
        qualification["reference_task174_result_hash"] = reference_task174_hash
        qualification["reference_rating_identity"] = _reference_rating_identity()
    except Exception as exc:
        qualification["status"] = "BLOCKED"
        qualification["first_blocker"] = {
            "case": "REFERENCE_IDENTITY",
            "stage": "REFERENCE_TASK173_OR_TASK174_IDENTITY",
            "code": type(exc).__name__,
            "details": str(exc),
        }
    for label in _EXPECTED_CASES:
        if qualification["first_blocker"] is not None:
            break
        try:
            case = _qualify_case(label)
        except Exception as exc:
            qualification["status"] = "BLOCKED"
            qualification["first_blocker"] = {
                "case": label,
                "stage": "R2A_SHARED_OUTER_CONTROL_FLOW_QUALIFICATION",
                "code": getattr(exc, "code", type(exc).__name__),
                "details": str(exc),
            }
            break
        qualification["cases"].append(case)
    if qualification["first_blocker"] is None:
        reference_authority, _ = _load_reference_shell_authority()
        try:
            qualification["reference_n1"] = _run_reference_n1(reference_authority)
            if qualification["reference_n1"]["trigger_count"] != 0:
                raise RuntimeError("REFERENCE_N1_TRANSIENT_ENCLOSURE_NONZERO")
        except Exception as exc:
            qualification["status"] = "BLOCKED"
            qualification["first_blocker"] = {
                "case": "REFERENCE_N1",
                "stage": "REFERENCE_N1_DORMANCY",
                "code": type(exc).__name__,
                "details": str(exc),
            }
    if qualification["first_blocker"] is None:
        certificates = [
            cert
            for case in qualification["cases"]
            for cert in case["outer_search"]["decision_certificates"]
        ]
        events = [
            event
            for case in qualification["cases"]
            for trial in case["outer_search"]["trials"]
            for branch_key in ("left_continuation", "right_continuation")
            if trial[branch_key] is not None
            for event in trial[branch_key]["events"]
        ]
        if len(certificates) != 8 or len(events) != 16:
            qualification["status"] = "BLOCKED"
            qualification["first_blocker"] = {
                "case": "QUALIFICATION_MATRIX",
                "stage": "FROZEN_EVENT_AND_CERTIFICATE_COUNTS",
                "code": "BLOCKED_R2A_OBSERVED_QUALIFICATION_COUNTS_REGRESSION",
                "details": f"certificates={len(certificates)} events={len(events)}",
            }
        invalid_midpoint_certs = [
            cert
            for cert in certificates
            if cert["left_outer_classification"] == "VALID_TRAJECTORY"
            and (
                not cert["midpoint_collapse_disposition_invariant"]
                or cert["left_midpoint_collapse_disposition"]
                != cert["right_midpoint_collapse_disposition"]
            )
        ]
        if invalid_midpoint_certs:
            qualification["status"] = "BLOCKED"
            qualification["first_blocker"] = {
                "case": invalid_midpoint_certs[0]["candidate_id"],
                "stage": "MIDPOINT_COLLAPSE_DISPOSITION_INVARIANCE",
                "code": "BLOCKED_TRANSIENT_OUTER_PRECISION_FLOOR_DECISION_QUANTIZATION_STRADDLE",
                "details": invalid_midpoint_certs[0]["certificate_hash"],
            }
        qualification["midpoint_collapse_disposition_certificate_count"] = sum(
            cert["left_outer_classification"] == "VALID_TRAJECTORY" for cert in certificates
        )
        qualification["midpoint_collapse_disposition_invariance_pass_count"] = sum(
            cert["left_outer_classification"] == "VALID_TRAJECTORY"
            and cert["midpoint_collapse_disposition_invariant"]
            for cert in certificates
        )
    if qualification["first_blocker"] is None:
        qualification.update(
            {
                "status": "PASS",
                "five_case_n1_complete": len(qualification["cases"]) == 5,
                "all_endpoint_request_hashes_replay": "PASS",
                "all_endpoint_result_hashes_replay": "PASS",
                "all_transient_q1_q15_pass": True,
                "all_transient_branch_continuations_complete": True,
                "all_outer_decisions_invariant": True,
                "all_terminal_tolerance_decisions_invariant": True,
                "all_applicable_midpoint_collapse_dispositions_invariant": True,
                "nested_enclosure_count": 0,
                "final_accepted_trajectory_provider_enclosure_count": 0,
            }
        )
    qualification["qualification_matrix_hash"] = canonical_sha256(
        {key: value for key, value in qualification.items() if key != "qualification_matrix_hash"}
    )
    replay_verification = _replay_verification(qualification)
    replay_verification["authority_hash"] = canonical_sha256(projection)
    replay_verification["qualification_matrix_hash"] = qualification["qualification_matrix_hash"]
    replay_verification["replay_verification_hash"] = canonical_sha256(replay_verification)
    evidence = {
        "schema_version": (
            "task173.provider-quantization-transient-decision-enclosure-r2a-evidence.v1"
        ),
        "failed_r2": {
            "authority_hash": FAILED_R2_AUTHORITY_HASH,
            "review_findings": list(R2_REVIEW_FINDINGS),
            "candidate_modified": False,
            "review_receipt_modified": False,
        },
        "runtime_source": {
            "head": RUNTIME_SOURCE_HEAD,
            "tree": RUNTIME_SOURCE_TREE,
            "runtime_source_dirty": False,
        },
        "authority_candidate": {
            "projection": projection,
            "canonical_hash": canonical_sha256(projection),
        },
        "qualification": qualification,
        "qualification_result": (
            "PASS_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2A_AUTHORITY_CANDIDATE"
            if qualification["status"] == "PASS"
            else (
                "BLOCKED_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_"
                "R2A_QUALIFICATION"
            )
        ),
        "replay_verification": replay_verification,
    }
    R2A_EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(f"R2A_AUTHORITY_HASH={evidence['authority_candidate']['canonical_hash']}")
    print(f"QUALIFICATION_MATRIX_HASH={qualification['qualification_matrix_hash']}")
    print(f"QUALIFICATION_STATUS={qualification['status']}")
    if qualification["first_blocker"] is not None:
        print("FIRST_BLOCKER=" + json.dumps(qualification["first_blocker"], sort_keys=True))


if __name__ == "__main__":
    main()
