"""TASK174 fail-closed orchestration across existing hydraulic producers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Literal, cast

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
from hexagent.exchangers.shell_tube.bell_delaware.decimal_math import engineering_context
from hexagent.exchangers.shell_tube.bell_delaware.models import (
    Task166BlockedResult,
    Task166Result,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import canonical as task034_canonical
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    ShellSidePressureDropResult,
    ShellSidePressureDropValidationResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition import (
    identity as task029_identity,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    CompletenessStatus,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockedResult,
    Task029RawBoundaryBlockedResult,
    Task029SuccessResult,
)

from .models import (
    TASK020_CONFIGURATION_HASH,
    TASK020_CONFIGURATION_ID,
    TASK025_HYDRAULIC_AUTHORITY_HASH,
    TASK025_RESULT_HASH,
    TUBE_COMPONENT_TYPES,
    Task174BlockedResult,
    Task174Blocker,
    Task174CaseRequest,
    Task174SuccessResult,
)

_EVENT_ROLE_COUNTS = {
    "BAFFLE": 4,
    "WINDOW": 4,
    "LEAKAGE_GEOMETRY": 4,
    "CENTRAL_CROSSFLOW": 3,
    "INLET_END_ZONE": 1,
    "OUTLET_END_ZONE": 1,
    "BYPASS_GEOMETRY": 1,
    "TUBE_ROW_OR_CROSSED_ROW": 1,
}

_BELL_ALLOCATION_BY_EVENT_ROLE = {
    "CENTRAL_CROSSFLOW": ("ADDITIVE_PRESSURE_REGION", "BELL_CENTRAL_CROSSFLOW_REGION"),
    "WINDOW": ("ADDITIVE_PRESSURE_REGION", "BELL_WINDOW_REGION"),
    "INLET_END_ZONE": ("ADDITIVE_PRESSURE_REGION", "BELL_INLET_END_ZONE"),
    "OUTLET_END_ZONE": ("ADDITIVE_PRESSURE_REGION", "BELL_OUTLET_END_ZONE"),
    "BAFFLE": ("CORRECTION_OR_GEOMETRY_SUPPORT", "BAFFLE_GEOMETRY_SUPPORT"),
    "LEAKAGE_GEOMETRY": ("CORRECTION_OR_GEOMETRY_SUPPORT", "RL_LEAKAGE_CORRECTION_SUPPORT"),
    "BYPASS_GEOMETRY": ("CORRECTION_OR_GEOMETRY_SUPPORT", "RB_BYPASS_CORRECTION_SUPPORT"),
    "TUBE_ROW_OR_CROSSED_ROW": (
        "CORRECTION_OR_GEOMETRY_SUPPORT",
        "CROSS_FLOW_ROW_COUNT_SUPPORT",
    ),
}


@dataclass(frozen=True)
class Task174NativeOutputs:
    """Already-produced lower-level results; TASK174 never fabricates them."""

    task029: Task029SuccessResult | Task029BlockedResult | Task029RawBoundaryBlockedResult | None
    task034: ShellSidePressureDropValidationResult | None
    task166: Task166Result | Task166BlockedResult | None


Task174Outcome = Task174BlockedResult | Task174SuccessResult


def _native_event_ledger_valid(
    request: Task174CaseRequest,
    task166: Task166Result | Task166BlockedResult | None,
) -> bool:
    if task166 is None or type(task166) is not Task166Result:
        return False
    try:
        replayed_hash = task166_canonical.result_hash(task166)
        replayed_id = task166_canonical.result_id(replayed_hash)
    except Exception:
        return False
    if (
        task166.result_hash != replayed_hash
        or task166.result_id != replayed_id
        or task166.blockers
        or task166.bell_geometry is None
    ):
        return False
    role_counts: dict[str, int] = {}
    for event in request.physical_events:
        role_counts[event.event_role] = role_counts.get(event.event_role, 0) + 1
    if role_counts != _EVENT_ROLE_COUNTS or len(request.physical_events) != 19:
        return False
    event_ids = {event.physical_event_id for event in request.physical_events}
    bell_ids = {binding.physical_event_id for binding in request.bell_event_region_allocations}
    if event_ids != bell_ids or len(bell_ids) != len(request.bell_event_region_allocations):
        return False
    by_event = {event.physical_event_id: event for event in request.physical_events}
    for binding in request.bell_event_region_allocations:
        event = by_event[binding.physical_event_id]
        expected_allocation = _BELL_ALLOCATION_BY_EVENT_ROLE.get(event.event_role)
        if (
            binding.task166_result_hash != task166.result_hash
            or expected_allocation is None
            or (binding.allocation_role, binding.bell_region_or_support_role) != expected_allocation
            or event.multiplicity != 1
            or not binding.evidence_refs
        ):
            return False
    additive_count = sum(
        binding.allocation_role == "ADDITIVE_PRESSURE_REGION"
        for binding in request.bell_event_region_allocations
    )
    support_count = sum(
        binding.allocation_role == "CORRECTION_OR_GEOMETRY_SUPPORT"
        for binding in request.bell_event_region_allocations
    )
    with localcontext(engineering_context()):
        try:
            reconciles = (
                task166.central_crossflow_contribution
                + task166.window_contribution
                + task166.entrance_zone_contribution
                + task166.exit_zone_contribution
                == task166.total_shell_pressure_drop
            )
        except Exception:
            return False
    return additive_count == 9 and support_count == 10 and reconciles


def _native_task166_valid(task166: Task166Result | Task166BlockedResult | None) -> bool:
    if type(task166) is not Task166Result:
        return False
    try:
        result_hash = task166_canonical.result_hash(task166)
        result_id = task166_canonical.result_id(result_hash)
    except Exception:
        return False
    return (
        task166.result_hash == result_hash
        and task166.result_id == result_id
        and not task166.blockers
        and not task166.warnings
        and task166.bell_geometry is not None
        and task166.applicability is not None
        and task166.applicability.status.value == "APPLICABLE"
        and task166.completeness is not None
        and task166.completeness.status == "COMPLETE"
    )


def _pressure_bindings_valid(request: Task174CaseRequest) -> bool:
    bindings = request.pressure_property_bindings
    if len(bindings) != 2:
        return False
    by_side = {item.side: item for item in bindings}
    return (
        len(by_side) == 2
        and set(by_side) == {"TUBE", "SHELL"}
        and by_side["TUBE"].pressure_pa == Decimal("101325")
        and by_side["SHELL"].pressure_pa == Decimal("101325")
    )


def _tube_path_complete(
    request: Task174CaseRequest,
    task029: Task029SuccessResult | Task029BlockedResult | Task029RawBoundaryBlockedResult | None,
) -> bool:
    observed: list[str] = [item.component_type for item in request.tube_component_bindings]
    observed.extend(item.component_type for item in request.physical_absence_exclusions)
    if len(observed) != len(set(observed)) or set(observed) != TUBE_COMPONENT_TYPES:
        return False
    if type(task029) is not Task029SuccessResult:
        return False
    if task029.warnings or task029.blockers:
        return False
    try:
        replayed_hash = task029_identity.compute_success_result_hash(task029)
        replayed_id = task029_identity.derive_result_id(replayed_hash)
    except Exception:
        return False
    if task029.result_hash != replayed_hash or task029.result_id != replayed_id:
        return False
    if (
        task029.task025_result_hash != TASK025_RESULT_HASH
        or task029.task025_hydraulic_authority_hash != TASK025_HYDRAULIC_AUTHORITY_HASH
    ):
        return False
    ledger = task029.completeness_ledger
    return (
        ledger.completeness_status is CompletenessStatus.COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY
        and ledger.expected_member_count == ledger.observed_member_count
        and len(ledger.ordered_member_evidence) == ledger.observed_member_count
        and type(task029.modeled_total_tube_side_pressure_drop_pa) is Decimal
        and task029.modeled_total_tube_side_pressure_drop_pa.is_finite()
        and task029.modeled_total_tube_side_pressure_drop_pa >= Decimal("0")
    )


def _task029_result_hash(
    task029: Task029SuccessResult | Task029BlockedResult | Task029RawBoundaryBlockedResult | None,
) -> str | None:
    if type(task029) is Task029SuccessResult:
        return task029.result_hash
    if type(task029) is Task029BlockedResult:
        return task029.result_hash
    return None


def _task166_result_hash(task166: Task166Result | Task166BlockedResult | None) -> str | None:
    if type(task166) is Task166Result:
        return task166.result_hash
    if type(task166) is Task166BlockedResult:
        return task166.result_hash
    return None


def _task166_evidence(result: Task166Result, field_name: str) -> str | None:
    return dict(result.shell_side_hydraulic_evidence).get(field_name)


def _task034_total(
    task034: ShellSidePressureDropValidationResult | None,
    task166: Task166Result | Task166BlockedResult | None,
) -> Decimal | None:
    if type(task034) is not ShellSidePressureDropValidationResult:
        return None
    if (
        task034.status.value != "VALID"
        or type(task034.pressure_drop) is not ShellSidePressureDropResult
    ):
        return None
    result = task034.pressure_drop
    if type(task166) is not Task166Result:
        return None
    task166_geometry_id = _task166_evidence(task166, "geometry_id")
    task166_geometry_hash = _task166_evidence(task166, "geometry_hash")
    if (
        result.task020_configuration_id != TASK020_CONFIGURATION_ID
        or result.task020_configuration_hash != TASK020_CONFIGURATION_HASH
        or task166_geometry_id is None
        or task166_geometry_hash is None
        or result.task031_geometry_id != task166_geometry_id
        or result.task031_geometry_hash != task166_geometry_hash
    ):
        return None
    try:
        replayed_hash = task034_canonical.success_result_hash(result)
        replayed_id = task034_canonical.result_id(replayed_hash)
    except Exception:
        return None
    if (
        result.result_hash != replayed_hash
        or result.result_id != replayed_id
        or result.blockers
        or type(result.modeled_shell_side_pressure_drop_pa) is not Decimal
        or not result.modeled_shell_side_pressure_drop_pa.is_finite()
        or result.modeled_shell_side_pressure_drop_pa < 0
    ):
        return None
    return result.modeled_shell_side_pressure_drop_pa


def _blocker_result(
    request_hash: str,
    blockers: tuple[Task174Blocker, ...],
    fiv_limit_missing: bool,
    *,
    tube_status: Literal["VALIDATED", "BLOCKED_INCOMPLETE_MODELED_BOUNDARY"],
    shell_status: Literal["VALIDATED", "BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION"],
    bell_status: Literal["VALIDATED", "BLOCKED_EVENT_TO_REGION_MAPPING"],
    pressure_status: Literal["VALIDATED", "BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY"],
) -> Task174BlockedResult:
    evidence = {
        "schema_version": "task174.case-hydraulic-orchestration-blocked.v2",
        "request_hash": request_hash,
        "blockers": [item.model_dump(mode="json") for item in blockers],
        "tube_pressure_drop_status": tube_status,
        "shell_pressure_drop_status": shell_status,
        "bell_aggregation_status": bell_status,
        "pressure_coupling_status": pressure_status,
        "fiv_mode": "DIAGNOSTIC_SCREENING_ONLY",
        "fiv_numeric_limit_authority_missing": fiv_limit_missing,
        "fiv_numeric_limit_not_guessed": True,
    }
    return Task174BlockedResult(
        status="BLOCKED",
        request_hash=request_hash,
        tube_pressure_drop_status=tube_status,
        shell_pressure_drop_status=shell_status,
        bell_aggregation_status=bell_status,
        pressure_coupling_status=pressure_status,
        fiv_status="WARN_MISSING_NUMERIC_LIMIT" if fiv_limit_missing else "DIAGNOSTIC_ONLY",
        fiv_numeric_limit_authority_missing=fiv_limit_missing,
        fiv_numeric_limit_not_guessed=True,
        blockers=blockers,
        warnings=("FIV is diagnostic-only; no numeric critical-velocity limit was guessed",)
        if fiv_limit_missing
        else (),
        result_hash=canonical_sha256(evidence),
        result_id=f"urn:hxforge:task174:{canonical_sha256(evidence)}",
    )


def recompute_task174_result_hash(result: Task174Outcome) -> str:
    """Replay either TASK174 outcome identity from its closed public fields."""
    if type(result) is Task174BlockedResult:
        projection = {
            "schema_version": "task174.case-hydraulic-orchestration-blocked.v2",
            "request_hash": result.request_hash,
            "blockers": [item.model_dump(mode="json") for item in result.blockers],
            "tube_pressure_drop_status": result.tube_pressure_drop_status,
            "shell_pressure_drop_status": result.shell_pressure_drop_status,
            "bell_aggregation_status": result.bell_aggregation_status,
            "pressure_coupling_status": result.pressure_coupling_status,
            "fiv_mode": "DIAGNOSTIC_SCREENING_ONLY",
            "fiv_numeric_limit_authority_missing": result.fiv_numeric_limit_authority_missing,
            "fiv_numeric_limit_not_guessed": result.fiv_numeric_limit_not_guessed,
        }
    elif type(result) is Task174SuccessResult:
        projection = {
            "schema_version": "task174.case-hydraulic-orchestration-result.v2",
            "request_hash": result.request_hash,
            "task029_result_id": result.task029_result_id,
            "task029_result_hash": result.task029_result_hash,
            "task166_result_id": result.task166_result_id,
            "task166_result_hash": result.task166_result_hash,
            "modeled_total_tube_side_pressure_drop_pa": str(
                result.modeled_total_tube_side_pressure_drop_pa
            ),
            "bell_total_shell_pressure_drop_pa": str(result.bell_total_shell_pressure_drop_pa),
            "bell_central_crossflow_contribution_pa": str(
                result.bell_central_crossflow_contribution_pa
            ),
            "bell_window_contribution_pa": str(result.bell_window_contribution_pa),
            "bell_inlet_end_zone_contribution_pa": str(result.bell_inlet_end_zone_contribution_pa),
            "bell_outlet_end_zone_contribution_pa": str(
                result.bell_outlet_end_zone_contribution_pa
            ),
            "task034_screening_result_id": result.task034_screening_result_id,
            "task034_screening_result_hash": result.task034_screening_result_hash,
            "kern_screening_pressure_drop_pa": (
                None
                if result.kern_screening_pressure_drop_pa is None
                else str(result.kern_screening_pressure_drop_pa)
            ),
            "tube_outlet_pressure_pa": str(result.tube_outlet_pressure_pa),
            "shell_outlet_pressure_pa": str(result.shell_outlet_pressure_pa),
            "bell_physical_event_count": result.bell_physical_event_count,
            "event_multiplicity_sum": result.event_multiplicity_sum,
            "bell_additive_event_count": result.bell_additive_event_count,
            "bell_support_event_count": result.bell_support_event_count,
            "pressure_coupling_authority_id": result.pressure_coupling_authority_id,
            "fiv_status": result.fiv_status,
            "fiv_numeric_limit_authority_missing": result.fiv_numeric_limit_authority_missing,
            "fiv_numeric_limit_not_guessed": result.fiv_numeric_limit_not_guessed,
        }
    else:
        raise TypeError("TASK174 identity replay requires an exact public outcome model")
    return canonical_sha256(projection)


def validate_request(raw_request: object, native_outputs: Task174NativeOutputs) -> Task174Outcome:
    """Validate a case and orchestrate only complete, source-bound native results."""
    if type(native_outputs) is not Task174NativeOutputs:
        raise TypeError("native_outputs must be exact Task174NativeOutputs")
    if type(raw_request) is Task174CaseRequest:
        request = raw_request
    elif type(raw_request) is dict:
        try:
            request = Task174CaseRequest.model_validate(raw_request, strict=True)
        except ValidationError:
            digest = canonical_sha256({"schema": "task174.invalid-request.v1", "status": "BLOCKED"})
            return _blocker_result(
                digest,
                (
                    Task174Blocker(
                        code="INVALID_TASK174_REQUEST_SCHEMA",
                        scope="REQUEST",
                        missing_bindings=("strict native request schema",),
                        consumer="TASK174.request_validation",
                    ),
                ),
                True,
                tube_status="BLOCKED_INCOMPLETE_MODELED_BOUNDARY",
                shell_status="BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION",
                bell_status="BLOCKED_EVENT_TO_REGION_MAPPING",
                pressure_status="BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY",
            )
    else:
        digest = canonical_sha256({"schema": "task174.invalid-request.v1", "status": "BLOCKED"})
        return _blocker_result(
            digest,
            (
                Task174Blocker(
                    code="INVALID_TASK174_REQUEST_TYPE",
                    scope="REQUEST",
                    missing_bindings=("exact dict or Task174CaseRequest",),
                    consumer="TASK174.request_validation",
                ),
            ),
            True,
            tube_status="BLOCKED_INCOMPLETE_MODELED_BOUNDARY",
            shell_status="BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION",
            bell_status="BLOCKED_EVENT_TO_REGION_MAPPING",
            pressure_status="BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY",
        )

    request_projection = request.model_dump(mode="json")
    request_hash = canonical_sha256(
        {
            "request": request_projection,
            "native_task029_result_hash": _task029_result_hash(native_outputs.task029),
            "native_task034_result_hash": (
                native_outputs.task034.pressure_drop.result_hash
                if native_outputs.task034 is not None
                and native_outputs.task034.pressure_drop is not None
                else None
            ),
            "native_task166_result_hash": _task166_result_hash(native_outputs.task166),
        }
    )
    blockers: list[Task174Blocker] = []
    components = {item.component_type for item in request.tube_component_bindings}
    exclusions = {item.component_type for item in request.physical_absence_exclusions}
    component_coverage = (
        components | exclusions == TUBE_COMPONENT_TYPES and not components & exclusions
    )
    if not component_coverage or not _tube_path_complete(request, native_outputs.task029):
        missing = tuple(sorted(TUBE_COMPONENT_TYPES - components - exclusions))
        blockers.append(
            Task174Blocker(
                code="TUBE_DP_BLOCKED_INCOMPLETE_MODELED_BOUNDARY",
                scope="TUBE_SIDE_TASK029_PATH",
                missing_bindings=missing
                + (
                    ()
                    if type(native_outputs.task029) is Task029SuccessResult
                    else ("complete native TASK029 success result",)
                ),
                consumer=(
                    "TASK029 completeness partition; TASK174 may not publish "
                    "a partial modeled total"
                ),
            )
        )

    shell_valid = _native_task166_valid(native_outputs.task166) and _native_event_ledger_valid(
        request, native_outputs.task166
    )
    if not shell_valid:
        missing_shell: list[str] = []
        if not _native_task166_valid(native_outputs.task166):
            missing_shell.append("valid native TASK166 Bell-Delaware result")
        if not _native_event_ledger_valid(request, native_outputs.task166):
            missing_shell.append(
                "one-to-one source-bound TASK171 physical-event to Bell-region allocation"
            )
        if request.event_to_bell_region_authority_id != "V07-T174-BELL-EVENT-REGION-ALLOCATION-R1":
            missing_shell.append(
                "reviewed TASK171-event to Bell pressure-region allocation authority"
            )
        blockers.append(
            Task174Blocker(
                code="SHELL_DP_BLOCKED_PHYSICAL_EVENT_AND_PRESSURE_STATE_BINDING",
                scope="SHELL_SIDE_TASK166_BELL_AGGREGATION",
                missing_bindings=tuple(missing_shell),
                consumer=(
                    "TASK166 native Bell decomposition and exact-once physical-event allocation"
                ),
            )
        )

    pressure_valid = (
        request.pressure_coupling_authority_id == "V07-T174-REFERENCE-PRESSURE-COUPLING-R1"
        and _pressure_bindings_valid(request)
    )
    if not pressure_valid:
        blockers.append(
            Task174Blocker(
                code="BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY",
                scope="CASE_PRESSURE_PATH",
                missing_bindings=(
                    "one-way frozen reference-pressure authority",
                    "exact tube and shell 101325 Pa reference-pressure snapshots",
                ),
                consumer=(
                    "Stage-1 property provider and one-way post-hydraulic outlet-domain guard"
                ),
            )
        )

    if blockers:
        return _blocker_result(
            request_hash,
            tuple(blockers),
            request.fiv_array_specific_critical_velocity_limit_m_s is None,
            tube_status=(
                "VALIDATED"
                if component_coverage and type(native_outputs.task029) is Task029SuccessResult
                else "BLOCKED_INCOMPLETE_MODELED_BOUNDARY"
            ),
            shell_status="VALIDATED"
            if shell_valid
            else "BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION",
            bell_status="VALIDATED" if shell_valid else "BLOCKED_EVENT_TO_REGION_MAPPING",
            pressure_status=(
                "VALIDATED" if pressure_valid else "BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY"
            ),
        )

    task029 = cast(Task029SuccessResult, native_outputs.task029)
    task166 = cast(Task166Result, native_outputs.task166)
    tube_reference_pressure = next(
        item.pressure_pa for item in request.pressure_property_bindings if item.side == "TUBE"
    )
    shell_reference_pressure = next(
        item.pressure_pa for item in request.pressure_property_bindings if item.side == "SHELL"
    )
    with localcontext(engineering_context()):
        tube_outlet_pressure = (
            tube_reference_pressure - task029.modeled_total_tube_side_pressure_drop_pa
        )
        shell_outlet_pressure = shell_reference_pressure - task166.total_shell_pressure_drop
    pressure_domain_pass = all(
        Decimal("100000") <= pressure <= Decimal("101325")
        for pressure in (tube_outlet_pressure, shell_outlet_pressure)
    )
    if not pressure_domain_pass:
        return _blocker_result(
            request_hash,
            (
                Task174Blocker(
                    code="BLOCKED_PROPERTY_PRESSURE_DOMAIN_EXIT",
                    scope="CASE_PRESSURE_PATH",
                    missing_bindings=(
                        "both one-way calculated outlet pressures remain within 100000..101325 Pa",
                    ),
                    consumer="Stage-1 property-provider admitted pressure domain",
                ),
            ),
            request.fiv_array_specific_critical_velocity_limit_m_s is None,
            tube_status="VALIDATED",
            shell_status="VALIDATED",
            bell_status="VALIDATED",
            pressure_status="BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY",
        )
    task034_total = _task034_total(native_outputs.task034, task166)
    task034_result = (
        native_outputs.task034.pressure_drop
        if native_outputs.task034 is not None
        and type(native_outputs.task034.pressure_drop) is ShellSidePressureDropResult
        and task034_total is not None
        else None
    )
    fiv_missing = request.fiv_array_specific_critical_velocity_limit_m_s is None
    additive_event_count = sum(
        item.allocation_role == "ADDITIVE_PRESSURE_REGION"
        for item in request.bell_event_region_allocations
    )
    support_event_count = sum(
        item.allocation_role == "CORRECTION_OR_GEOMETRY_SUPPORT"
        for item in request.bell_event_region_allocations
    )
    success_projection = {
        "request_hash": request_hash,
        "task029_result_id": task029.result_id,
        "task029_result_hash": task029.result_hash,
        "task166_result_id": task166.result_id,
        "task166_result_hash": task166.result_hash,
        "modeled_total_tube_side_pressure_drop_pa": str(
            task029.modeled_total_tube_side_pressure_drop_pa
        ),
        "bell_total_shell_pressure_drop_pa": str(task166.total_shell_pressure_drop),
        "bell_central_crossflow_contribution_pa": str(task166.central_crossflow_contribution),
        "bell_window_contribution_pa": str(task166.window_contribution),
        "bell_inlet_end_zone_contribution_pa": str(task166.entrance_zone_contribution),
        "bell_outlet_end_zone_contribution_pa": str(task166.exit_zone_contribution),
        "task034_screening_result_id": None if task034_result is None else task034_result.result_id,
        "task034_screening_result_hash": None
        if task034_result is None
        else task034_result.result_hash,
        "kern_screening_pressure_drop_pa": (
            None
            if task034_result is None
            else str(task034_result.modeled_shell_side_pressure_drop_pa)
        ),
        "tube_outlet_pressure_pa": str(tube_outlet_pressure),
        "shell_outlet_pressure_pa": str(shell_outlet_pressure),
        "bell_physical_event_count": len(request.physical_events),
        "event_multiplicity_sum": sum(event.multiplicity for event in request.physical_events),
        "bell_additive_event_count": additive_event_count,
        "bell_support_event_count": support_event_count,
        "pressure_coupling_authority_id": request.pressure_coupling_authority_id,
        "fiv_status": "WARN_MISSING_NUMERIC_LIMIT" if fiv_missing else "DIAGNOSTIC_ONLY",
        "fiv_numeric_limit_authority_missing": fiv_missing,
        "fiv_numeric_limit_not_guessed": True,
    }
    result_hash = canonical_sha256(
        {
            "schema_version": "task174.case-hydraulic-orchestration-result.v2",
            **success_projection,
        }
    )
    return Task174SuccessResult(
        status="VALIDATED",
        request_hash=request_hash,
        task029_result_id=task029.result_id,
        task029_result_hash=task029.result_hash,
        task166_result_id=task166.result_id,
        task166_result_hash=task166.result_hash,
        modeled_total_tube_side_pressure_drop_pa=task029.modeled_total_tube_side_pressure_drop_pa,
        bell_total_shell_pressure_drop_pa=task166.total_shell_pressure_drop,
        bell_central_crossflow_contribution_pa=task166.central_crossflow_contribution,
        bell_window_contribution_pa=task166.window_contribution,
        bell_inlet_end_zone_contribution_pa=task166.entrance_zone_contribution,
        bell_outlet_end_zone_contribution_pa=task166.exit_zone_contribution,
        task034_screening_result_id=None if task034_result is None else task034_result.result_id,
        task034_screening_result_hash=None
        if task034_result is None
        else task034_result.result_hash,
        kern_screening_pressure_drop_pa=(
            None if task034_result is None else task034_result.modeled_shell_side_pressure_drop_pa
        ),
        tube_outlet_pressure_pa=tube_outlet_pressure,
        shell_outlet_pressure_pa=shell_outlet_pressure,
        bell_physical_event_count=len(request.physical_events),
        event_multiplicity_sum=sum(event.multiplicity for event in request.physical_events),
        bell_additive_event_count=additive_event_count,
        bell_support_event_count=support_event_count,
        pressure_coupling_authority_id=request.pressure_coupling_authority_id,
        fiv_status="WARN_MISSING_NUMERIC_LIMIT" if fiv_missing else "DIAGNOSTIC_ONLY",
        fiv_numeric_limit_authority_missing=fiv_missing,
        fiv_numeric_limit_not_guessed=True,
        result_hash=result_hash,
        result_id=f"urn:hxforge:task174:{result_hash}",
    )


__all__ = [
    "Task174NativeOutputs",
    "Task174Outcome",
    "recompute_task174_result_hash",
    "validate_request",
]
