"""Frozen behavior environment contract for TASK-015A.

This module defines the single canonical fingerprint authority for the behavior
environment.  It establishes a封闭允许列表 of environment variables that
affect test collection/import behavior, and a governed-prefix fail-closed
mechanism for detecting unknown behavior-affecting variables.

P0-1: PYTEST_TIMEOUT is now explicitly in the allowlist because it is injected
by the CI workflow and affects execution authority.

Governed namespace:
  Variables whose name starts with one of the governed prefixes MUST be
  declared in BEHAVIOR_ENV_ALLOWLIST.  An undeclared governed variable
  raises BehaviorEnvironmentError — fail-closed.

Non-governed variables (standard GitHub runner env vars) are not checked.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Final

# ── Governed namespace prefixes ─────────────────────────────────────────────
GOVERNED_PREFIXES: Final[tuple[str, ...]] = ("HX_", "HEXAGENT_", "COOLPROP_", "PYTEST_")

# ── Behavior-affecting environment variables (allowlist) ────────────────────
BEHAVIOR_ENV_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "PYTHONHASHSEED",
        "TZ",
        "LC_ALL",
        "LANG",
        "PYTEST_ADDOPTS",
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
        "PYTEST_TIMEOUT",
        "HX_TRACK",
        "HX_COMMIT_SHA",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
    }
)

# ── Behavior-affecting file inputs ──────────────────────────────────────────
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
    """Fail-closed check for unknown governed-namespace variables."""
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

    Returns dict with 'payload', 'canonical_json', 'fingerprint'.
    """
    root = repo_root or Path.cwd()
    allowed = BEHAVIOR_ENV_ALLOWLIST | (extra_allowed_vars or frozenset())

    check_governed_unknowns(extra_allowed_vars=extra_allowed_vars)

    env_snapshot: dict[str, str] = {}
    for key in sorted(allowed):
        value = os.environ.get(key, "")
        if value:
            env_snapshot[key] = value

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    file_digests: dict[str, str] = {}
    for filename in sorted(BEHAVIOR_FILE_INPUTS):
        filepath = root / filename
        file_digests[filename] = sha256_file(filepath)

    working_dir = str(Path.cwd().resolve())

    payload: dict[str, Any] = {
        "python_version": python_version,
        "environment": env_snapshot,
        "file_digests": file_digests,
        "working_directory": working_dir,
    }

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
    """Build and save the auditable behavior-environment.json artifact."""
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
    """Verify that all fingerprints are identical."""
    unique = set(fingerprints)
    if len(unique) != 1:
        raise BehaviorEnvironmentError(
            f"behavior fingerprint inconsistency in {context}: "
            f"found {len(unique)} distinct values: {sorted(unique)}"
        )


def canonicalize_payload(payload: dict[str, Any]) -> str:
    """Return the canonical JSON string for a payload (no plugin info)."""
    # Strip plugin_versions if present (standalone re-canonicalization)
    stripped = {k: v for k, v in payload.items() if k != "plugin_versions"}
    return json.dumps(stripped, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
