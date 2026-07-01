"""Tests for EngineeringMessage, EngineeringMessageSeverity, ErrorCode.

Covers: all severity levels, JSON round-trip, code constants, and
allows_continuation semantics.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
    RunFailure,
)

pytestmark = pytest.mark.coolprop

# ---------------------------------------------------------------------------
# Tests: EngineeringMessageSeverity
# ---------------------------------------------------------------------------


class TestEngineeringMessageSeverity:
    """All severity levels are accessible."""

    def test_info(self) -> None:
        assert EngineeringMessageSeverity.INFO == "info"

    def test_warning(self) -> None:
        assert EngineeringMessageSeverity.WARNING == "warning"

    def test_error(self) -> None:
        assert EngineeringMessageSeverity.ERROR == "error"

    def test_blocker(self) -> None:
        assert EngineeringMessageSeverity.BLOCKER == "blocker"

    def test_all_values_are_lowercase(self) -> None:
        for sev in EngineeringMessageSeverity:
            assert sev.value == sev.value.lower()

    def test_iterable(self) -> None:
        values = list(EngineeringMessageSeverity)
        assert len(values) == 4


# ---------------------------------------------------------------------------
# Tests: ErrorCode
# ---------------------------------------------------------------------------


class TestErrorCode:
    """ErrorCode constants exist and are stable strings."""

    def test_input_missing(self) -> None:
        assert ErrorCode.INPUT_MISSING == "input_missing"

    def test_input_inconsistent(self) -> None:
        assert ErrorCode.INPUT_INCONSISTENT == "input_inconsistent"

    def test_unit_invalid(self) -> None:
        assert ErrorCode.UNIT_INVALID == "unit_invalid"

    def test_property_unavailable(self) -> None:
        assert ErrorCode.PROPERTY_UNAVAILABLE == "property_unavailable"

    def test_property_out_of_range(self) -> None:
        assert ErrorCode.PROPERTY_OUT_OF_RANGE == "property_out_of_range"

    def test_calculation_not_converged(self) -> None:
        assert ErrorCode.CALCULATION_NOT_CONVERGED == "calculation_not_converged"

    def test_calculation_blocked(self) -> None:
        assert ErrorCode.CALCULATION_BLOCKED == "calculation_blocked"

    def test_unsupported_service(self) -> None:
        assert ErrorCode.UNSUPPORTED_SERVICE == "unsupported_service"

    def test_not_implemented(self) -> None:
        assert ErrorCode.NOT_IMPLEMENTED == "not_implemented"

    def test_provenance_incomplete(self) -> None:
        assert ErrorCode.PROVENANCE_INCOMPLETE == "provenance_incomplete"

    def test_hash_mismatch(self) -> None:
        assert ErrorCode.HASH_MISMATCH == "hash_mismatch"

    def test_invalid_state_transition(self) -> None:
        assert ErrorCode.INVALID_STATE_TRANSITION == "invalid_state_transition"


# ---------------------------------------------------------------------------
# Tests: EngineeringMessage
# ---------------------------------------------------------------------------


class TestEngineeringMessage:
    """Construction, validation, and serialisation of EngineeringMessage."""

    def test_create_info_message(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.INFO,
            message="Informational note",
        )
        assert msg.severity == EngineeringMessageSeverity.INFO
        assert msg.allows_continuation is True  # INFO allows continuation

    def test_create_warning_message(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.PROPERTY_OUT_OF_RANGE,
            severity=EngineeringMessageSeverity.WARNING,
            message="Temperature outside correlation envelope",
            allows_continuation=True,
        )
        assert msg.severity == EngineeringMessageSeverity.WARNING
        assert msg.allows_continuation is True

    def test_create_error_message(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            severity=EngineeringMessageSeverity.ERROR,
            message="Solver did not converge",
        )
        assert msg.severity == EngineeringMessageSeverity.ERROR

    def test_create_blocker_message(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="Fatal: no fluid defined",
        )
        assert msg.severity == EngineeringMessageSeverity.BLOCKER

    def test_default_allows_continuation_by_severity(self) -> None:
        # WARNING and INFO allow continuation
        warn = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="test",
        )
        assert warn.allows_continuation is True
        # ERROR and BLOCKER do not
        err = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="test",
        )
        assert err.allows_continuation is False

    def test_with_context(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="Missing data",
            context=(("field", "inlet_temperature"), ("stream", "hot")),
        )
        ctx_dict = dict(msg.context)
        assert ctx_dict["field"] == "inlet_temperature"

    def test_with_affected_paths(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.PROPERTY_UNAVAILABLE,
            severity=EngineeringMessageSeverity.ERROR,
            message="Property not available",
            affected_paths=("hot_stream.fluid", "cold_stream.fluid"),
        )
        assert len(msg.affected_paths) == 2

    def test_frozen_model(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="test",
        )
        with pytest.raises((ValueError, ValidationError)):
            msg.message = "changed"  # type: ignore[misc]

    def test_json_round_trip(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.PROPERTY_OUT_OF_RANGE,
            severity=EngineeringMessageSeverity.WARNING,
            message="Value out of range",
            source_module="properties.coolprop",
            affected_paths=("hot_stream",),
            context=(("min", 200), ("max", 500)),
            allows_continuation=True,
        )
        json_str = msg.to_json()
        restored = EngineeringMessage.from_json(json_str)
        assert restored.code == msg.code
        assert restored.severity == msg.severity
        assert restored.message == msg.message
        assert restored.source_module == msg.source_module
        assert restored.affected_paths == msg.affected_paths
        assert restored.context == msg.context
        assert restored.allows_continuation is True

    def test_code_must_not_be_empty(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            EngineeringMessage(
                code="",  # type: ignore[arg-type]  # empty string not valid ErrorCode
                severity=EngineeringMessageSeverity.WARNING,
                message="test",
            )

    def test_message_must_not_be_empty(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            EngineeringMessage(
                code=ErrorCode.INPUT_MISSING,
                severity=EngineeringMessageSeverity.WARNING,
                message="",
            )


# ---------------------------------------------------------------------------
# Tests: allows_continuation semantics
# ---------------------------------------------------------------------------


class TestAllowsContinuationSemantics:
    """The allows_continuation flag controls downstream behaviour."""

    def test_warning_with_continuation(self) -> None:
        msg = EngineeringMessage(
            code=ErrorCode.PROPERTY_OUT_OF_RANGE,
            severity=EngineeringMessageSeverity.WARNING,
            message="Extrapolating",
            allows_continuation=True,
        )
        # Downstream code should check this flag, not the severity alone
        assert msg.allows_continuation is True
        # The message can carry a warning without blocking the run
        assert msg.severity == EngineeringMessageSeverity.WARNING

    def test_severity_overrides_continuation(self) -> None:
        # Even if caller passes allows_continuation=False, WARNING severity
        # overrides it to True
        msg = EngineeringMessage(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            severity=EngineeringMessageSeverity.WARNING,
            message="Near singular matrix",
            allows_continuation=False,
        )
        assert msg.allows_continuation is True  # derived from severity


# ---------------------------------------------------------------------------
# Tests: RunFailure
# ---------------------------------------------------------------------------


class TestRunFailure:
    """Structured failure records."""

    def test_create_failure(self) -> None:
        f = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Convergence failed after 100 iterations",
        )
        assert f.code == ErrorCode.CALCULATION_NOT_CONVERGED
        assert f.traceback is None

    def test_with_traceback(self) -> None:
        f = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Error",
            traceback="Traceback: ...",
        )
        assert f.traceback == "Traceback: ..."

    def test_json_round_trip(self) -> None:
        f = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Error",
            context=(("iterations", 100),),
        )
        json_str = f.to_json()
        restored = RunFailure.from_json(json_str)
        assert restored.code == f.code
        assert restored.message == f.message
        assert restored.context == f.context

    def test_frozen(self) -> None:
        f = RunFailure(code=ErrorCode.BLOCKER, message="test")
        with pytest.raises((ValueError, ValidationError)):
            f.message = "changed"  # type: ignore[misc]
