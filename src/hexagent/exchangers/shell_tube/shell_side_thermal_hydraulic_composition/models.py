"""Immutable public models for the TASK-035 composition boundary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, TypeAlias

from .schema import (
    APPLICABILITY_PROFILE_ID,
    BLOCKED_RESULT_SCHEMA_VERSION,
    COMPLETENESS_PROFILE_ID,
    DEFERRED_CAPABILITIES,
    FIRST_SLICE_PROFILE_ID,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
)


class ValidationStatus(StrEnum):
    """Public TASK-035 validation status."""

    VALID = "VALID"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class BlockerEntry:
    """A deterministic TASK-035 blocker record."""

    code: str
    stage: str
    field_path: str | None = None
    message_key: str = ""
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class WarningEntry:
    """A deterministic TASK-035 warning record."""

    code: str
    field_path: str | None = None
    message_key: str = ""


ProducerEvidence: TypeAlias = Any
LedgerProjection: TypeAlias = tuple[tuple[str, Any], ...]
ProvenanceProjection: TypeAlias = tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class Task035Request:
    """The exact seven-field typed TASK-035 request."""

    schema_version: str
    profile_id: str
    task031_result: ProducerEvidence
    task032_result: ProducerEvidence
    task033_result: ProducerEvidence
    task034_result: ProducerEvidence
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Task035SuccessResult:
    """The exact 41-field successful composition projection."""

    schema_version: str
    profile_id: str
    first_slice_profile_id: str
    implementation_software_version: str
    shell_side_case_id: str
    shell_side_stream_id: str
    shell_side_fluid_id: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task021_layout_id: str
    task021_layout_hash: str
    task024_geometry_id: str
    task024_geometry_hash: str
    task031_request_hash: str
    task031_geometry_id: str
    task031_geometry_hash: str
    task032_request_hash: str
    task032_result_hash: str
    task032_result_id: str
    task033_request_hash: str
    task033_result_hash: str
    task033_result_id: str
    task034_request_hash: str
    task034_result_hash: str
    task034_result_id: str
    property_snapshot_hash: str
    mass_flow_authority_hash: str
    task033_correlation_id: str
    task034_correlation_id: str
    heat_transfer_surface: str
    modeled_shell_side_heat_transfer_coefficient_w_m2_k: Decimal
    modeled_shell_side_pressure_drop_pa: Decimal
    applicability_ledger: LedgerProjection
    completeness_ledger: LedgerProjection
    request_hash: str
    result_hash: str
    result_id: str
    warnings: tuple[str, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: ProvenanceProjection


@dataclass(frozen=True)
class Task035TypedBlockedResult:
    """The exact 25-field typed blocked projection."""

    schema_version: str
    profile_id: str
    implementation_software_version: str
    failure_stage: str
    shell_side_case_id: str | None
    shell_side_stream_id: str | None
    shell_side_fluid_id: str | None
    task031_geometry_id: str | None
    task031_geometry_hash: str | None
    task032_request_hash: str | None
    task032_result_hash: str | None
    task032_result_id: str | None
    task033_result_hash: str | None
    task033_result_id: str | None
    task034_result_hash: str | None
    task034_result_id: str | None
    property_snapshot_hash: str | None
    mass_flow_authority_hash: str | None
    request_hash: str | None
    blocked_result_hash: str
    result_id: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: ProvenanceProjection


@dataclass(frozen=True)
class Task035RawBoundaryBlockedResult:
    """The exact eight-field raw-boundary blocked projection."""

    schema_version: str
    profile_id: str
    implementation_software_version: str
    raw_request_projection: Any
    blocked_result_hash: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class Task035ValidationResult:
    """Public result wrapper with mutually exclusive payload branches."""

    status: ValidationStatus
    success_result: Task035SuccessResult | None
    blocked_result: Task035TypedBlockedResult | None
    raw_boundary_blocked_result: Task035RawBoundaryBlockedResult | None

    @property
    def result(
        self,
    ) -> Task035SuccessResult | Task035TypedBlockedResult | Task035RawBoundaryBlockedResult | None:
        """Return the selected public payload branch."""

        return self.success_result or self.blocked_result or self.raw_boundary_blocked_result

    @property
    def typed_blocked_result(self) -> Task035TypedBlockedResult | None:
        """Compatibility alias for the typed blocked branch."""

        return self.blocked_result

    @property
    def warnings(self) -> tuple[Any, ...]:
        result = self.result
        return () if result is None else result.warnings

    @property
    def blockers(self) -> tuple[BlockerEntry, ...]:
        result = self.result
        return () if result is None else result.blockers


# Public identity aliases make the schema vocabulary available without adding
# alternative runtime shapes.
Task035Result = Task035SuccessResult
Task035BlockedResult = Task035TypedBlockedResult
Task035RawBlockedResult = Task035RawBoundaryBlockedResult


__all__ = [
    "APPLICABILITY_PROFILE_ID",
    "BLOCKED_RESULT_SCHEMA_VERSION",
    "BlockerEntry",
    "COMPLETENESS_PROFILE_ID",
    "DEFERRED_CAPABILITIES",
    "FIRST_SLICE_PROFILE_ID",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "LedgerProjection",
    "PROFILE_ID",
    "ProducerEvidence",
    "ProvenanceProjection",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "Task035BlockedResult",
    "Task035RawBlockedResult",
    "Task035RawBoundaryBlockedResult",
    "Task035Request",
    "Task035Result",
    "Task035SuccessResult",
    "Task035TypedBlockedResult",
    "Task035ValidationResult",
    "ValidationStatus",
    "WarningEntry",
]
