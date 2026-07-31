"""TASK-026 blocker registry tests (T1-R2 numbered_inventory items 21-24).

Frozen test reference set (T1-R2):
  21. test_registry_size_is_14
  22. test_severity_is_hard_for_every_entry
  23. test_BL_NON_CONVERGENCE_not_emitted
  24. test_BL_PARTIAL_RESULT_FORBIDDEN_is_defensive_unreachable

T1-R2 module allocation: 4 tests in this module.
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    DEFENSIVE_COUNT,
    DEFENSIVE_UNREACHABLE_CODE,
    REACHABLE_COUNT,
    RESERVED_NOT_EMITTED,
    TASK026_BLOCKER_CODE_COUNT,
    TASK026_BLOCKER_REGISTRY,
    TASK026_BLOCKER_SEVERITY,
    TASK026_DEFENSIVE_BLOCKERS,
    TASK026_REACHABLE_BLOCKERS,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    BlockerCode,
    BlockerEntry,
)


def test_registry_size_is_14() -> None:
    """T1-R2 21 — Registry has exactly 14 codes."""
    assert len(TASK026_BLOCKER_REGISTRY) == 14
    assert TASK026_BLOCKER_CODE_COUNT == 14
    assert len(BlockerCode.__members__) == 14


def test_severity_is_hard_for_every_entry() -> None:
    """T1-R2 22 — All entries have severity 'hard'."""
    for code in TASK026_BLOCKER_REGISTRY:
        assert TASK026_BLOCKER_SEVERITY[code] == 'hard'


def test_BL_NON_CONVERGENCE_not_emitted() -> None:
    """T1-R2 23 — BL_NON_CONVERGENCE is NOT in the registry."""
    assert 'BL_NON_CONVERGENCE' not in TASK026_BLOCKER_REGISTRY
    assert RESERVED_NOT_EMITTED == 'BL_NON_CONVERGENCE'
    # Constructing a BlockerEntry with this code should fail.
    import pytest
    with pytest.raises(ValueError):
        BlockerEntry(
            code='BL_NON_CONVERGENCE',
            severity='hard',
            stage='S09',
            payload=(),
            message_template='should not be emitted',
        )


def test_BL_PARTIAL_RESULT_FORBIDDEN_is_defensive_unreachable() -> None:
    """T1-R2 24 — BL_PARTIAL_RESULT_FORBIDDEN is defensive, not reachable."""
    assert DEFENSIVE_UNREACHABLE_CODE == 'BL_PARTIAL_RESULT_FORBIDDEN'
    assert 'BL_PARTIAL_RESULT_FORBIDDEN' in TASK026_DEFENSIVE_BLOCKERS
    assert 'BL_PARTIAL_RESULT_FORBIDDEN' not in TASK026_REACHABLE_BLOCKERS
    assert DEFENSIVE_COUNT == 1
    assert REACHABLE_COUNT == 13
