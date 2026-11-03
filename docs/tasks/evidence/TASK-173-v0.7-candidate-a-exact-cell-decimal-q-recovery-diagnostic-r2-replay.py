#!/usr/bin/env python3
"""Build once from local R2 capture files, then replay the committed compact bundle.

Neither mode invokes a property provider, Task172 solver, Candidate Rating, or Sizing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import runpy
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)

ROOT = Path(__file__).resolve().parents[3]
STEM = "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2"
SUMMARY_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}-execution-summary.json"
RAW_EVIDENCE_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}.json"
RAW_CHECKPOINT_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}-execution" / "checkpoint.json"
RAW_TRACE_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}-execution" / "trace.jsonl"
PREFLIGHT_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}-preflight.json"
RUNNER_PATH = (
    ROOT
    / "docs/tasks/evidence"
    / "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r1.py"
)

EXPECTED = {
    "start_head": "2348b977e71d8f88f4107fceab35392962f8aa92",
    "runtime_head": "21386a88f8290538172e9389ed46f50c3697a426",
    "runtime_tree": "ce61a818b82f908729d2bdf4553cc27012354952",
    "request_hash": "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7",
    "candidate_id": "adeab5b1-a339-5eb3-aa66-011ffe49bac0",
    "candidate_hash": "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767",
    "completion_request_hash": "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae",
    "candidate_space_hash": "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea",
    "blocked_result_hash": "daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c",
    "left_q": "268.4228547695099",
    "right_q": "268.42285476950997",
    "support_id": (
        "urn:hxforge:task171:candidate:"
        "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2"
    ),
    "task172_calls": 144217,
    "task172_holes": 27,
}


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            length += len(block)
    return digest.hexdigest(), length


def _restore_pairs(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__task173_type__") == "ReferencePlanePair":
            return ReferencePlanePair(
                start=ReferencePlaneToken(value["start"]),
                end=ReferencePlaneToken(value["end"]),
            )
        return {key: _restore_pairs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_pairs(item) for item in value]
    return value


def _compact_trial(index: int, trial: dict[str, Any]) -> dict[str, Any]:
    call = trial["task172_call"]
    provider_calls = trial.get("provider_ph_calls", [])
    return {
        "trial_index": index,
        "control_mode": trial["control_mode"],
        "mesh_subdivisions": trial["mesh_subdivisions"],
        "q_w": trial["q_w_repr"],
        "q_binary64_hex": trial["q_w_binary64_hex"],
        "F_native_context_w": trial.get("f_production_decimal_context"),
        "F_exact_binary64_w": trial.get("f_exact_binary64_endpoint"),
        "cell_evaluation_status": trial["cell_evaluation_status"],
        "support_projection": trial.get("support_projection"),
        "task172_result_type": call.get("result_type"),
        "task172_status": call.get("status", "BLOCKED"),
        "task172_request_hash": call["request_hash"],
        "task172_result_hash": call.get("result_hash", call.get("blocked_result_hash")),
        "task172_request_hash_replay": call["request_hash_replay"],
        "task172_result_hash_replay": call.get(
            "result_hash_replay", call.get("blocked_result_hash_replay_passed")
        ),
        "task172_failure_code": call.get("failure_code"),
        "task172_signed_q_hot_to_cold_w": trial.get("task172_signed_q_hot_to_cold_w"),
        "provider_ph_inputs": [
            {
                "role": role,
                "decimal_enthalpy_before_float": item["enthalpy_decimal_before_float"],
                "provider_enthalpy_float_hex": item["provider_enthalpy_float_hex"],
                "provider_snapshot_hash": item["state_after_provider"]["property_snapshot_hash"],
            }
            for role, item in zip(
                (
                    "tube_downstream",
                    "shell_next_physical",
                    "tube_midpoint",
                    "shell_midpoint",
                ),
                provider_calls,
                strict=False,
            )
        ],
    }


def _validate_raw_capture() -> dict[str, Any]:
    raw_bytes = RAW_EVIDENCE_PATH.read_bytes()
    evidence = json.loads(raw_bytes)
    recorded_hash = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != recorded_hash:
        raise RuntimeError("raw R2 evidence canonical hash mismatch")
    if (
        evidence.get("execution_start_head") != EXPECTED["start_head"]
        or evidence.get("runtime_source_head") != EXPECTED["runtime_head"]
        or evidence.get("runtime_source_tree") != EXPECTED["runtime_tree"]
    ):
        raise RuntimeError("raw R2 evidence runtime identity mismatch")
    capture = evidence["diagnostic_execution"]
    if (
        capture.get("n32_boundary_outcome") != "BLOCKED"
        or capture.get("task172_local_evaluation_count_from_stats") != EXPECTED["task172_calls"]
        or capture.get("task172_validator_call_count") != EXPECTED["task172_calls"]
        or capture.get("task172_numerical_hole_count_from_stats") != EXPECTED["task172_holes"]
        or capture.get("failure", {}).get("code")
        != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        or capture.get("failure", {}).get("support_id") != EXPECTED["support_id"]
        or capture.get("failure", {}).get("mesh_subdivisions") != 32
        or capture.get("frozen_failure_diagnostics_match") is not True
    ):
        raise RuntimeError("captured n32 failure did not match the frozen target")

    runner = runpy.run_path(str(RUNNER_PATH))
    replay = runner["_check_capture_replay"](capture)
    trials = capture.get("target_cell_trials", [])
    if len(trials) != 749:
        raise RuntimeError(f"unexpected target-cell trial count: {len(trials)}")
    endpoint_map = {trial["q_w_repr"]: trial for trial in trials}
    left = endpoint_map.get(EXPECTED["left_q"])
    right = endpoint_map.get(EXPECTED["right_q"])
    if left is None or right is None:
        raise RuntimeError("frozen binary64 endpoints missing from target-cell trials")
    if not math.nextafter(float(EXPECTED["left_q"]), math.inf) == float(EXPECTED["right_q"]):
        raise RuntimeError("frozen q endpoints are not adjacent binary64 values")

    checkpoint_hash, checkpoint_size = _sha256_file(RAW_CHECKPOINT_PATH)
    trace_hash, trace_size = _sha256_file(RAW_TRACE_PATH)
    raw_checkpoint_sha = checkpoint_hash
    raw_checkpoint_bytes = checkpoint_size
    raw_trace_sha = trace_hash
    raw_trace_bytes = trace_size
    trace_count = 0
    with RAW_TRACE_PATH.open(encoding="utf-8") as trace:
        for trace_count, line in enumerate(trace, start=1):
            if json.loads(line).get("sequence") != trace_count:
                raise RuntimeError(f"raw trace sequence mismatch at {trace_count}")
    if not trace_count:
        raise RuntimeError("R2 trace is empty")
    if capture.get("last_successful_checkpoint_call_count") != EXPECTED["task172_calls"]:
        raise RuntimeError("checkpoint Task172 call count differs from execution receipt")
    ledger = [_compact_trial(index, trial) for index, trial in enumerate(trials, start=1)]
    endpoint_roles = ("tube_downstream", "shell_next_physical", "tube_midpoint", "shell_midpoint")
    endpoint_pair_comparison = []
    for role_index, role in enumerate(endpoint_roles):
        left_ph = left["provider_ph_calls"][role_index]
        right_ph = right["provider_ph_calls"][role_index]
        left_state = left_ph["state_after_provider"]
        right_state = right_ph["state_after_provider"]
        endpoint_pair_comparison.append(
            {
                "role": role,
                "provider_enthalpy_float_hex_left": left_ph["provider_enthalpy_float_hex"],
                "provider_enthalpy_float_hex_right": right_ph["provider_enthalpy_float_hex"],
                "provider_input_equal": left_ph["provider_enthalpy_float_hex"]
                == right_ph["provider_enthalpy_float_hex"],
                "provider_output_snapshot_hash_left": left_state["property_snapshot_hash"],
                "provider_output_snapshot_hash_right": right_state["property_snapshot_hash"],
                "provider_output_equal": left_state["property_snapshot_hash"]
                == right_state["property_snapshot_hash"],
            }
        )
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    preflight_raw_sha, _ = _sha256_file(PREFLIGHT_PATH)
    preflight_hash = preflight.pop("canonical_evidence_hash", None)
    if canonical_sha256(preflight) != preflight_hash:
        raise RuntimeError("preflight canonical evidence hash mismatch")
    summary: dict[str, Any] = {
        "schema_version": "task173.candidate-a-decimal-q-r2-execution-summary.v1",
        "task_id": evidence["task_id"],
        "execution_start_head": evidence["execution_start_head"],
        "runtime_source_head": evidence["runtime_source_head"],
        "runtime_source_tree": evidence["runtime_source_tree"],
        "execution_evidence_canonical_hash": recorded_hash,
        "execution_evidence_raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "executed_runner_sha256": capture["runtime_identity"]["diagnostic_runner_sha256"],
        "request_identity": capture["request_identity"],
        "preflight": {
            "preflight_result": preflight["preflight_result"],
            "checks": preflight["checks"],
            "preflight_raw_sha256": preflight_raw_sha,
            "preflight_canonical_hash": preflight_hash,
        },
        "raw_artifacts": {
            "checkpoint_path": str(RAW_CHECKPOINT_PATH.relative_to(ROOT)),
            "checkpoint_sha256": raw_checkpoint_sha,
            "checkpoint_raw_bytes": raw_checkpoint_bytes,
            "trace_path": str(RAW_TRACE_PATH.relative_to(ROOT)),
            "trace_sha256": raw_trace_sha,
            "trace_raw_bytes": raw_trace_bytes,
            "trace_event_count": trace_count,
            "raw_artifacts_included_in_commit": False,
        },
        "execution": {
            "n32_reconstruction_outcome": capture["n32_boundary_outcome"],
            "failure": capture["failure"],
            "frozen_failure_diagnostics_match": capture["frozen_failure_diagnostics_match"],
            "task172_total_calls": capture["task172_validator_call_count"],
            "task172_local_evaluation_count": capture["task172_local_evaluation_count_from_stats"],
            "task172_numerical_hole_count": capture["task172_numerical_hole_count_from_stats"],
            "task172_hole_counts_by_code": capture["task172_hole_counts_by_code"],
            "target_cell_trial_count": len(trials),
            "target_trial_identity_replay_count": replay[
                "target_cell_trial_task172_identity_replay_count"
            ],
            "target_endpoint_identity_replay": replay["endpoint_request_result_identity_replay"],
            "transient_event_modes": [
                event.get("mode") for event in capture.get("transient_events", [])
            ],
            "transient_outer_decision_certificate_hashes": [
                item["certificate_hash"]
                for item in capture.get("transient_outer_decision_certificates", [])
            ],
            "provider_state_ph_call_count_total": capture["provider_state_ph_call_count_total"],
            "provider_state_tp_call_count_total": capture["provider_state_tp_call_count_total"],
            "process_cpu_seconds": capture["process_cpu_seconds"],
            "wall_seconds": capture["wall_seconds"],
            "total_process_cpu_seconds_including_candidate_preparation": capture[
                "total_process_cpu_seconds_including_candidate_preparation"
            ],
            "total_wall_seconds_including_candidate_preparation": capture[
                "total_wall_seconds_including_candidate_preparation"
            ],
            "decimal_q_probe_count": capture.get("decimal_probe_count", 0),
            "decimal_probe_invoked": "decimal_q_probe_in_progress" in capture,
            "exception": capture.get("fatal_exception"),
            "exception_phase": "CAPTURED_ENDPOINT_IDENTITY_REPLAY_BEFORE_DECIMAL_PROVIDER_CALL",
            "production_code_changed": evidence["production_code_changed"],
            "task172_contract_changed": evidence["task172_contract_changed"],
            "r2a_authority_changed": evidence["r2a_authority_changed"],
            "numerical_tolerance_changed": evidence["numerical_tolerance_changed"],
            "public_candidate_full_rating_reexecuted": evidence[
                "public_candidate_full_rating_reexecuted"
            ],
            "public_sizing_reexecuted": evidence["public_sizing_reexecuted"],
            "task175_executed": evidence["task175_executed"],
        },
        "failed_cell": {
            "mesh_subdivisions": capture["failure"]["mesh_subdivisions"],
            "support_id": capture["failure"]["support_id"],
            "outer_iteration": capture["failure"]["outer_iteration"],
            "shooting_enthalpy_j_kg": capture["failure"]["shooting_enthalpy_j_kg"],
            "tube_cell_id": capture["failure"]["tube_cell_id"],
            "shell_cell_id": capture["failure"]["shell_cell_id"],
            "wall_interface_id": capture["failure"]["wall_interface_id"],
            "tube_upstream_state": capture["failure"]["tube_upstream_state"],
            "shell_physical_left_state": capture["failure"]["shell_physical_left_state"],
            "support_projection": left["support_projection"],
            "left_endpoint": left,
            "right_endpoint": right,
            "target_trial_ledger": ledger,
            "target_trial_ledger_canonical_hash": canonical_sha256(ledger),
            "endpoint_provider_coordinate_comparison": endpoint_pair_comparison,
            "offline_native_identity_replay": replay,
        },
        "interpretation": {
            "exact_target_cell_reconstructed": True,
            "exact_target_cell_basis": (
                "frozen n32 count/hole/failure signature plus offline replay of all 749 "
                "captured Task172 request/result identities and both exact endpoint F values"
            ),
            "decimal_probe_count": 0,
            "point_root_recovered": "NOT_TESTED",
            "provider_ph_plateau": "PARTIAL_ENDPOINT_COORDINATE_COLLAPSE_ONLY",
            "task172_discontinuity": "ENDPOINT_OUTPUT_CHANGE_OBSERVED_NOT_CAUSALLY_CLASSIFIED",
            "solver_resumption_supported": False,
        },
    }
    summary["canonical_summary_hash"] = canonical_sha256(summary)
    return summary


def _capture() -> None:
    if SUMMARY_PATH.exists():
        raise RuntimeError("summary already exists; refusing to overwrite evidence")
    summary = _validate_raw_capture()
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("RAW_R2_EXECUTION_AND_ENDPOINT_IDENTITIES=PASS")
    print(f"SUMMARY_PATH={SUMMARY_PATH.relative_to(ROOT)}")
    print(f"SUMMARY_CANONICAL_HASH={summary['canonical_summary_hash']}")


def _replay() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    recorded = summary.pop("canonical_summary_hash", None)
    if canonical_sha256(summary) != recorded:
        raise RuntimeError("compact R2 summary canonical hash replay failed")
    summary["canonical_summary_hash"] = recorded
    failed = summary["failed_cell"]
    if (
        canonical_sha256(failed["target_trial_ledger"])
        != failed["target_trial_ledger_canonical_hash"]
    ):
        raise RuntimeError("target trial ledger hash replay failed")
    left = failed["left_endpoint"]
    right = failed["right_endpoint"]
    failure = summary["execution"]["failure"]
    for state_name in ("tube_upstream_state", "shell_physical_left_state"):
        expected_state = failure[state_name]
        for side, endpoint in (("left", left), ("right", right)):
            endpoint_state = endpoint[state_name]
            if (
                endpoint_state["property_snapshot_hash"] != expected_state["property_snapshot_hash"]
                or canonical_sha256(endpoint_state["property_snapshot"])
                != endpoint_state["property_snapshot_hash"]
            ):
                raise RuntimeError(f"{side} failed-cell upstream state replay failed")
    runner = runpy.run_path(str(RUNNER_PATH))
    rating = runner["rating"]
    for side, endpoint in (("left", left), ("right", right)):
        request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(endpoint["task172_request_projection"]), strict=False
        )
        result = Task172LocalResult.model_validate(
            _restore_pairs(endpoint["task172_result_projection"]), strict=False
        )
        if rating.recompute_task172_request_hash(request) != endpoint["task172_request_hash"]:
            raise RuntimeError(f"{side} endpoint request hash replay failed")
        if rating.recompute_task172_result_hash(result) != endpoint["task172_result_hash"]:
            raise RuntimeError(f"{side} endpoint result hash replay failed")
        q = float(endpoint["q_w_repr"])
        if (
            str(q) != endpoint["q_w_repr"]
            or result.status != "VALIDATED"
            or request.case_id != EXPECTED["candidate_id"]
            or request.case_revision_id != EXPECTED["candidate_id"]
            or request.support.physical_segment_id != EXPECTED["support_id"]
            or result.physical_segment_id != EXPECTED["support_id"]
            or result.physical_support_id != rating.recompute_task172_support_id(request)
        ):
            raise RuntimeError(f"{side} endpoint q/status replay failed")
        if (
            str(rating._d(q) - result.signed_q_hot_to_cold_w)
            != endpoint["f_production_decimal_context"]
        ):
            raise RuntimeError(f"{side} endpoint production F replay failed")
        with localcontext() as context:
            context.prec = 100
            f_exact = Decimal.from_float(q) - result.signed_q_hot_to_cold_w
        if str(f_exact) != endpoint["f_exact_binary64_endpoint"]:
            raise RuntimeError(f"{side} endpoint F replay failed")
        for provider_record in endpoint["provider_ph_calls"]:
            state = provider_record["state_after_provider"]
            if canonical_sha256(state["property_snapshot"]) != state["property_snapshot_hash"]:
                raise RuntimeError(f"{side} endpoint provider identity replay failed")
            provider_float = float(Decimal(provider_record["enthalpy_decimal_before_float"]))
            if (
                provider_float.hex() != provider_record["provider_enthalpy_float_hex"]
                or str(Decimal.from_float(provider_float))
                != provider_record["decimal_from_provider_float"]
                or state["property_snapshot"]["inputs"]["enthalpy_j_kg"] != str(provider_float)
            ):
                raise RuntimeError(f"{side} provider PH input replay failed")
    if not math.nextafter(float(left["q_w_repr"]), math.inf) == float(right["q_w_repr"]):
        raise RuntimeError("endpoint binary64 adjacency replay failed")
    if summary["execution"]["target_trial_identity_replay_count"] != 749:
        raise RuntimeError("captured target trial identity replay count mismatch")
    if summary["execution"]["decimal_q_probe_count"] != 0:
        raise RuntimeError("unexpected Decimal probe count in stop receipt")
    print("R2_COMPACT_SUMMARY_HASH_REPLAY=PASS")
    print("TARGET_TRIAL_LEDGER_HASH_REPLAY=PASS")
    print("FAILED_CELL_UPSTREAM_STATE_REPLAY=PASS")
    print("LEFT_RIGHT_TASK172_REQUEST_RESULT_HASH_REPLAY=PASS")
    print("LEFT_RIGHT_PROVIDER_SNAPSHOT_HASH_REPLAY=PASS")
    print("FROZEN_BINARY64_BRACKET_REPLAY=PASS")
    print("EXACT_TARGET_CELL_RECONSTRUCTED=true")
    print("DECIMAL_Q_PROBE_COUNT=0")
    print("POINT_ROOT_RECOVERED=NOT_TESTED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-local-run-artifacts", action="store_true")
    args = parser.parse_args()
    if args.capture_local_run_artifacts:
        _capture()
    else:
        _replay()


if __name__ == "__main__":
    main()
