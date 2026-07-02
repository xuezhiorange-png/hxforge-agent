"""Frozen behavior environment contract for TASK-015A.

This module defines the single canonical fingerprint authority for the behavior
environment.  It establishes a封闭允许列表 of environment variables that
affect test collection/import behavior, and a governed-prefix fail-closed
mechanism for detecting unknown behavior-affecting variables.

Global and shard fingerprints MUST be consistent.  The canonical JSON payload
is what gets SHA-256 hashed for the fingerprint.

Governed namespace:
  Variables whose name starts with one of the governed prefixes MUST be
  declared in BEHAVIOR_ENV_ALLOWLIST.  An undeclared governed variable
  raises BehaviorEnvironmentError — fail-closed.

Non-governed variables (standard GitHub runner env vars) are not checked.

The auditable payload (behavior-environment.json) must be saved as an
artifact so that fingerprints can be verified post-hoc.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Final

# ── Governed namespace prefixes ─────────────────────────────────────────────
# Variables whose name starts with these prefixes are under HX governance.
# If a governed variable is present in the environment but NOT in the allowlist,
# the fingerprint computation MUST fail closed.
GOVERNED_PREFIXES: Final[tuple[str, ...]] = ("HX_", "HEXAGENT_", "COOLPROP_", "PYTEST_")

# ── Behavior-affecting environment variables (allowlist) ────────────────────
# Only these variables may influence collection/import behavior.
# Governed-namespace variables not in this set cause fail-closed rejection.
# Non-governed (standard runner) variables are silently ignored.
BEHAVIOR_ENV_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "PYTHONHASHSEED",
        "TZ",
        "LC_ALL",
        "LANG",
        "PYTEST_ADDOPTS",
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
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


class BehaviorEnvironmentError(Exception):
    """Raised when the behavior environment contract is violated."""


def sha256_file(path: Path) -> str:
    """Compute SHA-256 digest of a file."""
    if not path.is_file():
        raise BehaviorEnvironmentError(f"required behavior environment input missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def check_governed_unknowns(*, extra_allowed_vars: frozenset[str] | None = None) -> None:
    """Fail-closed check for unknown governed-namespace variables.

    Inspects os.environ for variables starting with GOVERNED_PREFIXES.
    Any governed variable not in BEHAVIOR_ENV_ALLOWLIST (or extra_allowed_vars)
    triggers a BehaviorEnvironmentError.

    Standard runner variables (without governed prefixes) are not checked.
    """
    allowed = BEHAVIOR_ENV_ALLOWLIST | (extra_allowed_vars or frozenset())
    unknown: set[str] = set()
    for key in os.environ:
        if key.startswith(GOVERNED_PREFIXES) and key not in allowed:
            unknown.add(key)
    if unknown:
        raise BehaviorEnvironmentError(
            f"undeclared governed variables found in environment: "
            f"{sorted(unknown)!r}.  Add to BEHAVIOR_ENV_ALLOWLIST or remove."
        )


def build_behavior_fingerprint(
    *,
    repo_root: Path | None = None,
    extra_allowed_vars: frozenset[str] | None = None,
    config: Any = None,
) -> dict[str, Any]:
    """Build the canonical behavior environment fingerprint payload.

    The payload includes all allowed env vars, file digests, Python/pytest
    version info, and plugin versions (when config is provided).
    The SHA-256 of the canonical JSON serialization is the fingerprint.

    Parameters
    ----------
    repo_root : Path, optional
        Repository root directory.  Defaults to cwd.
    extra_allowed_vars : frozenset[str], optional
        Additional variables to allow (e.g. for nightly-specific config).
    config : pytest.Config, optional
        When provided, pytest/plugin versions are included in the payload.
        When None, those fields are omitted (for standalone use).

    Returns
    -------
    dict with keys:
      'payload'           – the canonical dict
      'canonical_json'    – canonical JSON string
      'fingerprint'       – SHA-256 hex digest

    Raises
    ------
    BehaviorEnvironmentError
        If required files are missing or unknown governed variables are present.
    """
    root = repo_root or Path.cwd()
    allowed = BEHAVIOR_ENV_ALLOWLIST | (extra_allowed_vars or frozenset())

    # Check for unknown governed variables BEFORE building payload
    check_governed_unknowns(extra_allowed_vars=extra_allowed_vars)

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

    # Optionally include pytest/plugin versions when config is available
    if config is not None:
        import pytest as _pytest

        payload["pytest_version"] = _pytest.__version__
        plugin_versions: dict[str, str] = {}
        for _plugin, distribution in config.pluginmanager.list_plugin_distinfo():
            name = getattr(distribution, "project_name", None)
            version = getattr(distribution, "version", None)
            if isinstance(name, str) and isinstance(version, str):
                previous = plugin_versions.setdefault(name, version)
                if previous != version:
                    raise BehaviorEnvironmentError(
                        f"conflicting versions for pytest plugin {name!r}: "
                        f"{previous!r} vs {version!r}"
                    )
        payload["plugin_versions"] = dict(sorted(plugin_versions.items()))

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "payload": payload,
        "canonical_json": canonical,
        "fingerprint": fingerprint,
    }


def save_behavior_environment(
    *,
    output_path: Path,
    repo_root: Path | None = None,
    extra_allowed_vars: frozenset[str] | None = None,
    config: Any = None,
) -> dict[str, Any]:
    """Build and save the auditable behavior-environment.json artifact.

    Returns the full artifact dict (schema_version + payload + fingerprint).
    """
    result = build_behavior_fingerprint(
        repo_root=repo_root,
        extra_allowed_vars=extra_allowed_vars,
        config=config,
    )
    artifact: dict[str, Any] = {
        "schema_version": "1",
        "payload": result["payload"],
        "canonical_json_sha256": f"sha256:{result['fingerprint']}",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact


def verify_fingerprint_consistency(
    fingerprints: list[str],
    context: str,
) -> None:
    """Verify that all fingerprints are identical.

    Raises BehaviorEnvironmentError if fingerprints differ.
    """
    unique = set(fingerprints)
    if len(unique) != 1:
        raise BehaviorEnvironmentError(
            f"behavior fingerprint inconsistency in {context}: "
            f"found {len(unique)} distinct values: {sorted(unique)}"
        )
