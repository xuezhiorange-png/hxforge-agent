"""Frozen behavior environment contract for TASK-015A.

This module defines the封闭允许列表 of environment variables that affect
test collection/import behavior.  Global and shard fingerprints must be
consistent.  Unknown behavior-affecting variables MUST NOT be silently ignored.

The canonical JSON payload is what gets SHA-256 hashed for the fingerprint.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Final

# ── Behavior-affecting environment variables (allowlist) ────────────────────
# Only these variables may influence collection/import behavior.
# Any variable NOT in this set that is added to the environment will cause
# the fingerprint to differ and verification to fail.
BEHAVIOR_ENV_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "PYTHONHASHSEED",
        "TZ",
        "LC_ALL",
        "LANG",
        "PYTEST_ADDOPTS",
        "HX_TRACK",
        "HX_COMMIT_SHA",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
    }
)

# ── Behavior-affecting file inputs ──────────────────────────────────────────
# Files whose content affects collection/import behavior.
BEHAVIOR_FILE_INPUTS: Final[frozenset[str]] = frozenset(
    {
        "uv.lock",
        "pyproject.toml",
    }
)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 digest of a file."""
    if not path.is_file():
        raise ValueError(f"required behavior environment input missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def build_behavior_fingerprint(
    *,
    repo_root: Path | None = None,
    extra_allowed_vars: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Build the canonical behavior environment fingerprint payload.

    The payload includes all allowed env vars, file digests, and version info.
    The SHA-256 of the canonical JSON serialization is the fingerprint.

    Parameters
    ----------
    repo_root : Path, optional
        Repository root directory.  Defaults to cwd.
    extra_allowed_vars : frozenset[str], optional
        Additional variables to allow (e.g. for nightly-specific config).

    Returns
    -------
    dict with 'payload' (canonical JSON) and 'fingerprint' (SHA-256 hex).

    Raises
    ------
    ValueError
        If required files are missing or unknown behavior-affecting variables
        are present in the environment.
    """
    root = repo_root or Path.cwd()
    allowed = BEHAVIOR_ENV_ALLOWLIST | (extra_allowed_vars or frozenset())

    env_snapshot: dict[str, str] = {}
    for key in sorted(allowed):
        value = os.environ.get(key, "")
        if value:
            env_snapshot[key] = value

    # Python version info
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    # File digests
    file_digests: dict[str, str] = {}
    for filename in sorted(BEHAVIOR_FILE_INPUTS):
        filepath = root / filename
        file_digests[filename] = sha256_file(filepath)

    # Working directory
    working_dir = str(Path.cwd().resolve())

    payload: dict[str, Any] = {
        "python_version": python_version,
        "environment": env_snapshot,
        "file_digests": file_digests,
        "working_directory": working_dir,
    }

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "payload": payload,
        "canonical_json": canonical,
        "fingerprint": fingerprint,
    }


def verify_fingerprint_consistency(
    fingerprints: list[str],
    context: str,
) -> None:
    """Verify that all fingerprints are identical.

    Raises ValueError if fingerprints differ.
    """
    unique = set(fingerprints)
    if len(unique) != 1:
        raise ValueError(
            f"behavior fingerprint inconsistency in {context}: "
            f"found {len(unique)} distinct values: {sorted(unique)}"
        )
