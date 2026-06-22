"""Pure-function applicability assessment engine.

All functions in this module are deterministic and side-effect-free.
"""

from __future__ import annotations

from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    ApplicabilityVariable,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationKey,
    GeometryType,
    NumericBound,
    OutOfRangeAction,
    OutOfRangePolicy,
    PhaseRegime,
    VariableApplicabilityStatus,
    VariableAssessment,
    compute_assessment_hash,
)
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode


def _action_to_severity(
    action: OutOfRangeAction, allow_extrapolation: bool
) -> EngineeringMessageSeverity:
    """Centralized action→severity mapping.

    allow_explicit_opt_in:
      - with opt-in → WARNING (continuable)
      - without opt-in → BLOCKER (not continuable)
    """
    if action == OutOfRangeAction.block:
        return EngineeringMessageSeverity.BLOCKER
    if action == OutOfRangeAction.warn:
        return EngineeringMessageSeverity.WARNING
    if action == OutOfRangeAction.allow_explicit_opt_in:
        return (
            EngineeringMessageSeverity.WARNING
            if allow_extrapolation
            else EngineeringMessageSeverity.BLOCKER
        )
    if action == OutOfRangeAction.fallback_required:
        return EngineeringMessageSeverity.ERROR
    return EngineeringMessageSeverity.BLOCKER


def _check_geometry_compatible(
    geometry: GeometryType,
    allowed: frozenset[GeometryType],
) -> bool:
    """Check if geometry is compatible. Generic matches ANY geometry."""
    if GeometryType.generic in allowed:
        return True
    return geometry in allowed


def _check_phase_compatible(
    phase_regime: PhaseRegime,
    allowed: frozenset[PhaseRegime],
) -> bool:
    """Check if phase regime is compatible. Generic matches ANY phase."""
    if PhaseRegime.generic in allowed:
        return True
    return phase_regime in allowed


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

    # Item 4: Apply tolerance_fraction — if within tolerance of bound, treat as in range
    tolerance = bound.tolerance_fraction

    # Check absolute bounds (with tolerance)
    if bound.minimum is not None:
        effective_min = bound.minimum * (1.0 - tolerance) if tolerance > 0 else bound.minimum
        if bound.minimum_inclusive:
            if value < effective_min:
                status = VariableApplicabilityStatus.below_absolute
        else:
            if value <= effective_min:
                status = VariableApplicabilityStatus.below_absolute

    if bound.maximum is not None and status == VariableApplicabilityStatus.applicable:
        effective_max = bound.maximum * (1.0 + tolerance) if tolerance > 0 else bound.maximum
        if bound.maximum_inclusive:
            if value > effective_max:
                status = VariableApplicabilityStatus.above_absolute
        else:
            if value >= effective_max:
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
    missing_input_policy: OutOfRangeAction = OutOfRangeAction.block,
    allow_extrapolation: bool = False,
) -> tuple[EngineeringMessage, ...]:
    """Build warning/blocker messages for out-of-range variables.

    Item 3: allow_explicit_opt_in without opt-in → BLOCKER.
    """
    status = var_result.status

    if status in (VariableApplicabilityStatus.applicable, VariableApplicabilityStatus.missing):
        return ()

    var_name = var_result.variable.value

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
    elif status in rec_statuses:
        policy = recommended_policy
        code = ErrorCode.CORRELATION_RECOMMENDED_RANGE_EXCEEDED
    elif status == VariableApplicabilityStatus.missing:
        code = ErrorCode.CORRELATION_INPUT_MISSING
        policy = missing_input_policy
    else:
        return ()

    severity = _action_to_severity(policy, allow_extrapolation)

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
    return (msg,)


def _derive_allows_evaluation(
    status: ApplicabilityStatus,
    policy: OutOfRangePolicy,
    has_absolute_violation: bool,
    has_recommended_violation: bool,
    allow_extrapolation: bool,
    has_missing_required: bool,
    geometry_compatible: bool,
    phase_compatible: bool,
    flow_compatible: bool,
) -> ApplicabilityStatus:
    """Item 4: Derive overall status and allows_evaluation from status + policy.

    OutOfRangePolicy is the SOLE authority for continuation semantics.
    """
    # Priority: incompatible geometry > incompatible phase > incompatible flow
    if not geometry_compatible:
        return ApplicabilityStatus.incompatible_geometry
    if not phase_compatible:
        return ApplicabilityStatus.incompatible_phase
    if not flow_compatible:
        return ApplicabilityStatus.incompatible_flow_regime
    if has_missing_required:
        return ApplicabilityStatus.missing_input

    if has_absolute_violation:
        return ApplicabilityStatus.absolute_range_exceeded
    if has_recommended_violation:
        return ApplicabilityStatus.recommended_range_exceeded

    return ApplicabilityStatus.applicable


