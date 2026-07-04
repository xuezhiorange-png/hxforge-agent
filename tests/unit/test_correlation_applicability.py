"""Tests for the pure-function applicability assessment engine."""

from __future__ import annotations

import pytest

from hexagent.correlations.applicability import assess_applicability
from hexagent.correlations.models import (
    ApplicabilityEnvelope,
    ApplicabilityStatus,
    ApplicabilityVariable,
    BibliographicSource,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationKey,
    CorrelationPurpose,
    FlowRegime,
    GeometryType,
    NumericBound,
    OutOfRangeAction,
    OutOfRangePolicy,
    PhaseRegime,
)

pytestmark = pytest.mark.pure

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_definition(
    *,
    geometry_types: frozenset[GeometryType] | None = None,
    phase_regimes: frozenset[PhaseRegime] | None = None,
    flow_regimes: frozenset[FlowRegime] | None = None,
    bounds: tuple[NumericBound, ...] | None = None,
    required_inputs: frozenset[ApplicabilityVariable] | None = None,
    out_of_range_policy: OutOfRangePolicy | None = None,
) -> CorrelationDefinition:
    """Build a minimal valid CorrelationDefinition for testing."""
    gt = geometry_types or frozenset({GeometryType.circular_tube})
    pr = phase_regimes or frozenset({PhaseRegime.single_phase_liquid})
    fr = flow_regimes or frozenset({FlowRegime.turbulent})
    bnds = bounds or ()
    # Item 3: required_inputs must include all bounded variables
    ri = required_inputs if required_inputs is not None else frozenset()
    if bnds and not ri:
        ri = frozenset({b.variable for b in bnds})
    return CorrelationDefinition.create(
        key=CorrelationKey(correlation_id="fixture.htc.tube", version="1.0.0"),
        name="Fixture HTC Tube",
        purpose=CorrelationPurpose.heat_transfer_coefficient,
        description="A fixture correlation for testing applicability",
        geometry=gt,
        phase_regimes=pr,
        envelope=ApplicabilityEnvelope(
            geometry_types=gt,
            phase_regimes=pr,
            flow_regimes=fr,
            bounds=bnds,
            required_inputs=ri,
        ),
        source=BibliographicSource(
            source_id="src-001",
            title="Fictional Paper",
            publication="Fictional Journal",
            year=2020,
        ),
        out_of_range_policy=out_of_range_policy or OutOfRangePolicy(),
    )


