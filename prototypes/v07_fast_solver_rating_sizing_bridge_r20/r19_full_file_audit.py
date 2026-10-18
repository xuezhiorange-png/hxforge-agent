"""Independent file-level audit of pinned R19 FULL_LIVE_RATING.json."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    LIVE_RATING_RESULT_R19_AUTHORITY_ID,
    live_rating_result_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_pinned_identity import (
    ACCEPTED_MESH_RESULT_HASH,
    HEADROOM_MESH_RESULT_HASH,
    R19_FULL_JSON_GIT_BLOB,
    R19_FULL_JSON_REL,
    R19_FULL_JSON_SHA256,
    R19_RESULT_HASH,
    R19_SOURCE_COMMIT,
    RATING_REQUEST_HASH,
    TASK174_RESULT_HASH,
)


class R19AuditError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha256(root: Path, commit: str, rel_path: str) -> str:
    spec = f"{commit}:{rel_path}"
    proc = subprocess.run(
        ["git", "cat-file", "-p", spec],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise R19AuditError("GIT_CAT_FILE_FAILED", spec, proc.stderr.decode("utf-8", "replace"))
    return hashlib.sha256(proc.stdout).hexdigest()


def git_blob_id(root: Path, commit: str, rel_path: str) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", f"{commit}:{rel_path}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise R19AuditError("GIT_REV_PARSE_FAILED", rel_path)
    return proc.stdout.strip()


def audit_r19_full_live_rating_file(root: Path) -> dict[str, Any]:
    full_path = root / R19_FULL_JSON_REL
    if not full_path.is_file():
        raise R19AuditError("R19_FULL_FILE_MISSING", R19_FULL_JSON_REL)

    on_disk_sha = file_sha256(full_path)
    if on_disk_sha != R19_FULL_JSON_SHA256:
        raise R19AuditError(
            "R19_FULL_FILE_SHA256_MISMATCH",
            f"expected={R19_FULL_JSON_SHA256}",
            f"actual={on_disk_sha}",
        )

    blob_id = git_blob_id(root, R19_SOURCE_COMMIT, R19_FULL_JSON_REL)
    if blob_id != R19_FULL_JSON_GIT_BLOB:
        raise R19AuditError(
            "R19_FULL_GIT_BLOB_ID_MISMATCH",
            f"expected={R19_FULL_JSON_GIT_BLOB}",
            f"actual={blob_id}",
        )

    blob_sha = git_blob_sha256(root, R19_SOURCE_COMMIT, R19_FULL_JSON_REL)
    if blob_sha != R19_FULL_JSON_SHA256:
        raise R19AuditError("R19_GIT_BLOB_CONTENT_SHA_MISMATCH", blob_sha)

    full = ExperimentalCandidateRatingResult.model_validate_json(
        full_path.read_text(encoding="utf-8"),
        strict=True,
    )
    recomputed = live_rating_result_hash(full)
    if recomputed != R19_RESULT_HASH:
        raise R19AuditError(
            "R19_RESULT_HASH_REPLAY_MISMATCH",
            f"expected={R19_RESULT_HASH}",
            f"actual={recomputed}",
        )
    if full.result_hash != R19_RESULT_HASH:
        raise R19AuditError("R19_EMBEDDED_RESULT_HASH_MISMATCH")

    if full.experimental_rating_authority_id != LIVE_RATING_RESULT_R19_AUTHORITY_ID:
        raise R19AuditError("R19_FULL_AUTHORITY_ID_MISMATCH")
    if full.rating_request_hash != RATING_REQUEST_HASH:
        raise R19AuditError("R19_RATING_REQUEST_HASH_MISMATCH")
    if full.accepted_mesh_result_hash != ACCEPTED_MESH_RESULT_HASH:
        raise R19AuditError("R19_ACCEPTED_MESH_HASH_MISMATCH")
    if full.headroom_mesh_result_hash != HEADROOM_MESH_RESULT_HASH:
        raise R19AuditError("R19_HEADROOM_MESH_HASH_MISMATCH")
    if full.task174_result_hash != TASK174_RESULT_HASH:
        raise R19AuditError("R19_TASK174_RESULT_HASH_MISMATCH")

    if full.mesh_sequence_gate != "PASS":
        raise R19AuditError("R19_MESH_SEQUENCE_GATE_NOT_PASS")
    if not full.strict_replay_pass:
        raise R19AuditError("R19_STRICT_REPLAY_NOT_PASS")

    return {
        "r19_source_commit": R19_SOURCE_COMMIT,
        "full_rel_path": R19_FULL_JSON_REL,
        "full_file_sha256": on_disk_sha,
        "full_git_blob_id": blob_id,
        "full_git_blob_content_sha256": blob_sha,
        "full_result_hash": full.result_hash,
        "full_result_hash_recomputed": recomputed,
        "accepted_mesh_result_hash": full.accepted_mesh_result_hash,
        "headroom_mesh_result_hash": full.headroom_mesh_result_hash,
        "task174_result_hash": full.task174_result_hash,
        "experimental_rating_authority_id": full.experimental_rating_authority_id,
        "schema_version": full.schema_version,
    }
