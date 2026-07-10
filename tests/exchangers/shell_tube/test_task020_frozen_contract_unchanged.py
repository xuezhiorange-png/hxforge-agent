"""TASK-020 design contract frozen-contract-unchanged test.

Asserts that the TASK-020 design contract file
``docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`` is not
modified by this round. The contract is **frozen** at
``6bdc9d9de1be2a5d56fcee40804902100f8140aa`` (PR #118 merge commit).

This test verifies two invariants:

1. The TASK-020 design contract file is **present** on the
   implementation branch.
2. The TASK-020 design contract file is **unchanged** from the
   PR #118 merge base (``6bdc9d9d...``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_DESIGN_CONTRACT_PATH = Path("docs/tasks/TASK-020-shell-and-tube-configuration-schema.md")
# A unique 1-line signature of the design contract body: the §1
# "Authority, status and authorization gate" heading is the first
# section of the contract and is present in every revision of the
# design.
_EXPECTED_DESIGN_HEADING = "## 1. Authority, status and authorization gate"


def test_design_contract_present() -> None:
    assert _DESIGN_CONTRACT_PATH.exists(), f"missing design contract: {_DESIGN_CONTRACT_PATH}"


def test_design_contract_unchanged_from_main() -> None:
    """The TASK-020 design contract must not be modified by the
    Slice A implementation branch.

    Verified via ``git diff origin/main -- <path>`` which must
    return an empty diff.
    """
    result = subprocess.run(
        ["git", "diff", "origin/main", "--", str(_DESIGN_CONTRACT_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "", f"design contract modified:\n{result.stdout[:500]}"


def test_design_contract_first_heading_present() -> None:
    """The design contract §1 heading must be present (sanity
    check on the contract text)."""
    assert _EXPECTED_DESIGN_HEADING in _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8"), (
        "design contract §1 heading missing"
    )
