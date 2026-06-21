"""Tests for the pure-function applicability assessment engine."""

from __future__ import annotations

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
    ri = required_inputs or frozenset()
    return CorrelationDefinition(
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
            title="Fixture Paper",
            publication="Fixture Journal",
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
        """Absolute exceeded + allow_extrapolation → explicit_extrapolation."""
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
        assert result.status == ApplicabilityStatus.explicit_extrapolation
        assert result.allows_evaluation is True

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
        # Warn policy means warnings not blockers
        assert len(result.warnings) >= 1

    def test_no_bounds_returns_applicable(self) -> None:
        """No bounds defined → applicable (nothing to check)."""
        defn = _make_definition()
        inputs = _make_input()
        result = assess_applicability(defn, inputs)
        assert result.status == ApplicabilityStatus.applicable

    def test_optional_variable_not_supplied(self) -> None:
        """Non-required variable not supplied → still applicable (no bounds check)."""
        defn = _make_definition(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
        )
        inputs = _make_input(values={})  # reynolds not required but has bounds
        result = assess_applicability(defn, inputs)
        # Not required, so missing_input doesn't apply;
        # variable result is "missing" but overall status is applicable
        # because missing non-required variables don't block evaluation
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
