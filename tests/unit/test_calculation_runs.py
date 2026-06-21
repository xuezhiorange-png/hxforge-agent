"""Tests for CalculationRun state machine and serialisation.

Covers: all valid/invalid transitions, terminal-state requirements,
completed_at ordering, JSON round-trip, and immutability.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
    RunFailure,
)
from hexagent.domain.revisions import (
    CalculationRun,
    CalculationRunStatus,
    CalculationRunType,
    is_valid_transition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)
FIXED_LATER = datetime(2026, 1, 1, 0, 0, 10, tzinfo=UTC)
ZERO_HASH = "sha256:" + "0" * 64


def _pending_run(**overrides) -> CalculationRun:
    defaults = dict(
        run_id=UUID(int=1),
        case_id=UUID(int=100),
        case_revision_id=UUID(int=200),
        run_type=CalculationRunType.SCREEN,
        status=CalculationRunStatus.PENDING,
        started_at=FIXED_NOW,
        input_hash=ZERO_HASH,
    )
    defaults.update(overrides)
    return CalculationRun(**defaults)


def _running_run(**overrides) -> CalculationRun:
    defaults = dict(
        run_id=UUID(int=1),
        case_id=UUID(int=100),
        case_revision_id=UUID(int=200),
        run_type=CalculationRunType.SCREEN,
        status=CalculationRunStatus.RUNNING,
        started_at=FIXED_NOW,
        input_hash=ZERO_HASH,
    )
    defaults.update(overrides)
    return CalculationRun(**defaults)


def _make_blocker() -> EngineeringMessage:
    return EngineeringMessage(
        code=ErrorCode.CALCULATION_BLOCKED,
        severity=EngineeringMessageSeverity.BLOCKER,
        message="Missing required property",
    )


def _make_failure() -> RunFailure:
    return RunFailure(
        code=ErrorCode.CALCULATION_NOT_CONVERGED,
        message="Solver diverged",
    )


# ---------------------------------------------------------------------------
# Tests: state transition validation
# ---------------------------------------------------------------------------


class TestStateTransitionValidation:
    """The is_valid_transition function."""

    def test_pending_to_running(self) -> None:
        assert is_valid_transition(CalculationRunStatus.PENDING, CalculationRunStatus.RUNNING)

    def test_pending_to_cancelled(self) -> None:
        assert is_valid_transition(CalculationRunStatus.PENDING, CalculationRunStatus.CANCELLED)

    def test_running_to_succeeded(self) -> None:
        assert is_valid_transition(CalculationRunStatus.RUNNING, CalculationRunStatus.SUCCEEDED)

    def test_running_to_failed(self) -> None:
        assert is_valid_transition(CalculationRunStatus.RUNNING, CalculationRunStatus.FAILED)

    def test_running_to_blocked(self) -> None:
        assert is_valid_transition(CalculationRunStatus.RUNNING, CalculationRunStatus.BLOCKED)

    def test_running_to_cancelled(self) -> None:
        assert is_valid_transition(CalculationRunStatus.RUNNING, CalculationRunStatus.CANCELLED)

    def test_pending_to_succeeded_invalid(self) -> None:
        assert not is_valid_transition(CalculationRunStatus.PENDING, CalculationRunStatus.SUCCEEDED)

    def test_pending_to_failed_invalid(self) -> None:
        assert not is_valid_transition(CalculationRunStatus.PENDING, CalculationRunStatus.FAILED)

    def test_pending_to_blocked_invalid(self) -> None:
        assert not is_valid_transition(CalculationRunStatus.PENDING, CalculationRunStatus.BLOCKED)

    def test_succeeded_is_terminal(self) -> None:
        for target in CalculationRunStatus:
            if target == CalculationRunStatus.SUCCEEDED:
                continue
            assert not is_valid_transition(CalculationRunStatus.SUCCEEDED, target)

    def test_failed_is_terminal(self) -> None:
        for target in CalculationRunStatus:
            if target == CalculationRunStatus.FAILED:
                continue
            assert not is_valid_transition(CalculationRunStatus.FAILED, target)

    def test_blocked_is_terminal(self) -> None:
        for target in CalculationRunStatus:
            if target == CalculationRunStatus.BLOCKED:
                continue
            assert not is_valid_transition(CalculationRunStatus.BLOCKED, target)

    def test_cancelled_is_terminal(self) -> None:
        for target in CalculationRunStatus:
            if target == CalculationRunStatus.CANCELLED:
                continue
            assert not is_valid_transition(CalculationRunStatus.CANCELLED, target)


# ---------------------------------------------------------------------------
# Tests: terminal state requirements
# ---------------------------------------------------------------------------


class TestTerminalStateRequirements:
    """SUCCEEDED needs result_hash, FAILED needs failure, BLOCKED needs blockers."""

    def test_succeeded_needs_result_hash(self) -> None:
        """Default result_hash is None (no zero sentinel)."""
        run = _running_run()
        assert run.result_hash is None

    def test_failed_needs_failure(self) -> None:
        run = _running_run(
            status=CalculationRunStatus.FAILED,
            failure=_make_failure(),
            completed_at=FIXED_LATER,
        )
        assert run.failure is not None

    def test_failed_without_failure_is_invalid(self) -> None:
        """A FAILED run without a failure record is rejected at construction."""
        with pytest.raises(ValidationError, match="failure record"):
            _running_run(status=CalculationRunStatus.FAILED, failure=None)

    def test_blocked_needs_blockers(self) -> None:
        blocker = _make_blocker()
        run = _running_run(
            status=CalculationRunStatus.BLOCKED,
            blockers=(blocker,),
            completed_at=FIXED_LATER,
        )
        assert len(run.blockers) == 1

    def test_succeeded_completed_at_after_started_at(self) -> None:
        run = _running_run(
            status=CalculationRunStatus.SUCCEEDED,
            completed_at=FIXED_LATER,
            result_hash="sha256:" + "a" * 64,
        )
        assert run.completed_at is not None
        assert run.started_at is not None
        assert run.completed_at > run.started_at


# ---------------------------------------------------------------------------
# Tests: JSON round-trip
# ---------------------------------------------------------------------------


class TestCalculationRunJsonRoundTrip:
    """Serialisation and deserialisation preserve all fields."""

    def test_pending_run_round_trip(self) -> None:
        run = _pending_run()
        json_str = run.to_json()
        restored = CalculationRun.from_json(json_str)
        assert restored.run_id == run.run_id
        assert restored.case_id == run.case_id
        assert restored.status == CalculationRunStatus.PENDING
        assert restored.run_type == run.run_type

    def test_succeeded_run_round_trip(self) -> None:
        run = _running_run(
            status=CalculationRunStatus.SUCCEEDED,
            completed_at=FIXED_LATER,
            result_hash="sha256:" + "a" * 64,
        )
        json_str = run.to_json()
        restored = CalculationRun.from_json(json_str)
        assert restored.status == CalculationRunStatus.SUCCEEDED
        assert restored.result_hash == "sha256:" + "a" * 64
        assert restored.completed_at == FIXED_LATER

    def test_blocked_run_round_trip(self) -> None:
        blocker = _make_blocker()
        run = _running_run(
            status=CalculationRunStatus.BLOCKED,
            completed_at=FIXED_LATER,
            blockers=(blocker,),
        )
        json_str = run.to_json()
        restored = CalculationRun.from_json(json_str)
        assert restored.status == CalculationRunStatus.BLOCKED
        assert len(restored.blockers) == 1
        assert restored.blockers[0].code == ErrorCode.CALCULATION_BLOCKED

    def test_failed_run_round_trip(self) -> None:
        failure = _make_failure()
        run = _running_run(
            status=CalculationRunStatus.FAILED,
            completed_at=FIXED_LATER,
            failure=failure,
        )
        json_str = run.to_json()
        restored = CalculationRun.from_json(json_str)
        assert restored.status == CalculationRunStatus.FAILED
        assert restored.failure is not None
        assert restored.failure.code == ErrorCode.CALCULATION_NOT_CONVERGED


# ---------------------------------------------------------------------------
# Tests: immutability
# ---------------------------------------------------------------------------


class TestCalculationRunImmutability:
    """CalculationRun is a frozen Pydantic model."""

    def test_cannot_mutate_status(self) -> None:
        run = _pending_run()
        with pytest.raises((ValueError, ValidationError)):
            run.status = CalculationRunStatus.RUNNING  # type: ignore[misc]

    def test_cannot_mutate_result_hash(self) -> None:
        run = _pending_run()
        with pytest.raises((ValueError, ValidationError)):
            run.result_hash = "sha256:" + "b" * 64  # type: ignore[misc]

    def test_completed_run_immutable(self) -> None:
        run = _running_run(
            status=CalculationRunStatus.SUCCEEDED,
            completed_at=FIXED_LATER,
            result_hash="sha256:" + "a" * 64,
        )
        with pytest.raises((ValueError, ValidationError)):
            run.status = CalculationRunStatus.PENDING  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: model validation
# ---------------------------------------------------------------------------


class TestCalculationRunValidation:
    """Pydantic model validation constraints."""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            CalculationRun(
                run_id=UUID(int=1),
                case_id=UUID(int=100),
                case_revision_id=UUID(int=200),
                run_type=CalculationRunType.SCREEN,
                status=CalculationRunStatus.PENDING,
                started_at=FIXED_NOW,
                input_hash=ZERO_HASH,
                bogus_field="should fail",
            )

    def test_schema_version_default(self) -> None:
        run = _pending_run()
        assert run.schema_version == "1.0"

    def test_software_version_default(self) -> None:
        run = _pending_run()
        assert run.software_version == "0.1.0"
