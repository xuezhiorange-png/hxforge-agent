"""TASK-015 governance — Section 11.2.8 frozen-contract reference test.

Implements the TASK-015 frozen design contract
(``docs/tasks/TASK-015-ci-security-and-release-automation.md``,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 11.2.8 — a spec referencing a frozen contract (TASK-011 /
TASK-012 / TASK-013 / TASK-014 / TASK-015 / TASK-015A) that is not yet
established MUST raise :class:`GovernanceAuthorityError`. Conversely,
a spec referencing an established frozen contract MUST pass.

This test file uses a **validator-level hook** that is pure and
deterministic — it does not perform any GitHub API call. The
"established" status is supplied through the existing
``validate_spec(..., known_failure_modes=...)`` interface, extended
here with a new ``established_frozen_contracts`` keyword. By default,
ALL governed frozen contracts are treated as established (matching the
state on ``main`` after TASK-015 first-slice merge).

The tests below verify both directions:
* pass when the spec references an established frozen contract,
* raise :class:`GovernanceAuthorityError` when the spec references an
  unestablished frozen contract.
"""

from __future__ import annotations

from typing import Any

import pytest

from hexagent.governance import (
    GOVERNED_FROZEN_CONTRACTS,
    GovernanceAuthorityError,
    SPEC_PATH_RELEASE,
    ValidationFinding,
    validate_spec,
)

from ._factories import build_release_spec


def _spec_with_frozen_contract_ref(reference: str) -> dict[str, Any]:
    """Build a release-spec data dict that references ``reference`` as
    its single frozen-contract authority. The factory default lists
    five references; we override with one to make the test targeted.
    """
    from hexagent.governance.spec_validator import _spec_for_hash, compute_content_hash

    data = build_release_spec()
    data["release_gate"] = {
        "require_content_hash_stability": True,
        "require_frozen_contract_reference": True,
        "frozen_contract_references": [reference],
    }
    # content_hash must match the new canonical form (Section 9.2).
    data["content_hash"] = compute_content_hash(_spec_for_hash(data))
    return data


def test_11_2_8_all_governed_frozen_contracts_are_known() -> None:
    """Section 11.2.8 + Section 8.1 closed enum — every frozen-contract
    identifier in the closed enum is recognized. This is a sanity
    check that the test itself is built against an up-to-date enum.
    """
    expected = {
        "task_011_frozen_contract",
        "task_012_frozen_contract",
        "task_013_frozen_contract",
        "task_014_frozen_contract",
        "task_015_frozen_contract",
        "task_015a_frozen_contract",
    }
    assert GOVERNED_FROZEN_CONTRACTS == frozenset(expected)


def test_11_2_8_established_frozen_contract_reference_passes() -> None:
    """Section 11.2.8 — a spec referencing an established frozen
    contract MUST pass (no ``governance_authority_error`` finding).
    """
    spec_path = SPEC_PATH_RELEASE
    data = _spec_with_frozen_contract_ref("task_014_frozen_contract")
    report = validate_spec(spec_path, data)
    governance_findings = [
        f for f in (*report.blockers, *report.warnings)
        if f.error_code == "governance_authority_error"
    ]
    assert governance_findings == [], (
        "established frozen contract should not raise governance_authority_error; "
        f"got {[f.to_dict() for f in governance_findings]}"
    )


@pytest.mark.parametrize(
    "unestablished_reference",
    [
        "task_011_frozen_contract",
        "task_012_frozen_contract",
        "task_013_frozen_contract",
        "task_014_frozen_contract",
        "task_015_frozen_contract",
        "task_015a_frozen_contract",
    ],
)
def test_11_2_8_unestablished_frozen_contract_reference_raises_blocker(
    unestablished_reference: str,
) -> None:
    """Section 11.2.8 — a spec referencing a frozen contract that is
    not yet established MUST raise ``governance_authority_error`` as a
    BLOCKER (not a warning).

    The validator-level hook (validated via the test-level
    ``established_frozen_contracts`` argument) records every governed
    frozen contract as unestablished by default in this test, so
    every reference is rejected.
    """
    spec_path = SPEC_PATH_RELEASE
    data = _spec_with_frozen_contract_ref(unestablished_reference)
    # Establish nothing — every governed contract is unestablished.
    report = validate_spec(
        spec_path,
        data,
        established_frozen_contracts=frozenset(),
    )
    blocker = [
        f for f in report.blockers
        if f.error_code == "governance_authority_error"
        and f.context.get("missing_authority") == unestablished_reference
    ]
    assert len(blocker) == 1, (
        f"expected exactly one governance_authority_error blocker for "
        f"{unestablished_reference!r}; got "
        f"blockers={[f.to_dict() for f in report.blockers]}"
    )
    assert blocker[0].severity == "blocker", (
        "Section 11.2.8 — governance_authority_error MUST surface as a BLOCKER"
    )


def test_11_2_8_governance_authority_error_is_distinct_from_identifier_collision() -> None:
    """Section 8.2 — GovernanceAuthorityError is disambiguated from
    SpecIdentifierCollision. The test confirms the two error codes
    never overlap on a single finding.
    """
    spec_path = SPEC_PATH_RELEASE
    data = _spec_with_frozen_contract_ref("task_011_frozen_contract")
    report = validate_spec(
        spec_path,
        data,
        established_frozen_contracts=frozenset(),
    )
    codes = {f.error_code for f in report.blockers}
    assert "governance_authority_error" in codes
    assert "spec_identifier_collision" not in codes, (
        "Section 8.2 — GovernanceAuthorityError MUST NOT be conflated "
        "with SpecIdentifierCollision"
    )


def test_11_2_8_partial_established_set_only_flags_unestablished() -> None:
    """Section 11.2.8 — when SOME frozen contracts are established and
    others are not, only the unestablished references raise
    ``governance_authority_error``. This is the partial-establishment
    case that motivates the explicit ``established_frozen_contracts``
    hook (rather than a boolean "all / none" flag).
    """
    spec_path = SPEC_PATH_RELEASE
    data = build_release_spec()
    # Two references: one established, one not.
    from hexagent.governance.spec_validator import _spec_for_hash, compute_content_hash

    data["release_gate"] = {
        "require_content_hash_stability": True,
        "require_frozen_contract_reference": True,
        "frozen_contract_references": [
            "task_011_frozen_contract",  # established
            "task_015_frozen_contract",  # NOT established
        ],
    }
    data["content_hash"] = compute_content_hash(_spec_for_hash(data))

    report = validate_spec(
        spec_path,
        data,
        established_frozen_contracts=frozenset({"task_011_frozen_contract"}),
    )
    blockers = [
        f for f in report.blockers
        if f.error_code == "governance_authority_error"
    ]
    assert len(blockers) == 1, (
        f"expected exactly one blocker (task_015_frozen_contract); "
        f"got {[(f.error_code, f.context.get('missing_authority')) for f in blockers]}"
    )
    assert blockers[0].context.get("missing_authority") == "task_015_frozen_contract"