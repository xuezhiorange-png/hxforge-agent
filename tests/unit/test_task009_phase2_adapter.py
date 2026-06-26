"""Comprehensive P0-5 production adapter spy tests — exercise the real
evaluate_all_candidates pipeline with a spy rating_fn that records every call.

Tests cover:
  a) Valid production batch — exact forwarding, every field
  b) Candidate-set digest mismatch → 0 rating calls
  c) Request identity mismatch (fluids/flows/temps) → 0 rating calls
  d) Fluid components mismatch → 0 rating calls
  e) Gate/materialization mismatch → 0 rating calls
  f) Hash false → later rating call count = 0
  g) Hash raise → later rating call count = 0
  h) Provenance false → later rating call count = 0
  i) Provenance raise → later rating call count = 0
  j) Adapter exception → later rating call count = 0, structured failure
  k) Provider consistency applied by batch
  l) All candidate records in canonical order
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

import pytest

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import (
    CalculationContext,
    ExecutionContextSnapshot,
    ProviderIdentitySnapshot,
)
from hexagent.domain.messages import ErrorCode
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
    RatingStatus,
)
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.adapter import evaluate_all_candidates
from hexagent.optimization.catalog import compute_catalog_content_hash
from hexagent.optimization.context import (
    TASK009_CONTEXT_NAMESPACE,
    ExpectedProviderIdentity,
    OptimizationObjective,
    SizingRequestIdentity,
    build_sizing_request_identity,
    create_passed_sizing_gate,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationState,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    execution_context_snapshot_payload,
    rating_request_identity_payload,
    verified_rating_evidence_payload,
)
from hexagent.optimization.identities import (
    MaterializationResult,
    build_candidate,
    catalog_snapshot_ref,
    materialize_all_candidates,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthSource,
    OptionRawCountRecord,
    SizingRequest,
)
from hexagent.properties.base import FluidIdentifier, PropertyProvider

# ============================================================================
# Helpers
# ============================================================================


def _make_opt(
    option_id: str = "opt1",
    quantum: str = "0.1",
    lengths: tuple[float, ...] = (1.0, 2.0, 3.0),
) -> CompleteDoublePipeAssemblyOption:
    return CompleteDoublePipeAssemblyOption(
        assembly_option_id=option_id,
        inner_tube_inner_diameter_m=0.05,
        inner_tube_outer_diameter_m=0.06,
        outer_pipe_inner_diameter_m=0.10,
        wall_thermal_conductivity_w_m_k=50.0,
        inner_surface_roughness_m=1e-5,
        annulus_surface_roughness_m=1e-5,
        inner_fouling_resistance_m2k_w=0.0001,
        outer_fouling_resistance_m2k_w=0.0002,
        manufacturing_option_identity="std",
        manufacturing_metadata=(),
        length_source=LengthSource(
            length_quantum_m=quantum,
            allowed_effective_lengths_m=lengths,
        ),
    )


def _hash_cat(
    catalog_id: str = "c1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> str:
    return compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
    )


def _make_cat(
    catalog_id: str = "c1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    h = _hash_cat(catalog_id=catalog_id, options=options)
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
        catalog_content_hash=h,
    )


def _default_expected_provider() -> ExpectedProviderIdentity:
    return ExpectedProviderIdentity(
        name="test_provider",
        version="1.0",
        git_revision="abc123",
        reference_state_policy="default",
    )


def _make_minimal_result(
    hash_passes: bool = True,
    prov_passes: bool = True,
    status: RatingStatus = RatingStatus.SUCCEEDED,
    with_request_identity: bool = True,
) -> Any:
    """Create a duck-typed RatingResult using object.__new__."""
    result = object.__new__(RatingResult)
    object.__setattr__(result, "status", status)
    object.__setattr__(result, "flow_arrangement", FlowArrangement.COUNTERFLOW)
    object.__setattr__(result, "result_hash", "sha256:" + "e" * 64)
    object.__setattr__(result, "provenance_digest", "prov_digest")
    object.__setattr__(result, "heat_duty_w", 1000.0)
    object.__setattr__(result, "hot_outlet_temperature_k", 350.0)
    object.__setattr__(result, "cold_outlet_temperature_k", 310.0)
    object.__setattr__(result, "area_inner_m2", 1.5)
    object.__setattr__(result, "area_outer_m2", 2.0)
    object.__setattr__(result, "UA_w_k", 500.0)
    object.__setattr__(result, "LMTD_k", 40.0)
    object.__setattr__(result, "energy_residual_w", 0.001)
    object.__setattr__(result, "ua_lmtd_residual_w", 0.002)
    object.__setattr__(result, "tube_selected_correlation_id", "corr_1")
    object.__setattr__(result, "tube_selected_correlation_version", "1.0")
    object.__setattr__(result, "annulus_selected_correlation_id", "corr_2")
    object.__setattr__(result, "annulus_selected_correlation_version", "1.0")
    object.__setattr__(result, "warnings", ())
    object.__setattr__(result, "blockers", ())
    object.__setattr__(result, "failure", None)
    object.__setattr__(result, "hot_inlet_state", None)
    object.__setattr__(result, "cold_inlet_state", None)
    object.__setattr__(result, "tube_selected_correlation", None)
    object.__setattr__(result, "annulus_selected_correlation", None)

    if with_request_identity:
        rri = RatingRequestIdentity(
            hot_fluid_name="w",
            hot_fluid_backend="i",
            hot_fluid_components=(),
            cold_fluid_name="b",
            cold_fluid_backend="n",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            flow_arrangement="counterflow",
            geometry={
                "inner_tube_inner_diameter_m": 0.05,
                "inner_tube_outer_diameter_m": 0.06,
                "outer_pipe_inner_diameter_m": 0.10,
                "effective_length_m": 1.0,
                "wall_thermal_conductivity_w_m_k": 50.0,
                "inner_surface_roughness_m": 1e-5,
                "annulus_surface_roughness_m": 1e-5,
                "inner_fouling_resistance_m2k_w": 0.0001,
                "outer_fouling_resistance_m2k_w": 0.0002,
            },
            solver_absolute_residual_w=1e-3,
            solver_relative_residual_fraction=1e-8,
            solver_bracket_temperature_tolerance_k=1e-4,
            solver_max_iterations=100,
        )
        object.__setattr__(result, "request_identity", rri)

        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)

        ec = object.__new__(ExecutionContextSnapshot)
        object.__setattr__(ec, "request_id", None)
        object.__setattr__(ec, "design_case_revision_id", None)
        object.__setattr__(ec, "calculation_run_id", None)
        # Extra fields expected by execution_context_snapshot_payload in evaluation.py
        object.__setattr__(ec, "execution_id", None)
        object.__setattr__(ec, "rating_software_version", None)
        object.__setattr__(ec, "execution_context_policy_version", None)
        object.__setattr__(result, "execution_context", ec)
    else:
        object.__setattr__(result, "request_identity", None)
        object.__setattr__(result, "provider_identity", None)
        object.__setattr__(result, "execution_context", None)

    def _verify_hash() -> bool:
        return hash_passes

    def _verify_provenance() -> bool:
        return prov_passes

    object.__setattr__(result, "verify_hash", _verify_hash)
    object.__setattr__(result, "verify_provenance", _verify_provenance)

    return result


def make_spy(
    hash_passes: bool = True,
    prov_passes: bool = True,
    status: RatingStatus = RatingStatus.SUCCEEDED,
) -> tuple[list[dict[str, Any]], Any]:
    """Create a spy rating_fn and a calls list."""
    calls: list[dict[str, Any]] = []

    def spy_fn(**kwargs: Any) -> Any:
        calls.append(dict(kwargs))
        return _make_minimal_result(
            hash_passes=hash_passes,
            prov_passes=prov_passes,
            status=status,
        )

    return calls, spy_fn


# Valid ThermalBoundaryCondition values (NOT "adiabatic" which is invalid)
BUILDER_TUBE_BC = "constant_wall_temperature"
BUILDER_ANNULUS_BC = "inner_wall_heated"


def _build_and_materialize(
    *options: CompleteDoublePipeAssemblyOption,
) -> tuple[
    SizingRequestIdentity,
    CompleteDoublePipeCatalogSnapshot,
    MaterializationResult,
]:
    """Build a sizing identity, gate, and materialize using the REAL production chain.

    Returns (identity, catalog, materialization_result) where
    materialization_result is a validated MaterializationResult.
    """
    cat = _make_cat(options=options)
    req = SizingRequest(catalogs=(cat,))

    ident = build_sizing_request_identity(
        request=req,
        hot_fluid_name="w",
        cold_fluid_name="b",
        hot_fluid_equation_of_state="i",
        cold_fluid_equation_of_state="n",
        hot_fluid_normalized_components=(),
        cold_fluid_normalized_components=(),
        hot_inlet_temperature_k=300.0,
        cold_inlet_temperature_k=280.0,
        hot_inlet_pressure_pa=1e5,
        cold_inlet_pressure_pa=2e5,
        hot_mass_flow_kg_s=5.0,
        cold_mass_flow_kg_s=5.0,
        tube_in_hot=True,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        tube_boundary_condition=BUILDER_TUBE_BC,
        annulus_boundary_condition=BUILDER_ANNULUS_BC,
        minimum_terminal_delta_t=5.0,
        required_duty_w=1000.0,
        duty_absolute_tolerance_w=10.0,
        duty_relative_tolerance=0.01,
        optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        top_n=5,
        solver_params=SolverParams(),
        expected_provider_identity=_default_expected_provider(),
        design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
        calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
    )

    recs: list[OptionRawCountRecord] = []
    for opt in options:
        rec = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=len(opt.length_source.allowed_effective_lengths_m),
        )
        recs.append(rec)

    total_raw = sum(r.raw_count for r in recs)
    gate = create_passed_sizing_gate(
        sizing_request_identity_digest=ident.sizing_request_identity_digest,
        raw_combination_count=total_raw,
        effective_cap=100,
        per_option_records=tuple(recs),
    )

    # USE THE REAL PRODUCTION CHAIN
    mat_result = materialize_all_candidates(
        catalogs=(cat,),
        sizing_gate=gate,
    )

    return ident, cat, mat_result


# ============================================================================
# Tests
# ============================================================================


class TestAdapterSpy:
    """P0-5: Production adapter spy tests — real evaluate_all_candidates."""

    @pytest.fixture
    def provider(self) -> PropertyProvider:
        """Minimal mock PropertyProvider."""
        import unittest.mock

        return unittest.mock.MagicMock(spec=PropertyProvider)

    @pytest.fixture
    def solver_params(self) -> SolverParams:
        return SolverParams(
            absolute_residual_w=1e-3,
            relative_residual_fraction=1e-8,
            bracket_temperature_tolerance_k=1e-4,
            max_iterations=100,
        )

    def _eval(self, mat_result, ident, solver_params, provider, rating_fn, **overrides):
        """Call evaluate_all_candidates with valid defaults for boundary conditions."""
        params = dict(
            materialization_result=mat_result,
            hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
            cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            provider=provider,
            solver_params=solver_params,
            minimum_terminal_delta_t=5.0,
            tube_boundary_condition=BUILDER_TUBE_BC,
            annulus_boundary_condition=BUILDER_ANNULUS_BC,
            sizing_request_identity=ident,
            rating_fn=rating_fn,
        )
        params.update(overrides)
        return evaluate_all_candidates(**params)

    # ------------------------------------------------------------------
    # a) Valid production batch — exact forwarding
    # ------------------------------------------------------------------

    def test_valid_batch_exact_forwarding(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Spy records every call; results are VERIFIED."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        calls, spy_fn = make_spy()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=spy_fn,
        )

        expected_count = len(candidates)
        assert len(records) == expected_count
        assert len(calls) == expected_count

        for i, rec in enumerate(records):
            assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
            assert rec.evaluation_order_index == i
            assert rec.source_qualified_candidate_id == candidates[i].source_qualified_candidate_id

        # Verify spy call parameters match what was passed — P0-8 complete assertions
        all_lengths = {1.0, 2.0}
        request_ids = []
        for call in calls:
            # --- Geometry ---
            geom = call["geometry"]
            assert geom.inner_tube_inner_diameter_m == 0.05
            assert geom.inner_tube_outer_diameter_m == 0.06
            assert geom.outer_pipe_inner_diameter_m == 0.10
            assert geom.effective_length_m in all_lengths
            assert geom.wall_thermal_conductivity_w_m_k == 50.0
            assert geom.inner_surface_roughness_m == 1e-5
            assert geom.annulus_surface_roughness_m == 1e-5
            assert geom.inner_fouling_resistance_m2k_w == 0.0001
            assert geom.outer_fouling_resistance_m2k_w == 0.0002

            # --- Fluids ---
            assert call["hot_fluid"].name == "w"
            assert call["hot_fluid"].equation_of_state_backend == "i"
            assert call["hot_fluid"].components == ()
            assert call["cold_fluid"].name == "b"
            assert call["cold_fluid"].equation_of_state_backend == "n"
            assert call["cold_fluid"].components == ()

            # --- Rating inputs ---
            assert call["hot_mass_flow_kg_s"] == 5.0
            assert call["cold_mass_flow_kg_s"] == 5.0
            assert call["hot_inlet_temperature_k"] == 300.0
            assert call["cold_inlet_temperature_k"] == 280.0
            assert call["hot_inlet_pressure_pa"] == 1e5
            assert call["cold_inlet_pressure_pa"] == 2e5
            assert call["tube_in_hot"] is True
            assert isinstance(call["flow_arrangement"], FlowArrangement)
            assert call["flow_arrangement"] is FlowArrangement.COUNTERFLOW

            # --- Provider and Solver (same instance) ---
            assert call["provider"] is provider
            assert call["solver_params"] is solver_params

            # --- Context UUID & solver params (P0-8 exact assertions) ---
            assert isinstance(call["context"], CalculationContext)
            request_ids.append(call["context"].request_id)
            assert call["context"].design_case_revision_id == ident.design_case_revision_id
            assert call["context"].calculation_run_id == ident.calculation_run_id

            # --- Minimum terminal delta T, boundary conditions ---
            assert call["minimum_terminal_delta_t"] == 5.0
            assert call["tube_boundary_condition"] == BUILDER_TUBE_BC
            assert call["annulus_boundary_condition"] == BUILDER_ANNULUS_BC

        # Each call has a unique context request_id (P0-8 UUID check)
        assert len(set(request_ids)) == len(request_ids)

        # P0-8: Per-candidate UUID5 exact assertions and solver field assertions
        for i, (candidate, call) in enumerate(zip(candidates, calls, strict=False)):
            expected_request_id = uuid5(
                TASK009_CONTEXT_NAMESPACE,
                f"{ident.sizing_request_identity_digest}:{candidate.source_qualified_candidate_id}",
            )
            assert call["context"].request_id == expected_request_id, (
                f"Candidate {i}: UUID5 mismatch"
            )
            assert call["context"].design_case_revision_id == ident.design_case_revision_id
            assert call["context"].calculation_run_id == ident.calculation_run_id

            # Solver field exact assertions
            assert (
                call["solver_params"].absolute_residual_w == ident.rating_solver_absolute_residual_w
            )
            assert (
                call["solver_params"].relative_residual_fraction
                == ident.rating_solver_relative_residual_fraction
            )
            assert (
                call["solver_params"].bracket_temperature_tolerance_k
                == ident.rating_solver_bracket_temperature_tolerance_k
            )
            assert call["solver_params"].max_iterations == ident.rating_solver_max_iterations

    # ------------------------------------------------------------------
    # b) Candidate-set digest mismatch
    # ------------------------------------------------------------------

    def test_candidate_set_digest_mismatch(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Tampering with candidate_set digest raises ValueError before spy."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
        )
        bad_set = mat_result.candidate_set.model_copy(
            update={"candidate_set_digest": "sha256:" + "f" * 64}
        )
        bad_mat_result = object.__new__(type(mat_result))
        object.__setattr__(bad_mat_result, "candidates", mat_result.candidates)
        object.__setattr__(bad_mat_result, "candidate_set", bad_set)
        calls, spy_fn = make_spy()

        with pytest.raises(ValueError, match="digest verification failed"):
            self._eval(
                mat_result=bad_mat_result,
                ident=ident,
                solver_params=solver_params,
                provider=provider,
                rating_fn=spy_fn,
            )

        assert len(calls) == 0

    # ------------------------------------------------------------------
    # c) Request identity mismatch (fluids/flows/temps)
    # ------------------------------------------------------------------

    def test_identity_mismatch_fluids(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Wrong fluid name raises ValueError before spy."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
        )
        wrong_hot = FluidIdentifier(name="steam", equation_of_state_backend="i")
        calls, spy_fn = make_spy()

        with pytest.raises(ValueError, match="Input parameter mismatch"):
            self._eval(
                mat_result=mat_result,
                ident=ident,
                solver_params=solver_params,
                provider=provider,
                rating_fn=spy_fn,
                hot_fluid=wrong_hot,
            )

        assert len(calls) == 0

    def test_identity_mismatch_flow_temp(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Wrong flow rate raises ValueError before spy."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
        )
        calls, spy_fn = make_spy()

        with pytest.raises(ValueError, match="Input parameter mismatch"):
            self._eval(
                mat_result=mat_result,
                ident=ident,
                solver_params=solver_params,
                provider=provider,
                rating_fn=spy_fn,
                hot_mass_flow_kg_s=999.0,
            )

        assert len(calls) == 0

    # ------------------------------------------------------------------
    # d) Fluid components mismatch
    # ------------------------------------------------------------------

    def test_fluid_components_mismatch(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Components in FluidIdentifier don't match identity's normalized components."""
        # Build a sizing identity that expects empty components
        opt = _make_opt("a", lengths=(1.0,))
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="water",
            cold_fluid_name="brine",
            hot_fluid_equation_of_state="HEOS",
            cold_fluid_equation_of_state="HEOS",
            hot_fluid_normalized_components=(),  # identity expects empty
            cold_fluid_normalized_components=(),  # identity expects empty
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition=BUILDER_TUBE_BC,
            annulus_boundary_condition=BUILDER_ANNULUS_BC,
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=solver_params,
            expected_provider_identity=_default_expected_provider(),
        )

        # Build candidates and set for this identity
        rec = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )
        all_cands = [build_candidate(cat, opt, "1.0")]
        from hexagent.optimization.identities import deduplicate_and_order_candidates

        deduped = deduplicate_and_order_candidates(tuple(all_cands))
        cat_refs = (catalog_snapshot_ref(cat),)

        # Use _create_materialized_candidate_set for correct digest
        from hexagent.optimization.context import _create_materialized_candidate_set

        mcs = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=cat_refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=deduped,
        )

        # Wrap into MaterializationResult
        mat_result = object.__new__(MaterializationResult)
        object.__setattr__(mat_result, "candidates", deduped)
        object.__setattr__(mat_result, "candidate_set", mcs)

        # Use a fluid WITH components, but identity says empty
        wrong_hot = FluidIdentifier(
            name="water",
            equation_of_state_backend="HEOS",
            components=(("water", 1.0),),
        )
        cold = FluidIdentifier(name="brine", equation_of_state_backend="HEOS")
        calls, spy_fn = make_spy()

        with pytest.raises((ValueError,), match="normalized_components|Input parameter mismatch"):
            self._eval(
                mat_result=mat_result,
                ident=ident,
                solver_params=solver_params,
                provider=provider,
                rating_fn=spy_fn,
                hot_fluid=wrong_hot,
                cold_fluid=cold,
            )

        assert len(calls) == 0

    # ------------------------------------------------------------------
    # e) Gate/materialization mismatch
    # ------------------------------------------------------------------

    def test_gate_identity_digest_mismatch(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """candidate_set.sizing_request_identity_digest mismatch raises ValueError."""
        # Build one setup normally
        ident1, cat1, mat_result1 = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
        )

        # Build a different identity
        opt2 = _make_opt("b", lengths=(2.0,))
        cat2 = _make_cat(options=(opt2,))
        req2 = SizingRequest(catalogs=(cat2,))
        ident2 = build_sizing_request_identity(
            request=req2,
            hot_fluid_name="steam",  # different from mcs1 identity
            cold_fluid_name="oil",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition=BUILDER_TUBE_BC,
            annulus_boundary_condition=BUILDER_ANNULUS_BC,
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=solver_params,
            expected_provider_identity=_default_expected_provider(),
        )

        calls, spy_fn = make_spy()

        with pytest.raises(ValueError, match="sizing_request_identity_digest mismatch"):
            self._eval(
                mat_result=mat_result1,
                ident=ident2,
                solver_params=solver_params,
                provider=provider,
                rating_fn=spy_fn,
                hot_fluid=FluidIdentifier(name="steam", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="oil", equation_of_state_backend="n"),
            )

        assert len(calls) == 0

    # ------------------------------------------------------------------
    # f) Hash false → later rating call count = 0
    # ------------------------------------------------------------------

    def test_hash_false_stops_pipeline(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """When verify_hash returns False, remaining candidates are UNEVALUATED."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) >= 2

        calls, spy_fn = make_spy(hash_passes=False)

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=spy_fn,
        )

        assert len(records) == 2
        # First candidate: hash failed → INTEGRITY_INVALID
        assert (
            records[0].candidate_evaluation_state
            == CandidateEvaluationState.INTEGRITY_INVALID.value
        )
        assert len(calls) == 1
        # Second candidate: UNEVALUATED
        assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value

    # ------------------------------------------------------------------
    # g) Hash raise → later rating call count = 0
    # ------------------------------------------------------------------

    def test_hash_raise_stops_pipeline(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """When verify_hash raises, remaining candidates are UNEVALUATED."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) >= 2

        custom_calls: list[dict[str, Any]] = []
        call_count = [0]

        def custom_spy(**kwargs: Any) -> Any:
            custom_calls.append(dict(kwargs))
            call_count[0] += 1
            if call_count[0] == 1:
                obj = _make_minimal_result(hash_passes=True)

                def _rh() -> bool:
                    raise RuntimeError("hash crash")

                object.__setattr__(obj, "verify_hash", _rh)
                return obj
            return _make_minimal_result()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=custom_spy,
        )

        assert len(records) == 2
        assert len(custom_calls) == 1
        assert (
            records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        )
        assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value

    # ------------------------------------------------------------------
    # h) Provenance false → later rating call count = 0
    # ------------------------------------------------------------------

    def test_provenance_false_stops_pipeline(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """When verify_provenance returns False, remaining are UNEVALUATED."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) >= 2

        custom_calls: list[dict[str, Any]] = []
        call_count = [0]

        def custom_spy(**kwargs: Any) -> Any:
            custom_calls.append(dict(kwargs))
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_minimal_result(hash_passes=True, prov_passes=False)
            return _make_minimal_result()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=custom_spy,
        )

        assert len(records) == 2
        assert len(custom_calls) == 1
        assert (
            records[0].candidate_evaluation_state
            == CandidateEvaluationState.INTEGRITY_INVALID.value
        )
        assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value

    # ------------------------------------------------------------------
    # i) Provenance raise → later rating call count = 0
    # ------------------------------------------------------------------

    def test_provenance_raise_stops_pipeline(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """When verify_provenance raises, remaining are UNEVALUATED."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) >= 2

        custom_calls: list[dict[str, Any]] = []
        call_count = [0]

        def custom_spy(**kwargs: Any) -> Any:
            custom_calls.append(dict(kwargs))
            call_count[0] += 1
            if call_count[0] == 1:
                obj = _make_minimal_result(hash_passes=True, prov_passes=True)

                def _rp() -> bool:
                    raise RuntimeError("prov crash")

                object.__setattr__(obj, "verify_provenance", _rp)
                return obj
            return _make_minimal_result()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=custom_spy,
        )

        assert len(records) == 2
        assert len(custom_calls) == 1
        assert (
            records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        )
        assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value

    # ------------------------------------------------------------------
    # j) Adapter exception → later rating call count = 0
    # ------------------------------------------------------------------

    def test_adapter_exception_stops_pipeline(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """When the spy raises, that candidate is RUNTIME_FAILED, rest UNEVALUATED."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) >= 2

        custom_calls: list[dict[str, Any]] = []
        call_idx = [0]

        def raising_spy(**kwargs: Any) -> Any:
            custom_calls.append(dict(kwargs))
            call_idx[0] += 1
            if call_idx[0] == 1:
                raise RuntimeError("adapter explosion")
            return _make_minimal_result()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=raising_spy,
        )

        assert len(records) == 2
        assert (
            records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        )
        assert records[0].evaluation_failure is not None
        assert records[0].evaluation_failure.code == ErrorCode.TASK008_ADAPTER
        assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value
        assert len(custom_calls) == 1

    # ------------------------------------------------------------------
    # k) Provider consistency applied by batch
    # ------------------------------------------------------------------

    def test_provider_consistency_applied(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Different provider identities across candidates is detected."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
            _make_opt("c", lengths=(3.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) >= 3

        pi_a = ProviderIdentitySnapshot(
            name="provider_a",
            version="1.0",
            git_revision="aaa",
            reference_state_policy="default",
        )
        pi_b = ProviderIdentitySnapshot(
            name="provider_b",
            version="2.0",
            git_revision="bbb",
            reference_state_policy="alt",
        )

        call_idx = [0]

        def provider_spy(**kwargs: Any) -> Any:
            call_idx[0] += 1
            result = _make_minimal_result()
            if call_idx[0] == 2:
                object.__setattr__(result, "provider_identity", pi_b)
            else:
                object.__setattr__(result, "provider_identity", pi_a)
            return result

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=provider_spy,
        )

        assert len(records) == 3
        for rec in records:
            assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value

        # Provider consistency: second candidate has different provider
        # All should be marked as mismatched
        assert not records[0].provider_identity_matches
        assert not records[1].provider_identity_matches
        assert not records[2].provider_identity_matches

    # ------------------------------------------------------------------
    # l) All candidate records in canonical order
    # ------------------------------------------------------------------

    def test_canonical_order(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Records are returned in the same order as the candidates."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        candidates = mat_result.candidates
        calls, spy_fn = make_spy()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=spy_fn,
        )

        for i, candidate in enumerate(candidates):
            assert (
                records[i].source_qualified_candidate_id == candidate.source_qualified_candidate_id
            )
            assert records[i].evaluation_order_index == i

        ids = [r.source_qualified_candidate_id for r in records]
        assert ids == sorted(ids)

    # ------------------------------------------------------------------
    # Three candidates all verified
    # ------------------------------------------------------------------

    def test_three_candidates_all_verified(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Three candidates all pass verification."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
            _make_opt("c", lengths=(3.0,)),
        )
        candidates = mat_result.candidates
        assert len(candidates) == 3

        calls, spy_fn = make_spy()

        records = self._eval(
            mat_result=mat_result,
            ident=ident,
            solver_params=solver_params,
            provider=provider,
            rating_fn=spy_fn,
        )

        assert len(records) == 3
        assert len(calls) == 3
        for rec in records:
            assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value

    # ------------------------------------------------------------------
    # Candidate ordering mismatch with set
    # ------------------------------------------------------------------

    def test_candidate_ordering_mismatch_raises(
        self,
        solver_params: SolverParams,
        provider: PropertyProvider,
    ) -> None:
        """Passing candidates in wrong order relative to set raises ValueError."""
        ident, cat, mat_result = _build_and_materialize(
            _make_opt("a", lengths=(1.0,)),
            _make_opt("b", lengths=(2.0,)),
        )
        calls, spy_fn = make_spy()

        # Build a MaterializationResult where candidates are in reversed order
        # relative to candidate_set.ordered_candidate_ids.
        # We keep the original (sorted) candidate_set but pass candidates
        # in reverse order, then bypass __post_init__ to avoid its validation.
        reversed_candidates = tuple(reversed(mat_result.candidates))
        bad_mat_result = object.__new__(type(mat_result))
        object.__setattr__(bad_mat_result, "candidates", reversed_candidates)
        object.__setattr__(bad_mat_result, "candidate_set", mat_result.candidate_set)

        with pytest.raises(ValueError, match="Candidate ordering mismatch"):
            self._eval(
                mat_result=bad_mat_result,
                ident=ident,
                solver_params=solver_params,
                provider=provider,
                rating_fn=spy_fn,
            )

        assert len(calls) == 0


# ============================================================================
# P0-9: 26-field evidence digest mutation suite
# ============================================================================


EXPECTED_26_FIELD_KEYS = (
    "rating_status",
    "heat_duty_w",
    "hot_outlet_temperature_k",
    "cold_outlet_temperature_k",
    "area_inner_m2",
    "area_outer_m2",
    "UA_w_k",
    "LMTD_k",
    "energy_residual_w",
    "ua_lmtd_residual_w",
    "tube_inlet_density_kg_m3",
    "annulus_inlet_density_kg_m3",
    "tube_flow_area_m2",
    "annulus_flow_area_m2",
    "warning_digests",
    "blocker_digests",
    "failure_digest",
    "provider_identity_digest",
    "tube_correlation_digest",
    "annulus_correlation_digest",
    "rating_result_hash",
    "rating_provenance_digest",
    "hash_verification_outcome",
    "provenance_verification_outcome",
    "rating_request_identity_digest",
    "rating_execution_context_digest",
)


class TestEvidencePayloadMutation:
    """P0-9: 26-field evidence digest mutation test suite."""

    def _baseline_evidence(self) -> VerifiedRatingEvidenceSnapshot:
        from hexagent.exchangers.double_pipe.result import (
            RatingRequestIdentity,
            RatingStatus,
        )

        rri = RatingRequestIdentity(
            hot_fluid_name="w",
            hot_fluid_backend="i",
            hot_fluid_components=(),
            cold_fluid_name="b",
            cold_fluid_backend="n",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            flow_arrangement="counterflow",
            geometry={
                "inner_tube_inner_diameter_m": 0.05,
                "inner_tube_outer_diameter_m": 0.06,
                "outer_pipe_inner_diameter_m": 0.10,
                "effective_length_m": 1.0,
                "wall_thermal_conductivity_w_m_k": 50.0,
                "inner_surface_roughness_m": 1e-5,
                "annulus_surface_roughness_m": 1e-5,
                "inner_fouling_resistance_m2k_w": 0.0001,
                "outer_fouling_resistance_m2k_w": 0.0002,
            },
            solver_absolute_residual_w=1e-3,
            solver_relative_residual_fraction=1e-8,
            solver_bracket_temperature_tolerance_k=1e-4,
            solver_max_iterations=100,
            tube_boundary_condition="adiabatic",
            annulus_boundary_condition="adiabatic",
            minimum_terminal_delta_t=5.0,
        )
        ec = ExecutionContextSnapshot()
        pi = ProviderIdentitySnapshot(
            name="test",
            version="1",
            git_revision="abc",
            reference_state_policy="default",
        )
        return VerifiedRatingEvidenceSnapshot(
            rating_status=RatingStatus.SUCCEEDED,
            heat_duty_w=1000.0,
            hot_outlet_temperature_k=350.0,
            cold_outlet_temperature_k=310.0,
            area_inner_m2=1.5,
            area_outer_m2=2.0,
            UA_w_k=500.0,
            LMTD_k=40.0,
            energy_residual_w=0.001,
            ua_lmtd_residual_w=0.002,
            tube_inlet_density_kg_m3=1000.0,
            annulus_inlet_density_kg_m3=800.0,
            tube_flow_area_m2=0.02,
            annulus_flow_area_m2=0.04,
            rating_result_hash="sha256:" + "a" * 64,
            rating_provenance_digest="prov_digest",
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            rating_request_identity=rri,
            rating_request_identity_digest=sha256_digest(rating_request_identity_payload(rri)),
            rating_execution_context=ec,
            rating_execution_context_digest=sha256_digest(execution_context_snapshot_payload(ec)),
            provider_identity=pi,
        )

    def test_payload_has_exactly_26_fields(self) -> None:
        evidence = self._baseline_evidence()
        payload = verified_rating_evidence_payload(evidence)
        assert len(payload) == 26
        assert tuple(payload.keys()) == EXPECTED_26_FIELD_KEYS

    def test_payload_digest_stable(self) -> None:
        ev1 = self._baseline_evidence()
        ev2 = self._baseline_evidence()
        assert sha256_digest(verified_rating_evidence_payload(ev1)) == sha256_digest(
            verified_rating_evidence_payload(ev2)
        )

    @pytest.mark.parametrize(
        ("field_name", "mutate_kwargs"),
        [
            ("rating_status", {"rating_status": RatingStatus.BLOCKED}),
            ("heat_duty_w", {"heat_duty_w": 999.0}),
            ("hot_outlet_temperature_k", {"hot_outlet_temperature_k": 340.0}),
            ("cold_outlet_temperature_k", {"cold_outlet_temperature_k": 300.0}),
            ("area_inner_m2", {"area_inner_m2": 1.0}),
            ("area_outer_m2", {"area_outer_m2": 1.5}),
            ("UA_w_k", {"UA_w_k": 499.0}),
            ("LMTD_k", {"LMTD_k": 39.0}),
            ("energy_residual_w", {"energy_residual_w": 0.002}),
            ("ua_lmtd_residual_w", {"ua_lmtd_residual_w": 0.003}),
            ("tube_inlet_density_kg_m3", {"tube_inlet_density_kg_m3": 900.0}),
            ("annulus_inlet_density_kg_m3", {"annulus_inlet_density_kg_m3": 700.0}),
            ("tube_flow_area_m2", {"tube_flow_area_m2": 0.01}),
            ("annulus_flow_area_m2", {"annulus_flow_area_m2": 0.03}),
            ("rating_result_hash", {"rating_result_hash": "sha256:" + "b" * 64}),
            ("rating_provenance_digest", {"rating_provenance_digest": "other_prov"}),
            (
                "hash_verification_outcome",
                {"hash_verification_outcome": VerificationOutcome.FAILED},
            ),
            (
                "provenance_verification_outcome",
                {"provenance_verification_outcome": VerificationOutcome.FAILED},
            ),
            (
                "rating_request_identity_digest",
                {"rating_request_identity_digest": "different_digest"},
            ),
            (
                "rating_execution_context_digest",
                {"rating_execution_context_digest": "different_ec"},
            ),
        ],
    )
    def test_top_level_field_mutation_changes_digest(
        self,
        field_name: str,
        mutate_kwargs: dict,
    ) -> None:
        baseline = self._baseline_evidence()
        mutated = baseline.model_copy(update=mutate_kwargs)
        base_digest = sha256_digest(verified_rating_evidence_payload(baseline))
        mut_digest = sha256_digest(verified_rating_evidence_payload(mutated))
        assert base_digest != mut_digest, f"Field {field_name} mutation did not change digest"

    def test_warning_digests_permutation_stable(self) -> None:
        from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity

        base = self._baseline_evidence()
        w1 = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="test",
            allows_continuation=True,
        )
        w2 = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="other",
            allows_continuation=True,
        )
        ev_a = base.model_copy(update={"warnings": (w1, w2)})
        ev_b = base.model_copy(update={"warnings": (w2, w1)})
        assert sha256_digest(verified_rating_evidence_payload(ev_a)) == sha256_digest(
            verified_rating_evidence_payload(ev_b)
        )

    def test_blocker_digests_permutation_stable(self) -> None:
        from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity

        base = self._baseline_evidence()
        b1 = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="blocker1",
            allows_continuation=False,
        )
        b2 = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="blocker2",
            allows_continuation=False,
        )
        ev_a = base.model_copy(update={"blockers": (b1, b2)})
        ev_b = base.model_copy(update={"blockers": (b2, b1)})
        assert sha256_digest(verified_rating_evidence_payload(ev_a)) == sha256_digest(
            verified_rating_evidence_payload(ev_b)
        )