def _policy_allows_evaluation(
    status: ApplicabilityStatus,
    policy: OutOfRangePolicy,
    allow_extrapolation: bool,
) -> bool:
    """Item 4: Determine allows_evaluation based on status and policy.

    OutOfRangePolicy is the SOLE authority:
    - recommended_violation=warn → allows_evaluation=True
    - absolute_violation=block → allows_evaluation=False
    - absolute_violation=allow_explicit_opt_in AND inputs.allow_extrapolation=True → True
    - missing_input policy determines continuation
    - incompatible_* → uses respective policy
    - fallback_required → always False
    """
    if status == ApplicabilityStatus.applicable:
        return True

    if status == ApplicabilityStatus.recommended_range_exceeded:
        # recommended_violation=warn allows continuation
        return policy.recommended_violation == OutOfRangeAction.warn

    if status == ApplicabilityStatus.absolute_range_exceeded:
        if policy.absolute_violation == OutOfRangeAction.warn:
            return True
        return (
            policy.absolute_violation == OutOfRangeAction.allow_explicit_opt_in
            and allow_extrapolation
        )

    if status == ApplicabilityStatus.explicit_extrapolation:
        return True

    if status == ApplicabilityStatus.missing_input:
        if policy.missing_input == OutOfRangeAction.warn:
            return True
        return (
            policy.missing_input == OutOfRangeAction.allow_explicit_opt_in and allow_extrapolation
        )

    if status == ApplicabilityStatus.incompatible_geometry:
        if policy.incompatible_geometry == OutOfRangeAction.warn:
            return True
        return (
            policy.incompatible_geometry == OutOfRangeAction.allow_explicit_opt_in
            and allow_extrapolation
        )

    if status == ApplicabilityStatus.incompatible_phase:
        if policy.incompatible_phase == OutOfRangeAction.warn:
            return True
        return (
            policy.incompatible_phase == OutOfRangeAction.allow_explicit_opt_in
            and allow_extrapolation
        )

    if status == ApplicabilityStatus.incompatible_flow_regime:
        if policy.incompatible_flow_regime == OutOfRangeAction.warn:
            return True
        return (
            policy.incompatible_flow_regime == OutOfRangeAction.allow_explicit_opt_in
            and allow_extrapolation
        )

    # any other status → False
    return False


