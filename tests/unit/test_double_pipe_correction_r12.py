"""Comprehensive tests for TASK-008 engineering correction round 12.

Covers:
1. TestQMaxPinchTracking - verify pinch_lo/pinch_hi tracking in Q_max bisection
2. TestQMaxIterationLimitCalls - verify no extra calls on iteration limit
3. TestQMaxDiagnosticsTamper - Q_max diagnostics tamper detection
4. TestVerifierParallelLimitsNoPinch - parallel limits without pinch is rejected
5. TestVerifierParallelLimitsPartialPinch - partial limits trace is valid
6. TestVerifierEmptyCallsSucceeded - empty calls with SUCCEEDED is rejected
7. TestVerifierEmptyCallsBlockedInput - empty calls with input BLOCKED is allowed
"""

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

import pytest

from hexagent.core.heat_balance import PropertyCallRecord
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.provenance import ProvenanceNodeType
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import (
    _compute_q_max_parallel,
    rate_double_pipe,
)
from hexagent.exchangers.double_pipe.recorder import (
    EvaluationRecorder,
    EvaluationRole,
)
from hexagent.exchangers.double_pipe.result import (
    RatingResult,
    RatingStatus,
)
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import (
    FluidIdentifier,
    PropertyProvider,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# -----------------------------------------------------------------------
# Fixtures & constants
# -----------------------------------------------------------------------


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


def _run_rating(
    provider: PropertyProvider,
    *,
    tube_in_hot: bool = True,
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW,
    **extra,
) -> RatingResult:
    """Run rate_double_pipe with standard conditions."""
    kwargs = dict(
        geometry=STANDARD_GEOMETRY,
        hot_fluid=WATER,
        cold_fluid=WATER,
        hot_mass_flow_kg_s=0.5,
        cold_mass_flow_kg_s=1.5,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=300.0,
        hot_inlet_pressure_pa=200000.0,
        cold_inlet_pressure_pa=150000.0,
        tube_in_hot=tube_in_hot,
        flow_arrangement=flow_arrangement,
        provider=provider,
        minimum_terminal_delta_t=0.5,
        tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
        annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
    )
    kwargs.update(extra)
    return rate_double_pipe(**kwargs)


# =========================================================================
# 1. TestQMaxPinchTracking - verify pinch_lo/pinch_hi tracking
# =========================================================================


class TestQMaxPinchTracking:
    """Verify that the converged bisection Q_max satisfies pinch tracking contracts."""

    def test_qmax_pinch_tracking(self, provider: CoolPropProvider) -> None:
        """Run _compute_q_max_parallel and verify pinch tracking and call counts."""
        recorder = EvaluationRecorder()
        h_hot_in = provider.state_tp(WATER, 350.0, 200000.0).enthalpy_j_kg
        h_cold_in = provider.state_tp(WATER, 300.0, 150000.0).enthalpy_j_kg

        qmax = _compute_q_max_parallel(
            provider=provider,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_inlet_temperature_k=350.0,
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200000.0,
            cold_inlet_pressure_pa=150000.0,
            h_hot_in=h_hot_in,
            h_cold_in=h_cold_in,
            hot_mass_flow_kg_s=0.5,
            cold_mass_flow_kg_s=1.5,
            minimum_terminal_delta_t=0.5,
            recorder=recorder,
        )

        # Must converge (standard conditions should always converge)
        assert qmax.termination_reason == "bisection_converged", (
            f"Expected bisection_converged, got {qmax.termination_reason}"
        )

        # Contract 1: q_max_w == final_q_low_w (solution is at q_lo)
        assert qmax.q_max_w == qmax.final_q_low_w, (
            f"q_max_w ({qmax.q_max_w}) != final_q_low_w ({qmax.final_q_low_w})"
        )

        # Contract 2: bracket width within tolerance
        assert qmax.final_q_width_w is not None
        assert qmax.q_tolerance_w is not None
        assert qmax.final_q_width_w <= qmax.q_tolerance_w, (
            f"final_q_width_w ({qmax.final_q_width_w}) > q_tolerance_w ({qmax.q_tolerance_w})"
        )

        # Contract 3: pinch residual within tolerance
        assert qmax.pinch_temperature_tolerance_k is not None
        assert abs(qmax.final_pinch_residual_k) <= qmax.pinch_temperature_tolerance_k, (
            f"abs(pinch_residual) ({abs(qmax.final_pinch_residual_k)}) > "
            f"pinch_tolerance ({qmax.pinch_temperature_tolerance_k})"
        )

        # Verify property-call count: 2 TP limits + 2 PH q_upper + N*2 PH iterations
        expected_total = 2 + 2 + qmax.iterations * 2
        assert recorder.record_count == expected_total, (
            f"Expected {expected_total} records (2 TP + 2 PH q_upper + "
            f"{qmax.iterations}*2 PH iterations), got {recorder.record_count}"
        )
        assert recorder.record_count == 78, (
            f"Expected exactly 78 records, got {recorder.record_count}"
        )

        # Count PH calls with evaluation_role=q_max_parallel_pinch
        pinch_calls = [
            c
            for c in recorder.records
            if c.evaluation_role == EvaluationRole.Q_MAX_PARALLEL_PINCH.value
        ]
        assert len(pinch_calls) == 76, (
            f"Expected 76 PH pinch calls (2 q_upper + 37*2 iterations), got {len(pinch_calls)}"
        )
        # All pinch calls should be PH queries
        for c in pinch_calls:
            assert c.query_type == "PH", f"Pinch call query_type should be PH, got {c.query_type}"


# =========================================================================
# 2. TestQMaxIterationLimitCalls - verify no extra calls on iteration limit
# =========================================================================


class TestQMaxIterationLimitCalls:
    """Verify deterministic iteration limit behavior when Q_MAX_MAX_ITERATIONS=1."""

    def test_iteration_limit_calls(self, provider: CoolPropProvider) -> None:
        """_compute_q_max_parallel with iterations=1 produces exactly 6 calls."""
        recorder = EvaluationRecorder()
        h_hot_in = provider.state_tp(WATER, 350.0, 200000.0).enthalpy_j_kg
        h_cold_in = provider.state_tp(WATER, 300.0, 150000.0).enthalpy_j_kg

        # Monkeypatch Q_MAX_MAX_ITERATIONS to 1
        import hexagent.exchangers.double_pipe.rating as rating_mod

        original = rating_mod.Q_MAX_MAX_ITERATIONS
        rating_mod.Q_MAX_MAX_ITERATIONS = 1
        try:
            qmax = _compute_q_max_parallel(
                provider=provider,
                hot_fluid=WATER,
                cold_fluid=WATER,
                hot_inlet_temperature_k=350.0,
                cold_inlet_temperature_k=300.0,
                hot_inlet_pressure_pa=200000.0,
                cold_inlet_pressure_pa=150000.0,
                h_hot_in=h_hot_in,
                h_cold_in=h_cold_in,
                hot_mass_flow_kg_s=0.5,
                cold_mass_flow_kg_s=1.5,
                minimum_terminal_delta_t=0.5,
                recorder=recorder,
            )
        finally:
            rating_mod.Q_MAX_MAX_ITERATIONS = original

        assert qmax.termination_reason == "iteration_limit"
        assert qmax.iterations == 1

        # Total calls: 2 TP limits + 2 PH q_upper + 2 PH iteration = 6
        assert recorder.record_count == 6, (
            f"Expected 6 records (2 TP + 2 PH q_upper + 2 PH iteration), "
            f"got {recorder.record_count}"
        )


# =========================================================================
# 3. TestQMaxDiagnosticsTamper - verify Q_max diagnostics tamper detection
# =========================================================================


class TestQMaxDiagnosticsTamper:
    """Verify tamper detection for Q_max diagnostics fields."""

    def test_tamper_q_max_w(self, provider: CoolPropProvider) -> None:
        """Tamper q_max_diagnostics.q_max_w → construction fails (invariant enforced at init)."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.q_max_diagnostics is not None
        assert result.verify_hash() is True
        assert result.verify_provenance() is True

        # Tamper q_max_diagnostics.q_max_w — now caught at construction
        original_qmax_w = result.q_max_diagnostics.q_max_w
        with pytest.raises(ValueError, match="q_max_w == final_q_low_w"):
            dataclasses.replace(result.q_max_diagnostics, q_max_w=original_qmax_w + 1.0)

    def test_tamper_provenance_graph_metadata(self, provider: CoolPropProvider) -> None:
        """Add extra field to q_max_diagnostics in provenance graph → False."""
        result = _run_rating(provider, flow_arrangement=FlowArrangement.PARALLEL)
        assert result.q_max_diagnostics is not None
        assert result.verify_provenance() is True

        graph = result.provenance_graph

        # Find the CALCULATION_RUN node
        calc_node = None
        for n in graph.nodes:
            if n.node_type == ProvenanceNodeType.CALCULATION_RUN:
                calc_node = n
                break
        assert calc_node is not None

        # Find q_max_diagnostics in metadata
        q_max_idx = None
        for i, (key, _val) in enumerate(calc_node.metadata):
            if key == "q_max_diagnostics":
                q_max_idx = i
                break
        assert q_max_idx is not None

        # Add extra field to q_max_diagnostics metadata
        old_q_max_meta = calc_node.metadata[q_max_idx][1]
        new_q_max_meta = old_q_max_meta + (("extra_field", "extra_value"),)
        new_metadata = list(calc_node.metadata)
        new_metadata[q_max_idx] = ("q_max_diagnostics", new_q_max_meta)
        new_metadata = tuple(new_metadata)

        tampered_calc = calc_node.model_copy(update={"metadata": new_metadata})

        # Rebuild nodes list with tampered node
        new_nodes = tuple(
            tampered_calc if n.node_id == calc_node.node_id else n for n in graph.nodes
        )
        tampered_graph = graph.model_copy(update={"nodes": new_nodes})

        tampered = result.model_copy(update={"provenance_graph": tampered_graph})
        assert tampered.verify_provenance() is False


# =========================================================================
# 4. TestVerifierParallelLimitsNoPinch - parallel limits without pinch rejected
# =========================================================================


class TestVerifierParallelLimitsNoPinch:
    """Verify that parallel limits without pinch evaluation is rejected."""

    def _make_synthetic_calls(self, result: RatingResult) -> tuple[PropertyCallRecord, ...]:
        """Build synthetic property_calls with parallel_limits but no pinch."""
        # Use first call from result as template for backend metadata
        base = result.property_calls[0]
        fluid_name = base.fluid
        backend_name = base.backend_name
        backend_version = base.backend_version
        ref_policy = base.reference_state_policy
        backend_rev = base.backend_git_revision
        config_fp = base.configuration_fingerprint
        validation_level = base.validation_level
        cache_policy = base.cache_policy_version

        def _make_call(
            *,
            seq_idx: int,
            eval_idx: int,
            role: str,
            call_idx: int,
            query_type: str,
            stream_role: str,
            stage: str,
            trial_q_w: float | None,
            success: bool = True,
            error_code: str | None = None,
            error_message: str | None = None,
        ) -> PropertyCallRecord:
            return PropertyCallRecord(
                fluid=fluid_name,
                query_type=query_type,
                inputs=(("temperature_k", 350.0), ("pressure_pa", 200000.0)),
                backend_name=backend_name,
                backend_version=backend_version,
                reference_state_policy=ref_policy,
                stage=stage,
                success=success,
                error_code=error_code,
                error_message=error_message,
                stream_role=stream_role,
                sequence_index=seq_idx,
                backend_git_revision=backend_rev,
                configuration_fingerprint=config_fp,
                validation_level=validation_level,
                cache_policy_version=cache_policy,
                evaluation_index=eval_idx,
                evaluation_role=role,
                call_index_within_evaluation=call_idx,
                trial_q_w=trial_q_w,
            )

        calls = []
        seq = 0

        # eval 0: INLET (2 calls)
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_inlet",
                stage="inlet",
                trial_q_w=None,
            )
        )
        seq += 1
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=0,
                role=EvaluationRole.INLET.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_inlet",
                stage="inlet",
                trial_q_w=None,
            )
        )
        seq += 1

        # eval 1: Q_MAX_PARALLEL_LIMITS (2 calls, both succeed)
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=0,
                query_type="TP",
                stream_role="hot_limit",
                stage="q_max",
                trial_q_w=None,
            )
        )
        seq += 1
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=1,
                role=EvaluationRole.Q_MAX_PARALLEL_LIMITS.value,
                call_idx=1,
                query_type="TP",
                stream_role="cold_limit",
                stage="q_max",
                trial_q_w=None,
            )
        )
        seq += 1

        # NO q_max_parallel_pinch evaluation

        # eval 2: BRACKET_PROBE (2 calls)
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=2,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="bracket_probe",
                trial_q_w=50000.0,
            )
        )
        seq += 1
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=2,
                role=EvaluationRole.BRACKET_PROBE.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="bracket_probe",
                trial_q_w=50000.0,
            )
        )
        seq += 1

        # eval 3: SOLVER_ITERATION (2 calls)
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=3,
                role=EvaluationRole.SOLVER_ITERATION.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="brent_evaluation",
                trial_q_w=55000.0,
            )
        )
        seq += 1
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=3,
                role=EvaluationRole.SOLVER_ITERATION.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="brent_evaluation",
                trial_q_w=55000.0,
            )
        )
        seq += 1

        # eval 4: FINAL_EVALUATION (2 calls)
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=4,
                role=EvaluationRole.FINAL_EVALUATION.value,
                call_idx=0,
                query_type="PH",
                stream_role="hot_solver",
                stage="final_state",
                trial_q_w=55000.0,
            )
        )
        seq += 1
        calls.append(
            _make_call(
                seq_idx=seq,
                eval_idx=4,
                role=EvaluationRole.FINAL_EVALUATION.value,
                call_idx=1,
                query_type="PH",
                stream_role="cold_solver",
                stage="final_state",
                trial_q_w=55000.0,
            )
        )

        return tuple(calls)

    def test_parallel_limits_no_pinch_rejected(self, provider: CoolPropProvider) -> None:
        """Parallel limits (both succeed) without pinch → verify_provenance is False."""
        result = _run_rating(provider)
        assert result.verify_provenance() is True

        synthetic_calls = self._make_synthetic_calls(result)
        tampered = result.model_copy(update={"property_calls": synthetic_calls})
        assert tampered.verify_provenance() is False


# =========================================================================
# 5. TestVerifierParallelLimitsPartialPinch - partial limits trace is valid
# =========================================================================


class TestVerifierParallelLimitsPartialPinch:
    """Verify that a partial limits trace (one limit fails) is valid."""

    def _make_partial_limits_provider(self, provider: CoolPropProvider) -> MagicMock:
        """Provider that fails on the 4th TP call (cold limit)."""
        mock = MagicMock()
        mock.name = provider.name
        mock.version = provider.version
        mock.git_revision = ""
        mock.reference_state_policy = provider.reference_state_policy
        real_tp = provider.state_tp
        real_ph = provider.state_ph
        mock.state_tp.side_effect = real_tp
        mock.state_ph.side_effect = real_ph

        tp_call_count = [0]

        def _selective_tp(fluid, T, P):
            tp_call_count[0] += 1
            # 4th TP call is the cold limit call
            if tp_call_count[0] == 4:
                raise PropertyServiceError(
                    code=PropertyErrorCode.BACKEND_FAILURE,
                    message="Cold limit TP failed",
                )
            return real_tp(fluid, T, P)

        mock.state_tp.side_effect = _selective_tp
        return mock

    def test_partial_limits_valid(self, provider: CoolPropProvider) -> None:
        """Partial limits (one fails, no pinch) → verify_provenance is True."""
        mock_provider = self._make_partial_limits_provider(provider)
        result = _run_rating(mock_provider, flow_arrangement=FlowArrangement.PARALLEL)

        # Should be BLOCKED due to property failure
        assert result.status == RatingStatus.BLOCKED
        # Should have exactly 4 property calls: 2 inlet + 2 limits (1 success + 1 failure)
        assert len(result.property_calls) == 4
        # Verify the limits evaluation has one success and one failure
        limits_calls = [
            c
            for c in result.property_calls
            if c.evaluation_role == EvaluationRole.Q_MAX_PARALLEL_LIMITS.value
        ]
        assert len(limits_calls) == 2
        assert limits_calls[0].success is True
        assert limits_calls[1].success is False

        # No pinch evaluation present
        pinch_calls = [
            c
            for c in result.property_calls
            if c.evaluation_role == EvaluationRole.Q_MAX_PARALLEL_PINCH.value
        ]
        assert len(pinch_calls) == 0

        # verify_provenance should pass (graph was built with these exact calls)
        assert result.verify_provenance() is True


# =========================================================================
# 6. TestVerifierEmptyCallsSucceeded - empty calls with SUCCEEDED rejected
# =========================================================================


class TestVerifierEmptyCallsSucceeded:
    """Verify that empty property_calls on a SUCCEEDED result is rejected."""

    def test_empty_calls_succeeded_rejected(self, provider: CoolPropProvider) -> None:
        """SUCCEEDED result with empty property_calls → verify_provenance is False."""
        result = _run_rating(provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.verify_provenance() is True

        # Replace property_calls with empty tuple
        tampered = result.model_copy(update={"property_calls": ()})
        assert tampered.verify_provenance() is False


# =========================================================================
# 7. TestVerifierEmptyCallsBlockedInput - empty calls with BLOCKED allowed
# =========================================================================


class TestVerifierEmptyCallsBlockedInput:
    """Verify that empty property_calls on a BLOCKED input result is allowed."""

    def test_empty_calls_blocked_input_allowed(self) -> None:
        """BLOCKED result from input validation (no property calls) → True."""
        # Trigger BLOCKED on input validation (hot_inlet <= cold_inlet)
        # This blocks before any property evaluations, so property_calls is empty
        result = rate_double_pipe(
            geometry=STANDARD_GEOMETRY,
            hot_fluid=WATER,
            cold_fluid=WATER,
            hot_mass_flow_kg_s=0.5,
            cold_mass_flow_kg_s=1.5,
            hot_inlet_temperature_k=300.0,  # NOT greater than cold inlet
            cold_inlet_temperature_k=300.0,
            hot_inlet_pressure_pa=200000.0,
            cold_inlet_pressure_pa=150000.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            provider=CoolPropProvider(cache_size=64),
            minimum_terminal_delta_t=0.5,
            tube_boundary_condition=ThermalBoundaryCondition.constant_wall_temperature,
            annulus_boundary_condition=ThermalBoundaryCondition.inner_wall_heated,
        )

        assert result.status == RatingStatus.BLOCKED
        assert len(result.property_calls) == 0
        assert result.verify_provenance() is True
