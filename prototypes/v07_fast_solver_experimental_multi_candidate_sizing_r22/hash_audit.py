"""Independent hash audits for R22A engineering admission."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.pinned_r21e_full_gate import (
    audit_r21e_full_live_rating_file,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    EXPERIMENTAL_SIZING_RESULT_HASH_DOMAIN,
    R21E_COMPACT_HASH,
    R21E_FULL_GIT_BLOB,
    R21E_FULL_JSON_SHA256,
    R21E_RESULT_HASH,
    R22_RAW_RESULT_REL,
    R22_RAW_RESULT_SHA256,
    R22_SIZING_RESULT_HASH,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import (
    audit_r19_full_live_rating_file,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    R19_FULL_JSON_GIT_BLOB,
    R19_FULL_JSON_SHA256,
    R19_RESULT_HASH,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_lists_to_tuples(value: object) -> object:
    if isinstance(value, list):
        return tuple(_json_lists_to_tuples(item) for item in value)
    if isinstance(value, dict):
        return {key: _json_lists_to_tuples(item) for key, item in value.items()}
    return value


def audit_r22_raw_result(root: Path) -> dict[str, Any]:
    raw_path = root / R22_RAW_RESULT_REL
    if not raw_path.is_file():
        return {"blocked": True, "code": "R22_RAW_RESULT_MISSING", "path": R22_RAW_RESULT_REL}
    raw_sha = file_sha256(raw_path)
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    sizing_body = _json_lists_to_tuples(payload.get("sizing_result"))
    if sizing_body is None:
        return {
            "blocked": True,
            "code": "R22_RAW_MISSING_SIZING_RESULT",
            "raw_file_sha256": raw_sha,
        }
    if not isinstance(sizing_body, dict):
        return {"blocked": True, "code": "R22_RAW_SIZING_RESULT_INVALID"}
    body_for_hash = {
        key: value for key, value in sizing_body.items() if key not in ("result_hash", "result_id")
    }
    body_for_hash["_experimental_sizing_hash_domain"] = EXPERIMENTAL_SIZING_RESULT_HASH_DOMAIN
    replay_hash = canonical_sha256(body_for_hash)
    records = sizing_body.get("candidate_records") or []
    trace = sizing_body.get("ranking_trace") or []
    ledger_ids = tuple(item["candidate_id"] for item in records)
    trace_ids = tuple(item["candidate_id"] for item in trace)
    ledger_hash_binding = all(
        entry["candidate_hash"]
        == next(
            rec["candidate_hash"] for rec in records if rec["candidate_id"] == entry["candidate_id"]
        )
        for entry in trace
    )
    recommended = sizing_body.get("recommended_candidate_id")
    alternatives = tuple(sizing_body.get("alternative_candidate_ids") or ())
    ranked = tuple(entry["candidate_id"] for entry in sorted(trace, key=lambda item: item["rank"]))
    return {
        "blocked": False,
        "raw_file_sha256": raw_sha,
        "raw_file_sha256_parity": raw_sha == R22_RAW_RESULT_SHA256,
        "sizing_result_hash_replay": replay_hash,
        "sizing_result_hash_parity": replay_hash == R22_SIZING_RESULT_HASH,
        "sizing_result_hash_declared": sizing_body.get("result_hash"),
        "declared_result_hash_parity": sizing_body.get("result_hash") == R22_SIZING_RESULT_HASH,
        "recommended_candidate_id": recommended,
        "alternative_candidate_ids": alternatives,
        "candidate_ledger_ids": ledger_ids,
        "ranking_trace_ids": trace_ids,
        "ranking_trace_order": ranked,
        "ledger_trace_binding": ledger_hash_binding and ranked == trace_ids,
        "recommended_in_ledger": recommended in ledger_ids if recommended else False,
        "alternatives_subset_ledger": all(item in ledger_ids for item in alternatives),
    }


def audit_r19_r21e_full_hash_replay(root: Path) -> dict[str, Any]:
    r19 = audit_r19_full_live_rating_file(root)
    r21e = audit_r21e_full_live_rating_file(root)
    return {
        "r19_full_file_sha256": r19["full_file_sha256"],
        "r19_full_file_sha256_parity": r19["full_file_sha256"] == R19_FULL_JSON_SHA256,
        "r19_git_blob": r19["full_git_blob_id"],
        "r19_git_blob_parity": r19["full_git_blob_id"] == R19_FULL_JSON_GIT_BLOB,
        "r19_full_result_hash": r19["full_result_hash"],
        "r19_full_result_hash_parity": r19["full_result_hash"] == R19_RESULT_HASH,
        "r21e_full_file_sha256": r21e["full_file_sha256"],
        "r21e_full_file_sha256_parity": r21e["full_file_sha256"] == R21E_FULL_JSON_SHA256,
        "r21e_git_blob": r21e["full_git_blob_id"],
        "r21e_git_blob_parity": r21e["full_git_blob_id"] == R21E_FULL_GIT_BLOB,
        "r21e_full_result_hash": r21e["full_result_hash"],
        "r21e_full_result_hash_parity": r21e["full_result_hash"] == R21E_RESULT_HASH,
        "r21e_compact_hash_pinned": R21E_COMPACT_HASH,
        "full_compact_identity_gate": (
            r19["full_result_hash"] == R19_RESULT_HASH
            and r21e["full_result_hash"] == R21E_RESULT_HASH
        ),
    }
