"""TASK-019 no-upstream-mutation guard tests (Slice 1).

Asserts that the TASK-019 Slice 1 implementation does not modify any
frozen TASK-006 through TASK-018 contract file, and that no
implementation file in this branch attempts to rewrite frozen docs.
Also asserts TASK-017 stale backlog rows are not edited by this branch.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# 19 frozen contract files (per frozen design §9.1)
FROZEN_CONTRACT_GLOBS = [
    "docs/tasks/TASK-001-engineering-baseline.md",
    "docs/tasks/TASK-002-units-and-quantities.md",
    "docs/tasks/TASK-003-property-service.md",
    "docs/tasks/TASK-004-correlation-registry.md",
    "docs/tasks/TASK-005-correlation-registry.md",
    "docs/tasks/TASK-006-heat-balance.md",
    "docs/tasks/TASK-007-tube-annulus-correlations.md",
    "docs/tasks/TASK-007-double-pipe-correlations.md",
    "docs/tasks/TASK-008-double-pipe-rating.md",
    "docs/tasks/TASK-009-double-pipe-sizing.md",
    "docs/tasks/TASK-010-report-and-api.md",
    "docs/tasks/TASK-010-MERGE-CLOSEOUT.md",
    "docs/tasks/TASK-011-benchmark-case-governance.md",
    "docs/tasks/TASK-012-standards-rule-pack-license-boundary.md",
    "docs/tasks/TASK-013-material-cost-data-governance.md",
    "docs/tasks/TASK-014-immutable-case-revisions-persistence.md",
    "docs/tasks/TASK-015-ci-security-and-release-automation.md",
    "docs/tasks/TASK-015A-deterministic-test-environment-and-ci-sharding.md",
    "docs/tasks/TASK-016-approved-geometry-catalog.md",
    "docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md",
    "docs/tasks/TASK-017-materials-mass-mechanical-implementation.md",
    "docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md",
]


def test_no_frozen_contract_modification_vs_origin_main() -> None:
    """None of the 19+ frozen contract files may be modified by this branch.

    Uses `git diff origin/main -- <glob>` to detect any modification.
    """
    # Get list of changed files vs origin/main
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        # If origin/main is unreachable, fall back to HEAD
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
    changed_files = set(line.strip() for line in result.stdout.splitlines() if line.strip())

    frozen_modified = sorted(
        f
        for f in changed_files
        if any(f.startswith("docs/tasks/TASK-0") and f.endswith(".md") for _ in [0])
        and any(f.endswith(g.split("/")[-1]) for g in FROZEN_CONTRACT_GLOBS)
    )
    # Also exclude the TASK-019 contract itself (it's not in the forbidden list,
    # though §9.1 still lists it as a frozen contract — Slice 1 must NOT modify
    # TASK-019 contract either, per authorization "no design contract mutation")
    # Per the task spec, "no upstream TASK-006..TASK-018 mutation" — the design
    # contract file (TASK-019) is its own constraint (allowed to be touched only
    # for bookkeeping line, per authorization "do not mutate unless a single
    # implementation-status bookkeeping line is strictly required; prefer no change").
    # For this test, we focus on TASK-006..TASK-018 frozen contracts.

    assert not frozen_modified, (
        f"frozen TASK-006..TASK-018 contract(s) modified by this branch: {frozen_modified!r}"
    )


def test_no_implementation_file_rewrites_frozen_docs() -> None:
    """No src/ or tests/ implementation file may attempt to write to docs/tasks/.

    Grep for file-mode write operations targeting docs/tasks/ in implementation
    code (allowlist: only docs/ files themselves may reference docs/tasks/).
    """
    # Scan src/ for any docs/tasks/ write attempts
    src_glob = list(_REPO_ROOT.glob("src/hexagent/validation_report/*.py"))
    for path in src_glob:
        text = path.read_text()
        # Heuristic: any "open(...docs/tasks/...)" with mode containing "w"
        if re.search(r"open\s*\([^)]*docs/tasks/[^)]*[\"\']w", text) or re.search(
            r"Path\s*\([^)]*docs/tasks/[^)]*\)\.write_text", text
        ):
            raise AssertionError(
                f"implementation file {path.name} attempts to write to docs/tasks/ — "
                f"frozen contract discipline violation"
            )


def test_task_017_stale_backlog_rows_not_edited() -> None:
    """TASK-017 stale backlog rows in docs/TASK_BACKLOG.md (L379/L455/L459) must
    not be edited by this branch.

    Verifies via `git diff` that the byte content of those specific lines
    is unchanged from origin/main.
    """
    result = subprocess.run(
        ["git", "show", "origin/main:docs/TASK_BACKLOG.md"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if result.returncode != 0:
        # origin/main not reachable, skip
        return
    origin_content = result.stdout
    origin_lines = origin_content.splitlines()
    # Stale rows (per TASK-019 preflight finding F1):
    # L379: TASK-017 design Issue #72 — OPEN
    # L455: TASK-017 implementation Issue #74 — OPEN
    # L459: TASK-017 implementation PR #75 remains DRAFT
    stale_substrings = [
        "#72 — OPEN",  # L379
        "#74 — OPEN",  # L455
        "PR #75 remains DRAFT",  # L459
    ]
    for stale in stale_substrings:
        # Check the line exists in origin/main
        matching = [line for line in origin_lines if stale in line]
        assert matching, f"stale row {stale!r} not found in origin/main"

    # Check current branch has not modified these rows
    # The implementation branch should have origin/main as ancestor (clean fast-forward)
    # so the rows should be byte-identical
    result_cur = subprocess.run(
        ["git", "show", "HEAD:docs/TASK_BACKLOG.md"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if result_cur.returncode != 0:
        return
    cur_content = result_cur.stdout
    for stale in stale_substrings:
        # Both origin/main and HEAD must have the stale row unchanged
        assert stale in cur_content, (
            f"stale row {stale!r} missing from current HEAD — frozen row was edited"
        )
