"""Replay every committed R2A authority, event, request, certificate and trajectory hash."""

from __future__ import annotations

import hashlib
import json
import math
import runpy
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    CANDIDATE_HASH_DOMAIN,
    sha256_domain_hex,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_id as candidate_id_from_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174SuccessResult,
    recompute_task174_result_hash,
)

HERE = Path(__file__).resolve().parent
EVIDENCE_PATH = HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
QUALIFICATION_RUNNER = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-qualification.py"
)
R2_REPLAY_RUNNER = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-replay.py"
)
R2A_H2_CAPTURE = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole-capture.py"
)
R2A_H2_REPLAY = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole-replay.py"
)
R2A_PARITY = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-control-flow-parity.py"
)
REFERENCE_RATING_RECEIPT = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-"
    "reference-rating-identity.json"
)
LEGACY_H2_CAPTURE = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole-capture.py"
)
EXPECTED_PARENT_PACKAGE_ID = "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
EXPECTED_PARENT_PACKAGE_HASH = "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
EXPECTED_TRAJECTORY_HASHES = {
    "TRAIN_A": "c865fabcd42658368fa3eb10a4e6edbd1124a1ba649dfc7cd650ae7bc7358843",
    "TRAIN_B": "b2e579624aae8a1a09a89c6236e3dc4ee40bf8aa952681ef884ee5f8ff179cfc",
    "H1": "c76b049b491235066ed8ea8ae005c3e125b359b8fd8fc1dd91938c8ff1d1bf50",
    "H2": "52b93a79a30693a843fab7cb7575560ecebc3051512fdf987d6eef040aa839d0",
    "H3": "73a0e5e199d452ba7e8a6dc7239c43f1f9bd857028c9722a6db9e9a1a444698a",
}


def _without_hash(value: dict[str, Any], name: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != name}


def _branch_run(continuation: dict[str, Any]) -> Any:
    payload = continuation["mesh_run"]
    shell_faces = payload["shell_faces"]
    terminal_face = shell_faces[-1]
    return SimpleNamespace(
        observables=SimpleNamespace(
            terminal_boundary_residual_k=Decimal(
                payload["observables"]["terminal_boundary_residual_k"]
            ),
            terminal_boundary_residual_j_kg=Decimal(
                payload["observables"]["terminal_boundary_residual_j_kg"]
            ),
        ),
        faces_shell=(
            SimpleNamespace(
                property_snapshot=SimpleNamespace(
                    cp_j_kg_k=terminal_face["property_snapshot"]["cp_j_kg_k"]
                )
            ),
        ),
    )


def _replay_midpoint_disposition(run: Any) -> tuple[str, Decimal]:
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


def _replay_outer_action(classification: str, terminal_pass: bool) -> str:
    if classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
        return "UPDATE_H_LOW"
    if classification != "VALID_TRAJECTORY":
        raise AssertionError(f"UNSUPPORTED_OUTER_CLASSIFICATION:{classification}")
    return "CANDIDATE_SHOOTING_ENTHALPY_SELECTED" if terminal_pass else "UPDATE_H_HIGH_CONTINUE"