def assess_applicability(
    definition: CorrelationDefinition,
    inputs: CorrelationApplicabilityInput,
) -> ApplicabilityAssessment:
    """Pure, deterministic applicability assessment.

    Steps:
    1. Check geometry compatibility (generic matches ANY geometry).
    2. Check phase regime compatibility (generic matches ANY phase).
    3. Check flow regime compatibility.
    4. Check each NumericBound against supplied values (with tolerance).
    5. Check required inputs.
    6. Derive overall status from policy (Item 4: policy is SOLE authority).
    7. Build warnings/blockers based on OutOfRangePolicy.
    8. Derive allows_evaluation from status + policy (never caller input).
    9. Compute assessment_hash.
    """
    key = definition.key
    envelope = definition.envelope
    policy = definition.out_of_range_policy

    # Build a lookup from variable to value for the input
    values_dict: dict[ApplicabilityVariable, float] = dict(inputs.values)

    # 1. Geometry check (generic wildcard semantics)
    geometry_compatible = _check_geometry_compatible(inputs.geometry, envelope.geometry_types)

    # 2. Phase regime check (generic wildcard semantics)
    phase_compatible = _check_phase_compatible(inputs.phase_regime, envelope.phase_regimes)

    # 3. Flow regime check
    flow_compatible = inputs.flow_regime in envelope.flow_regimes

    # 4. Check each NumericBound
    variable_results: list[VariableAssessment] = []
    for bound in envelope.bounds:
        value = values_dict.get(bound.variable)
        vr = _assess_variable_bound(bound, value)
        variable_results.append(vr)

    # 5. Check required inputs
    has_missing_required = False
    for req_var in envelope.required_inputs:
        if req_var not in values_dict:
            has_missing_required = True
            already_present = any(vr.variable == req_var for vr in variable_results)
            if not already_present:
                variable_results.append(
                    VariableAssessment(
                        variable=req_var,
                        supplied_value=None,
                        status=VariableApplicabilityStatus.missing,
                    )
                )

    # Item 4: Check for missing non-required bounded variables that are absent
    # A non-required bounded variable that is missing is NOT an error (no blocker)
    # but it produces a variable result with status=missing

    # 6. Determine overall status
    abs_statuses = (
        VariableApplicabilityStatus.below_absolute,
        VariableApplicabilityStatus.above_absolute,
    )
    rec_statuses = (
        VariableApplicabilityStatus.below_recommended,
        VariableApplicabilityStatus.above_recommended,
    )
    has_absolute_violation = any(vr.status in abs_statuses for vr in variable_results)
    has_recommended_violation = any(vr.status in rec_statuses for vr in variable_results)

    overall_status = _derive_allows_evaluation(
        status=ApplicabilityStatus.applicable,  # placeholder, derived below
        policy=policy,
        has_absolute_violation=has_absolute_violation,
        has_recommended_violation=has_recommended_violation,
        allow_extrapolation=inputs.allow_extrapolation,
        has_missing_required=has_missing_required,
        geometry_compatible=geometry_compatible,
        phase_compatible=phase_compatible,
        flow_compatible=flow_compatible,
    )

    # Item 4: Handle explicit_extrapolation when policy allows
    if (
        has_absolute_violation
        and inputs.allow_extrapolation
        and policy.absolute_violation == OutOfRangeAction.allow_explicit_opt_in
    ):
        overall_status = ApplicabilityStatus.explicit_extrapolation

    # Item 4: Handle recommended range exceeded with warn policy
    if has_recommended_violation and not has_absolute_violation:
        rec_action = policy.recommended_violation
        if rec_action in (OutOfRangeAction.warn, OutOfRangeAction.block):
            overall_status = ApplicabilityStatus.recommended_range_exceeded
        elif (
            policy.recommended_violation == OutOfRangeAction.allow_explicit_opt_in
            and inputs.allow_extrapolation
        ):
            overall_status = ApplicabilityStatus.explicit_extrapolation
        else:
            overall_status = ApplicabilityStatus.recommended_range_exceeded

    # 7. Build warnings/blockers
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []
    for vr in variable_results:
        msgs = _build_boundary_messages(
            key,
            vr,
            policy.absolute_violation,
            policy.recommended_violation,
            allow_extrapolation=inputs.allow_extrapolation,
        )
        for msg in msgs:
            if msg.allows_continuation:
                warnings.append(msg)
            else:
                blockers.append(msg)

    # Missing required input messages
    if has_missing_required:
        missing_policy = policy.missing_input
        missing_severity = _action_to_severity(missing_policy, inputs.allow_extrapolation)
        for vr in variable_results:
            if vr.status == VariableApplicabilityStatus.missing:
                msg = EngineeringMessage(
                    code=ErrorCode.CORRELATION_INPUT_MISSING,
                    severity=missing_severity,
                    message=(
                        f"Required variable '{vr.variable.value}' missing "
                        f"for {key.correlation_id} v{key.version}"
                    ),
                    source_module="correlations.applicability",
                    context=(
                        ("correlation_id", key.correlation_id),
                        ("correlation_version", key.version),
                        ("variable", vr.variable.value),
                        ("status", "missing"),
                    ),
                )
                if msg.allows_continuation:
                    warnings.append(msg)
                else:
                    blockers.append(msg)

    # Incompatibility messages
    if not geometry_compatible:
        _geo_severity = _action_to_severity(
            policy.incompatible_geometry, inputs.allow_extrapolation
        )
        geo_msg = EngineeringMessage(
            code=ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
            severity=_geo_severity,
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
        if geo_msg.allows_continuation:
            warnings.append(geo_msg)
        else:
            blockers.append(geo_msg)

    if not phase_compatible:
        _phase_severity = _action_to_severity(policy.incompatible_phase, inputs.allow_extrapolation)
        phase_msg = EngineeringMessage(
            code=ErrorCode.CORRELATION_PHASE_INCOMPATIBLE,
            severity=_phase_severity,
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
        if phase_msg.allows_continuation:
            warnings.append(phase_msg)
        else:
            blockers.append(phase_msg)

    if not flow_compatible:
        _flow_severity = _action_to_severity(
            policy.incompatible_flow_regime, inputs.allow_extrapolation
        )
        flow_msg = EngineeringMessage(
            code=ErrorCode.CORRELATION_FLOW_REGIME_INCOMPATIBLE,
            severity=_flow_severity,
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
        if flow_msg.allows_continuation:
            warnings.append(flow_msg)
        else:
            blockers.append(flow_msg)

    # Item 8: Handle fallback_required as non-continuable
    # fallback_required is already non-continuable by severity=ERROR

    # 8. Derive allows_evaluation from status + policy
    allows_evaluation = _policy_allows_evaluation(
        overall_status,
        policy,
        inputs.allow_extrapolation,
    )

    # 9. Compute assessment_hash
    assessment_hash = compute_assessment_hash(
        definition_hash=definition.definition_hash,
        correlation_key=key,
        geometry=inputs.geometry,
        phase_regime=inputs.phase_regime,
        flow_regime=inputs.flow_regime,
        input_values=inputs.values,
        status=overall_status,
        variable_results=tuple(variable_results),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        policy=policy,
        allow_extrapolation=inputs.allow_extrapolation,
    )

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
