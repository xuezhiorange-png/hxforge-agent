"""Immutable public value models for TASK-038."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeAlias, cast
from uuid import UUID

from .raw_projection import FrozenRawProjection
from .schema import (
    APPLICABILITY_ROWS,
    COMPLETENESS_ROWS,
    DEFERRED_CAPABILITIES,
    DESIGN_REVISION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    SUCCESS_RESULT_SCHEMA_VERSION,
    TASK038_VERSION,
    TYPED_BLOCKED_RESULT_SCHEMA_VERSION,
)

_HEX = frozenset("0123456789abcdef")


def _text(value: object, field: str, *, allow_none: bool = False) -> str | None:
    if allow_none and value is None:
        return None
    if type(value) is not str or not value:
        raise ValueError(f"{field} must be a non-empty str")
    return value


def _hash(value: object, field: str, *, allow_none: bool = False) -> str | None:
    if allow_none and value is None:
        return None
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise ValueError(f"{field} must be lowercase 64-character SHA-256 hex")
    return value


def _strings(value: object, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) not in {tuple, list}:
        raise ValueError(f"{field} must be tuple/list of strings")
    values: tuple[object, ...] = tuple(cast(Iterable[object], value))
    if not allow_empty and not values:
        raise ValueError(f"{field} must not be empty")
    for item in values:
        _text(item, f"{field} entry")
    return tuple(cast(str, item) for item in values)


@dataclass(frozen=True)
class BlockerEntry:
    code: str
    stage: str
    field_path: str | None = None
    message_key: str = ""
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _text(self.code, "blocker.code")
        _text(self.stage, "blocker.stage")
        _text(self.field_path, "blocker.field_path", allow_none=True)
        if type(self.message_key) is not str:
            raise ValueError("blocker.message_key must be str")
        if type(self.details) not in {tuple, list}:
            raise ValueError("blocker.details must be a tuple of records")
        normalized: list[tuple[str, str]] = []
        for detail in self.details:
            if not isinstance(detail, (tuple, list)) or len(detail) != 2:
                raise ValueError("blocker detail must be a key/value pair")
            _text(detail[0], "blocker.details.key")
            if type(detail[1]) is not str:
                raise ValueError("blocker.details.value must be str")
            normalized.append((detail[0], detail[1]))
        object.__setattr__(self, "details", tuple(normalized))


@dataclass(frozen=True)
class WarningEntry:
    code: str
    field_path: str | None = None
    message_key: str = ""

    def __post_init__(self) -> None:
        _text(self.code, "warning.code")
        _text(self.field_path, "warning.field_path", allow_none=True)
        if type(self.message_key) is not str:
            raise ValueError("warning.message_key must be str")


@dataclass(frozen=True)
class ProducerIdentityEnvelope:
    producer_task_id: str
    branch: str
    native_result_id: str | None
    native_result_hash: str | None
    producer_evidence_hash: str

    def __post_init__(self) -> None:
        if self.producer_task_id not in {"TASK025", "TASK026", "TASK035", "TASK037"}:
            raise ValueError("producer_task_id is not an allowed direct producer")
        if self.branch not in {"SUCCESS", "TYPED_BLOCKED", "RAW_BOUNDARY_BLOCKED"}:
            raise ValueError("producer branch is not frozen")
        _text(self.native_result_id, "native_result_id", allow_none=True)
        _hash(self.native_result_hash, "native_result_hash", allow_none=True)
        _hash(self.producer_evidence_hash, "producer_evidence_hash")
        if self.branch == "SUCCESS" and (
            self.native_result_id is None or self.native_result_hash is None
        ):
            raise ValueError("success envelope requires native result identity")


@dataclass(frozen=True)
class TubeSideServiceBindingAuthority:
    authority_id: str
    tube_side_fluid_service_id: str
    task026_result_hash: str
    task026_property_snapshot_hash: str
    source_id: str
    source_version: str
    source_location: str
    source_class: str
    permission_status: str
    approval_status: str
    evidence_refs: tuple[str, ...]
    authority_hash: str

    def __post_init__(self) -> None:
        for name in (
            "authority_id",
            "tube_side_fluid_service_id",
            "source_id",
            "source_version",
            "source_location",
            "source_class",
            "permission_status",
            "approval_status",
        ):
            _text(getattr(self, name), f"service_binding.{name}")
        _hash(self.task026_result_hash, "service_binding.task026_result_hash")
        _hash(
            self.task026_property_snapshot_hash,
            "service_binding.task026_property_snapshot_hash",
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _strings(self.evidence_refs, "service_binding.evidence_refs"),
        )
        _hash(self.authority_hash, "service_binding.authority_hash")


@dataclass(frozen=True)
class EngineeringSourceIdentity:
    source_id: str
    source_version: str
    source_class: str
    source_locations: tuple[str, ...]
    permission_status: str

    def __post_init__(self) -> None:
        for name in ("source_id", "source_version", "source_class", "permission_status"):
            _text(getattr(self, name), f"engineering_source.{name}")
        object.__setattr__(
            self,
            "source_locations",
            _strings(
                self.source_locations, "engineering_source.source_locations", allow_empty=False
            ),
        )


@dataclass(frozen=True)
class ThermalResistanceLedgerRow:
    term_id: str
    producer_owner: str
    source_field_or_projection: str
    native_reference_surface: str
    composed_reference_surface: str
    transformation_authority_hash_or_none: str | None
    value_m2_k_w: Decimal
    status: str

    def __post_init__(self) -> None:
        for name in (
            "term_id",
            "producer_owner",
            "source_field_or_projection",
            "native_reference_surface",
            "composed_reference_surface",
            "status",
        ):
            _text(getattr(self, name), f"resistance_row.{name}")
        _hash(
            self.transformation_authority_hash_or_none,
            "resistance_row.transformation_authority_hash_or_none",
            allow_none=True,
        )
        if type(self.value_m2_k_w) is not Decimal or not self.value_m2_k_w.is_finite():
            raise ValueError("resistance_row.value_m2_k_w must be finite Decimal")


@dataclass(frozen=True)
class LedgerRow:
    row_id: str
    status: str

    def __post_init__(self) -> None:
        _text(self.row_id, "ledger.row_id")
        _text(self.status, "ledger.status")


@dataclass(frozen=True)
class Task038Request:
    schema_version: str
    profile_id: str
    task025_result: Any
    task026_result: Any
    task035_result: Any
    task037_result: Any
    tube_side_service_binding_authority: TubeSideServiceBindingAuthority
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_SCHEMA_VERSION:
            raise ValueError("request schema_version is not frozen")
        if self.profile_id != PROFILE_ID:
            raise ValueError("request profile_id is not frozen")
        if type(self.tube_side_service_binding_authority) is not TubeSideServiceBindingAuthority:
            raise ValueError("service binding has wrong type")
        object.__setattr__(
            self, "evidence_refs", _strings(self.evidence_refs, "request.evidence_refs")
        )


@dataclass(frozen=True)
class Task038Provenance:
    task_id: str
    source_definition_issue: int
    source_definition_revision: str
    design_issue: int
    design_revision: str
    implementation_software_version: str
    base_main_sha: str
    base_main_tree: str
    baseline_repair_governance_comment_id: str
    request_hash: str
    task025_result_hash: str
    task025_result_id: str
    task025_hydraulic_authority_hash: str
    task026_result_hash: str
    task026_result_id: str
    task026_property_snapshot_hash: str
    task035_result_hash: str
    task035_result_id: str
    task035_shell_side_fluid_id: str
    task037_result_hash: str
    task037_result_id: str
    task037_surface_transform_authority_hash: str
    task037_inside_fouling_authority_hash: str
    task037_outside_fouling_authority_hash: str
    task037_task025_area_quantum_m2: Decimal
    task037_task025_area_rounding_mode: str
    task037_producer_area_precision_policy_id: str
    task037_producer_area_precision_policy_hash: str
    task037_producer_precision_limitation_disclosed: bool
    task037_producer_precision_threshold_defined: bool
    tube_side_service_binding_authority_hash: str
    engineering_source_identity_hashes: tuple[str, ...]
    cross_producer_compatibility_hash: str
    resistance_composition_authority_hash: str
    outer_area_projection_authority_hash: str
    ua_composition_authority_hash: str
    overall_u_reference_surface: str
    modeled_overall_heat_transfer_coefficient_w_m2_k: Decimal
    outer_tube_surface_effective_area_m2: Decimal
    modeled_ua_w_k: Decimal
    evidence_refs: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    provenance_hash: str

    def __post_init__(self) -> None:
        _text(self.task_id, "provenance.task_id")
        if type(self.source_definition_issue) is not int or type(self.design_issue) is not int:
            raise ValueError("provenance issue fields must be int")
        for name in (
            "source_definition_revision",
            "design_revision",
            "implementation_software_version",
            "base_main_sha",
            "base_main_tree",
            "baseline_repair_governance_comment_id",
            "overall_u_reference_surface",
            "task037_task025_area_rounding_mode",
            "task037_producer_area_precision_policy_id",
        ):
            _text(getattr(self, name), f"provenance.{name}")
        for name in (
            "request_hash",
            "task025_result_hash",
            "task025_hydraulic_authority_hash",
            "task026_result_hash",
            "task026_property_snapshot_hash",
            "task035_result_hash",
            "task037_result_hash",
            "task037_surface_transform_authority_hash",
            "task037_inside_fouling_authority_hash",
            "task037_outside_fouling_authority_hash",
            "task037_producer_area_precision_policy_hash",
            "tube_side_service_binding_authority_hash",
            "cross_producer_compatibility_hash",
            "resistance_composition_authority_hash",
            "outer_area_projection_authority_hash",
            "ua_composition_authority_hash",
            "provenance_hash",
        ):
            _hash(getattr(self, name), f"provenance.{name}")
        for name in (
            "task025_result_id",
            "task026_result_id",
            "task035_result_id",
            "task037_result_id",
        ):
            _text(getattr(self, name), f"provenance.{name}")
        for name in (
            "task037_task025_area_quantum_m2",
            "modeled_overall_heat_transfer_coefficient_w_m2_k",
            "outer_tube_surface_effective_area_m2",
            "modeled_ua_w_k",
        ):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise ValueError(f"provenance.{name} must be finite Decimal")
        for name in (
            "task037_producer_precision_limitation_disclosed",
            "task037_producer_precision_threshold_defined",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"provenance.{name} must be bool")
        for name in (
            "engineering_source_identity_hashes",
            "evidence_refs",
            "deferred_capabilities",
        ):
            values = _strings(getattr(self, name), f"provenance.{name}")
            object.__setattr__(self, name, values)
        if self.design_revision != DESIGN_REVISION:
            raise ValueError("provenance design revision is not R4 authority")


@dataclass(frozen=True)
class Task038SuccessResult:
    schema_version: str
    task038_version: str
    profile_id: str
    implementation_software_version: str
    request_hash: str
    overall_u_reference_surface: str
    full_thermal_resistance_composition_ledger: tuple[ThermalResistanceLedgerRow, ...]
    modeled_overall_heat_transfer_coefficient_w_m2_k: Decimal
    outer_tube_surface_effective_area_m2: Decimal
    modeled_ua_w_k: Decimal
    applicability_ledger: tuple[LedgerRow, ...]
    completeness_ledger: tuple[LedgerRow, ...]
    warnings: tuple[WarningEntry, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task038Provenance
    result_hash: str
    result_id: str

    def __post_init__(self) -> None:
        if self.schema_version != SUCCESS_RESULT_SCHEMA_VERSION:
            raise ValueError("success schema_version is not frozen")
        if self.task038_version != TASK038_VERSION or self.profile_id != PROFILE_ID:
            raise ValueError("success task/profile identity is not frozen")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError("success implementation token is not frozen")
        _hash(self.request_hash, "success.request_hash")
        _hash(self.result_hash, "success.result_hash")
        if type(self.overall_u_reference_surface) is not str:
            raise ValueError("success reference surface must be str")
        for name in (
            "modeled_overall_heat_transfer_coefficient_w_m2_k",
            "outer_tube_surface_effective_area_m2",
            "modeled_ua_w_k",
        ):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise ValueError(f"success.{name} must be finite Decimal")
        if type(self.full_thermal_resistance_composition_ledger) is not tuple:
            raise ValueError("resistance ledger must be tuple")
        if len(self.full_thermal_resistance_composition_ledger) != 5:
            raise ValueError("resistance ledger must contain five rows")
        if any(
            type(row) is not ThermalResistanceLedgerRow
            for row in self.full_thermal_resistance_composition_ledger
        ):
            raise ValueError("invalid resistance ledger row")
        for name in ("applicability_ledger", "completeness_ledger", "warnings", "blockers"):
            if type(getattr(self, name)) is not tuple:
                raise ValueError(f"success.{name} must be tuple")
        if tuple(row.row_id for row in self.applicability_ledger) != APPLICABILITY_ROWS:
            raise ValueError("applicability ledger order is not frozen")
        if tuple(row.row_id for row in self.completeness_ledger) != COMPLETENESS_ROWS:
            raise ValueError("completeness ledger order is not frozen")
        if any(
            type(row) is not LedgerRow
            for row in self.applicability_ledger + self.completeness_ledger
        ):
            raise ValueError("invalid ledger row")
        if self.warnings != () or self.blockers != ():
            raise ValueError("successful result must have empty warnings/blockers")
        if self.deferred_capabilities != DEFERRED_CAPABILITIES:
            raise ValueError("deferred capabilities are not frozen")
        if type(self.provenance) is not Task038Provenance:
            raise ValueError("success provenance has wrong type")
        try:
            result_uuid = UUID(self.result_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("result_id must be UUID text") from exc
        if result_uuid.version != 5 or result_uuid.variant != "specified in RFC 4122":
            raise ValueError("result_id must be UUIDv5")


@dataclass(frozen=True)
class Task038TypedBlockedResult:
    schema_version: str
    task038_version: str
    implementation_software_version: str
    failure_stage: str
    request_hash: str | None
    producer_result_identities: tuple[ProducerIdentityEnvelope, ...]
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[WarningEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance_or_none: Task038Provenance | None
    blocked_result_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != TYPED_BLOCKED_RESULT_SCHEMA_VERSION:
            raise ValueError("typed blocked schema is not frozen")
        if self.task038_version != TASK038_VERSION:
            raise ValueError("typed blocked task version is not frozen")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError("typed blocked implementation token is not frozen")
        _text(self.failure_stage, "typed_blocked.failure_stage")
        _hash(self.request_hash, "typed_blocked.request_hash", allow_none=True)
        if type(self.producer_result_identities) is not tuple:
            raise ValueError("producer identities must be tuple")
        if any(
            type(item) is not ProducerIdentityEnvelope for item in self.producer_result_identities
        ):
            raise ValueError("invalid producer identity envelope")
        if type(self.blockers) is not tuple or not self.blockers:
            raise ValueError("typed blocked result requires blockers")
        if any(type(item) is not BlockerEntry for item in self.blockers):
            raise ValueError("invalid typed blocker")
        if type(self.warnings) is not tuple or any(
            type(item) is not WarningEntry for item in self.warnings
        ):
            raise ValueError("invalid typed warnings")
        if self.deferred_capabilities != DEFERRED_CAPABILITIES:
            raise ValueError("deferred capabilities are not frozen")
        if (
            self.provenance_or_none is not None
            and type(self.provenance_or_none) is not Task038Provenance
        ):
            raise ValueError("invalid typed blocked provenance")
        _hash(self.blocked_result_hash, "typed_blocked.blocked_result_hash")


@dataclass(frozen=True)
class Task038RawBoundaryBlockedResult:
    schema_version: str
    task038_version: str
    implementation_software_version: str
    raw_request_projection: FrozenRawProjection
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[WarningEntry, ...]
    deferred_capabilities: tuple[str, ...]
    blocked_result_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION:
            raise ValueError("raw blocked schema is not frozen")
        if self.task038_version != TASK038_VERSION:
            raise ValueError("raw blocked task version is not frozen")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError("raw blocked implementation token is not frozen")
        if type(self.raw_request_projection) is not FrozenRawProjection:
            raise ValueError("raw projection has wrong type")
        if type(self.blockers) is not tuple or not self.blockers:
            raise ValueError("raw blocked result requires blockers")
        if any(type(item) is not BlockerEntry for item in self.blockers):
            raise ValueError("invalid raw blocker")
        if type(self.warnings) is not tuple or any(
            type(item) is not WarningEntry for item in self.warnings
        ):
            raise ValueError("invalid raw warnings")
        if self.deferred_capabilities != DEFERRED_CAPABILITIES:
            raise ValueError("deferred capabilities are not frozen")
        _hash(self.blocked_result_hash, "raw_blocked.blocked_result_hash")


@dataclass(frozen=True)
class Task038ValidationResult:
    status: str
    success_result: Task038SuccessResult | None = None
    blocked_result: Task038TypedBlockedResult | None = None
    raw_boundary_blocked_result: Task038RawBoundaryBlockedResult | None = None

    def __post_init__(self) -> None:
        if self.status not in {"VALID", "BLOCKED"}:
            raise ValueError("status must be VALID or BLOCKED")
        branches = (self.success_result, self.blocked_result, self.raw_boundary_blocked_result)
        if sum(branch is not None for branch in branches) != 1:
            raise ValueError("exactly one result branch must be populated")
        if self.status == "VALID" and self.success_result is None:
            raise ValueError("VALID requires success_result")
        if self.status == "BLOCKED" and self.success_result is not None:
            raise ValueError("BLOCKED cannot contain success result")

    @property
    def result(
        self,
    ) -> Task038SuccessResult | Task038TypedBlockedResult | Task038RawBoundaryBlockedResult:
        return self.success_result or self.blocked_result or self.raw_boundary_blocked_result  # type: ignore[return-value]

    @property
    def typed_blocked_result(self) -> Task038TypedBlockedResult | None:
        return self.blocked_result

    @property
    def warnings(self) -> tuple[Any, ...]:
        return self.result.warnings

    @property
    def blockers(self) -> tuple[Any, ...]:
        return self.result.blockers


Task038Result: TypeAlias = Task038SuccessResult
Task038BlockedResult: TypeAlias = Task038TypedBlockedResult
Task038RawBlockedResult: TypeAlias = Task038RawBoundaryBlockedResult

__all__ = [name for name in globals() if not name.startswith("_")]
