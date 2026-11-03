"""Replay the committed R2 authority and all persisted qualification identities."""

from __future__ import annotations

import hashlib
import json
import math
import runpy
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    CANDIDATE_HASH_DOMAIN,
    sha256_domain_hex,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    candidate_id as candidate_id_from_hash,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174SuccessResult,
    recompute_task174_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import FlowRegime
from hexagent.exchangers.shell_tube.tube_side_thermal.nusselt_selector import (
    check_pr_envelope,
    select_regime,
)

HERE = Path(__file__).resolve().parent
EVIDENCE_PATH = HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2.json"
QUALIFICATION_RUNNER = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-qualification.py"
)
REPLAY_RUNNER = Path(__file__)


def _restore(value: Any) -> Any:
    if isinstance(value, dict) and value.get("__task173_type__") == "ReferencePlanePair":
        return ReferencePlanePair(
            ReferencePlaneToken(value["start"]), ReferencePlaneToken(value["end"])
        )
    if isinstance(value, dict):
        return {key: _restore(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore(item) for item in value]
    return value


def _without_hash(value: dict[str, Any], field: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != field}


def _replay_endpoint(
    request_projection: dict[str, Any], result_projection: dict[str, Any]
) -> dict[str, Any]:
    request = CandidateTask172LocalRequest.model_validate(
        _restore(request_projection), strict=False
    )
    result = Task172LocalResult.model_validate(result_projection, strict=False)
    request_hash = task172.recompute_task172_request_hash(request)
    result_hash = task172.recompute_task172_result_hash(result)
    binding = request.candidate_binding
    checks = {
        "request_hash": request_hash == result.request_hash,
        "result_hash": result_hash == result.result_hash,
        "support_identity": task172.recompute_task172_support_id(request)
        == result.physical_support_id,
        "candidate_binding": result.case_id == binding.candidate_id
        and result.case_revision_id == binding.candidate_id
        and binding.candidate_hash == request.candidate_binding.candidate_hash,
        "authority_package_binding": binding.authority_package_id
        == "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
        and binding.authority_package_hash
        == "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9",
        "task166_binding": result.task171_result_hash == binding.task171_result.result_hash
        and binding.task171_result.result_hash == result.task171_result_hash
        and binding.task166_result.result_hash
        == request.shell_flow_authority.task166_result.result_hash,
        "task171_binding": result.topology_id == binding.task171_result.topology_id
        and result.task171_result_hash == binding.task171_result.result_hash
        and result.physical_ownership_hash == binding.task171_result.physical_ownership_hash,
    }
    if not all(checks.values()):
        raise AssertionError(f"ENDPOINT_REPLAY_FAILURE:{checks}")
    return {
        "request_hash": request_hash,
        "result_hash": result_hash,
        "support_id": task172.recompute_task172_support_id(request),
        "candidate_id": binding.candidate_id,
        "candidate_hash": binding.candidate_hash,
        "authority_package_id": binding.authority_package_id,
        "authority_package_hash": binding.authority_package_hash,
        "task166_result_hash": binding.task166_result.result_hash,
        "task171_result_hash": binding.task171_result.result_hash,
        "checks": checks,
    }


def _verify_event(event: dict[str, Any]) -> int:
    expected_event_hash = canonical_sha256(_without_hash(event, "event_hash"))
    if expected_event_hash != event["event_hash"]:
        raise AssertionError(f"EVENT_HASH_MISMATCH:{event.get('label')}:{event.get('branch')}")
    left = _replay_endpoint(
        event["endpoint_request_projection_left"], event["endpoint_result_projection_left"]
    )
    right = _replay_endpoint(
        event["endpoint_request_projection_right"], event["endpoint_result_projection_right"]
    )
    left_result = Task172LocalResult.model_validate(
        event["endpoint_result_projection_left"], strict=False
    )
    right_result = Task172LocalResult.model_validate(
        event["endpoint_result_projection_right"], strict=False
    )
    left_q = float.fromhex(event["left_q_hex"])
    right_q = float.fromhex(event["right_q_hex"])
    left_f = Decimal(event["left_f_w"])
    right_f = Decimal(event["right_f_w"])
    left_residual = Decimal(str(left_q)) - left_result.signed_q_hot_to_cold_w
    right_residual = Decimal(str(right_q)) - right_result.signed_q_hot_to_cold_w
    if (
        left_q.hex() != event["left_q_hex"]
        or right_q.hex() != event["right_q_hex"]
        or math.nextafter(left_q, right_q) != right_q
        or left_f != left_residual
        or right_f != right_residual
        or not left_f < 0 < right_f
        or abs(left_f) <= Decimal("1e-6")
        or abs(right_f) <= Decimal("1e-6")
        or left["request_hash"] != event["left_task172_request_hash"]
        or right["request_hash"] != event["right_task172_request_hash"]
        or left["result_hash"] != event["left_task172_result_hash"]
        or right["result_hash"] != event["right_task172_result_hash"]
    ):
        raise AssertionError(f"EVENT_ENDPOINT_FACT_MISMATCH:{event.get('event_hash')}")
    q_checks = event["Q1_Q15"]
    if set(q_checks) != {f"Q{i}" for i in range(1, 16)} or not all(q_checks.values()):
        raise AssertionError(f"EVENT_Q_PREDICATE_FAILURE:{event.get('event_hash')}:{q_checks}")
    expected_coordinate_names = {
        "tube_downstream_h",
        "shell_next_face_h",
        "tube_midpoint_h",
        "shell_midpoint_h",
    }
    coordinates = event["provider_coordinates"]
    if {item["name"] for item in coordinates} != expected_coordinate_names:
        raise AssertionError("PROVIDER_COORDINATE_COVERAGE_MISMATCH")
    snapshots = event["provider_state_snapshots"]
    if len(snapshots) != 8:
        raise AssertionError("PROVIDER_SNAPSHOT_COUNT_MISMATCH")
    for coordinate in coordinates:
        provider_state_names = {
            "tube_downstream_h": ("left_tube_downstream", "right_tube_downstream"),
            "shell_next_face_h": ("left_shell_next_face", "right_shell_next_face"),
            "tube_midpoint_h": ("left_tube_midpoint", "right_tube_midpoint"),
            "shell_midpoint_h": ("left_shell_midpoint", "right_shell_midpoint"),
        }
        left_snapshot_name, right_snapshot_name = provider_state_names[coordinate["name"]]
        if (
            coordinate["left_decimal"] != snapshots[left_snapshot_name]["inputs"]["enthalpy_j_kg"]
            or coordinate["right_decimal"]
            != snapshots[right_snapshot_name]["inputs"]["enthalpy_j_kg"]
        ):
            raise AssertionError("PROVIDER_COORDINATE_NOT_BOUND_TO_ACTUAL_PH_SNAPSHOT")
        left_value = float.fromhex(coordinate["left_hex"])
        right_value = float.fromhex(coordinate["right_hex"])
        identical = left_value == right_value
        adjacent = identical or math.nextafter(left_value, right_value) == right_value
        if (
            identical != coordinate["identical"]
            or not adjacent
            or not coordinate["adjacent_or_identical"]
            or (not identical and coordinate["nextafter_left_toward_right"] != right_value.hex())
        ):
            raise AssertionError(f"PROVIDER_COORDINATE_NOT_EXHAUSTED:{coordinate}")
    for snapshot in snapshots.values():
        if (
            snapshot["phase"] != "liquid"
            or snapshot["backend"] != "HEOS::Water"
            or snapshot["provider"] != "CoolProp"
            or snapshot["provider_version"] != "8.0.0"
            or snapshot["provider_git_revision"] != "ae81610e7d23efc57f9d051c8e70a4d66e87537f"
            or snapshot["reference_state"] != "DEF"
        ):
            raise AssertionError("PROVIDER_SNAPSHOT_AUTHORITY_MISMATCH")
    if (
        left_result.status != "VALIDATED"
        or right_result.status != "VALIDATED"
        or left_result.case_id != right_result.case_id
        or left_result.task171_result_hash != right_result.task171_result_hash
        or left_result.physical_support_id != right_result.physical_support_id
        or left_result.wall_interface_id != right_result.wall_interface_id
    ):
        raise AssertionError("ENDPOINT_SUPPORT_OR_CANDIDATE_MISMATCH")
    left_regime, left_correlation, left_version = select_regime(
        left_result.tube_reynolds_number, left_result.tube_prandtl_number_bulk
    )
    right_regime, right_correlation, right_version = select_regime(
        right_result.tube_reynolds_number, right_result.tube_prandtl_number_bulk
    )
    if (
        left_regime is not FlowRegime.TURBULENT
        or right_regime is not FlowRegime.TURBULENT
        or not check_pr_envelope(left_regime, left_result.tube_prandtl_number_bulk)
        or not check_pr_envelope(right_regime, right_result.tube_prandtl_number_bulk)
        or left_correlation != right_correlation
        or left_version != right_version
    ):
        raise AssertionError("ENDPOINT_APPLICABILITY_BRANCH_MISMATCH")
    if event["representative_endpoint"] not in {"LEFT", "RIGHT"} or event["exact_point_root_found"]:
        raise AssertionError("ENCLOSURE_ROOT_SEMANTICS_MISMATCH")
    if event["used_in_final_physical_acceptance"]:
        raise AssertionError("TRANSIENT_ENCLOSURE_USED_AS_PHYSICAL_ACCEPTANCE")
    return 2


def _verify_mesh_run(mesh_run: dict[str, Any]) -> int:
    if canonical_sha256(mesh_run["mesh_projection"]) != mesh_run["mesh_result_hash"]:
        raise AssertionError("MESH_RESULT_HASH_MISMATCH")
    endpoint_count = 0
    for cell in mesh_run["accepted_cells"]:
        replay = _replay_endpoint(
            cell["task172_request_projection"], cell["task172_result_projection"]
        )
        if (
            replay["request_hash"] != cell["task172_request_hash"]
            or replay["result_hash"] != cell["task172_result_hash"]
        ):
            raise AssertionError("ACCEPTED_CELL_ENDPOINT_IDENTITY_MISMATCH")
        endpoint_count += 1
    return endpoint_count


def main() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text())
    projection = evidence["authority_candidate"]["projection"]
    runtime_head = projection["runtime_snapshot_head"]
    is_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", runtime_head, "HEAD"], check=False
    )
    if is_ancestor.returncode != 0:
        raise AssertionError("RUNTIME_SNAPSHOT_NOT_IN_REPLAY_HEAD_ANCESTRY")
    runtime_tree = subprocess.check_output(
        ["git", "rev-parse", f"{runtime_head}^{{tree}}"], text=True
    ).strip()
    if runtime_tree != projection["runtime_snapshot_tree"]:
        raise AssertionError("RUNTIME_SNAPSHOT_TREE_MISMATCH")
    runtime_paths = [
        "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
        "src/hexagent/exchangers/shell_tube/task172_local_runtime",
        "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
        "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
        "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
        "tests/exchangers/shell_tube/test_task173_integrated_sizing.py",
        "tests/exchangers/shell_tube/test_task174_hydraulic_orchestration.py",
    ]
    subprocess.run(
        ["git", "diff", "--exit-code", runtime_head, "HEAD", "--", *runtime_paths],
        check=True,
    )
    rebaseline = evidence["runtime_rebaseline_v3"]
    if (
        canonical_sha256(
            {key: value for key, value in rebaseline.items() if key != "provenance_hash"}
        )
        != projection["runtime_rebaseline_v3_provenance_hash"]
    ):
        raise AssertionError("RUNTIME_REBASELINE_V3_PROVENANCE_REPLAY_FAILURE")
    qualification_module = runpy.run_path(str(QUALIFICATION_RUNNER))
    qualification_module["_check_committed_runtime"]()
    authority_hash = canonical_sha256(projection)
    if authority_hash != evidence["authority_candidate"]["canonical_hash"]:
        raise AssertionError("AUTHORITY_HASH_REPLAY_FAILURE")
    artifacts = projection["qualification_artifacts"]
    expected_qualification_sha = artifacts["qualification_runner_sha256"]
    expected_replay_sha = artifacts["replay_runner_sha256"]
    if hashlib.sha256(QUALIFICATION_RUNNER.read_bytes()).hexdigest() != expected_qualification_sha:
        raise AssertionError("QUALIFICATION_RUNNER_SHA256_MISMATCH")
    if hashlib.sha256(REPLAY_RUNNER.read_bytes()).hexdigest() != expected_replay_sha:
        raise AssertionError("REPLAY_RUNNER_SHA256_MISMATCH")
    qualification = evidence["qualification"]
    matrix_hash = canonical_sha256(_without_hash(qualification, "qualification_matrix_hash"))
    if matrix_hash != qualification["qualification_matrix_hash"]:
        raise AssertionError("QUALIFICATION_MATRIX_HASH_REPLAY_FAILURE")
    if qualification["runtime_source_head"] != projection["runtime_snapshot_head"]:
        raise AssertionError("RUNTIME_SNAPSHOT_BINDING_MISMATCH")

    event_hashes: list[str] = []
    endpoint_replays = 0
    continuation_replays = 0
    certificate_hashes: list[str] = []
    trajectory_hashes: list[str] = []
    for case in qualification["cases"]:
        candidate_projection = case["candidate_projection"]
        candidate_base = _without_hash(
            _without_hash(candidate_projection, "candidate_hash"), "candidate_id"
        )
        candidate_hash = sha256_domain_hex(CANDIDATE_HASH_DOMAIN, candidate_base)
        if (
            candidate_hash != case["candidate_hash"]
            or candidate_hash != case["candidate_hash_replay"]
            or candidate_id_from_hash(candidate_hash) != case["candidate_id"]
            or candidate_projection["candidate_hash"] != candidate_hash
            or candidate_projection["candidate_id"] != case["candidate_id"]
        ):
            raise AssertionError(f"CANDIDATE_IDENTITY_REPLAY_FAILURE:{case['label']}")
        _candidate, _bundle, _topology, _task174, rating_request, _space_hash = (
            qualification_module["_build_candidate"](case["label"])
        )
        replayed_rating_projection = rating_request.model_dump(
            mode="json", fallback=qualification_module["_pair_fallback"]
        )
        if (
            canonical_sha256(replayed_rating_projection)
            != canonical_sha256(case["candidate_rating_request_projection"])
            or candidate_rating_request_hash(rating_request)
            != case["candidate_rating_request_hash"]
        ):
            raise AssertionError(f"CANDIDATE_RATING_REQUEST_HASH_MISMATCH:{case['label']}")
        task174 = Task174SuccessResult.model_validate(
            case["task174_result_projection"], strict=False
        )
        if (
            recompute_task174_result_hash(task174) != case["task174_result_hash_replay"]
            or task174.result_hash != case["native_identities"]["TASK174"]
            or task174.status != "VALIDATED"
        ):
            raise AssertionError(f"TASK174_IDENTITY_REPLAY_FAILURE:{case['label']}")
        accepted = case["accepted_trajectory"]
        trajectory_hash = canonical_sha256(_without_hash(accepted, "trajectory_hash"))
        if (
            trajectory_hash != accepted["trajectory_hash"]
            or trajectory_hash != case["trajectory_hash"]
            or case["final_accepted_trajectory_provider_enclosure_count"] != 0
            or accepted["provider_enclosure_count"] != 0
            or accepted["provider_enclosure_fallback_allowed"]
            or accepted["transient_search_mode"]
        ):
            raise AssertionError(f"ACCEPTED_TRAJECTORY_IDENTITY_OR_SCOPE_FAILURE:{case['label']}")
        trajectory_hashes.append(trajectory_hash)
        endpoint_replays += _verify_mesh_run(accepted)
        for trial in case["outer_search"]["trials"]:
            for branch_key in ("left_branch", "right_branch"):
                branch = trial[branch_key]
                if (
                    branch["transient_search_mode"] is not True
                    or branch["provider_enclosure_fallback_allowed"] is not True
                ):
                    raise AssertionError("TRANSIENT_SCOPE_FLAG_MISMATCH")
            if not trial["enclosure_used"]:
                if trial["decision_certificate"] is not None:
                    raise AssertionError("CERTIFICATE_WITHOUT_ENCLOSURE")
                continue
            left_continuation = trial["left_continuation"]
            right_continuation = trial["right_continuation"]
            if left_continuation is None or right_continuation is None:
                raise AssertionError("ENCLOSURE_CONTINUATION_MISSING")
            for continuation in (left_continuation, right_continuation):
                continuation_hash = canonical_sha256(
                    _without_hash(continuation, "continuation_hash")
                )
                if continuation_hash != continuation["continuation_hash"]:
                    raise AssertionError("ENCLOSURE_CONTINUATION_HASH_MISMATCH")
                continuation_replays += 1
                for event in continuation["events"]:
                    endpoint_replays += _verify_event(event)
                    event_hashes.append(event["event_hash"])
            certificate = trial["decision_certificate"]
            cert_hash = canonical_sha256(_without_hash(certificate, "certificate_hash"))
            if (
                cert_hash != certificate["certificate_hash"]
                or certificate["left_continuation_hash"] != left_continuation["continuation_hash"]
                or certificate["right_continuation_hash"] != right_continuation["continuation_hash"]
                or certificate["left_outer_classification"]
                != certificate["right_outer_classification"]
                or certificate["left_terminal_tolerance_decision"]
                != certificate["right_terminal_tolerance_decision"]
                or certificate["left_outer_bisection_action"]
                != certificate["right_outer_bisection_action"]
                or certificate["representative_branch_used_to_decide_outer_action"]
            ):
                raise AssertionError("OUTER_DECISION_CERTIFICATE_REPLAY_FAILURE")
            certificate_hashes.append(cert_hash)
        case_hash = canonical_sha256(_without_hash(case, "case_hash"))
        if case_hash != case["case_hash"]:
            raise AssertionError(f"CASE_HASH_MISMATCH:{case['label']}")

    if qualification["status"] == "PASS" and len(qualification["cases"]) != 5:
        raise AssertionError("PASS_WITH_INCOMPLETE_FIVE_CASE_MATRIX")
    reference = qualification.get("reference_n1")
    if qualification["status"] == "PASS" and (reference is None or reference["trigger_count"] != 0):
        raise AssertionError("REFERENCE_N1_DORMANCY_REPLAY_FAILURE")
    event_hash_rows = [event["event_hash"] for event in _iter_events(qualification)]
    if event_hash_rows != event_hashes:
        raise AssertionError("EVENT_TRAVERSAL_COUNT_MISMATCH")

    replay_verification = evidence["replay_verification"]
    replay_payload = _without_hash(replay_verification, "replay_verification_hash")
    if canonical_sha256(replay_payload) != replay_verification["replay_verification_hash"]:
        raise AssertionError("REPLAY_VERIFICATION_HASH_MISMATCH")
    expected_replay_verification = {
        "schema_version": "task173.r2.replay-verification.v1",
        "status": "PASS",
        "authority_hash": authority_hash,
        "qualification_matrix_hash": matrix_hash,
        "event_hash_replay_count": len(event_hashes),
        "endpoint_request_result_replay_count": endpoint_replays,
        "continuation_hash_replay_count": continuation_replays,
        "outer_decision_certificate_hash_replay_count": len(certificate_hashes),
        "trajectory_hash_replay_count": len(trajectory_hashes),
        "all_replay_pass": True,
    }
    if replay_payload != expected_replay_verification:
        raise AssertionError("REPLAY_VERIFICATION_COUNTS_OR_BINDINGS_MISMATCH")

    print(f"AUTHORITY_HASH={authority_hash}")
    print(f"QUALIFICATION_MATRIX_HASH={matrix_hash}")
    print(f"EVENT_HASH_REPLAY_COUNT={len(event_hashes)}")
    print(f"ENDPOINT_REQUEST_RESULT_REPLAY_COUNT={endpoint_replays}")
    print(f"CONTINUATION_HASH_REPLAY_COUNT={continuation_replays}")
    print(f"OUTER_DECISION_CERTIFICATE_HASH_REPLAY_COUNT={len(certificate_hashes)}")
    print(f"TRAJECTORY_HASH_REPLAY_COUNT={len(trajectory_hashes)}")
    print(f"QUALIFICATION_STATUS={qualification['status']}")
    print("ALL_REPLAY_PASS=true")


def _iter_events(qualification: dict[str, Any]):
    for case in qualification["cases"]:
        for trial in case["outer_search"]["trials"]:
            for continuation_key in ("left_continuation", "right_continuation"):
                continuation = trial.get(continuation_key)
                if continuation is not None:
                    yield from continuation["events"]


if __name__ == "__main__":
    main()
