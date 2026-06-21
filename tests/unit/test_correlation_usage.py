"""Tests for CorrelationUsageRecord and provenance conversion."""

from __future__ import annotations

import pytest

from hexagent.correlations.models import (
    ApplicabilityStatus,
    CorrelationKey,
    UncertaintySpec,
)
from hexagent.correlations.usage import CorrelationUsageRecord
from hexagent.domain.provenance import ProvenanceNode, ProvenanceNodeType

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCorrelationUsageRecord:
    """Usage record construction and provenance conversion."""

    def test_create_record(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash="sha256:" + "a" * 64,
            source_id="run-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(("reynolds", 25000.0), ("prandtl", 5.0)),
            assessment_hash="sha256:" + "b" * 64,
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
            definition_hash="sha256:" + "a" * 64,
            source_id="run-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(("reynolds", 25000.0),),
            assessment_hash="sha256:" + "b" * 64,
            extrapolation_used=False,
        )
        with pytest.raises((ValueError, ValidationError)):
            record.source_id = "changed"  # type: ignore[misc]

    def test_to_provenance_node(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash="sha256:" + "a" * 64,
            source_id="run-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(("reynolds", 25000.0),),
            assessment_hash="sha256:" + "b" * 64,
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

    def test_to_provenance_node_with_uncertainty(self) -> None:
        key = CorrelationKey(correlation_id="fixture.ff", version="2.0.0")
        uncertainty = UncertaintySpec(
            basis="Test uncertainty",
            relative_uncertainty_fraction=0.15,
            confidence_level_fraction=0.95,
        )
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash="sha256:" + "c" * 64,
            source_id="run-002",
            applicability_status=ApplicabilityStatus.recommended_range_exceeded,
            input_values=(("reynolds", 100000.0),),
            assessment_hash="sha256:" + "d" * 64,
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
            definition_hash="sha256:" + "e" * 64,
            source_id="run-003",
            applicability_status=ApplicabilityStatus.explicit_extrapolation,
            input_values=(("reynolds", 500000.0),),
            assessment_hash="sha256:" + "f" * 64,
            extrapolation_used=True,
        )
        node = record.to_provenance_node()
        meta_dict = dict(node.metadata)
        assert meta_dict["extrapolation_used"] is True

    def test_to_provenance_node_unique_ids(self) -> None:
        """Each call to to_provenance_node produces a unique node_id."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash="sha256:" + "a" * 64,
            source_id="run-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(("reynolds", 25000.0),),
            assessment_hash="sha256:" + "b" * 64,
            extrapolation_used=False,
        )
        node1 = record.to_provenance_node()
        node2 = record.to_provenance_node()
        assert node1.node_id != node2.node_id

    def test_extra_forbidden(self) -> None:
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        with pytest.raises(ValidationError):
            CorrelationUsageRecord(
                correlation_key=key,
                definition_hash="sha256:" + "a" * 64,
                source_id="run-001",
                applicability_status=ApplicabilityStatus.applicable,
                input_values=(("reynolds", 25000.0),),
                assessment_hash="sha256:" + "b" * 64,
                extrapolation_used=False,
                extra_field="bad",  # type: ignore[call-arg]
            )

    def test_input_values_sorted_tuple(self) -> None:
        """Input values are stored as a tuple of (name, value) pairs."""
        key = CorrelationKey(correlation_id="fixture.htc", version="1.0.0")
        record = CorrelationUsageRecord(
            correlation_key=key,
            definition_hash="sha256:" + "a" * 64,
            source_id="run-001",
            applicability_status=ApplicabilityStatus.applicable,
            input_values=(("prandtl", 5.0), ("reynolds", 25000.0)),
            assessment_hash="sha256:" + "b" * 64,
            extrapolation_used=False,
        )
        assert record.input_values == (("prandtl", 5.0), ("reynolds", 25000.0))


# Avoid import error for ValidationError
from pydantic import ValidationError  # noqa: E402
