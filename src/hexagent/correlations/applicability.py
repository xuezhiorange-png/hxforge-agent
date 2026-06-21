"""Pure-function applicability assessment engine.

All functions in this module are deterministic and side-effect-free.
"""

from __future__ import annotations

from hexagent.core.canonical import sha256_digest
from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationKey,
    NumericBound,
    OutOfRangeAction,
    VariableApplicabilityStatus,
    VariableAssessment,
)
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode


def _assess_variable_bound(
    bound: NumericBound,
    value: float | None,
) -> VariableAssessment:
    """Assess a single variable against its numeric bound."""
    if value is None:
        return VariableAssessment(
            variable=bound.variable,
            supplied_value=None,
            absolute_minimum=bound.minimum,
            absolute_maximum=bound.maximum,
            recommended_minimum=bound.recommended_minimum,
            recommended_maximum=bound.recommended_maximum,
            status=VariableApplicabilityStatus.missing,
        )

    status = VariableApplicabilityStatus.applicable

    # Check absolute bounds
    if bound.minimum is not None:
        if bound.minimum_inclusive:
            if value < bound.minimum:
                status = VariableApplicabilityStatus.below_absolute
        else:
            if value <= bound.minimum:
                status = VariableApplicabilityStatus.below_absolute

    if bound.maximum is not None and status == VariableApplicabilityStatus.applicable:
        if bound.maximum_inclusive:
            if value > bound.maximum:
                status = VariableApplicabilityStatus.above_absolute
        else:
            if value >= bound.maximum:
                status = VariableApplicabilityStatus.above_absolute

    # Check recommended bounds (only if within absolute)
    if status == VariableApplicabilityStatus.applicable:
        if bound.recommended_minimum is not None and value < bound.recommended_minimum:
            status = VariableApplicabilityStatus.below_recommended
        elif bound.recommended_maximum is not None and value > bound.recommended_maximum:
            status = VariableApplicabilityStatus.above_recommended

    return VariableAssessment(
        variable=bound.variable,
        supplied_value=value,
        absolute_minimum=bound.minimum,
        absolute_maximum=bound.maximum,
        recommended_minimum=bound.recommended_minimum,
        recommended_maximum=bound.recommended_maximum,
        status=status,
    )


def _build_boundary_messages(
    key: CorrelationKey,
    var_result: VariableAssessment,
    out_of_range_policy: OutOfRangeAction,
    recommended_policy: OutOfRangeAction,
) -> tuple[EngineeringMessage, ...]:
    """Build warning/blocker messages for out-of-range variables."""
    messages: list[EngineeringMessage] = []
    status = var_result.status

    if status == VariableApplicabilityStatus.applicable:
        return ()

    # Determine the variable name for context
    var_name = var_result.variable.value

    # Determine severity and error code based on status and policy
    abs_statuses = (
        VariableApplicabilityStatus.below_absolute,
        VariableApplicabilityStatus.above_absolute,
    )
    rec_statuses = (
        VariableApplicabilityStatus.below_recommended,
        VariableApplicabilityStatus.above_recommended,
    )
    if status in abs_statuses:
        policy = out_of_range_policy
        code = ErrorCode.CORRELATION_ABSOLUTE_RANGE_EXCEEDED
        severity_map = {
            OutOfRangeAction.block: EngineeringMessageSeverity.BLOCKER,
            OutOfRangeAction.warn: EngineeringMessageSeverity.WARNING,
            OutOfRangeAction.allow_explicit_opt_in: EngineeringMessageSeverity.WARNING,
            OutOfRangeAction.fallback_required: EngineeringMessageSeverity.ERROR,
        }
    elif status in rec_statuses:
        policy = recommended_policy
        code = ErrorCode.CORRELATION_RECOMMENDED_RANGE_EXCEEDED
        severity_map = {
            OutOfRangeAction.block: EngineeringMessageSeverity.BLOCKER,
            OutOfRangeAction.warn: EngineeringMessageSeverity.WARNING,
            OutOfRangeAction.allow_explicit_opt_in: EngineeringMessageSeverity.WARNING,
            OutOfRangeAction.fallback_required: EngineeringMessageSeverity.ERROR,
        }
    elif status == VariableApplicabilityStatus.missing:
        code = ErrorCode.CORRELATION_INPUT_MISSING
        severity_map = {
            OutOfRangeAction.block: EngineeringMessageSeverity.BLOCKER,
            OutOfRangeAction.warn: EngineeringMessageSeverity.WARNING,
            OutOfRangeAction.allow_explicit_opt_in: EngineeringMessageSeverity.WARNING,
            OutOfRangeAction.fallback_required: EngineeringMessageSeverity.ERROR,
        }
        # Use the default for missing input
        policy = OutOfRangeAction.block  # default for missing input
    else:
        return ()

    severity = severity_map.get(policy, EngineeringMessageSeverity.WARNING)

    # Build range info string
    range_parts: list[str] = []
    if var_result.absolute_minimum is not None:
        range_parts.append(f"min={var_result.absolute_minimum}")
    if var_result.absolute_maximum is not None:
        range_parts.append(f"max={var_result.absolute_maximum}")
    if var_result.recommended_minimum is not None:
        range_parts.append(f"rec_min={var_result.recommended_minimum}")
    if var_result.recommended_maximum is not None:
        range_parts.append(f"rec_max={var_result.recommended_maximum}")

    range_str = ", ".join(range_parts) if range_parts else "no bounds defined"

    msg = EngineeringMessage(
        code=code,
        severity=severity,
        message=(
            f"Variable '{var_name}' has status '{status.value}' "
            f"for {key.correlation_id} v{key.version} "
            f"(bounds: {range_str})"
        ),
        source_module="correlations.applicability",
        context=(
            ("correlation_id", key.correlation_id),
            ("correlation_version", key.version),
            ("variable", var_name),
            ("status", status.value),
            ("supplied_value", var_result.supplied_value),
            ("range", range_str),
        ),
    )
    messages.append(msg)
    return tuple(messages)


