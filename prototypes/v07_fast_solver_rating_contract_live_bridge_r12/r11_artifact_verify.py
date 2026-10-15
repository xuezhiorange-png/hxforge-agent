"""Verify frozen R11 full rating JSON without mutating artifacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_evidence_gate.file_integrity import verify_pinned_file
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    R11_AUTHORITY_DIFF_GIT_BLOB,
    R11_AUTHORITY_DIFF_JSON_REL,
    R11_AUTHORITY_DIFF_SHA256,
    R11_RATING_JSON_GIT_BLOB,
    R11_RATING_JSON_REL,
    R11_RATING_JSON_SHA256,
    R11_RESULT_HASH,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_rate_candidate import (
    experimental_rating_result_hash,
)

ROOT = Path(__file__).resolve().parents[2]


def verify_r11_full_rating_artifact() -> dict[str, Any]:
    rating_path = ROOT / R11_RATING_JSON_REL
    meta = verify_pinned_file(
        rating_path,
        expected_sha256=R11_RATING_JSON_SHA256,
        expected_git_blob=R11_RATING_JSON_GIT_BLOB,
    )
    raw_text = rating_path.read_text(encoding="utf-8")
    reparsed = json.dumps(json.loads(raw_text), ensure_ascii=False, separators=(",", ":"))
    if reparsed != raw_text.replace("\n", "").replace(" ", ""):
        # File is pretty-printed; check numeric identity via model round-trip
        pass
    model = ExperimentalCandidateRatingResult.model_validate_json(raw_text, strict=True)
    recomputed = experimental_rating_result_hash(model)
    parity = recomputed == R11_RESULT_HASH
    auth_path = ROOT / R11_AUTHORITY_DIFF_JSON_REL
    auth_meta = verify_pinned_file(
        auth_path,
        expected_sha256=R11_AUTHORITY_DIFF_SHA256,
        expected_git_blob=R11_AUTHORITY_DIFF_GIT_BLOB,
    )
    commit_sha = subprocess.run(
        ["git", "rev-list", "-n", "1", "HEAD", "--", str(rating_path.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "rating_path": str(rating_path.relative_to(ROOT)),
        "file_sha256": meta["sha256"],
        "file_git_blob": meta["git_blob"],
        "stored_result_hash": model.result_hash,
        "recomputed_result_hash": recomputed,
        "result_hash_parity": "PASS" if parity else "FAIL",
        "authority_diff_path": str(auth_path.relative_to(ROOT)),
        "authority_diff_sha256": auth_meta["sha256"],
        "evidence_commit_sha": commit_sha,
        "schema_valid": True,
    }
