"""R7 archived n=16 bracket gate with pinned trusted identities."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.file_integrity import verify_pinned_file
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    CANDIDATE_B_ID,
    R7_ARCHIVED_MESH_N,
    R7_HIGH_TRIAL_INDEX,
    R7_LOW_TRIAL_INDEX,
    R7_RESULT_JSON_GIT_BLOB,
    R7_RESULT_JSON_REL,
    R7_RESULT_JSON_SHA256,
    R7_SOURCE_COMMIT,
    R7_TASK_ID,
    R7_TRIALS_JSONL_GIT_BLOB,
    R7_TRIALS_JSONL_REL,
    R7_TRIALS_JSONL_SHA256,
    RATING_REQUEST_HASH,
)

ROOT = Path(__file__).resolve().parents[2]


def load_trial_by_index(path: Path, trial_index: int) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if int(record["trial_index"]) == trial_index:
            return record
    raise KeyError(f"trial_index {trial_index} not in {path}")


def verify_r7_archived_bracket(*, rating_request_hash: str) -> dict[str, Any]:
    if rating_request_hash != RATING_REQUEST_HASH:
        raise ValueError("rating_request_hash mismatch vs pinned trusted value")
    trials_path = ROOT / R7_TRIALS_JSONL_REL
    result_path = ROOT / R7_RESULT_JSON_REL
    trials_meta = verify_pinned_file(
        trials_path,
        expected_sha256=R7_TRIALS_JSONL_SHA256,
        expected_git_blob=R7_TRIALS_JSONL_GIT_BLOB,
    )
    result_meta = verify_pinned_file(
        result_path,
        expected_sha256=R7_RESULT_JSON_SHA256,
        expected_git_blob=R7_RESULT_JSON_GIT_BLOB,
    )
    r7_meta = json.loads(result_path.read_text(encoding="utf-8"))
    if r7_meta.get("task_id") != R7_TASK_ID:
        raise ValueError("R7 result task_id mismatch")
    low_rec = load_trial_by_index(trials_path, R7_LOW_TRIAL_INDEX)
    high_rec = load_trial_by_index(trials_path, R7_HIGH_TRIAL_INDEX)
    if int(low_rec.get("subdivisions", R7_ARCHIVED_MESH_N)) != R7_ARCHIVED_MESH_N:
        raise ValueError("archived low trial mesh n mismatch")
    if int(high_rec.get("subdivisions", R7_ARCHIVED_MESH_N)) != R7_ARCHIVED_MESH_N:
        raise ValueError("archived high trial mesh n mismatch")
    if low_rec["classification"] != "LOW_SIDE_DOMAIN_INFEASIBLE":
        raise ValueError("archived low trial classification mismatch")
    if high_rec["classification"] != "VALID_TRAJECTORY":
        raise ValueError("archived high trial classification mismatch")
    h_low = Decimal(low_rec["shooting_enthalpy_j_kg"])
    h_high = Decimal(high_rec["shooting_enthalpy_j_kg"])
    if h_low >= h_high:
        raise ValueError("archived bracket ordering invalid")
    return {
        "r7_source_commit": R7_SOURCE_COMMIT,
        "r7_trials_jsonl_path": R7_TRIALS_JSONL_REL,
        "r7_trials_jsonl_sha256": trials_meta["sha256"],
        "r7_trials_jsonl_git_blob": trials_meta["git_blob"],
        "r7_result_json_sha256": result_meta["sha256"],
        "r7_result_json_git_blob": result_meta["git_blob"],
        "r7_task_id": R7_TASK_ID,
        "candidate_b_id": CANDIDATE_B_ID,
        "rating_request_hash_expected": RATING_REQUEST_HASH,
        "subdivisions": R7_ARCHIVED_MESH_N,
        "archived_low_trial_index": R7_LOW_TRIAL_INDEX,
        "archived_high_trial_index": R7_HIGH_TRIAL_INDEX,
        "archived_low_shooting_enthalpy_j_kg": low_rec["shooting_enthalpy_j_kg"],
        "archived_high_shooting_enthalpy_j_kg": high_rec["shooting_enthalpy_j_kg"],
        "archived_high_terminal_residual_k": high_rec.get("terminal_residual_k"),
        "archived_low_record": low_rec,
        "archived_high_record": high_rec,
        "trusted_gate": "R7_ARCHIVED_BRACKET_PINNED",
    }
