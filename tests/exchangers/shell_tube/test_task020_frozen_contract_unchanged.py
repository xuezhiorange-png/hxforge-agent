"""TASK-020 design contract frozen-contract-unchanged test.

Asserts that the TASK-020 design contract file
``docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`` is not
modified by this round. The contract is **frozen** at
``6bdc9d9de1be2a5d56fcee40804902100f8140aa`` (PR #118 merge commit).

This test verifies three invariants:

1. The TASK-020 design contract file is **present** on the
   implementation branch.
2. The TASK-020 design contract file is **unchanged** from the
   PR #118 merge base (``6bdc9d9d...``), verified by content hash
   (CI-independent: no git history or remote refs required).
3. The TASK-020 design contract §1 heading is present (sanity check
   on the contract text).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_DESIGN_CONTRACT_PATH = Path("docs/tasks/TASK-020-shell-and-tube-configuration-schema.md")
# A unique 1-line signature of the design contract body: the §1
# "Authority, status and authorization gate" heading is the first
# section of the contract and is present in every revision of the
# design.
_EXPECTED_DESIGN_HEADING = "## 1. Authority, status and authorization gate"

# SHA-256 of docs/tasks/TASK-020-shell-and-tube-configuration-schema.md
# at the frozen authority commit 6bdc9d9de1be2a5d56fcee40804902100f8140aa
# (PR #118 merge). Pre-computed via:
#   git show 6bdc9d9de1be2a5d56fcee40804902100f8140aa \
#     -- docs/tasks/TASK-020-shell-and-tube-configuration-schema.md \
#     | sha256sum
_EXPECTED_FROZEN_SHA256 = "2fde322d901fce25da1976bde40dffcac886fe4a7c92a42163afb7e9655ba623"


def test_design_contract_present() -> None:
    assert _DESIGN_CONTRACT_PATH.exists(), f"missing design contract: {_DESIGN_CONTRACT_PATH}"


def test_design_contract_unchanged_from_frozen_authority() -> None:
    """The TASK-020 design contract must not be modified by the
    Slice A implementation branch.

    Verified by content hash (SHA-256) against the pre-computed
    hash of the frozen authority commit's file content. This
    check is CI-independent: it requires only the checked-out
    file content, not git history, ``origin/main``, or any
    remote ref (which a shallow CI checkout may not provide).
    """
    current_sha256 = hashlib.sha256(_DESIGN_CONTRACT_PATH.read_bytes()).hexdigest()
    assert current_sha256 == _EXPECTED_FROZEN_SHA256, (
        "TASK-020 frozen design contract has drifted:\n"
        f"  current: {current_sha256}\n"
        f"  expected: {_EXPECTED_FROZEN_SHA256}"
    )


def test_design_contract_first_heading_present() -> None:
    """The design contract §1 heading must be present (sanity
    check on the contract text)."""
    assert _EXPECTED_DESIGN_HEADING in _DESIGN_CONTRACT_PATH.read_text(encoding="utf-8"), (
        "design contract §1 heading missing"
    )
