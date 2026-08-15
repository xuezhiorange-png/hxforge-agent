"""TASK-029 public composition pipeline.

I13J: sole orchestration entry ``compute_task029_composition()`` — raw boundary,
typed request transition, and validation scheduler passthrough only.
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    Task027SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    FrozenTask029RawProjection,
    Task029BlockedResult,
    Task029RawBoundaryBlockedResult,
    Task029SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.raw_boundary import (
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.validation import (
    run_validation_scheduler,
)


def compute_task029_composition(
    raw_input: object,
    *,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
    input_evidence_refs: tuple[str, ...],
    raw_upstream_blocked_projection: FrozenTask029RawProjection | None = None,
) -> Task029SuccessResult | Task029BlockedResult | Task029RawBoundaryBlockedResult:
    """Run raw boundary validation and, when typed, the T00–T12 validation scheduler."""
    boundary_result = validate_raw_boundary(
        raw_input,
        task027_success_result=task027_success_result,
        task028_success_result=task028_success_result,
    )
    if boundary_result.blocked:
        blocked_result = boundary_result.blocked_result
        if blocked_result is None:
            msg = "raw-boundary blocked path requires Task029RawBoundaryBlockedResult"
            raise ValueError(msg)
        return blocked_result

    request = boundary_result.request
    if request is None:
        msg = "raw-boundary success path requires Task029Request"
        raise ValueError(msg)

    scheduler_result = run_validation_scheduler(
        request,
        raw_request_projection=boundary_result.raw_request_projection,
        input_evidence_refs=input_evidence_refs,
        raw_upstream_blocked_projection=raw_upstream_blocked_projection,
    )
    if scheduler_result.blocked:
        typed_blocked_result = scheduler_result.blocked_result
        if typed_blocked_result is None:
            msg = "scheduler blocked path requires Task029BlockedResult"
            raise ValueError(msg)
        return typed_blocked_result

    success_result = scheduler_result.success_result
    if success_result is None:
        msg = "scheduler success path requires Task029SuccessResult"
        raise ValueError(msg)
    return success_result


__all__ = [
    "compute_task029_composition",
]