def _verify_decision_certificate(trial: dict[str, Any]) -> None:
    left = trial["left_continuation"]
    right = trial["right_continuation"]
    cert = trial["decision_certificate"]
    if left is None or right is None or cert is None:
        raise AssertionError("ENCLOSURE_CONTINUATION_OR_CERTIFICATE_MISSING")
    if (
        trial["left_branch"]["classification"] != left["classification"]
        or trial["right_branch"]["classification"] != right["classification"]
        or trial["outer_action"] != cert["left_outer_bisection_action"]
        or trial["outer_action"] != cert["right_outer_bisection_action"]
    ):
        raise AssertionError("TRIAL_BRANCH_OR_ACTION_CROSS_BINDING_MISMATCH")
    for branch in (left, right):
        if not branch.get("provider_enclosure_fallback_disabled_after_trigger"):
            raise AssertionError("NESTED_ENCLOSURE_FALLBACK_NOT_DISABLED")
        if (
            canonical_sha256(_without_hash(branch, "continuation_hash"))
            != branch["continuation_hash"]
        ):
            raise AssertionError("CONTINUATION_HASH_MISMATCH")
    left_events, right_events = left["events"], right["events"]
    if len(left_events) != 1 or len(right_events) != 1:
        raise AssertionError("R2A_ENCLOSURE_BRANCH_EVENT_COUNT_NOT_ONE")
    if left["classification"] == "LOW_SIDE_DOMAIN_INFEASIBLE":
        if (
            right["classification"] != "LOW_SIDE_DOMAIN_INFEASIBLE"
            or cert["left_terminal_residual_k"] is not None
            or cert["right_terminal_residual_k"] is not None
            or cert["left_terminal_residual_j_kg"] is not None
            or cert["right_terminal_residual_j_kg"] is not None
            or cert["left_terminal_tolerance_decision"] is not None
            or cert["right_terminal_tolerance_decision"] is not None
            or cert["left_midpoint_collapse_disposition"] != "NOT_APPLICABLE"
            or cert["right_midpoint_collapse_disposition"] != "NOT_APPLICABLE"
            or cert["left_temperature_ulp_floor_k"] is not None
            or cert["right_temperature_ulp_floor_k"] is not None
            or not cert["midpoint_collapse_disposition_invariant"]
            or cert["left_outer_bisection_action"] != "UPDATE_H_LOW"
            or cert["right_outer_bisection_action"] != "UPDATE_H_LOW"
            or cert["left_outer_bisection_action"] != trial["outer_action"]
            or cert["representative_branch_used_to_decide_outer_action"]
        ):
            raise AssertionError("LOW_SIDE_OUTER_DECISION_CERTIFICATE_BINDING_MISMATCH")
        if canonical_sha256(_without_hash(cert, "certificate_hash")) != cert["certificate_hash"]:
            raise AssertionError("OUTER_DECISION_CERTIFICATE_HASH_MISMATCH")
        return
    if left["classification"] != "VALID_TRAJECTORY":
        raise AssertionError(f"UNSUPPORTED_OUTER_CLASSIFICATION:{left['classification']}")
    left_observables = left["observables"]
    right_observables = right["observables"]
    left_run = _branch_run(left)
    right_run = _branch_run(right)
    left_tol = rating._terminal_tolerance_pass(left_run)
    right_tol = rating._terminal_tolerance_pass(right_run)
    left_disposition, left_floor = _replay_midpoint_disposition(left_run)
    right_disposition, right_floor = _replay_midpoint_disposition(right_run)
    if left_tol != right_tol or left_disposition != right_disposition:
        raise AssertionError("TRANSIENT_OUTER_TERMINAL_OR_PRECISION_DECISION_STRADDLE")
    if (
        cert["candidate_id"] != left_events[0]["candidate_id"]
        or cert["candidate_hash"] != left_events[0]["candidate_hash"]
        or cert["mesh_identity"] != left_events[0]["mesh_identity"]
        or cert["mesh_subdivisions"] != left_events[0]["mesh_subdivisions"]
        or cert["shooting_enthalpy_j_kg"] != trial["enthalpy_j_kg"]
        or cert["outer_iteration"] != trial["iteration"]
        or cert["trigger_support_id"] != left_events[0]["physical_support_id"]
        or cert["left_continuation_hash"] != left["continuation_hash"]
        or cert["right_continuation_hash"] != right["continuation_hash"]
        or cert["left_endpoint_event_hashes"] != [event["event_hash"] for event in left_events]
        or cert["right_endpoint_event_hashes"] != [event["event_hash"] for event in right_events]
        or cert["left_outer_classification"] != left["classification"]
        or cert["right_outer_classification"] != right["classification"]
        or left["classification"] != right["classification"]
        or cert["left_terminal_residual_k"] != left_observables["terminal_boundary_residual_k"]
        or cert["right_terminal_residual_k"] != right_observables["terminal_boundary_residual_k"]
        or cert["left_terminal_residual_j_kg"]
        != left_observables["terminal_boundary_residual_j_kg"]
        or cert["right_terminal_residual_j_kg"]
        != right_observables["terminal_boundary_residual_j_kg"]
        or cert["left_terminal_tolerance_decision"] != left_tol
        or cert["right_terminal_tolerance_decision"] != right_tol
        or cert["left_midpoint_collapse_disposition"] != left_disposition
        or cert["right_midpoint_collapse_disposition"] != right_disposition
        or cert["left_temperature_ulp_floor_k"] != str(left_floor)
        or cert["right_temperature_ulp_floor_k"] != str(right_floor)
        or not cert["midpoint_collapse_disposition_invariant"]
        or cert["left_outer_bisection_action"]
        != _replay_outer_action(left["classification"], left_tol)
        or cert["right_outer_bisection_action"]
        != _replay_outer_action(right["classification"], right_tol)
        or cert["left_outer_bisection_action"] != cert["right_outer_bisection_action"]
        or cert["left_outer_bisection_action"] != trial["outer_action"]
        or cert["representative_branch_used_to_decide_outer_action"]
    ):
        raise AssertionError("OUTER_DECISION_CERTIFICATE_BINDING_MISMATCH")
    if canonical_sha256(_without_hash(cert, "certificate_hash")) != cert["certificate_hash"]:
        raise AssertionError("OUTER_DECISION_CERTIFICATE_HASH_MISMATCH")


