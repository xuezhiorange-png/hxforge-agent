"""Verify producer origin metadata against approved production contracts."""

# ruff: noqa: E501

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    APPROVED_PROVIDER,
)


def current_repo_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def verify_producer_origin_record(
    origin: dict[str, Any] | None,
    *,
    root: Path,
    expected_provider_version: str = APPROVED_PROVIDER["provider_version"],
) -> tuple[bool, str]:
    if origin is None:
        return False, "R2A_PRODUCER_ORIGIN_MISSING"
    if origin.get("producer_authority_id") != R2A_AUTHORITY_ID:
        return False, "R2A_PRODUCER_AUTHORITY_MISMATCH"
    if origin.get("provider_version") != expected_provider_version:
        return False, "R2A_PROVIDER_VERSION_MISMATCH"
    if origin.get("provider") != APPROVED_PROVIDER["provider"]:
        return False, "R2A_PROVIDER_IDENTITY_MISMATCH"
    git_head = origin.get("git_commit_head")
    if not isinstance(git_head, str) or len(git_head) != 40:
        return False, "R2A_PRODUCER_GIT_HEAD_INVALID"
    if origin.get("verify_git_head_matches_runtime") is True and git_head != current_repo_head(
        root
    ):
        return False, "R2A_PRODUCER_GIT_HEAD_RUNTIME_MISMATCH"
    return True, "PASS"


def build_runtime_producer_origin(root: Path) -> dict[str, Any]:
    return {
        "producer_authority_id": R2A_AUTHORITY_ID,
        "provider": APPROVED_PROVIDER["provider"],
        "provider_version": APPROVED_PROVIDER["provider_version"],
        "provider_git_revision": APPROVED_PROVIDER["provider_git_revision"],
        "git_commit_head": current_repo_head(root),
        "verify_git_head_matches_runtime": False,
        "evidence_class": "CAPTURED_TASK173_PRECISION_FLOOR_REPLAY",
    }
