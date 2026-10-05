"""Replay the complete native Task172 identities for the frozen H2 hole trial."""

from __future__ import annotations

import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172BlockedResult,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)

HERE = Path(__file__).resolve().parent
RUNTIME_HEAD = "b1b9d676c693e09d740c47b642198b5e4f543409"
RUNTIME_TREE = "b0cfbdb7c4a9c3136fda317723fb5eab30c40e1e"
EVIDENCE_PATH = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole.json"
)
QUALIFICATION_PATH = HERE / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2.json"
)
H2_CANDIDATE_ID = "aa70248a-9f76-542d-bc77-1e935b9c32d4"
H2_CANDIDATE_HASH = "a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5"


def _without_hash(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "evidence_hash"}


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


def _replay_evaluation(row: dict[str, Any]) -> dict[str, Any]:
    request = CandidateTask172LocalRequest.model_validate(
        _restore(row["request_projection"]), strict=False
    )
    request_hash = task172.recompute_task172_request_hash(request)
    if request_hash != row["request_hash"]:
        raise AssertionError(f"REQUEST_HASH_MISMATCH:{row['role']}")
    binding = request.candidate_binding
    support_identity = task172.recompute_task172_support_id(request)
    if (
        binding.candidate_id != H2_CANDIDATE_ID
        or binding.candidate_hash != H2_CANDIDATE_HASH
        or binding.authority_package_id != "V07-T173-SIZING-AUTHORITY-PACKAGE-R2"
        or binding.authority_package_hash
        != "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
        or support_identity != row["task172_support_identity"]
        or request.support.physical_segment_id != row["physical_segment_id"]
    ):
        raise AssertionError(f"REQUEST_BINDING_MISMATCH:{row['role']}")

    if row["result_type"] == "Task172LocalResult":
        result = Task172LocalResult.model_validate(row["result_projection"], strict=False)
        result_hash = task172.recompute_task172_result_hash(result)
        if (
            row["result_status"] != "VALID"
            or result_hash != row["result_hash"]
            or result.result_hash != row["result_hash"]
            or result.request_hash != request_hash
            or result.physical_support_id != support_identity
            or result.case_id != H2_CANDIDATE_ID
            or result.case_revision_id != H2_CANDIDATE_ID
            or result.task171_result_hash != binding.task171_result.result_hash
        ):
            raise AssertionError(f"VALID_RESULT_IDENTITY_MISMATCH:{row['role']}")
        if row["role"] not in {"LEFT_VALID_NEIGHBOR", "RIGHT_VALID_NEIGHBOR"}:
            raise AssertionError(f"UNEXPECTED_VALID_ROLE:{row['role']}")
        q = Decimal(row["q_trial_w"])
        residual = q - result.signed_q_hot_to_cold_w
        if residual != Decimal(row["f_q_w"]):
            raise AssertionError(f"NEIGHBOR_RESIDUAL_MISMATCH:{row['role']}")
        return {
            "role": row["role"],
            "request_hash": request_hash,
            "result_hash": result_hash,
            "physical_segment_id": row["physical_segment_id"],
            "task172_support_identity": support_identity,
            "candidate_id": binding.candidate_id,
            "candidate_hash": binding.candidate_hash,
            "residual_w": str(residual),
        }

    if row["result_type"] != "Task172BlockedResult":
        raise AssertionError(f"UNEXPECTED_RESULT_TYPE:{row['role']}:{row['result_type']}")
    blocked = Task172BlockedResult.model_validate(row["result_projection"], strict=False)
    blocked_hash = task172.recompute_task172_blocked_result_hash(blocked)
    if (
        row["role"] != "HOLE_BLOCKED"
        or row["result_status"] != "BLOCKED"
        or blocked.failure_code != "BLOCKED_RESIDUAL_ACCEPTANCE"
        or blocked_hash != row["result_hash"]
        or blocked.blocked_result_hash != row["result_hash"]
        or blocked.request_hash != request_hash
    ):
        raise AssertionError("BLOCKED_HOLE_IDENTITY_MISMATCH")
    return {
        "role": row["role"],
        "request_hash": request_hash,
        "blocked_result_hash": blocked_hash,
        "failure_code": blocked.failure_code,
        "physical_segment_id": row["physical_segment_id"],
        "task172_support_identity": support_identity,
        "candidate_id": binding.candidate_id,
        "candidate_hash": binding.candidate_hash,
        "blocked_result_never_promoted": True,
    }


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
    if (head, tree) != (RUNTIME_HEAD, RUNTIME_TREE):
        raise AssertionError(f"RUNTIME_BASELINE_MISMATCH:{head}:{tree}")

    document = json.loads(EVIDENCE_PATH.read_text())
    payload = _without_hash(document)
    if canonical_sha256(payload) != document["evidence_hash"]:
        raise AssertionError("H2_HOLE_EVIDENCE_HASH_MISMATCH")
    parent = json.loads(QUALIFICATION_PATH.read_text())
    if (
        hashlib.sha256(QUALIFICATION_PATH.read_bytes()).hexdigest()
        != payload["parent_qualification_sha256"]
    ):
        raise AssertionError("PARENT_QUALIFICATION_RAW_SHA_MISMATCH")
    qualification = parent["qualification"]
    matrix_hash = canonical_sha256(
        {key: value for key, value in qualification.items() if key != "qualification_matrix_hash"}
    )
    if matrix_hash != qualification["qualification_matrix_hash"]:
        raise AssertionError("PARENT_QUALIFICATION_MATRIX_HASH_MISMATCH")
    if qualification["qualification_matrix_hash"] != payload["parent_qualification_matrix_hash"]:
        raise AssertionError("PARENT_QUALIFICATION_MATRIX_BINDING_MISMATCH")
    cases = [case for case in qualification["cases"] if case["label"] == "H2"]
    if len(cases) != 1:
        raise AssertionError("PARENT_H2_CASE_NOT_UNIQUE")
    case = cases[0]
    if (
        case["candidate_id"] != H2_CANDIDATE_ID
        or case["candidate_hash"] != H2_CANDIDATE_HASH
        or case["cut"] != "0.275"
        or case["candidate_hash_replay"] != H2_CANDIDATE_HASH
    ):
        raise AssertionError("PARENT_H2_IDENTITY_MISMATCH")
    trials = [
        trial
        for trial in case["outer_search"]["trials"]
        if trial["iteration"] == payload["outer_trial"]["iteration"]
    ]
    if len(trials) != 1:
        raise AssertionError("PARENT_H2_OUTER_TRIAL_NOT_UNIQUE")
    trial = trials[0]
    branch = trial["left_branch"]
    for key in ("shooting_enthalpy_j_kg",):
        if payload["outer_trial"][key] != trial["enthalpy_j_kg"]:
            raise AssertionError(f"OUTER_TRIAL_BINDING_MISMATCH:{key}")
    if (
        trial["enclosure_used"]
        or branch["classification"] != payload["outer_trial"]["classification"]
        or branch["continuation_hash"] != payload["outer_trial"]["continuation_hash"]
        or branch["mesh_result_hash"] != payload["outer_trial"]["mesh_result_hash"]
        or branch["observables"]["task172_numerical_hole_neighborhoods"][0]
        != payload["hole_neighborhood"]
    ):
        raise AssertionError("OUTER_TRIAL_OR_HOLE_NEIGHBORHOOD_MISMATCH")

    evaluations = payload["task172_evaluations"]
    expected_roles = ["LEFT_VALID_NEIGHBOR", "HOLE_BLOCKED", "RIGHT_VALID_NEIGHBOR"]
    if [row["role"] for row in evaluations] != expected_roles:
        raise AssertionError("H2_HOLE_EVALUATION_ROLE_ORDER_MISMATCH")
    replayed = [_replay_evaluation(row) for row in evaluations]
    blocked_row = next(row for row in replayed if row["role"] == "HOLE_BLOCKED")
    receipt = payload["blocked_cell_trial_receipt"]
    if (
        receipt["task172_request_hash"] != blocked_row["request_hash"]
        or receipt["blocked_result_hash"] != blocked_row["blocked_result_hash"]
        or receipt["failure_code"] != blocked_row["failure_code"]
        or receipt["physical_segment_id"] != blocked_row["physical_segment_id"]
        or receipt["task172_support_identity"] != blocked_row["task172_support_identity"]
        or receipt["blocked_request_hash_replay_passed"] is not True
        or receipt["blocked_result_hash_replay_passed"] is not True
        or receipt["exact_blocked_result_type"] is not True
    ):
        raise AssertionError("BLOCKED_RECEIPT_CROSS_BINDING_MISMATCH")
    if payload["production_code_changed"] or payload["task172_acceptance_changed"]:
        raise AssertionError("PRODUCTION_OR_ACCEPTANCE_SCOPE_CHANGED")

    print(f"H2_HOLE_EVIDENCE_HASH={document['evidence_hash']}")
    print(f"PARENT_QUALIFICATION_MATRIX_HASH={qualification['qualification_matrix_hash']}")
    print(f"H2_HOLE_ENDPOINT_IDENTITY_REPLAY_COUNT={len(replayed)}")
    print("H2_BLOCKED_REQUEST_RESULT_REPLAY=PASS")
    print("H2_LEFT_RIGHT_VALID_NEIGHBOR_REPLAY=PASS")
    print("H2_OUTER_TRIAL_CROSS_BINDING=PASS")
    print("ALL_H2_HOLE_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
