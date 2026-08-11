"""Task028Provenance (5-field), Task028SuccessResult (14-field), Task028BlockedResult (15-field),
Task028RawBoundaryBlockedResult (6-field), build factories.

§13, §14, §15 — Result contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
    Task028BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    IMPLEMENTATION_SOFTWARE_VERSION,
    TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
    TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
    TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
    canonicalize_component_result,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.identity import (
    compute_blocked_result_hash,
    compute_result_id,
    compute_success_result_hash,
)

# §26 — Frozen field counts
SUCCESS_RESULT_FIELD_COUNT: Final[int] = 14
BLOCKED_RESULT_FIELD_COUNT: Final[int] = 15
RAW_BOUNDARY_BLOCKED_FIELD_COUNT: Final[int] = 6
PROVENANCE_FIELD_COUNT: Final[int] = 5
BLOCKER_ENTRY_FIELD_COUNT: Final[int] = 4


# §17 — Provenance
@dataclass(frozen=True)
class Task028Provenance:
    """§17.1 — TASK-028 provenance (5-field)."""

    task_id: str  # "TASK-028"
    design_contract_path: str
    implementation_software_version: str
    input_evidence_refs: tuple[str, ...]
    upstream_identity_hashes: tuple[str, ...]


# §15 — Success result (14 fields)
@dataclass(frozen=True)
class Task028SuccessResult:
    """§15 — TASK-028 success result (14 fields)."""

    schema_version: str
    profile_id: str
    request_hash: str
    result_hash: str
    result_id: str
    task025_hydraulic_authority_hash: str
    task025_result_hash: str
    task026_result_hash: str
    property_snapshot_hash: str
    component_results: tuple[Any, ...]  # TubeSideLocalLossComponentResult
    warnings: tuple[str, ...]
    blockers: tuple[Task028BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task028Provenance

    def __post_init__(self) -> None:
        if self.schema_version != TASK028_SUCCESS_RESULT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{TASK028_SUCCESS_RESULT_SCHEMA_VERSION}'")
        if self.blockers != ():
            raise ValueError("success result blockers must be empty")


# §15 — Blocked result (15 fields)
@dataclass(frozen=True)
class Task028BlockedResult:
    """§15 — TASK-028 blocked result (15 fields)."""

    schema_version: str
    profile_id: str
    implementation_software_version: str
    request_hash: str
    result_hash: str
    result_id: str
    task025_hydraulic_authority_hash: str | None
    task026_result_hash: str | None
    property_snapshot_hash: str | None
    raw_request_projection: Any  # Task028RawProjection | None
    raw_upstream_blocked_projection: Any  # Task028RawProjection | None
    warnings: tuple[str, ...]
    blockers: tuple[Task028BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task028Provenance | None

    def __post_init__(self) -> None:
        if self.schema_version != TASK028_BLOCKED_RESULT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{TASK028_BLOCKED_RESULT_SCHEMA_VERSION}'")
        if len(self.blockers) == 0:
            raise ValueError("blocked result must have non-empty blockers")


# §15 — Raw boundary blocked result (6 fields)
@dataclass(frozen=True)
class Task028RawBoundaryBlockedResult:
    """§15 — TASK-028 raw boundary blocked result (6 fields)."""

    schema_version: str
    implementation_software_version: str
    raw_request_projection: Any  # Task028RawProjection
    blockers: tuple[Task028BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be '{TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION}'"
            )
        if len(self.blockers) == 0:
            raise ValueError("raw boundary blocked result must have non-empty blockers")


def build_success_result(
    *,
    profile_id: str,
    request_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    component_results: tuple[Any, ...],
    warnings: tuple[str, ...],
    blockers: tuple[Task028BlockerEntry, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Task028Provenance,
) -> Task028SuccessResult:
    """Build a frozen Task028SuccessResult with computed hash and ID."""
    # §15 — Canonical component result hashes (computed directly from each record)
    component_result_hashes = tuple(
        canonicalize_component_result(
            component_id=cr.component_id,
            component_type=cr.component_type.value
            if hasattr(cr.component_type, "value")
            else str(cr.component_type),
            path_sequence_index=cr.path_sequence_index,
            upstream_reference_plane=cr.upstream_reference_plane,
            downstream_reference_plane=cr.downstream_reference_plane,
            flow_direction_assertion=cr.flow_direction_assertion.value
            if hasattr(cr.flow_direction_assertion, "value")
            else str(cr.flow_direction_assertion),
            authority_hash=cr.authority_hash,
            reference_flow_area_m2=str(cr.reference_flow_area_m2),
            reference_velocity_m_s=str(cr.reference_velocity_m_s),
            loss_coefficient=str(cr.loss_coefficient),
            loss_coefficient_convention=cr.loss_coefficient_convention.value
            if hasattr(cr.loss_coefficient_convention, "value")
            else str(cr.loss_coefficient_convention),
            multiplicity=cr.multiplicity,
            single_occurrence_irreversible_pressure_loss_pa=str(
                cr.single_occurrence_irreversible_pressure_loss_pa
            ),
            component_irreversible_pressure_loss_pa=str(cr.component_irreversible_pressure_loss_pa),
        )
        for cr in component_results
    )

    result_hash = compute_success_result_hash(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id=profile_id,
        request_hash=request_hash,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task025_result_hash=task025_result_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        component_result_hashes=component_result_hashes,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=deferred_capabilities,
        provenance=provenance,
    )
    result_id = compute_result_id(result_hash)
    return Task028SuccessResult(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id=profile_id,
        request_hash=request_hash,
        result_hash=result_hash,
        result_id=result_id,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task025_result_hash=task025_result_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        component_results=component_results,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=deferred_capabilities,
        provenance=provenance,
    )


def build_blocked_result(
    *,
    profile_id: str,
    request_hash: str | None,
    task025_hydraulic_authority_hash: str | None,
    task026_result_hash: str | None,
    property_snapshot_hash: str | None,
    raw_request_projection: Any,
    raw_upstream_blocked_projection: Any,
    warnings: tuple[str, ...],
    blockers: tuple[Task028BlockerEntry, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Task028Provenance | None,
) -> Task028BlockedResult:
    """Build a frozen Task028BlockedResult with computed hash and ID."""
    result_hash = compute_blocked_result_hash(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=profile_id,
        request_hash=request_hash or "",
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash or "",
        task026_result_hash=task026_result_hash or "",
        property_snapshot_hash=property_snapshot_hash or "",
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=raw_upstream_blocked_projection,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=deferred_capabilities,
        provenance=provenance,
    )
    result_id = compute_result_id(result_hash)
    return Task028BlockedResult(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id=profile_id,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        request_hash=request_hash or "",
        result_hash=result_hash,
        result_id=result_id,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=raw_upstream_blocked_projection,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=deferred_capabilities,
        provenance=provenance,
    )


def build_raw_boundary_blocked_result(
    *,
    raw_request_projection: Any,
    blockers: tuple[Task028BlockerEntry, ...],
) -> Task028RawBoundaryBlockedResult:
    """Build a frozen Task028RawBoundaryBlockedResult."""
    return Task028RawBoundaryBlockedResult(
        schema_version=TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=raw_request_projection,
        blockers=blockers,
        warnings=(),
        deferred_capabilities=(),
    )


__all__ = [
    "Task028Provenance",
    "Task028SuccessResult",
    "Task028BlockedResult",
    "Task028RawBoundaryBlockedResult",
    "SUCCESS_RESULT_FIELD_COUNT",
    "BLOCKED_RESULT_FIELD_COUNT",
    "RAW_BOUNDARY_BLOCKED_FIELD_COUNT",
    "PROVENANCE_FIELD_COUNT",
    "BLOCKER_ENTRY_FIELD_COUNT",
    "build_success_result",
    "build_blocked_result",
    "build_raw_boundary_blocked_result",
]
