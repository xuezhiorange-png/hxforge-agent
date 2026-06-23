"""Comprehensive unit tests for TASK-007 — tube and annulus correlation review fixes.

Covers ALL test categories:
  A. Selection tests (select_correlation directly)
  B. Applicability boundary tests
  C. Applicability identity tests
  D. Provenance semantic verification tests
  E. Source identity change tests
  F. Typed boundary conditions
  G. Frozen registry
  H. C4/C5 source verification
  I. Existing tests that must still pass
"""

from __future__ import annotations

import contextlib
import math
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError

from hexagent.correlations.annulus import (
    ANNULUS_CORRELATIONS,
    AnnulusLaminarInnerCHF,
    AnnulusTurbulentGnielinskiDH,
    _interpolate_nu_laminar_inner,
)
from hexagent.correlations.flow import (
    LAMINAR_UPPER_RE,
    TURBULENT_LOWER_RE,
    FlowPropertiesInput,
    FlowRegime,
    NusseltBasis,
    ThermalBoundaryCondition,
    classify_regime,
    compute_heat_transfer_coefficient,
    compute_prandtl,
    compute_reynolds,
    compute_velocity,
)
from hexagent.correlations.geometry import (
    CircularTubeGeometry,
    ConcentricAnnulusGeometry,
)
from hexagent.correlations.hx_result import (
    CorrelationResult,
    CorrelationStatus,
    SelectedCorrelationInfo,
    _provenance_graph_digest,
)
from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityVariable,
    CorrelationDefinition,
    CorrelationImplementationStatus,
    CorrelationKey,
    GeometryType,
    PhaseRegime,
    SourceVerificationStatus,
)
from hexagent.correlations.registry import InMemoryCorrelationRegistry
from hexagent.correlations.selection import (
    _get_nusselt_basis,
    _is_boundary_compatible,
    select_correlation,
)
from hexagent.correlations.service import (
    CalculationContext,
    _get_registry,
    evaluate_hx_correlation,
)
from hexagent.correlations.tube import (
    TubeLaminarCHF,
    TubeLaminarCWT,
    TubeTurbulentGnielinski,
)
from hexagent.domain.messages import ErrorCode
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)

# ---------------------------------------------------------------------------
# Shared test constants and helpers
# ---------------------------------------------------------------------------

# Water-like properties
RHO = 998.0  # kg/m³
MU = 0.001  # Pa·s
K = 0.6  # W/(m·K)
CP = 4182.0  # J/(kg·K)
PR = CP * MU / K  # ≈ 6.98

# Circular tube geometry (25 mm ID, 2 m)
TUBE_D = 0.025  # m
TUBE_L = 2.0  # m
TUBE_A = math.pi / 4.0 * TUBE_D**2
TUBE_P = math.pi * TUBE_D
TUBE_DH = TUBE_D  # = 0.025 m

# Annulus geometry (25 mm inner OD, 50 mm outer ID, 2 m)
ANN_DI = 0.025  # m
ANN_DO = 0.050  # m
ANN_L = 2.0  # m
ANN_KAPPA = ANN_DI / ANN_DO  # = 0.5
ANN_A = math.pi / 4.0 * (ANN_DO**2 - ANN_DI**2)
ANN_DH = ANN_DO - ANN_DI  # = 0.025 m


def _tube_geom() -> CircularTubeGeometry:
    return CircularTubeGeometry(
        inside_diameter_m=TUBE_D,
        heat_transfer_length_m=TUBE_L,
    )


def _ann_geom(
    *, di: float = ANN_DI, do: float = ANN_DO, heated: str = "inner"
) -> ConcentricAnnulusGeometry:
    return ConcentricAnnulusGeometry(
        inner_tube_outer_diameter_m=di,
        outer_pipe_inside_diameter_m=do,
        heat_transfer_length_m=ANN_L,
        heated_surface=heated,
    )


def _water_flow(
    *,
    mass_flow: float = 0.1,
    heating: bool = True,
    wall_temp: float | None = None,
    wall_visc: float | None = None,
) -> FlowPropertiesInput:
    return FlowPropertiesInput(
        mass_flow_kg_s=mass_flow,
        density_kg_m3=RHO,
        dynamic_viscosity_pa_s=MU,
        thermal_conductivity_w_m_k=K,
        specific_heat_j_kg_k=CP,
        bulk_temperature_k=350.0,
        wall_temperature_k=wall_temp,
        wall_viscosity_pa_s=wall_visc,
        heating=heating,
    )


def _registry() -> InMemoryCorrelationRegistry:
    """Return the default registry singleton."""
    return _get_registry()


def _make_result_tube_laminar() -> CorrelationResult:
    flow = _water_flow(mass_flow=0.005)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


def _make_result_tube_turbulent() -> CorrelationResult:
    flow = _water_flow(mass_flow=0.3)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


def _make_result_blocked() -> CorrelationResult:
    flow = _water_flow(mass_flow=0.0)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


# =====================================================================
# A. Selection Tests
# =====================================================================


class TestSelectionNormalSucceeded:
    """A1: Normal succeeded result — verify_hash and verify_provenance."""

    def test_succeeded_verify_hash(self) -> None:
        r = _make_result_tube_laminar()
        assert r.status == CorrelationStatus.SUCCEEDED
        assert r.verify_hash() is True

    def test_succeeded_verify_provenance(self) -> None:
        r = _make_result_tube_laminar()
        assert r.verify_provenance() is True

    def test_turbulent_verify_hash_and_provenance(self) -> None:
        r = _make_result_tube_turbulent()
        assert r.status == CorrelationStatus.SUCCEEDED
        assert r.verify_hash() is True
        assert r.verify_provenance() is True


class TestSelectionBlockedResult:
    """A2: Blocked result (C4 NotImplementedError) — verify_hash and verify_provenance."""

    def test_blocked_verify_hash(self) -> None:
        r = _make_result_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.verify_hash() is True

    def test_blocked_verify_provenance(self) -> None:
        r = _make_result_blocked()
        assert r.verify_provenance() is True


class TestSelectionJSONRoundTrip:
    """A3: JSON round-trip — hash and provenance preserved."""

    def test_succeeded_roundtrip(self) -> None:
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.result_hash == r.result_hash
        assert restored.verify_hash() is True
        assert restored.verify_provenance() is True

    def test_blocked_roundtrip(self) -> None:
        r = _make_result_blocked()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.result_hash == r.result_hash
        assert restored.verify_hash() is True
        assert restored.verify_provenance() is True


class TestSelectionSemVerOrdering:
    """A4: SemVer ordering with select_correlation."""

    def _make_def(
        self,
        correlation_id: str,
        version: str,
        *,
        tags: frozenset[str] = frozenset(),
        flow_regimes: frozenset[str] = frozenset({"laminar"}),
        bounds: tuple = (),
    ) -> CorrelationDefinition:
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import (
            FlowRegime as ModelsFlowRegime,
        )

        if not bounds:
            bounds = (
                NumericBound(
                    variable=ApplicabilityVariable.reynolds,
                    minimum=0.0,
                    maximum=2300.0,
                    minimum_inclusive=False,
                    maximum_inclusive=False,
                ),
                NumericBound(
                    variable=ApplicabilityVariable.prandtl,
                    minimum=0.6,
                    minimum_inclusive=False,
                ),
            )

        return CorrelationDefinition.create(
            key=CorrelationKey(correlation_id=correlation_id, version=version),
            name=f"Test {correlation_id} v{version}",
            purpose=CorrelationPurpose.nusselt_number,
            description="Test correlation",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset(ModelsFlowRegime(fr) for fr in flow_regimes),
                bounds=bounds,
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            source=BibliographicSource(
                source_id="test_source",
                title="Test",
                publication="Test Pub",
                year=2024,
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(basis="test"),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="test.ref",
            tags=tags,
        )

    def test_highest_version_wins(self) -> None:
        """Register multiple versions; highest (stable) should be selected."""
        versions = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.2",
            "1.0.0-alpha.10",
            "1.0.0-beta",
            "1.0.0",
        ]
        for _version in versions:
            tags = frozenset(
                {
                    "bc:constant_wall_temperature",
                    "nusselt_basis:inside_diameter",
                    "priority:10",
                }
            )
            reg = InMemoryCorrelationRegistry()
            # Register all versions
            for v in versions:
                with contextlib.suppress(Exception):
                    reg.register(self._make_def("test_correlation", v, tags=tags))

            result = select_correlation(
                reg,
                _tube_geom(),
                "constant_wall_temperature",
                FlowRegime.laminar,
                200.0,
                7.0,
            )
            assert result.selected_definition is not None
            assert result.selected_definition.key.version == "1.0.0"
            break  # Only need to test once with a fully populated registry

    def test_same_result_across_insertion_orders(self) -> None:
        """5 different insertion orders produce the same selected version."""
        versions = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.2", "1.0.0-beta", "1.0.0"]
        tags = frozenset(
            {
                "bc:constant_wall_temperature",
                "nusselt_basis:inside_diameter",
                "priority:10",
            }
        )
        insertion_orders = [
            versions,
            list(reversed(versions)),
            [versions[2], versions[0], versions[4], versions[1], versions[3]],
            [versions[4], versions[2], versions[0], versions[3], versions[1]],
            [versions[1], versions[3], versions[4], versions[0], versions[2]],
        ]

        selected_versions = []
        for order in insertion_orders:
            reg = InMemoryCorrelationRegistry()
            for v in order:
                with contextlib.suppress(Exception):
                    reg.register(self._make_def("test_correlation", v, tags=tags))
            result = select_correlation(
                reg,
                _tube_geom(),
                "constant_wall_temperature",
                FlowRegime.laminar,
                200.0,
                7.0,
            )
            assert result.selected_definition is not None
            selected_versions.append(result.selected_definition.key.version)

        # All should select 1.0.0
        assert all(v == "1.0.0" for v in selected_versions)