def main() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    projection = evidence["authority_candidate"]["projection"]
    qualification = evidence["qualification"]
    qmodule = runpy.run_path(str(QUALIFICATION_RUNNER), run_name="task173_r2a_replay_library")
    qmodule["_check_committed_runtime"]()

    receipt_raw = REFERENCE_RATING_RECEIPT.read_bytes()
    if (
        hashlib.sha256(receipt_raw).hexdigest()
        != projection["qualification_artifacts"]["reference_rating_replay_receipt_sha256"]
    ):
        raise AssertionError("REFERENCE_RATING_RECEIPT_RAW_HASH_MISMATCH")
    receipt = json.loads(receipt_raw)
    if canonical_sha256(receipt["projection"]) != receipt["canonical_hash"]:
        raise AssertionError("REFERENCE_RATING_RECEIPT_CANONICAL_HASH_MISMATCH")
    replayed_reference_identity = qmodule["_reference_rating_identity"]()
    if replayed_reference_identity != qualification["reference_rating_identity"]:
        raise AssertionError("REFERENCE_RATING_IDENTITY_CAPTURE_REPLAY_MISMATCH")

    authority_hash = canonical_sha256(projection)
    if authority_hash != evidence["authority_candidate"]["canonical_hash"]:
        raise AssertionError("R2A_AUTHORITY_HASH_REPLAY_FAILURE")
    if (
        projection["parent_sizing_authority_package_id"] != EXPECTED_PARENT_PACKAGE_ID
        or projection["parent_sizing_authority_package_hash"] != EXPECTED_PARENT_PACKAGE_HASH
        or len(projection["parent_sizing_authority_package_hash"]) != 64
    ):
        raise AssertionError("PARENT_PACKAGE_INPUT_BINDING_MISMATCH")
    point_root = projection["ordinary_point_root_contract"]
    scope = projection["scope"]
    accepted_contract = projection["accepted_trajectory_contract"]
    if (
        point_root["equation"] != "F(q)=q-q_TASK172(q)"
        or point_root["task172_result_required"] != "VALID"
        or point_root["point_root_tolerance_w"] != "1e-6"
        or point_root["point_root_tolerance_changed"]
        or point_root["task172_acceptance_changed"]
        or not scope["enclosure_allowed_in_transient_outer_search"]
        or scope["enclosure_allowed_in_accepted_trajectory"]
        or scope["enclosure_allowed_in_final_mesh_observables"]
        or scope["maximum_provider_enclosures_per_transient_trajectory"] != 1
        or accepted_contract["provider_enclosure_allowed"]
        or accepted_contract["accepted_provider_enclosure_count"] != 0
        or accepted_contract["every_cell_closure_mode"] != "EXACT_VALID_POINT_ROOT"
        or accepted_contract["transient_enclosure_uncertainty_added_to_rated_cell_floors"]
        or accepted_contract["transient_enclosure_uncertainty_added_to_mesh_observables"]
        or accepted_contract["transient_enclosure_uncertainty_added_to_energy_tolerance"]
        or accepted_contract["energy_balance_semantics_changed"]
        or accepted_contract["mesh_precision_semantics_changed"]
        or projection["transient_diagnostics_only"]["used_in_final_physical_acceptance"]
        or projection["resource_caps"]["cell_root_bisection_iterations_total"] != 128
        or projection["resource_caps"]["task172_evaluations_per_cell_per_continuation"] != 512
        or projection["resource_caps"]["hole_recovery_levels_per_bracket"] != 12
        or projection["resource_caps"]["hole_recovery_brackets_per_cell"] != 15
        or projection["resource_caps"]["caps_increased"]
    ):
        raise AssertionError("R2A_AUTHORITY_SCOPE_OR_POINT_ROOT_CONTRACT_MISMATCH")
    matrix_hash = canonical_sha256(_without_hash(qualification, "qualification_matrix_hash"))
    if matrix_hash != qualification["qualification_matrix_hash"]:
        raise AssertionError("R2A_QUALIFICATION_MATRIX_HASH_REPLAY_FAILURE")
    if qualification["status"] != "PASS" or len(qualification["cases"]) != 5:
        raise AssertionError("R2A_QUALIFICATION_NOT_PASS_OR_INCOMPLETE")
    frozen_cuts = {
        "TRAIN_A": "0.215",
        "TRAIN_B": "0.220",
        "H1": "0.225",
        "H2": "0.275",
        "H3": "0.350",
    }
    if {case["label"]: case["cut"] for case in qualification["cases"]} != frozen_cuts:
        raise AssertionError("R2A_FROZEN_CASE_SELECTION_MISMATCH")

    artifacts = projection["qualification_artifacts"]
    artifact_pairs = (
        ("qualification_runner_sha256", QUALIFICATION_RUNNER),
        ("replay_runner_sha256", Path(__file__)),
        ("h2_capture_runner_sha256", R2A_H2_CAPTURE),
        ("h2_replay_runner_sha256", R2A_H2_REPLAY),
        ("control_flow_parity_runner_sha256", R2A_PARITY),
        ("legacy_h2_capture_runner_sha256", LEGACY_H2_CAPTURE),
    )
    for key, path in artifact_pairs:
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifacts[key]:
            raise AssertionError(f"R2A_ARTIFACT_HASH_MISMATCH:{key}")
    h2_evidence_path = (
        HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole.json"
    )
    h2_evidence = json.loads(h2_evidence_path.read_text(encoding="utf-8"))
    if (
        hashlib.sha256(h2_evidence_path.read_bytes()).hexdigest()
        != artifacts["h2_hole_evidence_sha256"]
        or h2_evidence["evidence_hash"] != artifacts["h2_hole_evidence_hash"]
    ):
        raise AssertionError("R2A_H2_HOLE_EVIDENCE_HASH_BINDING_MISMATCH")
    reproduced_projection = qmodule["build_authority_projection"]()
    reproduced_artifacts = reproduced_projection["qualification_artifacts"]
    reproduced_artifacts["h2_hole_evidence_path"] = str(
        Path(
            "docs/tasks/evidence/"
            "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole.json"
        )
    )
    reproduced_artifacts["h2_hole_evidence_sha256"] = hashlib.sha256(
        h2_evidence_path.read_bytes()
    ).hexdigest()
    reproduced_artifacts["h2_hole_evidence_hash"] = h2_evidence["evidence_hash"]
    if reproduced_projection != projection:
        raise AssertionError("R2A_AUTHORITY_PROJECTION_RECONSTRUCTION_MISMATCH")
    parity_run = subprocess.run(
        [sys.executable, str(R2A_PARITY)], check=True, capture_output=True, text=True
    )
    if "QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_PARITY=PASS" not in parity_run.stdout:
        raise AssertionError("R2A_SHARED_PRODUCTION_CONTROL_FLOW_PARITY_FAILURE")

    replayer = runpy.run_path(str(R2_REPLAY_RUNNER), run_name="task173_r2_replay_library")
    event_hashes: list[str] = []
    certificate_hashes: list[str] = []
    trajectory_hashes: list[str] = []
    endpoint_replay_count = 0
    continuation_hash_count = 0
    for case in qualification["cases"]:
        label = case["label"]
        candidate, _bundle, _topology, task174_result, request, _space_hash = qmodule[
            "_build_candidate"
        ](label)
        candidate_projection = case["candidate_projection"]
        candidate_base = _without_hash(
            _without_hash(candidate_projection, "candidate_hash"), "candidate_id"
        )
        candidate_hash = sha256_domain_hex(CANDIDATE_HASH_DOMAIN, candidate_base)
        if (
            candidate_hash != case["candidate_hash"]
            or candidate_hash != case["candidate_hash_replay"]
            or candidate_id_from_hash(candidate_hash) != case["candidate_id"]
            or candidate.candidate_hash != case["candidate_hash"]
            or candidate.candidate_id != case["candidate_id"]
        ):
            raise AssertionError(f"CANDIDATE_IDENTITY_REPLAY_FAILURE:{label}")
        rating_projection = request.model_dump(mode="json", fallback=qmodule["_pair_fallback"])
        if (
            canonical_sha256(rating_projection)
            != canonical_sha256(case["candidate_rating_request_projection"])
            or candidate_rating_request_hash(request) != case["candidate_rating_request_hash"]
        ):
            raise AssertionError(f"CANDIDATE_RATING_REQUEST_REPLAY_FAILURE:{label}")
        task174 = Task174SuccessResult.model_validate(
            case["task174_result_projection"], strict=False
        )
        if (
            recompute_task174_result_hash(task174) != case["task174_result_hash_replay"]
            or task174.result_hash != task174_result.result_hash
            or task174.status != "VALIDATED"
        ):
            raise AssertionError(f"TASK174_RESULT_REPLAY_FAILURE:{label}")

        accepted = case["accepted_trajectory"]
        trajectory_hash = canonical_sha256(_without_hash(accepted, "trajectory_hash"))
        if (
            trajectory_hash != accepted["trajectory_hash"]
            or trajectory_hash != case["trajectory_hash"]
            or trajectory_hash != EXPECTED_TRAJECTORY_HASHES[label]
            or case["final_accepted_trajectory_provider_enclosure_count"] != 0
            or accepted["provider_enclosure_count"] != 0
            or accepted["transient_search_mode"]
            or accepted["provider_enclosure_fallback_allowed"]
            or set(accepted["closure_modes"]) != {"EXACT_VALID_POINT_ROOT"}
            or len(accepted["accepted_cells"]) != 5
        ):
            raise AssertionError(f"ACCEPTED_TRAJECTORY_REPLAY_OR_SCOPE_FAILURE:{label}")
        trajectory_hashes.append(trajectory_hash)
        endpoint_replay_count += replayer["_verify_mesh_run"](accepted)

        if (
            case["outer_search"]["control_flow_source"] != "SHARED_PRODUCTION_HELPER"
            or case["outer_search"]["actions"]
            != [trial["outer_action"] for trial in case["outer_search"]["trials"]]
            or accepted["shooting_enthalpy_j_kg"]
            != case["outer_search"]["selected_shooting_enthalpy_j_kg"]
            or case["nested_enclosure_count"] != 0
            or case["final_accepted_trajectory_provider_enclosure_count"] != 0
        ):
            raise AssertionError(f"OUTER_SEARCH_OR_ACCEPTED_TRAJECTORY_BINDING_MISMATCH:{label}")
        case_event_hashes: list[str] = []
        for trial in case["outer_search"]["trials"]:
            for branch_key in ("left_branch", "right_branch"):
                branch = trial[branch_key]
                if (
                    branch["transient_search_mode"] is not True
                    or branch["provider_enclosure_fallback_allowed"] is not True
                ):
                    raise AssertionError("TRANSIENT_SEARCH_SCOPE_MISMATCH")
            if not trial["enclosure_used"]:
                if trial["decision_certificate"] is not None:
                    raise AssertionError("CERTIFICATE_WITHOUT_ENCLOSURE")
                continue
            _verify_decision_certificate(trial)
            for continuation_key in ("left_continuation", "right_continuation"):
                continuation = trial[continuation_key]
                continuation_hash_count += 1
                for event in continuation["events"]:
                    endpoint_replay_count += replayer["_verify_event"](event)
                    event_hashes.append(event["event_hash"])
                    case_event_hashes.append(event["event_hash"])
            certificate_hashes.append(trial["decision_certificate"]["certificate_hash"])
        if case_event_hashes != case["outer_search"]["event_hashes"]:
            raise AssertionError(f"CASE_EVENT_HASH_ORDER_MISMATCH:{label}")
        if canonical_sha256(_without_hash(case, "case_hash")) != case["case_hash"]:
            raise AssertionError(f"CASE_HASH_MISMATCH:{label}")

    if (
        len(event_hashes) != 16
        or len(certificate_hashes) != 8
        or continuation_hash_count != 16
        or len(trajectory_hashes) != 5
        or endpoint_replay_count != 57
    ):
        raise AssertionError(
            "R2A_REPLAY_COUNT_MISMATCH:"
            f"events={len(event_hashes)} certs={len(certificate_hashes)} "
            f"continuations={continuation_hash_count} trajectories={len(trajectory_hashes)} "
            f"endpoints={endpoint_replay_count}"
        )
    midpoint_certs = [
        trial["decision_certificate"]
        for case in qualification["cases"]
        for trial in case["outer_search"]["trials"]
        if trial["decision_certificate"] is not None
        and trial["decision_certificate"]["left_outer_classification"] == "VALID_TRAJECTORY"
    ]
    if (
        qualification["midpoint_collapse_disposition_certificate_count"] != len(midpoint_certs)
        or qualification["midpoint_collapse_disposition_invariance_pass_count"]
        != sum(cert["midpoint_collapse_disposition_invariant"] for cert in midpoint_certs)
        or not all(cert["midpoint_collapse_disposition_invariant"] for cert in midpoint_certs)
        or qualification["all_applicable_midpoint_collapse_dispositions_invariant"] is not True
    ):
        raise AssertionError("R2A_MIDPOINT_COLLAPSE_INVARIANCE_COUNT_MISMATCH")
    if qualification["reference_n1"]["trigger_count"] != 0:
        raise AssertionError("REFERENCE_N1_ENCLOSURE_NOT_DORMANT")

    replay_verification = evidence["replay_verification"]
    replay_payload = _without_hash(replay_verification, "replay_verification_hash")
    expected_replay_payload = {
        "schema_version": "task173.r2a.replay-verification.v1",
        "status": "PASS",
        "authority_hash": authority_hash,
        "qualification_matrix_hash": matrix_hash,
        "event_hash_replay_count": len(event_hashes),
        "endpoint_request_result_replay_count": endpoint_replay_count,
        "continuation_hash_replay_count": continuation_hash_count,
        "outer_decision_certificate_hash_replay_count": len(certificate_hashes),
        "trajectory_hash_replay_count": len(trajectory_hashes),
        "all_replay_pass": True,
    }
    if (
        canonical_sha256(replay_payload) != replay_verification["replay_verification_hash"]
        or replay_payload != expected_replay_payload
    ):
        raise AssertionError("R2A_REPLAY_VERIFICATION_BINDING_MISMATCH")

    print(f"AUTHORITY_HASH={authority_hash}")
    print(f"QUALIFICATION_MATRIX_HASH={matrix_hash}")
    print(f"EVENT_HASH_REPLAY_COUNT={len(event_hashes)}")
    print(f"ENDPOINT_REQUEST_RESULT_REPLAY_COUNT={endpoint_replay_count}")
    print(f"CONTINUATION_HASH_REPLAY_COUNT={continuation_hash_count}")
    print(f"OUTER_DECISION_CERTIFICATE_HASH_REPLAY_COUNT={len(certificate_hashes)}")
    print(f"TRAJECTORY_HASH_REPLAY_COUNT={len(trajectory_hashes)}")
    print(f"QUALIFICATION_STATUS={qualification['status']}")
    print("ALL_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
