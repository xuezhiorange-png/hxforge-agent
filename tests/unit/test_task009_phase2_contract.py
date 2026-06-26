"""
TASK-009 Phase 2 contract tests — SizingRequestIdentity, CalculationContext,
CandidateEvaluationIdentity, verification states, provider consistency,
adapter mapping, batch isolation, and trust boundaries.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
    RatingStatus,
)
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.context import (
    ExpectedProviderIdentity,
    OptimizationObjective,
    SizingRequestIdentity,
    build_candidate_calculation_context,
    build_sizing_request_identity,
    create_passed_sizing_gate,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationIdentity,
    CandidateEvaluationState,
    FeasibilityStatus,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    check_provider_consistency,
    verify_and_evaluate_candidate,
)
from hexagent.optimization.materialization import (
    materialize_lengths_for_source,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthSource,
    SizingRequest,
)

# ============================================================================
# Fixtures
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
    from hexagent.optimization.catalog import compute_catalog_content_hash

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


def _make_minimal_result(
    hash_passes: bool = True,
    prov_passes: bool = True,
    status: RatingStatus = RatingStatus.SUCCEEDED,
    with_request_identity: bool = True,
) -> Any:
    """Create a duck-typed RatingResult using object.__new__."""
    result = object.__new__(RatingResult)
    # Use __setattr__ to bypass frozen
    object.__setattr__(result, "status", status)

    from hexagent.exchangers.double_pipe.thermal import FlowArrangement

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

    # Request identity
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

        from hexagent.core.heat_balance import ExecutionContextSnapshot

        ec = ExecutionContextSnapshot()
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


def _default_expected_provider() -> ExpectedProviderIdentity:
    return ExpectedProviderIdentity(
        name="test_provider",
        version="1.0",
        git_revision="abc123",
        reference_state_policy="default",
    )


def _default_sizing_identity_digest() -> str:
    return "sha256:" + "a" * 64


# ============================================================================
# P0-1: SizingRequestIdentity
# ============================================================================


class TestSizingRequestIdentity:
    """Full SizingRequestIdentity contract."""

    def _make_identity(self, **overrides: Any) -> SizingRequestIdentity:
        opt = _make_opt()
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        params = {
            "request": req,
            "hot_fluid_name": "water",
            "cold_fluid_name": "brine",
            "hot_fluid_equation_of_state": "iapws97",
            "cold_fluid_equation_of_state": "nacl",
            "hot_inlet_temperature_k": 373.0,
            "cold_inlet_temperature_k": 293.0,
            "hot_inlet_pressure_pa": 1e5,
            "cold_inlet_pressure_pa": 2e5,
            "hot_mass_flow_kg_s": 10.0,
            "cold_mass_flow_kg_s": 5.0,
            "tube_in_hot": True,
            "flow_arrangement": FlowArrangement.COUNTERFLOW,
            "minimum_terminal_delta_t": 5.0,
            "required_duty_w": 50000.0,
            "duty_absolute_tolerance_w": 500.0,
            "duty_relative_tolerance": 0.05,
            "optimization_objective": OptimizationObjective.MINIMIZE_AREA,
            "top_n": 5,
            "solver_params": SolverParams(),
            "expected_provider_identity": _default_expected_provider(),
        }
        params.update(overrides)
        return build_sizing_request_identity(**params)

    def test_required_duty_must_be_typed(self) -> None:
        """required_duty_w must be present and a float."""
        ident = self._make_identity(required_duty_w=1.0)
        assert isinstance(ident.required_duty_w, float)

    def test_top_n_bool_rejected(self) -> None:
        with pytest.raises(TypeError):
            self._make_identity(top_n=True)  # type: ignore[arg-type]

    def test_top_n_zero_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._make_identity(top_n=0)

    def test_top_n_negative_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._make_identity(top_n=-1)

    def test_solver_params_bound(self) -> None:
        ident = self._make_identity()
        assert ident.rating_solver_absolute_residual_w == SolverParams().absolute_residual_w

    def test_design_case_uuid(self) -> None:
        uid = UUID("12345678-1234-5678-1234-567812345678")
        ident = self._make_identity(design_case_revision_id=uid)
        assert ident.design_case_revision_id == uid

    def test_calculation_run_uuid(self) -> None:
        uid = UUID("87654321-4321-8765-4321-876543210987")
        ident = self._make_identity(calculation_run_id=uid)
        assert ident.calculation_run_id == uid

    def test_components_canonical_order(self) -> None:
        components = (("water", 0.8), ("steam", 0.2))
        ident = self._make_identity(hot_fluid_normalized_components=components)
        # Already canonical by field_validator
        assert ident.hot_fluid_normalized_components == (("steam", 0.2), ("water", 0.8))

    def test_duplicate_component_rejected(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            self._make_identity(hot_fluid_normalized_components=(("water", 0.5), ("water", 0.5)))

    def test_catalog_permutation_same_digest(self) -> None:
        o1 = _make_opt("a", lengths=(1.0,))
        o2 = _make_opt("b", lengths=(2.0,))
        ca = _make_cat("X", options=(o1,))
        cb = _make_cat("Y", options=(o2,))
        ident_a = self._make_identity(request=SizingRequest(catalogs=(ca, cb)))
        ident_b = self._make_identity(request=SizingRequest(catalogs=(cb, ca)))
        assert ident_a.sizing_request_identity_digest == ident_b.sizing_request_identity_digest

    def test_any_field_mutation_changes_digest(self) -> None:
        base = self._make_identity()
        mutated = self._make_identity(hot_fluid_name="steam")
        assert base.sizing_request_identity_digest != mutated.sizing_request_identity_digest

    def test_uuid_json_roundtrip(self) -> None:
        uid = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        ident = self._make_identity(design_case_revision_id=uid)
        j = ident.model_dump_json()
        restored = SizingRequestIdentity.model_validate_json(j)
        assert restored.design_case_revision_id == uid


# ============================================================================
# P0-2: CalculationContext
# ============================================================================


class TestCandidateContext:
    """Typed per-candidate CalculationContext."""

    def _make_ctx_identity(
        self,
        digest_suffix: str = "d",
    ) -> SizingRequestIdentity:
        opt = _make_opt()
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        return build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMIZE_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=_default_expected_provider(),
        )

    def test_uuid5_deterministic(self) -> None:
        ident = self._make_ctx_identity("d1")
        ctx_a = build_candidate_calculation_context(ident, "sq_1")
        ctx_b = build_candidate_calculation_context(ident, "sq_1")
        assert ctx_a.request_id == ctx_b.request_id
        assert ctx_a.request_id.version == 5

    def test_candidate_changes_id(self) -> None:
        ident = self._make_ctx_identity("d2")
        a = build_candidate_calculation_context(ident, "sq_a")
        b = build_candidate_calculation_context(ident, "sq_b")
        assert a.request_id != b.request_id

    def test_sizing_identity_changes_id(self) -> None:
        # Different fluid names produce different digests -> different IDs
        opt = _make_opt()
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        ident_a = build_sizing_request_identity(
            request=req,
            hot_fluid_name="water",
            cold_fluid_name="brine",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMIZE_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=_default_expected_provider(),
        )
        ident_b = build_sizing_request_identity(
            request=req,
            hot_fluid_name="steam",
            cold_fluid_name="oil",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMIZE_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=_default_expected_provider(),
        )
        a = build_candidate_calculation_context(ident_a, "sq1")
        b = build_candidate_calculation_context(ident_b, "sq1")
        assert a.request_id != b.request_id

    def test_domain_id_preserved(self) -> None:
        uid = UUID("00000000-0000-0000-0000-000000000001")
        # Use SizingRequestIdentity with domain IDs
        opt = _make_opt()
        cat = _make_cat(options=(opt,))
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMIZE_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=_default_expected_provider(),
            design_case_revision_id=uid,
        )
        ctx = build_candidate_calculation_context(ident, "sq_1")
        assert ctx.design_case_revision_id == uid

    def test_missing_id_none(self) -> None:
        ident = self._make_ctx_identity("d3")
        ctx = build_candidate_calculation_context(ident, "sq_1")
        assert ctx.design_case_revision_id is None
        assert ctx.calculation_run_id is None


# ============================================================================
# P0-3: CandidateEvaluationIdentity
# ============================================================================


class TestEvaluationIdentity:
    """CandidateEvaluationIdentity — only for VERIFIED."""

    def _make_eval_id(self, **kw: Any) -> CandidateEvaluationIdentity:
        params = dict(
            sizing_request_identity_digest="sha256:digest",
            source_qualified_candidate_id="sq_id",
            rating_request_identity_digest="sha256:req_id",
            rating_result_hash="sha256:result_hash",
            rating_provenance_digest="sha256:prov_digest",
            rating_execution_context_digest="sha256:ctx_digest",
            provider_identity_digest="sha256:pi_digest",
            tube_in_hot=True,
        )
        params.update(kw)
        return CandidateEvaluationIdentity(**params)

    def test_identity_present_only_for_verified(self) -> None:
        """VERIFIED evaluation record has identity."""
        result = _make_minimal_result()
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        assert rec.candidate_evaluation_identity is not None

    def test_integrity_invalid_no_identity(self) -> None:
        result = _make_minimal_result(hash_passes=False)
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_identity is None

    def test_runtime_failed_no_identity(self) -> None:
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            "not_a_rating_result",
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_identity is None

    def test_tube_in_hot_bound(self) -> None:
        eid = self._make_eval_id(tube_in_hot=True)
        assert eid.tube_in_hot is True

    def test_field_mutation_changes_digest(self) -> None:
        a = self._make_eval_id(tube_in_hot=True)
        b = self._make_eval_id(tube_in_hot=False)
        assert a.candidate_evaluation_identity_digest != b.candidate_evaluation_identity_digest


# ============================================================================
# P0-4/P0-5: Exact-type safe extraction + ClaimedAuditSnapshot
# ============================================================================


class TestExactTypeBoundary:
    """Non-exact RatingResult must be RUNTIME_FAILED + UNREADABLE."""

    def test_non_exact_type(self) -> None:
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            {"not": "rating"},
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        # Non-exact objects never enter audit; audit is None
        assert rec.claimed_rating_result_audit is None

    def test_audit_snapshot_has_claim_state(self) -> None:
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            _make_minimal_result(hash_passes=False),
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.claimed_rating_result_audit is not None
        assert isinstance(rec.claimed_rating_result_audit.claim_state, str)


# ============================================================================
# P0-6: One-shot frozen verified evidence + P0-7: Feasibility
# ============================================================================


class TestVerifiedEvidence:
    """VerifiedEvidence is one-shot constructed and complete."""

    def test_rating_status_typed(self) -> None:
        result = _make_minimal_result()
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        ev = rec.verified_rating_evidence
        assert ev is not None
        assert type(ev.rating_status) is RatingStatus

    def test_evidence_has_request_identity_digest(self) -> None:
        result = _make_minimal_result()
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        ev = rec.verified_rating_evidence
        assert ev is not None
        assert ev.rating_request_identity_digest != ""

    def test_evidence_has_execution_context_digest(self) -> None:
        result = _make_minimal_result()
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        ev = rec.verified_rating_evidence
        assert ev is not None
        assert ev.rating_execution_context_digest != ""

    def test_evidence_digest_stable(self) -> None:
        result = _make_minimal_result()
        r1 = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        r2 = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        ev1 = r1.verified_rating_evidence
        ev2 = r2.verified_rating_evidence
        assert ev1 is not None and ev2 is not None
        assert ev1.evidence_digest == ev2.evidence_digest

    def test_succeeded_still_not_feasible(self) -> None:
        """Phase 2: verified SUCCEEDED candidate has feasible=False."""
        result = _make_minimal_result(status=RatingStatus.SUCCEEDED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        assert not rec.feasible
        assert rec.feasibility_status == FeasibilityStatus.NOT_EVALUATED.value

    def test_json_roundtrip_evidence(self) -> None:
        result = _make_minimal_result()
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        ev = rec.verified_rating_evidence
        assert ev is not None
        j = ev.model_dump_json()
        restored = VerifiedRatingEvidenceSnapshot.model_validate_json(j)
        assert restored.evidence_digest == ev.evidence_digest


# ============================================================================
# P0-8: Provider matching from verified result
# ============================================================================


class TestProviderMatching:
    """Provider matching uses result.provider_identity."""

    def test_expected_match(self) -> None:
        result = _make_minimal_result()
        ep = _default_expected_provider()
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=ep,
        )
        assert rec.provider_identity_matches

    def test_mandatory_mismatch(self) -> None:
        result = _make_minimal_result()
        ep = ExpectedProviderIdentity(
            name="wrong",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=ep,
        )
        assert not rec.provider_identity_matches

    def test_mismatch_retains_evidence(self) -> None:
        result = _make_minimal_result()
        ep = ExpectedProviderIdentity(
            name="wrong",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=ep,
        )
        assert rec.verified_rating_evidence is not None
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value

    def test_mismatch_not_feasible(self) -> None:
        result = _make_minimal_result(status=RatingStatus.SUCCEEDED)
        ep = ExpectedProviderIdentity(
            name="wrong",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=ep,
        )
        assert not rec.feasible
        assert rec.feasibility_status == FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH.value


# ============================================================================
# P0-9: Cross-candidate provider consistency
# ============================================================================


class TestProviderConsistency:
    """Cross-candidate provider consistency check."""

    def test_identical_verified_passes(self) -> None:
        result = _make_minimal_result()
        r1 = verify_and_evaluate_candidate(
            0,
            "a",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        r2 = verify_and_evaluate_candidate(
            1,
            "b",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        results = check_provider_consistency((r1, r2))
        for r in results:
            assert r.provider_identity_matches

    def test_provider_consistency_fails_on_mismatch(self) -> None:
        """Simulate different provider by setting different evidence."""
        r1 = verify_and_evaluate_candidate(
            0,
            "a",
            _make_minimal_result(),
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        r2 = verify_and_evaluate_candidate(
            1,
            "b",
            _make_minimal_result(),
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        # Manually set different provider identity on r2's evidence
        ev2 = r2.verified_rating_evidence
        if ev2 is not None:
            from hexagent.core.heat_balance import ProviderIdentitySnapshot

            pi2 = ProviderIdentitySnapshot(
                name="other",
                version="2.0",
                git_revision="xyz",
                reference_state_policy="alt",
            )
            object.__setattr__(ev2, "provider_identity", pi2)
        results = check_provider_consistency((r1, r2))
        assert any(not r.provider_identity_matches for r in results)

    def test_integrity_invalid_ignored(self) -> None:
        """Claimed provider from integrity-invalid does not affect baseline."""
        r_valid = verify_and_evaluate_candidate(
            0,
            "a",
            _make_minimal_result(),
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        r_invalid = verify_and_evaluate_candidate(
            1,
            "b",
            _make_minimal_result(hash_passes=False),
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        results = check_provider_consistency((r_invalid, r_valid))
        verified_recs = [
            r
            for r in results
            if r.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        ]
        assert all(r.provider_identity_matches for r in verified_recs)


# ============================================================================
# P0-10: INTEGRITY_INVALID invariants
# ============================================================================


class TestIntegrityInvalid:
    """INTEGRITY_INVALID invariants."""

    def test_rating_status_is_none(self) -> None:
        result = _make_minimal_result(hash_passes=False)
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID.value
        assert rec.rating_status is None

    def test_no_evaluation_identity(self) -> None:
        result = _make_minimal_result(hash_passes=False)
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_identity is None
        assert rec.verified_rating_evidence is None

    def test_invalid_evidence_present(self) -> None:
        result = _make_minimal_result(hash_passes=False)
        rec = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.invalid_rating_evidence is not None
        assert (
            rec.invalid_rating_evidence.hash_verification_outcome
            == VerificationOutcome.FAILED.value
        )


# ============================================================================
# Verification state tests
# ============================================================================


class TestVerificationStates:
    """All verification states."""

    def test_hash_false(self) -> None:
        r = _make_minimal_result(hash_passes=False)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            r,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID.value
        assert rec.hash_verification_outcome == VerificationOutcome.FAILED.value
        assert rec.provenance_verification_outcome == VerificationOutcome.NOT_RUN.value

    def test_hash_raises(self) -> None:
        result = _make_minimal_result()

        def _raise() -> bool:
            raise RuntimeError("hash crash")

        object.__setattr__(result, "verify_hash", _raise)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        assert rec.hash_verification_outcome == VerificationOutcome.ERROR.value

    def test_provenance_false(self) -> None:
        r = _make_minimal_result(prov_passes=False)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            r,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID.value
        assert rec.hash_verification_outcome == VerificationOutcome.PASSED.value
        assert rec.provenance_verification_outcome == VerificationOutcome.FAILED.value

    def test_provenance_raises(self) -> None:
        result = _make_minimal_result()

        def _raise() -> bool:
            raise RuntimeError("prov crash")

        object.__setattr__(result, "verify_provenance", _raise)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        assert rec.provenance_verification_outcome == VerificationOutcome.ERROR.value

    def test_both_pass_succeeded(self) -> None:
        r = _make_minimal_result(status=RatingStatus.SUCCEEDED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            r,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        assert rec.verified_rating_evidence is not None

    def test_both_pass_blocked(self) -> None:
        r = _make_minimal_result(status=RatingStatus.BLOCKED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            r,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value

    def test_both_pass_failed(self) -> None:
        r = _make_minimal_result(status=RatingStatus.FAILED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            r,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value


# ============================================================================
# Materialization + quantum + count checks
# ============================================================================


class TestMaterializationQuantum:
    """Materialization quantum contract."""

    def test_external_quantum_validation(self) -> None:
        """External quantum mismatch must be rejected."""
        opt = _make_opt(quantum="0.1", lengths=(1.0,))
        from hexagent.optimization.errors import CatalogInvalid

        with pytest.raises(CatalogInvalid):
            materialize_lengths_for_source(
                opt.length_source,
                quantum="0.01",
            )

    def test_external_quantum_matches(self) -> None:
        opt = _make_opt(quantum="0.1", lengths=(1.0, 2.0))
        lengths = materialize_lengths_for_source(
            opt.length_source,
            quantum="0.1",
        )
        assert len(lengths) == 2

    def test_default_quantum_from_source(self) -> None:
        opt = _make_opt(quantum="0.1", lengths=(1.0, 2.0, 3.0))
        lengths = materialize_lengths_for_source(opt.length_source)
        assert len(lengths) == 3


# ============================================================================
# PassedSizingGate artifact
# ============================================================================


class TestPassedSizingGate:
    """PassedSizingGate artifact."""

    def test_gate_created(self) -> None:
        from hexagent.optimization.models import OptionRawCountRecord

        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash="h1",
            assembly_option_id="opt1",
            canonical_length_quantum_m="0.1",
            raw_count=5,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest="sha256:d",
            raw_combination_count=5,
            effective_cap=100,
            per_option_records=(rec,),
        )
        assert gate.status == "passed"
        assert gate.gate_digest != ""
        assert gate.verify_digest()

    def test_gate_digest_deterministic(self) -> None:
        from hexagent.optimization.models import OptionRawCountRecord

        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash="h1",
            assembly_option_id="opt1",
            canonical_length_quantum_m="0.1",
            raw_count=5,
        )
        g1 = create_passed_sizing_gate(
            sizing_request_identity_digest="sha256:d",
            raw_combination_count=5,
            effective_cap=100,
            per_option_records=(rec,),
        )
        g2 = create_passed_sizing_gate(
            sizing_request_identity_digest="sha256:d",
            raw_combination_count=5,
            effective_cap=100,
            per_option_records=(rec,),
        )
        assert g1.gate_digest == g2.gate_digest
        assert g1.verify_digest()
        assert g2.verify_digest()


# ============================================================================
# Phase boundary tests
# ============================================================================


class TestPhaseBoundary:
    """Phase 2 must not implement Phase 3 features."""

    def test_verified_succeeded_is_not_feasible(self) -> None:
        result = _make_minimal_result(status=RatingStatus.SUCCEEDED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        assert rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        assert not rec.feasible  # Phase 2: always not feasible

    def test_no_ranking(self) -> None:
        """Verify no ranking/selected/feasibility fields exist in Phase 2 code."""
        result = _make_minimal_result(status=RatingStatus.SUCCEEDED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        # Not checking that ranking exists — checking that it doesn't
        assert not hasattr(rec, "selected_candidate")
        assert not hasattr(rec, "top_candidates")

    def test_no_duty_tolerance_processing(self) -> None:
        """Duty feasibility must not be implemented."""
        result = _make_minimal_result(status=RatingStatus.SUCCEEDED)
        rec = verify_and_evaluate_candidate(
            0,
            "sq",
            result,
            sizing_request_identity_digest="d",
            tube_in_hot=True,
            expected_provider=_default_expected_provider(),
        )
        ev = rec.verified_rating_evidence
        assert ev is not None
        # No margin/shortfall fields
        assert not hasattr(ev, "duty_margin_w")
        assert not hasattr(ev, "target_satisfaction")