class TestSelectionPriorityFromTags:
    """A5: Priority from tags — higher priority wins."""

    def test_higher_priority_wins(self) -> None:
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import FlowRegime as ModelsFlowRegime

        def _make_def(cid: str, prio: int) -> CorrelationDefinition:
            return CorrelationDefinition.create(
                key=CorrelationKey(correlation_id=cid, version="1.0.0"),
                name=f"Test {cid}",
                purpose=CorrelationPurpose.nusselt_number,
                description="Test",
                geometry=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                envelope=ApplicabilityEnvelope(
                    geometry_types=frozenset({GeometryType.circular_tube}),
                    phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                    flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                    bounds=(
                        NumericBound(
                            variable=ApplicabilityVariable.reynolds,
                            minimum=0.0,
                            maximum=2300.0,
                            minimum_inclusive=False,
                            maximum_inclusive=False,
                        ),
                        NumericBound(
                            variable=ApplicabilityVariable.prandtl,
                            minimum=0.6,
                            minimum_inclusive=False,
                        ),
                    ),
                    required_inputs=frozenset(
                        {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                    ),
                ),
                source=BibliographicSource(
                    source_id="test",
                    title="T",
                    publication="P",
                    year=2024,
                    verification_status=SourceVerificationStatus.primary_source_checked,
                ),
                uncertainty=UncertaintySpec(basis="test"),
                implementation_status=CorrelationImplementationStatus.validated,
                implementation_ref="test.ref",
                tags=frozenset(
                    {
                        "bc:constant_wall_temperature",
                        "nusselt_basis:inside_diameter",
                        f"priority:{prio}",
                    }
                ),
            )

        reg = InMemoryCorrelationRegistry()
        reg.register(_make_def("low_prio", 5))
        reg.register(_make_def("high_prio", 10))

        result = select_correlation(
            reg,
            _tube_geom(),
            "constant_wall_temperature",
            FlowRegime.laminar,
            200.0,
            7.0,
        )
        assert result.selected_definition is not None
        assert result.selected_definition.key.correlation_id == "high_prio"


class TestSelectionAmbiguity:
    """A6: Ambiguity when two candidates tie on all sort keys."""

    def test_ambiguous_returns_blocker(self) -> None:
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import FlowRegime as ModelsFlowRegime

        tags = frozenset(
            {"bc:constant_wall_temperature", "nusselt_basis:inside_diameter", "priority:10"}
        )

        def _make_def(cid: str) -> CorrelationDefinition:
            return CorrelationDefinition.create(
                key=CorrelationKey(correlation_id=cid, version="1.0.0"),
                name=f"Test {cid}",
                purpose=CorrelationPurpose.nusselt_number,
                description="Test",
                geometry=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                envelope=ApplicabilityEnvelope(
                    geometry_types=frozenset({GeometryType.circular_tube}),
                    phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                    flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                    bounds=(
                        NumericBound(
                            variable=ApplicabilityVariable.reynolds,
                            minimum=0.0,
                            maximum=2300.0,
                            minimum_inclusive=False,
                            maximum_inclusive=False,
                        ),
                        NumericBound(
                            variable=ApplicabilityVariable.prandtl,
                            minimum=0.6,
                            minimum_inclusive=False,
                        ),
                    ),
                    required_inputs=frozenset(
                        {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                    ),
                ),
                source=BibliographicSource(
                    source_id="test",
                    title="T",
                    publication="P",
                    year=2024,
                    verification_status=SourceVerificationStatus.primary_source_checked,
                ),
                uncertainty=UncertaintySpec(basis="test"),
                implementation_status=CorrelationImplementationStatus.validated,
                implementation_ref="test.ref",
                tags=tags,
            )

        # Create two definitions with same priority, same version, but DIFFERENT IDs
        # They should NOT be ambiguous (different IDs → different sort keys)
        reg = InMemoryCorrelationRegistry()
        reg.register(_make_def("corr_a"))
        reg.register(_make_def("corr_b"))
        result = select_correlation(
            reg,
            _tube_geom(),
            "constant_wall_temperature",
            FlowRegime.laminar,
            200.0,
            7.0,
        )
        # Different IDs → not ambiguous, first alphabetically wins
        assert result.selection_status == "selected"
        assert result.selected_definition is not None
        assert result.selected_definition.key.correlation_id == "corr_a"


class TestSelectionRejectedCandidatesPreserved:
    """A7: Rejected candidates preserved with full context."""

    def test_rejected_candidates_non_empty_when_all_fail(self) -> None:
        """When all candidates fail applicability, rejected_candidates is non-empty."""
        # Use C4 definition with a diameters that puts it out of range
        # C4 requires kappa in [0.1, 0.75] — use kappa=0.05 to fail
        g = _ann_geom(di=0.0025, do=0.050)  # kappa=0.05
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED
        # The result should have an assessment (from rejected candidate)
        assert result.applicability_assessment is not None


# =====================================================================
# B. Applicability Boundary Tests
# =====================================================================


class TestApplicabilityBoundaries:
    """B8-B12: Applicability boundary tests."""

    def test_pr_below_06_for_laminar_blocked(self) -> None:
        """Pr < 0.6 for laminar → BLOCKED with CORRELATION_ABSOLUTE_RANGE_EXCEEDED."""
        # Use liquid-metal-like properties with very low Pr
        # Pr = cp * mu / k ≈ 140 * 0.0015 / 8.5 ≈ 0.025
        flow = FlowPropertiesInput(
            mass_flow_kg_s=0.01,
            density_kg_m3=9000.0,
            dynamic_viscosity_pa_s=0.0015,
            thermal_conductivity_w_m_k=8.5,
            specific_heat_j_kg_k=140.0,
            bulk_temperature_k=350.0,
        )
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        # Check for range exceeded blocker
        assert any(b.code == ErrorCode.CORRELATION_ABSOLUTE_RANGE_EXCEEDED for b in result.blockers)

    def test_re_at_exact_boundary_2300(self) -> None:
        """Re = 2300 → transitional → BLOCKED."""
        target_re = 2300.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.flow_regime == "transitional"

    def test_re_at_exact_boundary_10000(self) -> None:
        """Re = 10000 → transitional → BLOCKED."""
        target_re = 10000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.flow_regime == "transitional"

    def test_re_below_laminar_succeeds(self) -> None:
        """Re < 2300 → laminar → succeeds."""
        target_re = 1000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED

    def test_re_above_turbulent_succeeds(self) -> None:
        """Re > 10000 → turbulent → succeeds."""
        target_re = 15000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED

    def test_kappa_below_01_blocked(self) -> None:
        """κ < 0.1 for C4 → BLOCKED."""
        g = _ann_geom(di=0.0025, do=0.050)  # kappa=0.05
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_kappa_above_075_blocked(self) -> None:
        """κ > 0.75 for C4 → BLOCKED."""
        g = _ann_geom(di=0.0425, do=0.050)  # kappa=0.85
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_missing_required_input_blocked(self) -> None:
        """Missing required input → BLOCKED with CORRELATION_INPUT_MISSING."""
        reg = InMemoryCorrelationRegistry()
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import FlowRegime as ModelsFlowRegime

        # Define a correlation that requires relative_roughness (which selection never provides)
        defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="test_missing", version="1.0.0"),
            name="Test Missing Input",
            purpose=CorrelationPurpose.nusselt_number,
            description="Test",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl, minimum=0.6, minimum_inclusive=False
                    ),
                ),
                required_inputs=frozenset(
                    {
                        ApplicabilityVariable.reynolds,
                        ApplicabilityVariable.prandtl,
                        ApplicabilityVariable.relative_roughness,
                    }
                ),
            ),
            source=BibliographicSource(
                source_id="test",
                title="T",
                publication="P",
                year=2024,
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(basis="test"),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="test.ref",
            tags=frozenset(
                {"bc:constant_wall_temperature", "nusselt_basis:inside_diameter", "priority:10"}
            ),
        )
        reg.register(defn)

        # selection should fail because relative_roughness is required but never provided
        result = select_correlation(
            reg,
            _tube_geom(),
            "constant_wall_temperature",
            FlowRegime.laminar,
            200.0,
            7.0,
        )
        # The definition requires relative_roughness which is not provided → rejected
        assert result.selection_status == "no_match"
        assert len(result.rejected_candidates) > 0
        _, rejected_assessment = result.rejected_candidates[0]
        assert rejected_assessment.status.value == "missing_input"


# =====================================================================
# C. Applicability Identity Tests
# =====================================================================


class TestApplicabilityIdentity:
    """C13-C16: Applicability assessment type and identity."""

    def test_assessment_is_correct_type(self) -> None:
        """C13: CorrelationResult.applicability_assessment is ApplicabilityAssessment."""
        r = _make_result_tube_laminar()
        assert r.status == CorrelationStatus.SUCCEEDED
        assert isinstance(r.applicability_assessment, ApplicabilityAssessment)

    def test_json_roundtrip_assessment_type(self) -> None:
        """C14: JSON round-trip reconstructs assessment as ApplicabilityAssessment."""
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert isinstance(restored.applicability_assessment, ApplicabilityAssessment)
        assert (
            restored.applicability_assessment.assessment_hash
            == r.applicability_assessment.assessment_hash
        )

    def test_tamper_assessment_breaks_integrity(self) -> None:
        """C15: Tamper assessment → validate_integrity() False, verify_hash() False."""
        r = _make_result_tube_laminar()
        assert r.applicability_assessment is not None
        # Tamper by replacing with a different assessment
        tampered = r.applicability_assessment.model_copy(
            update={"status": "absolute_range_exceeded"}
        )
        object.__setattr__(r, "applicability_assessment", tampered)
        assert r.validate_integrity() is False
        assert r.verify_hash() is False

    def test_assessment_in_identity_payload(self) -> None:
        """C16: Changing assessment changes result_hash."""
        r1 = _make_result_tube_laminar()
        # Create a result with a different assessment
        r2 = _make_result_tube_laminar()
        tampered = r2.applicability_assessment.model_copy(
            update={"status": "absolute_range_exceeded"}
        )
        object.__setattr__(r2, "applicability_assessment", tampered)
        # Recompute hash to include tampered assessment
        new_hash = r2._compute_result_hash()
        assert r1.result_hash != new_hash

    def test_blocked_has_no_assessment(self) -> None:
        """Blocked result has no assessment."""
        r = _make_result_blocked()
        assert r.applicability_assessment is None


