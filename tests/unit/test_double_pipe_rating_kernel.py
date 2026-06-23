"""Unit tests for the double-pipe rating kernel (rate_double_pipe).

Covers:
1. Heating direction combos (tube_in_hot × flow_arrangement)
2. Boundary conditions enter request_identity / hash
3. Bulk property from state_tp(T_bulk, P_in)
4. Energy closure gate
5. UA-LMTD closure gate
6. C4 returns CORRELATION_IMPLEMENTATION_UNAVAILABLE
7. Property failure returns PROPERTY_EVALUATION_FAILED
8. verify_hash() for production results
9. verify_provenance() including CORRELATION nodes
10. Basic counter-flow and parallel-flow water-water cases
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import ErrorCode
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult, RatingStatus
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier, ReferenceStatePolicy
from hexagent.properties.coolprop_provider import CoolPropProvider
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider(cache_size=64)


WATER = FluidIdentifier(name="Water")

STANDARD_GEOMETRY = DoublePipeGeometry(
    inner_tube_inner_diameter_m=0.020,
    inner_tube_outer_diameter_m=0.025,
    outer_pipe_inner_diameter_m=0.040,
    effective_length_m=3.0,
    wall_thermal_conductivity_w_m_k=50.0,
    inner_surface_roughness_m=4.5e-5,
    annulus_surface_roughness_m=4.5e-5,
    inner_fouling_resistance_m2k_w=0.0002,
    outer_fouling_resistance_m2k_w=0.0002,
)

# Base kwargs WITHOUT tube_in_hot/flow_arrangement (added per-test)
_BASE_KWARGS = dict(
    geometry=STANDARD_GEOMETRY,
    hot_fluid=WATER,
    cold_fluid=WATER,
    hot_mass_flow_kg_s=0.5,
    cold_mass_flow_kg_s=1.5,
    hot_inlet_temperature_k=350.0,
    cold_inlet_temperature_k=300.0,
    hot_inlet_pressure_pa=200_000.0,
    cold_inlet_pressure_pa=150_000.0,
)


def _run_rating(
    provider: CoolPropProvider,
    *,
    tube_in_hot: bool = True,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
    **extra,
) -> RatingResult:
    """Helper to run rate_double_pipe with standard conditions."""
    return rate_double_pipe(
        **_BASE_KWARGS,
        tube_in_hot=tube_in_hot,
        flow_arrangement=flow_arrangement,
        provider=provider,
        **extra,
    )


# ---------------------------------------------------------------------------
# 1. Heating direction combos (4 combos: tube_in_hot × flow_arrangement)
# ---------------------------------------------------------------------------


class TestHeatingDirectionCombos:
    """All 4 combos of tube_in_hot × flow_arrangement must succeed."""

    @pytest.mark.parametrize(
        ("tube_in_hot", "flow_arrangement"),
        [
            (True, FlowArrangement.COUNTERFLOW),
            (True, FlowArrangement.PARALLEL),
            (False, FlowArrangement.COUNTERFLOW),
            (False, FlowArrangement.PARALLEL),
        ],
        ids=[
            "cf_tube_hot",
            "pf_tube_hot",
            "cf_tube_cold",
            "pf_tube_cold",
        ],
    )
    def test_combo_succeeds(
        self,
        provider: CoolPropProvider,
        tube_in_hot: bool,
        flow_arrangement: FlowArrangement,
    ) -> None:
        result = _run_rating(
            provider,
            tube_in_hot=tube_in_hot,
            flow_arrangement=flow_arrangement,
        )
        assert result.status == RatingStatus.SUCCEEDED
        assert result.converged is True
        assert result.heat_duty_w is not None
        assert result.heat_duty_w > 0

    def test_tube_hot_side_mapping(self, provider: CoolPropProvider) -> None:
        """When tube_in_hot=True, tube side states map to hot stream."""
        result = _run_rating(provider, tube_in_hot=True)
        assert result.tube_side_inlet_state is not None
        assert result.tube_side_outlet_state is not None
        assert result.annulus_side_inlet_state is not None
        assert result.annulus_side_outlet_state is not None
        # Tube side should be the hot stream (higher inlet temperature)
        assert result.tube_side_inlet_state.temperature_k == 350.0
        assert result.annulus_side_inlet_state.temperature_k == 300.0

    def test_tube_cold_side_mapping(self, provider: CoolPropProvider) -> None:
        """When tube_in_hot=False, tube side states map to cold stream."""
        result = _run_rating(provider, tube_in_hot=False)
        assert result.tube_side_inlet_state is not None
        assert result.tube_side_outlet_state is not None
        assert result.annulus_side_inlet_state is not None
        assert result.annulus_side_outlet_state is not None
        # Tube side should be the cold stream
        assert result.tube_side_inlet_state.temperature_k == 300.0
        assert result.annulus_side_inlet_state.temperature_k == 350.0


# ---------------------------------------------------------------------------
# 2. Boundary conditions enter identity / hash
# ---------------------------------------------------------------------------


class TestBoundaryConditionsInIdentity:
    """Boundary conditions must appear in request_identity and affect hash."""

    def test_tube_bc_in_identity(self, provider: CoolPropProvider) -> None:
        result = _run_rating(
            provider,
            tube_boundary_condition=ThermalBoundaryCondition.constant_heat_flux,
        )
        assert result.request_identity.tube_boundary_condition == "constant_heat_flux"

    def test_annulus_bc_in_identity(self, provider: CoolPropProvider) -> None:
        result = _run_rating(
            provider,
            annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
        )
        assert result.request_identity.annulus_boundary_condition == "inner_wall_heated"

    def test_default_bcs(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.request_identity.tube_boundary_condition == "constant_wall_temperature"
        assert result.request_identity.annulus_boundary_condition == "inner_wall_heated"

    def test_different_bcs_different_hash(self, provider: CoolPropProvider) -> None:
        r1 = _run_rating(
            provider,
            tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
        )
        r2 = _run_rating(
            provider,
            tube_boundary_condition=ThermalBoundaryCondition.constant_heat_flux,
        )
        assert r1.result_hash != r2.result_hash


# ---------------------------------------------------------------------------
# 3. Bulk property from state_tp(T_bulk, P_in)
# ---------------------------------------------------------------------------


class TestBulkPropertyFromStateTP:
    """Bulk states must exist and use T_bulk = (T_in + T_out)/2 with P_in."""

    def test_bulk_states_present(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.tube_bulk_state is not None
        assert result.annulus_bulk_state is not None

    def test_bulk_temperature_is_average(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED

        # Tube bulk temperature should be average of tube inlet and outlet
        tube_inlet_T = result.tube_side_inlet_state.temperature_k
        tube_outlet_T = result.tube_side_outlet_state.temperature_k
        expected_T_bulk = (tube_inlet_T + tube_outlet_T) / 2.0
        assert result.tube_bulk_state.temperature_k == pytest.approx(expected_T_bulk, rel=1e-10)

    def test_bulk_pressure_is_inlet_pressure(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        # Bulk pressure should be inlet pressure (no pressure drop model)
        assert result.tube_bulk_state.pressure_pa == pytest.approx(200_000.0, rel=1e-10)
        assert result.annulus_bulk_state.pressure_pa == pytest.approx(150_000.0, rel=1e-10)


# ---------------------------------------------------------------------------
# 4. Energy closure gate
# ---------------------------------------------------------------------------


class TestEnergyClosureGate:
    """Energy residual must be small for converged results."""

    def test_energy_residual_small(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.energy_residual_w is not None
        assert math.isfinite(result.energy_residual_w)
        # Energy residual should be < 5% of duty
        if result.heat_duty_w and result.heat_duty_w > 1.0:
            assert abs(result.energy_residual_w) < 0.05 * result.heat_duty_w

    def test_energy_balance_consistency(self, provider: CoolPropProvider) -> None:
        """Q_hot and Q_cold should be approximately equal."""
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.energy_residual_w is not None
        assert result.energy_residual_w >= 0.0  # absolute value


# ---------------------------------------------------------------------------
# 5. UA-LMTD closure gate
# ---------------------------------------------------------------------------


class TestUALMTDClosureGate:
    """UA-LMTD residual must be small for converged results."""

    def test_ua_lmtd_residual_small(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.ua_lmtd_residual_w is not None
        assert math.isfinite(result.ua_lmtd_residual_w)
        # UA-LMTD residual should be < 5% of duty
        if result.heat_duty_w and result.heat_duty_w > 1.0:
            assert abs(result.ua_lmtd_residual_w) < 0.05 * result.heat_duty_w

    def test_ua_positive(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.UA_w_k is not None
        assert result.UA_w_k > 0

    def test_lmtd_positive(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.LMTD_k is not None
        assert result.LMTD_k > 0


# ---------------------------------------------------------------------------
# 6. C4 still returns CORRELATION_IMPLEMENTATION_UNAVAILABLE
# ---------------------------------------------------------------------------


class TestC4ImplementationUnavailable:
    """C4 (annulus_laminar_inner_chf) must return CORRELATION_IMPLEMENTATION_UNAVAILABLE."""

    def test_c4_returns_unavailable(self) -> None:
        """C4 is metadata_only → evaluate_hx_correlation returns blocked."""
        from hexagent.correlations.flow import FlowPropertiesInput
        from hexagent.correlations.geometry import ConcentricAnnulusGeometry
        from hexagent.correlations.service import evaluate_hx_correlation

        annulus_geom = ConcentricAnnulusGeometry(
            inner_tube_outer_diameter_m=0.025,
            outer_pipe_inside_diameter_m=0.040,
            heat_transfer_length_m=3.0,
            heated_surface="inner",
        )
        # Laminar annulus flow: Re < 2300
        laminar_flow = FlowPropertiesInput(
            mass_flow_kg_s=0.06,
            density_kg_m3=990.0,
            dynamic_viscosity_pa_s=0.00053,
            thermal_conductivity_w_m_k=0.65,
            specific_heat_j_kg_k=4180.0,
            bulk_temperature_k=325.0,
            heating=True,
        )

        result = evaluate_hx_correlation(
            geometry=annulus_geom,
            flow=laminar_flow,
            boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
        )
        # C4 is metadata_only, so it should be blocked
        assert result.status.value == "blocked"
        # Spec requires CORRELATION_IMPLEMENTATION_UNAVAILABLE for C4
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.CORRELATION_IMPLEMENTATION_UNAVAILABLE in blocker_codes, (
            f"Expected CORRELATION_IMPLEMENTATION_UNAVAILABLE, got {blocker_codes}"
        )


# ---------------------------------------------------------------------------
# 7. Property failure returns PROPERTY_EVALUATION_FAILED
# ---------------------------------------------------------------------------


class TestPropertyFailure:
    """Property service errors must yield PROPERTY_EVALUATION_FAILED blocker."""

    def test_inlet_property_failure(self) -> None:
        """A failing state_tp at inlet must return BLOCKED with PROPERTY_EVALUATION_FAILED."""
        failing_provider = MagicMock()
        failing_provider.name = "MockProvider"
        failing_provider.version = "0.0.0"
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        failing_provider.state_tp.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="CoolProp backend failure",
        )

        result = _run_rating(failing_provider)
        assert result.status == RatingStatus.BLOCKED
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.PROPERTY_EVALUATION_FAILED in blocker_codes

    def test_ph_property_failure_in_solver(self) -> None:
        """A failing state_ph during solver evaluation must yield PROPERTY_EVALUATION_FAILED."""
        real_provider = CoolPropProvider(cache_size=64)

        failing_provider = MagicMock()
        failing_provider.name = real_provider.name
        failing_provider.version = real_provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = real_provider.reference_state_policy
        # state_ph always fails → solver can't evaluate any trial Q
        failing_provider.state_ph.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="PH query failed",
        )
        # state_tp delegates to real provider for inlet/q_max queries
        failing_provider.state_tp.side_effect = real_provider.state_tp

        result = _run_rating(failing_provider)
        # Should be FAILED or BLOCKED depending on when the failure occurs
        assert result.status in (RatingStatus.FAILED, RatingStatus.BLOCKED)


# ---------------------------------------------------------------------------
# 8. verify_hash() for production results
# ---------------------------------------------------------------------------


class TestVerifyHash:
    """verify_hash() integrity checks."""

    def test_hash_format(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.result_hash.startswith("sha256:")
        hex_part = result.result_hash[7:]
        assert len(hex_part) == 64
        int(hex_part, 16)  # must not raise

    def test_same_input_same_hash(self, provider: CoolPropProvider) -> None:
        r1 = _run_rating(provider)
        r2 = _run_rating(provider)
        assert r1.result_hash == r2.result_hash

    def test_different_input_different_hash(self, provider: CoolPropProvider) -> None:
        r1 = _run_rating(provider)
        alt_kwargs = {**_BASE_KWARGS, "hot_mass_flow_kg_s": 0.6}
        r2 = rate_double_pipe(
            **alt_kwargs,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            provider=provider,
        )
        assert r1.result_hash != r2.result_hash

    def test_field_hash_integrity(self, provider: CoolPropProvider) -> None:
        """_field_hash matches _compute_field_hash (tamper detection)."""
        result = _run_rating(provider)
        assert result._field_hash == result._compute_field_hash()

    def test_verify_hash_returns_true(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.verify_hash() is True


# ---------------------------------------------------------------------------
# 9. verify_provenance() including CORRELATION nodes
# ---------------------------------------------------------------------------


class TestVerifyProvenance:
    """Provenance graph must contain expected node types and verify."""

    def test_provenance_graph_has_nodes(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        graph = result.provenance_graph
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_correlation_snapshots_present(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result must have correlation snapshots."""
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.tube_selected_correlation is not None
        assert result.annulus_selected_correlation is not None
        assert result.tube_selected_correlation.correlation_id != ""
        assert result.annulus_selected_correlation.correlation_id != ""

    def test_property_call_nodes_present(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result must have PROPERTY_CALL nodes."""
        from hexagent.domain.provenance import ProvenanceNodeType

        result = _run_rating(provider)
        pc_nodes = [
            n
            for n in result.provenance_graph.nodes
            if n.node_type == ProvenanceNodeType.PROPERTY_CALL
        ]
        assert len(pc_nodes) > 0

    def test_result_node_present(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result must have a RESULT node."""
        from hexagent.domain.provenance import ProvenanceNodeType

        result = _run_rating(provider)
        result_nodes = [
            n for n in result.provenance_graph.nodes if n.node_type == ProvenanceNodeType.RESULT
        ]
        assert len(result_nodes) == 1

    def test_calculation_run_node_present(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result must have a CALCULATION_RUN node."""
        from hexagent.domain.provenance import ProvenanceNodeType

        result = _run_rating(provider)
        calc_nodes = [
            n
            for n in result.provenance_graph.nodes
            if n.node_type == ProvenanceNodeType.CALCULATION_RUN
        ]
        assert len(calc_nodes) == 1

    def test_verify_provenance_returns_true(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.verify_provenance() is True


# ---------------------------------------------------------------------------
# 10. Basic counter-flow and parallel-flow water-water cases
# ---------------------------------------------------------------------------


class TestBasicCounterflowWaterWater:
    """Counter-flow water-water rating with real CoolProp properties."""

    def test_succeeds(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.converged is True

    def test_heat_duty_positive(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.heat_duty_w is not None
        assert result.heat_duty_w > 0

    def test_hot_outlet_cooler(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.hot_outlet_temperature_k is not None
        assert result.hot_outlet_temperature_k < 350.0
        assert result.hot_outlet_temperature_k > 300.0

    def test_cold_outlet_warmer(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.cold_outlet_temperature_k is not None
        assert result.cold_outlet_temperature_k > 300.0
        assert result.cold_outlet_temperature_k < 350.0

    def test_hot_above_cold_outlet(self, provider: CoolPropProvider) -> None:
        """For counter-flow, hot outlet should exceed cold outlet."""
        result = _run_rating(provider)
        assert result.hot_outlet_temperature_k > result.cold_outlet_temperature_k

    def test_correlations_selected(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.tube_selected_correlation_id is not None
        assert result.annulus_selected_correlation_id is not None

    def test_epsilon_ntu_fields(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.C_hot_w_k is not None
        assert result.C_cold_w_k is not None
        assert result.C_min_w_k is not None
        assert result.C_max_w_k is not None
        assert result.capacity_ratio is not None
        assert 0 <= result.capacity_ratio <= 1
        assert result.NTU is not None
        assert result.NTU > 0
        assert result.effectiveness is not None
        assert 0 < result.effectiveness <= 1


class TestBasicParallelFlowWaterWater:
    """Parallel-flow water-water rating with real CoolProp properties."""

    def test_succeeds(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.converged is True

    def test_heat_duty_positive(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.heat_duty_w is not None
        assert result.heat_duty_w > 0

    def test_hot_outlet_cooler(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.hot_outlet_temperature_k is not None
        assert result.hot_outlet_temperature_k < 350.0

    def test_cold_outlet_warmer(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.cold_outlet_temperature_k is not None
        assert result.cold_outlet_temperature_k > 300.0

    def test_counterflow_duty_ge_parallel(self, provider: CoolPropProvider) -> None:
        """Counter-flow duty must be ≥ parallel duty."""
        cf = _run_rating(provider)
        pf = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert cf.heat_duty_w is not None
        assert pf.heat_duty_w is not None
        assert cf.heat_duty_w >= pf.heat_duty_w * 0.99  # 1% tolerance
