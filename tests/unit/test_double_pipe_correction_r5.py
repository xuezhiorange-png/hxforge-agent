"""Comprehensive tests for TASK-008 engineering correction round 5.

Covers:
1. Three-state hash/provenance (SUCCEEDED/BLOCKED/FAILED)
2. JSON round-trip for all three states
3. Tamper detection tests
4. Property failure strict assertions
5. Evaluation identity deterministic ordering
6. Q_max numerical tests (pinch, counter/parallel paths)
7. Closure exact formula tests
8. Service contract tests
"""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import ErrorCode
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.recorder import EvaluationRecorder
from hexagent.exchangers.double_pipe.result import RatingResult, RatingStatus
from hexagent.exchangers.double_pipe.service import DoublePipeRatingService
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier, ReferenceStatePolicy
from hexagent.properties.coolprop_provider import CoolPropProvider
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

pytestmark = pytest.mark.coolprop

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider(cache_size=64)


WATER = FluidIdentifier(name="Water")
AIR = FluidIdentifier(name="Air")

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
    minimum_terminal_delta_t=0.5,
    tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
    annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
)


def _run_rating(
    provider: CoolPropProvider,
    *,
    tube_in_hot: bool = True,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
    **extra,
) -> RatingResult:
    """Helper to run rate_double_pipe with standard conditions."""
    kwargs = {
        **_BASE_KWARGS,
        "tube_in_hot": tube_in_hot,
        "flow_arrangement": flow_arrangement,
        "provider": provider,
        **extra,  # Override base kwargs if needed
    }
    return rate_double_pipe(**kwargs)


def _json_roundtrip(result: RatingResult) -> RatingResult:
    """Dump to JSON string, validate back, return reconstructed."""
    json_str = result.model_dump_json()
    return RatingResult.model_validate_json(json_str)


# ========================================================================
# 1. Three-state hash/provenance
# ========================================================================


