"""
TASK-009 Phase 3 comprehensive unit tests.

Covers:
1. NORMAL FLOW — feasibility → ranking → Top-N
2. GATE & MATERIALIZATION
3. BATCH INPUT CONSISTENCY
4. INTEGRITY & PROVENANCE (fail-closed)
5. VERIFIER — all public entry points
6. RANKING & TOP-N
7. FAILURE PROPAGATION
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import (
    ExecutionContextSnapshot,
    ProviderIdentitySnapshot,
)
from hexagent.domain.messages import (
    ErrorCode,
    RunFailure,
)
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingStatus,
)
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.context import (
    ExpectedProviderIdentity,
    OptimizationObjective,
    SizingRequestIdentity,
    build_sizing_request_identity,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationIdentity,
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    FeasibilityStatus,
    InvalidRatingEvidenceRecord,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    _build_run_failure_descriptor,
    execution_context_snapshot_payload,
    provider_identity_snapshot_payload,
    rating_request_identity_payload,
)
from hexagent.optimization.identities import (
    ManufacturableCandidate,
    build_candidate,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthSource,
    SizingRequest,
)
from hexagent.optimization.phase3_builder import (
    OptimizationResultCoreValues,
    _build_feasible,
    _build_infeasible,
    _build_provider_mismatch,
    _expected_ranked_values,
    _map_non_verified,
    _phase3_runtime,
    _phase3_runtime_from_validation,
    build_ranked_candidate_record,
    classify_candidate,
    validate_blocked_evidence,
    validate_failed_evidence,
)
from hexagent.optimization.phase3_core import (
    FailureOrigin,
    FeasibilityDiagnosticKey,
    Phase2SourceRecordDescriptor,
    Phase2SourceRecordIdentitySnapshot,
    Phase2SourceRecordSnapshot,
    Phase3Disposition,
    Phase3MessageDescriptor,
    Phase3MessageDescriptorBinding,
    Phase3PreparationFailureStage,
    Phase3PreparationStatus,
    Phase3ProvenanceRelation,
    Phase3RunFailureDescriptorBinding,
    TerminationStatus,
    build_identity_snapshot,
    build_phase2_source_record_descriptor,
    build_phase2_source_record_snapshot,
    build_phase3_message_descriptor_binding,
    build_phase3_run_failure_descriptor_binding,
    canonical_decimal,
    canonical_decimal_string,
    to_canonical_decimal,
    verify_canonical_decimal_string,
)
from pydantic import ValidationError
from hexagent.optimization.phase3_evaluation import (
    Phase3CandidateClassificationInput,
    Phase3EvaluationInput,
    Phase3SourceRecordBinding,
    build_candidate_disposition_record,
    build_phase3_candidate_preparation_result,
    build_phase3_source_record_binding,
    candidate_disposition_payload,
    verify_candidate_disposition_failure_matrix,
    verify_phase3_index_artifact_matrix,
)
from hexagent.optimization.phase3_verifier import (
    verify_phase3_message_descriptor_or_raise,
)

# ============================================================================
# Shared digest pattern for tests
# ============================================================================

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DUMMY_DIGEST = "sha256:" + "a" * 64
DUMMY_DIGEST2 = "sha256:" + "b" * 64
DUMMY_DIGEST3 = "sha256:" + "c" * 64
DUMMY_DIGEST4 = "sha256:" + "d" * 64


def _make_digest(seed: str) -> str:
    return sha256_digest({"seed": seed})


# ============================================================================
# Helpers for building test fixtures
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


def _make_catalog(
    catalog_id: str = "c1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    from hexagent.optimization.catalog import compute_catalog_content_hash

    h = compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
    )
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
        catalog_content_hash=h,
    )


def _make_provider() -> ProviderIdentitySnapshot:
    return ProviderIdentitySnapshot(
        name="test_provider",
        version="1.0",
        git_revision="abc123",
        reference_state_policy="default",
    )


def _make_exec_ctx() -> ExecutionContextSnapshot:
    return ExecutionContextSnapshot()


def _make_blocked_evidence() -> VerifiedRatingEvidenceSnapshot:
    """Build blocked evidence (no thermal results, blocked status)."""
    rri = RatingRequestIdentity(
        hot_fluid_name="Water",
        hot_fluid_backend="CP",
        hot_fluid_components=(),
        cold_fluid_name="Water",
        cold_fluid_backend="CP",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
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
    exec_ctx = _make_exec_ctx()
    rri_digest = sha256_digest(rating_request_identity_payload(rri))
    ec_digest = sha256_digest(execution_context_snapshot_payload(exec_ctx))
    return VerifiedRatingEvidenceSnapshot(
        rating_status=RatingStatus.BLOCKED,
        heat_duty_w=None,
        hot_outlet_temperature_k=None,
        cold_outlet_temperature_k=None,
        area_inner_m2=4.0,
        area_outer_m2=5.0,
        tube_flow_area_m2=0.002,
        annulus_flow_area_m2=0.005,
        provider_identity=_make_provider(),
        rating_result_hash="sha256:" + "e" * 64,
        rating_provenance_digest="sha256:" + "f" * 64,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        rating_request_identity=rri,
        rating_request_identity_digest=rri_digest,
        rating_execution_context=exec_ctx,
        rating_execution_context_digest=ec_digest,
    )


def _make_evidence(
    *,
    heat_duty_w: float = 5000.0,
    area_outer_m2: float = 5.0,
    hot_outlet_temperature_k: float = 310.0,
    cold_outlet_temperature_k: float = 330.0,
    rating_status: RatingStatus = RatingStatus.SUCCEEDED,
) -> VerifiedRatingEvidenceSnapshot:
    rri = RatingRequestIdentity(
        hot_fluid_name="Water",
        hot_fluid_backend="CP",
        hot_fluid_components=(),
        cold_fluid_name="Water",
        cold_fluid_backend="CP",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
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
    exec_ctx = _make_exec_ctx()
    rri_digest = sha256_digest(rating_request_identity_payload(rri))
    ec_digest = sha256_digest(execution_context_snapshot_payload(exec_ctx))
    return VerifiedRatingEvidenceSnapshot(
        rating_status=rating_status,
        heat_duty_w=heat_duty_w,
        hot_outlet_temperature_k=hot_outlet_temperature_k,
        cold_outlet_temperature_k=cold_outlet_temperature_k,
        area_inner_m2=area_outer_m2 * 0.8,
        area_outer_m2=area_outer_m2,
        tube_flow_area_m2=0.002,
        annulus_flow_area_m2=0.005,
        provider_identity=_make_provider(),
        rating_result_hash="sha256:" + "e" * 64,
        rating_provenance_digest="sha256:" + "f" * 64,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        rating_request_identity=rri,
        rating_request_identity_digest=rri_digest,
        rating_execution_context=exec_ctx,
        rating_execution_context_digest=ec_digest,
    )


def _make_candidate(
    evaluation_order_index: int = 0,
    effective_length_m: float = 1.0,
    catalog_id: str = "c1",
    option_id: str = "opt1",
) -> ManufacturableCandidate:
    """Build a ManufacturableCandidate using the real factory."""
    opt = _make_opt(option_id=option_id)
    cat = _make_catalog(catalog_id=catalog_id, options=(opt,))
    return build_candidate(
        catalog=cat,
        option=opt,
        effective_length_m_canonical=str(effective_length_m),
        evaluation_order_index=evaluation_order_index,
    )


def _make_cei(
    source_qualified_candidate_id: str,
    evidence: VerifiedRatingEvidenceSnapshot,
) -> CandidateEvaluationIdentity:
    """Build a CandidateEvaluationIdentity from evidence fields."""
    provider_digest = sha256_digest(provider_identity_snapshot_payload(evidence.provider_identity))
    return CandidateEvaluationIdentity(
        sizing_request_identity_digest=DUMMY_DIGEST,
        source_qualified_candidate_id=source_qualified_candidate_id,
        rating_request_identity_digest=evidence.rating_request_identity_digest,
        rating_result_hash=evidence.rating_result_hash,
        rating_provenance_digest=evidence.rating_provenance_digest,
        rating_execution_context_digest=evidence.rating_execution_context_digest,
        provider_identity_digest=provider_digest,
        tube_in_hot=True,
    )


def _make_verified_record(
    candidate: ManufacturableCandidate,
    evidence: VerifiedRatingEvidenceSnapshot | None = None,
    *,
    provider_identity_matches: bool = True,
    rating_status: str | None = "succeeded",
) -> CandidateEvaluationRecord:
    """Build a VERIFIED CandidateEvaluationRecord matching the given candidate."""
    ev = evidence or _make_evidence()
    source_id = candidate.source_qualified_candidate_id
    idx = candidate.evaluation_order_index
    cei = _make_cei(source_id, ev)
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_id,
        evaluation_order_index=idx,
        candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
        feasible=True,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        candidate_evaluation_identity=cei,
        verified_rating_evidence=ev,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
    )


def _make_ver(
    source_id: str = "c1",
    idx: int = 0,
    evidence: VerifiedRatingEvidenceSnapshot | None = None,
    *,
    provider_identity_matches: bool = True,
    rating_status: str | None = "succeeded",
) -> tuple[CandidateEvaluationRecord, ManufacturableCandidate]:
    cand = _make_candidate(evaluation_order_index=idx)
    rec = _make_verified_record(
        cand,
        evidence=evidence,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
    )
    return rec, cand


def _make_integrity_invalid_record(
    source_qualified_candidate_id: str = "cand_1",
    evaluation_order_index: int = 0,
    hash_outcome: VerificationOutcome = VerificationOutcome.FAILED,
    prov_outcome: VerificationOutcome = VerificationOutcome.NOT_RUN,
) -> CandidateEvaluationRecord:
    inv = InvalidRatingEvidenceRecord(
        candidate_id=source_qualified_candidate_id,
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=prov_outcome,
    )
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID,
        feasible=False,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=prov_outcome,
        invalid_rating_evidence=inv,
        provider_identity_matches=False,
    )


def _make_runtime_failed_record(
    source_qualified_candidate_id: str = "cand_1",
    evaluation_order_index: int = 0,
) -> CandidateEvaluationRecord:
    failure = RunFailure(
        code=ErrorCode.INPUT_INCONSISTENT,
        message="Runtime error",
        context=(("source", "test"),),
    )
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
        feasible=False,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=VerificationOutcome.NOT_RUN,
        provenance_verification_outcome=VerificationOutcome.NOT_RUN,
        evaluation_failure=failure,
        provider_identity_matches=True,
    )


def _make_unevaluated_record(
    source_qualified_candidate_id: str = "cand_1",
    evaluation_order_index: int = 0,
) -> CandidateEvaluationRecord:
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=CandidateEvaluationState.UNEVALUATED,
        feasible=False,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=VerificationOutcome.NOT_RUN,
        provenance_verification_outcome=VerificationOutcome.NOT_RUN,
        provider_identity_matches=True,
    )


def _make_csnap(
    rec: CandidateEvaluationRecord,
    sdesc: Phase2SourceRecordDescriptor,
) -> Phase2SourceRecordSnapshot:
    """Build a complete_snapshot from record + descriptor for testing."""
    return build_phase2_source_record_snapshot(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        candidate_evaluation_state=rec.candidate_evaluation_state,
        feasible=rec.feasible,
        feasibility_status=rec.feasibility_status,
        hash_verification_outcome=rec.hash_verification_outcome,
        provenance_verification_outcome=rec.provenance_verification_outcome,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=(
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None
            else None
        ),
        verified_rating_evidence_digest=(
            rec.verified_rating_evidence.compute_explicit_evidence_digest()
            if rec.verified_rating_evidence is not None
            else None
        ),
        invalid_rating_evidence_digest=(
            rec.invalid_rating_evidence.invalid_evidence_digest
            if rec.invalid_rating_evidence is not None
            else None
        ),
        claimed_rating_result_audit_digest=(
            rec.verified_rating_evidence.rating_result_hash
            if rec.verified_rating_evidence is not None
            else None
        ),
        evaluation_failure_digest=(
            rec.evaluation_failure.failure_digest if rec.evaluation_failure is not None else None
        ),
        phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
        warning_descriptor_binding_digests=(),
        blocker_descriptor_binding_digests=(),
        source_evaluation_failure_binding_digest=None,
        evidence_failure_binding_digest=None,
    )


def _make_sizing_request_identity(
    *,
    optimization_objective: OptimizationObjective = (
        OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA
    ),
    top_n: int = 3,
) -> SizingRequestIdentity:
    cat = _make_catalog(options=(_make_opt(),))
    return build_sizing_request_identity(
        request=SizingRequest(catalogs=(cat,)),
        hot_fluid_name="Water",
        cold_fluid_name="Water",
        hot_fluid_equation_of_state="IdealGas",
        cold_fluid_equation_of_state="IdealGas",
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        tube_in_hot=True,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        minimum_terminal_delta_t=5.0,
        required_duty_w=5000.0,
        duty_absolute_tolerance_w=500.0,
        duty_relative_tolerance=0.1,
        optimization_objective=optimization_objective,
        top_n=top_n,
        solver_params=SolverParams(),
        expected_provider_identity=ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        ),
    )


def _make_sizing_request_identity_parallel(
    *,
    optimization_objective: OptimizationObjective = (
        OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA
    ),
    top_n: int = 3,
) -> SizingRequestIdentity:
    cat = _make_catalog(options=(_make_opt(),))
    return build_sizing_request_identity(
        request=SizingRequest(catalogs=(cat,)),
        hot_fluid_name="Water",
        cold_fluid_name="Water",
        hot_fluid_equation_of_state="IdealGas",
        cold_fluid_equation_of_state="IdealGas",
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        tube_in_hot=True,
        flow_arrangement=FlowArrangement.PARALLEL,
        minimum_terminal_delta_t=5.0,
        required_duty_w=5000.0,
        duty_absolute_tolerance_w=500.0,
        duty_relative_tolerance=0.1,
        optimization_objective=optimization_objective,
        top_n=top_n,
        solver_params=SolverParams(),
        expected_provider_identity=ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        ),
    )


def _make_message_descriptor(
    original_code: str = "TEST001",
    owner_sort_key: tuple = ("a", "TEST001", "c", "d", (), "e"),
    message_payload_digest: str | None = None,
) -> Phase3MessageDescriptor:
    if message_payload_digest is None:
        message_payload_digest = sha256_digest({"msg": original_code})
    return Phase3MessageDescriptor(
        owner_sort_key=owner_sort_key,
        original_code=original_code,
        message_payload_digest=message_payload_digest,
    )


def _make_message_descriptor_binding(
    desc: Phase3MessageDescriptor | None = None,
) -> Phase3MessageDescriptorBinding:
    if desc is None:
        desc = _make_message_descriptor()
    return build_phase3_message_descriptor_binding(desc)


def _make_failure_binding() -> Phase3RunFailureDescriptorBinding:
    failure = RunFailure(
        code=ErrorCode.INPUT_INCONSISTENT,
        message="test failure",
        context=(("key", "value"),),
    )
    desc = _build_run_failure_descriptor(failure)
    return build_phase3_run_failure_descriptor_binding(desc)


def _build_cin(
    rec: CandidateEvaluationRecord,
    candidate: ManufacturableCandidate,
    sri: SizingRequestIdentity,
    isnap: Phase2SourceRecordIdentitySnapshot,
    sdesc: Phase2SourceRecordDescriptor,
    sb: Phase3SourceRecordBinding,
) -> Phase3CandidateClassificationInput:
    """Build and validate a Phase3CandidateClassificationInput."""
    # Compute payload and digest before construction so validation passes
    cin_digest = sha256_digest(
        {
            "schema_version": 1,
            "source_identity_record_descriptor_digest": isnap.identity_snapshot_digest,
            "source_record_descriptor_digest": sdesc.descriptor_digest,
            "materialized_candidate_digest": candidate.source_qualified_candidate_id,
            "sizing_request_identity_digest": sri.sizing_request_identity_digest,
            "identity_snapshot_digest": sb.phase2_identity_snapshot_digest,
            "source_binding_digest": sb.binding_digest,
            "verified_rating_evidence_digest": sb.verified_rating_evidence_digest,
        }
    )
    return Phase3CandidateClassificationInput(
        source_record=rec,
        source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
        source_record_descriptor_digest=sdesc.descriptor_digest,
        materialized_candidate=candidate,
        sizing_request_identity=sri,
        sizing_request_identity_digest=sri.sizing_request_identity_digest,
        evidence_binding=sb,
        verified_rating_evidence_digest=sb.verified_rating_evidence_digest,
        classification_input_digest=cin_digest,
    )


# ============================================================================
# Section 1: NORMAL FLOW — end-to-end
# ============================================================================


class TestEndToEndFlow:
    """Complete feasibility → ranking → Top-N end-to-end tests."""

    def test_single_candidate_feasible(self) -> None:
        """Single verified candidate with adequate duty and delta-T → FEASIBLE."""
        evidence = _make_evidence(heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("BLOCK001")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.FEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.NONE

    def test_single_candidate_infeasible_duty(self) -> None:
        """Candidate with duty shortfall → INFEASIBLE."""
        evidence = _make_evidence(heat_duty_w=100.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B01")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.DUTY_SHORTFALL

    def test_multiple_candidates_mixed(self) -> None:
        """Multiple candidates with mixed feasible/infeasible."""
        evidence1 = _make_evidence(heat_duty_w=5000.0, area_outer_m2=5.0)
        evidence2 = _make_evidence(heat_duty_w=5000.0, area_outer_m2=3.0)
        evidence3 = _make_evidence(heat_duty_w=100.0)
        recs_and_cands = [
            _make_ver("c1", 0, evidence=evidence1),
            _make_ver("c2", 1, evidence=evidence2),
            _make_ver("c3", 2, evidence=evidence3),
        ]
        recs = [r for r, _ in recs_and_cands]
        cands = [c for _, c in recs_and_cands]
        cands = [
            _make_candidate(evaluation_order_index=0),
            _make_candidate(evaluation_order_index=1),
            _make_candidate(evaluation_order_index=2),
        ]
        sri = _make_sizing_request_identity(top_n=2)
        dispositions = []
        for i in range(3):
            isnap = build_identity_snapshot(recs[i])
            sdesc = build_phase2_source_record_descriptor(
                source_record=recs[i],
                identity_snapshot=isnap,
                verified_evidence=recs[i].verified_rating_evidence,
                source_failure_binding=None,
            )
            csnap = _make_csnap(recs[i], sdesc)
            wd = _make_message_descriptor(f"W{i}")
            bd = _make_message_descriptor(f"B{i}")
            wbd = _make_message_descriptor_binding(wd)
            bbd = _make_message_descriptor_binding(bd)
            ev = recs[i].verified_rating_evidence
            sb = build_phase3_source_record_binding(
                source_qualified_candidate_id=recs[i].source_qualified_candidate_id,  # f"c{i+1}"
                evaluation_order_index=i,
                phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
                verified_rating_evidence_digest=ev.compute_explicit_evidence_digest()
                if ev
                else None,
                phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
                warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
                blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
                source_evaluation_failure_binding_digest=None,
                evidence_failure_binding_digest=None,
            )
            cin = _build_cin(recs[i], cands[i], sri, isnap, sdesc, sb)
            disp = classify_candidate(
                cin,
                warning_descriptors=(wd,),
                blocker_descriptors=(bd,),
                warning_descriptor_bindings=(wbd,),
                blocker_descriptor_bindings=(bbd,),
                source_failure_binding=None,
                evidence_failure_binding=None,
                identity_snapshot=isnap,
                complete_snapshot=csnap,
                source_record_descriptor=sdesc,
            )
            dispositions.append(disp)
        feasible = [d for d in dispositions if d.disposition == Phase3Disposition.FEASIBLE]
        infeasible = [d for d in dispositions if d.disposition == Phase3Disposition.INFEASIBLE]
        assert len(feasible) == 2
        assert len(infeasible) == 1

    def test_all_blocked_candidates(self) -> None:
        """All candidates rated as 'blocked' → all infeasible."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        # Evidence has no warnings/blockers, so descriptors and bindings must be empty
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(),
            blocker_descriptors=(),
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=(),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.RATING_BLOCKED

    def test_terminal_delta_t_inadequate(self) -> None:
        """Terminal delta-T below minimum → INFEASIBLE."""
        evidence = _make_evidence(
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=296.0,  # close to cold_in=290 giving small delta
            cold_outlet_temperature_k=348.0,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE

    def test_parallel_flow_delta_t(self) -> None:
        """Parallel flow with valid delta-T → FEASIBLE."""
        evidence = _make_evidence(
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=320.0,
            cold_outlet_temperature_k=310.0,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity_parallel()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        # Should be feasible (hot_in=350, cold_in=290 → dt1=60, hot_out=320, cold_out=310 → dt2=10)
        assert disp.disposition == Phase3Disposition.FEASIBLE


# ============================================================================
# Section 2: GATE & MATERIALIZATION
# ============================================================================


class TestGateAndMaterialization:
    """Gate record consistency and materialization validation."""

    def test_catalog_identity_mismatch(self) -> None:
        """Catalog identity mismatch should be caught."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        isnap.verify_or_raise(source_record=rec)
        tampered = isnap.model_copy(update={"source_qualified_candidate_id": "wrong"})
        with pytest.raises(ValueError, match="candidate_id"):
            tampered.verify_or_raise(source_record=rec)

    def test_bounds_mismatch(self) -> None:
        """Bounds mismatch on evaluation order index should fail."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"evaluation_order_index": 999})
        with pytest.raises(ValueError, match="evaluation_index"):
            tampered.verify_or_raise(source_record=rec)

    def test_count_mismatch(self) -> None:
        """Count mismatch between snapshots and records."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=(
                rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
                if rec.candidate_evaluation_identity
                else None
            ),
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        opt = _make_opt()
        cat = _make_catalog(options=(opt,))

        from hexagent.optimization.context import (
            OptionRawCountRecord,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import materialize_all_candidates

        por = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=3,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=sri.sizing_request_identity_digest,
            raw_combination_count=3,
            effective_cap=100,
            per_option_records=(por,),
        )
        mat = materialize_all_candidates(
            catalogs=(cat,),
            sizing_gate=gate,
        )
        with pytest.raises(ValueError, match="count"):
            Phase3EvaluationInput(
                sizing_request_identity=sri,
                sizing_request_identity_digest=sri.sizing_request_identity_digest,
                materialization_result=mat,
                candidate_set_digest=mat.candidate_set.candidate_set_digest,
                gate_digest=gate.gate_digest,
                evaluation_records=(rec,),
                evaluation_record_count=2,
                identity_snapshots=(isnap,),
                complete_snapshots=(cs,),
                ordered_identity_snapshot_digests=(isnap.identity_snapshot_digest,),
                ordered_phase2_source_snapshot_digests=(cs.snapshot_digest,),
                ordered_phase2_source_record_descriptor_digests=(sdesc.descriptor_digest,),
                evaluation_input_digest="sha256:" + "0" * 64,
            )


# ============================================================================
# Section 3: BATCH INPUT CONSISTENCY
# ============================================================================


class TestBatchInputConsistency:
    """Per-field correctness of batch input data."""

    def test_fluid_identity_preserved(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.hot_fluid_name == "Water"

    def test_mass_flow_preserved(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.hot_mass_flow_kg_s == 1.0

    def test_temperature_values(self) -> None:
        evidence = _make_evidence()
        assert evidence.hot_outlet_temperature_k == 310.0

    def test_pressure_values(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.hot_inlet_pressure_pa == 2e5

    def test_flow_direction(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.flow_arrangement == "counterflow"

    def test_solver_config(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.solver_max_iterations == 100

    def test_candidate_identity(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("cand_xyz", 5, evidence=evidence)
        assert DIGEST_RE.match(rec.source_qualified_candidate_id)
        assert rec.evaluation_order_index == 5


# ============================================================================
# Section 4: INTEGRITY & PROVENANCE (fail-closed)
# ============================================================================


class TestIntegrityAndProvenance:
    """All integrity and provenance tamper attempts must fail closed."""

    def test_hash_tamper_detected(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"identity_snapshot_digest": DUMMY_DIGEST2})
        with pytest.raises(ValueError, match="identity_snapshot_digest mismatch"):
            Phase2SourceRecordIdentitySnapshot(**tampered.model_dump())

    def test_uuid_tamper_detected(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"source_qualified_candidate_id": "evil_cand"})
        with pytest.raises(ValueError):
            Phase2SourceRecordIdentitySnapshot(**tampered.model_dump())

    def test_wrong_source_record(self) -> None:
        evidence = _make_evidence()
        rec1, _ = _make_ver("c1", 0, evidence=evidence)
        rec2, _ = _make_ver("c2", 1, evidence=evidence)
        isnap = build_identity_snapshot(rec1)
        with pytest.raises(ValueError, match="evaluation_index"):
            isnap.verify_or_raise(source_record=rec2)

    def test_wrong_verified_evidence(self) -> None:
        evidence1 = _make_evidence(area_outer_m2=5.0)
        evidence2 = _make_evidence(area_outer_m2=3.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence1)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence1,
            source_failure_binding=None,
        )
        with pytest.raises(ValueError, match="verified_rating_evidence_digest"):
            sdesc.verify_or_raise(
                source_record=rec,
                identity_snapshot=isnap,
                verified_evidence=evidence2,
                source_failure_binding=None,
            )

    def test_wrong_evaluator_identity(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"provider_identity_matches": False})
        with pytest.raises(ValueError):
            Phase2SourceRecordIdentitySnapshot(**tampered.model_dump())

    def test_record_hash_tamper(self) -> None:
        desc = _make_message_descriptor()
        binding = build_phase3_message_descriptor_binding(desc)
        tampered = binding.model_copy(update={"descriptor_binding_digest": DUMMY_DIGEST3})
        with pytest.raises(ValueError, match="descriptor_binding_digest mismatch"):
            Phase3MessageDescriptorBinding(**tampered.model_dump())


# ============================================================================
# Section 5: VERIFIER
# ============================================================================


class TestVerifier:
    """All public/external verifier entry points."""

    def test_verify_message_descriptor_or_raise_valid(self) -> None:
        desc = _make_message_descriptor()
        verify_phase3_message_descriptor_or_raise(desc)

    def test_verify_message_descriptor_or_raise_empty_code(self) -> None:
        with pytest.raises(ValueError, match="original_code"):
            Phase3MessageDescriptor(
                owner_sort_key=("a", "b", "c", "d", (), "e"),
                original_code="",
                message_payload_digest=sha256_digest({"msg": "test"}),
            )

    def test_verify_message_descriptor_or_raise_invalid_digest(self) -> None:
        with pytest.raises(ValueError, match="invalid message_payload_digest"):
            Phase3MessageDescriptor(
                owner_sort_key=("a", "b", "c", "d", (), "e"),
                original_code="TEST001",
                message_payload_digest="not-a-digest",
            )

    def test_verify_message_descriptor_or_raise_bad_sort_key_length(self) -> None:
        desc = Phase3MessageDescriptor(
            owner_sort_key=("a", "TEST001", "c", "d", (), "b"),
            original_code="WRONG_CODE",
            message_payload_digest=sha256_digest({"msg": "test"}),
        )
        with pytest.raises(ValueError, match="owner_sort_key\\[1\\]"):
            verify_phase3_message_descriptor_or_raise(desc)

    def test_verify_message_descriptor_or_raise_code_mismatch(self) -> None:
        desc = Phase3MessageDescriptor(
            owner_sort_key=("a", "wrong_code", "c", "d", (), "e"),
            original_code="TEST001",
            message_payload_digest=sha256_digest({"msg": "test"}),
        )
        with pytest.raises(ValueError, match="owner_sort_key\\[1\\]"):
            verify_phase3_message_descriptor_or_raise(desc)

    def test_identity_snapshot_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        isnap.verify_or_raise(source_record=rec)

    def test_source_record_snapshot_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sid = rec.source_qualified_candidate_id
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id=sid,
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cs.verify_or_raise(
            source_record=rec,
            identity_snapshot=isnap,
            source_record_descriptor=sdesc,
            verified_evidence=evidence,
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=(),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )

    def test_source_binding_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sid = rec.source_qualified_candidate_id
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id=sid,
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        wbd = _make_message_descriptor_binding(_make_message_descriptor())
        bbd = _make_message_descriptor_binding(_make_message_descriptor("B99"))
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=sid,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        sb.verify_or_raise(
            source_record=rec,
            identity_snapshot=isnap,
            complete_snapshot=cs,
            source_record_descriptor=sdesc,
            verified_evidence=evidence,
            warning_bindings=(wbd,),
            blocker_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )

    def test_preparation_result_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sid = rec.source_qualified_candidate_id
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id=sid,
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        wbd = _make_message_descriptor_binding(_make_message_descriptor())
        bbd = _make_message_descriptor_binding(_make_message_descriptor("B99"))
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=sid,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        sri = _make_sizing_request_identity()
        candidate = _make_candidate(evaluation_order_index=0)
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        prep = build_phase3_candidate_preparation_result(
            status=Phase3PreparationStatus.READY,
            source_qualified_candidate_id=sid,
            evaluation_order_index=0,
            identity_snapshot=isnap,
            complete_snapshot=cs,
            source_binding=sb,
            classification_input=cin,
        )
        prep.verify_or_raise(
            source_record=rec,
            identity_snapshot=isnap,
            complete_snapshot=cs,
            source_binding=sb,
            classification_input=cin,
            evidence_failure_binding=None,
            source_failure_binding=None,
            phase3_failure_binding=None,
        )

    def test_index_artifact_matrix_integrity_invalid(self) -> None:
        rec = _make_integrity_invalid_record("c1", 0)
        verify_phase3_index_artifact_matrix(
            source_record=rec,
            identity_snapshot=None,
            complete_snapshot=None,
            source_record_descriptor=None,
            source_binding=None,
            classification_input=None,
            preparation_result=None,
            evidence_failure_binding=None,
            source_failure_binding=None,
            phase3_failure_binding=None,
        )
        # Adding any artifact should fail
        with pytest.raises(ValueError, match="INTEGRITY_INVALID.*FORBIDDEN"):
            verify_phase3_index_artifact_matrix(
                source_record=rec,
                identity_snapshot=None,
                complete_snapshot=build_phase2_source_record_snapshot(
                    source_qualified_candidate_id=rec.source_qualified_candidate_id,
                    evaluation_order_index=0,
                    candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
                    feasible=True,
                    feasibility_status=FeasibilityStatus.NOT_EVALUATED,
                    hash_verification_outcome=VerificationOutcome.PASSED,
                    provenance_verification_outcome=VerificationOutcome.PASSED,
                    provider_identity_matches=True,
                    rating_status="succeeded",
                    candidate_evaluation_identity_digest=None,
                    verified_rating_evidence_digest=None,
                    invalid_rating_evidence_digest=None,
                    claimed_rating_result_audit_digest=None,
                    evaluation_failure_digest=None,
                    phase2_source_record_descriptor_digest=_make_digest("sd"),
                    warning_descriptor_binding_digests=(),
                    blocker_descriptor_binding_digests=(),
                    source_evaluation_failure_binding_digest=None,
                    evidence_failure_binding_digest=None,
                ),
                source_record_descriptor=None,
                source_binding=None,
                classification_input=None,
                preparation_result=None,
                evidence_failure_binding=None,
                source_failure_binding=None,
                phase3_failure_binding=None,
            )

    def test_index_artifact_matrix_runtime_failed(self) -> None:
        rec = _make_runtime_failed_record("c1", 0)
        fb = _make_failure_binding()
        verify_phase3_index_artifact_matrix(
            source_record=rec,
            identity_snapshot=None,
            complete_snapshot=None,
            source_record_descriptor=None,
            source_binding=None,
            classification_input=None,
            preparation_result=None,
            evidence_failure_binding=None,
            source_failure_binding=fb,
            phase3_failure_binding=None,
        )
        with pytest.raises(ValueError, match="RUNTIME_FAILED.*REQUIRED"):
            verify_phase3_index_artifact_matrix(
                source_record=rec,
                identity_snapshot=None,
                complete_snapshot=None,
                source_record_descriptor=None,
                source_binding=None,
                classification_input=None,
                preparation_result=None,
                evidence_failure_binding=None,
                source_failure_binding=None,
                phase3_failure_binding=None,
            )

    def test_index_artifact_matrix_unevaluated(self) -> None:
        rec = _make_unevaluated_record("c1", 0)
        verify_phase3_index_artifact_matrix(
            source_record=rec,
            identity_snapshot=None,
            complete_snapshot=None,
            source_record_descriptor=None,
            source_binding=None,
            classification_input=None,
            preparation_result=None,
            evidence_failure_binding=None,
            source_failure_binding=None,
            phase3_failure_binding=None,
        )


# ============================================================================
# Section 6: RANKING & TOP-N
# ============================================================================


class TestRankingAndTopN:
    """Ranking and Top-N selection tests."""

    def test_same_rank_key_tie_break(self) -> None:
        evidence1 = _make_evidence(area_outer_m2=5.0)
        evidence2 = _make_evidence(area_outer_m2=5.0)
        # Build candidates with different effective lengths for tie-break
        cand1 = _make_candidate(evaluation_order_index=0, effective_length_m=2.0)
        cand2 = _make_candidate(evaluation_order_index=1, effective_length_m=1.0)
        rec1 = _make_verified_record(cand1, evidence=evidence1)
        rec2 = _make_verified_record(cand2, evidence=evidence2)
        sri = _make_sizing_request_identity()
        isnap1 = build_identity_snapshot(rec1)
        sdesc1 = build_phase2_source_record_descriptor(
            source_record=rec1,
            identity_snapshot=isnap1,
            verified_evidence=evidence1,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb1 = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec1.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc1.descriptor_digest,
            verified_rating_evidence_digest=evidence1.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap1.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        csnap1 = _make_csnap(rec1, sdesc1)
        cin1 = _build_cin(rec1, cand1, sri, isnap1, sdesc1, sb1)
        disp1 = classify_candidate(
            cin1,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap1,
            complete_snapshot=csnap1,
            source_record_descriptor=sdesc1,
        )
        isnap2 = build_identity_snapshot(rec2)
        sdesc2 = build_phase2_source_record_descriptor(
            source_record=rec2,
            identity_snapshot=isnap2,
            verified_evidence=evidence2,
            source_failure_binding=None,
        )
        sb2 = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec2.source_qualified_candidate_id,
            evaluation_order_index=1,
            phase2_source_record_descriptor_digest=sdesc2.descriptor_digest,
            verified_rating_evidence_digest=evidence2.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap2.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        csnap2 = _make_csnap(rec2, sdesc2)
        cin2 = _build_cin(rec2, cand2, sri, isnap2, sdesc2, sb2)
        disp2 = classify_candidate(
            cin2,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap2,
            complete_snapshot=csnap2,
            source_record_descriptor=sdesc2,
        )
        assert disp1.disposition == Phase3Disposition.FEASIBLE
        assert disp2.disposition == Phase3Disposition.FEASIBLE
        pv1, pf1, sv1, sf1 = _expected_ranked_values(
            disp1,
            cand1,
            OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        )
        pv2, pf2, sv2, sf2 = _expected_ranked_values(
            disp2,
            cand2,
            OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        )
        assert pv1 == pv2
        assert Decimal(sv2) < Decimal(sv1)

    def test_illegal_n_rejected(self) -> None:
        """Top-N values of 0 or negative are rejected by the authoritative entry point."""
        # top_n=0 rejected
        with pytest.raises(ValueError, match="top_n must be >= 1"):
            _make_sizing_request_identity(top_n=0)

        # top_n negative rejected
        with pytest.raises(ValueError, match="top_n must be >= 1"):
            _make_sizing_request_identity(top_n=-1)

        # top_n=-5 rejected
        with pytest.raises(ValueError, match="top_n must be >= 1"):
            _make_sizing_request_identity(top_n=-5)

    def test_boundary_n_value(self) -> None:
        core = OptimizationResultCoreValues(
            schema_version=1,
            sizing_request_identity_digest=DUMMY_DIGEST,
            passed_gate_digest=DUMMY_DIGEST2,
            candidate_set_digest=DUMMY_DIGEST3,
            evaluation_input_digest=DUMMY_DIGEST4,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            requested_top_n=1,
            total_candidate_count=1,
            feasible_candidate_count=0,
            infeasible_candidate_count=1,
            provider_mismatch_count=0,
            integrity_failed_count=0,
            provenance_failed_count=0,
            runtime_failed_count=0,
            unevaluated_count=0,
            phase2_verified_record_count=1,
            phase2_integrity_invalid_record_count=0,
            phase2_runtime_failed_record_count=0,
            phase2_unevaluated_record_count=0,
            runtime_failed_from_phase2_verified_count=0,
            runtime_failed_from_phase2_runtime_failed_count=0,
            ordered_disposition_record_digests=(DUMMY_DIGEST,),
            ordered_ranked_record_digests=(),
            ordered_top_n_record_digests=(),
            ordered_identity_snapshot_digests=(DUMMY_DIGEST,),
            ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST,),
            ordered_phase3_source_binding_digests=(DUMMY_DIGEST,),
            ordered_phase3_preparation_result_digests=(DUMMY_DIGEST,),
            termination_status=TerminationStatus.COMPLETE,
            ordered_warning_digests=(),
            ordered_blocker_digests=(),
        )
        assert core.requested_top_n == 1


# ============================================================================
# Section 7: FAILURE PROPAGATION
# ============================================================================


class TestFailurePropagation:
    """Failure propagation through the Phase 3 pipeline."""

    def test_provider_identity_mismatch(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, provider_identity_matches=False)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
        assert disp.diagnostic == FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH

    def test_missing_rating_status_phase3_runtime(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status=None)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        csnap = _make_csnap(rec, sdesc)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=None,
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_integrity_invalid_hash_failed(self) -> None:
        rec = _make_integrity_invalid_record(
            "c1",
            0,
            hash_outcome=VerificationOutcome.FAILED,
            prov_outcome=VerificationOutcome.NOT_RUN,
        )
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=None,
            warning_descriptors=(),
            blocker_descriptors=(),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.INTEGRITY_FAILED

    def test_integrity_invalid_provenance_failed(self) -> None:
        rec = _make_integrity_invalid_record(
            "c1",
            0,
            hash_outcome=VerificationOutcome.PASSED,
            prov_outcome=VerificationOutcome.FAILED,
        )
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=None,
            warning_descriptors=(),
            blocker_descriptors=(),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.PROVENANCE_FAILED

    def test_runtime_failed_mapped(self) -> None:
        rec = _make_runtime_failed_record("c1", 0)
        fb = _make_failure_binding()
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=fb,
            warning_descriptors=(),
            blocker_descriptors=(),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE2_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE2_EVALUATION

    def test_unevaluated_mapped(self) -> None:
        rec = _make_unevaluated_record("c1", 0)
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=None,
            warning_descriptors=(),
            blocker_descriptors=(),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.UNEVALUATED

    def test_phase3_runtime_from_builder(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _phase3_runtime(
            rec,
            sb,
            ErrorCode.INPUT_INCONSISTENT,
            "Test runtime",
            failure_stage=Phase3PreparationFailureStage.SOURCE_BINDING,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(),
            blocker_descriptors=(),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION

        failure = RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="validation failure",
            context=(("key", "val"),),
        )
        disp2 = _phase3_runtime_from_validation(
            rec,
            sb,
            failure,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            failure_stage=Phase3PreparationFailureStage.SOURCE_BINDING,
            warning_descriptors=(),
            blocker_descriptors=(),
        )
        assert disp2.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp2.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED


# ============================================================================
# Section 8: DECIMAL HELPERS
# ============================================================================


class TestDecimalHelpers:
    """Tests for canonical decimal helpers."""

    def test_canonical_decimal_normal(self) -> None:
        assert canonical_decimal(Decimal("5.0")) == Decimal("5")
        assert canonical_decimal(Decimal("0.0")) == Decimal("0")
        assert canonical_decimal(Decimal("1.000")) == Decimal("1")

    def test_canonical_decimal_string(self) -> None:
        assert canonical_decimal_string(Decimal("5.0")) == "5"
        assert canonical_decimal_string(Decimal("0")) == "0"
        assert canonical_decimal_string(Decimal("1.5")) == "1.5"

    def test_to_canonical_decimal_float(self) -> None:
        assert to_canonical_decimal(5.0) == Decimal("5")

    def test_to_canonical_decimal_int(self) -> None:
        assert to_canonical_decimal(5) == Decimal("5")

    def test_to_canonical_decimal_decimal(self) -> None:
        assert to_canonical_decimal(Decimal("5.0")) == Decimal("5")

    def test_to_canonical_decimal_bool_rejected(self) -> None:
        with pytest.raises(TypeError, match="bool"):
            to_canonical_decimal(True)

    def test_to_canonical_decimal_non_finite_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            to_canonical_decimal(float("inf"))

    def test_verify_canonical_decimal_string_valid(self) -> None:
        verify_canonical_decimal_string("5")
        verify_canonical_decimal_string("1.5")
        verify_canonical_decimal_string("0")

    def test_verify_canonical_decimal_string_invalid(self) -> None:
        with pytest.raises(ValueError, match="not canonical"):
            verify_canonical_decimal_string("5.0")

    def test_verify_canonical_decimal_string_non_finite(self) -> None:
        with pytest.raises(ValueError):
            verify_canonical_decimal_string("Infinity")


# ============================================================================
# Section 9: CORE TYPES
# ============================================================================


class TestCoreTypes:
    """Tests for core types: enums, descriptors, snapshots, bindings."""

    def test_phase3_disposition_values(self) -> None:
        assert Phase3Disposition.FEASIBLE == "feasible"
        assert Phase3Disposition.INFEASIBLE == "infeasible"
        assert Phase3Disposition.PROVIDER_IDENTITY_MISMATCH == "provider_identity_mismatch"

    def test_feasibility_diagnostic_key_values(self) -> None:
        assert FeasibilityDiagnosticKey.DUTY_SHORTFALL == "duty_shortfall"
        assert FeasibilityDiagnosticKey.RATING_BLOCKED == "rating_blocked"

    def test_termination_status_values(self) -> None:
        assert TerminationStatus.COMPLETE == "complete"
        assert TerminationStatus.PARTIAL == "partial"

    def test_failure_origin_values(self) -> None:
        assert FailureOrigin.NONE == "none"
        assert FailureOrigin.PHASE2_EVALUATION == "phase2_evaluation"
        assert FailureOrigin.PHASE3_CLASSIFICATION == "phase3_classification"

    def test_provenance_relation_values(self) -> None:
        assert Phase3ProvenanceRelation.REGULATES == "regulates"
        assert Phase3ProvenanceRelation.EVALUATED == "evaluated"
        assert Phase3ProvenanceRelation.RANKED == "ranked"

    def test_preparation_status_values(self) -> None:
        assert Phase3PreparationStatus.READY == "ready"
        assert Phase3PreparationStatus.FAILED == "failed"

    def test_message_descriptor_binding_roundtrip(self) -> None:
        desc = _make_message_descriptor()
        binding = build_phase3_message_descriptor_binding(desc)
        assert binding.owner_sort_key == desc.owner_sort_key
        assert binding.original_code == desc.original_code
        assert binding.message_payload_digest == desc.message_payload_digest
        assert DIGEST_RE.match(binding.descriptor_binding_digest)

    def test_message_descriptor_binding_tamper(self) -> None:
        desc = _make_message_descriptor()
        binding = build_phase3_message_descriptor_binding(desc)
        tampered = binding.model_copy(update={"descriptor_binding_digest": DUMMY_DIGEST4})
        with pytest.raises(ValueError, match="descriptor_binding_digest mismatch"):
            Phase3MessageDescriptorBinding(**tampered.model_dump())

    def test_failure_descriptor_binding_roundtrip(self) -> None:
        fb = _make_failure_binding()
        assert fb.original_code is not None
        assert DIGEST_RE.match(fb.descriptor_binding_digest)

    def test_identity_snapshot_build_and_verify(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        assert isnap.source_qualified_candidate_id == rec.source_qualified_candidate_id
        assert isnap.evaluation_order_index == 0
        assert DIGEST_RE.match(isnap.identity_snapshot_digest)
        isnap.verify_or_raise(source_record=rec)

    def test_source_record_descriptor_build(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        assert sdesc.source_qualified_candidate_id == rec.source_qualified_candidate_id
        assert DIGEST_RE.match(sdesc.descriptor_digest)

    def test_source_record_snapshot_build(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        assert cs.source_qualified_candidate_id == rec.source_qualified_candidate_id
        assert DIGEST_RE.match(cs.snapshot_digest)


# ============================================================================
# Section 10: BUILDER HELPERS
# ============================================================================


class TestBuilderHelpers:
    """Tests for builder helper functions."""

    def test_build_feasible(self) -> None:
        evidence = _make_evidence(area_outer_m2=5.0, heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_feasible(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        assert disp.disposition == Phase3Disposition.FEASIBLE
        assert disp.primary_engineering_value == "5"
        assert disp.secondary_engineering_value == "5000"

    def test_build_infeasible(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_infeasible(
            rec,
            sb,
            FeasibilityDiagnosticKey.RATING_BLOCKED,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.RATING_BLOCKED

    def test_build_provider_mismatch(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, provider_identity_matches=False)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_provider_mismatch(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH

    def test_ranked_candidate_record_valid(self) -> None:
        rr = build_ranked_candidate_record(
            rank=1,
            source_qualified_candidate_id="c1",
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            primary_objective_value="5",
            primary_objective_field="area_outer_m2",
            secondary_tie_break_value="1",
            secondary_tie_break_field="effective_length_m_canonical",
            candidate_evaluation_identity_digest=DUMMY_DIGEST,
            verified_rating_evidence_digest=DUMMY_DIGEST2,
            feasibility_digest=DUMMY_DIGEST3,
        )
        assert rr.rank == 1
        assert DIGEST_RE.match(rr.ranked_record_digest)

    def test_ranked_candidate_record_invalid_rank(self) -> None:
        with pytest.raises(ValueError, match="rank must be"):
            build_ranked_candidate_record(
                rank=0,
                source_qualified_candidate_id="c1",
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                primary_objective_value="5",
                primary_objective_field="area_outer_m2",
                secondary_tie_break_value="1",
                secondary_tie_break_field="effective_length_m_canonical",
                candidate_evaluation_identity_digest=DUMMY_DIGEST,
                verified_rating_evidence_digest=DUMMY_DIGEST2,
                feasibility_digest=DUMMY_DIGEST3,
            )

    def test_ranked_candidate_record_wrong_field(self) -> None:
        with pytest.raises(ValueError, match="MIN_OA"):
            build_ranked_candidate_record(
                rank=1,
                source_qualified_candidate_id="c1",
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                primary_objective_value="5",
                primary_objective_field="effective_length_m_canonical",
                secondary_tie_break_value="1",
                secondary_tie_break_field="area_outer_m2",
                candidate_evaluation_identity_digest=DUMMY_DIGEST,
                verified_rating_evidence_digest=DUMMY_DIGEST2,
                feasibility_digest=DUMMY_DIGEST3,
            )

    def test_ranked_candidate_record_non_canonical_value(self) -> None:
        with pytest.raises(ValueError, match="not canonical"):
            build_ranked_candidate_record(
                rank=1,
                source_qualified_candidate_id="c1",
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                primary_objective_value="5.0",
                primary_objective_field="area_outer_m2",
                secondary_tie_break_value="1",
                secondary_tie_break_field="effective_length_m_canonical",
                candidate_evaluation_identity_digest=DUMMY_DIGEST,
                verified_rating_evidence_digest=DUMMY_DIGEST2,
                feasibility_digest=DUMMY_DIGEST3,
            )

    def test_expected_ranked_values_area_objective(self) -> None:
        evidence = _make_evidence(area_outer_m2=5.0, heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        cand = _make_candidate(evaluation_order_index=0, effective_length_m=1.0)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_feasible(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        pv, pf, sv, sf = _expected_ranked_values(
            disp,
            cand,
            OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        )
        assert pf == "area_outer_m2"
        assert sf == "effective_length_m_canonical"
        assert pv == "5"
        assert sv == "1"

    def test_expected_ranked_values_length_objective(self) -> None:
        evidence = _make_evidence(area_outer_m2=5.0, heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        cand = _make_candidate(evaluation_order_index=0, effective_length_m=2.5)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_feasible(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        pv, pf, sv, sf = _expected_ranked_values(
            disp,
            cand,
            OptimizationObjective.MINIMUM_EFFECTIVE_LENGTH,
        )
        assert pf == "effective_length_m_canonical"
        assert sf == "area_outer_m2"


# ============================================================================
# Section 11: CANDIDATE DISPOSITION RECORD
# ============================================================================


class TestCandidateDispositionRecord:
    """Tests for CandidateDispositionRecord construction and validation."""

    def test_build_method(self) -> None:
        sri = _make_sizing_request_identity()
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        record = build_candidate_disposition_record(
            source_qualified_candidate_id="c1",
            evaluation_order_index=0,
            source_candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            source_hash_verification_outcome=VerificationOutcome.PASSED,
            source_provenance_verification_outcome=VerificationOutcome.PASSED,
            source_record_descriptor_digest=DUMMY_DIGEST,
            source_identity_record_descriptor_digest=sri.sizing_request_identity_digest,
            disposition=Phase3Disposition.FEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.NONE,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=DUMMY_DIGEST2,
            verified_rating_evidence_digest=DUMMY_DIGEST3,
            invalid_rating_evidence_digest=None,
            primary_engineering_value="5",
            secondary_engineering_value="5000",
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=FailureOrigin.NONE,
        )
        assert record.disposition == Phase3Disposition.FEASIBLE
        assert DIGEST_RE.match(record.feasibility_digest)

    def test_disposition_payload_roundtrip(self) -> None:
        sri = _make_sizing_request_identity()
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        record = build_candidate_disposition_record(
            source_qualified_candidate_id="c2",
            evaluation_order_index=0,
            source_candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            source_hash_verification_outcome=VerificationOutcome.PASSED,
            source_provenance_verification_outcome=VerificationOutcome.PASSED,
            source_record_descriptor_digest=DUMMY_DIGEST,
            source_identity_record_descriptor_digest=sri.sizing_request_identity_digest,
            disposition=Phase3Disposition.FEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.NONE,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=DUMMY_DIGEST2,
            verified_rating_evidence_digest=DUMMY_DIGEST3,
            invalid_rating_evidence_digest=None,
            primary_engineering_value="5",
            secondary_engineering_value="5000",
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=FailureOrigin.NONE,
        )
        payload = candidate_disposition_payload(record)
        assert payload["disposition"] == "feasible"
        assert payload["source_qualified_candidate_id"] == "c2"

    def test_failure_matrix_non_failure_dispositions(self) -> None:
        with pytest.raises(ValueError, match="failure_origin must be NONE"):
            verify_candidate_disposition_failure_matrix(
                disposition=Phase3Disposition.FEASIBLE,
                failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
                failure_stage=None,
                source_failure_binding_digest=None,
                source_failure_payload_digest=None,
                phase3_failure_binding_digest=None,
                phase3_failure_payload_digest=None,
                source_identity_record_descriptor_digest=DUMMY_DIGEST,
            )

    def test_failure_matrix_p2_runtime(self) -> None:
        with pytest.raises(ValueError, match="source_failure_binding_digest required"):
            verify_candidate_disposition_failure_matrix(
                disposition=Phase3Disposition.RUNTIME_FAILED,
                failure_origin=FailureOrigin.PHASE2_EVALUATION,
                failure_stage=None,
                source_failure_binding_digest=None,
                source_failure_payload_digest=None,
                phase3_failure_binding_digest=None,
                phase3_failure_payload_digest=None,
                source_identity_record_descriptor_digest=DUMMY_DIGEST,
            )

    def test_failure_matrix_p3_runtime(self) -> None:
        with pytest.raises(ValueError, match="phase3_failure_binding_digest required"):
            verify_candidate_disposition_failure_matrix(
                disposition=Phase3Disposition.RUNTIME_FAILED,
                failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
                failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
                source_failure_binding_digest=None,
                source_failure_payload_digest=None,
                phase3_failure_binding_digest=None,
                phase3_failure_payload_digest=None,
                source_identity_record_descriptor_digest=DUMMY_DIGEST,
            )


# ============================================================================
# Section 12: OPTIMIZATION RESULT CORE VALUES
# ============================================================================


class TestOptimizationResultCoreValues:
    """Tests for OptimizationResultCoreValues validation."""

    def test_populated_counts_sum(self) -> None:
        core = OptimizationResultCoreValues(
            schema_version=1,
            sizing_request_identity_digest=DUMMY_DIGEST,
            passed_gate_digest=DUMMY_DIGEST2,
            candidate_set_digest=DUMMY_DIGEST3,
            evaluation_input_digest=DUMMY_DIGEST4,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            requested_top_n=3,
            total_candidate_count=3,
            feasible_candidate_count=1,
            infeasible_candidate_count=1,
            provider_mismatch_count=0,
            integrity_failed_count=0,
            provenance_failed_count=0,
            runtime_failed_count=0,
            unevaluated_count=1,
            phase2_verified_record_count=2,
            phase2_integrity_invalid_record_count=0,
            phase2_runtime_failed_record_count=0,
            phase2_unevaluated_record_count=1,
            runtime_failed_from_phase2_verified_count=0,
            runtime_failed_from_phase2_runtime_failed_count=0,
            ordered_disposition_record_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
            ordered_ranked_record_digests=(DUMMY_DIGEST4,),
            ordered_top_n_record_digests=(DUMMY_DIGEST4,),
            ordered_identity_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
            ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
            ordered_phase3_source_binding_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
            ordered_phase3_preparation_result_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
            termination_status=TerminationStatus.COMPLETE,
            ordered_warning_digests=(),
            ordered_blocker_digests=(),
        )
        assert core.total_candidate_count == 3
        assert core.feasible_candidate_count == 1

    def test_counts_must_sum_correctly(self) -> None:
        with pytest.raises(ValueError, match="don't sum"):
            OptimizationResultCoreValues(
                schema_version=1,
                sizing_request_identity_digest=DUMMY_DIGEST,
                passed_gate_digest=DUMMY_DIGEST2,
                candidate_set_digest=DUMMY_DIGEST3,
                evaluation_input_digest=DUMMY_DIGEST4,
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                requested_top_n=3,
                total_candidate_count=3,
                feasible_candidate_count=1,
                infeasible_candidate_count=1,
                provider_mismatch_count=0,
                integrity_failed_count=0,
                provenance_failed_count=0,
                runtime_failed_count=0,
                unevaluated_count=0,
                phase2_verified_record_count=2,
                phase2_integrity_invalid_record_count=0,
                phase2_runtime_failed_record_count=0,
                phase2_unevaluated_record_count=1,
                runtime_failed_from_phase2_verified_count=0,
                runtime_failed_from_phase2_runtime_failed_count=0,
                ordered_disposition_record_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_ranked_record_digests=(DUMMY_DIGEST4,),
                ordered_top_n_record_digests=(DUMMY_DIGEST4,),
                ordered_identity_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_source_binding_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_preparation_result_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                termination_status=TerminationStatus.COMPLETE,
                ordered_warning_digests=(),
                ordered_blocker_digests=(),
            )

    def test_phase2_counts_must_sum(self) -> None:
        with pytest.raises(ValueError, match="Phase 2 counts don't sum"):
            OptimizationResultCoreValues(
                schema_version=1,
                sizing_request_identity_digest=DUMMY_DIGEST,
                passed_gate_digest=DUMMY_DIGEST2,
                candidate_set_digest=DUMMY_DIGEST3,
                evaluation_input_digest=DUMMY_DIGEST4,
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                requested_top_n=3,
                total_candidate_count=3,
                feasible_candidate_count=1,
                infeasible_candidate_count=1,
                provider_mismatch_count=0,
                integrity_failed_count=0,
                provenance_failed_count=0,
                runtime_failed_count=0,
                unevaluated_count=1,
                phase2_verified_record_count=1,
                phase2_integrity_invalid_record_count=0,
                phase2_runtime_failed_record_count=0,
                phase2_unevaluated_record_count=1,
                runtime_failed_from_phase2_verified_count=0,
                runtime_failed_from_phase2_runtime_failed_count=0,
                ordered_disposition_record_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_ranked_record_digests=(DUMMY_DIGEST4,),
                ordered_top_n_record_digests=(DUMMY_DIGEST4,),
                ordered_identity_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_source_binding_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_preparation_result_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                termination_status=TerminationStatus.COMPLETE,
                ordered_warning_digests=(),
                ordered_blocker_digests=(),
            )


# ============================================================================
# Section 13: EVIDENCE VALIDATORS
# ============================================================================

_SENTINEL = object()


class TestEvidenceValidators:
    """Comprehensive tests for validate_blocked_evidence and validate_failed_evidence
    exercised via classify_candidate."""

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_blocked_artifacts(
        rec: CandidateEvaluationRecord,
        candidate: ManufacturableCandidate,
        evidence: VerifiedRatingEvidenceSnapshot | None,
        *,
        sri: SizingRequestIdentity | None = None,
        warnings: tuple[Phase3MessageDescriptor, ...] = (),
        blockers: tuple[Phase3MessageDescriptor, ...] = (),
        warning_bindings: tuple[Phase3MessageDescriptorBinding, ...] = (),
        blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...] = (),
        tampered_src_id: str | None = None,
        tampered_idx: int | None = None,
        binding_evidence_digest: str | None = _SENTINEL,  # sentinel = compute from evidence
        evidence_failure_binding: Phase3RunFailureDescriptorBinding | None = None,
    ):
        """Build all classification artifacts for blocked evidence."""
        if sri is None:
            sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )

        src_id = (
            tampered_src_id if tampered_src_id is not None else rec.source_qualified_candidate_id
        )
        eval_idx = tampered_idx if tampered_idx is not None else rec.evaluation_order_index

        # Compute evidence digest for binding
        if binding_evidence_digest is _SENTINEL:
            ev_digest = (
                evidence.compute_explicit_evidence_digest() if evidence is not None else None
            )
        else:
            ev_digest = binding_evidence_digest

        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=src_id,
            evaluation_order_index=eval_idx,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=ev_digest,
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=tuple(
                b.descriptor_binding_digest for b in warning_bindings
            ),
            blocker_descriptor_binding_digests=tuple(
                b.descriptor_binding_digest for b in blocker_bindings
            ),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=(
                evidence_failure_binding.descriptor_binding_digest
                if evidence_failure_binding is not None
                else None
            ),
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        csnap = _make_csnap(rec, sdesc)
        return (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap,
            warnings,
            blockers,
            warning_bindings,
            blocker_bindings,
        )

    @staticmethod
    def _build_failed_artifacts(
        rec: CandidateEvaluationRecord,
        candidate: ManufacturableCandidate,
        evidence: VerifiedRatingEvidenceSnapshot | None,
        *,
        sri: SizingRequestIdentity | None = None,
        warnings: tuple[Phase3MessageDescriptor, ...] = (),
        blockers: tuple[Phase3MessageDescriptor, ...] = (),
        warning_bindings: tuple[Phase3MessageDescriptorBinding, ...] = (),
        blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...] = (),
        tampered_src_id: str | None = None,
        tampered_idx: int | None = None,
        binding_evidence_digest: str | None = _SENTINEL,
        evidence_failure_binding: Phase3RunFailureDescriptorBinding | None = None,
        binding_ef_digest: str | None = _SENTINEL,
    ):
        """Build all classification artifacts for failed evidence."""
        if sri is None:
            sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )

        src_id = (
            tampered_src_id if tampered_src_id is not None else rec.source_qualified_candidate_id
        )
        eval_idx = tampered_idx if tampered_idx is not None else rec.evaluation_order_index

        if binding_evidence_digest is _SENTINEL:
            ev_digest = (
                evidence.compute_explicit_evidence_digest() if evidence is not None else None
            )
        else:
            ev_digest = binding_evidence_digest

        if binding_ef_digest is _SENTINEL:
            ef_digest = (
                evidence_failure_binding.descriptor_binding_digest
                if evidence_failure_binding is not None
                else None
            )
        else:
            ef_digest = binding_ef_digest

        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id=src_id,
            evaluation_order_index=eval_idx,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=ev_digest,
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=tuple(
                b.descriptor_binding_digest for b in warning_bindings
            ),
            blocker_descriptor_binding_digests=tuple(
                b.descriptor_binding_digest for b in blocker_bindings
            ),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=ef_digest,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        csnap = _make_csnap(rec, sdesc)
        return (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap,
            warnings,
            blockers,
            warning_bindings,
            blocker_bindings,
        )

    @staticmethod
    def _make_msg_descriptors(
        evidence: VerifiedRatingEvidenceSnapshot,
    ) -> tuple[
        tuple[Phase3MessageDescriptor, ...],
        tuple[Phase3MessageDescriptor, ...],
        tuple[Phase3MessageDescriptorBinding, ...],
        tuple[Phase3MessageDescriptorBinding, ...],
    ]:
        """Build warning/blocker descriptors and bindings matching evidence content."""
        from hexagent.optimization.evaluation import _build_message_descriptor as bmd

        wds: list[Phase3MessageDescriptor] = []
        bds: list[Phase3MessageDescriptor] = []
        for w in evidence.warnings:
            desc = bmd(w)
            wds.append(
                Phase3MessageDescriptor(
                    owner_sort_key=desc.owner_sort_key,
                    original_code=desc.original_code,
                    message_payload_digest=desc.message_payload_digest,
                )
            )
        for b in evidence.blockers:
            desc = bmd(b)
            bds.append(
                Phase3MessageDescriptor(
                    owner_sort_key=desc.owner_sort_key,
                    original_code=desc.original_code,
                    message_payload_digest=desc.message_payload_digest,
                )
            )
        wbds = tuple(build_phase3_message_descriptor_binding(d) for d in wds)
        bbds = tuple(build_phase3_message_descriptor_binding(d) for d in bds)
        return tuple(wds), tuple(bds), wbds, bbds

    @staticmethod
    def _failed_evidence(
        *,
        failure_msg: str = "test failure",
        warnings: tuple = (),
        blockers: tuple = (),
    ) -> VerifiedRatingEvidenceSnapshot:
        """Build failed evidence with a RunFailure payload and no thermal results."""
        from hexagent.domain.messages import (
            EngineeringMessage,
            EngineeringMessageSeverity,
        )

        failure = RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=failure_msg,
            context=(("key", "val"),),
        )
        rri = RatingRequestIdentity(
            hot_fluid_name="Water",
            hot_fluid_backend="CP",
            hot_fluid_components=(),
            cold_fluid_name="Water",
            cold_fluid_backend="CP",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=1.0,
            cold_mass_flow_kg_s=0.8,
            hot_inlet_pressure_pa=2e5,
            cold_inlet_pressure_pa=1.5e5,
            hot_inlet_temperature_k=350.0,
            cold_inlet_temperature_k=290.0,
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
        exec_ctx = _make_exec_ctx()
        rri_digest = sha256_digest(rating_request_identity_payload(rri))
        ec_digest = sha256_digest(execution_context_snapshot_payload(exec_ctx))
        _warnings = (
            warnings
            if warnings
            else (
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.WARNING,
                    message="test warning",
                    source_module="test",
                ),
            )
        )
        _blockers = (
            blockers
            if blockers
            else (
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message="test blocker",
                    source_module="test",
                ),
            )
        )
        return VerifiedRatingEvidenceSnapshot(
            rating_status=RatingStatus.FAILED,
            heat_duty_w=None,
            hot_outlet_temperature_k=None,
            cold_outlet_temperature_k=None,
            area_inner_m2=4.0,
            area_outer_m2=5.0,
            tube_flow_area_m2=0.002,
            annulus_flow_area_m2=0.005,
            provider_identity=_make_provider(),
            rating_result_hash="sha256:" + "e" * 64,
            rating_provenance_digest="sha256:" + "f" * 64,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            rating_request_identity=rri,
            rating_request_identity_digest=rri_digest,
            rating_execution_context=exec_ctx,
            rating_execution_context_digest=ec_digest,
            failure=failure,
            warnings=_warnings,
            blockers=_blockers,
        )

    # ══════════════════════════════════════════════════════════════════════
    # POSITIVE TESTS
    # ══════════════════════════════════════════════════════════════════════

    def test_valid_blocked_evidence_passes_validation(self) -> None:
        """Valid blocked evidence passes validation and classifies as INFEASIBLE/RATING_BLOCKED."""
        evidence = _make_blocked_evidence()  # no warnings, no blockers
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.RATING_BLOCKED

    def test_valid_failed_evidence_passes_validation(self) -> None:
        """Valid failed evidence passes validation and classifies as INFEASIBLE/RATING_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.RATING_FAILED

    # ══════════════════════════════════════════════════════════════════════
    # NEGATIVE TESTS — BLOCKED EVIDENCE
    # ══════════════════════════════════════════════════════════════════════

    def test_blocked_missing_evidence_none__direct(self) -> None:
        """Blocked path: validate_blocked_evidence returns RunFailure for None evidence."""
        rec, candidate = _make_ver("c1", 0, rating_status="blocked")
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=None,
            source_failure_binding=None,
        )
        eb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=None,
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        result = validate_blocked_evidence(
            rec,
            None,
            eb,
            warning_descriptors=(),
            blocker_descriptors=(),
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=(),
            evidence_failure_binding=None,
        )
        assert isinstance(result, RunFailure)
        assert "missing" in result.message.lower()

    def test_blocked_rating_status_mismatch(self) -> None:
        """Blocked path with evidence rating_status not 'blocked' → RUNTIME_FAILED."""
        evidence = _make_evidence(rating_status=RatingStatus.SUCCEEDED)
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            binding_evidence_digest=None,  # required for CLASSIFICATION stage
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_candidate_id_mismatch(self) -> None:
        """Blocked path with mismatched candidate ID in binding → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            tampered_src_id="sha256:" + "9" * 64,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_evaluation_index_mismatch(self) -> None:
        """Blocked path with mismatched evaluation index in binding → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            tampered_idx=999,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_rating_request_identity_mismatch(self) -> None:
        """Blocked path with mismatched RRI digest → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        # model_construct with actual nested objects to avoid dict issues
        tampered_evidence = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest="sha256:" + "1" * 64,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered_evidence})
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered_evidence,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_provider_identity_mismatch(self) -> None:
        """Blocked path with rec.provider_identity_matches=False → PROVIDER_IDENTITY_MISMATCH."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver(
            "c1", 0, evidence=evidence, rating_status="blocked", provider_identity_matches=False
        )
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
        assert disp.diagnostic == FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH

    def test_blocked_hash_outcome_not_passed(self) -> None:
        """Blocked path with hash_verification_outcome not PASSED → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=VerificationOutcome.FAILED,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_provenance_outcome_not_passed(self) -> None:
        """Blocked path with provenance_verification_outcome not PASSED → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=VerificationOutcome.FAILED,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_missing_warning_descriptor(self) -> None:
        """Blocked path: evidence has warnings but no descriptors → RUNTIME_FAILED."""
        from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity

        evidence = _make_blocked_evidence()
        tampered = evidence.model_copy(
            update={
                "warnings": (
                    EngineeringMessage(
                        code=ErrorCode.INPUT_INCONSISTENT,
                        severity=EngineeringMessageSeverity.WARNING,
                        message="unexpected warning",
                        source_module="test",
                    ),
                )
            }
        )
        rec, candidate = _make_ver("c1", 0, evidence=tampered, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=(),
            blocker_descriptors=bds,
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_extra_warning_descriptor(self) -> None:
        """Blocked path: more descriptors than evidence warnings → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        wd = _make_message_descriptor()
        wbd = _make_message_descriptor_binding(wd)
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            warnings=(wd,),
            warning_bindings=(wbd,),
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=bds,
            warning_descriptor_bindings=(wbd,),
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_duplicate_warning_descriptor(self) -> None:
        """Blocked path: descriptor digest mismatch vs evidence warning → RUNTIME_FAILED."""
        from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity

        evidence = _make_blocked_evidence()
        tampered = evidence.model_copy(
            update={
                "warnings": (
                    EngineeringMessage(
                        code=ErrorCode.INPUT_INCONSISTENT,
                        severity=EngineeringMessageSeverity.WARNING,
                        message="specific warning",
                        source_module="test",
                    ),
                )
            }
        )
        rec, candidate = _make_ver("c1", 0, evidence=tampered, rating_status="blocked")
        wd_wrong = _make_message_descriptor()
        wbd_wrong = _make_message_descriptor_binding(wd_wrong)
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            tampered,
            warnings=(wd_wrong,),
            warning_bindings=(wbd_wrong,),
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd_wrong,),
            blocker_descriptors=bds,
            warning_descriptor_bindings=(wbd_wrong,),
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_missing_blocker_descriptor(self) -> None:
        """Blocked path: evidence has blockers but no descriptors → RUNTIME_FAILED."""
        from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity

        evidence = _make_blocked_evidence()
        tampered = evidence.model_copy(
            update={
                "blockers": (
                    EngineeringMessage(
                        code=ErrorCode.INPUT_INCONSISTENT,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message="unexpected blocker",
                        source_module="test",
                    ),
                )
            }
        )
        rec, candidate = _make_ver("c1", 0, evidence=tampered, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=(),
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=(),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_extra_blocker_descriptor(self) -> None:
        """Blocked path: more blocker descriptors than evidence blockers → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        bd = _make_message_descriptor("B01")
        bbd = _make_message_descriptor_binding(bd)
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            blockers=(bd,),
            blocker_bindings=(bbd,),
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_duplicate_blocker_descriptor(self) -> None:
        """Blocked path: blocker descriptor digest mismatch vs evidence blocker → RUNTIME_FAILED."""
        from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity

        evidence = _make_blocked_evidence()
        tampered = evidence.model_copy(
            update={
                "blockers": (
                    EngineeringMessage(
                        code=ErrorCode.INPUT_INCONSISTENT,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message="specific blocker",
                        source_module="test",
                    ),
                )
            }
        )
        rec, candidate = _make_ver("c1", 0, evidence=tampered, rating_status="blocked")
        bd_wrong = _make_message_descriptor("B01")
        bbd_wrong = _make_message_descriptor_binding(bd_wrong)
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            tampered,
            blockers=(bd_wrong,),
            blocker_bindings=(bbd_wrong,),
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=(bd_wrong,),
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=(bbd_wrong,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_warning_binding_tamper(self) -> None:
        """Blocked path: warning binding digest mismatch vs SourceRecordBinding → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        wd = _make_message_descriptor()
        wbd = _make_message_descriptor_binding(wd)
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            warnings=(wd,),
            warning_bindings=(wbd,),
            binding_evidence_digest=None,
        )
        other_wbd = _make_message_descriptor_binding(_make_message_descriptor("ALTERED"))
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=bds,
            warning_descriptor_bindings=(other_wbd,),
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_blocker_binding_tamper(self) -> None:
        """Blocked path: blocker binding digest mismatch vs SourceRecordBinding → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        bd = _make_message_descriptor("B01")
        bbd = _make_message_descriptor_binding(bd)
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            blockers=(bd,),
            blocker_bindings=(bbd,),
            binding_evidence_digest=None,
        )
        other_bbd = _make_message_descriptor_binding(_make_message_descriptor("ALTERED_B"))
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=(other_bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_evidence_digest_tamper(self) -> None:
        """Blocked path: evidence digest mismatch vs binding → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            binding_evidence_digest=None,  # None != actual → mismatch
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_failure_not_none(self) -> None:
        """Blocked path: evidence has failure (should be None for blocked) → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        failure = RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="bad",
            context=(("k", "v"),),
        )
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_successful_thermal_values_mixed_in(self) -> None:
        """Blocked path: evidence has thermal results (heat_duty_w set) → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            tampered_rec,
            candidate,
            tampered,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_evidence_failure_binding_not_none(self) -> None:
        """Blocked path: evidence_failure_binding not None (must be None) → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            binding_evidence_digest=None,
        )
        efb = _make_failure_binding()
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_artifact_from_another_candidate(self) -> None:
        """Blocked path: binding candidate ID differs from record ID → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        other_id = "sha256:" + "a" * 64
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            tampered_src_id=other_id,
            binding_evidence_digest=None,
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    # ══════════════════════════════════════════════════════════════════════
    # NEGATIVE TESTS — FAILED EVIDENCE
    # ══════════════════════════════════════════════════════════════════════

    def test_failed_missing_evidence_none__direct(self) -> None:
        """Failed path: validate_failed_evidence returns RunFailure for None evidence."""
        rec, candidate = _make_ver("c1", 0, rating_status="failed")
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=None,
            source_failure_binding=None,
        )
        eb = build_phase3_source_record_binding(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=None,
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        result = validate_failed_evidence(
            rec,
            None,
            eb,
            warning_descriptors=(),
            blocker_descriptors=(),
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=(),
            evidence_failure_binding=None,
        )
        assert isinstance(result, RunFailure)
        assert "missing" in result.message.lower()

    def test_failed_rating_status_mismatch(self) -> None:
        """Failed path with evidence not having FAILED status → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds = self._build_failed_artifacts(
            rec,
            candidate,
            evidence,
            evidence_failure_binding=_make_failure_binding(),
            binding_evidence_digest=None,
        )
        efb = _make_failure_binding()
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_candidate_id_mismatch(self) -> None:
        """Failed path: binding candidate ID mismatch → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                tampered_src_id="sha256:" + "9" * 64,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_evaluation_index_mismatch(self) -> None:
        """Failed path: binding evaluation index mismatch → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                tampered_idx=999,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_hash_outcome_not_passed(self) -> None:
        """Failed path: hash_verification_outcome not PASSED → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=VerificationOutcome.FAILED,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        failure_desc = _build_run_failure_descriptor(tampered.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        wds, bds, wbds, bbds = self._make_msg_descriptors(tampered)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                tampered_rec,
                candidate,
                tampered,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_provenance_outcome_not_passed(self) -> None:
        """Failed path: provenance_verification_outcome not PASSED → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=VerificationOutcome.FAILED,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        failure_desc = _build_run_failure_descriptor(tampered.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        wds, bds, wbds, bbds = self._make_msg_descriptors(tampered)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                tampered_rec,
                candidate,
                tampered,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_failure_payload_digest_tamper(self) -> None:
        """Failed path: failure payload digest mismatch → RUNTIME_FAILED."""
        evidence = self._failed_evidence(failure_msg="original message")
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        other_failure = RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="tampered message",
            context=(("k", "v"),),
        )
        other_desc = _build_run_failure_descriptor(other_failure)
        efb = build_phase3_run_failure_descriptor_binding(other_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_failure_descriptor_binding_tamper(self) -> None:
        """Failed path: evidence_failure_binding descriptor_binding_digest mismatch."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        from hexagent.optimization.phase3_core import Phase3RunFailureDescriptorBinding as RFDB

        tampered_efb = RFDB.model_construct(
            _fields_set=set(RFDB.model_fields.keys()),
            **{**efb.model_dump(), "descriptor_binding_digest": "sha256:" + "b" * 64},
        )
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=tampered_efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=tampered_efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_wrong_evidence_failure_binding(self) -> None:
        """Failed path: evidence_failure_binding mismatch vs SourceRecordBinding."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        other_failure = RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="other",
            context=(("k", "v"),),
        )
        other_desc = _build_run_failure_descriptor(other_failure)
        other_efb = build_phase3_run_failure_descriptor_binding(other_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=other_efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_successful_thermal_values_mixed_in(self) -> None:
        """Failed path: evidence has heat_duty_w (should not for failed) → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        from hexagent.optimization.evaluation import (
            VerifiedRatingEvidenceSnapshot as VRES,
        )

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        failure_desc = _build_run_failure_descriptor(tampered.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        wds, bds, wbds, bbds = self._make_msg_descriptors(tampered)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                tampered_rec,
                candidate,
                tampered,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_warning_descriptor_mismatch(self) -> None:
        """Failed path: warning descriptor count mismatch → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=(),
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_blocker_descriptor_mismatch(self) -> None:
        """Failed path: blocker descriptor count mismatch → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=(),
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=(),
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_evidence_digest_tamper(self) -> None:
        """Failed path: evidence digest mismatch vs binding → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,  # None != actual
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_warning_binding_tamper(self) -> None:
        """Failed path: warning binding digest mismatch vs SourceRecordBinding."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        other_wbd = _make_message_descriptor_binding(_make_message_descriptor("ALTERED"))
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=(other_wbd,),
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_blocker_binding_tamper(self) -> None:
        """Failed path: blocker binding digest mismatch vs SourceRecordBinding."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        other_bbd = _make_message_descriptor_binding(_make_message_descriptor("ALTERED_B"))
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=(other_bbd,),
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_artifact_from_another_candidate(self) -> None:
        """Failed path: binding candidate ID differs from record ID → RUNTIME_FAILED."""
        evidence = self._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        other_id = "sha256:" + "a" * 64
        wds, bds, wbds, bbds = self._make_msg_descriptors(evidence)
        cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out = (
            self._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                tampered_src_id=other_id,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED


# ============================================================================
# Round 3 Adversarial Tests — new identity, thermal-state, and source binding
# ============================================================================


class TestRound3Adversarial:
    """Adversarial tests for new Round 3 validations in validate_blocked_evidence,
    validate_failed_evidence, and classify_candidate with eb.verify_or_raise()."""

    # ── Shared helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_snapshots(
        rec: CandidateEvaluationRecord,
        evidence: VerifiedRatingEvidenceSnapshot | None,
        sb: Phase3SourceRecordBinding,
    ) -> tuple[
        Phase2SourceRecordIdentitySnapshot,
        Phase2SourceRecordDescriptor,
        Phase2SourceRecordSnapshot,
    ]:
        """Build identity snapshot, descriptor, and complete snapshot for eb.verify_or_raise()."""
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None
            else None
        )
        ev_digest = evidence.compute_explicit_evidence_digest() if evidence is not None else None
        csnap = build_phase2_source_record_snapshot(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            candidate_evaluation_state=rec.candidate_evaluation_state,
            feasible=rec.feasible,
            feasibility_status=rec.feasibility_status,
            hash_verification_outcome=rec.hash_verification_outcome,
            provenance_verification_outcome=rec.provenance_verification_outcome,
            provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=ev_digest,
            invalid_rating_evidence_digest=(
                rec.invalid_rating_evidence.invalid_evidence_digest
                if rec.invalid_rating_evidence is not None
                else None
            ),
            claimed_rating_result_audit_digest=(
                rec.claimed_rating_result_audit.audit_digest
                if rec.claimed_rating_result_audit is not None
                else None
            ),
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=sb.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=sb.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=sb.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=sb.evidence_failure_binding_digest,
        )
        return isnap, sdesc, csnap

    # ══════════════════════════════════════════════════════════════════════
    # FAILED REQUEST IDENTITY TESTS
    # ══════════════════════════════════════════════════════════════════════

    def test_failed_evidence_request_object_tampered(self) -> None:
        """Failed evidence: rating_request_identity object tampered so recomputed
        digest differs from evidence.rating_request_identity_digest → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        tampered_rri = RatingRequestIdentity(
            hot_fluid_name=evidence.rating_request_identity.hot_fluid_name,
            hot_fluid_backend=evidence.rating_request_identity.hot_fluid_backend,
            hot_fluid_components=evidence.rating_request_identity.hot_fluid_components,
            cold_fluid_name=evidence.rating_request_identity.cold_fluid_name,
            cold_fluid_backend=evidence.rating_request_identity.cold_fluid_backend,
            cold_fluid_components=evidence.rating_request_identity.cold_fluid_components,
            hot_mass_flow_kg_s=evidence.rating_request_identity.hot_mass_flow_kg_s,
            cold_mass_flow_kg_s=evidence.rating_request_identity.cold_mass_flow_kg_s,
            hot_inlet_pressure_pa=evidence.rating_request_identity.hot_inlet_pressure_pa,
            cold_inlet_pressure_pa=evidence.rating_request_identity.cold_inlet_pressure_pa,
            hot_inlet_temperature_k=evidence.rating_request_identity.hot_inlet_temperature_k,
            cold_inlet_temperature_k=evidence.rating_request_identity.cold_inlet_temperature_k,
            flow_arrangement=evidence.rating_request_identity.flow_arrangement,
            geometry={**evidence.rating_request_identity.geometry, "effective_length_m": 99.9},
            solver_absolute_residual_w=evidence.rating_request_identity.solver_absolute_residual_w,
            solver_relative_residual_fraction=evidence.rating_request_identity.solver_relative_residual_fraction,
            solver_bracket_temperature_tolerance_k=evidence.rating_request_identity.solver_bracket_temperature_tolerance_k,
            solver_max_iterations=evidence.rating_request_identity.solver_max_iterations,
        )
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered_evidence = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=tampered_rri,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_rec = rec.model_copy(
            update={
                "verified_rating_evidence": tampered_evidence,
                "candidate_evaluation_identity": None,
            }
        )
        rec2, _ = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        cei = _make_cei(rec2.source_qualified_candidate_id, tampered_evidence)
        tampered_rec = tampered_rec.model_copy(update={"candidate_evaluation_identity": cei})
        failure_desc = _build_run_failure_descriptor(tampered_evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(tampered_evidence)
        _r = TestEvidenceValidators._build_failed_artifacts(
            tampered_rec,
            candidate,
            tampered_evidence,
            warnings=wds,
            blockers=bds,
            warning_bindings=wbds,
            blocker_bindings=bbds,
            evidence_failure_binding=efb,
            binding_evidence_digest=None,
        )
        cin = _r[0]
        isnap = _r[2]
        sdesc = _r[3]
        csnap = _r[5]
        wds_out = _r[6]
        bds_out = _r[7]
        wbds_out = _r[8]
        bbds_out = _r[9]
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_evidence_request_digest_tampered(self) -> None:
        """Failed evidence: rating_request_identity_digest tampered → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered_evidence = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest="sha256:" + "1" * 64,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_rec = rec.model_copy(
            update={
                "verified_rating_evidence": tampered_evidence,
                "candidate_evaluation_identity": None,
            }
        )
        rec2, _ = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        cei = _make_cei(rec2.source_qualified_candidate_id, tampered_evidence)
        tampered_rec = tampered_rec.model_copy(update={"candidate_evaluation_identity": cei})
        failure_desc = _build_run_failure_descriptor(tampered_evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(tampered_evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                tampered_evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_cei_request_digest_tampered(self) -> None:
        """Failed evidence: CEI.rating_request_identity_digest tampered → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_cei = CandidateEvaluationIdentity(
            sizing_request_identity_digest=rec.candidate_evaluation_identity.sizing_request_identity_digest,
            source_qualified_candidate_id=rec.candidate_evaluation_identity.source_qualified_candidate_id,
            rating_request_identity_digest="sha256:" + "2" * 64,
            rating_result_hash=rec.candidate_evaluation_identity.rating_result_hash,
            rating_provenance_digest=rec.candidate_evaluation_identity.rating_provenance_digest,
            rating_execution_context_digest=rec.candidate_evaluation_identity.rating_execution_context_digest,
            provider_identity_digest=rec.candidate_evaluation_identity.provider_identity_digest,
            tube_in_hot=rec.candidate_evaluation_identity.tube_in_hot,
        )
        tampered_rec = rec.model_copy(update={"candidate_evaluation_identity": tampered_cei})
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_evidence_belongs_to_another_candidate(self) -> None:
        """Failed evidence: binding candidate ID differs from record → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        other_id = "sha256:" + "f" * 64
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                tampered_src_id=other_id,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_record_rating_status_not_failed(self) -> None:
        """Failed evidence: rec.rating_status != 'failed' → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="succeeded")
        tampered_rec = rec.model_copy(
            update={"rating_status": "succeeded", "verified_rating_evidence": evidence}
        )
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    # ══════════════════════════════════════════════════════════════════════
    # FAILED PROVIDER IDENTITY TESTS
    # ══════════════════════════════════════════════════════════════════════

    def test_failed_evidence_provider_object_tampered(self) -> None:
        """Failed evidence: provider_identity object tampered → recomputed digest
        differs from CEI → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        tampered_provider = ProviderIdentitySnapshot(
            name="tampered_provider",
            version="9.9",
            git_revision="deadbeef",
            reference_state_policy="altered",
        )
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered_evidence = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=tampered_provider,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        cei = _make_cei(rec.source_qualified_candidate_id, evidence)
        tampered_rec = rec.model_copy(
            update={
                "verified_rating_evidence": tampered_evidence,
                "candidate_evaluation_identity": cei,
            }
        )
        failure_desc = _build_run_failure_descriptor(tampered_evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(tampered_evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                tampered_evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_provider_digest_differs_from_cei(self) -> None:
        """Failed evidence: CEI.provider_identity_digest differs from recomputed
        → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_cei = CandidateEvaluationIdentity(
            sizing_request_identity_digest=rec.candidate_evaluation_identity.sizing_request_identity_digest,
            source_qualified_candidate_id=rec.candidate_evaluation_identity.source_qualified_candidate_id,
            rating_request_identity_digest=rec.candidate_evaluation_identity.rating_request_identity_digest,
            rating_result_hash=rec.candidate_evaluation_identity.rating_result_hash,
            rating_provenance_digest=rec.candidate_evaluation_identity.rating_provenance_digest,
            rating_execution_context_digest=rec.candidate_evaluation_identity.rating_execution_context_digest,
            provider_identity_digest="sha256:" + "9" * 64,
            tube_in_hot=rec.candidate_evaluation_identity.tube_in_hot,
        )
        tampered_rec = rec.model_copy(update={"candidate_evaluation_identity": tampered_cei})
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_provider_matches_true_but_digest_mismatch(self) -> None:
        """Failed evidence: provider_identity_matches=True but recomputed
        provider digest differs from CEI → RUNTIME_FAILED (fail closed)."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_cei = CandidateEvaluationIdentity(
            sizing_request_identity_digest=rec.candidate_evaluation_identity.sizing_request_identity_digest,
            source_qualified_candidate_id=rec.candidate_evaluation_identity.source_qualified_candidate_id,
            rating_request_identity_digest=rec.candidate_evaluation_identity.rating_request_identity_digest,
            rating_result_hash=rec.candidate_evaluation_identity.rating_result_hash,
            rating_provenance_digest=rec.candidate_evaluation_identity.rating_provenance_digest,
            rating_execution_context_digest=rec.candidate_evaluation_identity.rating_execution_context_digest,
            provider_identity_digest="sha256:" + "a" * 64,
            tube_in_hot=rec.candidate_evaluation_identity.tube_in_hot,
        )
        tampered_rec = rec.model_copy(
            update={
                "candidate_evaluation_identity": tampered_cei,
                "provider_identity_matches": True,
            }
        )
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_provider_identity_matches_false(self) -> None:
        """Failed evidence: provider_identity_matches=False → PROVIDER_IDENTITY_MISMATCH."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver(
            "c1", 0, evidence=evidence, rating_status="failed", provider_identity_matches=False
        )
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
        assert disp.diagnostic == FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH

    def test_failed_provider_artifact_from_another_candidate(self) -> None:
        """Failed evidence: evidence belongs to another candidate → RUNTIME_FAILED."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        other_id = "sha256:" + "b" * 64
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                rec,
                candidate,
                evidence,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                tampered_src_id=other_id,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    # ══════════════════════════════════════════════════════════════════════
    # BLOCKED PROVIDER IDENTITY TESTS
    # ══════════════════════════════════════════════════════════════════════

    def test_blocked_provider_object_tampered(self) -> None:
        """Blocked evidence: provider_identity object tampered → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        tampered_provider = ProviderIdentitySnapshot(
            name="tampered_provider",
            version="9.9",
            git_revision="deadbeef",
            reference_state_policy="altered",
        )
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered_evidence = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=tampered_provider,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        cei = _make_cei(rec.source_qualified_candidate_id, evidence)
        tampered_rec = rec.model_copy(
            update={
                "verified_rating_evidence": tampered_evidence,
                "candidate_evaluation_identity": cei,
            }
        )
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                tampered_evidence,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_provider_digest_mismatch(self) -> None:
        """Blocked evidence: CEI.provider_identity_digest differs from recomputed
        → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_cei = CandidateEvaluationIdentity(
            sizing_request_identity_digest=rec.candidate_evaluation_identity.sizing_request_identity_digest,
            source_qualified_candidate_id=rec.candidate_evaluation_identity.source_qualified_candidate_id,
            rating_request_identity_digest=rec.candidate_evaluation_identity.rating_request_identity_digest,
            rating_result_hash=rec.candidate_evaluation_identity.rating_result_hash,
            rating_provenance_digest=rec.candidate_evaluation_identity.rating_provenance_digest,
            rating_execution_context_digest=rec.candidate_evaluation_identity.rating_execution_context_digest,
            provider_identity_digest="sha256:" + "9" * 64,
            tube_in_hot=rec.candidate_evaluation_identity.tube_in_hot,
        )
        tampered_rec = rec.model_copy(update={"candidate_evaluation_identity": tampered_cei})
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                evidence,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_provider_matches_true_digest_mismatch(self) -> None:
        """Blocked evidence: provider_identity_matches=True but digest mismatch → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_cei = CandidateEvaluationIdentity(
            sizing_request_identity_digest=rec.candidate_evaluation_identity.sizing_request_identity_digest,
            source_qualified_candidate_id=rec.candidate_evaluation_identity.source_qualified_candidate_id,
            rating_request_identity_digest=rec.candidate_evaluation_identity.rating_request_identity_digest,
            rating_result_hash=rec.candidate_evaluation_identity.rating_result_hash,
            rating_provenance_digest=rec.candidate_evaluation_identity.rating_provenance_digest,
            rating_execution_context_digest=rec.candidate_evaluation_identity.rating_execution_context_digest,
            provider_identity_digest="sha256:" + "a" * 64,
            tube_in_hot=rec.candidate_evaluation_identity.tube_in_hot,
        )
        tampered_rec = rec.model_copy(
            update={
                "candidate_evaluation_identity": tampered_cei,
                "provider_identity_matches": True,
            }
        )
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                evidence,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_provider_identity_matches_false(self) -> None:
        """Blocked evidence: provider_identity_matches=False → PROVIDER_IDENTITY_MISMATCH."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver(
            "c1", 0, evidence=evidence, rating_status="blocked", provider_identity_matches=False
        )
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                rec,
                candidate,
                evidence,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
        assert disp.diagnostic == FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH

    def test_blocked_provider_artifact_from_another_candidate(self) -> None:
        """Blocked evidence: evidence belongs to another candidate → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        other_id = "sha256:" + "b" * 64
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                rec,
                candidate,
                evidence,
                tampered_src_id=other_id,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    # ══════════════════════════════════════════════════════════════════════
    # THERMAL-STATE MATRIX TESTS
    # ══════════════════════════════════════════════════════════════════════

    def test_blocked_energy_residual_w_non_none(self) -> None:
        """Blocked evidence: energy_residual_w non-None → RUNTIME_FAILED (thermal matrix)."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=42.0,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                tampered,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_failed_energy_residual_w_non_none(self) -> None:
        """Failed evidence: energy_residual_w non-None → RUNTIME_FAILED (thermal matrix)."""
        evidence = TestEvidenceValidators._failed_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=42.0,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        failure_desc = _build_run_failure_descriptor(tampered.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(tampered)
        (cin, _, isnap, sdesc, _, csnap, wds_out, bds_out, wbds_out, bbds_out) = (
            TestEvidenceValidators._build_failed_artifacts(
                tampered_rec,
                candidate,
                tampered,
                warnings=wds,
                blockers=bds,
                warning_bindings=wbds,
                blocker_bindings=bbds,
                evidence_failure_binding=efb,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_ua_lmtd_residual_w_non_none(self) -> None:
        """Blocked evidence: ua_lmtd_residual_w non-None → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=100.0,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                tampered,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_heat_duty_w_non_none(self) -> None:
        """Blocked evidence: heat_duty_w non-None → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                tampered,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_successful_outlet_temps(self) -> None:
        """Blocked evidence: hot_outlet_temperature_k non-None → RUNTIME_FAILED."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=310.0,
            cold_outlet_temperature_k=None,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=evidence.UA_w_k,
            LMTD_k=evidence.LMTD_k,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                tampered,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_blocked_ua_lmtd_in_blocked(self) -> None:
        """Blocked evidence: UA_w_k non-None → RUNTIME_FAILED (UA/LMTD in blocked)."""
        evidence = _make_blocked_evidence()
        from hexagent.optimization.evaluation import VerifiedRatingEvidenceSnapshot as VRES

        tampered = VRES.model_construct(
            _fields_set=set(VRES.model_fields.keys()),
            rating_status=evidence.rating_status,
            heat_duty_w=evidence.heat_duty_w,
            hot_outlet_temperature_k=evidence.hot_outlet_temperature_k,
            cold_outlet_temperature_k=evidence.cold_outlet_temperature_k,
            area_inner_m2=evidence.area_inner_m2,
            area_outer_m2=evidence.area_outer_m2,
            UA_w_k=150.0,
            LMTD_k=50.0,
            energy_residual_w=evidence.energy_residual_w,
            ua_lmtd_residual_w=evidence.ua_lmtd_residual_w,
            tube_inlet_density_kg_m3=evidence.tube_inlet_density_kg_m3,
            annulus_inlet_density_kg_m3=evidence.annulus_inlet_density_kg_m3,
            tube_flow_area_m2=evidence.tube_flow_area_m2,
            annulus_flow_area_m2=evidence.annulus_flow_area_m2,
            warnings=evidence.warnings,
            blockers=evidence.blockers,
            failure=evidence.failure,
            provider_identity=evidence.provider_identity,
            tube_correlation=evidence.tube_correlation,
            annulus_correlation=evidence.annulus_correlation,
            rating_result_hash=evidence.rating_result_hash,
            rating_provenance_digest=evidence.rating_provenance_digest,
            hash_verification_outcome=evidence.hash_verification_outcome,
            provenance_verification_outcome=evidence.provenance_verification_outcome,
            rating_request_identity=evidence.rating_request_identity,
            rating_request_identity_digest=evidence.rating_request_identity_digest,
            rating_execution_context=evidence.rating_execution_context,
            rating_execution_context_digest=evidence.rating_execution_context_digest,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        tampered_rec = rec.model_copy(update={"verified_rating_evidence": tampered})
        (cin, _, isnap, sdesc, _, csnap, wds, bds, wbds, bbds) = (
            TestEvidenceValidators._build_blocked_artifacts(
                tampered_rec,
                candidate,
                tampered,
                binding_evidence_digest=None,
            )
        )
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    # ══════════════════════════════════════════════════════════════════════
    # SOURCE BINDING PRECONDITION TESTS (eb.verify_or_raise)
    # ══════════════════════════════════════════════════════════════════════

    def test_tampered_source_binding_digest_rejected(self) -> None:
        """Tampered SourceRecordBinding.binding_digest → rejected by eb.verify_or_raise()."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap,
            wds,
            bds,
            wbds,
            bbds,
        ) = TestEvidenceValidators._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
        )
        from hexagent.optimization.phase3_evaluation import Phase3SourceRecordBinding as PSB

        tampered_sb = PSB.model_construct(
            _fields_set=set(PSB.model_fields.keys()),
            source_qualified_candidate_id=sb.source_qualified_candidate_id,
            evaluation_order_index=sb.evaluation_order_index,
            phase2_source_record_descriptor_digest=sb.phase2_source_record_descriptor_digest,
            verified_rating_evidence_digest=sb.verified_rating_evidence_digest,
            phase2_identity_snapshot_digest=sb.phase2_identity_snapshot_digest,
            warning_descriptor_binding_digests=sb.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=sb.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=sb.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=sb.evidence_failure_binding_digest,
            binding_digest="sha256:" + "b" * 64,
        )
        tampered_cin = cin.model_copy(update={"evidence_binding": tampered_sb})
        _, _, csnap = self._build_snapshots(rec, evidence, sb)
        disp = classify_candidate(
            tampered_cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION

    def test_tampered_identity_snapshot_digest_rejected(self) -> None:
        """Tampered identity_snapshot_digest in binding → rejected by eb.verify_or_raise()."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap,
            wds,
            bds,
            wbds,
            bbds,
        ) = TestEvidenceValidators._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
        )
        from hexagent.optimization.phase3_evaluation import Phase3SourceRecordBinding as PSB

        tampered_sb = PSB.model_construct(
            _fields_set=set(PSB.model_fields.keys()),
            source_qualified_candidate_id=sb.source_qualified_candidate_id,
            evaluation_order_index=sb.evaluation_order_index,
            phase2_source_record_descriptor_digest=sb.phase2_source_record_descriptor_digest,
            verified_rating_evidence_digest=sb.verified_rating_evidence_digest,
            phase2_identity_snapshot_digest="sha256:" + "c" * 64,
            warning_descriptor_binding_digests=sb.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=sb.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=sb.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=sb.evidence_failure_binding_digest,
            binding_digest=sb.binding_digest,
        )
        tampered_cin = cin.model_copy(update={"evidence_binding": tampered_sb})
        _, _, csnap = self._build_snapshots(rec, evidence, sb)
        disp = classify_candidate(
            tampered_cin,
            warning_descriptors=wds,
            blocker_descriptors=bds,
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION

    def test_tampered_warning_binding_rejected(self) -> None:
        """Tampered warning binding digest → rejected by eb.verify_or_raise()."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        wd = _make_message_descriptor()
        wbd = _make_message_descriptor_binding(wd)
        (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap,
            wds,
            bds,
            wbds,
            bbds,
        ) = TestEvidenceValidators._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            warnings=(wd,),
            warning_bindings=(wbd,),
        )
        _, _, csnap = self._build_snapshots(rec, evidence, sb)
        other_wbd = _make_message_descriptor_binding(_make_message_descriptor("ALTERED"))
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=bds,
            warning_descriptor_bindings=(other_wbd,),
            blocker_descriptor_bindings=bbds,
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION

    def test_tampered_blocker_binding_rejected(self) -> None:
        """Tampered blocker binding digest → rejected by eb.verify_or_raise()."""
        evidence = _make_blocked_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        bd = _make_message_descriptor("B01")
        bbd = _make_message_descriptor_binding(bd)
        (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap,
            wds,
            bds,
            wbds,
            bbds,
        ) = TestEvidenceValidators._build_blocked_artifacts(
            rec,
            candidate,
            evidence,
            blockers=(bd,),
            blocker_bindings=(bbd,),
        )
        _, _, csnap = self._build_snapshots(rec, evidence, sb)
        other_bbd = _make_message_descriptor_binding(_make_message_descriptor("ALTERED_B"))
        disp = classify_candidate(
            cin,
            warning_descriptors=wds,
            blocker_descriptors=(bd,),
            warning_descriptor_bindings=wbds,
            blocker_descriptor_bindings=(other_bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION

    def test_tampered_evidence_failure_binding_rejected(self) -> None:
        """Tampered evidence_failure_binding digest → rejected by eb.verify_or_raise()."""
        evidence = TestEvidenceValidators._failed_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="failed")
        failure_desc = _build_run_failure_descriptor(evidence.failure)
        efb = build_phase3_run_failure_descriptor_binding(failure_desc)
        wds, bds, wbds, bbds = TestEvidenceValidators._make_msg_descriptors(evidence)
        (
            cin,
            sri,
            isnap,
            sdesc,
            sb,
            csnap_from_artifacts,
            wds_out,
            bds_out,
            wbds_out,
            bbds_out,
        ) = TestEvidenceValidators._build_failed_artifacts(
            rec,
            candidate,
            evidence,
            warnings=wds,
            blockers=bds,
            warning_bindings=wbds,
            blocker_bindings=bbds,
            evidence_failure_binding=efb,
        )
        from hexagent.optimization.phase3_core import Phase3RunFailureDescriptorBinding as RFDB

        tampered_efb = RFDB.model_construct(
            _fields_set=set(RFDB.model_fields.keys()),
            **{**efb.model_dump(), "descriptor_binding_digest": "sha256:" + "d" * 64},
        )
        # Use csnap from artifacts (correctly unpacked), not independently built
        csnap = csnap_from_artifacts
        disp = classify_candidate(
            cin,
            warning_descriptors=wds_out,
            blocker_descriptors=bds_out,
            warning_descriptor_bindings=wbds_out,
            blocker_descriptor_bindings=bbds_out,
            source_failure_binding=None,
            evidence_failure_binding=tampered_efb,
            identity_snapshot=isnap,
            complete_snapshot=csnap,
            source_record_descriptor=sdesc,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION
