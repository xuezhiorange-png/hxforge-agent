"""Replay the complete frozen H2 numerical-hole trace for R2A."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256

HERE = Path(__file__).resolve().parent
EVIDENCE_PATH = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-h2-hole.json"
)
QUALIFICATION_PATH = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
)
QUALIFICATION_RUNNER = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-qualification.py"
)
LEGACY_REPLAY = (
    HERE / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2-h2-hole-replay.py"
)
EXPECTED = {
    "hole_request_hash": "6f4d89289c045d822285aa9b46d1ae07bff8c524d51b73ac4efe0177847982d1",
    "hole_result_hash": "56a9eb129c971e9c7dfed9766494d934069a471f2beca8210eac54c69d97c4eb",
    "left_q": "8600.866943237208",
    "left_f": "-0.000090940275",
    "left_result_hash": "722284bf5379d897de288a2e8aa46798871a0b2f76e58a1d531b83e5aedda92d",
    "right_q": "8600.867200622995",
    "right_f": "0.000177409965",
    "right_result_hash": "18c2ab5de834d8bcb5c5a160cef0f8d2a24e5c4d2184521367a1630e1620817d",
}


def _without_hash(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "evidence_hash"}


def main() -> None:
    qrunner = runpy.run_path(str(QUALIFICATION_RUNNER), run_name="task173_r2a_h2_replay_runtime")
    qrunner["_check_committed_runtime"]()
    document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    payload = _without_hash(document)
    if canonical_sha256(payload) != document["evidence_hash"]:
        raise AssertionError("R2A_H2_EVIDENCE_HASH_MISMATCH")
    qualification_document = json.loads(QUALIFICATION_PATH.read_text(encoding="utf-8"))
    qualification = qualification_document["qualification"]
    matrix_hash = canonical_sha256(
        {key: value for key, value in qualification.items() if key != "qualification_matrix_hash"}
    )
    if (
        matrix_hash != qualification["qualification_matrix_hash"]
        or matrix_hash != payload["parent_qualification_matrix_hash"]
        or qualification_document["qualification_result"]
        != "PASS_TASK173_PROVIDER_QUANTIZATION_TRANSIENT_DECISION_ENCLOSURE_R2A_AUTHORITY_CANDIDATE"
    ):
        raise AssertionError("R2A_PARENT_QUALIFICATION_MATRIX_BINDING_MISMATCH")

    h2_rows = [case for case in qualification["cases"] if case["label"] == "H2"]
    if len(h2_rows) != 1:
        raise AssertionError("R2A_H2_CASE_NOT_UNIQUE")
    case = h2_rows[0]
    if (case["cut"], case["candidate_id"], case["candidate_hash"]) != (
        "0.275",
        "aa70248a-9f76-542d-bc77-1e935b9c32d4",
        "a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5",
    ):
        raise AssertionError("R2A_H2_CANDIDATE_IDENTITY_MISMATCH")
    if (
        payload["case"]["task171_result_hash"] != case["native_identities"]["TASK171"]
        or payload["case"]["task174_result_hash"] != case["native_identities"]["TASK174"]
        or payload["case"]["candidate_space_hash"] != case["candidate_space_hash"]
        or payload["case"]["candidate_hash"] != case["candidate_hash"]
    ):
        raise AssertionError("R2A_H2_CANDIDATE_NATIVE_BINDING_MISMATCH")

    outer = payload["outer_trial"]
    trials = [
        trial
        for trial in case["outer_search"]["trials"]
        if trial["iteration"] == outer["iteration"]
    ]
    if len(trials) != 1:
        raise AssertionError("R2A_H2_HOLE_OUTER_TRIAL_NOT_UNIQUE")
    trial = trials[0]
    branch = trial["left_branch"]
    if (
        outer["iteration"] != 11
        or outer["shooting_enthalpy_j_kg"] != "107469.424689940170810546875"
        or outer["shooting_enthalpy_j_kg"] != trial["enthalpy_j_kg"]
        or outer["classification"] != branch["classification"]
        or outer["continuation_hash"] != branch["continuation_hash"]
        or outer["mesh_result_hash"] != branch["mesh_result_hash"]
        or trial["enclosure_used"]
        or not branch["observables"]["task172_numerical_hole_neighborhoods"]
        or branch["observables"]["task172_numerical_hole_neighborhoods"][0]
        != payload["hole_neighborhood"]
    ):
        raise AssertionError("R2A_H2_OUTER_TRIAL_CROSS_BINDING_MISMATCH")

    legacy_replay = runpy.run_path(str(LEGACY_REPLAY), run_name="task173_r2_h2_replay_library")
    evaluations = payload["task172_evaluations"]
    if [row["role"] for row in evaluations] != [
        "LEFT_VALID_NEIGHBOR",
        "HOLE_BLOCKED",
        "RIGHT_VALID_NEIGHBOR",
    ]:
        raise AssertionError("R2A_H2_EVALUATION_ORDER_MISMATCH")
    replayed = [legacy_replay["_replay_evaluation"](row) for row in evaluations]
    native_requests = [
        legacy_replay["CandidateTask172LocalRequest"].model_validate(
            legacy_replay["_restore"](row["request_projection"]), strict=False
        )
        for row in evaluations
    ]
    by_role = {row["role"]: row for row in replayed}
    task171_case_hash = payload["case"]["task171_result_hash"]
    task166_case_hash = case["native_identities"]["TASK166"]
    checks = {
        "hole_request_hash": by_role["HOLE_BLOCKED"]["request_hash"]
        == EXPECTED["hole_request_hash"],
        "hole_result_hash": by_role["HOLE_BLOCKED"]["blocked_result_hash"]
        == EXPECTED["hole_result_hash"],
        "left_q": evaluations[0]["q_trial_w"] == EXPECTED["left_q"],
        "left_residual": evaluations[0]["f_q_w"] == EXPECTED["left_f"],
        "left_result_hash": by_role["LEFT_VALID_NEIGHBOR"]["result_hash"]
        == EXPECTED["left_result_hash"],
        "right_q": evaluations[2]["q_trial_w"] == EXPECTED["right_q"],
        "right_residual": evaluations[2]["f_q_w"] == EXPECTED["right_f"],
        "right_result_hash": by_role["RIGHT_VALID_NEIGHBOR"]["result_hash"]
        == EXPECTED["right_result_hash"],
        "task171_cross_binding": all(
            request.candidate_binding.task171_result.result_hash == task171_case_hash
            for request in native_requests
        ),
        "task166_cross_binding": all(
            request.candidate_binding.task166_result.result_hash == task166_case_hash
            for request in native_requests
        ),
        "hole_not_promoted": by_role["HOLE_BLOCKED"]["failure_code"]
        == "BLOCKED_RESIDUAL_ACCEPTANCE",
    }
    if not all(checks.values()):
        raise AssertionError(f"R2A_H2_FROZEN_IDENTITY_MISMATCH:{checks}")
    print(f"H2_HOLE_EVIDENCE_HASH={document['evidence_hash']}")
    print(f"PARENT_QUALIFICATION_MATRIX_HASH={matrix_hash}")
    print(f"H2_HOLE_ENDPOINT_IDENTITY_REPLAY_COUNT={len(replayed)}")
    print("H2_BLOCKED_REQUEST_RESULT_REPLAY=PASS")
    print("H2_LEFT_RIGHT_VALID_NEIGHBOR_REPLAY=PASS")
    print("H2_OUTER_TRIAL_CROSS_BINDING=PASS")
    print("ALL_H2_HOLE_REPLAY_PASS=true")


if __name__ == "__main__":
    main()