def _make_input(
    *,
    geometry: GeometryType = GeometryType.circular_tube,
    phase_regime: PhaseRegime = PhaseRegime.single_phase_liquid,
    flow_regime: FlowRegime = FlowRegime.turbulent,
    values: dict[ApplicabilityVariable, float] | None = None,
    allow_extrapolation: bool = False,
) -> CorrelationApplicabilityInput:
    return CorrelationApplicabilityInput(
        geometry=geometry,
        phase_regime=phase_regime,
        flow_regime=flow_regime,
        values=values or {},
        allow_extrapolation=allow_extrapolation,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAssessApplicability:
    """Core applicability assessment tests."""

    def test_all_applicable(self) -> None:
        """All criteria met → applicable."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable
        assert result.allows_evaluation is True
        assert len(result.warnings) == 0
        assert len(result.blockers) == 0
        assert result.assessment_hash.startswith("sha256:")

    def test_geometry_incompatible(self) -> None:
        """Wrong geometry → incompatible_geometry blocker."""
        defn = _make_definition(
            geometry_types=frozenset({GeometryType.circular_tube}),
        )
        inputs = _make_input(geometry=GeometryType.annulus)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_geometry
        assert result.allows_evaluation is False
        assert len(result.blockers) >= 1
        blocker_codes = [b.code.value for b in result.blockers]
        assert "correlation_geometry_incompatible" in blocker_codes

    def test_phase_incompatible(self) -> None:
        """Wrong phase → incompatible_phase blocker."""
        defn = _make_definition(
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
        )
        inputs = _make_input(phase_regime=PhaseRegime.boiling)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_phase
        assert len(result.blockers) >= 1

    def test_flow_regime_incompatible(self) -> None:
        """Wrong flow regime → incompatible_flow_regime blocker."""
        defn = _make_definition(
            flow_regimes=frozenset({FlowRegime.turbulent}),
        )
        inputs = _make_input(flow_regime=FlowRegime.laminar)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_flow_regime
        assert len(result.blockers) >= 1

    def test_missing_required_input(self) -> None:
        """Missing required variable → missing_input."""
        defn = _make_definition(
            required_inputs=frozenset({ApplicabilityVariable.reynolds}),
        )
        inputs = _make_input(values={})  # reynolds missing
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.missing_input
        assert result.allows_evaluation is False

    def test_recommended_range_exceeded(self) -> None:
        """Value above recommended but within absolute → recommended_range_exceeded."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 75000.0},  # above rec max
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.recommended_range_exceeded
        # Item 4: recommended_violation=warn → allows_evaluation=True
        assert result.allows_evaluation is True
        assert len(result.warnings) >= 1

    def test_absolute_range_exceeded(self) -> None:
        """Value outside absolute range → absolute_range_exceeded."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},  # above abs max
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is False

    def test_extrapolation_allowed(self) -> None:
        """Absolute exceeded + allow_extrapolation + allow_explicit_opt_in policy."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
            allow_extrapolation=True,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.explicit_extrapolation
        assert result.allows_evaluation is True

    def test_extrapolation_blocked_by_default_policy(self) -> None:
        """Item 4: allow_extrapolation=True with absolute_violation=block → blocked."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
            allow_extrapolation=True,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is False

    def test_below_absolute_range(self) -> None:
        """Value below absolute minimum → absolute_range_exceeded."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 1000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded

    def test_below_recommended_range(self) -> None:
        """Value below recommended minimum → recommended_range_exceeded."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 5000.0},  # below rec min
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.recommended_range_exceeded

    def test_custom_out_of_range_policy_warn(self) -> None:
        """Custom policy: absolute violation → warn (not block)."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.warn,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        # Warn policy → warnings not blockers, allows_evaluation=True
        assert len(result.warnings) >= 1
        assert result.allows_evaluation is True

    def test_no_bounds_returns_applicable(self) -> None:
        """No bounds defined → applicable (nothing to check)."""
        defn = _make_definition()
        inputs = _make_input()
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable

    def test_assessment_hash_deterministic(self) -> None:
        """Same inputs → same assessment hash."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        r1 = assess_applicability(defn, inputs)
        r2 = assess_applicability(defn, inputs)
        assert r1.assessment_hash == r2.assessment_hash

    def test_multiple_variables_mixed(self) -> None:
        """Multiple variables with mixed statuses → overall status based on worst."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
                NumericBound(
                    variable=ApplicabilityVariable.prandtl,
                    minimum=0.5,
                    maximum=500.0,
                    recommended_minimum=1.0,
                    recommended_maximum=100.0,
                ),
            ),
            required_inputs=frozenset(
                {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
            ),
        )
        inputs = _make_input(
            values={
                ApplicabilityVariable.reynolds: 25000.0,  # within rec range
                ApplicabilityVariable.prandtl: 200.0,  # above rec max
            },
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.recommended_range_exceeded
        assert len(result.variable_results) == 2

    def test_exclusive_bounds(self) -> None:
        """Exclusive bounds (min_inclusive=False, max_inclusive=False)."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    minimum_inclusive=False,
                    maximum_inclusive=False,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 3000.0},  # at minimum, exclusive
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded

    def test_inclusive_bounds_at_edge(self) -> None:
        """Inclusive bounds at exact edge → applicable."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    minimum_inclusive=True,
                    maximum_inclusive=True,
                ),
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 3000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable

    def test_tolerance_fraction_within_bound(self) -> None:
        """Item 4: Value within tolerance_fraction of bound is treated as in range."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    tolerance_fraction=0.1,  # 10% tolerance
                ),
            ),
        )
        # Value is 10% below minimum (3000 * 0.9 = 2700), should be within tolerance
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 2700.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable

    def test_tolerance_fraction_outside_bound(self) -> None:
        """Item 4: Value outside tolerance_fraction of bound is still out of range."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    tolerance_fraction=0.1,  # 10% tolerance
                ),
            ),
        )
        # Value is 20% below minimum (3000 * 0.8 = 2400), outside 10% tolerance
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 2400.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded

    def test_generic_geometry_matches_any(self) -> None:
        """Item 3: generic geometry matches ANY geometry."""
        defn = _make_definition(
            geometry_types=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
        )
        inputs = _make_input(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable

    def test_generic_phase_matches_any(self) -> None:
        """Item 3: generic phase matches ANY phase."""
        defn = _make_definition(
            phase_regimes=frozenset({PhaseRegime.generic}),
        )
        inputs = _make_input(phase_regime=PhaseRegime.boiling)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable

    # -------------------------------------------------------------------------
    # Item 4: Complete policy × violation decision-table tests
    # -------------------------------------------------------------------------

    def test_policy_decision_table_recommended_warn(self) -> None:
        """recommended_violation=warn → allows_evaluation=True."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                recommended_violation=OutOfRangeAction.warn,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 75000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.recommended_range_exceeded
        assert result.allows_evaluation is True

    def test_policy_decision_table_absolute_block(self) -> None:
        """absolute_violation=block → allows_evaluation=False."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.block,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is False

    def test_policy_decision_table_absolute_block_with_extrapolation(self) -> None:
        """Item 4: absolute_violation=block blocks even with allow_extrapolation."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.block,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
            allow_extrapolation=True,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is False

    def test_policy_decision_table_absolute_allow_opt_in(self) -> None:
        """absolute_violation=allow_explicit_opt_in + extrapolation → allows."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
            allow_extrapolation=True,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.explicit_extrapolation
        assert result.allows_evaluation is True

    def test_policy_decision_table_absolute_allow_opt_in_no_extrapolation(self) -> None:
        """absolute_violation=allow_explicit_opt_in + no extrapolation → blocks."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
            allow_extrapolation=False,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is False

    def test_policy_decision_table_absolute_warn(self) -> None:
        """absolute_violation=warn → allows_evaluation=True."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.warn,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is True

    def test_policy_decision_table_absolute_fallback(self) -> None:
        """absolute_violation=fallback_required → allows_evaluation=False."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.fallback_required,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 150000.0},
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.absolute_range_exceeded
        assert result.allows_evaluation is False

    def test_policy_decision_table_missing_input_block(self) -> None:
        """missing_input=block → allows_evaluation=False."""
        defn = _make_definition(
            required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            out_of_range_policy=OutOfRangePolicy(
                missing_input=OutOfRangeAction.block,
            ),
        )
        inputs = _make_input(values={})
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.missing_input
        assert result.allows_evaluation is False

    def test_policy_decision_table_missing_input_warn(self) -> None:
        """Item 4: missing_input=warn → allows_evaluation=True."""
        defn = _make_definition(
            required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            out_of_range_policy=OutOfRangePolicy(
                missing_input=OutOfRangeAction.warn,
            ),
        )
        inputs = _make_input(values={})
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.missing_input
        assert result.allows_evaluation is True

    # -------------------------------------------------------------------------
    # Item 2: Comprehensive decision-table tests for allow_explicit_opt_in
    # across ALL violation types
    # -------------------------------------------------------------------------

    def test_opt_in_missing_input_no_extrapolation(self) -> None:
        """Item 2: missing_input=allow_explicit_opt_in + no opt-in → BLOCKER."""
        defn = _make_definition(
            required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            out_of_range_policy=OutOfRangePolicy(
                missing_input=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(values={}, allow_extrapolation=False)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.missing_input
        assert result.allows_evaluation is False
        # All missing-input messages should be BLOCKER
        missing_msgs = [m for m in result.blockers if "missing" in m.message.lower()]
        assert len(missing_msgs) >= 1

    def test_opt_in_missing_input_with_extrapolation(self) -> None:
        """Item 2: missing_input=allow_explicit_opt_in + opt-in → WARNING."""
        defn = _make_definition(
            required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            out_of_range_policy=OutOfRangePolicy(
                missing_input=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(values={}, allow_extrapolation=True)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.missing_input
        assert result.allows_evaluation is True
        # All missing-input messages should be WARNING
        missing_warnings = [m for m in result.warnings if "missing" in m.message.lower()]
        assert len(missing_warnings) >= 1

    def test_opt_in_geometry_no_extrapolation(self) -> None:
        """Item 2: incompatible_geometry=allow_explicit_opt_in + no opt-in → BLOCKER."""
        defn = _make_definition(
            geometry_types=frozenset({GeometryType.circular_tube}),
            out_of_range_policy=OutOfRangePolicy(
                incompatible_geometry=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(geometry=GeometryType.annulus, allow_extrapolation=False)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_geometry
        assert result.allows_evaluation is False
        geo_blockers = [m for m in result.blockers if "geometry" in m.message.lower()]
        assert len(geo_blockers) >= 1

    def test_opt_in_geometry_with_extrapolation(self) -> None:
        """Item 2: incompatible_geometry=allow_explicit_opt_in + opt-in → WARNING."""
        defn = _make_definition(
            geometry_types=frozenset({GeometryType.circular_tube}),
            out_of_range_policy=OutOfRangePolicy(
                incompatible_geometry=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(geometry=GeometryType.annulus, allow_extrapolation=True)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_geometry
        assert result.allows_evaluation is True
        geo_warnings = [m for m in result.warnings if "geometry" in m.message.lower()]
        assert len(geo_warnings) >= 1

    def test_opt_in_phase_no_extrapolation(self) -> None:
        """Item 2: incompatible_phase=allow_explicit_opt_in + no opt-in → BLOCKER."""
        defn = _make_definition(
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            out_of_range_policy=OutOfRangePolicy(
                incompatible_phase=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(phase_regime=PhaseRegime.boiling, allow_extrapolation=False)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_phase
        assert result.allows_evaluation is False
        phase_blockers = [m for m in result.blockers if "phase" in m.message.lower()]
        assert len(phase_blockers) >= 1

    def test_opt_in_phase_with_extrapolation(self) -> None:
        """Item 2: incompatible_phase=allow_explicit_opt_in + opt-in → WARNING."""
        defn = _make_definition(
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            out_of_range_policy=OutOfRangePolicy(
                incompatible_phase=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(phase_regime=PhaseRegime.boiling, allow_extrapolation=True)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_phase
        assert result.allows_evaluation is True
        phase_warnings = [m for m in result.warnings if "phase" in m.message.lower()]
        assert len(phase_warnings) >= 1

    def test_opt_in_flow_no_extrapolation(self) -> None:
        """Item 2: incompatible_flow_regime=allow_explicit_opt_in + no opt-in → BLOCKER."""
        defn = _make_definition(
            flow_regimes=frozenset({FlowRegime.turbulent}),
            out_of_range_policy=OutOfRangePolicy(
                incompatible_flow_regime=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(flow_regime=FlowRegime.laminar, allow_extrapolation=False)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_flow_regime
        assert result.allows_evaluation is False
        flow_blockers = [m for m in result.blockers if "flow" in m.message.lower()]
        assert len(flow_blockers) >= 1

    def test_opt_in_flow_with_extrapolation(self) -> None:
        """Item 2: incompatible_flow_regime=allow_explicit_opt_in + opt-in → WARNING."""
        defn = _make_definition(
            flow_regimes=frozenset({FlowRegime.turbulent}),
            out_of_range_policy=OutOfRangePolicy(
                incompatible_flow_regime=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(flow_regime=FlowRegime.laminar, allow_extrapolation=True)
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.incompatible_flow_regime
        assert result.allows_evaluation is True
        flow_warnings = [m for m in result.warnings if "flow" in m.message.lower()]
        assert len(flow_warnings) >= 1

    def test_opt_in_recommended_range_no_extrapolation(self) -> None:
        """Item 2: recommended_violation=allow_explicit_opt_in + no opt-in → BLOCKER."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                recommended_violation=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 75000.0},
            allow_extrapolation=False,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.recommended_range_exceeded
        assert result.allows_evaluation is False

    def test_opt_in_recommended_range_with_extrapolation(self) -> None:
        """Item 2: recommended_violation=allow_explicit_opt_in + opt-in → explicit_extrapolation."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                    recommended_minimum=10000.0,
                    recommended_maximum=50000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                recommended_violation=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )
        inputs = _make_input(
            values={ApplicabilityVariable.reynolds: 75000.0},
            allow_extrapolation=True,
        )
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.explicit_extrapolation
        assert result.allows_evaluation is True

    # -------------------------------------------------------------------------
    # Item 3: Assessment hash completeness tests
    # -------------------------------------------------------------------------

    def test_assessment_hash_includes_geometry(self) -> None:
        """Item 3: Changing geometry changes assessment hash."""
        defn = _make_definition(
            geometry_types=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
        )
        inputs1 = _make_input(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
        )
        inputs2 = _make_input(
            geometry=GeometryType.annulus,
            phase_regime=PhaseRegime.single_phase_liquid,
        )
        r1 = assess_applicability(defn, inputs1)
        r2 = assess_applicability(defn, inputs2)
        # Different geometry → different hash
        assert r1.assessment_hash != r2.assessment_hash

    def test_assessment_hash_includes_phase(self) -> None:
        """Item 3: Changing phase changes assessment hash."""
        defn = _make_definition(
            geometry_types=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
        )
        inputs1 = _make_input(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
        )
        inputs2 = _make_input(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.boiling,
        )
        r1 = assess_applicability(defn, inputs1)
        r2 = assess_applicability(defn, inputs2)
        assert r1.assessment_hash != r2.assessment_hash

    def test_assessment_hash_includes_flow(self) -> None:
        """Item 3: Changing flow changes assessment hash."""
        defn = _make_definition(
            flow_regimes=frozenset({FlowRegime.turbulent}),
        )
        inputs1 = _make_input(flow_regime=FlowRegime.turbulent)
        inputs2 = _make_input(flow_regime=FlowRegime.laminar)
        r1 = assess_applicability(defn, inputs1)
        r2 = assess_applicability(defn, inputs2)
        assert r1.assessment_hash != r2.assessment_hash

    def test_assessment_hash_includes_input_values(self) -> None:
        """Item 3: Changing input values changes hash."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
        )
        inputs1 = _make_input(values={ApplicabilityVariable.reynolds: 25000.0})
        inputs2 = _make_input(values={ApplicabilityVariable.reynolds: 50000.0})
        r1 = assess_applicability(defn, inputs1)
        r2 = assess_applicability(defn, inputs2)
        assert r1.assessment_hash != r2.assessment_hash

    def test_assessment_hash_includes_policy(self) -> None:
        """Item 3: Changing policy changes hash."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.block,
            ),
        )
        defn2 = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.warn,
            ),
        )
        inputs = _make_input(values={ApplicabilityVariable.reynolds: 150000.0})
        r1 = assess_applicability(defn, inputs)
        r2 = assess_applicability(defn2, inputs)
        assert r1.assessment_hash != r2.assessment_hash

    def test_assessment_hash_includes_allow_extrapolation(self) -> None:
        """Item 3: Changing allow_extrapolation changes hash."""
        defn = _make_definition()
        inputs1 = _make_input(allow_extrapolation=False)
        inputs2 = _make_input(allow_extrapolation=True)
        r1 = assess_applicability(defn, inputs1)
        r2 = assess_applicability(defn, inputs2)
        assert r1.assessment_hash != r2.assessment_hash