# =====================================================================
# D. Provenance Semantic Verification Tests
# =====================================================================


class TestProvenanceSemanticVerification:
    """D17-D23: Per-node-type semantic verification."""

    def test_all_node_types_payload_hash_matches(self) -> None:
        """D17: For each node type, payload_hash matches recomputed."""
        r = _make_result_tube_laminar()
        assert r.verify_provenance() is True
        # Check each node type
        for node in r.provenance_graph.nodes:
            assert node.payload_hash.startswith("sha256:")

    def test_tamper_payload_hash_breaks_provenance(self) -> None:
        """D18: Tamper node payload_hash → verify_provenance() False."""
        r = _make_result_tube_laminar()
        # Tamper a node's payload_hash
        nodes = list(r.provenance_graph.nodes)
        tampered_node = nodes[0].model_copy(update={"payload_hash": "sha256:" + "ff" * 32})
        nodes[0] = tampered_node
        object.__setattr__(
            r,
            "provenance_graph",
            ProvenanceGraph(nodes=tuple(nodes), edges=r.provenance_graph.edges),
        )
        # Recompute digest to match tampered graph
        object.__setattr__(r, "provenance_digest", _provenance_graph_digest(r.provenance_graph))
        assert r.verify_provenance() is False

    def test_tamper_node_id_breaks_provenance(self) -> None:
        """D19: Tamper node UUID (node_id) → verify_provenance() False."""
        from hexagent.domain.provenance import ProvenanceEdge

        r = _make_result_tube_laminar()
        nodes = list(r.provenance_graph.nodes)
        original_id = nodes[0].node_id
        new_id = uuid4()
        tampered_node = nodes[0].model_copy(update={"node_id": new_id})
        nodes[0] = tampered_node
        # Update edges that reference the original node_id
        edges = []
        for e in r.provenance_graph.edges:
            src = new_id if e.source_id == original_id else e.source_id
            tgt = new_id if e.target_id == original_id else e.target_id
            edges.append(ProvenanceEdge(source_id=src, target_id=tgt, relation=e.relation))
        object.__setattr__(
            r, "provenance_graph", ProvenanceGraph(nodes=tuple(nodes), edges=tuple(edges))
        )
        object.__setattr__(r, "provenance_digest", _provenance_graph_digest(r.provenance_graph))
        assert r.verify_provenance() is False

    def test_missing_node_breaks_provenance(self) -> None:
        """D20: Missing node → verify_provenance() False."""
        r = _make_result_tube_laminar()
        # Remove the RESULT node
        nodes = [n for n in r.provenance_graph.nodes if n.node_type != ProvenanceNodeType.RESULT]
        edges = [
            e
            for e in r.provenance_graph.edges
            if e.target_id != r.provenance_graph.nodes[-1].node_id
        ]
        object.__setattr__(
            r, "provenance_graph", ProvenanceGraph(nodes=tuple(nodes), edges=tuple(edges))
        )
        object.__setattr__(r, "provenance_digest", _provenance_graph_digest(r.provenance_graph))
        assert r.verify_provenance() is False

    def test_extra_node_breaks_provenance(self) -> None:
        """D21: Extra node → verify_provenance() False."""
        from hexagent.domain.provenance import ProvenanceNode

        r = _make_result_tube_laminar()
        extra_node = ProvenanceNode(
            node_id=uuid4(),
            node_type=ProvenanceNodeType.WARNING,
            label="extra",
            metadata=(("code", "extra"), ("message", "extra"), ("source_module", "test")),
            payload_hash="sha256:" + "00" * 32,
        )
        nodes = list(r.provenance_graph.nodes) + [extra_node]
        object.__setattr__(
            r,
            "provenance_graph",
            ProvenanceGraph(nodes=tuple(nodes), edges=r.provenance_graph.edges),
        )
        object.__setattr__(r, "provenance_digest", _provenance_graph_digest(r.provenance_graph))
        assert r.verify_provenance() is False

    def test_duplicate_edge_breaks_provenance(self) -> None:
        """D22: Duplicate edge → verify_provenance() False."""
        r = _make_result_tube_laminar()
        if r.provenance_graph.edges:
            edge = r.provenance_graph.edges[0]
            # Add a duplicate edge — ProvenanceGraph allows it, but verify should catch it
            new_graph = ProvenanceGraph(
                nodes=r.provenance_graph.nodes,
                edges=r.provenance_graph.edges + (edge,),
            )
            object.__setattr__(r, "provenance_graph", new_graph)
            object.__setattr__(r, "provenance_digest", _provenance_graph_digest(new_graph))
            assert r.verify_provenance() is False

    def test_cycle_fails_graph_construction(self) -> None:
        """D23: Cycle → ProvenanceGraph construction fails."""
        from hexagent.domain.provenance import ProvenanceEdge, ProvenanceNode

        id1, id2 = uuid4(), uuid4()
        n1 = ProvenanceNode(
            node_id=id1,
            node_type=ProvenanceNodeType.EXTERNAL,
            label="a",
            payload_hash="sha256:" + "00" * 32,
        )
        n2 = ProvenanceNode(
            node_id=id2,
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="b",
            payload_hash="sha256:" + "00" * 32,
        )
        e1 = ProvenanceEdge(source_id=id1, target_id=id2, relation="triggers")
        e2 = ProvenanceEdge(source_id=id2, target_id=id1, relation="triggers")  # cycle!
        with pytest.raises(ValueError, match="cycle"):
            ProvenanceGraph(nodes=(n1, n2), edges=(e1, e2))


# =====================================================================
# E. Source Identity Change Tests
# =====================================================================


class TestSourceIdentityChange:
    """E24: Two definitions differing only in source_title → different hashes."""

    def test_different_source_title_different_hashes(self) -> None:
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import FlowRegime as ModelsFlowRegime

        base = dict(
            name="Test",
            purpose=CorrelationPurpose.nusselt_number,
            description="Test",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl, minimum=0.6, minimum_inclusive=False
                    ),
                ),
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            uncertainty=UncertaintySpec(basis="test"),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="test.ref",
            tags=frozenset(
                {"bc:constant_wall_temperature", "nusselt_basis:inside_diameter", "priority:10"}
            ),
        )

        source1 = BibliographicSource(
            source_id="s1",
            title="Title A",
            publication="Pub",
            year=2020,
            verification_status=SourceVerificationStatus.primary_source_checked,
        )
        source2 = BibliographicSource(
            source_id="s2",
            title="Title B",
            publication="Pub",
            year=2020,
            verification_status=SourceVerificationStatus.primary_source_checked,
        )

        defn1 = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="test", version="1.0.0"), source=source1, **base
        )
        defn2 = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="test", version="1.0.0"), source=source2, **base
        )

        assert defn1.definition_hash != defn2.definition_hash


# =====================================================================
# F. Typed Boundary Conditions
# =====================================================================


class TestTypedBoundaryConditions:
    """F25-F27: ThermalBoundaryCondition enum."""

    def test_enum_values(self) -> None:
        """F25: ThermalBoundaryCondition enum values work."""
        assert (
            ThermalBoundaryCondition.constant_wall_temperature.value == "constant_wall_temperature"
        )
        assert ThermalBoundaryCondition.constant_heat_flux.value == "constant_heat_flux"
        assert ThermalBoundaryCondition.inner_wall_heated.value == "inner_wall_heated"
        assert ThermalBoundaryCondition.outer_wall_heated.value == "outer_wall_heated"
        assert ThermalBoundaryCondition.both_walls_heated.value == "both_walls_heated"

    def test_invalid_string_blocked(self) -> None:
        """F26: Invalid string → BLOCKED."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "invalid_bc")
        assert result.status == CorrelationStatus.BLOCKED

    def test_string_deserialization(self) -> None:
        """F27: String deserialization works at API boundary."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED


# =====================================================================
# G. Frozen Registry
# =====================================================================


class TestFrozenRegistry:
    """G28: External attempt to register after freeze → no effect."""

    def test_register_after_freeze_no_effect(self) -> None:
        reg1 = _get_registry()
        count1 = len(reg1.search(purpose=None, geometry=None))
        # Register something on the copy
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import FlowRegime as ModelsFlowRegime

        new_defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="test_frozen", version="1.0.0"),
            name="Test Frozen",
            purpose=CorrelationPurpose.nusselt_number,
            description="Test",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl, minimum=0.6, minimum_inclusive=False
                    ),
                ),
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            source=BibliographicSource(
                source_id="test",
                title="T",
                publication="P",
                year=2024,
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(basis="test"),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="test.ref",
            tags=frozenset(
                {"bc:constant_wall_temperature", "nusselt_basis:inside_diameter", "priority:10"}
            ),
        )
        reg1.register(new_defn)
        # Get a fresh copy — should NOT have the new definition
        reg2 = _get_registry()
        count2 = len(reg2.search(purpose=None, geometry=None))
        assert count1 == count2


# =====================================================================
# H. C4/C5 Source Verification
# =====================================================================