def _compute_overall_status(
    variable_results: tuple[VariableAssessment, ...],
    geometry_compatible: bool,
    phase_compatible: bool,
    flow_compatible: bool,
    required_inputs_missing: bool,
    allow_extrapolation: bool,
) -> ApplicabilityStatus:
    """Determine the overall applicability status."""
    # Priority: incompatible geometry > incompatible phase > incompatible flow
    if not geometry_compatible:
        return ApplicabilityStatus.incompatible_geometry
    if not phase_compatible:
        return ApplicabilityStatus.incompatible_phase
    if not flow_compatible:
        return ApplicabilityStatus.incompatible_flow_regime
    if required_inputs_missing:
        return ApplicabilityStatus.missing_input

    # Check variable results
    abs_statuses = (
        VariableApplicabilityStatus.below_absolute,
        VariableApplicabilityStatus.above_absolute,
    )
    rec_statuses = (
        VariableApplicabilityStatus.below_recommended,
        VariableApplicabilityStatus.above_recommended,
    )
    has_absolute_violation = False
    has_recommended_violation = False
    for vr in variable_results:
        if vr.status in abs_statuses:
            has_absolute_violation = True
        elif vr.status in rec_statuses:
            has_recommended_violation = True

    if has_absolute_violation:
        if allow_extrapolation:
            return ApplicabilityStatus.explicit_extrapolation
        return ApplicabilityStatus.absolute_range_exceeded
    if has_recommended_violation:
        if allow_extrapolation:
            return ApplicabilityStatus.explicit_extrapolation
        return ApplicabilityStatus.recommended_range_exceeded

    return ApplicabilityStatus.applicable