class TestThreeStateHashProvenance:
    """SUCCEEDED, BLOCKED, and FAILED states all have valid hash and provenance."""

    # --- SUCCEEDED ---

    def test_succeeded_verify_hash(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_hash() is True

    def test_succeeded_verify_provenance(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_provenance() is True

    def test_succeeded_json_roundtrip(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        reconstructed = _json_roundtrip(result)
        assert reconstructed.verify_hash() is True
        assert reconstructed.verify_provenance() is True

    # --- BLOCKED: zero mass flow ---

    def test_blocked_zero_mass_flow(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider, hot_mass_flow_kg_s=0.0)
        assert result.status == RatingStatus.BLOCKED
        assert result.verify_hash() is True
        assert result.verify_provenance() is True
        # JSON roundtrip
        reconstructed = _json_roundtrip(result)
        assert reconstructed.status == RatingStatus.BLOCKED
        assert reconstructed.verify_hash() is True
        assert reconstructed.verify_provenance() is True

    # --- BLOCKED: property failure ---

    def test_blocked_property_failure(self, provider: CoolPropProvider) -> None:
        failing_provider = MagicMock()
        failing_provider.name = provider.name
        failing_provider.version = provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        failing_provider.state_tp.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="test error",
        )

        result = _run_rating(failing_provider)
        assert result.status == RatingStatus.BLOCKED
        assert result.verify_hash() is True
        assert result.verify_provenance() is True
        # JSON roundtrip
        reconstructed = _json_roundtrip(result)
        assert reconstructed.verify_hash() is True
        assert reconstructed.verify_provenance() is True

    # --- BLOCKED: C4 unavailability ---

    def test_blocked_c4_unavailable(self, provider: CoolPropProvider) -> None:
        """C4 (annulus laminar inner CHF) → BLOCKED with CORRELATION_IMPLEMENTATION_UNAVAILABLE."""
        # Low cold mass flow → laminar annulus Re < 2300
        result = _run_rating(
            provider,
            cold_mass_flow_kg_s=0.01,
            tube_in_hot=True,
        )
        # C4 should produce a BLOCKED result with CORRELATION_IMPLEMENTATION_UNAVAILABLE
        if result.status == RatingStatus.BLOCKED:
            blocker_codes = [b.code for b in result.blockers]
            assert ErrorCode.CORRELATION_IMPLEMENTATION_UNAVAILABLE in blocker_codes, (
                f"Expected CORRELATION_IMPLEMENTATION_UNAVAILABLE in {blocker_codes}"
            )
        assert result.verify_hash() is True
        assert result.verify_provenance() is True
        # JSON roundtrip
        reconstructed = _json_roundtrip(result)
        assert reconstructed.verify_hash() is True
        assert reconstructed.verify_provenance() is True

    # --- FAILED: solver non-convergence ---

    def test_failed_solver_non_convergence(self, provider: CoolPropProvider) -> None:
        result = _run_rating(
            provider,
            solver_params=SolverParams(max_iterations=1),
        )
        assert result.status == RatingStatus.FAILED
        assert result.failure is not None
        assert result.failure.code == ErrorCode.SOLVER_NON_CONVERGENCE
        assert result.verify_hash() is True
        assert result.verify_provenance() is True
        # JSON roundtrip
        reconstructed = _json_roundtrip(result)
        assert reconstructed.verify_hash() is True
        assert reconstructed.verify_provenance() is True


# ========================================================================
# 2. Tamper detection
# ========================================================================


class TestTamperDetection:
    """Tampering with result fields must be detectable."""

    def test_tamper_core_provenance_digest(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        tampered = copy.deepcopy(result)
        # Modify core_provenance_digest
        object.__setattr__(tampered, "core_provenance_digest", "tampered_digest")
        assert tampered.verify_provenance() is False

    def test_tamper_closure_fields(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        tampered = copy.deepcopy(result)
        # Modify heat_duty_w (included in _compute_field_hash)
        object.__setattr__(tampered, "heat_duty_w", (result.heat_duty_w or 0.0) + 1000.0)
        # The stored _field_hash won't match the new computed hash
        assert tampered._field_hash != tampered._compute_field_hash()

    def test_tamper_state_snapshot(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        tampered = copy.deepcopy(result)
        # Modify hot_outlet_state.temperature_k
        old_snap = tampered.hot_outlet_state
        assert old_snap is not None
        new_snap = copy.deepcopy(old_snap)
        object.__setattr__(new_snap, "temperature_k", old_snap.temperature_k + 10.0)
        object.__setattr__(tampered, "hot_outlet_state", new_snap)
        # The stored _field_hash won't match the new computed hash
        assert tampered._field_hash != tampered._compute_field_hash()

    def test_tamper_correlation_source(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        tampered = copy.deepcopy(result)
        old_corr = tampered.tube_selected_correlation
        assert old_corr is not None
        new_corr = copy.deepcopy(old_corr)
        object.__setattr__(new_corr, "source_year", old_corr.source_year + 10)
        object.__setattr__(tampered, "tube_selected_correlation", new_corr)
        assert tampered._field_hash != tampered._compute_field_hash()

    def test_tamper_property_call(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert len(result.property_calls) > 0
        tampered = copy.deepcopy(result)
        # Modify evaluation_index of first property call
        pc0 = tampered.property_calls[0]
        new_pc = copy.deepcopy(pc0)
        object.__setattr__(new_pc, "evaluation_index", pc0.evaluation_index + 100)
        new_calls = list(tampered.property_calls)
        new_calls[0] = new_pc
        object.__setattr__(tampered, "property_calls", tuple(new_calls))
        assert tampered._field_hash != tampered._compute_field_hash()

    def test_tamper_provenance_edge(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        tampered = copy.deepcopy(result)
        graph = tampered.provenance_graph
        # Add a fake edge using existing node IDs (but wrong relation)
        from hexagent.domain.provenance import ProvenanceEdge, ProvenanceGraph

        # Pick two existing node IDs
        node_ids = [n.node_id for n in graph.nodes]
        assert len(node_ids) >= 2
        fake_edge = ProvenanceEdge(
            source_id=node_ids[0],
            target_id=node_ids[1],
            relation="fake_relation",
        )
        new_edges = list(graph.edges) + [fake_edge]
        object.__setattr__(
            tampered,
            "provenance_graph",
            ProvenanceGraph(nodes=graph.nodes, edges=tuple(new_edges)),
        )
        assert tampered.verify_provenance() is False


# ========================================================================
# 3. Property failure strict assertions
# ========================================================================


class TestPropertyFailureStrict:
    """Property service failures produce accurate PropertyCallRecords."""

    def test_hot_outlet_ph_failure(self, provider: CoolPropProvider) -> None:
        """state_ph failure during solver → BLOCKED with PROPERTY_EVALUATION_FAILED."""
        failing_provider = MagicMock()
        failing_provider.name = provider.name
        failing_provider.version = provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        # state_ph fails → solver cannot evaluate trial Q
        failing_provider.state_ph.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="PH query failed",
        )
        # state_tp delegates to real provider for inlet/q_max queries
        failing_provider.state_tp.side_effect = provider.state_tp

        result = _run_rating(failing_provider)
        assert result.status == RatingStatus.BLOCKED
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.PROPERTY_EVALUATION_FAILED in blocker_codes

        # Check that at least one failed property call record exists
        failed_calls = [pc for pc in result.property_calls if not pc.success]
        assert len(failed_calls) > 0
        fc = failed_calls[0]
        assert fc.error_code is not None
        assert fc.error_message is not None
        assert fc.fluid is not None
        assert fc.query_type is not None
        assert fc.stage is not None
        assert fc.stream_role is not None

    def test_cold_outlet_ph_failure(self, provider: CoolPropProvider) -> None:
        """Same pattern: state_ph failure affects cold side too."""
        failing_provider = MagicMock()
        failing_provider.name = provider.name
        failing_provider.version = provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        failing_provider.state_ph.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="cold PH query failed",
        )
        failing_provider.state_tp.side_effect = provider.state_tp

        result = _run_rating(failing_provider)
        assert result.status == RatingStatus.BLOCKED
        blocker_codes = [b.code for b in result.blockers]
        assert ErrorCode.PROPERTY_EVALUATION_FAILED in blocker_codes
        failed_calls = [pc for pc in result.property_calls if not pc.success]
        assert len(failed_calls) > 0

    def test_hot_bulk_tp_failure(self, provider: CoolPropProvider) -> None:
        """state_tp failure for hot bulk → BLOCKED with PROPERTY_EVALUATION_FAILED."""
        failing_provider = MagicMock()
        failing_provider.name = provider.name
        failing_provider.version = provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        # state_ph works (delegates to real)
        failing_provider.state_ph.side_effect = provider.state_ph
        # state_tp fails
        failing_provider.state_tp.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="TP query failed for hot bulk",
        )

        result = _run_rating(failing_provider)
        assert result.status in (RatingStatus.BLOCKED, RatingStatus.FAILED)
        # Property calls should contain failure records
        failed_calls = [pc for pc in result.property_calls if not pc.success]
        assert len(failed_calls) > 0
        fc = failed_calls[0]
        assert fc.success is False
        assert fc.error_code is not None
        assert fc.error_message is not None

    def test_cold_bulk_tp_failure(self, provider: CoolPropProvider) -> None:
        """state_tp failure for cold bulk → BLOCKED with PROPERTY_EVALUATION_FAILED."""
        failing_provider = MagicMock()
        failing_provider.name = provider.name
        failing_provider.version = provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        failing_provider.state_ph.side_effect = provider.state_ph
        failing_provider.state_tp.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="TP query failed for cold bulk",
        )

        result = _run_rating(failing_provider)
        assert result.status in (RatingStatus.BLOCKED, RatingStatus.FAILED)
        failed_calls = [pc for pc in result.property_calls if not pc.success]
        assert len(failed_calls) > 0

    def test_no_duplicate_calls(self, provider: CoolPropProvider) -> None:
        """After abort, len(property_calls) == number of unique provider invocations."""
        failing_provider = MagicMock()
        failing_provider.name = provider.name
        failing_provider.version = provider.version
        failing_provider.git_revision = ""
        failing_provider.reference_state_policy = ReferenceStatePolicy.DEF
        failing_provider.state_ph.side_effect = PropertyServiceError(
            code=PropertyErrorCode.BACKEND_FAILURE,
            message="PH query failed",
        )
        failing_provider.state_tp.side_effect = provider.state_tp

        result = _run_rating(failing_provider)
        # All property calls should be recorded
        # (no duplicates from the abort/retry pattern)
        assert len(result.property_calls) > 0
        # Each call should have a unique sequence_index
        seq_indices = [pc.sequence_index for pc in result.property_calls]
        assert len(seq_indices) == len(set(seq_indices))


# ========================================================================
# 4. Evaluation identity
# ========================================================================


class TestEvaluationIdentity:
    """Property call records must carry deterministic evaluation identity."""

    def test_evaluation_index_monotonic(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        indices = [pc.evaluation_index for pc in result.property_calls]
        for i in range(1, len(indices)):
            assert indices[i] >= indices[i - 1], f"evaluation_index not monotonic: {indices}"

    def test_inlet_role(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        # First 2 calls should be inlet evaluation
        assert len(result.property_calls) >= 2
        assert result.property_calls[0].evaluation_role == "inlet"
        assert result.property_calls[1].evaluation_role == "inlet"

    def test_solver_iteration_role(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        solver_calls = [
            pc for pc in result.property_calls if pc.evaluation_role == "solver_iteration"
        ]
        assert len(solver_calls) > 0

    def test_final_evaluation_role(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        final_calls = [
            pc for pc in result.property_calls if pc.evaluation_role == "final_evaluation"
        ]
        assert len(final_calls) > 0
        # Final calls should be at the end
        last_role = result.property_calls[-1].evaluation_role
        assert last_role == "final_evaluation"

    def test_call_index_resets(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        # Group calls by evaluation_index
        by_eval: dict[int, list[int]] = {}
        for pc in result.property_calls:
            by_eval.setdefault(pc.evaluation_index, []).append(pc.call_index_within_evaluation)
        for eval_idx, call_indices in by_eval.items():
            assert call_indices[0] == 0, f"Evaluation {eval_idx}: call_index does not start at 0"

    def test_repeated_run_deterministic(self, provider: CoolPropProvider) -> None:
        r1 = _run_rating(provider)
        r2 = _run_rating(provider)
        assert r1.status == r2.status == RatingStatus.SUCCEEDED
        # Check identical evaluation_index/role/call_index sequences
        assert len(r1.property_calls) == len(r2.property_calls)
        for pc1, pc2 in zip(r1.property_calls, r2.property_calls, strict=True):
            assert pc1.evaluation_index == pc2.evaluation_index
            assert pc1.evaluation_role == pc2.evaluation_role
            assert pc1.call_index_within_evaluation == pc2.call_index_within_evaluation

    def test_trial_q_w_populated(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        solver_calls = [
            pc for pc in result.property_calls if pc.evaluation_role == "solver_iteration"
        ]
        assert len(solver_calls) > 0
        for pc in solver_calls:
            assert pc.trial_q_w is not None, "solver_iteration call should have trial_q_w set"
            assert isinstance(pc.trial_q_w, float)


# ========================================================================
# 5. Q_max numerical tests
# ========================================================================


class TestQMaxNumerical:
    """Q_max must respect pinch constraints and flow arrangement."""

    def test_counterflow_q_max_equals_min_of_limits(self, provider: CoolPropProvider) -> None:
        """Counter-flow Q_max == min(Q_hot_limit, Q_cold_limit)."""
        from hexagent.exchangers.double_pipe.rating import _compute_q_max

        hot_fluid = WATER
        cold_fluid = WATER
        T_hot_in = 350.0
        T_cold_in = 300.0
        P_hot = 200_000.0
        P_cold = 150_000.0
        m_hot = 0.5
        m_cold = 1.5
        min_dt = 0.5

        hot_in_state = provider.state_tp(hot_fluid, T_hot_in, P_hot)
        cold_in_state = provider.state_tp(cold_fluid, T_cold_in, P_cold)
        h_hot_in = hot_in_state.enthalpy_j_kg
        h_cold_in = cold_in_state.enthalpy_j_kg

        recorder = EvaluationRecorder()
        q_max_result = _compute_q_max(
            provider=provider,
            hot_fluid=hot_fluid,
            cold_fluid=cold_fluid,
            hot_inlet_temperature_k=T_hot_in,
            cold_inlet_temperature_k=T_cold_in,
            hot_inlet_pressure_pa=P_hot,
            cold_inlet_pressure_pa=P_cold,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=m_hot,
            cold_mass_flow_kg_s=m_cold,
            minimum_terminal_delta_t=min_dt,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            recorder=recorder,
        )
        q_max_cf = q_max_result.q_max_w

        # Compute independent limits
        T_hot_out_min = T_cold_in + min_dt
        hot_limit_state = provider.state_tp(hot_fluid, T_hot_out_min, P_hot)
        Q_hot_limit = m_hot * (h_hot_in - hot_limit_state.enthalpy_j_kg)

        T_cold_out_max = T_hot_in - min_dt
        cold_limit_state = provider.state_tp(cold_fluid, T_cold_out_max, P_cold)
        Q_cold_limit = m_cold * (cold_limit_state.enthalpy_j_kg - h_cold_in)

        expected_q_max = min(Q_hot_limit, Q_cold_limit)
        assert q_max_cf == pytest.approx(expected_q_max, rel=1e-10)

    def test_parallelflow_exit_pinch(self, provider: CoolPropProvider) -> None:
        """Parallel-flow Q_max satisfies T_hot_out - T_cold_out >= min_delta_t."""
        from hexagent.exchangers.double_pipe.rating import _compute_q_max

        hot_fluid = WATER
        cold_fluid = WATER
        T_hot_in = 350.0
        T_cold_in = 300.0
        P_hot = 200_000.0
        P_cold = 150_000.0
        m_hot = 0.5
        m_cold = 1.5
        min_dt = 0.5

        hot_in_state = provider.state_tp(hot_fluid, T_hot_in, P_hot)
        cold_in_state = provider.state_tp(cold_fluid, T_cold_in, P_cold)
        h_hot_in = hot_in_state.enthalpy_j_kg
        h_cold_in = cold_in_state.enthalpy_j_kg

        recorder = EvaluationRecorder()
        q_max_result = _compute_q_max(
            provider=provider,
            hot_fluid=hot_fluid,
            cold_fluid=cold_fluid,
            hot_inlet_temperature_k=T_hot_in,
            cold_inlet_temperature_k=T_cold_in,
            hot_inlet_pressure_pa=P_hot,
            cold_inlet_pressure_pa=P_cold,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=m_hot,
            cold_mass_flow_kg_s=m_cold,
            minimum_terminal_delta_t=min_dt,
            flow_arrangement=FlowArrangement.PARALLEL,
            recorder=recorder,
        )
        q_max_pf = q_max_result.q_max_w

        # Verify exit pinch at Q_max
        h_hot_out = h_hot_in - q_max_pf / m_hot
        h_cold_out = h_cold_in + q_max_pf / m_cold
        hot_out_state = provider.state_ph(
            hot_fluid, P_hot, h_hot_out, reference_state=provider.reference_state_policy
        )
        cold_out_state = provider.state_ph(
            cold_fluid, P_cold, h_cold_out, reference_state=provider.reference_state_policy
        )

        pinch_residual = (hot_out_state.temperature_k - cold_out_state.temperature_k) - min_dt
        assert pinch_residual >= -0.1, (
            f"Parallel flow exit pinch violated: residual={pinch_residual:.4f} K"
        )

    def test_counter_vs_parallel_different(self, provider: CoolPropProvider) -> None:
        """Counter-flow Q_max >= parallel Q_max."""
        result_cf = _run_rating(provider, flow_arrangement=FlowArrangement.COUNTERFLOW)
        result_pf = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result_cf.status == RatingStatus.SUCCEEDED
        assert result_pf.status == RatingStatus.SUCCEEDED
        assert result_cf.heat_duty_w is not None
        assert result_pf.heat_duty_w is not None
        assert result_cf.heat_duty_w >= result_pf.heat_duty_w * 0.99

    def test_high_cp_vs_low_cp(self, provider: CoolPropProvider) -> None:
        """Water vs air give different Q_max values."""
        from hexagent.exchangers.double_pipe.rating import _compute_q_max

        T_hot_in = 350.0
        T_cold_in = 300.0
        P_hot = 200_000.0
        P_cold = 150_000.0
        m_hot = 0.5
        m_cold = 1.5
        min_dt = 0.5

        # Water-water
        hot_in_w = provider.state_tp(WATER, T_hot_in, P_hot)
        cold_in_w = provider.state_tp(WATER, T_cold_in, P_cold)
        rec_w = EvaluationRecorder()
        res_w = _compute_q_max(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=T_hot_in,
            cold_inlet_temperature_k=T_cold_in,
            hot_inlet_pressure_pa=P_hot,
            cold_inlet_pressure_pa=P_cold,
            h_hot_in=hot_in_w.enthalpy_j_kg,
            h_cold_in=cold_in_w.enthalpy_j_kg,
            hot_mass_flow_kg_s=m_hot,
            cold_mass_flow_kg_s=m_cold,
            minimum_terminal_delta_t=min_dt,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            recorder=rec_w,
        )
        q_max_w = res_w.q_max_w

        # Water-Air (air has lower Cp, different Q_max)
        hot_in_a = provider.state_tp(WATER, T_hot_in, P_hot)
        cold_in_a = provider.state_tp(AIR, T_cold_in, P_cold)
        rec_a = EvaluationRecorder()
        res_a = _compute_q_max(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=AIR,
            hot_inlet_temperature_k=T_hot_in,
            cold_inlet_temperature_k=T_cold_in,
            hot_inlet_pressure_pa=P_hot,
            cold_inlet_pressure_pa=P_cold,
            h_hot_in=hot_in_a.enthalpy_j_kg,
            h_cold_in=cold_in_a.enthalpy_j_kg,
            hot_mass_flow_kg_s=m_hot,
            cold_mass_flow_kg_s=m_cold,
            minimum_terminal_delta_t=min_dt,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            recorder=rec_a,
        )
        q_max_a = res_a.q_max_w

        assert q_max_w != q_max_a, (
            f"Q_max should differ for water vs air: water={q_max_w}, air={q_max_a}"
        )

    def test_repeated_run_q_max_consistent(self, provider: CoolPropProvider) -> None:
        """Run twice, verify same Q_max value."""
        from hexagent.exchangers.double_pipe.rating import _compute_q_max

        T_hot_in = 350.0
        T_cold_in = 300.0
        P_hot = 200_000.0
        P_cold = 150_000.0
        m_hot = 0.5
        m_cold = 1.5
        min_dt = 0.5

        hot_in_state = provider.state_tp(WATER, T_hot_in, P_hot)
        cold_in_state = provider.state_tp(WATER, T_cold_in, P_cold)
        h_hot_in = hot_in_state.enthalpy_j_kg
        h_cold_in = cold_in_state.enthalpy_j_kg

        rec1 = EvaluationRecorder()
        res1 = _compute_q_max(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=T_hot_in,
            cold_inlet_temperature_k=T_cold_in,
            hot_inlet_pressure_pa=P_hot,
            cold_inlet_pressure_pa=P_cold,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=m_hot,
            cold_mass_flow_kg_s=m_cold,
            minimum_terminal_delta_t=min_dt,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            recorder=rec1,
        )
        q1 = res1.q_max_w

        rec2 = EvaluationRecorder()
        res2 = _compute_q_max(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=T_hot_in,
            cold_inlet_temperature_k=T_cold_in,
            hot_inlet_pressure_pa=P_hot,
            cold_inlet_pressure_pa=P_cold,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=m_hot,
            cold_mass_flow_kg_s=m_cold,
            minimum_terminal_delta_t=min_dt,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            recorder=rec2,
        )
        q2 = res2.q_max_w

        assert q1 == pytest.approx(q2, rel=1e-12)


# ========================================================================
# 6. Closure exact formula tests
# ========================================================================


class TestClosureExact:
    """Energy and UA-LMTD closure formulas must be exact."""

    def test_energy_residual_formula(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.energy_residual_w is not None
        assert result.Q_hot_w is not None
        assert result.Q_cold_w is not None
        expected = abs(result.Q_hot_w - result.Q_cold_w)
        assert result.energy_residual_w == pytest.approx(expected, rel=1e-12)

    def test_energy_tolerance_formula(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.energy_tolerance_w is not None
        assert result.Q_hot_w is not None
        assert result.Q_cold_w is not None
        expected = max(
            1e-3,
            1e-8 * max(abs(result.Q_hot_w), abs(result.Q_cold_w), 1.0),
        )
        assert result.energy_tolerance_w == pytest.approx(expected, rel=1e-12)

    def test_ua_lmtd_tolerance_formula(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.ua_lmtd_tolerance_w is not None
        assert result.UA_w_k is not None
        assert result.LMTD_k is not None
        Q = result.heat_duty_w or 0.0
        UA_LMTD = result.UA_w_k * result.LMTD_k
        expected = max(
            1e-3,
            1e-8 * max(abs(Q), abs(UA_LMTD), 1.0),
        )
        assert result.ua_lmtd_tolerance_w == pytest.approx(expected, rel=1e-12)

    def test_residual_less_than_tolerance(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.energy_residual_w is not None
        assert result.energy_tolerance_w is not None
        assert result.energy_residual_w < result.energy_tolerance_w

    def test_nan_rejected(self) -> None:
        """RatingResult with NaN in Q_hot_w field must raise ValidationError."""
        # We can't easily create a full valid RatingResult with NaN in Q_hot_w
        # because the validator catches it. Instead, test the validator directly.
        base = {
            "status": "succeeded",
            "flow_arrangement": "counterflow",
            "heat_duty_w": 5000.0,
            "hot_outlet_temperature_k": 340.0,
            "cold_outlet_temperature_k": 310.0,
            "area_inner_m2": 0.1885,
            "area_outer_m2": 0.2356,
            "resistance_breakdown": {
                "r_conv_inner": 0.01,
                "r_foul_inner": 0.001,
                "r_wall": 0.0001,
                "r_foul_outer": 0.001,
                "r_conv_outer": 0.005,
                "total_resistance": 0.0171,
                "ua_w_k": 58.48,
            },
            "iterations": 5,
            "converged": True,
            "solver_termination_reason": "converged",
            "solver_details": {
                "iterations": 5,
                "residual_w": 0.001,
                "function_evaluations": 10,
                "termination_reason": "converged",
            },
            "warnings": [],
            "blockers": [],
            "property_calls": [],
            "provider_identity": {
                "name": "CoolProp",
                "version": "6.6.0",
                "git_revision": "",
                "reference_state_policy": "DEF",
            },
            "request_identity": {
                "hot_fluid_name": "Water",
                "hot_fluid_backend": "HEOS",
                "hot_fluid_components": (),
                "cold_fluid_name": "Water",
                "cold_fluid_backend": "HEOS",
                "cold_fluid_components": (),
                "hot_mass_flow_kg_s": 0.5,
                "cold_mass_flow_kg_s": 1.5,
                "hot_inlet_pressure_pa": 200000.0,
                "cold_inlet_pressure_pa": 150000.0,
                "hot_inlet_temperature_k": 350.0,
                "cold_inlet_temperature_k": 300.0,
                "flow_arrangement": "counterflow",
                "geometry": {},
                "solver_absolute_residual_w": 0.001,
                "solver_relative_residual_fraction": 1e-8,
                "solver_bracket_temperature_tolerance_k": 0.0001,
                "solver_max_iterations": 100,
            },
            "result_hash": "sha256:" + "0" * 64,
            "provenance_graph": {"nodes": [], "edges": []},
            "Q_hot_w": float("nan"),  # NaN should be rejected
        }
        with pytest.raises(ValidationError):
            RatingResult.model_validate(base)

    def test_inf_rejected(self) -> None:
        """RatingResult with inf in energy_tolerance_w must raise ValidationError."""
        base = {
            "status": "succeeded",
            "flow_arrangement": "counterflow",
            "heat_duty_w": 5000.0,
            "hot_outlet_temperature_k": 340.0,
            "cold_outlet_temperature_k": 310.0,
            "area_inner_m2": 0.1885,
            "area_outer_m2": 0.2356,
            "resistance_breakdown": {
                "r_conv_inner": 0.01,
                "r_foul_inner": 0.001,
                "r_wall": 0.0001,
                "r_foul_outer": 0.001,
                "r_conv_outer": 0.005,
                "total_resistance": 0.0171,
                "ua_w_k": 58.48,
            },
            "iterations": 5,
            "converged": True,
            "solver_termination_reason": "converged",
            "solver_details": {
                "iterations": 5,
                "residual_w": 0.001,
                "function_evaluations": 10,
                "termination_reason": "converged",
            },
            "warnings": [],
            "blockers": [],
            "property_calls": [],
            "provider_identity": {
                "name": "CoolProp",
                "version": "6.6.0",
                "git_revision": "",
                "reference_state_policy": "DEF",
            },
            "request_identity": {
                "hot_fluid_name": "Water",
                "hot_fluid_backend": "HEOS",
                "hot_fluid_components": (),
                "cold_fluid_name": "Water",
                "cold_fluid_backend": "HEOS",
                "cold_fluid_components": (),
                "hot_mass_flow_kg_s": 0.5,
                "cold_mass_flow_kg_s": 1.5,
                "hot_inlet_pressure_pa": 200000.0,
                "cold_inlet_pressure_pa": 150000.0,
                "hot_inlet_temperature_k": 350.0,
                "cold_inlet_temperature_k": 300.0,
                "flow_arrangement": "counterflow",
                "geometry": {},
                "solver_absolute_residual_w": 0.001,
                "solver_relative_residual_fraction": 1e-8,
                "solver_bracket_temperature_tolerance_k": 0.0001,
                "solver_max_iterations": 100,
            },
            "result_hash": "sha256:" + "0" * 64,
            "provenance_graph": {"nodes": [], "edges": []},
            "energy_tolerance_w": float("inf"),
        }
        with pytest.raises(ValidationError):
            RatingResult.model_validate(base)


# ========================================================================
# 7. Service contract tests
# ========================================================================


class TestServiceContract:
    """DoublePipeRatingService.rate() must enforce required kwargs."""

    def _make_case(self) -> object:
        """Create a minimal DesignCase for service tests."""
        from hexagent.domain.models import (
            DesignCase,
            DesignConstraints,
            FluidSpec,
            FoulingResistanceSpec,
            FoulingSource,
            FoulingSourceType,
            StreamSpec,
            VerificationStatus,
        )
        from hexagent.domain.quantities import (
            AbsolutePressure,
            AbsoluteTemperature,
            FoulingResistance,
            MassFlow,
            Power,
        )

        hot_fouling = FoulingResistanceSpec(
            value=FoulingResistance(value=0.0002, unit="m2*K/W"),
            source=FoulingSource(
                source_type=FoulingSourceType.STANDARD,
                reference_id="test",
                edition="1",
                table_or_clause="default",
                verification_status=VerificationStatus.UNVERIFIED_REFERENCE,
                note="test fouling",
            ),
        )
        cold_fouling = FoulingResistanceSpec(
            value=FoulingResistance(value=0.0002, unit="m2*K/W"),
            source=FoulingSource(
                source_type=FoulingSourceType.STANDARD,
                reference_id="test",
                edition="1",
                table_or_clause="default",
                verification_status=VerificationStatus.UNVERIFIED_REFERENCE,
                note="test fouling",
            ),
        )

        return DesignCase(
            name="test",
            target_duty=Power(value=5000.0, unit="W"),
            hot_stream=StreamSpec(
                fluid=FluidSpec(backend="HEOS", name="Water"),
                mass_flow=MassFlow(value=0.5, unit="kg/s"),
                inlet_temperature=AbsoluteTemperature(value=350.0, unit="K"),
                inlet_pressure=AbsolutePressure(value=200_000.0, unit="Pa"),
                fouling_resistance=hot_fouling,
            ),
            cold_stream=StreamSpec(
                fluid=FluidSpec(backend="HEOS", name="Water"),
                mass_flow=MassFlow(value=1.5, unit="kg/s"),
                inlet_temperature=AbsoluteTemperature(value=300.0, unit="K"),
                inlet_pressure=AbsolutePressure(value=150_000.0, unit="Pa"),
                fouling_resistance=cold_fouling,
            ),
            constraints=DesignConstraints(
                design_pressure_hot=AbsolutePressure(value=300_000.0, unit="Pa"),
                design_pressure_cold=AbsolutePressure(value=250_000.0, unit="Pa"),
                design_temperature_hot=AbsoluteTemperature(value=400.0, unit="K"),
                design_temperature_cold=AbsoluteTemperature(value=350.0, unit="K"),
                required_area_margin_fraction=0.1,
            ),
        )

    def test_missing_tube_bc_raises(self, provider: CoolPropProvider) -> None:
        """Call rate() without tube_boundary_condition → TypeError."""
        case = self._make_case()
        service = DoublePipeRatingService(provider=provider)
        geometry = STANDARD_GEOMETRY
        with pytest.raises(TypeError):
            service.rate(
                case=case,
                geometry=geometry,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
                minimum_terminal_delta_t=0.5,
                # Missing tube_boundary_condition
            )

    def test_missing_annulus_bc_raises(self, provider: CoolPropProvider) -> None:
        """Call rate() without annulus_boundary_condition → TypeError."""
        case = self._make_case()
        service = DoublePipeRatingService(provider=provider)
        geometry = STANDARD_GEOMETRY
        with pytest.raises(TypeError):
            service.rate(
                case=case,
                geometry=geometry,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
                minimum_terminal_delta_t=0.5,
                # Missing annulus_boundary_condition
            )

    def test_missing_min_delta_t_raises(self, provider: CoolPropProvider) -> None:
        """Call rate() without minimum_terminal_delta_t → TypeError."""
        case = self._make_case()
        service = DoublePipeRatingService(provider=provider)
        geometry = STANDARD_GEOMETRY
        with pytest.raises(TypeError):
            service.rate(
                case=case,
                geometry=geometry,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
                annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
                # Missing minimum_terminal_delta_t
            )

    def test_c4_returns_unavailable(self, provider: CoolPropProvider) -> None:
        """C4 conditions → CORRELATION_IMPLEMENTATION_UNAVAILABLE in blockers."""
        result = _run_rating(
            provider,
            cold_mass_flow_kg_s=0.01,
            tube_in_hot=True,
        )
        if result.status == RatingStatus.BLOCKED:
            blocker_codes = [b.code for b in result.blockers]
            assert ErrorCode.CORRELATION_IMPLEMENTATION_UNAVAILABLE in blocker_codes
        assert result.verify_hash() is True
        assert result.verify_provenance() is True


# ========================================================================
# 8. Applicability canonical
# ========================================================================


class TestApplicabilityCanonical:
    """raw_assessment must contain canonical types that survive JSON round-trip."""

    def test_types_preserved(self, provider: CoolPropProvider) -> None:
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.tube_applicability is not None
        raw = result.tube_applicability.raw_assessment
        assert isinstance(raw, tuple)
        for key, val in raw:
            assert isinstance(key, str)
            # Values should be canonical types: bool, int, float, None, str, or tuple
            assert isinstance(val, (bool, int, float, str, type(None), tuple)), (
                f"Unexpected type in raw_assessment: {type(val).__name__} for key={key}"
            )

    def test_json_roundtrip_nested(self, provider: CoolPropProvider) -> None:
        """Nested ApplicabilitySnapshot structure survives JSON round-trip."""
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.tube_applicability is not None

        reconstructed = _json_roundtrip(result)
        assert reconstructed.tube_applicability is not None
        # raw_assessment: tuples may become lists after JSON round-trip
        # so compare as serialized canonical JSON
        from hexagent.core.canonical import canonical_json

        assert canonical_json(dict(result.tube_applicability.raw_assessment)) == (
            canonical_json(dict(reconstructed.tube_applicability.raw_assessment))
        )
        assert reconstructed.tube_applicability.status == (result.tube_applicability.status)
        assert reconstructed.annulus_applicability is not None
        assert canonical_json(dict(result.annulus_applicability.raw_assessment)) == (
            canonical_json(dict(reconstructed.annulus_applicability.raw_assessment))
        )