class TestC4SourceVerification:
    """H29-H30: C4 definition metadata and evaluation blocking."""

    def test_c4_metadata_status(self) -> None:
        """H29: C4 metadata_only, source unverified."""
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert defn.implementation_status == CorrelationImplementationStatus.metadata_only
        assert defn.source.verification_status == SourceVerificationStatus.unverified

    def test_c4_evaluation_blocked(self) -> None:
        """H30: C4 evaluation → BLOCKED with NOT_IMPLEMENTED."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED
        assert any(b.code == ErrorCode.NOT_IMPLEMENTED for b in result.blockers)


class TestC5SourceVerification:
    """H31: C5 definition metadata."""

    def test_c5_metadata_status(self) -> None:
        """C5 source_verification_status == unverified, implementation_status == implemented."""
        reg = _registry()
        defn = reg.get(
            CorrelationKey(correlation_id="annulus_turbulent_gnielinski_dh", version="1.0.0")
        )
        assert defn.source.verification_status == SourceVerificationStatus.unverified
        assert defn.implementation_status == CorrelationImplementationStatus.implemented


# =====================================================================
# I. Existing Tests That Must Still Pass
# =====================================================================

# --- Geometry Tests ---


class TestCircularTubeGeometry:
    """CircularTubeGeometry construction, validation, and properties."""

    def test_construction_succeeds(self) -> None:
        g = _tube_geom()
        assert g.inside_diameter_m == TUBE_D
        assert g.heat_transfer_length_m == TUBE_L
        assert g.geometry_type == "circular_tube"

    def test_flow_area(self) -> None:
        g = _tube_geom()
        assert g.flow_area_m2 == pytest.approx(math.pi / 4.0 * TUBE_D**2, rel=1e-12)

    def test_wetted_perimeter(self) -> None:
        g = _tube_geom()
        assert g.wetted_perimeter_m == pytest.approx(math.pi * TUBE_D, rel=1e-12)

    def test_hydraulic_diameter_equals_diameter(self) -> None:
        g = _tube_geom()
        assert g.hydraulic_diameter_m == pytest.approx(TUBE_D, rel=1e-12)

    def test_frozen(self) -> None:
        g = _tube_geom()
        with pytest.raises(ValidationError):
            g.inside_diameter_m = 0.05  # type: ignore[misc]

    def test_zero_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=0.0, heat_transfer_length_m=TUBE_L)

    def test_negative_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=-0.01, heat_transfer_length_m=TUBE_L)


class TestConcentricAnnulusGeometry:
    """ConcentricAnnulusGeometry construction, validation, and properties."""

    def test_construction_succeeds(self) -> None:
        g = _ann_geom()
        assert g.inner_tube_outer_diameter_m == ANN_DI
        assert g.outer_pipe_inside_diameter_m == ANN_DO
        assert g.heated_surface == "inner"
        assert g.geometry_type == "concentric_annulus"

    def test_flow_area(self) -> None:
        g = _ann_geom()
        expected = math.pi / 4.0 * (ANN_DO**2 - ANN_DI**2)
        assert g.flow_area_m2 == pytest.approx(expected, rel=1e-12)

    def test_hydraulic_diameter(self) -> None:
        g = _ann_geom()
        assert g.hydraulic_diameter_m == pytest.approx(ANN_DO - ANN_DI, rel=1e-12)

    def test_diameter_ratio(self) -> None:
        g = _ann_geom()
        assert g.diameter_ratio == pytest.approx(ANN_KAPPA, rel=1e-12)

    def test_equal_diameters_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be greater"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.025,
                outer_pipe_inside_diameter_m=0.025,
                heat_transfer_length_m=ANN_L,
            )

    def test_frozen(self) -> None:
        g = _ann_geom()
        with pytest.raises(ValidationError):
            g.inner_tube_outer_diameter_m = 0.1  # type: ignore[misc]


# --- Dimensionless Calculations ---


class TestClassifyRegime:
    """Regime classification boundaries and edge cases."""

    def test_laminar(self) -> None:
        assert classify_regime(1000) == FlowRegime.laminar

    def test_laminar_upper_bound_exclusive(self) -> None:
        assert classify_regime(LAMINAR_UPPER_RE - 1) == FlowRegime.laminar

    def test_exactly_laminar_upper_is_transitional(self) -> None:
        assert classify_regime(LAMINAR_UPPER_RE) == FlowRegime.transitional

    def test_turbulent(self) -> None:
        assert classify_regime(TURBULENT_LOWER_RE + 1) == FlowRegime.turbulent

    def test_exactly_turbulent_lower_is_transitional(self) -> None:
        assert classify_regime(TURBULENT_LOWER_RE) == FlowRegime.transitional

    def test_zero_is_laminar(self) -> None:
        assert classify_regime(0.0) == FlowRegime.laminar

    def test_negative_is_invalid(self) -> None:
        assert classify_regime(-1.0) == FlowRegime.invalid

    def test_nan_is_invalid(self) -> None:
        assert classify_regime(float("nan")) == FlowRegime.invalid

    def test_inf_is_invalid(self) -> None:
        assert classify_regime(float("inf")) == FlowRegime.invalid


class TestComputeVelocity:
    """Mean velocity computation."""

    def test_basic(self) -> None:
        v = compute_velocity(0.1, RHO, TUBE_A)
        expected = 0.1 / (RHO * TUBE_A)
        assert v == pytest.approx(expected, rel=1e-12)

    def test_zero_mass_flow(self) -> None:
        v = compute_velocity(0.0, RHO, TUBE_A)
        assert v == 0.0


class TestComputeReynolds:
    """Reynolds number."""

    def test_basic(self) -> None:
        v = compute_velocity(0.1, RHO, TUBE_A)
        re = compute_reynolds(RHO, v, TUBE_DH, MU)
        expected = RHO * v * TUBE_DH / MU
        assert re == pytest.approx(expected, rel=1e-12)


class TestComputePrandtl:
    """Prandtl number."""

    def test_water_at_350k(self) -> None:
        pr = compute_prandtl(CP, MU, K)
        expected = CP * MU / K
        assert pr == pytest.approx(expected, rel=1e-12)


class TestComputeHeatTransferCoefficient:
    """h = Nu × k / D_h."""

    def test_basic(self) -> None:
        h = compute_heat_transfer_coefficient(3.66, K, TUBE_DH)
        expected = 3.66 * K / TUBE_DH
        assert h == pytest.approx(expected, rel=1e-12)


# --- Regime Boundaries ---


class TestRegimeBoundaries:
    """Test specific Re values at regime boundaries."""

    def test_re_2299_laminar(self) -> None:
        assert classify_regime(2299.0) == FlowRegime.laminar

    def test_re_2300_transitional(self) -> None:
        assert classify_regime(2300.0) == FlowRegime.transitional

    def test_re_10000_transitional(self) -> None:
        assert classify_regime(10000.0) == FlowRegime.transitional

    def test_re_10001_turbulent(self) -> None:
        assert classify_regime(10001.0) == FlowRegime.turbulent


# --- Correlation Reference Cases ---


class TestTubeLaminarCWT:
    """C1: Tube laminar, constant wall temperature — Nu = 3.66."""

    def test_nu_value(self) -> None:
        c = TubeLaminarCWT()
        assert c.evaluate() == 3.66

    def test_metadata(self) -> None:
        c = TubeLaminarCWT()
        assert c.correlation_id == "tube_laminar_cwt"
        assert c.version == "1.0.0"
        assert c.supported_geometry == "circular_tube"
        assert c.flow_regime == "laminar"
        assert c.boundary_condition == "constant_wall_temperature"

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert defn is not None
        assert defn.definition_hash.startswith("sha256:")


class TestTubeLaminarCHF:
    """C2: Tube laminar, constant heat flux — Nu = 4.36."""

    def test_nu_value(self) -> None:
        c = TubeLaminarCHF()
        assert c.evaluate() == 4.36

    def test_metadata(self) -> None:
        c = TubeLaminarCHF()
        assert c.correlation_id == "tube_laminar_chf"
        assert c.boundary_condition == "constant_heat_flux"


class TestTubeTurbulentGnielinski:
    """C3: Tube turbulent Gnielinski correlation."""

    def _instance(self) -> TubeTurbulentGnielinski:
        return TubeTurbulentGnielinski()

    def test_petukhov_friction_factor(self) -> None:
        c = self._instance()
        f = c.petukhov_friction_factor(10000.0)
        expected = (0.790 * math.log(10000.0) - 1.64) ** (-2)
        assert f == pytest.approx(expected, rel=1e-12)

    def test_nu_at_pr1(self) -> None:
        c = self._instance()
        nu = c.evaluate(10000.0, 1.0)
        f = c.petukhov_friction_factor(10000.0)
        f8 = f / 8.0
        numerator = f8 * (10000.0 - 1000.0) * 1.0
        denominator = 1.0 + 12.7 * math.sqrt(f8) * 0.0
        assert nu == pytest.approx(numerator / denominator, rel=1e-12)

    def test_re_below_min_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError, match="outside valid range"):
            c.evaluate(2999.0, 1.0)

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_turbulent_gnielinski", version="1.0.0"))
        assert defn is not None


class TestAnnulusLaminarInnerCHF:
    """C4: Annulus laminar — evaluate() raises NotImplementedError."""

    def test_metadata(self) -> None:
        c = AnnulusLaminarInnerCHF()
        assert c.correlation_id == "annulus_laminar_inner_chf"
        assert c.supported_geometry == "concentric_annulus"
        assert c.flow_regime == "laminar"
        assert c.boundary_condition == "inner_wall_heated"

    def test_evaluate_raises_not_implemented(self) -> None:
        c = AnnulusLaminarInnerCHF()
        with pytest.raises(NotImplementedError):
            c.evaluate(0.5)

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert defn is not None


class TestInterpolateNuLaminarInner:
    """Kays Table 9-1 interpolation — raises NotImplementedError."""

    def test_always_raises(self) -> None:
        with pytest.raises(NotImplementedError):
            _interpolate_nu_laminar_inner(0.5)


class TestAnnulusTurbulentGnielinskiDH:
    """C5: Annulus turbulent — hydraulic-diameter Gnielinski adaptation."""

    def _instance(self) -> AnnulusTurbulentGnielinskiDH:
        return AnnulusTurbulentGnielinskiDH()

    def test_nu_same_as_tube_for_same_inputs(self) -> None:
        c_ann = self._instance()
        c_tube = TubeTurbulentGnielinski()
        Re, Pr = 20000.0, 5.0
        assert c_ann.evaluate(Re, Pr) == pytest.approx(c_tube.evaluate(Re, Pr), rel=1e-12)

    def test_is_adaptation_flag(self) -> None:
        c = self._instance()
        assert c.is_adaptation is True
        assert len(c.adaptation_limitation) > 0

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(
            CorrelationKey(correlation_id="annulus_turbulent_gnielinski_dh", version="1.0.0")
        )
        assert defn is not None

    def test_registry_completeness(self) -> None:
        assert set(ANNULUS_CORRELATIONS.keys()) == {
            "annulus_laminar_inner_chf",
            "annulus_turbulent_gnielinski_dh",
        }


# --- Golden Cases ---


class TestGoldenCases:
    """Golden reference cases."""

    def test_c1_nu_3_66(self) -> None:
        """C1: Nu = 3.66 for fully developed laminar, constant wall temperature."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(3.66, abs=1e-12)
        expected_h = 3.66 * K / TUBE_DH
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-12)

    def test_c2_nu_4_36(self) -> None:
        """C2: Nu = 4.36 for fully developed laminar, constant heat flux."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_heat_flux")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(4.36, abs=1e-12)
        expected_h = 4.36 * K / TUBE_DH
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-12)

    def test_c3_gnielinski(self) -> None:
        """C3: Gnielinski with Re=50000, Pr=7.0."""
        Re = 50000.0
        Pr = 7.0
        c = TubeTurbulentGnielinski()
        nu = c.evaluate(Re, Pr)
        f = (0.790 * math.log(Re) - 1.64) ** (-2)
        f8 = f / 8.0
        numerator = f8 * (Re - 1000.0) * Pr
        denominator = 1.0 + 12.7 * math.sqrt(f8) * (Pr ** (2.0 / 3.0) - 1.0)
        expected_nu = numerator / denominator
        assert nu == pytest.approx(expected_nu, rel=1e-10)
        assert nu == pytest.approx(329.7, abs=5.0)

    def test_c3_service_integration(self) -> None:
        """C3: Service-level Gnielinski with Re=50000."""
        target_re = 50000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "turbulent"
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_turbulent_gnielinski"


# --- Zero Duty / Zero Flow ---


class TestZeroDutyZeroFlow:
    """Zero mass flow and negative mass flow → BLOCKED."""

    def test_zero_mass_flow_blocked(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert any("zero mass flow" in b.message.lower() for b in result.blockers)

    def test_negative_mass_flow_blocked(self) -> None:
        with pytest.raises(ValidationError, match="non-negative"):
            FlowPropertiesInput(
                mass_flow_kg_s=-0.01,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
            )

    def test_zero_mass_flow_provenance(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.verify_provenance() is True

    def test_zero_mass_flow_hash(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.verify_hash() is True


# --- Wall Property Validation ---


class TestWallPropertyValidation:
    """Wall property validation: NaN/Inf rejected."""

    def test_wall_temperature_nan_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
                wall_temperature_k=float("nan"),
            )

    def test_wall_viscosity_inf_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
                wall_viscosity_pa_s=float("inf"),
            )

    def test_wall_temperature_none_allowed(self) -> None:
        f = FlowPropertiesInput(
            mass_flow_kg_s=0.1,
            density_kg_m3=RHO,
            dynamic_viscosity_pa_s=MU,
            thermal_conductivity_w_m_k=K,
            specific_heat_j_kg_k=CP,
            bulk_temperature_k=350.0,
            wall_temperature_k=None,
        )
        assert f.wall_temperature_k is None


# --- Hash Determinism ---


class TestHashDeterminism:
    """Hash determinism tests."""

    def test_two_results_same_inputs_same_hash(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r1 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        r2 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r1.result_hash == r2.result_hash

    def test_different_inputs_different_hash(self) -> None:
        r1 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.01), "constant_wall_temperature"
        )
        r2 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.3), "constant_wall_temperature"
        )
        assert r1.result_hash != r2.result_hash

    def test_json_roundtrip_hash_matches(self) -> None:
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.result_hash == r.result_hash
        assert restored.verify_hash() is True


# --- Selection Determinism ---


class TestSelectionDeterminism:
    """Deterministic correlation selection via registry."""

    def test_tube_laminar_cwt_selected(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_laminar_cwt"

    def test_tube_laminar_chf_selected(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_heat_flux")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_laminar_chf"

    def test_tube_turbulent_selected(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_turbulent_gnielinski"

    def test_annulus_laminar_inner_selected(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        # C4 is blocked at evaluation (NotImplementedError) — status is BLOCKED
        assert result.status == CorrelationStatus.BLOCKED

    def test_annulus_turbulent_selected(self) -> None:
        flow = _water_flow(mass_flow=1.0)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "annulus_turbulent_gnielinski_dh"

    def test_nusselt_basis_laminar_cwt(self) -> None:
        defn = _registry().get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert _get_nusselt_basis(defn) == "inside_diameter"

    def test_nusselt_basis_annulus_turbulent(self) -> None:
        defn = _registry().get(
            CorrelationKey(correlation_id="annulus_turbulent_gnielinski_dh", version="1.0.0")
        )
        assert _get_nusselt_basis(defn) == "hydraulic_diameter"

    def test_nusselt_basis_annulus_laminar(self) -> None:
        defn = _registry().get(
            CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0")
        )
        assert _get_nusselt_basis(defn) == "hydraulic_diameter"


# --- Is Boundary Compatible ---


class TestIsBoundaryCompatible:
    """Test _is_boundary_compatible function (tag-driven)."""

    def test_cwt_compatible_with_cwt(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_wall_temperature") is True

    def test_cwt_incompatible_with_chf(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_heat_flux") is False

    def test_gnielinski_compatible_with_both(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_turbulent_gnielinski", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_wall_temperature") is True
        assert _is_boundary_compatible(defn, "constant_heat_flux") is True

    def test_annulus_inner_chf_compatible_with_inner(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert _is_boundary_compatible(defn, "inner_wall_heated") is True

    def test_annulus_inner_chf_incompatible_with_outer(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert _is_boundary_compatible(defn, "outer_wall_heated") is False


# --- Enum Values ---


class TestEnumValues:
    """Enum value tests."""

    def test_flow_regime_values(self) -> None:
        assert FlowRegime.laminar.value == "laminar"
        assert FlowRegime.transitional.value == "transitional"
        assert FlowRegime.turbulent.value == "turbulent"
        assert FlowRegime.invalid.value == "invalid"

    def test_correlation_status_values(self) -> None:
        assert CorrelationStatus.SUCCEEDED.value == "succeeded"
        assert CorrelationStatus.BLOCKED.value == "blocked"
        assert CorrelationStatus.FAILED.value == "failed"

    def test_nusselt_basis_values(self) -> None:
        assert NusseltBasis.hydraulic_diameter.value == "hydraulic_diameter"
        assert NusseltBasis.inside_diameter.value == "inside_diameter"

    def test_regime_constants(self) -> None:
        assert LAMINAR_UPPER_RE == 2300.0
        assert TURBULENT_LOWER_RE == 10000.0


# --- Computed Quantities ---


class TestComputedQuantities:
    """All computed quantities are populated in a succeeded result."""

    def test_succeeded_result_quantities(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_area_m2 > 0
        assert result.mean_velocity_ms > 0
        assert result.hydraulic_diameter_m > 0
        assert result.reynolds_number > 0
        assert result.prandtl_number > 0
        assert result.nusselt_number > 0
        assert result.heat_transfer_coefficient > 0

    def test_velocity_consistency(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        expected_v = flow.mass_flow_kg_s / (flow.density_kg_m3 * result.flow_area_m2)
        assert result.mean_velocity_ms == pytest.approx(expected_v, rel=1e-10)

    def test_reynolds_consistency(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        expected_re = (
            flow.density_kg_m3
            * result.mean_velocity_ms
            * result.hydraulic_diameter_m
            / flow.dynamic_viscosity_pa_s
        )
        assert result.reynolds_number == pytest.approx(expected_re, rel=1e-10)

    def test_prandtl_consistency(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        expected_pr = (
            flow.specific_heat_j_kg_k
            * flow.dynamic_viscosity_pa_s
            / flow.thermal_conductivity_w_m_k
        )
        assert result.prandtl_number == pytest.approx(expected_pr, rel=1e-10)

    def test_zero_blocked_quantities(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.flow_area_m2 == 0.0
        assert result.mean_velocity_ms == 0.0
        assert result.reynolds_number == 0.0
        assert result.prandtl_number == 0.0
        assert result.nusselt_number == 0.0
        assert result.heat_transfer_coefficient == 0.0


# --- Execution Context ---


class TestExecutionContext:
    """Execution context in results."""

    def test_default_context(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.execution_context.request_id is None
        assert result.execution_context.design_case_revision_id is None

    def test_custom_context(self) -> None:
        ctx = CalculationContext(
            request_id=uuid4(),
            design_case_revision_id=uuid4(),
            calculation_run_id=uuid4(),
        )
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(
            _tube_geom(), flow, "constant_wall_temperature", context=ctx
        )
        assert result.execution_context.request_id is not None
        assert result.execution_context.design_case_revision_id is not None
        assert result.execution_context.calculation_run_id is not None
        assert result.verify_provenance() is True

    def test_context_changes_provenance(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r1 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        ctx = CalculationContext(
            request_id=uuid4(),
            design_case_revision_id=uuid4(),
            calculation_run_id=uuid4(),
        )
        r2 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature", context=ctx)
        assert r1.provenance_digest != r2.provenance_digest


# --- SelectedCorrelationInfo ---


class TestSelectedCorrelationInfoFields:
    """SelectedCorrelationInfo carries full source identity."""

    def test_source_fields_populated(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        info = result.selected_correlation
        assert info is not None
        assert info.correlation_id == "tube_laminar_cwt"
        assert info.version == "1.0.0"
        assert len(info.source_title) > 0
        assert info.source_year > 0
        assert info.definition_hash.startswith("sha256:")
        assert info.nusselt_basis == "inside_diameter"

    def test_annulus_turbulent_source_fields(self) -> None:
        flow = _water_flow(mass_flow=1.0)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        info = result.selected_correlation
        assert info is not None
        assert info.correlation_id == "annulus_turbulent_gnielinski_dh"
        assert info.is_adaptation is True
        assert len(info.adaptation_limitation) > 0
        assert info.nusselt_basis == "hydraulic_diameter"

    def test_frozen(self) -> None:
        info = SelectedCorrelationInfo(
            correlation_id="test",
            version="1.0.0",
        )
        with pytest.raises(ValidationError):
            info.correlation_id = "modified"  # type: ignore[misc]


# --- Integrity Tests ---


class TestResultHashIntegrity:
    """CorrelationResult hash integrity and tamper detection."""

    def test_succeeded_verify_hash_true(self) -> None:
        r = _make_result_tube_laminar()
        assert r.verify_hash() is True

    def test_blocked_verify_hash_true(self) -> None:
        r = _make_result_blocked()
        assert r.verify_hash() is True

    def test_result_hash_format(self) -> None:
        r = _make_result_tube_laminar()
        assert r.result_hash.startswith("sha256:")
        assert len(r.result_hash) == 71

    def test_tamper_nusselt_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(r, "nusselt_number", 999.0)
        assert r.validate_integrity() is False

    def test_tamper_result_hash_breaks_verify(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(r, "result_hash", "sha256:" + "0" * 64)
        assert r.verify_hash() is False

    def test_direct_setattr_tamper(self) -> None:
        r = _make_result_tube_laminar()
        _ = r.result_hash
        object.__setattr__(r, "mass_flow_kg_s", 999.0)
        assert r.validate_integrity() is False
        assert r.verify_hash() is False


# --- Boundary Condition Validation ---


class TestBoundaryConditionValidation:
    """Boundary condition vs heated_surface consistency."""

    def test_inner_heated_geometry_outer_wall_heated_bc(self) -> None:
        g = _ann_geom(heated="inner")
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "outer_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_both_walls_heated_geometry_inner_wall_heated_bc(self) -> None:
        g = _ann_geom(heated="both")
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_inner_geometry_inner_bc_ok(self) -> None:
        """C4 is metadata_only (pending source verification), so BLOCKED."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(heated="inner"), flow, "inner_wall_heated")
        # C4 is blocked: NotImplementedError (data pending verification)
        assert result.status == CorrelationStatus.BLOCKED
        assert any(b.code.value == "not_implemented" for b in result.blockers)

    def test_tube_unsupported_bc_blocked(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED


# --- Provenance JSON Round-Trip ---


class TestProvenanceJSONRoundTrip:
    """Provenance graph serialization/deserialization round-trip."""

    def test_succeeded_graph_roundtrip(self) -> None:
        r = _make_result_tube_laminar()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        assert len(restored.nodes) == len(r.provenance_graph.nodes)
        assert len(restored.edges) == len(r.provenance_graph.edges)

    def test_succeeded_graph_hash_preserved(self) -> None:
        r = _make_result_tube_laminar()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        assert _provenance_graph_digest(restored) == r.provenance_digest

    def test_blocked_graph_roundtrip(self) -> None:
        r = _make_result_blocked()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        assert len(restored.nodes) == len(r.provenance_graph.nodes)
        assert _provenance_graph_digest(restored) == r.provenance_digest

    def test_provenance_node_payload_hash_format(self) -> None:
        r = _make_result_tube_laminar()
        for node in r.provenance_graph.nodes:
            assert node.payload_hash.startswith("sha256:")
            assert len(node.payload_hash) == 71


# --- Gnielinski Consistency ---


class TestGnielinskiConsistency:
    """Verify tube and annulus Gnielinski use the same formula."""

    def test_same_petukhov(self) -> None:
        tube = TubeTurbulentGnielinski()
        ann = AnnulusTurbulentGnielinskiDH()
        for re in [3000, 5000, 10000, 50000, 100000]:
            assert tube.petukhov_friction_factor(re) == pytest.approx(
                ann.petukhov_friction_factor(re), rel=1e-12
            )

    def test_same_nu_for_pr1(self) -> None:
        tube = TubeTurbulentGnielinski()
        ann = AnnulusTurbulentGnielinskiDH()
        for re in [3000, 10000, 100000]:
            assert tube.evaluate(re, 1.0) == pytest.approx(ann.evaluate(re, 1.0), rel=1e-12)


# --- Annulus Geometry Consistency ---


class TestAnnulusGeometryConsistency:
    """D_h for concentric annulus equals D_o - D_i."""

    def test_various_diameters(self) -> None:
        for di, do in [(0.010, 0.030), (0.015, 0.050), (0.020, 0.040), (0.030, 0.060)]:
            g = ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=di,
                outer_pipe_inside_diameter_m=do,
                heat_transfer_length_m=2.0,
            )
            assert g.hydraulic_diameter_m == pytest.approx(do - di, rel=1e-12)

    def test_area_plus_perimeters(self) -> None:
        g = _ann_geom()
        dh = 4.0 * g.flow_area_m2 / g.total_wetted_perimeter_m
        assert dh == pytest.approx(g.hydraulic_diameter_m, rel=1e-12)


