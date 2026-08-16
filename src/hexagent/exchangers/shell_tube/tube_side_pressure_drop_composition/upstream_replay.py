"""TASK-029 upstream production replay adapters for TASK-027 and TASK-028.

I05 scope only: exact-type gates, schema safety, and production hash/UUID replay.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    Task027SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    compute_result_hash as task027_compute_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    derive_result_id as task027_derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    canonicalize_component_result,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.identity import (
    compute_result_id as task028_compute_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.identity import (
    compute_success_result_hash as task028_compute_success_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    TubeSideLocalLossComponentResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    TASK027_ACCEPTED_SCHEMA_VERSION,
    TASK028_ACCEPTED_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
)


@dataclass(frozen=True)
class Task027ReplayEvidence:
    """Package-internal trusted replay evidence from TASK-027 production identity."""

    result_hash: str
    result_id: str
    straight_tube_friction_pressure_drop_pa: Decimal
    profile_id: str
    task025_hydraulic_authority_hash: str
    task025_result_hash: str
    task026_result_hash: str
    property_snapshot_hash: str


@dataclass(frozen=True)
class Task028ReplayEvidence:
    """Package-internal trusted replay evidence from TASK-028 production identity."""

    result_hash: str
    result_id: str
    profile_id: str
    task025_hydraulic_authority_hash: str
    task025_result_hash: str
    task026_result_hash: str
    property_snapshot_hash: str
    component_results: tuple[TubeSideLocalLossComponentResult, ...]
    components_by_id: dict[str, TubeSideLocalLossComponentResult]


def _blocker(code: Task029BlockerCode, field_path: str) -> Task029BlockerEntry:
    return Task029BlockerEntry(
        code=code,
        field_path=field_path,
        message_key=code.value,
        evidence_refs=(),
    )


def _task027_decimal_field(value: Decimal) -> str:
    return str(value)


def _canonicalize_task028_component_records(
    component_results: tuple[TubeSideLocalLossComponentResult, ...],
) -> tuple[bytes, ...]:
    records: list[bytes] = []
    for component in component_results:
        record_bytes, _component_hash = canonicalize_component_result(
            component_id=component.component_id,
            component_type=component.component_type.value,
            path_sequence_index=component.path_sequence_index,
            upstream_reference_plane=component.upstream_reference_plane,
            downstream_reference_plane=component.downstream_reference_plane,
            flow_direction_assertion=component.flow_direction_assertion.value,
            authority_hash=component.authority_hash,
            reference_flow_area_m2=component.reference_flow_area_m2,
            reference_velocity_m_s=component.reference_velocity_m_s,
            loss_coefficient=component.loss_coefficient,
            loss_coefficient_convention=component.loss_coefficient_convention.value,
            multiplicity=component.multiplicity,
            single_occurrence_irreversible_pressure_loss_pa=(
                component.single_occurrence_irreversible_pressure_loss_pa
            ),
            component_irreversible_pressure_loss_pa=component.component_irreversible_pressure_loss_pa,
        )
        records.append(record_bytes)
    return tuple(records)


def _build_task028_components_by_id(
    component_results: tuple[TubeSideLocalLossComponentResult, ...],
) -> dict[str, TubeSideLocalLossComponentResult]:
    components_by_id: dict[str, TubeSideLocalLossComponentResult] = {}
    for component in component_results:
        components_by_id[component.component_id] = component
    return components_by_id


def replay_task027_success(result: object) -> Task027ReplayEvidence | Task029BlockerEntry:
    """Replay TASK-027 production result hash and UUID; return trusted evidence."""
    if type(result) is not Task027SuccessResult:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPE_INVALID,
            "task027_success_result",
        )

    if result.schema_version != TASK027_ACCEPTED_SCHEMA_VERSION:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED,
            "task027_success_result.schema_version",
        )

    replayed_result_hash = task027_compute_result_hash(
        schema_version=result.schema_version,
        profile_id=result.profile_id,
        request_hash=result.request_hash,
        darcy_friction_factor=_task027_decimal_field(result.darcy_friction_factor),
        friction_length_m=_task027_decimal_field(result.friction_length_m),
        upstream_reference_plane=result.upstream_reference_plane,
        downstream_reference_plane=result.downstream_reference_plane,
        straight_tube_friction_pressure_drop_pa=_task027_decimal_field(
            result.straight_tube_friction_pressure_drop_pa
        ),
        task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
        task025_result_hash=result.task025_result_hash,
        task026_result_hash=result.task026_result_hash,
        property_snapshot_hash=result.property_snapshot_hash,
    )
    replayed_result_id = task027_derive_result_id(replayed_result_hash)

    if replayed_result_hash != result.result_hash or replayed_result_id != result.result_id:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID,
            "task027_success_result.result_hash",
        )

    return Task027ReplayEvidence(
        result_hash=result.result_hash,
        result_id=result.result_id,
        straight_tube_friction_pressure_drop_pa=result.straight_tube_friction_pressure_drop_pa,
        profile_id=result.profile_id,
        task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
        task025_result_hash=result.task025_result_hash,
        task026_result_hash=result.task026_result_hash,
        property_snapshot_hash=result.property_snapshot_hash,
    )


def replay_task028_success(result: object) -> Task028ReplayEvidence | Task029BlockerEntry:
    """Replay TASK-028 production result hash and UUID; return trusted evidence."""
    if type(result) is not Task028SuccessResult:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPE_INVALID,
            "task028_success_result",
        )

    if result.schema_version != TASK028_ACCEPTED_SCHEMA_VERSION:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED,
            "task028_success_result.schema_version",
        )

    if type(result.component_results) is not tuple or len(result.component_results) == 0:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID,
            "task028_success_result.result_hash",
        )

    component_result_records = _canonicalize_task028_component_records(result.component_results)
    replayed_result_hash = task028_compute_success_result_hash(
        schema_version=result.schema_version,
        profile_id=result.profile_id,
        request_hash=result.request_hash,
        task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
        task025_result_hash=result.task025_result_hash,
        task026_result_hash=result.task026_result_hash,
        property_snapshot_hash=result.property_snapshot_hash,
        component_result_records=component_result_records,
        warnings=result.warnings,
        blockers=result.blockers,
        deferred_capabilities=result.deferred_capabilities,
        provenance=result.provenance,
    )
    replayed_result_id = task028_compute_result_id(replayed_result_hash)

    if replayed_result_hash != result.result_hash or replayed_result_id != result.result_id:
        return _blocker(
            Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID,
            "task028_success_result.result_hash",
        )

    return Task028ReplayEvidence(
        result_hash=result.result_hash,
        result_id=result.result_id,
        profile_id=result.profile_id,
        task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
        task025_result_hash=result.task025_result_hash,
        task026_result_hash=result.task026_result_hash,
        property_snapshot_hash=result.property_snapshot_hash,
        component_results=result.component_results,
        components_by_id=_build_task028_components_by_id(result.component_results),
    )


__all__ = [
    "Task027ReplayEvidence",
    "Task028ReplayEvidence",
    "replay_task027_success",
    "replay_task028_success",
]
