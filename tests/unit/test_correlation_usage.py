"""Tests for CorrelationUsageRecord and provenance conversion."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hexagent.correlations.models import (
    ApplicabilityStatus,
    ApplicabilityVariable,
    CorrelationKey,
    FlowRegime,
    GeometryType,
    OutOfRangePolicy,
    PhaseRegime,
    UncertaintySpec,
)
from hexagent.correlations.usage import CorrelationUsageRecord
from hexagent.domain.provenance import ProvenanceNode, ProvenanceNodeType

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
        from hexagent.correlations.models import (
            ApplicabilityAssessment,
            CorrelationApplicabilityInput,
            FlowRegime,
            GeometryType,
            PhaseRegime,
            compute_assessment_hash,
        )

        defn, _ = self._make_definition_and_assessment()
        assessment_hash = compute_assessment_hash(
            definition_hash=defn.definition_hash,
            correlation_key=defn.key,
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
            input_values=(),
            status=ApplicabilityStatus.explicit_extrapolation,
            variable_results=(),
            warnings=(),
            blockers=(),
            policy=OutOfRangePolicy(),
            allow_extrapolation=True,
        )
        assessment = ApplicabilityAssessment(
            correlation_key=defn.key,
            status=ApplicabilityStatus.explicit_extrapolation,
            assessment_hash=assessment_hash,
        )
        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.generic,
            phase_regime=PhaseRegime.generic,
            flow_regime=FlowRegime.not_applicable,
            allow_extrapolation=True,
        )
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