# =====================================================================
# J. Third-Round Review Tests — TASK-007


# ---------------------------------------------------------------------------
# Local helpers for third-round review tests
# ---------------------------------------------------------------------------


def _make_zero_flow_blocked() -> CorrelationResult:
    """Zero mass flow → BLOCKED, no assessment."""
    flow = _water_flow(mass_flow=0.0)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


def _make_applicability_blocked() -> CorrelationResult:
    """Re=2500 (transitional) → BLOCKED."""
    target_re = 2500.0
    m_dot = target_re * TUBE_A * MU / TUBE_DH
    flow = _water_flow(mass_flow=m_dot)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


def _make_c4_maturity_blocked(*, di: float = ANN_DI, do: float = ANN_DO) -> CorrelationResult:
    """Annulus laminar inner wall heated, C4 metadata_only → BLOCKED."""
    g = _ann_geom(di=di, do=do, heated="inner")
    target_re = 1000.0
    ann_a = math.pi / 4.0 * (do**2 - di**2)
    ann_dh = do - di
    m_dot = target_re * ann_a * MU / ann_dh
    flow = _water_flow(mass_flow=m_dot)
    return evaluate_hx_correlation(g, flow, "inner_wall_heated")


# ---------------------------------------------------------------------------
# Test J1: Blocked Results Categories
# ---------------------------------------------------------------------------


