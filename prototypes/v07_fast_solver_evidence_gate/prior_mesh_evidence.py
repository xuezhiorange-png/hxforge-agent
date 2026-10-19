"""Load and gate R6 n=8 and R8 n=16 terminal evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.file_integrity import verify_pinned_file
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    R6_RESULT_JSON_GIT_BLOB,
    R6_RESULT_JSON_REL,
    R6_RESULT_JSON_SHA256,
    R6_SOURCE_COMMIT,
    R6_TASK_ID,
    R8_RESULT_COMMIT,
    R8_RESULT_JSON_GIT_BLOB,
    R8_RESULT_JSON_REL,
    R8_RESULT_SHA256,
    R8_TASK_ID,
    R9_RESULT_COMMIT,
    R9_RESULT_JSON_GIT_BLOB,
    R9_RESULT_JSON_REL,
    R9_RESULT_SHA256,
    R9_TASK_ID,
    RATING_REQUEST_HASH,
)

ROOT = Path(__file__).resolve().parents[2]


def verify_and_load_r6_n8_result_body() -> dict[str, Any]:
    path = ROOT / R6_RESULT_JSON_REL
    verify_pinned_file(
        path,
        expected_sha256=R6_RESULT_JSON_SHA256,
        expected_git_blob=R6_RESULT_JSON_GIT_BLOB,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("task_id") != R6_TASK_ID:
        raise ValueError("R6 task_id mismatch")
    body = data.get("n8_run", {}).get("result", {})
    if body.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise ValueError("R6 n8 not terminal accepted")
    if body.get("rating_request_hash") != RATING_REQUEST_HASH:
        raise ValueError("R6 rating_request_hash mismatch")
    return {
        "source_commit": R6_SOURCE_COMMIT,
        "evidence_path": R6_RESULT_JSON_REL,
        "result_body": body,
    }


def verify_and_load_r8_n16_result_body() -> dict[str, Any]:
    path = ROOT / R8_RESULT_JSON_REL
    verify_pinned_file(
        path,
        expected_sha256=R8_RESULT_SHA256,
        expected_git_blob=R8_RESULT_JSON_GIT_BLOB,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("task_id") != R8_TASK_ID:
        raise ValueError("R8 task_id mismatch")
    if data.get("result") != "N16_OUTER_BOUNDARY_TERMINAL_ACCEPTED":
        raise ValueError("R8 result not terminal accepted")
    body = data.get("n16_run", {}).get("result", {})
    if body.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise ValueError("R8 n16 outer status mismatch")
    if body.get("rating_request_hash") != RATING_REQUEST_HASH:
        raise ValueError("R8 rating_request_hash mismatch")
    return {
        "source_commit": R8_RESULT_COMMIT,
        "evidence_path": R8_RESULT_JSON_REL,
        "result_body": body,
    }


def verify_and_load_r9_n32_result_body() -> dict[str, Any]:
    path = ROOT / R9_RESULT_JSON_REL
    verify_pinned_file(
        path,
        expected_sha256=R9_RESULT_SHA256,
        expected_git_blob=R9_RESULT_JSON_GIT_BLOB,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("task_id") != R9_TASK_ID:
        raise ValueError("R9 task_id mismatch")
    if data.get("result") != "N32_OUTER_BOUNDARY_TERMINAL_ACCEPTED":
        raise ValueError("R9 result not terminal accepted")
    body = data.get("n32_run", {}).get("result", {})
    if body.get("outer_boundary_status") != "TERMINAL_ACCEPTED":
        raise ValueError("R9 n32 outer status mismatch")
    if body.get("rating_request_hash") != RATING_REQUEST_HASH:
        raise ValueError("R9 rating_request_hash mismatch")
    return {
        "source_commit": R9_RESULT_COMMIT,
        "evidence_path": R9_RESULT_JSON_REL,
        "result_body": body,
    }
