"""Worktree file integrity vs pinned SHA256 and git blob ids."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_hash_object(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def verify_pinned_file(
    path: Path,
    *,
    expected_sha256: str,
    expected_git_blob: str,
) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha256:
        raise ValueError(f"{path}: sha256 mismatch expected={expected_sha256} actual={actual_sha}")
    actual_blob = git_hash_object(path)
    if actual_blob != expected_git_blob:
        raise ValueError(
            f"{path}: git blob mismatch expected={expected_git_blob} actual={actual_blob}"
        )
    return {"sha256": actual_sha, "git_blob": actual_blob}
