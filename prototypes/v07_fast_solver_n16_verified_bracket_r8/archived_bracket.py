"""Load and verify R7 archived n=16 outer trial bracket (candidate only)."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
R7_TRIALS_JSONL = (
    ROOT
    / "docs/tasks/evidence/V07-FAST-SOLVER-outer-continuation-n16-r7-20261012T155035Z.trials.jsonl"
)
R7_SOURCE_COMMIT = "86cf9583eb3f417d66f3f0c6e7603db2504fa43b"
R7_RESULT_JSON = (
    ROOT / "docs/tasks/evidence/V07-FAST-SOLVER-outer-continuation-n16-r7-20261012T155035Z.json"
)
LOW_TRIAL_INDEX = 21
HIGH_TRIAL_INDEX = 25
CANDIDATE_B_ID = "e152cca9-fd5d-59ca-9b46-1df574eee841"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_trial_by_index(path: Path, trial_index: int) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if int(record["trial_index"]) == trial_index:
            return record
    raise KeyError(f"trial_index {trial_index} not in {path}")


def verify_archived_bracket_inputs(
    *,
    rating_request_hash: str,
) -> dict[str, Any]:
    trials_sha = sha256_file(R7_TRIALS_JSONL)
    result_sha = sha256_file(R7_RESULT_JSON)
    r7_meta = json.loads(R7_RESULT_JSON.read_text(encoding="utf-8"))
    low_rec = load_trial_by_index(R7_TRIALS_JSONL, LOW_TRIAL_INDEX)
    high_rec = load_trial_by_index(R7_TRIALS_JSONL, HIGH_TRIAL_INDEX)
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
        "r7_trials_jsonl_path": str(R7_TRIALS_JSONL.relative_to(ROOT)),
        "r7_trials_jsonl_sha256": trials_sha,
        "r7_result_json_sha256": result_sha,
        "r7_task_id": r7_meta.get("task_id"),
        "candidate_b_id": CANDIDATE_B_ID,
        "rating_request_hash_expected": rating_request_hash,
        "subdivisions": 16,
        "archived_low_trial_index": LOW_TRIAL_INDEX,
        "archived_high_trial_index": HIGH_TRIAL_INDEX,
        "archived_low_shooting_enthalpy_j_kg": low_rec["shooting_enthalpy_j_kg"],
        "archived_high_shooting_enthalpy_j_kg": high_rec["shooting_enthalpy_j_kg"],
        "archived_high_terminal_residual_k": high_rec.get("terminal_residual_k"),
        "archived_low_record": low_rec,
        "archived_high_record": high_rec,
    }
