"""Spawn-safe immutable CandidateRatingRequest snapshot (no Q13 in worker)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_success_result_hash as task029_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029SuccessResult,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.native_codec import (
    candidate_request_from_projection,
    native_projection,
)

SNAPSHOT_SCHEMA = "task173.experimental-live-rating-request-snapshot.v1"
NUMERICAL_AUTHORITY_ID = "V07-FAST-SOLVER-RATING-AUTHORITY-ADMISSION-R11"
PROPERTY_PROVIDER_ID = "CoolPropProvider"


def _execution_environment_id() -> str:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = head.stdout.strip() if head.returncode == 0 else "unknown"
    return f"cursor-cloud:{commit}"


def upstream_binding_hashes(request: CandidateRatingRequest) -> dict[str, str]:
    if type(request.task029_result) is not Task029SuccessResult:
        raise TypeError("task029_result must be Task029SuccessResult")
    return {
        "task025_result_hash": request.task025_result.result_hash,
        "task029_result_hash": task029_result_hash(request.task029_result),
        "task166_result_hash": request.task166_result.result_hash,
        "task171_result_hash": request.task171_result.result_hash,
        "task174_result_hash": request.task174_result.result_hash,
    }


def build_request_snapshot_body(
    request: CandidateRatingRequest, *, source_commit: str
) -> dict[str, Any]:
    rating_hash = candidate_rating_request_hash(request)
    bindings = upstream_binding_hashes(request)
    return {
        "schema_version": SNAPSHOT_SCHEMA,
        "candidate_id": request.candidate_id,
        "candidate_hash": request.candidate_hash,
        "rating_request_hash": rating_hash,
        "upstream_binding_hashes": bindings,
        "numerical_authority": {
            "authority_id": NUMERICAL_AUTHORITY_ID,
            "property_provider_id": PROPERTY_PROVIDER_ID,
            "status": "CANDIDATE",
        },
        "rating_request_projection": native_projection(request),
        "source_commit": source_commit,
        "execution_environment_id": _execution_environment_id(),
    }


def snapshot_content_digest(body_without_digest: dict[str, Any]) -> str:
    encoded = json.dumps(
        body_without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_request_snapshot(
    request: CandidateRatingRequest, *, source_commit: str
) -> dict[str, Any]:
    body = build_request_snapshot_body(request, source_commit=source_commit)
    digest = snapshot_content_digest(body)
    body["snapshot_sha256"] = digest
    recomputed = snapshot_content_digest({k: v for k, v in body.items() if k != "snapshot_sha256"})
    if recomputed != digest:
        raise RuntimeError("snapshot digest mismatch")
    return body


def write_request_snapshot(path: Path, snapshot: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_snapshot_integrity(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA:
        raise ValueError("invalid snapshot schema_version")
    digest = snapshot.get("snapshot_sha256")
    if not digest:
        raise ValueError("missing snapshot_sha256")
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if snapshot_content_digest(body) != digest:
        raise ValueError("snapshot_sha256 mismatch (tampered content)")


def restore_request_from_snapshot(snapshot: dict[str, Any]) -> CandidateRatingRequest:
    verify_snapshot_integrity(snapshot)
    projection = snapshot["rating_request_projection"]
    request = candidate_request_from_projection(projection)
    if request.candidate_id != snapshot["candidate_id"]:
        raise ValueError("candidate_id mismatch vs snapshot")
    if request.candidate_hash != snapshot["candidate_hash"]:
        raise ValueError("candidate_hash mismatch vs snapshot")
    rating_hash = candidate_rating_request_hash(request)
    if rating_hash != snapshot["rating_request_hash"]:
        raise ValueError("rating_request_hash mismatch vs snapshot")
    bindings = upstream_binding_hashes(request)
    expected = snapshot["upstream_binding_hashes"]
    for key, value in expected.items():
        if bindings.get(key) != value:
            raise ValueError(f"upstream binding mismatch: {key}")
    return request


def load_request_from_snapshot_file(path: Path) -> CandidateRatingRequest:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return restore_request_from_snapshot(snapshot)