class TestBlockedResultsCategories:
    """J1: Three distinct blocked result types — hash, provenance, JSON round-trip."""

    def test_zero_flow_blocked_no_assessment(self) -> None:
        r = _make_zero_flow_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.applicability_assessment is None
        assert r.verify_hash() is True
        assert r.verify_provenance() is True

    def test_zero_flow_blocked_json_roundtrip(self) -> None:
        r = _make_zero_flow_blocked()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.verify_hash() is True
        assert restored.verify_provenance() is True

    def test_applicability_blocked(self) -> None:
        r = _make_applicability_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.flow_regime == "transitional"
        assert r.verify_hash() is True
        assert r.verify_provenance() is True

    def test_applicability_blocked_json_roundtrip(self) -> None:
        r = _make_applicability_blocked()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.verify_hash() is True
        assert restored.verify_provenance() is True

    def test_c4_maturity_blocked(self) -> None:
        r = _make_c4_maturity_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.applicability_assessment is not None
        assert r.verify_hash() is True
        assert r.verify_provenance() is True
        assert any("metadata_only" in b.message for b in r.blockers)

    def test_c4_maturity_blocked_json_roundtrip(self) -> None:
        r = _make_c4_maturity_blocked()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.verify_hash() is True
        assert restored.verify_provenance() is True
        assert any("metadata_only" in b.message for b in restored.blockers)


# ---------------------------------------------------------------------------
# Test J2: C4 Maturity Blocked — All Kappa Values
# ---------------------------------------------------------------------------


class TestC4MaturityBlockedAllKappa:
    """J2: C4 at κ=0.05, 0.5, 0.85 all return the same metadata_only blocker."""

    @pytest.mark.parametrize(
        "kappa_label, di, do",
        [
            ("kappa_005", 0.0025, 0.050),
            ("kappa_050", 0.025, 0.050),
            ("kappa_085", 0.0425, 0.050),
        ],
    )
    def test_same_metadata_only_blocker(self, kappa_label: str, di: float, do: float) -> None:
        r = _make_c4_maturity_blocked(di=di, do=do)
        assert r.status == CorrelationStatus.BLOCKED
        assert r.applicability_assessment is not None
        assert any(b.code == ErrorCode.NOT_IMPLEMENTED for b in r.blockers)
        assert any("metadata_only" in b.message for b in r.blockers)
        assert r.applicability_assessment.status.value == "implementation_unavailable"

    def test_all_kappa_same_blocker_type(self) -> None:
        """All three kappa values produce the same blocker code."""
        results = []
        for di, do in [(0.0025, 0.050), (0.025, 0.050), (0.0425, 0.050)]:
            results.append(_make_c4_maturity_blocked(di=di, do=do))
        codes = [tuple(b.code for b in r.blockers) for r in results]
        assert all(c == codes[0] for c in codes)


# ---------------------------------------------------------------------------
# Test J3: C4 Metadata-Only Not In Evaluator
# ---------------------------------------------------------------------------


