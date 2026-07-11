"""TASK-020 design contract frozen-contract-unchanged test.

Asserts that the TASK-020 design contract file
``docs/tasks/TASK-020-shell-and-tube-configuration-schema.md`` is not
modified except via this frozen-contract guard. The contract is
**frozen** at the Amendment 002 / Issue #131 review-correction
authority revision (PR #132 review "4677752194" P0/P1 fixes).

This test verifies three invariants:

1. The TASK-020 design contract file is **present** on the
   implementation branch.
2. The TASK-020 design contract file is **unchanged** from the
   Amendment 002 / Issue #131 review-correction final byte content,
   verified by content hash (CI-independent: no git history or
   remote refs required).
3. The TASK-020 design contract §1 heading is present (sanity
   check on the contract text).

This test is the **only** test mutation authorized by the
Amendment 002 / Issue #131 review-correction round (PR #132). It
MUST NOT be weakened or bypassed, MUST NOT carry a list or set of
accepted hashes, and MUST NOT retain any old hash as a fallback.
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
# at the frozen authority revision TASK-020 Design Amendment 002 /
# Issue #131 final byte content (this branch HEAD).
# Pre-computed via:
#   python3 -c \
#     "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('docs/tasks/TASK-020-shell-and-tube-configuration-schema.md').read_bytes()).hexdigest())"  # noqa: E501
#
# Authority chain: Amendment 001 merge SHA d4ee40109c74061db89339e55899cabfe2fb80fe
#                  → Design Amendment 002 / Issue #131 final byte content
#                  → SHA-256 ec15dd0668f4497c981a432bde5aaeef50560060e4733872f367aa9c35426ddb
# Authority chain: Amendment 001 merge SHA d4ee40109c74061db89339e55899cabfe2fb80fe
# (Design Amendment 001 frozen the design contract on main with SHA-256
#  0b369c9552bbe69c71faef92e564a974d2a6fab3badfb7866eadd752caed2f73);
# → Design Amendment 002 / Issue #131 round set _EXPECTED_FROZEN_SHA256
#   to ec15dd0668f4497c981a432bde5aaeef50560060e4733872f367aa9c35426ddb;
# → Review "4677752194" P0/P1 corrective Commit E (this branch HEAD)
#   fixed §12.5 fallback removal, narrowed §10.2 trigger, reconciled
#   §1 current-main vs proposed Amendment 002 authority; final byte
#   content SHA-256 is the single accepted hash below.
_EXPECTED_FROZEN_SHA256 = "9d6ae05ca2f1656f9a7c63a35f6043cea9220f21a59fcb7e97f3d79819a5c4c2"


def test_design_contract_present() -> None:
    assert _DESIGN_CONTRACT_PATH.exists(), f"missing design contract: {_DESIGN_CONTRACT_PATH}"


def test_design_contract_unchanged_from_frozen_authority() -> None:
    """The TASK-020 design contract must not be modified by the
    Amendment 002 / Issue #131 review-correction round except via
    this test's own SHA-256 update.

    Verified by content hash (SHA-256) against the pre-computed
    hash of the frozen authority revision's file content. This
    check is CI-independent: it requires only the checked-out
    file content, not git history, ``origin/main``, or any
    remote ref (which a shallow CI checkout may not provide).
    Only the single accepted hash listed at module scope is
    allowed; no fallback list, no set of accepted hashes, no
    OR-style bypass.
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
