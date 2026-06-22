"""Integration tests for correlation registry workflow.

End-to-end scenarios: register → get → assess → use → provenance.
"""

from __future__ import annotations

from hexagent.correlations.models import (
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
    PhaseRegime,
    SourceVerificationStatus,
    UncertaintySpec,
)
from hexagent.correlations.registry import InMemoryCorrelationRegistry
from hexagent.correlations.usage import CorrelationUsageRecord
from hexagent.domain.provenance import ProvenanceNodeType

# ---------------------------------------------------------------------------
# Fixture definitions — fictional, not real engineering formulas
# ---------------------------------------------------------------------------


def _fixture_htc_v1() -> CorrelationDefinition:
    """Fixture: heat transfer coefficient correlation v1.0.0."""
    return CorrelationDefinition.create(
        key=CorrelationKey(correlation_id="fixture.htc.tube", version="1.0.0"),
        name="Fixture HTC Tube v1",
        purpose=CorrelationPurpose.heat_transfer_coefficient,
        description="Fictional tube-side HTC for integration testing",
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
                NumericBound(
                    variable=ApplicabilityVariable.prandtl,
                    minimum=0.6,
                    maximum=130.0,
                    recommended_minimum=0.7,
                    recommended_maximum=70.0,
                ),
            ),
            required_inputs=frozenset(
                {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
            ),
        ),
        source=BibliographicSource(
            source_id="src-fixture-htc-001",
            authors=("Example Corp Author A", "Example Corp Author B"),
            title="Fictional Heat Transfer in Tubes",
            publication="Fictional Journal of Thermal Engineering",
            year=2020,
            doi="10.1000/fixture.001",
            verification_status=SourceVerificationStatus.independently_verified,
            verification_note="Cross-validated against 3 independent sources",
        ),
        uncertainty=UncertaintySpec(
            relative_uncertainty_fraction=0.15,
            confidence_level_fraction=0.95,
            basis="Fixture uncertainty analysis",
        ),
        implementation_status=CorrelationImplementationStatus.metadata_only,
        tags=frozenset({"validated", "production", "fixture"}),
    )


def _fixture_htc_v2() -> CorrelationDefinition:
    """Fixture: HTC correlation v2.0.0 (supersedes v1)."""
    return CorrelationDefinition.create(
        key=CorrelationKey(correlation_id="fixture.htc.tube", version="2.0.0"),
        name="Fixture HTC Tube v2",
        purpose=CorrelationPurpose.heat_transfer_coefficient,
        description="Fictional tube-side HTC v2 with wider range",
        geometry=frozenset({GeometryType.circular_tube}),
        phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
        envelope=ApplicabilityEnvelope(
            geometry_types=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            flow_regimes=frozenset({FlowRegime.turbulent, FlowRegime.transitional}),
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=2000.0,
                    maximum=500000.0,
                    recommended_minimum=5000.0,
                    recommended_maximum=200000.0,
                ),
                NumericBound(
                    variable=ApplicabilityVariable.prandtl,
                    minimum=0.5,
                    maximum=200.0,
                    recommended_minimum=0.6,
                    recommended_maximum=100.0,
                ),
            ),
            required_inputs=frozenset(
                {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
            ),
        ),
        source=BibliographicSource(
            source_id="src-fixture-htc-002",
            authors=("Example Corp Author C",),
            title="Fictional Heat Transfer in Tubes — Extended Range",
            publication="Fictional Journal of Thermal Engineering",
            year=2024,
            doi="10.1000/fixture.002",
            verification_status=SourceVerificationStatus.primary_source_checked,
        ),
        implementation_status=CorrelationImplementationStatus.implemented,
        implementation_ref="impl-fixture-htc-v2",
        supersedes=CorrelationKey(correlation_id="fixture.htc.tube", version="1.0.0"),
        tags=frozenset({"implemented", "fixture"}),
    )