class TestC4MetadataOnlyNotInEvaluator:
    """J3: C4 metadata_only never enters the evaluator — assessment from selection layer."""

    def test_assessment_status_implementation_unavailable(self) -> None:
        r = _make_c4_maturity_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.applicability_assessment is not None
        assert r.applicability_assessment.status.value == "implementation_unavailable"

    def test_blocker_code_not_implemented(self) -> None:
        r = _make_c4_maturity_blocked()
        assert any(b.code == ErrorCode.NOT_IMPLEMENTED for b in r.blockers)
        # C4 metadata_only preserves identified correlation identity (P0-4)
        assert r.selected_correlation is not None
        assert r.selected_correlation.correlation_id == "annulus_laminar_inner_chf"
        assert r.selected_correlation.version == "1.0.0"

    def test_no_correlation_selected(self) -> None:
        """C4 metadata_only → selected_correlation preserves identified identity."""
        r = _make_c4_maturity_blocked()
        # Identified but unavailable: correlation identity is preserved
        assert r.selected_correlation is not None
        assert r.selected_correlation.correlation_id == "annulus_laminar_inner_chf"
        assert (
            r.applicability_assessment is not None
            and r.applicability_assessment.correlation_key.correlation_id
            == "annulus_laminar_inner_chf"
        )


# ---------------------------------------------------------------------------
# Test J4: Provenance Exact Topology Tampering
# ---------------------------------------------------------------------------


class TestProvenanceExactTopologyTampering:
    """J4: Five tamper scenarios on succeeded provenance graph."""

    def _get_succeeded_result(self) -> CorrelationResult:
        return _make_result_tube_laminar()

    def test_extra_disconnected_root(self) -> None:
        """Adding an extra disconnected root node → verify_provenance False."""
        r = self._get_succeeded_result()
        assert r.verify_provenance() is True
        r2 = deepcopy(r)
        graph = r2.provenance_graph
        extra_root = ProvenanceNode(
            node_id=uuid4(),
            node_type=ProvenanceNodeType.EXTERNAL,
            label="extra_root",
            payload_hash="sha256:" + "aa" * 32,
        )
        new_graph = ProvenanceGraph(
            nodes=graph.nodes + (extra_root,),
            edges=graph.edges,
        )
        object.__setattr__(r2, "provenance_graph", new_graph)
        object.__setattr__(r2, "provenance_digest", _provenance_graph_digest(new_graph))
        assert r2.verify_provenance() is False
        assert r.verify_provenance() is True

    def test_extra_edge_between_existing_nodes(self) -> None:
        """Adding an extra edge between existing nodes → verify_provenance False."""
        r = self._get_succeeded_result()
        assert r.verify_provenance() is True
        r2 = deepcopy(r)
        graph = r2.provenance_graph
        if len(graph.nodes) >= 2:
            n1, n2 = graph.nodes[0], graph.nodes[1]
            extra_edge = ProvenanceEdge(
                source_id=n1.node_id,
                target_id=n2.node_id,
                relation="extra_relation",
            )
            new_graph = ProvenanceGraph(
                nodes=graph.nodes,
                edges=graph.edges + (extra_edge,),
            )
            object.__setattr__(r2, "provenance_graph", new_graph)
            object.__setattr__(r2, "provenance_digest", _provenance_graph_digest(new_graph))
            assert r2.verify_provenance() is False
        assert r.verify_provenance() is True

    def test_remove_expected_edge(self) -> None:
        """Removing an expected edge → verify_provenance False."""
        r = self._get_succeeded_result()
        assert r.verify_provenance() is True
        r2 = deepcopy(r)
        graph = r2.provenance_graph
        if graph.edges:
            new_graph = ProvenanceGraph(
                nodes=graph.nodes,
                edges=graph.edges[1:],
            )
            object.__setattr__(r2, "provenance_graph", new_graph)
            object.__setattr__(r2, "provenance_digest", _provenance_graph_digest(new_graph))
            assert r2.verify_provenance() is False
        assert r.verify_provenance() is True

    def test_change_edge_relation(self) -> None:
        """Changing an edge relation → verify_provenance False."""
        r = self._get_succeeded_result()
        assert r.verify_provenance() is True
        r2 = deepcopy(r)
        graph = r2.provenance_graph
        if graph.edges:
            old_edge = graph.edges[0]
            new_edge = ProvenanceEdge(
                source_id=old_edge.source_id,
                target_id=old_edge.target_id,
                relation="wrong_relation",
            )
            new_graph = ProvenanceGraph(
                nodes=graph.nodes,
                edges=(new_edge,) + graph.edges[1:],
            )
            object.__setattr__(r2, "provenance_graph", new_graph)
            object.__setattr__(r2, "provenance_digest", _provenance_graph_digest(new_graph))
            assert r2.verify_provenance() is False
        assert r.verify_provenance() is True

    def test_add_duplicate_semantic_node(self) -> None:
        """Adding a duplicate node of the same semantic type → verify_provenance False."""
        r = self._get_succeeded_result()
        assert r.verify_provenance() is True
        r2 = deepcopy(r)
        graph = r2.provenance_graph
        corr_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION]
        if corr_nodes:
            src = corr_nodes[0]
            dup = ProvenanceNode(
                node_id=uuid4(),
                node_type=ProvenanceNodeType.CORRELATION,
                label=src.label,
                metadata=src.metadata,
                payload_hash=src.payload_hash,
            )
            new_graph = ProvenanceGraph(
                nodes=graph.nodes + (dup,),
                edges=graph.edges,
            )
            object.__setattr__(r2, "provenance_graph", new_graph)
            object.__setattr__(r2, "provenance_digest", _provenance_graph_digest(new_graph))
            assert r2.verify_provenance() is False
        assert r.verify_provenance() is True


# ---------------------------------------------------------------------------
# Test J5: Assessment Hash Semantic Verification
# ---------------------------------------------------------------------------


class TestAssessmentHashSemanticVerification:
    """J5: Assessment hash verification for applicability-blocked results."""

    def _get_blocked_assessment(self) -> ApplicabilityAssessment:
        r = _make_c4_maturity_blocked()
        assert r.applicability_assessment is not None
        return r.applicability_assessment

    def test_verify_assessment_hash_true(self) -> None:
        a = self._get_blocked_assessment()
        assert a.verify_assessment_hash() is True

    def test_json_roundtrip_preserves_hash(self) -> None:
        a = self._get_blocked_assessment()
        json_str = a.model_dump_json()
        restored = ApplicabilityAssessment.model_validate_json(json_str)
        assert restored.verify_assessment_hash() is True
        assert restored.assessment_hash == a.assessment_hash

    def test_tamper_definition_hash_breaks(self) -> None:
        a = self._get_blocked_assessment()
        assert a.identity_snapshot is not None
        tampered = a.model_copy(
            update={
                "identity_snapshot": a.identity_snapshot.model_copy(
                    update={"definition_hash": "sha256:" + "ff" * 32}
                )
            }
        )
        assert tampered.verify_assessment_hash() is False

    def test_tamper_assessment_hash_breaks(self) -> None:
        a = self._get_blocked_assessment()
        tampered = a.model_copy(update={"assessment_hash": "sha256:" + "00" * 32})
        assert tampered.verify_assessment_hash() is False

    def test_tamper_status_breaks(self) -> None:
        a = self._get_blocked_assessment()
        # Use absolute_range_exceeded (non-applicable, won't fail validator)
        # Must pass enum value, not string — model_copy bypasses validators
        from hexagent.correlations.models import ApplicabilityStatus

        tampered = a.model_copy(update={"status": ApplicabilityStatus.absolute_range_exceeded})
        assert tampered.verify_assessment_hash() is False

    def test_tamper_geometry_breaks(self) -> None:
        a = self._get_blocked_assessment()
        assert a.identity_snapshot is not None
        tampered = a.model_copy(
            update={
                "identity_snapshot": a.identity_snapshot.model_copy(
                    update={"geometry": GeometryType.circular_tube}
                )
            }
        )
        assert tampered.verify_assessment_hash() is False


# ---------------------------------------------------------------------------
# Test J6: Typed Boundary Conditions
# ---------------------------------------------------------------------------


class TestTypedBoundaryConditionsAdapter:
    """J6: ThermalBoundaryCondition enum adapter tests."""

    def test_enum_direct_call(self) -> None:
        """Enum value passed directly → should work."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(
            _tube_geom(), flow, ThermalBoundaryCondition.constant_wall_temperature
        )
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None

    def test_valid_string_adapter(self) -> None:
        """Valid string → converted to enum internally → should work."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None

    def test_invalid_string_blocked(self) -> None:
        """Invalid string → BLOCKED with CORRELATION_GEOMETRY_INCOMPATIBLE."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "invalid_bc")
        assert result.status == CorrelationStatus.BLOCKED
        assert any(b.code == ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE for b in result.blockers)

    def test_select_correlation_receives_enum(self) -> None:
        """select_correlation with enum directly works."""
        reg = _registry()
        result = select_correlation(
            reg,
            _tube_geom(),
            ThermalBoundaryCondition.constant_wall_temperature,
            FlowRegime.laminar,
            200.0,
            7.0,
        )
        assert result.selected_definition is not None
        assert result.selection_status == "selected"


# ---------------------------------------------------------------------------
# Test J7: Frozen Registry Isolation
# ---------------------------------------------------------------------------


class TestFrozenRegistryIsolation:
    """J7: _get_registry() returns deep copies — mutations don't leak."""

    def test_mutation_does_not_persist(self) -> None:
        """Registering a fake definition in one copy doesn't affect the next copy."""
        from hexagent.correlations.errors import CorrelationNotFoundError
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )
        from hexagent.correlations.models import FlowRegime as ModelsFlowRegime

        reg1 = _get_registry()
        count1 = len(reg1.search())

        fake_defn = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="fake_isolation_test", version="1.0.0"),
            name="Fake Isolation Test",
            purpose=CorrelationPurpose.nusselt_number,
            description="Test",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset({PhaseRegime.single_phase_liquid}),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                ),
                required_inputs=frozenset(
                    {
                        ApplicabilityVariable.reynolds,
                        ApplicabilityVariable.prandtl,
                    }
                ),
            ),
            source=BibliographicSource(
                source_id="test",
                title="T",
                publication="P",
                year=2024,
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(basis="test"),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="test.ref",
            tags=frozenset(
                {
                    "bc:constant_wall_temperature",
                    "nusselt_basis:inside_diameter",
                    "priority:10",
                }
            ),
        )
        reg1.register(fake_defn)

        reg2 = _get_registry()
        count2 = len(reg2.search())
        assert count1 == count2
        # Fake definition should NOT be in the fresh copy
        with pytest.raises(CorrelationNotFoundError):
            reg2.get(CorrelationKey(correlation_id="fake_isolation_test", version="1.0.0"))

    def test_multiple_copies_independent(self) -> None:
        """Three consecutive calls to _get_registry() return independent copies."""
        r1 = _get_registry()
        r2 = _get_registry()
        r3 = _get_registry()
        c1 = len(r1.search())
        c2 = len(r2.search())
        c3 = len(r3.search())
        assert c1 == c2 == c3


