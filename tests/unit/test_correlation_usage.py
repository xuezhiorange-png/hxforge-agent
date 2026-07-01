"""Tests for CorrelationUsageRecord and provenance conversion."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    ApplicabilityVariable,
    CorrelationApplicabilityInput,
    CorrelationKey,
    FlowRegime,
    GeometryType,
    OutOfRangePolicy,
    PhaseRegime,
    UncertaintySpec,
)
from hexagent.correlations.usage import CorrelationUsageRecord
from hexagent.domain.provenance import ProvenanceNode, ProvenanceNodeType

pytestmark = pytest.mark.pure

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64
_HASH_C = "sha256:" + "c" * 64
_HASH_D = "sha256:" + "d" * 64
_HASH_E = "sha256:" + "e" * 64
_HASH_F = "sha256:" + "f" * 64

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCorrelationUsageRecord:
    """Usage record construction and provenance conversion."""

    def test_create_record(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(
                (ApplicabilityVariable.reynolds, 25000.0),
                (ApplicabilityVariable.prandtl, 5.0),
            ),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        assert record.correlation_key == key
        assert record.applicability_status == ApplicabilityStatus.applicable
        assert record.extrapolation_used is False
        assert record.schema_version == "1.0"

    def test_frozen(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        with pytest.raises((ValueError, ValidationError)):
            record.source_id = "changed"  # type: ignore[misc]

    def test_to_provenance_node(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        node = record.to_provenance_node()
        assert isinstance(node, ProvenanceNode)
        assert node.node_type == ProvenanceNodeType.CORRELATION
        assert "fixture.htc" in node.label
        assert "v1.0.0" in node.label
        assert node.payload_hash.startswith("sha256:")
        # Check metadata
        meta_dict = dict(node.metadata)
        assert meta_dict["correlation_id"] == "fixture.htc"
        assert meta_dict["correlation_version"] == "1.0.0"
        assert meta_dict["definition_hash"] == _HASH_A
        assert meta_dict["assessment_hash"] == _HASH_B
        assert meta_dict["source_id"] == "src-001"
        assert meta_dict["applicability_status"] == "applicable"
        assert meta_dict["extrapolation_used"] is False

    def test_to_provenance_node_with_uncertainty(self) -> None:
        key = CorrelationKey(correlation_id="fixture.ff", version="2.0.0")
        uncertainty = UncertaintySpec(
            basis="Test uncertainty",
            relative_uncertainty_fraction=0.15,
            confidence_level_fraction=0.95,
        )
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_C,
            source_id="src-002",
            applicability_status=ApplicabilityStatus.recommended_range_exceeded,
            input_values=((ApplicabilityVariable.reynolds, 100000.0),),
            assessment_hash=_HASH_D,
            extrapolation_used=False,
            uncertainty=uncertainty,
        )
        node = record.to_provenance_node()
        meta_dict = dict(node.metadata)
        assert meta_dict["uncertainty_basis"] == "Test uncertainty"
        assert meta_dict["applicability_status"] == "recommended_range_exceeded"

    def test_to_provenance_node_with_extrapolation(self) -> None:
        key = CorrelationKey(correlation_id="fixture.pd", version="1.2.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_E,
            source_id="src-003",
            applicability_status=ApplicabilityStatus.explicit_extrapolation,
            input_values=((ApplicabilityVariable.reynolds, 500000.0),),
            assessment_hash=_HASH_F,
            extrapolation_used=True,
        )
        node = record.to_provenance_node()
        meta_dict = dict(node.metadata)
        assert meta_dict["extrapolation_used"] is True

    def test_to_provenance_node_deterministic(self) -> None:
        """Item 8: Deterministic node_id from usage_hash, same for identical records."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        node1 = record.to_provenance_node()
        node2 = record.to_provenance_node()
        assert node1.node_id == node2.node_id  # Deterministic, not random

    def test_usage_hash_deterministic(self) -> None:
        """Item 8: usage_hash is deterministic for same record."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        assert record.usage_hash == record.usage_hash
        assert record.usage_hash.startswith("sha256:")

    def test_usage_hash_includes_uncertainty(self) -> None:
        """Item 8: usage_hash includes uncertainty."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record1 = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        record2 = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
            uncertainty=UncertaintySpec(basis="test", relative_uncertainty_fraction=0.15),
        )
        assert record1.usage_hash != record2.usage_hash

    def test_input_values_sorted(self) -> None:
        """Item 8: Input values are stored sorted."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(
                (ApplicabilityVariable.prandtl, 5.0),
                (ApplicabilityVariable.reynolds, 25000.0),
            ),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
        )
        # Values should be sorted by variable name
        assert record.input_values[0][0] == ApplicabilityVariable.prandtl
        assert record.input_values[1][0] == ApplicabilityVariable.reynolds

    def test_extrapolation_consistency(self) -> None:
        """Item 8: explicit_extrapolation requires extrapolation_used=True."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError, match="extrapolation_used must be True"):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash=_HASH_A,
                source_id="src-001",
                applicability_status=ApplicabilityStatus.explicit_extrapolation,
                input_values=((ApplicabilityVariable.reynolds, 25000.0),),
                assessment_hash=_HASH_B,
                extrapolation_used=False,
            )

    def test_definition_hash_format_validation(self) -> None:
        """Item 8: definition_hash format must be sha256:<64-hex>."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError, match="definition_hash"):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash="not-a-hash",
                source_id="src-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=(),
                assessment_hash=_HASH_B,
                extrapolation_used=False,
            )

    def test_assessment_hash_format_validation(self) -> None:
        """Item 8: assessment_hash format must be sha256:<64-hex>."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError, match="assessment_hash"):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash=_HASH_A,
                source_id="src-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=(),
                assessment_hash="not-a-hash",
                extrapolation_used=False,
            )

    def test_extra_forbidden(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash=_HASH_A,
                source_id="src-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=((ApplicabilityVariable.reynolds, 25000.0),),
                assessment_hash=_HASH_B,
                extrapolation_used=False,
                extra_field="bad",  # type: ignore[call-arg]
            )

    def test_nan_rejected_in_input_values(self) -> None:
        """Item 8: NaN values rejected."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError, match="NaN"):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash=_HASH_A,
                source_id="src-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=((ApplicabilityVariable.reynolds, float("nan")),),
                assessment_hash=_HASH_B,
                extrapolation_used=False,
            )

    def test_inf_rejected_in_input_values(self) -> None:
        """Item 8: Inf values rejected."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError, match="Inf"):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash=_HASH_A,
                source_id="src-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=((ApplicabilityVariable.reynolds, float("inf")),),
                assessment_hash=_HASH_B,
                extrapolation_used=False,
            )

    # -------------------------------------------------------------------------
    # Item 5: usage_hash includes source_id from UncertaintySpec
    # -------------------------------------------------------------------------

    def test_usage_hash_includes_uncertainty_source_id(self) -> None:
        """Item 5: usage_hash includes uncertainty.source_id."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record1 = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
            uncertainty=UncertaintySpec(basis="test", source_id="unc-src-1"),
        )
        record2 = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
            uncertainty=UncertaintySpec(basis="test", source_id="unc-src-2"),
        )
        assert record1.usage_hash != record2.usage_hash

    # -------------------------------------------------------------------------
    # Item 5: Bidirectional extrapolation consistency
    # -------------------------------------------------------------------------

    def test_extrapolation_used_with_non_extrapolation_status_rejected(self) -> None:
        """Item 5: extrapolation_used=True + non-extrapolation status → rejected."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError, match="extrapolation_used=True requires"):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash=_HASH_A,
                source_id="src-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=((ApplicabilityVariable.reynolds, 25000.0),),
                assessment_hash=_HASH_B,
                extrapolation_used=True,
            )

    # -------------------------------------------------------------------------
    # Item 5: Provenance metadata includes uncertainty source_id
    # -------------------------------------------------------------------------

    def test_provenance_includes_uncertainty_source_id(self) -> None:
        """Item 5: Provenance metadata includes uncertainty source_id."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        uncertainty = UncertaintySpec(
            basis="Test uncertainty",
            relative_uncertainty_fraction=0.15,
            confidence_level_fraction=0.95,
            source_id="unc-001",
        )
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash=_HASH_A,
            source_id="src-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=_HASH_B,
            extrapolation_used=False,
            uncertainty=uncertainty,
        )
        node = record.to_provenance_node()
        meta_dict = dict(node.metadata)
        assert meta_dict["uncertainty_basis"] == "Test uncertainty"
        assert meta_dict["uncertainty_source_id"] == "unc-001"


# ---------------------------------------------------------------------------
# Review-04: UsageRecordFactory
# ---------------------------------------------------------------------------


class TestUsageRecordFactory:
    """Test the CorrelationUsageRecord.create() factory method."""

    @staticmethod
    def _make_definition_and_assessment(
        *,
        key_id: str = "fixture.htc",
        version: str = "1.0.0",
    ):
        """Create a matched definition + assessment for factory tests."""
        from hexagent.correlations.models import (
            ApplicabilityAssessment,
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationKey,
            CorrelationPurpose,
            GeometryType,
            PhaseRegime,
            compute_assessment_hash,
        )

        defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id=key_id, version=version),
            name=f"Fixture {key_id} v{version}",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
            geometry=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
            envelope=ApplicabilityEnvelope(),
            source=BibliographicSource(
                source_id="src-001",
                title="Test",
                publication="Test Journal",
                year=2020,
            ),
        )

        assessment_hash = compute_assessment_hash(
            definition_hash=defn.definition_hash,
            correlation_key=defn.key,
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
            input_values=(),
            status=ApplicabilityStatus.applicable,
            variable_results=(),
            warnings=(),
            blockers=(),
            policy=OutOfRangePolicy(),
            allow_extrapolation=False,
        )

        assessment = ApplicabilityAssessment(
            correlation_key=defn.key,
            status=ApplicabilityStatus.applicable,
            assessment_hash=assessment_hash,
        )

        return defn, assessment

    def test_factory_creates_valid_record(self) -> None:
        from hexagent.correlations.models import (
            CorrelationApplicabilityInput,
        )

        defn, assessment = self._make_definition_and_assessment()
        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
        )
        record = CorrelationUsageRecord.create(defn, assessment, inputs)
        assert record.correlation_key == defn.key
        assert record.definition_hash == defn.definition_hash
        assert record.assessment_hash == assessment.assessment_hash
        assert record.applicability_status == ApplicabilityStatus.applicable
        assert record.extrapolation_used is False

    def test_factory_rejects_key_mismatch(self) -> None:
        from hexagent.correlations.models import (
            ApplicabilityAssessment,
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationApplicabilityInput,
            CorrelationDefinition,
            CorrelationKey,
            CorrelationPurpose,
            GeometryType,
            PhaseRegime,
            compute_assessment_hash,
        )

        defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="fixture.a", version="1.0.0"),
            name="A",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
            geometry=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
            envelope=ApplicabilityEnvelope(),
            source=BibliographicSource(
                source_id="src-001",
                title="Test",
                publication="Test Journal",
                year=2020,
            ),
        )

        other_key = CorrelationKey(correlation_id="fixture.b", version="1.0.0")
        a_hash = compute_assessment_hash(
            definition_hash=defn.definition_hash,
            correlation_key=other_key,
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
            input_values=(),
            status=ApplicabilityStatus.applicable,
            variable_results=(),
            warnings=(),
            blockers=(),
            policy=OutOfRangePolicy(),
            allow_extrapolation=False,
        )
        assessment = ApplicabilityAssessment(
            correlation_key=other_key,  # mismatch
            status=ApplicabilityStatus.applicable,
            assessment_hash=a_hash,
        )
        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
        )
        with pytest.raises(ValueError, match="correlation_key does not match"):
            CorrelationUsageRecord.create(defn, assessment, inputs)

    def test_factory_detects_extrapolation(self) -> None:
        """Factory correctly sets extrapolation_used when assessment has explicit_extrapolation."""
        from hexagent.correlations.applicability import assess_applicability
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationApplicabilityInput,
            CorrelationDefinition,
            CorrelationKey,
            CorrelationPurpose,
            GeometryType,
            NumericBound,
            OutOfRangeAction,
            OutOfRangePolicy,
            PhaseRegime,
        )

        # Definition with allow_explicit_opt_in policy
        defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="fixture.extrap", version="1.0.0"),
            name="Fixture Extrapolation",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
            geometry=frozenset({GeometryType.generic}),
            phase_regimes=frozenset({PhaseRegime.generic}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.generic}),
                phase_regimes=frozenset({PhaseRegime.generic}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=3000.0,
                        maximum=100000.0,
                    ),
                ),
                required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            ),
            source=BibliographicSource(
                source_id="src-001",
                title="Test",
                publication="Test Journal",
                year=2020,
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.allow_explicit_opt_in,
            ),
        )

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
            values={ApplicabilityVariable.reynolds: 150000.0},  # above absolute max
            allow_extrapolation=True,
        )

        # Get the real assessment from the engine
        assessment = assess_applicability(defn, inputs)
        assert assessment.status == ApplicabilityStatus.explicit_extrapolation

        record = CorrelationUsageRecord.create(defn, assessment, inputs)
        assert record.extrapolation_used is True

    def test_deterministic_node_ids(self) -> None:
        from hexagent.correlations.models import CorrelationApplicabilityInput

        defn, assessment = self._make_definition_and_assessment()
        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
        )
        record = CorrelationUsageRecord.create(defn, assessment, inputs)
        node1 = record.to_provenance_node()
        node2 = record.to_provenance_node()
        assert node1.node_id == node2.node_id

    def test_provenance_node_uses_uuid5(self) -> None:
        """Provenance node uses uuid5 (version == 5)."""
        from hexagent.correlations.models import CorrelationApplicabilityInput

        defn, assessment = self._make_definition_and_assessment()
        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
        )
        record = CorrelationUsageRecord.create(defn, assessment, inputs)
        node = record.to_provenance_node()
        assert node.node_id.version == 5


# ---------------------------------------------------------------------------
# Review-05: Cross-validation in CorrelationUsageRecord.create()
# ---------------------------------------------------------------------------


class TestUsageRecordCrossValidation:
    """The factory recomputes assess_applicability and cross-validates."""

    @staticmethod
    def _build_defn_and_inputs(
        *,
        key_id: str = "fixture.htc",
        geometry: GeometryType = GeometryType.circular_tube,
        phase: PhaseRegime = PhaseRegime.single_phase_liquid,
        flow: FlowRegime = FlowRegime.turbulent,
        bounds: tuple | None = None,
        policy: OutOfRangePolicy | None = None,
        values: dict | None = None,
        allow_extrapolation: bool = False,
    ):
        """Build a definition + inputs for cross-validation tests."""
        from hexagent.correlations.applicability import assess_applicability
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationApplicabilityInput,
            CorrelationDefinition,
            CorrelationKey,
            CorrelationPurpose,
        )

        gt = frozenset({geometry})
        pr = frozenset({phase})
        fr = frozenset({flow})
        bnds = bounds or ()
        ri = frozenset({b.variable for b in bnds}) if bnds else frozenset()

        defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id=key_id, version="1.0.0"),
            name=f"Fixture {key_id}",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
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
                title="Test",
                publication="Test Journal",
                year=2020,
            ),
            out_of_range_policy=policy or OutOfRangePolicy(),
        )

        inputs = CorrelationApplicabilityInput(
            geometry=geometry,
            phase_regime=phase,
            flow_regime=flow,
            values=values or {},
            allow_extrapolation=allow_extrapolation,
        )

        assessment = assess_applicability(defn, inputs)
        return defn, inputs, assessment

    def test_valid_definition_assessment_inputs_succeeds(self) -> None:
        """Valid definition + matching assessment + inputs → record created."""
        defn, inputs, assessment = self._build_defn_and_inputs(
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        record = CorrelationUsageRecord.create(defn, assessment, inputs)
        assert record.correlation_key == defn.key
        assert record.applicability_status == assessment.status

    def test_forged_assessment_hash_rejected(self) -> None:
        """Forged assessment_hash does not match recomputed → rejected."""

        defn, inputs, assessment = self._build_defn_and_inputs(
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        # Create a forged assessment with a different hash
        forged = ApplicabilityAssessment(
            correlation_key=assessment.correlation_key,
            status=assessment.status,
            assessment_hash="sha256:" + "f" * 64,  # forged hash
        )
        with pytest.raises(ValueError, match="assessment_hash does not match"):
            CorrelationUsageRecord.create(defn, forged, inputs)

    def test_forged_status_rejected(self) -> None:
        """Forged status does not match recomputed → rejected."""
        defn, inputs, assessment = self._build_defn_and_inputs(
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        # Create a forged assessment with a different status
        forged = ApplicabilityAssessment(
            correlation_key=assessment.correlation_key,
            status=ApplicabilityStatus.absolute_range_exceeded,  # forged
            assessment_hash=assessment.assessment_hash,
        )
        with pytest.raises(ValueError, match="assessment.status does not match"):
            CorrelationUsageRecord.create(defn, forged, inputs)

    def test_forged_blockers_rejected(self) -> None:
        """Forged blockers do not match recomputed → rejected."""
        from hexagent.correlations.models import NumericBound

        # Use inputs that produce a blocked assessment
        defn, inputs, assessment = self._build_defn_and_inputs(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            values={ApplicabilityVariable.reynolds: 150000.0},  # above max → blocker
        )
        assert len(assessment.blockers) >= 1  # real assessment has blockers
        # Create a forged assessment with matching status/hash/variable_results
        # but EMPTY blockers — the blocker check should catch this
        forged = ApplicabilityAssessment(
            correlation_key=assessment.correlation_key,
            status=assessment.status,
            assessment_hash=assessment.assessment_hash,
            variable_results=assessment.variable_results,  # match
            blockers=(),  # forged: stripped all blockers
        )
        with pytest.raises(ValueError, match="assessment.blockers do not match expected"):
            CorrelationUsageRecord.create(defn, forged, inputs)

    def test_different_inputs_rejected(self) -> None:
        """Same key but different inputs → recomputed assessment differs → rejected."""
        from hexagent.correlations.models import NumericBound

        defn, inputs_b, assessment_b = self._build_defn_and_inputs(
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=3000.0,
                    maximum=100000.0,
                ),
            ),
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        # Use assessment from correct inputs with wrong inputs
        wrong_inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 150000.0},  # different
        )
        with pytest.raises(ValueError, match="does not match"):
            CorrelationUsageRecord.create(defn, assessment_b, wrong_inputs)

    def test_different_definition_policy_rejected(self) -> None:
        """Same key but different policy → recomputed assessment differs → rejected."""
        from hexagent.correlations.applicability import assess_applicability
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationApplicabilityInput,
            CorrelationDefinition,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            OutOfRangeAction,
            OutOfRangePolicy,
        )

        # Definition with block policy
        defn_block = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="fixture.policy", version="1.0.0"),
            name="Fixture Policy",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
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
                    ),
                ),
                required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            ),
            source=BibliographicSource(
                source_id="src-001",
                title="Test",
                publication="Test Journal",
                year=2020,
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.block,
            ),
        )

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 150000.0},
        )

        # Get assessment from block policy
        assessment_block = assess_applicability(defn_block, inputs)
        assert assessment_block.status == ApplicabilityStatus.absolute_range_exceeded

        # Now create a different definition with warn policy
        defn_warn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="fixture.warn", version="1.0.0"),
            name="Fixture Warn",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Test",
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
                    ),
                ),
                required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            ),
            source=BibliographicSource(
                source_id="src-002",
                title="Test Warn",
                publication="Test Journal",
                year=2020,
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.warn,
            ),
        )

        # Try to use assessment from block-policy defn with warn-policy defn
        # The factory recomputes using defn_warn, which produces warnings not blockers
        # assessment_block has blockers → mismatch
        with pytest.raises(ValueError, match="does not match"):
            CorrelationUsageRecord.create(defn_warn, assessment_block, inputs)
