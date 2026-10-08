#!/usr/bin/env python3
"""Independently replay R3 snapshot and bounded-probe evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
STEM = "TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1"
RUNNER_PATH = Path(__file__).with_name(f"{STEM}.py")
EVIDENCE_PATH = Path(__file__).with_name(f"{STEM}.json")
PREFLIGHT_PATH = Path(__file__).with_name(f"{STEM}-preflight-r3.json")
REPLAY_RECEIPT_PATH = Path(__file__).with_name(f"{STEM}-replay-r2.json")
R1_HELPER_PATH = Path(__file__).with_name(
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r1.py"
)
R2_REPLAY_PATH = Path(__file__).with_name(
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-replay.py"
)
COMPLETION_REQUEST_REPLAY_PATH = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)


def _sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("r3_snapshot_decimal_probe_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R3 probe runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _file_receipt(path: Path) -> dict[str, Any]:
    digest, size = _sha256(path)
    return {"path": str(path.relative_to(ROOT)), "raw_bytes": size, "sha256": digest}


def _build_replay_receipt() -> dict[str, Any]:
    runner = _load_runner()
    runner.replay_final_evidence()
    r1 = runner._load_module("r1_runtime_binding_for_r3_replay", R1_HELPER_PATH)
    runtime_binding = r1._assert_runtime_binding(execution=False)
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    probes = evidence["execution"]["probes"]
    distinct_request_hashes = sorted({item["task172_request_hash"] for item in probes})
    distinct_result_hashes = sorted({item["task172_result_hash"] for item in probes})
    saved_right = evidence["preflight"]["rehydration_basis"]["right_endpoint"]
    first_probe = probes[0]
    request_projection_equal = (
        saved_right["task172_request_projection"] == first_probe["task172_request_projection"]
    )
    request_hash_equal = saved_right["task172_request_hash"] == first_probe["task172_request_hash"]
    historical_result_equal = (
        saved_right["task172_result_hash"] == first_probe["task172_result_hash"]
        and saved_right["task172_result_projection"] == first_probe["task172_result_projection"]
    )
    result_projection_diff_fields = sorted(
        key
        for key in set(saved_right["task172_result_projection"])
        | set(first_probe["task172_result_projection"])
        if saved_right["task172_result_projection"].get(key)
        != first_probe["task172_result_projection"].get(key)
    )
    within_probe_identity_stable = (
        len(distinct_request_hashes) == 1
        and len(distinct_result_hashes) == 1
        and len({json.dumps(item["task172_request_projection"], sort_keys=True) for item in probes})
        == 1
        and len({json.dumps(item["task172_result_projection"], sort_keys=True) for item in probes})
        == 1
    )
    if not request_projection_equal or not request_hash_equal:
        raise RuntimeError("R3 first probe does not exactly replay the saved RIGHT request")
    provider_signature_equal = [
        item["provider_enthalpy_float_hex"] for item in saved_right["provider_ph_calls"]
    ] == [item["provider_enthalpy_float_hex"] for item in first_probe["provider_ph_inputs_outputs"]]
    if not within_probe_identity_stable:
        raise RuntimeError("identical probe requests produced different R3 result preimages")
    if not historical_result_equal and result_projection_diff_fields != [
        "result_hash",
        "result_id",
        "shell_htc_w_m2_k",
        "shell_j_mu",
        "tube_htc_w_m2_k",
    ]:
        raise RuntimeError(
            "R2-to-R3 same-request result preimage differs in an unexpected field set: "
            f"{result_projection_diff_fields!r}"
        )
    evidence_hash, evidence_size = _sha256(EVIDENCE_PATH)
    if evidence["execution"]["task172_validation_count"] > runner.MAX_NEW_TASK172_VALIDATIONS:
        raise RuntimeError("R3 replay found validation count above the authorized cap")
    if evidence["execution"]["budget_units_used"] > runner.MAX_NEW_TASK172_VALIDATIONS:
        raise RuntimeError("R3 replay found identity-inclusive budget above the authorized cap")
    result = {
        "schema_version": "task173.r2-snapshot-decimal-q-probe-replay.v1",
        "task_id": runner.TASK_ID,
        "start_head": runner.START_HEAD,
        "replay_head": runner._git("rev-parse", "HEAD"),
        "runtime_source_head": runner.RUNTIME_HEAD,
        "runtime_source_tree": runner.RUNTIME_TREE,
        "runtime_source_binding": runtime_binding,
        "runner_sha256_at_replay": _file_receipt(RUNNER_PATH)["sha256"],
        "r1_probe_helper": _file_receipt(R1_HELPER_PATH),
        "r2_replay_script": _file_receipt(R2_REPLAY_PATH),
        "completion_request_replay_script": _file_receipt(COMPLETION_REQUEST_REPLAY_PATH),
        "r3_preflight": _file_receipt(PREFLIGHT_PATH),
        "r3_execution_evidence": {
            "path": str(EVIDENCE_PATH.relative_to(ROOT)),
            "raw_bytes": evidence_size,
            "sha256": evidence_hash,
            "canonical_hash": evidence["canonical_evidence_hash"],
        },
        "r2_raw_artifacts": evidence["preflight"]["raw_artifacts"],
        "completion_request_hash": evidence["preflight"]["completion_request_hash"],
        "candidate_rating_request_hash": evidence["preflight"]["candidate_rating_request_hash"],
        "task168_candidate_space_hash": evidence["preflight"]["task168_candidate_space_hash"],
        "original_endpoint_request_result_hashes": [
            {
                "side": item["label"],
                "request_hash": item["task172_request_hash"],
                "result_hash": item["task172_result_hash"],
                "F_native_decimal_context_w": item["F_native_decimal_context_w"],
            }
            for item in evidence["preflight"]["rehydration_basis"]["endpoint_identity_replay"]
        ],
        "same_request_r2_right_vs_r3_probe": {
            "saved_right_request_hash": saved_right["task172_request_hash"],
            "r3_probe_request_hash": first_probe["task172_request_hash"],
            "request_projection_exact_equal": request_projection_equal,
            "request_hash_equal": request_hash_equal,
            "saved_right_result_hash": saved_right["task172_result_hash"],
            "r3_probe_result_hash": first_probe["task172_result_hash"],
            "result_preimage_equal": historical_result_equal,
            "result_projection_diff_fields": result_projection_diff_fields,
            "classification": (
                "SAME_REQUEST_DIFFERENT_RESULT_IDENTITY_ACROSS_R2_R3"
                if not historical_result_equal
                else "SAME_REQUEST_RESULT_IDENTITY_REPLAYED_ACROSS_R2_R3"
            ),
            "provider_ph_input_signature_equal": provider_signature_equal,
        },
        "execution_summary": {
            "full_n32_reconstruction_executed": evidence["full_n32_reconstruction_executed"],
            "public_full_rating_reexecuted": evidence["public_full_rating_reexecuted"],
            "public_sizing_reexecuted": evidence["public_sizing_reexecuted"],
            "task172_validation_count": evidence["execution"]["task172_validation_count"],
            "validation_budget_cap": runner.MAX_NEW_TASK172_VALIDATIONS,
            "budget_units_including_two_saved_endpoint_identity_replays": evidence["execution"][
                "budget_units_used"
            ],
            "decimal_q_probe_count": evidence["execution"]["decimal_q_probe_count"],
            "validated_probe_count": evidence["execution"]["validated_decimal_q_probe_count"],
            "min_abs_f_w": evidence["execution"]["min_abs_f_w"],
            "point_root_recovered": evidence["execution"]["point_root_recovered"],
            "provider_ph_signature_count": evidence["execution"]["provider_ph_signature_count"],
            "provider_plateau_classification": evidence["execution"][
                "provider_plateau_classification"
            ],
            "task172_result_discontinuity_classification": evidence["execution"][
                "task172_result_discontinuity_classification"
            ],
            "distinct_probe_request_hash_count": len(distinct_request_hashes),
            "distinct_probe_result_hash_count": len(distinct_result_hashes),
            "distinct_probe_request_hashes": distinct_request_hashes,
            "distinct_probe_result_hashes": distinct_result_hashes,
            "within_probe_same_request_result_identity_replay": (
                "PASS" if within_probe_identity_stable else "FAIL"
            ),
            "cross_run_deterministic_result_identity": (
                "PASS" if historical_result_equal else "FAIL"
            ),
            "root_repeat_validation": evidence["execution"]["deterministic_root_replay"],
        },
        "checks": {
            "r2_snapshot_rehydration": "PASS",
            "completion_request_replay": "PASS",
            "original_endpoint_identity_replay": "PASS",
            "provider_snapshot_hash_replay": "PASS",
            "probe_request_result_hash_replay": "PASS",
            "validation_budget": "PASS",
            "runtime_source_binding": "PASS",
            "production_code_changed": "false",
            "task172_contract_changed": "false",
            "r2a_authority_changed": "false",
            "numerical_tolerance_changed": "false",
            "candidate_space_changed": "false",
            "frozen_completion_request_changed": "false",
        },
        "result": evidence["result"],
    }
    result["canonical_replay_receipt_hash"] = canonical_sha256(result)
    return result


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite replay receipt: {path}")
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    actual = _build_replay_receipt()
    if args.write_receipt:
        _write_once(REPLAY_RECEIPT_PATH, actual)
        receipt_hash = actual["canonical_replay_receipt_hash"]
    else:
        expected = json.loads(REPLAY_RECEIPT_PATH.read_text(encoding="utf-8"))
        recorded_hash = expected.pop("canonical_replay_receipt_hash", None)
        if canonical_sha256(expected) != recorded_hash:
            raise RuntimeError("committed R3 replay receipt canonical hash mismatch")
        recorded_head = expected["replay_head"]
        verified_head = actual["replay_head"]
        if recorded_head != actual["start_head"]:
            raise RuntimeError("replay receipt is not anchored to the R3 execution HEAD")
        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", recorded_head, verified_head],
            cwd=ROOT,
            check=False,
        )
        if ancestry.returncode:
            raise RuntimeError(
                "current replay HEAD is not a descendant of the recorded replay HEAD"
            )
        recorded_binding = expected["runtime_source_binding"]
        verified_binding = actual["runtime_source_binding"]
        if (
            verified_binding["runtime_source_head"] != recorded_binding["runtime_source_head"]
            or verified_binding["runtime_source_tree"] != recorded_binding["runtime_source_tree"]
            or not verified_binding["runtime_paths_byte_identical"]
            or not verified_binding["bound_runtime_worktree_clean"]
        ):
            raise RuntimeError("evidence descendant runtime binding differs from replay receipt")
        comparable = dict(actual)
        comparable["replay_head"] = recorded_head
        comparable_binding = dict(verified_binding)
        comparable_binding["current_head"] = recorded_binding["current_head"]
        comparable_binding["current_tree"] = recorded_binding["current_tree"]
        comparable["runtime_source_binding"] = comparable_binding
        comparable.pop("canonical_replay_receipt_hash", None)
        if comparable != expected or canonical_sha256(comparable) != recorded_hash:
            raise RuntimeError("R3 replay receipt differs from regenerated replay")
        receipt_hash = recorded_hash
    print("R2_SNAPSHOT_REHYDRATION=PASS")
    print("R3_EVIDENCE_REPLAY=PASS")
    print("ALL_COMPLETION_AND_PROBE_IDENTITIES_REPLAY=PASS")
    print("R3_EVIDENCE_DESCENDANT_RUNTIME_BINDING=PASS")
    print(f"REPLAY_VERIFIED_HEAD={actual['replay_head']}")
    print(f"DECIMAL_Q_PROBE_COUNT={actual['execution_summary']['decimal_q_probe_count']}")
    print(f"NEW_TASK172_VALIDATION_COUNT={actual['execution_summary']['task172_validation_count']}")
    print(f"MIN_ABS_F_W={actual['execution_summary']['min_abs_f_w']}")
    print(
        f"POINT_ROOT_RECOVERED={str(actual['execution_summary']['point_root_recovered']).lower()}"
    )
    print(
        "WITHIN_R3_DETERMINISTIC_REQUEST_RESULT_REPLAY="
        f"{actual['execution_summary']['within_probe_same_request_result_identity_replay']}"
    )
    print(
        "R2_TO_R3_SAME_REQUEST_RESULT_IDENTITY="
        f"{actual['same_request_r2_right_vs_r3_probe']['classification']}"
    )
    print(f"REPLAY_RECEIPT={REPLAY_RECEIPT_PATH.relative_to(ROOT)}")
    print(f"REPLAY_RECEIPT_HASH={receipt_hash}")


if __name__ == "__main__":
    main()