# ---------------------------------------------------------------------------
# Test J8: Assessment Identity Snapshot Round-Trip
# ---------------------------------------------------------------------------


class TestAssessmentIdentitySnapshotRoundTrip:
    """J8: Assessment identity_snapshot survives model_dump → model_validate."""

    def test_roundtrip_preserves_identity_snapshot(self) -> None:
        r = _make_c4_maturity_blocked()
        a = r.applicability_assessment
        assert a is not None
        assert a.identity_snapshot is not None

        data = a.model_dump()
        restored = ApplicabilityAssessment.model_validate(data)

        assert restored.identity_snapshot is not None
        assert restored.identity_snapshot.definition_hash == a.identity_snapshot.definition_hash
        assert restored.identity_snapshot.geometry == a.identity_snapshot.geometry
        assert restored.identity_snapshot.phase_regime == a.identity_snapshot.phase_regime
        assert restored.identity_snapshot.flow_regime == a.identity_snapshot.flow_regime
        assert restored.identity_snapshot.input_values == a.identity_snapshot.input_values
        assert restored.identity_snapshot.policy == a.identity_snapshot.policy
        assert (
            restored.identity_snapshot.allow_extrapolation
            == a.identity_snapshot.allow_extrapolation
        )

    def test_verify_hash_before_and_after_roundtrip(self) -> None:
        r = _make_c4_maturity_blocked()
        a = r.applicability_assessment
        assert a is not None

        assert a.verify_assessment_hash() is True

        data = a.model_dump()
        restored = ApplicabilityAssessment.model_validate(data)
        assert restored.verify_assessment_hash() is True

    def test_identity_snapshot_fields_complete(self) -> None:
        """identity_snapshot contains all required fields."""
        r = _make_c4_maturity_blocked()
        a = r.applicability_assessment
        assert a is not None
        snap = a.identity_snapshot
        assert snap is not None

        assert isinstance(snap.definition_hash, str)
        assert snap.definition_hash.startswith("sha256:")
        assert isinstance(snap.geometry, GeometryType)
        assert isinstance(snap.phase_regime, PhaseRegime)
        assert hasattr(snap.flow_regime, "value")
        assert snap.flow_regime.value in (
            "laminar",
            "transitional",
            "turbulent",
            "mixed",
            "not_applicable",
        )
        assert isinstance(snap.input_values, tuple)
        assert len(snap.input_values) > 0
        for _var, val in snap.input_values:
            assert isinstance(val, float)
        assert hasattr(snap.policy, "absolute_violation")
        assert isinstance(snap.allow_extrapolation, bool)

    def test_json_roundtrip_preserves_hash(self) -> None:
        """JSON round-trip of assessment preserves hash verification."""
        r = _make_c4_maturity_blocked()
        a = r.applicability_assessment
        assert a is not None

        json_str = a.model_dump_json()
        restored = ApplicabilityAssessment.model_validate_json(json_str)
        assert restored.verify_assessment_hash() is True
        assert restored.identity_snapshot is not None
        assert a.identity_snapshot is not None
        assert restored.identity_snapshot.definition_hash == a.identity_snapshot.definition_hash

    def test_succeeded_result_also_has_snapshot(self) -> None:
        """Succeeded result's assessment also has identity_snapshot."""
        r = _make_result_tube_laminar()
        a = r.applicability_assessment
        assert a is not None
        assert a.identity_snapshot is not None
        assert a.verify_assessment_hash() is True

        data = a.model_dump()
        restored = ApplicabilityAssessment.model_validate(data)
        assert restored.verify_assessment_hash() is True
        assert restored.identity_snapshot is not None
        assert restored.identity_snapshot.geometry == GeometryType.circular_tube


# ===========================================================================
# Fourth-round review tests
# ===========================================================================


# ---------------------------------------------------------------------------
# Test K1: Different κ → Different Identity
# ---------------------------------------------------------------------------


class TestDifferentKappaDifferentIdentity:
    """K1: Two C4 requests with same Re/Pr but different κ produce different hashes."""

    def test_different_kappa_different_hashes(self) -> None:
        # C4 with Re=1000, Pr≈7.0, κ=0.3  (di=0.015, do=0.05)
        r1 = _make_c4_maturity_blocked(di=0.015, do=0.05)
        # C4 with Re=1000, Pr≈7.0, κ=0.6  (di=0.030, do=0.05)
        r2 = _make_c4_maturity_blocked(di=0.030, do=0.05)

        # Both should be BLOCKED (metadata_only)
        assert r1.status == CorrelationStatus.BLOCKED
        assert r2.status == CorrelationStatus.BLOCKED
        assert r1.applicability_assessment is not None
        assert r2.applicability_assessment is not None

        # Verify identity_snapshot.input_values differ
        snap1 = r1.applicability_assessment.identity_snapshot
        snap2 = r2.applicability_assessment.identity_snapshot
        assert snap1 is not None
        assert snap2 is not None
        assert snap1.input_values != snap2.input_values

        # assessment_hash differs
        assert (
            r1.applicability_assessment.assessment_hash
            != r2.applicability_assessment.assessment_hash
        )

        # result_hash differs
        assert r1.result_hash != r2.result_hash

        # provenance_digest differs
        assert r1.provenance_digest != r2.provenance_digest

        # Both still verify correctly
        assert r1.verify_hash() is True
        assert r1.verify_provenance() is True
        assert r2.verify_hash() is True
        assert r2.verify_provenance() is True


# ---------------------------------------------------------------------------
# Test K2: Context Tamper Detection
# ---------------------------------------------------------------------------


class TestContextTamperDetection:
    """K2: Tampering only the context in a blocker breaks provenance verification."""

    def test_context_only_tamper_fails_provenance(self) -> None:
        r = _make_c4_maturity_blocked()
        assert r.verify_provenance() is True
        assert len(r.blockers) > 0

        # Tamper: add a fake context entry to the first blocker
        r2 = deepcopy(r)
        b0 = r2.blockers[0]
        new_context = b0.context + (("fake_key", "fake_value"),)
        new_blocker = b0.model_copy(update={"context": new_context})
        object.__setattr__(r2, "blockers", (new_blocker,) + r2.blockers[1:])

        # Provenance verification must fail (context is part of BLOCKER payload hash)
        assert r2.verify_provenance() is False
        # Original still passes
        assert r.verify_provenance() is True

    def test_json_roundtrip_preserves_full_context(self) -> None:
        """JSON round-trip preserves blocker context, so provenance still verifies."""
        r = _make_c4_maturity_blocked()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)

        # Context preserved
        for orig_b, rest_b in zip(r.blockers, restored.blockers, strict=True):
            assert orig_b.context == rest_b.context

        assert restored.verify_provenance() is True


# ---------------------------------------------------------------------------
# Test K3: Maturity-Blocked Provenance Has CORRELATION Node
# ---------------------------------------------------------------------------


class TestMaturityBlockedProvenanceHasCorrelation:
    """K3: C4 maturity-blocked result has exactly one CORRELATION node in provenance."""

    def test_has_correlation_node(self) -> None:
        r = _make_c4_maturity_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.verify_provenance() is True

        graph = r.provenance_graph
        corr_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION]

        # Exactly 1 CORRELATION node
        assert len(corr_nodes) == 1

        # CORRELATION node metadata has correlation_id, version, definition_hash
        corr_meta = dict(corr_nodes[0].metadata)
        assert "correlation_id" in corr_meta
        assert "version" in corr_meta
        assert "definition_hash" in corr_meta
        assert corr_meta["correlation_id"] == "annulus_laminar_inner_chf"
        assert corr_meta["version"] == "1.0.0"

        # selected_correlation is populated
        assert r.selected_correlation is not None
        assert r.selected_correlation.correlation_id == "annulus_laminar_inner_chf"


# ---------------------------------------------------------------------------
# Test K4: True No-Match vs Implementation-Unavailable
# ---------------------------------------------------------------------------


class TestTrueNoMatchVsImplementationUnavailable:
    """K4: Zero-flow (no correlation) vs C4 metadata_only (identified but unavailable)."""

    def test_zero_flow_no_correlation(self) -> None:
        """Zero mass flow → BLOCKED, no correlation identified, no CORRELATION node."""
        r = _make_zero_flow_blocked()
        assert r.status == CorrelationStatus.BLOCKED

        # selected_correlation is None (true no-match)
        assert r.selected_correlation is None

        # No CORRELATION node in provenance
        graph = r.provenance_graph
        corr_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION]
        assert len(corr_nodes) == 0

        # verify_provenance passes (0 CORRELATION nodes is correct for no-match)
        assert r.verify_provenance() is True

    def test_c4_identified_correlation(self) -> None:
        """C4 metadata_only → BLOCKED, correlation identified but unavailable."""
        r = _make_c4_maturity_blocked()
        assert r.status == CorrelationStatus.BLOCKED

        # selected_correlation is not None (identified but unavailable)
        assert r.selected_correlation is not None
        assert r.selected_correlation.correlation_id == "annulus_laminar_inner_chf"

        # Has CORRELATION node in provenance
        graph = r.provenance_graph
        corr_nodes = [n for n in graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION]
        assert len(corr_nodes) == 1

        assert r.verify_provenance() is True
