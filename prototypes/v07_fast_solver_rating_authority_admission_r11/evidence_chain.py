"""Verify frozen R8/R9/R10 mesh evidence for Candidate B rating admission."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.file_integrity import verify_pinned_file
from prototypes.v07_fast_solver_evidence_gate.prior_mesh_evidence import (
    verify_and_load_r8_n16_result_body,
    verify_and_load_r9_n32_result_body,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    R10_RESULT_JSON_GIT_BLOB,
    R10_RESULT_JSON_REL,
    R10_RESULT_SHA256,
    R10_TASK_ID,
    RATING_REQUEST_HASH,
)

ROOT = Path(__file__).resolve().parents[2]


def verify_and_load_r10_headroom_evidence() -> dict[str, Any]:
    path = ROOT / R10_RESULT_JSON_REL
    meta = verify_pinned_file(
        path,
        expected_sha256=R10_RESULT_SHA256,
        expected_git_blob=R10_RESULT_JSON_GIT_BLOB,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("task_id") != R10_TASK_ID:
        raise ValueError("R10 task_id mismatch")
    if data.get("result") != "N64_OUTER_BOUNDARY_TERMINAL_ACCEPTED":
        raise ValueError("R10 headroom not terminal accepted")
    if data.get("experimental_mesh_sequence_gate") != "PASS":
        raise ValueError("R10 mesh sequence gate not PASS")
    n64 = data.get("n64_run", {}).get("result", {})
    if n64.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise ValueError("R10 n64 outer status mismatch")
    return {
        "file_sha256": meta["sha256"],
        "file_git_blob": meta["git_blob"],
        "payload": data,
        "n64_result_body": n64,
        "n32_n64_comparison": data.get("n32_n64_mesh_comparison", {}),
    }


def verify_candidate_b_evidence_chain() -> dict[str, Any]:
    r8_n16 = verify_and_load_r8_n16_result_body()
    r9_n32 = verify_and_load_r9_n32_result_body()
    r10 = verify_and_load_r10_headroom_evidence()
    r9_data = json.loads((ROOT / r9_n32["evidence_path"]).read_text(encoding="utf-8"))
    if not r9_data.get("two_consecutive_pairs_pass"):
        raise ValueError("R9 two_consecutive_pairs_pass false")
    if r9_data.get("mesh_candidate_n") != 32:
        raise ValueError("R9 mesh_candidate_n not 32")
    n16_n32 = r9_data.get("n16_n32_mesh_comparison", {})
    if n16_n32.get("overall_status") != "PASS":
        raise ValueError("R9 n16_n32 overall not PASS")
    if r9_n32["result_body"].get("rating_request_hash") != RATING_REQUEST_HASH:
        raise ValueError("R9 rating hash mismatch")
    if r8_n16["result_body"].get("rating_request_hash") != RATING_REQUEST_HASH:
        raise ValueError("R8 rating hash mismatch")
    if r10["n64_result_body"].get("rating_request_hash") != RATING_REQUEST_HASH:
        raise ValueError("R10 rating hash mismatch")
    return {
        "rating_request_hash": RATING_REQUEST_HASH,
        "r8_n16_body": r8_n16["result_body"],
        "r9_n32_body": r9_n32["result_body"],
        "r10_n64_body": r10["n64_result_body"],
        "n16_n32_comparison": n16_n32,
        "n32_n64_comparison": r10["n32_n64_comparison"],
        "evidence_chain_hashes": (
            ("r8_result_path", r8_n16["evidence_path"]),
            ("r9_result_path", r9_n32["evidence_path"]),
            ("r10_result_path", R10_RESULT_JSON_REL),
            ("r10_file_sha256", r10["file_sha256"]),
        ),
    }
