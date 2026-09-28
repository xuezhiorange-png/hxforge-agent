"""TASK174 fail-closed orchestration across existing hydraulic producers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware import canonical as task166_canonical
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
    bell_ids = {binding.physical_event_id for binding in request.bell_event_pressure_bindings}
    if event_ids != bell_ids or len(bell_ids) != len(request.bell_event_pressure_bindings):
        return False
    by_event = {event.physical_event_id: event for event in request.physical_events}
    for binding in request.bell_event_pressure_bindings:
        event = by_event[binding.physical_event_id]
        if (
            binding.task166_result_hash != task166.result_hash
            or binding.multiplicity != event.multiplicity
            or binding.multiplicity != 1
            or binding.modeled_pressure_drop_pa is None
        ):
            return False
    return True


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
) -> Task174BlockedResult:
    evidence = {
        "schema_version": "task174.case-hydraulic-orchestration-blocked.v1",
        "request_hash": request_hash,
        "blockers": [item.model_dump(mode="json") for item in blockers],
        "fiv_mode": "DIAGNOSTIC_SCREENING_ONLY",
        "fiv_numeric_limit_authority_missing": fiv_limit_missing,
        "fiv_numeric_limit_not_guessed": True,
    }
    return Task174BlockedResult(
        status="BLOCKED",
        request_hash=request_hash,
        tube_pressure_drop_status="BLOCKED_INCOMPLETE_MODELED_BOUNDARY",
        shell_pressure_drop_status="BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION",
        bell_aggregation_status="BLOCKED_EVENT_TO_REGION_MAPPING",
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
            "schema_version": "task174.case-hydraulic-orchestration-blocked.v1",
            "request_hash": result.request_hash,
            "blockers": [item.model_dump(mode="json") for item in result.blockers],
            "fiv_mode": "DIAGNOSTIC_SCREENING_ONLY",
            "fiv_numeric_limit_authority_missing": result.fiv_numeric_limit_authority_missing,
            "fiv_numeric_limit_not_guessed": result.fiv_numeric_limit_not_guessed,
        }
    elif type(result) is Task174SuccessResult:
        projection = {
            "schema_version": "task174.case-hydraulic-orchestration-result.v1",
            "request_hash": result.request_hash,
            "task029_result_id": result.task029_result_id,
            "task029_result_hash": result.task029_result_hash,
            "task034_result_id": result.task034_result_id,
            "task034_result_hash": result.task034_result_hash,
            "tube_modeled_pressure_drop_pa": str(result.tube_modeled_pressure_drop_pa),
            "shell_modeled_pressure_drop_pa": str(result.shell_modeled_pressure_drop_pa),
            "bell_physical_event_count": result.bell_physical_event_count,
            "event_multiplicity_sum": result.event_multiplicity_sum,
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

    task034_total = _task034_total(native_outputs.task034, native_outputs.task166)
    if task034_total is None or not _native_event_ledger_valid(request, native_outputs.task166):
        missing_shell: list[str] = []
        if task034_total is None:
            missing_shell.append("valid native TASK034 complete shell pressure-drop result")
        if not _native_event_ledger_valid(request, native_outputs.task166):
            missing_shell.append(
                "one-to-one source-bound TASK171 physical-event to Bell-region allocation"
            )
        if request.event_to_bell_region_authority_id == "UNBOUND":
            missing_shell.append(
                "reviewed TASK171-event to Bell pressure-region allocation authority"
            )
        blockers.append(
            Task174Blocker(
                code="SHELL_DP_BLOCKED_PHYSICAL_EVENT_AND_PRESSURE_STATE_BINDING",
                scope="SHELL_SIDE_TASK034_BELL_AGGREGATION",
                missing_bindings=tuple(missing_shell),
                consumer=(
                    "TASK034/TASK166 physical-event aggregation; every physical event "
                    "must be allocated once"
                ),
            )
        )

    if (
        request.pressure_coupling_authority_id == "UNBOUND"
        or not request.pressure_property_bindings
    ):
        blockers.append(
            Task174Blocker(
                code="BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY",
                scope="CASE_PRESSURE_PATH",
                missing_bindings=(
                    "reviewed pressure-state coupling authority",
                    "exact support/location pressure-state and property-snapshot bindings",
                ),
                consumer=(
                    "TASK172 property provider + TASK027/TASK034 pressure-dependent state inputs"
                ),
            )
        )

    if blockers:
        return _blocker_result(
            request_hash,
            tuple(blockers),
            request.fiv_array_specific_critical_velocity_limit_m_s is None,
        )

    task029 = cast(Task029SuccessResult, native_outputs.task029)
    task034_validation = native_outputs.task034
    if (
        task034_validation is None
        or type(task034_validation.pressure_drop) is not ShellSidePressureDropResult
    ):
        raise RuntimeError("complete TASK034 result disappeared after blocker evaluation")
    task034 = task034_validation.pressure_drop
    fiv_missing = request.fiv_array_specific_critical_velocity_limit_m_s is None
    success_projection = {
        "request_hash": request_hash,
        "task029_result_id": task029.result_id,
        "task029_result_hash": task029.result_hash,
        "task034_result_id": task034.result_id,
        "task034_result_hash": task034.result_hash,
        "tube_modeled_pressure_drop_pa": str(task029.modeled_total_tube_side_pressure_drop_pa),
        "shell_modeled_pressure_drop_pa": str(task034.modeled_shell_side_pressure_drop_pa),
        "bell_physical_event_count": len(request.physical_events),
        "event_multiplicity_sum": sum(event.multiplicity for event in request.physical_events),
        "fiv_status": "WARN_MISSING_NUMERIC_LIMIT" if fiv_missing else "DIAGNOSTIC_ONLY",
        "fiv_numeric_limit_authority_missing": fiv_missing,
        "fiv_numeric_limit_not_guessed": True,
    }
    result_hash = canonical_sha256(
        {
            "schema_version": "task174.case-hydraulic-orchestration-result.v1",
            **success_projection,
        }
    )
    return Task174SuccessResult(
        status="VALIDATED",
        request_hash=request_hash,
        task029_result_id=task029.result_id,
        task029_result_hash=task029.result_hash,
        task034_result_id=task034.result_id,
        task034_result_hash=task034.result_hash,
        tube_modeled_pressure_drop_pa=task029.modeled_total_tube_side_pressure_drop_pa,
        shell_modeled_pressure_drop_pa=task034.modeled_shell_side_pressure_drop_pa,
        bell_physical_event_count=len(request.physical_events),
        event_multiplicity_sum=sum(event.multiplicity for event in request.physical_events),
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