def assess_applicability(
    definition: CorrelationDefinition,
    inputs: CorrelationApplicabilityInput,
) -> ApplicabilityAssessment:
    """Pure, deterministic applicability assessment.

    Steps:
    1. Check geometry compatibility.
    2. Check phase regime compatibility.
    3. Check flow regime compatibility.
    4. Check each NumericBound against supplied values.
    5. Check required inputs.
    6. Determine overall status.
    7. Build warnings/blockers based on OutOfRangePolicy.
    8. Compute assessment_hash.
    """
    key = definition.key
    envelope = definition.envelope
    policy = definition.out_of_range_policy

    # 1. Geometry check
    geometry_compatible = inputs.geometry in envelope.geometry_types
    if not geometry_compatible:
        pass  # handled later

    # 2. Phase regime check
    phase_compatible = inputs.phase_regime in envelope.phase_regimes

    # 3. Flow regime check
    flow_compatible = inputs.flow_regime in envelope.flow_regimes

    # 4. Check each NumericBound
    variable_results: list[VariableAssessment] = []
    for bound in envelope.bounds:
        value = inputs.values.get(bound.variable)
        vr = _assess_variable_bound(bound, value)
        variable_results.append(vr)

    # 5. Check required inputs
    required_inputs_missing = False
    for req_var in envelope.required_inputs:
        if req_var not in inputs.values:
            required_inputs_missing = True
            # Add a missing variable assessment if not already present
            already_present = any(vr.variable == req_var for vr in variable_results)
            if not already_present:
                variable_results.append(
                    VariableAssessment(
                        variable=req_var,
                        supplied_value=None,
                        status=VariableApplicabilityStatus.missing,
                    )
                )

    # 6. Determine overall status
    overall_status = _compute_overall_status(
        tuple(variable_results),
        geometry_compatible,
        phase_compatible,
        flow_compatible,
        required_inputs_missing,
        inputs.allow_extrapolation,
    )

    # 7. Build warnings/blockers
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []
    for vr in variable_results:
        msgs = _build_boundary_messages(
            key,
            vr,
            policy.absolute_violation,
            policy.recommended_violation,
        )
        for msg in msgs:
            if msg.allows_continuation:
                warnings.append(msg)
            else:
                blockers.append(msg)

    # Incompatibility messages
    if not geometry_compatible:
        geo_msg = EngineeringMessage(
            code=ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"Geometry '{inputs.geometry.value}' incompatible with "
                f"{key.correlation_id} v{key.version}"
            ),
            source_module="correlations.applicability",
            context=(
                ("correlation_id", key.correlation_id),
                ("correlation_version", key.version),
                ("geometry", inputs.geometry.value),
                ("allowed", ",".join(sorted(g.value for g in envelope.geometry_types))),
            ),
        )
        blockers.append(geo_msg)

    if not phase_compatible:
        phase_msg = EngineeringMessage(
            code=ErrorCode.CORRELATION_PHASE_INCOMPATIBLE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"Phase regime '{inputs.phase_regime.value}' incompatible with "
                f"{key.correlation_id} v{key.version}"
            ),
            source_module="correlations.applicability",
            context=(
                ("correlation_id", key.correlation_id),
                ("correlation_version", key.version),
                ("phase_regime", inputs.phase_regime.value),
                (
                    "allowed",
                    ",".join(sorted(p.value for p in envelope.phase_regimes)),
                ),
            ),
        )
        blockers.append(phase_msg)

    if not flow_compatible:
        flow_msg = EngineeringMessage(
            code=ErrorCode.CORRELATION_FLOW_REGIME_INCOMPATIBLE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"Flow regime '{inputs.flow_regime.value}' incompatible with "
                f"{key.correlation_id} v{key.version}"
            ),
            source_module="correlations.applicability",
            context=(
                ("correlation_id", key.correlation_id),
                ("correlation_version", key.version),
                ("flow_regime", inputs.flow_regime.value),
                (
                    "allowed",
                    ",".join(sorted(f.value for f in envelope.flow_regimes)),
                ),
            ),
        )
        blockers.append(flow_msg)

    # 8. Compute assessment_hash
    allows_evaluation = overall_status == ApplicabilityStatus.applicable or (
        overall_status == ApplicabilityStatus.explicit_extrapolation and inputs.allow_extrapolation
    )

    assessment_payload = {
        "correlation_key": {
            "correlation_id": key.correlation_id,
            "version": key.version,
        },
        "status": overall_status.value,
        "variable_results": [
            {
                "variable": vr.variable.value,
                "status": vr.status.value,
                "supplied_value": vr.supplied_value,
            }
            for vr in variable_results
        ],
        "allows_evaluation": allows_evaluation,
    }
    assessment_hash = sha256_digest(assessment_payload)

    return ApplicabilityAssessment(
        correlation_key=key,
        status=overall_status,
        variable_results=tuple(variable_results),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        allows_evaluation=allows_evaluation,
        assessment_hash=assessment_hash,
    )


__all__ = ["assess_applicability"]
