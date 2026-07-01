"""TASK-010 application services.

Wraps domain services with registry resolution, canonical request context,
and projection from public API DTOs to domain models.

RatingApplicationService — full rating pipeline (split prepare/execute).
SizingApplicationService — full sizing pipeline (split prepare/execute).
SizingService — re-exported from sizing_service.py (Phase 1 projection).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from hexagent.api.canonical_request import (
    build_rating_canonical_request_context,
    compute_api_request_digest,
)
from hexagent.api.models import (
    RatingApiRequest,
    ResolvedProviderAuthority,
    SizingApiRequest,
    SolverParamsSpec,
)
from hexagent.api.projection import (
    project_geometry_spec_to_geometry,
    project_solver_spec_to_solver,
    project_validation_to_design_case,
)
from hexagent.api.registry import CatalogRegistry, ProviderRegistry

# Re-export the sizing service (Phase 1 projection) — no duplication.
from hexagent.api.sizing_service import SizingService, SizingServiceResult  # noqa: E402
from hexagent.core.canonical import sha256_digest
from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.domain.messages import EngineeringMessage
from hexagent.domain.models import DesignCase
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.service import DoublePipeRatingService
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier, PropertyProvider

if TYPE_CHECKING:
    from hexagent.optimization.phase3_builder import OptimizationResult, RankedCandidateRecord
    from hexagent.optimization.phase3_core import Phase3RunFailureDescriptorBinding
    from hexagent.optimization.phase3_evaluation import (
        CandidateDispositionRecord,
        Phase3EvaluationInput,
    )
    from hexagent.optimization.phase3_verifier import Phase3AuthoritativeArtifacts

# ---------------------------------------------------------------------------
# RatingServiceResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RatingServiceResult:
    """Immutable result from the rating application service.

    Carries the domain ``RatingResult`` plus all API-layer artifacts
    needed for envelope construction, audit trails, and provenance.
    """

    result: RatingResult
    resolved_provider: ResolvedProviderAuthority
    request_digest: str
    canonical_request_snapshot: dict[str, Any]
    geometry_artifact: dict[str, Any]
    solver_artifact: dict[str, Any]
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    provenance: ProvenanceGraph


# ---------------------------------------------------------------------------
# PreparedRatingRun — frozen result of prepare()
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreparedRatingRun:
    """Frozen result of ``RatingApplicationService.prepare()``.

    Carries everything needed to execute the rating kernel *and* to
    build artifact bundles/envelopes — without having executed the
    kernel yet.  This enables the route to claim the idempotency
    namespace *before* running any expensive computation.
    """

    api_request: RatingApiRequest
    design_case: DesignCase
    geometry: DoublePipeGeometry
    solver_settings: SolverParams
    resolved_provider: ResolvedProviderAuthority
    execution_provider: PropertyProvider
    canonical_request_snapshot: dict[str, object]
    request_digest: str
    tube_in_hot: bool
    flow_arrangement: FlowArrangement
    tube_boundary_condition: ThermalBoundaryCondition
    annulus_boundary_condition: ThermalBoundaryCondition
    minimum_terminal_delta_t: float


# ---------------------------------------------------------------------------
# Provider identity verification
# ---------------------------------------------------------------------------


def _verify_provider_identity_match(
    authority: ResolvedProviderAuthority,
    provider: PropertyProvider,
) -> None:
    """Verify PropertyProvider identity matches resolved authority.

    Checks ALL 6 identity fields per contract C1:
    name, version, git_revision, reference_state_policy,
    configuration_fingerprint, cache_policy_version.

    A mismatch in any field means the resolved provider authority does
    not match the actual execution provider — pre-claim failure.
    """
    if authority.identity.name != provider.name:
        raise ValueError(
            f"Provider name mismatch: registry has {authority.identity.name!r}, "
            f"actual provider has {provider.name!r}"
        )
    if authority.identity.version != provider.version:
        raise ValueError(
            f"Provider version mismatch: registry has {authority.identity.version!r}, "
            f"actual provider has {provider.version!r}"
        )
    if authority.identity.git_revision != getattr(provider, "git_revision", ""):
        raise ValueError(
            f"Provider git_revision mismatch: registry has "
            f"{authority.identity.git_revision!r}, actual provider has "
            f"{getattr(provider, 'git_revision', '')!r}"
        )
    actual_policy = str(provider.reference_state_policy.value)
    if authority.identity.reference_state_policy != actual_policy:
        raise ValueError(
            f"Provider reference_state_policy mismatch: registry has "
            f"{authority.identity.reference_state_policy!r}, actual provider has "
            f"{actual_policy!r}"
        )
    # C1: configuration_fingerprint
    actual_fp = getattr(provider, "_construction_fingerprint", "")
    if authority.identity.configuration_fingerprint != actual_fp:
        raise ValueError(
            f"Provider configuration_fingerprint mismatch: registry has "
            f"{authority.identity.configuration_fingerprint!r}, actual provider has "
            f"{actual_fp!r}"
        )
    # C1: cache_policy_version
    actual_cpv = getattr(provider, "cache_policy_version", "")
    if authority.identity.cache_policy_version != actual_cpv:
        raise ValueError(
            f"Provider cache_policy_version mismatch: registry has "
            f"{authority.identity.cache_policy_version!r}, actual provider has "
            f"{actual_cpv!r}"
        )


def _verify_result_provenance(
    result: RatingResult,
    prepared: PreparedRatingRun,
) -> None:
    """Verify result provider_identity matches prepared provider authority.

    Checks ALL 6 identity fields per contract C1:
    name, version, git_revision, reference_state_policy,
    configuration_fingerprint, cache_policy_version.
    """
    expected = prepared.resolved_provider.identity
    actual = result.provider_identity
    all_fields = (
        "name",
        "version",
        "git_revision",
        "reference_state_policy",
        "configuration_fingerprint",
        "cache_policy_version",
    )
    for field_name in all_fields:
        expected_val = getattr(expected, field_name)
        actual_val = getattr(actual, field_name)
        if expected_val != actual_val:
            raise ValueError(
                f"Result provider_identity.{field_name} mismatch: "
                f"expected {expected_val!r}, got {actual_val!r}"
            )


# ---------------------------------------------------------------------------
# RatingApplicationService
# ---------------------------------------------------------------------------


class RatingApplicationService:
    """Application service for double-pipe rating requests.

    Responsibilities:
    1. Accept validated ``RatingApiRequest``
    2. Resolve provider authority via ``ProviderRegistry``
    3. Verify provider identity matches actual PropertyProvider (P0-2)
    4. Build canonical request context and compute request digest
    5. Project API DTOs to domain models
    6. Return frozen ``PreparedRatingRun`` (NO kernel execution)
    7. Execute the rating kernel on demand via ``execute()``
    8. Verify result provenance matches prepared provider

    The service accepts both a ``ProviderRegistry`` (for authority resolution)
    and a ``PropertyProvider`` (the actual CoolProp instance used by the
    rating kernel).  These are separate concerns: the registry produces
    ``ResolvedProviderAuthority`` for audit/envelope, while the property
    provider supplies fluid properties to the engineering kernel.
    """

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry,
        property_provider: PropertyProvider,
    ) -> None:
        self._provider_registry = provider_registry
        self._property_provider = property_provider

    def prepare(self, request: RatingApiRequest) -> PreparedRatingRun:
        """Prepare a rating run WITHOUT executing the kernel.

        Steps:
        1. Resolve provider via registry
        2. Verify provider identity (P0-2)
        3. Project to domain (design case, geometry, solver)
        4. Build canonical request context
        5. Compute request_digest
        6. Return frozen PreparedRatingRun
        """
        # 1. Resolve provider authority
        resolved = self._provider_registry.resolve(request.provider_ref)

        # 2. Verify provider identity matches actual PropertyProvider
        _verify_provider_identity_match(resolved, self._property_provider)

        # 3. Project to domain
        design_case = project_validation_to_design_case(request.case)
        geometry = project_geometry_spec_to_geometry(request.geometry)
        effective_solver = project_solver_spec_to_solver(
            request.solver_params if request.solver_params is not None else SolverParamsSpec()
        )

        # 4. Parse flow arrangement and boundary conditions
        flow_arrangement = FlowArrangement(request.flow_arrangement)
        tube_bc = ThermalBoundaryCondition(request.tube_boundary_condition)
        annulus_bc = ThermalBoundaryCondition(request.annulus_boundary_condition)

        # 5. Build canonical request context and compute digest
        context = build_rating_canonical_request_context(
            request=request,
            resolved_provider=resolved,
        )
        request_digest = compute_api_request_digest(context)

        # 6. Return frozen PreparedRatingRun
        return PreparedRatingRun(
            api_request=request,
            design_case=design_case,
            geometry=geometry,
            solver_settings=effective_solver,
            resolved_provider=resolved,
            execution_provider=self._property_provider,
            canonical_request_snapshot=context,
            request_digest=request_digest,
            tube_in_hot=request.tube_in_hot,
            flow_arrangement=flow_arrangement,
            tube_boundary_condition=tube_bc,
            annulus_boundary_condition=annulus_bc,
            minimum_terminal_delta_t=request.case.minimum_terminal_delta_t.si_value,
        )

    def execute(self, prepared: PreparedRatingRun) -> RatingServiceResult:
        """Execute the rating kernel using a PreparedRatingRun.

        Steps:
        1. Create DoublePipeRatingService with prepared.execution_provider
        2. Call rate
        3. Verify result provenance matches prepared provider
        4. Return RatingServiceResult
        """
        # 1-2. Execute rating using the REAL service with REAL provider
        rating_svc = DoublePipeRatingService(provider=prepared.execution_provider)
        result = rating_svc.rate(
            prepared.design_case,
            prepared.geometry,
            tube_in_hot=prepared.tube_in_hot,
            flow_arrangement=prepared.flow_arrangement,
            solver_params=prepared.solver_settings,
            tube_boundary_condition=prepared.tube_boundary_condition,
            annulus_boundary_condition=prepared.annulus_boundary_condition,
            minimum_terminal_delta_t=prepared.minimum_terminal_delta_t,
        )

        # 3. Verify result provenance matches prepared provider
        _verify_result_provenance(result, prepared)

        # 4. Build artifacts from prepared + result
        geometry_artifact = {
            "inner_tube_inner_diameter_m": prepared.geometry.inner_tube_inner_diameter_m,
            "inner_tube_outer_diameter_m": prepared.geometry.inner_tube_outer_diameter_m,
            "outer_pipe_inner_diameter_m": prepared.geometry.outer_pipe_inner_diameter_m,
            "effective_length_m": prepared.geometry.effective_length_m,
            "wall_thermal_conductivity_w_m_k": prepared.geometry.wall_thermal_conductivity_w_m_k,
            "inner_surface_roughness_m": prepared.geometry.inner_surface_roughness_m,
            "annulus_surface_roughness_m": prepared.geometry.annulus_surface_roughness_m,
        }
        solver_artifact = {
            "absolute_residual_w": prepared.solver_settings.absolute_residual_w,
            "relative_residual_fraction": prepared.solver_settings.relative_residual_fraction,
            "bracket_temperature_tolerance_k": (
                prepared.solver_settings.bracket_temperature_tolerance_k
            ),
            "max_iterations": prepared.solver_settings.max_iterations,
        }

        return RatingServiceResult(
            result=result,
            resolved_provider=prepared.resolved_provider,
            request_digest=prepared.request_digest,
            canonical_request_snapshot=prepared.canonical_request_snapshot,
            geometry_artifact=geometry_artifact,
            solver_artifact=solver_artifact,
            warnings=result.warnings,
            blockers=result.blockers,
            provenance=result.provenance_graph,
        )


# ---------------------------------------------------------------------------
# PreparedSizingRun — frozen result of SizingApplicationService.prepare()
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreparedSizingRun:
    """Frozen result of ``SizingApplicationService.prepare()``.

    Carries all Phase 1 projection artifacts plus the property provider
    needed to execute the sizing kernel.  This enables the route to claim
    the idempotency namespace *before* running any expensive computation.
    """

    service_result: SizingServiceResult
    execution_provider: PropertyProvider


@dataclass(frozen=True, slots=True)
class SizingExecutionResult:
    """Result of the sizing optimization pipeline (A1).

    Bundles the ``OptimizationResult``, provenance graph, warnings,
    blockers, and all Phase 3 artifacts needed to construct typed
    ``SizingRunArtifacts``.
    """

    optimization_result: OptimizationResult
    provenance: ProvenanceGraph
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    # A1: Phase 3 artifacts for typed SizingRunArtifacts
    evaluation_input: Phase3EvaluationInput
    phase3_authoritative_artifacts: Phase3AuthoritativeArtifacts
    dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]


# ---------------------------------------------------------------------------
# SizingApplicationService
# ---------------------------------------------------------------------------


class SizingApplicationService:
    """Application service for double-pipe sizing requests.

    Responsibilities:
    1. Accept validated ``SizingApiRequest``
    2. Resolve provider and catalog authorities via registries
    3. Project to domain models via Phase 1 projection (prepare)
    4. Execute the full sizing optimization pipeline (execute)
    5. Return structured result with OptimizationResult + provenance

    The service accepts a ``ProviderRegistry``, ``CatalogRegistry``,
    and ``PropertyProvider`` (the actual CoolProp instance).
    """

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry,
        catalog_registry: CatalogRegistry,
        property_provider: PropertyProvider,
    ) -> None:
        self._provider_registry = provider_registry
        self._catalog_registry = catalog_registry
        self._property_provider = property_provider
        # Inner SizingService for Phase 1 projection
        self._sizing_service = SizingService(
            provider_registry=provider_registry,
            catalog_registry=catalog_registry,
        )

    def prepare(self, request: SizingApiRequest) -> PreparedSizingRun:
        """Prepare a sizing run WITHOUT executing the optimization kernel.

        Steps:
        1. Delegate to SizingService.process() for full Phase 1 projection
        2. Return frozen PreparedSizingRun
        """
        service_result = self._sizing_service.process(request)
        return PreparedSizingRun(
            service_result=service_result,
            execution_provider=self._property_provider,
        )

    def execute(self, prepared: PreparedSizingRun) -> SizingExecutionResult:
        """Execute the full sizing optimization pipeline.

        Steps:
        1. Build FluidIdentifiers from design case
        2. Compute raw combination count and per-option records
        3. Check cap and create PassedSizingGate
        4. Materialize all candidates
        5. Evaluate all candidates via TASK-008 adapter
        6. Build Phase 3 artifacts for each candidate
        7. Build OptimizationResult
        8. Return SizingExecutionResult
        """
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.optimization.context import (
            create_passed_sizing_gate,
        )
        from hexagent.optimization.evaluation import (
            CandidateEvaluationState,
            _build_message_descriptor,
            _build_run_failure_descriptor,
        )
        from hexagent.optimization.identities import materialize_all_candidates
        from hexagent.optimization.length import (
            check_cap,
            compute_raw_combination_count,
        )
        from hexagent.optimization.phase3_builder import (  # type: ignore[attr-defined]
            FEASIBLE,
            Phase3CandidateClassificationInput,
            build_optimization_result,
            classify_candidate,
            map_non_verified,
        )
        from hexagent.optimization.phase3_core import (
            Phase3MessageDescriptor,
            build_identity_snapshot,
            build_phase2_source_record_descriptor,
            build_phase2_source_record_snapshot,
            build_phase3_message_descriptor_binding,
            build_phase3_run_failure_descriptor_binding,
        )
        from hexagent.optimization.phase3_evaluation import (  # type: ignore[attr-defined]
            Phase3PreparationStatus,
            build_phase3_candidate_preparation_result,
            build_phase3_source_record_binding,
        )

        sr = prepared.service_result
        sizing_request = sr.sizing_request
        sizing_request_identity = sr.sizing_request_identity
        design_case = sr.design_case

        # 1. Build FluidIdentifiers from design case
        hot_fluid_spec = design_case.hot_stream.fluid
        cold_fluid_spec = design_case.cold_stream.fluid
        hot_fluid = FluidIdentifier(
            name=hot_fluid_spec.name,
            equation_of_state_backend=hot_fluid_spec.backend,
            components=tuple(sorted(hot_fluid_spec.composition.items(), key=lambda p: p[0]))
            if hot_fluid_spec.composition
            else (),
        )
        cold_fluid = FluidIdentifier(
            name=cold_fluid_spec.name,
            equation_of_state_backend=cold_fluid_spec.backend,
            components=tuple(sorted(cold_fluid_spec.composition.items(), key=lambda p: p[0]))
            if cold_fluid_spec.composition
            else (),
        )

        # 2. Compute raw combination count and per-option records
        raw_count, per_option_records = compute_raw_combination_count(
            sizing_request.catalogs,
            minimum_effective_length_m=sizing_request.minimum_effective_length_m,
            maximum_effective_length_m=sizing_request.maximum_effective_length_m,
        )

        # 3. Check cap and create PassedSizingGate
        effective_cap = check_cap(
            raw_count,
            request_cap=sizing_request.request_raw_combination_cap,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=sizing_request_identity.sizing_request_identity_digest,
            raw_combination_count=raw_count,
            effective_cap=effective_cap,
            per_option_records=per_option_records,
        )

        # 4. Materialize all candidates
        mat = materialize_all_candidates(
            catalogs=sr.resolved_catalogs,
            sizing_gate=gate,
            minimum_effective_length_m=sizing_request.minimum_effective_length_m,
            maximum_effective_length_m=sizing_request.maximum_effective_length_m,
        )

        # 5. Evaluate all candidates via TASK-008 adapter
        eval_records = evaluate_all_candidates(
            mat,
            hot_fluid=hot_fluid,
            cold_fluid=cold_fluid,
            hot_mass_flow_kg_s=sizing_request_identity.hot_mass_flow_kg_s,
            cold_mass_flow_kg_s=sizing_request_identity.cold_mass_flow_kg_s,
            hot_inlet_temperature_k=sizing_request_identity.hot_inlet_temperature_k,
            cold_inlet_temperature_k=sizing_request_identity.cold_inlet_temperature_k,
            hot_inlet_pressure_pa=sizing_request_identity.hot_inlet_pressure_pa,
            cold_inlet_pressure_pa=sizing_request_identity.cold_inlet_pressure_pa,
            tube_in_hot=sizing_request_identity.tube_in_hot,
            flow_arrangement=sizing_request_identity.flow_arrangement,
            provider=prepared.execution_provider,
            solver_params=sr.effective_solver_params,
            minimum_terminal_delta_t=sizing_request_identity.minimum_terminal_delta_t,
            tube_boundary_condition=sizing_request_identity.tube_boundary_condition,
            annulus_boundary_condition=sizing_request_identity.annulus_boundary_condition,
            sizing_request_identity=sizing_request_identity,
        )

        N = len(eval_records)

        # 6. Build Phase 3 artifacts for each candidate
        identity_snapshots = []
        complete_snapshots: list[Any] = []
        descriptors: list[Any] = []
        source_bindings: list[Any] = []
        classification_inputs: list[Any] = []
        preparation_results: list[Any] = []
        dispositions: list[Any] = []
        warning_descriptor_tuples: list[tuple[Any, ...]] = []
        blocker_descriptor_tuples: list[tuple[Any, ...]] = []
        warning_binding_tuples: list[tuple[Any, ...]] = []
        blocker_binding_tuples: list[tuple[Any, ...]] = []
        evidence_failure_bindings: list[Any] = []
        source_failure_bindings: list[Any] = []
        phase3_failure_bindings: list[Any] = []

        candidates_tuple = mat.candidates

        for i in range(N):
            rec = eval_records[i]
            cand = candidates_tuple[i]

            # Build identity snapshot for all candidates
            isnap = build_identity_snapshot(rec)
            identity_snapshots.append(isnap)

            if rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED:
                evidence = rec.verified_rating_evidence
                assert evidence is not None, "VERIFIED must have evidence"

                # Build warning/blocker descriptors from evidence
                warn_descs: list[Any] = []
                warn_binds: list[Any] = []
                for w_msg in evidence.warnings:
                    cd = _build_message_descriptor(w_msg)
                    assert cd.message_payload_digest is not None
                    md = Phase3MessageDescriptor(
                        owner_sort_key=cd.owner_sort_key,
                        original_code=cd.original_code,
                        message_payload_digest=cd.message_payload_digest,
                    )
                    warn_descs.append(md)
                    warn_binds.append(build_phase3_message_descriptor_binding(md))

                block_descs: list[Any] = []
                block_binds: list[Any] = []
                for b_msg in evidence.blockers:
                    cd = _build_message_descriptor(b_msg)
                    assert cd.message_payload_digest is not None
                    md = Phase3MessageDescriptor(
                        owner_sort_key=cd.owner_sort_key,
                        original_code=cd.original_code,
                        message_payload_digest=cd.message_payload_digest,
                    )
                    block_descs.append(md)
                    block_binds.append(build_phase3_message_descriptor_binding(md))

                warning_descriptor_tuples.append(tuple(warn_descs))
                blocker_descriptor_tuples.append(tuple(block_descs))
                warning_binding_tuples.append(tuple(warn_binds))
                blocker_binding_tuples.append(tuple(block_binds))

                # Build evidence failure binding if evidence has failure
                efb: Phase3RunFailureDescriptorBinding | None = None
                if evidence.failure is not None:
                    fail_desc = _build_run_failure_descriptor(evidence.failure)
                    if fail_desc.canonicalization_error is None:
                        efb = build_phase3_run_failure_descriptor_binding(fail_desc)
                evidence_failure_bindings.append(efb)

                # Source failure binding forbidden for VERIFIED
                source_failure_bindings.append(None)
                phase3_failure_bindings.append(None)

                # Build source record descriptor
                desc = build_phase2_source_record_descriptor(
                    source_record=rec,
                    identity_snapshot=isnap,
                    verified_evidence=evidence,
                    source_failure_binding=None,
                )
                descriptors.append(desc)

                # Build source record snapshot
                cs = build_phase2_source_record_snapshot(
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
                    verified_rating_evidence_digest=(evidence.compute_explicit_evidence_digest()),
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
                    phase2_source_record_descriptor_digest=desc.descriptor_digest,
                    warning_descriptor_binding_digests=tuple(
                        b.descriptor_binding_digest for b in warn_binds
                    ),
                    blocker_descriptor_binding_digests=tuple(
                        b.descriptor_binding_digest for b in block_binds
                    ),
                    source_evaluation_failure_binding_digest=None,
                    evidence_failure_binding_digest=(
                        efb.descriptor_binding_digest if efb is not None else None
                    ),
                )
                complete_snapshots.append(cs)

                # Build source binding
                sb = build_phase3_source_record_binding(
                    source_qualified_candidate_id=rec.source_qualified_candidate_id,
                    evaluation_order_index=rec.evaluation_order_index,
                    phase2_source_record_descriptor_digest=desc.descriptor_digest,
                    verified_rating_evidence_digest=(evidence.compute_explicit_evidence_digest()),
                    phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
                    warning_descriptor_binding_digests=tuple(
                        b.descriptor_binding_digest for b in warn_binds
                    ),
                    blocker_descriptor_binding_digests=tuple(
                        b.descriptor_binding_digest for b in block_binds
                    ),
                    source_evaluation_failure_binding_digest=None,
                    evidence_failure_binding_digest=(
                        efb.descriptor_binding_digest if efb is not None else None
                    ),
                )
                source_bindings.append(sb)

                # Build classification input — compute digest first
                cin_payload = {
                    "schema_version": 1,
                    "source_identity_record_descriptor_digest": isnap.identity_snapshot_digest,
                    "source_record_descriptor_digest": desc.descriptor_digest,
                    "materialized_candidate_digest": cand.source_qualified_candidate_id,
                    "sizing_request_identity_digest": (
                        sizing_request_identity.sizing_request_identity_digest
                    ),
                    "identity_snapshot_digest": sb.phase2_identity_snapshot_digest,
                    "source_binding_digest": sb.binding_digest,
                    "verified_rating_evidence_digest": evidence.compute_explicit_evidence_digest(),
                }
                cin = Phase3CandidateClassificationInput(
                    source_record=rec,
                    source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
                    source_record_descriptor_digest=desc.descriptor_digest,
                    materialized_candidate=cand,
                    sizing_request_identity=sizing_request_identity,
                    sizing_request_identity_digest=sizing_request_identity.sizing_request_identity_digest,
                    evidence_binding=sb,
                    verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
                    classification_input_digest=sha256_digest(cin_payload),
                )
                classification_inputs.append(cin)

                # Classify candidate
                disp = classify_candidate(
                    cin,
                    warning_descriptors=tuple(warn_descs),
                    blocker_descriptors=tuple(block_descs),
                    warning_descriptor_bindings=tuple(warn_binds),
                    blocker_descriptor_bindings=tuple(block_binds),
                    source_failure_binding=None,
                    evidence_failure_binding=efb,
                    identity_snapshot=isnap,
                    complete_snapshot=cs,
                    source_record_descriptor=desc,
                )
                dispositions.append(disp)

                # Build preparation result
                pr = build_phase3_candidate_preparation_result(
                    status=Phase3PreparationStatus.READY,
                    source_qualified_candidate_id=rec.source_qualified_candidate_id,
                    evaluation_order_index=rec.evaluation_order_index,
                    identity_snapshot=isnap,
                    complete_snapshot=cs,
                    source_binding=sb,
                    classification_input=cin,
                )
                preparation_results.append(pr)

            elif rec.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED:
                # RUNTIME_FAILED: identity_snapshot + source_failure_binding
                complete_snapshots.append(None)
                descriptors.append(None)
                source_bindings.append(None)
                classification_inputs.append(None)
                preparation_results.append(None)
                warning_descriptor_tuples.append(())
                blocker_descriptor_tuples.append(())
                warning_binding_tuples.append(())
                blocker_binding_tuples.append(())
                evidence_failure_bindings.append(None)
                phase3_failure_bindings.append(None)

                # Build source failure binding from evaluation_failure
                if rec.evaluation_failure is not None:
                    fail_desc = _build_run_failure_descriptor(rec.evaluation_failure)
                    if fail_desc.canonicalization_error is None:
                        sfb = build_phase3_run_failure_descriptor_binding(fail_desc)
                    else:
                        sfb = None
                else:
                    sfb = None
                source_failure_bindings.append(sfb)

                # Generate disposition for RUNTIME_FAILED
                disp = map_non_verified(
                    rec,
                    source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
                    source_record_descriptor_digest=None,
                    source_failure_binding=sfb,
                    warning_descriptors=(),
                    blocker_descriptors=(),
                    evidence_failure_binding=None,
                )
                dispositions.append(disp)

            elif rec.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID:
                # INTEGRITY_INVALID: only identity_snapshot
                complete_snapshots.append(None)
                descriptors.append(None)
                source_bindings.append(None)
                classification_inputs.append(None)
                preparation_results.append(None)
                warning_descriptor_tuples.append(())
                blocker_descriptor_tuples.append(())
                warning_binding_tuples.append(())
                blocker_binding_tuples.append(())
                evidence_failure_bindings.append(None)
                source_failure_bindings.append(None)
                phase3_failure_bindings.append(None)

                # Generate disposition for INTEGRITY_INVALID
                disp = map_non_verified(
                    rec,
                    source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
                    source_record_descriptor_digest=None,
                    source_failure_binding=None,
                    warning_descriptors=(),
                    blocker_descriptors=(),
                    evidence_failure_binding=None,
                )
                dispositions.append(disp)

            else:
                # UNEVALUATED: only identity_snapshot
                complete_snapshots.append(None)
                descriptors.append(None)
                source_bindings.append(None)
                classification_inputs.append(None)
                preparation_results.append(None)
                warning_descriptor_tuples.append(())
                blocker_descriptor_tuples.append(())
                warning_binding_tuples.append(())
                blocker_binding_tuples.append(())
                evidence_failure_bindings.append(None)
                source_failure_bindings.append(None)
                phase3_failure_bindings.append(None)

                # Generate disposition for UNEVALUATED
                disp = map_non_verified(
                    rec,
                    source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
                    source_record_descriptor_digest=None,
                    source_failure_binding=None,
                    warning_descriptors=(),
                    blocker_descriptors=(),
                    evidence_failure_binding=None,
                )
                dispositions.append(disp)

        # 7. Rank feasible candidates
        feasible_dispositions = [d for d in dispositions if d.disposition is FEASIBLE]
        from hexagent.optimization.phase3_builder import (
            rank_feasible_candidate_dispositions,
        )

        obj = sizing_request_identity.optimization_objective
        ranked_records = list(
            rank_feasible_candidate_dispositions(
                dispositions=tuple(feasible_dispositions),
                optimization_objective=obj,
            )
        )

        # 8. Build OptimizationResult
        from hexagent.optimization.phase3_evaluation import Phase3EvaluationInput

        # Build Phase3EvaluationInput — compute digest first
        ordered_isd = tuple(isnap.identity_snapshot_digest for isnap in identity_snapshots)
        ordered_ssd = tuple(
            cs.snapshot_digest if cs is not None else None for cs in complete_snapshots
        )
        ordered_srd = tuple(
            desc.descriptor_digest if desc is not None else None for desc in descriptors
        )

        eval_input_payload = {
            "schema_version": 1,
            "sizing_request_identity_digest": (
                sizing_request_identity.sizing_request_identity_digest
            ),
            "candidate_set_digest": mat.candidate_set.candidate_set_digest,
            "gate_digest": gate.gate_digest,
            "evaluation_record_count": N,
            "ordered_identity_snapshot_digests": list(ordered_isd),
            "ordered_phase2_source_snapshot_digests": list(ordered_ssd),
            "ordered_phase2_source_record_descriptor_digests": list(ordered_srd),
        }

        eval_input = Phase3EvaluationInput(
            sizing_request_identity=sizing_request_identity,
            sizing_request_identity_digest=sizing_request_identity.sizing_request_identity_digest,
            materialization_result=mat,
            candidate_set_digest=mat.candidate_set.candidate_set_digest,
            gate_digest=gate.gate_digest,
            evaluation_records=eval_records,
            evaluation_record_count=N,
            identity_snapshots=tuple(identity_snapshots),
            complete_snapshots=tuple(complete_snapshots),
            ordered_identity_snapshot_digests=ordered_isd,
            ordered_phase2_source_snapshot_digests=ordered_ssd,
            ordered_phase2_source_record_descriptor_digests=ordered_srd,
            evaluation_input_digest=sha256_digest(eval_input_payload),
        )

        opt_result, provenance = build_optimization_result(
            evaluation_input=eval_input,
            sizing_request=sizing_request,
            candidates=candidates_tuple,
            phase2_source_record_descriptors=tuple(descriptors),
            preparation_results=tuple(preparation_results),
            dispositions=tuple(dispositions),
            ranked_records=tuple(ranked_records),
            source_bindings=tuple(source_bindings),
            classification_inputs=tuple(classification_inputs),
            warning_descriptor_tuples=tuple(warning_descriptor_tuples),
            blocker_descriptor_tuples=tuple(blocker_descriptor_tuples),
            warning_binding_tuples=tuple(warning_binding_tuples),
            blocker_binding_tuples=tuple(blocker_binding_tuples),
            evidence_failure_bindings=tuple(evidence_failure_bindings),
            source_failure_bindings=tuple(source_failure_bindings),
            phase3_failure_bindings=tuple(phase3_failure_bindings),
        )

        # A2: Authoritative verification after build_optimization_result
        from hexagent.optimization.phase3_verifier import (
            Phase3AuthoritativeArtifacts as _PAA,
        )
        from hexagent.optimization.phase3_verifier import (
            verify_phase3_result_semantics_or_raise,
        )

        phase3_artifacts = _PAA(
            sizing_request=sizing_request,
            phase2_source_record_descriptors=tuple(descriptors),
            source_bindings=tuple(source_bindings),
            classification_inputs=tuple(classification_inputs),
            preparation_results=tuple(preparation_results),
            warning_descriptor_tuples=tuple(warning_descriptor_tuples),
            blocker_descriptor_tuples=tuple(blocker_descriptor_tuples),
            warning_binding_tuples=tuple(warning_binding_tuples),
            blocker_binding_tuples=tuple(blocker_binding_tuples),
            evidence_failure_bindings=tuple(evidence_failure_bindings),
            source_failure_bindings=tuple(source_failure_bindings),
            phase3_failure_bindings=tuple(phase3_failure_bindings),
        )

        verify_phase3_result_semantics_or_raise(
            result=opt_result,
            graph=provenance,
            evaluation_input=eval_input,
            artifacts=phase3_artifacts,
            dispositions=tuple(dispositions),
            ranked_records=tuple(ranked_records),
        )

        # A3: Collect real warnings/blockers from evaluation records
        all_warnings: list[EngineeringMessage] = []
        all_blockers: list[EngineeringMessage] = []
        for rec in eval_records:
            if rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED:
                evidence = rec.verified_rating_evidence
                if evidence is not None:
                    all_warnings.extend(evidence.warnings)
                    all_blockers.extend(evidence.blockers)

        # Compute top_n from ranked records
        top_n = min(opt_result.requested_top_n, opt_result.feasible_candidate_count)

        return SizingExecutionResult(
            optimization_result=opt_result,
            provenance=provenance,
            warnings=tuple(all_warnings),
            blockers=tuple(all_blockers),
            evaluation_input=eval_input,
            phase3_authoritative_artifacts=phase3_artifacts,
            dispositions=tuple(dispositions),
            ranked_records=tuple(ranked_records),
            top_n_records=tuple(ranked_records[:top_n]),
        )


__all__ = [
    "PreparedRatingRun",
    "PreparedSizingRun",
    "RatingApplicationService",
    "RatingServiceResult",
    "SizingApplicationService",
    "SizingExecutionResult",
    "SizingService",
    "SizingServiceResult",
]
