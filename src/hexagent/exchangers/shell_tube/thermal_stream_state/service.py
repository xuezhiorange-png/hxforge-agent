"""TASK160 validation service and heat-capacity-rate calculation."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext

from .canonical import (
    request_hash,
    result_id,
    success_hash_from_inputs,
    typed_blocked_hash,
    typed_blocked_result_id,
)
from .errors import BlockerCode, make_blocker, sort_blockers
from .ingress import (
    RawIngressStructuralError,
    build_strict_request,
    coerce_raw_request,
    make_raw_boundary_blocked_result,
    project_raw_request,
)
from .models import (
    CalculationRunScope,
    CapacityRatedStream,
    FailureStage,
    Task160BlockedResult,
    Task160Blocker,
    Task160PreResultIdentityInputs,
    Task160RawRequest,
    Task160Request,
    Task160Result,
    Task160ValidationResult,
    ThermalRole,
    ValidationStatus,
)
from .provenance import build_provenance
from .validation import (
    make_applicability_ledger,
    make_completeness_ledger,
    resolve_thermal_roles,
    validate_base_streams,
)

TASK160_DECIMAL_CONTEXT = Context(
    prec=160,
    rounding=ROUND_HALF_EVEN,
    Emin=-999999,
    Emax=999999,
    capitals=1,
    clamp=0,
)


def _valid_decimal(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite()


def compute_heat_capacity_rate(mass_flow_kg_s: Decimal, specific_heat_J_kg_K: Decimal) -> Decimal:
    """Return Cdot in W/K without normalization or engineering tolerance."""
    if not _valid_decimal(mass_flow_kg_s) or not _valid_decimal(specific_heat_J_kg_K):
        raise ValueError("mass flow and specific heat must be finite Decimal values")
    if mass_flow_kg_s <= 0 or specific_heat_J_kg_K <= 0:
        raise ValueError("mass flow and specific heat must be positive")
    if (
        len(mass_flow_kg_s.as_tuple().digits) > 79
        or len(specific_heat_J_kg_K.as_tuple().digits) > 79
    ):
        raise ValueError("input exceeds TASK160 significant-digit limit")
    if not -499000 <= mass_flow_kg_s.adjusted() <= 499000:
        raise ValueError("mass flow adjusted exponent is outside TASK160 domain")
    if not -499000 <= specific_heat_J_kg_K.adjusted() <= 499000:
        raise ValueError("specific heat adjusted exponent is outside TASK160 domain")
    with localcontext(TASK160_DECIMAL_CONTEXT):
        result = mass_flow_kg_s * specific_heat_J_kg_K
    if not result.is_finite() or result <= 0:
        raise ValueError("heat-capacity rate is not finite and positive")
    return result


def _typed_blocked(
    request: Task160Request,
    request_hash_value: str,
    blockers: Iterable[Task160Blocker],
    stage: FailureStage,
) -> Task160ValidationResult:
    ordered = sort_blockers(blockers)
    blocked_hash = typed_blocked_hash(
        schema_version=request.schema_version,
        task160_version=request.task160_version,
        implementation_software_version=request.implementation_software_version,
        failure_stage=stage,
        request_hash_value=request_hash_value,
        blockers=ordered,
        deferred_capabilities=request.deferred_capabilities,
        producer_identity=request.provenance_inputs.producer_identity,
        provenance_inputs=request.provenance_inputs,
    )
    provenance = build_provenance(
        schema_version=request.schema_version,
        task160_version=request.task160_version,
        implementation_software_version=request.implementation_software_version,
        input_hash=request_hash_value,
        provenance_inputs=request.provenance_inputs,
        adapter_evidence=request.adapter_evidence,
        artifact_hash=blocked_hash,
        artifact_id=typed_blocked_result_id(blocked_hash),
        scope=CalculationRunScope.TYPED_BLOCKED,
        failure_stage=stage,
    )
    result = Task160BlockedResult(
        schema_version=request.schema_version,
        task160_version=request.task160_version,
        implementation_software_version=request.implementation_software_version,
        failure_stage=stage,
        request_hash=request_hash_value,
        blockers=ordered,
        warnings=(),
        deferred_capabilities=request.deferred_capabilities,
        producer_identity=request.provenance_inputs.producer_identity,
        provenance=provenance,
        blocked_result_hash=blocked_hash,
        blocked_result_id=typed_blocked_result_id(blocked_hash),
    )
    return Task160ValidationResult(ValidationStatus.TYPED_BLOCKED, None, result, None)


def _raw_blocked(
    raw: Task160RawRequest, blockers: Iterable[Task160Blocker]
) -> Task160ValidationResult:
    # Keep the raw transport's deferred-capability values in the artifact
    # where they are projectable; malformed/missing values remain empty.
    result = make_raw_boundary_blocked_result(raw, tuple(blockers))
    return Task160ValidationResult(ValidationStatus.RAW_BOUNDARY_BLOCKED, result, None, None)


def validate_request(raw: Task160RawRequest | dict[str, object]) -> Task160ValidationResult:
    """Validate raw TASK160 input and return exactly one result branch."""
    try:
        raw_request = coerce_raw_request(raw)
        # Projection is deliberately completed before any strict model is
        # built so all ordinary incomplete authority is hashable.
        project_raw_request(raw_request)
    except RawIngressStructuralError:
        raise

    strict_request, raw_blockers = build_strict_request(raw_request)
    if raw_blockers:
        return _raw_blocked(raw_request, raw_blockers)
    if strict_request is None:
        return _raw_blocked(
            raw_request,
            (
                make_blocker(
                    BlockerCode.B018, stage=FailureStage.RAW_BOUNDARY, field_path="request"
                ),
            ),
        )

    request_hash_value = request_hash(strict_request)
    try:
        states = validate_base_streams(strict_request)
    except (TypeError, ValueError):
        blocker = make_blocker(
            BlockerCode.B030, stage=FailureStage.STRICT_VALIDATION, field_path="stream_records"
        )
        return _typed_blocked(
            strict_request, request_hash_value, (blocker,), FailureStage.STRICT_VALIDATION
        )

    applicability = make_applicability_ledger(strict_request, states)
    if applicability.status.value != "APPLICABLE":
        return _typed_blocked(
            strict_request, request_hash_value, applicability.blockers, FailureStage.APPLICABILITY
        )

    try:
        role_resolved = resolve_thermal_roles(*states)
    except ValueError as exc:
        code = BlockerCode.B010 if str(exc) == BlockerCode.B010.value else BlockerCode.B009
        blocker = make_blocker(
            code, stage=FailureStage.STRICT_VALIDATION, field_path="inlet_temperature_K"
        )
        return _typed_blocked(
            strict_request, request_hash_value, (blocker,), FailureStage.STRICT_VALIDATION
        )

    try:
        rated = tuple(
            CapacityRatedStream(
                role,
                compute_heat_capacity_rate(
                    role.input_state.input.mass_flow_kg_s,
                    role.input_state.input.property_snapshot.specific_heat_J_kg_K,
                ),
            )
            for role in role_resolved
        )
    except (TypeError, ValueError, InvalidOperation):
        blocker = make_blocker(
            BlockerCode.B011, stage=FailureStage.STRICT_VALIDATION, field_path="mass_flow_kg_s"
        )
        return _typed_blocked(
            strict_request, request_hash_value, (blocker,), FailureStage.STRICT_VALIDATION
        )

    hot = next((item for item in rated if item.thermal_role is ThermalRole.HOT), None)
    cold = next((item for item in rated if item.thermal_role is ThermalRole.COLD), None)
    if hot is None or cold is None:
        blocker = make_blocker(
            BlockerCode.B010, stage=FailureStage.STRICT_VALIDATION, field_path="inlet_temperature_K"
        )
        return _typed_blocked(
            strict_request, request_hash_value, (blocker,), FailureStage.STRICT_VALIDATION
        )
    c_dot_hot = hot.heat_capacity_rate_W_K
    c_dot_cold = cold.heat_capacity_rate_W_K
    pre = Task160PreResultIdentityInputs(
        request_hash=request_hash_value,
        stream_records=(rated[0], rated[1]),
        envelope_authority=strict_request.envelope_authority,
        adapter_evidence=strict_request.adapter_evidence,
        deferred_capabilities=strict_request.deferred_capabilities,
        c_dot_hot_W_K=c_dot_hot,
        c_dot_cold_W_K=c_dot_cold,
        applicability=applicability,
        warnings=(),
        provenance_inputs=strict_request.provenance_inputs,
        source_definition_id="TASK160-SOURCE-DEFINITION-R1-ISSUE-221",
    )
    completeness = make_completeness_ledger(
        strict_request,
        rated,
        c_dot_hot_W_K=c_dot_hot,
        c_dot_cold_W_K=c_dot_cold,
        applicability=applicability,
        identity_inputs_ready=True,
    )
    if completeness.status.value != "COMPLETE":
        return _typed_blocked(
            strict_request, request_hash_value, completeness.blockers, FailureStage.COMPLETENESS
        )

    try:
        final_hash = success_hash_from_inputs(
            request_hash_value=request_hash_value,
            stream_records=pre.stream_records,
            envelope_authority=pre.envelope_authority,
            adapter_evidence=pre.adapter_evidence,
            deferred_capabilities=pre.deferred_capabilities,
            c_dot_hot_W_K=pre.c_dot_hot_W_K,
            c_dot_cold_W_K=pre.c_dot_cold_W_K,
            applicability=pre.applicability,
            completeness=completeness,
            provenance_inputs=pre.provenance_inputs,
            schema_version=strict_request.schema_version,
            task160_version=strict_request.task160_version,
            implementation_software_version=strict_request.implementation_software_version,
        )
        final_id = result_id(final_hash)
        provenance = build_provenance(
            schema_version=strict_request.schema_version,
            task160_version=strict_request.task160_version,
            implementation_software_version=strict_request.implementation_software_version,
            input_hash=request_hash_value,
            provenance_inputs=strict_request.provenance_inputs,
            adapter_evidence=strict_request.adapter_evidence,
            artifact_hash=final_hash,
            artifact_id=final_id,
            scope=CalculationRunScope.SUCCESS,
        )
        result = Task160Result(
            schema_version=strict_request.schema_version,
            task160_version=strict_request.task160_version,
            implementation_software_version=strict_request.implementation_software_version,
            request_hash=request_hash_value,
            stream_records=(rated[0], rated[1]),
            envelope_authority=strict_request.envelope_authority,
            adapter_evidence=strict_request.adapter_evidence,
            deferred_capabilities=strict_request.deferred_capabilities,
            c_dot_hot_W_K=c_dot_hot,
            c_dot_cold_W_K=c_dot_cold,
            applicability=applicability,
            completeness=completeness,
            warnings=(),
            blockers=(),
            provenance=provenance,
            result_hash=final_hash,
            result_id=final_id,
        )
    except (TypeError, ValueError, RuntimeError):
        blocker = make_blocker(
            BlockerCode.B023, stage=FailureStage.IDENTITY, field_path="result_identity"
        )
        return _typed_blocked(strict_request, request_hash_value, (blocker,), FailureStage.IDENTITY)
    return Task160ValidationResult(ValidationStatus.VALID, None, None, result)


__all__ = [
    "TASK160_DECIMAL_CONTEXT",
    "compute_heat_capacity_rate",
    "validate_request",
]
