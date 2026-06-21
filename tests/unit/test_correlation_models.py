"""Tests for correlation domain models.

Covers: enums, frozen models, validators, serialization round-trips.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityEnvelope,
    ApplicabilityStatus,
    ApplicabilityVariable,
    BibliographicSource,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationImplementationStatus,
    CorrelationKey,
    CorrelationPurpose,
    FlowRegime,
    GeometryType,
    NumericBound,
    OutOfRangeAction,
    OutOfRangePolicy,
    PhaseRegime,
    SourceVerificationStatus,
    UncertaintySpec,
    VariableApplicabilityStatus,
    VariableAssessment,
    parse_semver,
)
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestCorrelationPurpose:
    def test_all_values(self) -> None:
        values = [e.value for e in CorrelationPurpose]
        assert "heat_transfer_coefficient" in values
        assert "friction_factor" in values
        assert len(values) == 10

    def test_is_str_enum(self) -> None:
        assert isinstance(CorrelationPurpose.heat_transfer_coefficient, str)


class TestGeometryType:
    def test_all_values(self) -> None:
        values = [e.value for e in GeometryType]
        assert "circular_tube" in values
        assert "generic" in values
        assert len(values) == 9


class TestPhaseRegime:
    def test_all_values(self) -> None:
        values = [e.value for e in PhaseRegime]
        assert "single_phase_liquid" in values
        assert "boiling" in values
        assert "generic" in values
        assert len(values) == 8


class TestFlowRegime:
    def test_all_values(self) -> None:
        values = [e.value for e in FlowRegime]
        assert "laminar" in values
        assert "turbulent" in values
        assert "not_applicable" in values
        assert len(values) == 5


class TestApplicabilityVariable:
    def test_all_values(self) -> None:
        values = [e.value for e in ApplicabilityVariable]
        assert "reynolds" in values
        assert "prandtl" in values
        assert len(values) == 13


class TestCorrelationImplementationStatus:
    def test_all_values(self) -> None:
        values = [e.value for e in CorrelationImplementationStatus]
        assert "metadata_only" in values
        assert "deprecated" in values
        assert "withdrawn" in values
        assert len(values) == 5


class TestSourceVerificationStatus:
    def test_all_values(self) -> None:
        values = [e.value for e in SourceVerificationStatus]
        assert "unverified" in values
        assert "independently_verified" in values
        assert len(values) == 4


class TestOutOfRangeAction:
    def test_all_values(self) -> None:
        values = [e.value for e in OutOfRangeAction]
        assert "block" in values
        assert "warn" in values
        assert len(values) == 4


class TestApplicabilityStatus:
    def test_all_values(self) -> None:
        values = [e.value for e in ApplicabilityStatus]
        assert "applicable" in values
        assert "absolute_range_exceeded" in values
        assert len(values) == 8


class TestVariableApplicabilityStatus:
    def test_all_values(self) -> None:
        values = [e.value for e in VariableApplicabilityStatus]
        assert "applicable" in values
        assert "missing" in values
        assert len(values) == 6


# ---------------------------------------------------------------------------
# SemVer tests (Item 2)
# ---------------------------------------------------------------------------


class TestSemVer:
    def test_valid_stable(self) -> None:
        major, minor, patch, pre = parse_semver("1.0.0")
        assert (major, minor, patch) == (1, 0, 0)
        assert pre == ()

    def test_valid_prerelease(self) -> None:
        major, minor, patch, pre = parse_semver("1.0.0-alpha")
        assert (major, minor, patch) == (1, 0, 0)
        assert pre == ("alpha",)

    def test_valid_prerelease_numeric(self) -> None:
        major, minor, patch, pre = parse_semver("1.0.0-alpha.1")
        assert pre == ("alpha", 1)

    def test_malformed_no_patch(self) -> None:
        with pytest.raises(ValueError, match="Invalid SemVer"):
            parse_semver("1.0")

    def test_malformed_trailing_junk(self) -> None:
        with pytest.raises(ValueError, match="Invalid SemVer"):
            parse_semver("1.0.0junk")

    def test_build_metadata_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid SemVer"):
            parse_semver("1.0.0+build.123")

    def test_build_metadata_plus_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid SemVer"):
            parse_semver("1.0.0+build")

    def test_prerelease_precedence_numeric(self) -> None:
        """Numeric identifiers compared numerically: alpha.2 < alpha.10."""
        _, _, _, pre2 = parse_semver("1.0.0-alpha.2")
        _, _, _, pre10 = parse_semver("1.0.0-alpha.10")
        assert pre2 < pre10

    def test_prerelease_precedence_lexical(self) -> None:
        """Alphanumeric identifiers compared lexically: alpha < beta."""
        _, _, _, pre_alpha = parse_semver("1.0.0-alpha")
        _, _, _, pre_beta = parse_semver("1.0.0-beta")
        assert pre_alpha < pre_beta

    def test_stable_after_prerelease(self) -> None:
        """Stable sorts after prerelease of same version number."""
        from hexagent.correlations.models import CorrelationDefinition

        pre_defn = CorrelationDefinition(
            key=CorrelationKey(correlation_id="test", version="1.0.0-alpha"),
            name="Pre",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
            geometry=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
            envelope=ApplicabilityEnvelope(),
            source=BibliographicSource(source_id="s", title="T", publication="P", year=2020),
        )
        stable_defn = CorrelationDefinition(
            key=CorrelationKey(correlation_id="test", version="1.0.0"),
            name="Stable",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
            geometry=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
            envelope=ApplicabilityEnvelope(),
            source=BibliographicSource(source_id="s", title="T", publication="P", year=2020),
        )
        from hexagent.correlations.registry import _version_sort_key

        assert _version_sort_key(pre_defn) < _version_sort_key(stable_defn)

    def test_version_sorting_order(self) -> None:
        """1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.2 < 1.0.0-alpha.10 < 1.0.0-beta < 1.0.0"""
        from hexagent.correlations.models import CorrelationDefinition
        from hexagent.correlations.registry import _version_sort_key

        versions = [
            "1.0.0-beta",
            "1.0.0",
            "1.0.0-alpha",
            "1.0.0-alpha.10",
            "1.0.0-alpha.1",
            "1.0.0-alpha.2",
        ]
        defns = []
        for v in versions:
            defns.append(
                CorrelationDefinition(
                    key=CorrelationKey(correlation_id="test", version=v),
                    name=v,
                    purpose=CorrelationPurpose.heat_transfer_coefficient,
                    description="Test",
                    geometry=frozenset({GeometryType.generic}),
                    phase_regimes=frozenset({PhaseRegime.generic}),
                    envelope=ApplicabilityEnvelope(),
                    source=BibliographicSource(
                        source_id="s", title="T", publication="P", year=2020
                    ),
                )
            )
        sorted_defns = sorted(defns, key=_version_sort_key)
        sorted_versions = [d.key.version for d in sorted_defns]
        assert sorted_versions == [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.2",
            "1.0.0-alpha.10",
            "1.0.0-beta",
            "1.0.0",
        ]


# ---------------------------------------------------------------------------
# CorrelationKey tests
# ---------------------------------------------------------------------------


class TestCorrelationKey:
    def test_valid_key(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc.tube", version="1.0.0")
        assert key.correlation_id == "fixture.htc.tube"
        assert key.version == "1.0.0"

    def test_valid_prerelease_version(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0-alpha.1")
        assert key.version == "1.0.0-alpha.1"

    def test_valid_id_with_hyphens(self) -> None:
        key = CorrelationKey(correlation_id="fixture-htc", version="2.1.3")
        assert key.correlation_id == "fixture-htc"

    def test_valid_id_with_underscores(self) -> None:
        key = CorrelationKey(correlation_id="fixture_htc", version="0.0.1")
        assert key.correlation_id == "fixture_htc"

    def test_invalid_id_uppercase(self) -> None:
        with pytest.raises(ValidationError, match="correlation_id"):
            CorrelationKey(correlation_id="Fixture.HTC", version="1.0.0")

    def test_invalid_id_empty(self) -> None:
        with pytest.raises(ValidationError, match="correlation_id"):
            CorrelationKey(correlation_id="", version="1.0.0")

    def test_invalid_id_special_chars(self) -> None:
        with pytest.raises(ValidationError, match="correlation_id"):
            CorrelationKey(correlation_id="fixture@htc", version="1.0.0")

    def test_invalid_version_no_patch(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            CorrelationKey(correlation_id="fixture.htc", version="1.0")

    def test_invalid_version_empty(self) -> None:
        with pytest.raises(ValidationError, match="version"):
            CorrelationKey(correlation_id="fixture.htc", version="")

    def test_invalid_version_trailing_junk(self) -> None:
        """Item 2: Trailing junk is rejected."""
        with pytest.raises(ValidationError, match="version"):
            CorrelationKey(correlation_id="fixture.htc", version="1.0.0junk")

    def test_invalid_version_build_metadata(self) -> None:
        """Item 2: Build metadata is rejected."""
        with pytest.raises(ValidationError, match="version"):
            CorrelationKey(correlation_id="fixture.htc", version="1.0.0+build")

    def test_frozen(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises((ValueError, ValidationError)):
            key.correlation_id = "changed"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CorrelationKey(
                correlation_id="fixture.htc",
                version="1.0.0",
                extra_field="bad",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# NumericBound tests
# ---------------------------------------------------------------------------


class TestNumericBound:
    def test_valid_bound(self) -> None:
        bound = NumericBound(
            variable=ApplicabilityVariable.reynolds,
            minimum=100.0,
            maximum=100000.0,
        )
        assert bound.minimum == 100.0
        assert bound.maximum == 100000.0

    def test_min_less_than_max(self) -> None:
        with pytest.raises(ValidationError, match="minimum.*must be < maximum"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=100000.0,
                maximum=100.0,
            )

    def test_min_equal_max_rejected(self) -> None:
        with pytest.raises(ValidationError, match="minimum.*must be < maximum"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=100.0,
                maximum=100.0,
            )

    def test_recommended_within_absolute(self) -> None:
        with pytest.raises(ValidationError, match="recommended_minimum.*must be >= minimum"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=100.0,
                maximum=100000.0,
                recommended_minimum=50.0,
            )

    def test_recommended_max_within_absolute(self) -> None:
        with pytest.raises(ValidationError, match="recommended_maximum.*must be <= maximum"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=100.0,
                maximum=100000.0,
                recommended_maximum=200000.0,
            )

    def test_recommended_min_lte_max(self) -> None:
        """Item 3: recommended_minimum <= recommended_maximum."""
        with pytest.raises(
            ValidationError,
            match="recommended_minimum.*must be <= recommended_maximum",
        ):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=100.0,
                maximum=100000.0,
                recommended_minimum=50000.0,
                recommended_maximum=10000.0,
            )

    def test_tolerance_fraction_upper_bound(self) -> None:
        """Item 3: tolerance_fraction <= 1.0."""
        with pytest.raises(ValidationError, match="tolerance_fraction.*must be <= 1.0"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                tolerance_fraction=1.5,
            )

    def test_nan_rejected(self) -> None:
        with pytest.raises(ValidationError, match="NaN"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=float("nan"),
                maximum=100.0,
            )

    def test_inf_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Inf"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                minimum=0.0,
                maximum=float("inf"),
            )

    def test_negative_tolerance_rejected(self) -> None:
        with pytest.raises(ValidationError, match="tolerance_fraction.*must be >= 0"):
            NumericBound(
                variable=ApplicabilityVariable.reynolds,
                tolerance_fraction=-0.1,
            )

    def test_optional_bounds(self) -> None:
        bound = NumericBound(variable=ApplicabilityVariable.reynolds)
        assert bound.minimum is None
        assert bound.maximum is None

    def test_frozen(self) -> None:
        bound = NumericBound(variable=ApplicabilityVariable.reynolds, minimum=100.0)
        with pytest.raises((ValueError, ValidationError)):
            bound.minimum = 200.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BibliographicSource tests (Item 9: fictional names)
# ---------------------------------------------------------------------------


class TestBibliographicSource:
    def test_valid_source(self) -> None:
        src = BibliographicSource(
            source_id="src-001",
            title="Example Corp Internal Report 2024",
            publication="Fictional Engineering Journal",
            year=1930,
        )
        assert src.source_id == "src-001"
        assert src.year == 1930

    def test_year_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="year must be in range"):
            BibliographicSource(
                source_id="src-002",
                title="Future Paper",
                publication="Journal",
                year=2100,
            )

    def test_year_too_old(self) -> None:
        with pytest.raises(ValidationError, match="year must be in range"):
            BibliographicSource(
                source_id="src-003",
                title="Old Paper",
                publication="Journal",
                year=1800,
            )

    def test_valid_doi(self) -> None:
        src = BibliographicSource(
            source_id="src-004",
            title="Paper",
            publication="Journal",
            year=2020,
            doi="10.1000/xyz123",
        )
        assert src.doi == "10.1000/xyz123"

    def test_invalid_doi(self) -> None:
        with pytest.raises(ValidationError, match="DOI format"):
            BibliographicSource(
                source_id="src-005",
                title="Paper",
                publication="Journal",
                year=2020,
                doi="not-a-doi",
            )

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValidationError, match="title"):
            BibliographicSource(
                source_id="src-006",
                title="",
                publication="Journal",
                year=2020,
            )

    def test_frozen(self) -> None:
        src = BibliographicSource(
            source_id="src-007",
            title="Paper",
            publication="Journal",
            year=2020,
        )
        with pytest.raises((ValueError, ValidationError)):
            src.year = 2025  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UncertaintySpec tests (Item 9: fictional basis)
# ---------------------------------------------------------------------------


class TestUncertaintySpec:
    def test_valid_spec(self) -> None:
        spec = UncertaintySpec(basis="Fictional uncertainty analysis")
        assert spec.basis == "Fictional uncertainty analysis"
        assert spec.relative_uncertainty_fraction is None

    def test_relative_uncertainty_negative_rejected(self) -> None:
        with pytest.raises(ValidationError, match="relative_uncertainty_fraction.*must be >= 0"):
            UncertaintySpec(
                basis="test",
                relative_uncertainty_fraction=-0.1,
            )

    def test_confidence_level_out_of_range(self) -> None:
        with pytest.raises(ValidationError, match="confidence_level_fraction must be in"):
            UncertaintySpec(
                basis="test",
                confidence_level_fraction=0.0,
            )

    def test_confidence_level_above_one(self) -> None:
        with pytest.raises(ValidationError, match="confidence_level_fraction must be in"):
            UncertaintySpec(
                basis="test",
                confidence_level_fraction=1.5,
            )

    def test_valid_confidence(self) -> None:
        spec = UncertaintySpec(
            basis="test",
            confidence_level_fraction=0.95,
            relative_uncertainty_fraction=0.15,
        )
        assert spec.confidence_level_fraction == 0.95
        assert spec.relative_uncertainty_fraction == 0.15


# ---------------------------------------------------------------------------
# OutOfRangePolicy tests
# ---------------------------------------------------------------------------


class TestOutOfRangePolicy:
    def test_defaults(self) -> None:
        policy = OutOfRangePolicy()
        assert policy.absolute_violation == OutOfRangeAction.block
        assert policy.recommended_violation == OutOfRangeAction.warn
        assert policy.missing_input == OutOfRangeAction.block
        assert policy.incompatible_geometry == OutOfRangeAction.block
        assert policy.incompatible_phase == OutOfRangeAction.block

    def test_custom_policy(self) -> None:
        policy = OutOfRangePolicy(
            absolute_violation=OutOfRangeAction.warn,
            recommended_violation=OutOfRangeAction.allow_explicit_opt_in,
        )
        assert policy.absolute_violation == OutOfRangeAction.warn
        assert policy.recommended_violation == OutOfRangeAction.allow_explicit_opt_in


# ---------------------------------------------------------------------------
# ApplicabilityEnvelope tests (Item 3)
# ---------------------------------------------------------------------------


class TestApplicabilityEnvelope:
    def test_duplicate_bounds_rejected(self) -> None:
        """Item 3: Reject duplicate NumericBound.variable entries."""
        with pytest.raises(ValidationError, match="Duplicate NumericBound"):
            ApplicabilityEnvelope(
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=100.0,
                        maximum=10000.0,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=200.0,
                        maximum=20000.0,
                    ),
                ),
                required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            )

    def test_bound_without_required_rejected(self) -> None:
        """Item 3: Bounded variable must be in required_inputs."""
        with pytest.raises(ValidationError, match="has bounds but is not in required_inputs"):
            ApplicabilityEnvelope(
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=100.0,
                        maximum=10000.0,
                    ),
                ),
                required_inputs=frozenset(),
            )

    def test_bounds_sorted_canonical(self) -> None:
        """Item 3: Bounds are sorted by variable name."""
        env = ApplicabilityEnvelope(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.prandtl,
                    minimum=0.5,
                    maximum=100.0,
                ),
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=100.0,
                    maximum=10000.0,
                ),
            ),
            required_inputs=frozenset(
                {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
            ),
        )
        assert env.bounds[0].variable == ApplicabilityVariable.prandtl
        assert env.bounds[1].variable == ApplicabilityVariable.reynolds

    def test_generic_geometry_wildcard(self) -> None:
        """Item 3: generic geometry is valid."""
        env = ApplicabilityEnvelope(
            geometry_types=frozenset({GeometryType.generic}),
        )
        assert GeometryType.generic in env.geometry_types

    def test_generic_phase_wildcard(self) -> None:
        """Item 3: generic phase is valid."""
        env = ApplicabilityEnvelope(
            phase_regimes=frozenset({PhaseRegime.generic}),
        )
        assert PhaseRegime.generic in env.phase_regimes


# ---------------------------------------------------------------------------
# CorrelationDefinition tests
# ---------------------------------------------------------------------------


class TestCorrelationDefinition:
    def _make_definition(self) -> CorrelationDefinition:
        return CorrelationDefinition(
            key=CorrelationKey(
                correlation_id="fixture.htc.tube",
                version="1.0.0",
            ),
            name="Fixture HTC Tube",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="A fixture correlation for testing",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset({FlowRegime.turbulent}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=3000.0,
                        maximum=100000.0,
                        recommended_minimum=10000.0,
                        recommended_maximum=50000.0,
                    ),
                ),
                required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            ),
            source=BibliographicSource(
                source_id="src-fixture-001",
                title="Fictional Heat Transfer Correlation",
                publication="Fictional Journal",
                year=2020,
            ),
        )

    def test_create_definition(self) -> None:
        defn = self._make_definition()
        assert defn.key.correlation_id == "fixture.htc.tube"
        assert defn.name == "Fixture HTC Tube"
        assert defn.schema_version == "1.0"

    def test_frozen(self) -> None:
        defn = self._make_definition()
        with pytest.raises((ValueError, ValidationError)):
            defn.name = "Changed"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="Test",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                envelope=ApplicabilityEnvelope(),
                source=BibliographicSource(
                    source_id="s",
                    title="T",
                    publication="P",
                    year=2020,
                ),
                extra_field="bad",  # type: ignore[call-arg]
            )

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="name"):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                envelope=ApplicabilityEnvelope(),
                source=BibliographicSource(
                    source_id="s",
                    title="T",
                    publication="P",
                    year=2020,
                ),
            )

    def test_geometry_must_match_envelope(self) -> None:
        """Item 3: Definition geometry must equal envelope geometry."""
        with pytest.raises(ValidationError, match="geometry must equal"):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="Test",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                envelope=ApplicabilityEnvelope(
                    geometry_types=frozenset({GeometryType.annulus}),
                    phase_regimes=frozenset({PhaseRegime.generic}),
                ),
                source=BibliographicSource(source_id="s", title="T", publication="P", year=2020),
            )

    def test_phase_regimes_must_match_envelope(self) -> None:
        """Item 3: Definition phase_regimes must equal envelope phase_regimes."""
        with pytest.raises(ValidationError, match="phase_regimes must equal"):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="Test",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                envelope=ApplicabilityEnvelope(
                    geometry_types=frozenset({GeometryType.generic}),
                    phase_regimes=frozenset({PhaseRegime.boiling}),
                ),
                source=BibliographicSource(source_id="s", title="T", publication="P", year=2020),
            )

    def test_implementation_ref_required_for_implemented(self) -> None:
        """Item 7: implementation_ref required for implemented/validated."""
        with pytest.raises(ValidationError, match="implementation_ref is required"):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="Test",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                envelope=ApplicabilityEnvelope(),
                source=BibliographicSource(source_id="s", title="T", publication="P", year=2020),
                implementation_status=CorrelationImplementationStatus.implemented,
            )

    def test_self_supersession_rejected(self) -> None:
        """Item 7: Self-supersession is rejected."""
        with pytest.raises(ValidationError, match="cannot supersede itself"):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="Test",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                envelope=ApplicabilityEnvelope(),
                source=BibliographicSource(source_id="s", title="T", publication="P", year=2020),
                supersedes=CorrelationKey(correlation_id="fixture", version="1.0.0"),
            )

    def test_validated_requires_source_verification(self) -> None:
        """Item 7: Validated requires source.verification_status >= primary_source_checked."""
        with pytest.raises(ValidationError, match="primary_source_checked"):
            CorrelationDefinition(
                key=CorrelationKey(correlation_id="fixture", version="1.0.0"),
                name="Test",
                purpose=CorrelationPurpose.heat_transfer_coefficient,
                description="Test",
                geometry=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                envelope=ApplicabilityEnvelope(),
                source=BibliographicSource(
                    source_id="s",
                    title="T",
                    publication="P",
                    year=2020,
                    verification_status=SourceVerificationStatus.secondary_source,
                ),
                implementation_status=CorrelationImplementationStatus.validated,
                implementation_ref="impl-ref",
            )


# ---------------------------------------------------------------------------
# CorrelationApplicabilityInput tests
# ---------------------------------------------------------------------------


class TestCorrelationApplicabilityInput:
    def test_valid_input(self) -> None:
        inp = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        assert inp.geometry == GeometryType.circular_tube
        assert inp.allow_extrapolation is False

    def test_values_as_tuple_of_pairs(self) -> None:
        """Item 5: Values can be provided as tuple of pairs."""
        inp = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values=((ApplicabilityVariable.reynolds, 25000.0),),
        )
        assert len(inp.values) == 1
        assert inp.values[0] == (ApplicabilityVariable.reynolds, 25000.0)

    def test_values_sorted_deduplicated(self) -> None:
        """Item 5: Values are sorted and deduplicated."""
        inp = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.prandtl: 5.0, ApplicabilityVariable.reynolds: 25000.0},
        )
        assert inp.values[0][0] == ApplicabilityVariable.prandtl
        assert inp.values[1][0] == ApplicabilityVariable.reynolds

    def test_nan_rejected(self) -> None:
        """Item 5: NaN values are rejected."""
        with pytest.raises(ValidationError, match="NaN"):
            CorrelationApplicabilityInput(
                geometry=GeometryType.circular_tube,
                phase_regime=PhaseRegime.single_phase_liquid,
                flow_regime=FlowRegime.turbulent,
                values={ApplicabilityVariable.reynolds: float("nan")},
            )

    def test_inf_rejected(self) -> None:
        """Item 5: Inf values are rejected."""
        with pytest.raises(ValidationError, match="Inf"):
            CorrelationApplicabilityInput(
                geometry=GeometryType.circular_tube,
                phase_regime=PhaseRegime.single_phase_liquid,
                flow_regime=FlowRegime.turbulent,
                values={ApplicabilityVariable.reynolds: float("inf")},
            )

    def test_duplicate_variable_rejected(self) -> None:
        """Item 5: Duplicate variables are rejected."""
        with pytest.raises(ValidationError, match="Duplicate variable"):
            CorrelationApplicabilityInput(
                geometry=GeometryType.circular_tube,
                phase_regime=PhaseRegime.single_phase_liquid,
                flow_regime=FlowRegime.turbulent,
                values=[
                    (ApplicabilityVariable.reynolds, 25000.0),
                    (ApplicabilityVariable.reynolds, 30000.0),
                ],
            )

    def test_frozen(self) -> None:
        inp = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
        )
        with pytest.raises((ValueError, ValidationError)):
            inp.geometry = GeometryType.annulus  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ApplicabilityAssessment tests
# ---------------------------------------------------------------------------


class TestApplicabilityAssessment:
    def test_valid_assessment(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        assessment = ApplicabilityAssessment(
            correlation_key=key,
            status=ApplicabilityStatus.applicable,
            allows_evaluation=True,
        )
        assert assessment.status == ApplicabilityStatus.applicable
        assert assessment.allows_evaluation is True
        assert assessment.schema_version == "1.0"

    def test_applicable_with_blockers_rejected(self) -> None:
        """Item 5: applicable status must not have blockers."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        blocker = EngineeringMessage(
            code=ErrorCode.CORRELATION_ABSOLUTE_RANGE_EXCEEDED,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="test blocker",
        )
        with pytest.raises(ValidationError, match="applicable status must not have blockers"):
            ApplicabilityAssessment(
                correlation_key=key,
                status=ApplicabilityStatus.applicable,
                blockers=(blocker,),
                allows_evaluation=True,
            )

    def test_frozen(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        assessment = ApplicabilityAssessment(
            correlation_key=key,
            status=ApplicabilityStatus.applicable,
        )
        with pytest.raises((ValueError, ValidationError)):
            assessment.status = ApplicabilityStatus.absolute_range_exceeded  # type: ignore[misc]


# ---------------------------------------------------------------------------
# VariableAssessment tests
# ---------------------------------------------------------------------------


class TestVariableAssessment:
    def test_valid(self) -> None:
        va = VariableAssessment(
            variable=ApplicabilityVariable.reynolds,
            supplied_value=25000.0,
            absolute_minimum=3000.0,
            absolute_maximum=100000.0,
            status=VariableApplicabilityStatus.applicable,
        )
        assert va.supplied_value == 25000.0
        assert va.status == VariableApplicabilityStatus.applicable

    def test_missing_value(self) -> None:
        va = VariableAssessment(
            variable=ApplicabilityVariable.reynolds,
            status=VariableApplicabilityStatus.missing,
        )
        assert va.supplied_value is None
