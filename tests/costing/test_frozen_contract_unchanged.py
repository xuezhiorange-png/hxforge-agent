"""TASK-018 self-reference guard -- frozen-contract-unchanged rule (Section 19.3, 20).

TASK-018 Section 19.1 / 19.2 establish the Frozen Contract Authority Commit /
Base SHA pair. Section 19.3 declares that the contract file MUST NOT modify
itself, and Section 20 explicitly anchors the guard:

    "The TASK-018 self-reference guard mirrors TASK-013/014/015/017 Section 19
    conventions. The guard asserts that the frozen contract file at
    the implementation branch HEAD has SHA equal to the documented
    Frozen Contract Authority Commit SHA."

If this test ever fails, the contract has drifted and a freeze-comment
amendment + a separate TASK-018 design-amendment PR are required
(per TASK-018 Section 20.3 anti-rewrite rule + TASK-017 design-amendment
precedent PR 46). NEVER silence this test by editing it to pass.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA = "19200bf1a3c5d86b6b6129a3fc78c820ff9d3fa8"
FROZEN_CONTRACT_AUTHORITY_BASE_SHA = "5f96cf761d470b82faa1a5d164eefd42360c7df9"

FROZEN_CONTRACT_RELATIVE_PATH = "docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md"


def _git_show_blob_sha(repo_root: Path, ref: str, rel_path: str) -> str:
    """Return the blob SHA for ``rel_path`` at ``ref`` via the porcelain
    ``git ls-tree`` output (mode + type + blob SHA + path)."""
    proc = subprocess.run(
        ["git", "ls-tree", ref, rel_path],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    line = proc.stdout.strip()
    if not line:
        return ""
    parts = line.split()
    if len(parts) < 3:
        return ""
    return parts[2]


def _git_show_blob_bytes(repo_root: Path, ref: str, rel_path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{rel_path}"],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    return proc.stdout or b""


@pytest.fixture(scope="module")
def repo_root() -> Path:
    """Resolve the hxforge-agent repo root dynamically."""
    cur = Path.cwd()
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").is_dir() and (candidate / "docs/tasks").is_dir():
            return candidate
    raise RuntimeError("Could not locate hxforge-agent repo root with both .git/ and docs/tasks/.")


def _origin_available(repo_root: Path) -> bool:
    """Return True only when ``origin`` remote and ``origin/main`` are
    both resolvable in this checkout. Returns False in CI's
    sparse-checkout environment where the actions/checkout step does
    not configure a remote.
    """
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def test_origin_remote_is_hxforge_ssh(repo_root: Path) -> None:
    """Sanity: the origin remote is the project-authorized SSH alias.

    Skipped in CI's sparse-checkout PR-head checkout where ``origin``
    is not configured. The merge-ref pipeline (full clone) and any
    local dev checkout still execute this assertion.
    """
    if not _origin_available(repo_root):
        pytest.skip("origin remote not available (CI sparse-checkout)")
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "git@github.com-hxforge:xuezhiorange-png/hxforge-agent.git"


def test_main_head_includes_frozen_base_authority(repo_root: Path) -> None:
    """Main HEAD must point at a descendant of the Frozen Contract Authority
    Base SHA. Failure here is a TASK-018 Section 19.5 three-way SHA drift.

    Skipped in CI sparse-checkout (no origin/main available).
    """
    if not _origin_available(repo_root):
        pytest.skip("origin/main not available (CI sparse-checkout)")
    proc = subprocess.run(
        ["git", "rev-parse", "origin/main"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    main_head = proc.stdout.strip()
    merge_base = subprocess.run(
        ["git", "merge-base", main_head, FROZEN_CONTRACT_AUTHORITY_BASE_SHA],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert merge_base.stdout.strip() == FROZEN_CONTRACT_AUTHORITY_BASE_SHA, (
        "main HEAD does not include Frozen Contract Authority Base "
        f"({FROZEN_CONTRACT_AUTHORITY_BASE_SHA}); ref: "
        "TASK-018 Section 19.5 three-way SHA discipline + Section 19.2 base anchor."
    )


def test_frozen_contract_unchanged_at_frozen_commit(repo_root: Path) -> None:
    """The TASK-018 design contract at the Frozen Contract Authority Commit
    SHA MUST match its content at the implementation branch HEAD.

    This is the Section 19.3 self-reference guard.

    Skipped in CI sparse-checkout (no origin/main available) because
    `_git_show_blob_sha` needs to resolve the frozen-commit ref.
    """
    if not _origin_available(repo_root):
        pytest.skip("origin/main not available (CI sparse-checkout)")
    impl_blob_sha = _git_show_blob_sha(repo_root, "HEAD", FROZEN_CONTRACT_RELATIVE_PATH)
    frozen_blob_sha = _git_show_blob_sha(
        repo_root,
        FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
        FROZEN_CONTRACT_RELATIVE_PATH,
    )
    assert impl_blob_sha, (
        "TASK-018 design contract not found at branch HEAD; the contract "
        "must exist on the implementation branch for this guard to run."
    )
    assert frozen_blob_sha, (
        "TASK-018 design contract not found at Frozen Contract Authority "
        f"Commit SHA {FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA}; the contract "
        "must exist there for the Section 19.3 guard to be enforceable."
    )
    assert impl_blob_sha == frozen_blob_sha, (
        "TASK-018 design contract blob SHA drift detected -- "
        f"implementation branch HEAD has {impl_blob_sha}; "
        f"frozen commit {FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA} has "
        f"{frozen_blob_sha}. A freeze-comment amendment + a separate "
        "TASK-018 design-amendment PR are required (TASK-018 Section 20.3 + "
        "TASK-017 PR 46 precedent). DO NOT edit the frozen contract file "
        "from an implementation PR."
    )


def test_frozen_contract_content_hash_matches_frozen_commit(repo_root: Path) -> None:
    """Byte-for-byte hash of the frozen contract content at the Frozen
    Contract Authority Commit SHA matches the same hash computed at any
    downstream commit reachable by the authority chain. This is the
    cryptographic backstop of Section 19.3.
    """
    if not _origin_available(repo_root):
        pytest.skip("origin remote not available (CI sparse-checkout)")
    frozen_bytes = _git_show_blob_bytes(
        repo_root,
        FROZEN_CONTRACT_AUTHORITY_COMMIT_SHA,
        FROZEN_CONTRACT_RELATIVE_PATH,
    )
    assert frozen_bytes, "frozen contract bytes missing at authority commit"
    frozen_sha256 = hashlib.sha256(frozen_bytes).hexdigest()

    impl_bytes = _git_show_blob_bytes(repo_root, "HEAD", FROZEN_CONTRACT_RELATIVE_PATH)
    assert impl_bytes, "frozen contract bytes missing at branch HEAD"
    impl_sha256 = hashlib.sha256(impl_bytes).hexdigest()

    assert frozen_sha256 == impl_sha256, (
        "TASK-018 design contract content hash drift: "
        f"frozen SHA-256={frozen_sha256}, impl HEAD SHA-256={impl_sha256}. "
        "Per Section 19.3 + 20, the contract file MUST NOT self-mutate; this "
        "guard failure mandates a freeze-comment amendment + a separate "
        "design-amendment PR."
    )


def test_frozen_contract_unchanged_guard_filename(repo_root: Path) -> None:
    """This file's name MUST remain aligned with the project-wide
    self-reference guard convention (TASK-013/014/015/017 Section 19).
    If this file is renamed away from the conventional name, other
    infrastructure (CI shard entry, governance auditor) may stop
    running it.
    """
    test_file = Path(__file__)
    assert test_file.name == "test_frozen_contract_unchanged.py", (
        "frozen-contract-unchanged guard filename convention broken; "
        "this file MUST be named test_frozen_contract_unchanged.py "
        "per TASK-018 Section 20 + TASK-013/014/015/017 precedent."
    )