def _fixture_ff() -> CorrelationDefinition:
    """Fixture: friction factor correlation."""
    return CorrelationDefinition.create(
        key=CorrelationKey(correlation_id="fixture.ff.tube", version="1.0.0"),
        name="Fixture Friction Factor",
        purpose=CorrelationPurpose.friction_factor,
        description="Fictional friction factor for integration testing",
        geometry=frozenset({GeometryType.circular_tube}),
        phase_regimes=frozenset(
            {
                PhaseRegime.single_phase_liquid,
                PhaseRegime.single_phase_gas,
            }
        ),
        envelope=ApplicabilityEnvelope(
            geometry_types=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset(
                {
                    PhaseRegime.single_phase_liquid,
                    PhaseRegime.single_phase_gas,
                }
            ),
            flow_regimes=frozenset({FlowRegime.turbulent}),
            bounds=(
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=4000.0,
                    maximum=100000.0,
                ),
            ),
            required_inputs=frozenset({ApplicabilityVariable.reynolds}),
        ),
        source=BibliographicSource(
            source_id="src-fixture-ff-001",
            title="Fictional Friction in Smooth Tubes",
            publication="Fictional Fluid Mechanics Letters",
            year=2019,
            verification_status=SourceVerificationStatus.secondary_source,
        ),
        implementation_status=CorrelationImplementationStatus.implemented,
        implementation_ref="impl-fixture-ff-v1",
        tags=frozenset({"implemented", "fixture"}),
    )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestRegistryWorkflow:
    """End-to-end workflow: register → search → assess → record."""

    def test_register_and_search(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_fixture_htc_v1())
        reg.register(_fixture_htc_v2())
        reg.register(_fixture_ff())

        # Search by purpose
        htcs = reg.search(purpose=CorrelationPurpose.heat_transfer_coefficient)
        assert len(htcs) == 2

        # Search by geometry
        tube = reg.search(geometry=GeometryType.circular_tube)
        assert len(tube) == 3

        # Search by tags
        validated = reg.search(tags=frozenset({"validated"}))
        assert len(validated) == 1

    def test_version_management(self) -> None:
        reg = InMemoryCorrelationRegistry()
        reg.register(_fixture_htc_v1())
        reg.register(_fixture_htc_v2())

        versions = reg.list_versions("fixture.htc.tube")
        assert len(versions) == 2
        assert versions[0].key.version == "1.0.0"
        assert versions[1].key.version == "2.0.0"

        latest = reg.get_latest("fixture.htc.tube")
        assert latest.key.version == "2.0.0"

    def test_assessment_workflow(self) -> None:
        """Full assess → check → record workflow."""
        reg = InMemoryCorrelationRegistry()
        defn = _fixture_htc_v1()
        reg.register(defn)

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={
                ApplicabilityVariable.reynolds: 25000.0,
                ApplicabilityVariable.prandtl: 5.0,
            },
        )

        assessment = reg.assess(defn.key, inputs)
        assert assessment.status == ApplicabilityStatus.applicable
        assert assessment.allows_evaluation is True

        # Create usage record with computed definition_hash
        record = CorrelationUsageRecord(
            correlation_key=defn.key,
            definition_hash=defn.definition_hash or "sha256:" + "0" * 64,
            source_id=defn.source.source_id,
            applicability_status=assessment.status,
            input_values=(
                (ApplicabilityVariable.prandtl, 5.0),
                (ApplicabilityVariable.reynolds, 25000.0),
            ),
            assessment_hash=assessment.assessment_hash,
            extrapolation_used=False,
            uncertainty=defn.uncertainty,
        )

        node = record.to_provenance_node()
        assert node.node_type == ProvenanceNodeType.CORRELATION
        assert "fixture.htc.tube" in node.label

    def test_out_of_range_workflow(self) -> None:
        """Assessment with out-of-range values."""
        reg = InMemoryCorrelationRegistry()
        defn = _fixture_htc_v1()
        reg.register(defn)

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={
                ApplicabilityVariable.reynolds: 150000.0,  # above absolute max
                ApplicabilityVariable.prandtl: 5.0,
            },
        )

        assessment = reg.assess(defn.key, inputs)
        assert assessment.status == ApplicabilityStatus.absolute_range_exceeded
        assert assessment.allows_evaluation is False
        assert len(assessment.blockers) >= 1

    def test_incompatible_geometry_workflow(self) -> None:
        """Wrong geometry → blocked."""
        reg = InMemoryCorrelationRegistry()
        defn = _fixture_htc_v1()
        reg.register(defn)

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.annulus,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 25000.0},
        )

        assessment = reg.assess(defn.key, inputs)
        assert assessment.status == ApplicabilityStatus.incompatible_geometry

    def test_extrapolation_workflow(self) -> None:
        """Extrapolation with explicit opt-in."""
        reg = InMemoryCorrelationRegistry()
        defn = _fixture_htc_v1()
        reg.register(defn)

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={
                ApplicabilityVariable.reynolds: 150000.0,
                ApplicabilityVariable.prandtl: 5.0,
            },
            allow_extrapolation=True,
        )

        assessment = reg.assess(defn.key, inputs)
        # Default policy is block for absolute_violation
        assert assessment.status == ApplicabilityStatus.absolute_range_exceeded
        assert assessment.allows_evaluation is False

    def test_deprecated_correlation_workflow(self) -> None:
        """Deprecated correlations excluded from get_latest."""
        reg = InMemoryCorrelationRegistry()
        reg.register(_fixture_htc_v1())
        # Create a deprecated version
        deprecated_v2 = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="fixture.htc.tube", version="2.0.0"),
            name="Fixture HTC Tube v2",
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            description="Fictional tube-side HTC v2",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset({FlowRegime.turbulent}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=2000.0,
                        maximum=500000.0,
                    ),
                ),
                required_inputs=frozenset({ApplicabilityVariable.reynolds}),
            ),
            source=BibliographicSource(
                source_id="src-fixture-htc-002",
                title="Fictional HTC v2",
                publication="Fictional Journal",
                year=2024,
            ),
            implementation_status=CorrelationImplementationStatus.deprecated,
            tags=frozenset({"deprecated", "fixture"}),
        )
        reg.register(deprecated_v2)

        latest = reg.get_latest("fixture.htc.tube")
        assert latest.key.version == "1.0.0"

        latest_with_deprecated = reg.get_latest("fixture.htc.tube", include_deprecated=True)
        assert latest_with_deprecated.key.version == "2.0.0"

    def test_provenance_graph_integration(self) -> None:
        """Usage records integrate with provenance graph construction."""
        reg = InMemoryCorrelationRegistry()
        defn = _fixture_htc_v1()
        reg.register(defn)

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 25000.0},
        )

        assessment = reg.assess(defn.key, inputs)
        record = CorrelationUsageRecord(
            correlation_key=defn.key,
            definition_hash=defn.definition_hash or "sha256:" + "0" * 64,
            source_id=defn.source.source_id,
            applicability_status=assessment.status,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=assessment.assessment_hash,
            extrapolation_used=False,
        )

        node = record.to_provenance_node()
        # Verify node can be used in a provenance graph
        assert node.node_type == ProvenanceNodeType.CORRELATION
        assert node.payload_hash.startswith("sha256:")

    def test_multiple_correlations_search(self) -> None:
        """Search across multiple correlation types and purposes."""
        reg = InMemoryCorrelationRegistry()
        reg.register(_fixture_htc_v1())
        reg.register(_fixture_htc_v2())
        reg.register(_fixture_ff())

        # All correlations
        all_corr = reg.search()
        assert len(all_corr) == 3

        # By purpose
        htcs = reg.search(purpose=CorrelationPurpose.heat_transfer_coefficient)
        assert len(htcs) == 2
        ffs = reg.search(purpose=CorrelationPurpose.friction_factor)
        assert len(ffs) == 1

        # By implementation status
        metadata_only = reg.search(
            implementation_status=CorrelationImplementationStatus.metadata_only
        )
        assert len(metadata_only) == 1
        implemented = reg.search(implementation_status=CorrelationImplementationStatus.implemented)
        assert len(implemented) == 2

    def test_deterministic_provenance_node(self) -> None:
        """Item 8: Same usage record → same provenance node_id."""
        reg = InMemoryCorrelationRegistry()
        defn = _fixture_htc_v1()
        reg.register(defn)

        inputs = CorrelationApplicabilityInput(
            geometry=GeometryType.circular_tube,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=FlowRegime.turbulent,
            values={ApplicabilityVariable.reynolds: 25000.0},
        )
        assessment = reg.assess(defn.key, inputs)

        record = CorrelationUsageRecord(
            correlation_key=defn.key,
            definition_hash=defn.definition_hash or "sha256:" + "0" * 64,
            source_id=defn.source.source_id,
            applicability_status=assessment.status,
            input_values=((ApplicabilityVariable.reynolds, 25000.0),),
            assessment_hash=assessment.assessment_hash,
            extrapolation_used=False,
        )

        node1 = record.to_provenance_node()
        node2 = record.to_provenance_node()
        assert node1.node_id == node2.node_id  # Deterministic, not random
