"""TASK-029 typed request construction.

I13G: ``build_task029_request`` factory using I13A request hash primitive.
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    Task027SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    TASK029_REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_request_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029Request,
    TubeSidePressurePathCompositionAuthority,
)


def build_task029_request(
    *,
    profile_id: str,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
    composition_authority: TubeSidePressurePathCompositionAuthority,
) -> Task029Request:
    """Construct a frozen Task029Request with computed request_hash."""
    request_hash = compute_request_hash(
        schema_version=TASK029_REQUEST_SCHEMA_VERSION,
        profile_id=profile_id,
        task027_result_hash=task027_success_result.result_hash,
        task028_result_hash=task028_success_result.result_hash,
        task025_hydraulic_authority_hash=task027_success_result.task025_hydraulic_authority_hash,
        task025_result_hash=task027_success_result.task025_result_hash,
        task026_result_hash=task027_success_result.task026_result_hash,
        property_snapshot_hash=task027_success_result.property_snapshot_hash,
        composition_authority_hash=composition_authority.composition_authority_hash,
    )
    return Task029Request(
        schema_version=TASK029_REQUEST_SCHEMA_VERSION,
        profile_id=profile_id,
        task027_success_result=task027_success_result,
        task028_success_result=task028_success_result,
        composition_authority=composition_authority,
        request_hash=request_hash,
    )


__all__ = [
    "build_task029_request",
]
