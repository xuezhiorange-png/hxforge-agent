"""Immutable public TASK-037 request, authority and result models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeAlias
from uuid import UUID

from hexagent.exchangers.shell_tube.tube_side.provenance import (
    FrozenIdentity,
    FrozenRawProjection,
)

from .schema import (
    DEFERRED_CAPABILITIES,
    IMPLEMENTATION_SOFTWARE_VERSION,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    TASK037_VERSION,
    TYPED_BLOCKED_RESULT_SCHEMA_VERSION,
)

_HEX = frozenset("0123456789abcdef")


def _hash(value: object, field_path: str, *, allow_none: bool = False) -> str | None:
    if allow_none and value is None:
        return None
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise ValueError(f"{field_path} must be lowercase 64-character SHA-256 hex")
    return value


def _text(value: object, field_path: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{field_path} must be non-empty str")
    return value


def _strings(value: object, field_path: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_path} must be tuple/list of str")
    result = tuple(value)
    if not allow_empty and not result:
        raise ValueError(f"{field_path} must be non-empty")
    for item in result:
        if type(item) is not str or not item:
            raise ValueError(f"{field_path} entries must be non-empty str")
    return result


@dataclass(frozen=True)
class BlockerEntry:
    """Deterministically ordered blocker record."""

    code: str
    stage: str
    field_path: str | None = None
    message_key: str = ""
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _text(self.code, "blocker.code")
        _text(self.stage, "blocker.stage")
        if self.field_path is not None:
            _text(self.field_path, "blocker.field_path")
        if not isinstance(self.details, (tuple, list)):
            raise ValueError("blocker.details must contain string pairs")
        normalized: list[tuple[str, str]] = []
        for item in self.details:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError("blocker.details must contain string pairs")
            if type(item[0]) is not str or not item[0] or type(item[1]) is not str:
                raise ValueError("blocker.details must contain string pairs")
            normalized.append((item[0], item[1]))
        object.__setattr__(self, "details", tuple(normalized))


@dataclass(frozen=True)
class WarningEntry:
    """Deterministically ordered warning record."""

    code: str
    field_path: str | None = None
    message_key: str = ""

    def __post_init__(self) -> None:
        _text(self.code, "warning.code")
        if self.field_path is not None:
            _text(self.field_path, "warning.field_path")


@dataclass(frozen=True)
class TubeWallMaterialAuthority:
    authority_id: str
    material_id: str
    material_grade: str
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
            "material_id",
            "material_grade",
            "source_id",
            "source_version",
            "source_location",
            "source_class",
            "permission_status",
            "approval_status",
        ):
            _text(getattr(self, name), f"material.{name}")
        object.__setattr__(
            self,
            "evidence_refs",
            _strings(self.evidence_refs, "material.evidence_refs", allow_empty=False),
        )
        _hash(self.authority_hash, "material.authority_hash")


@dataclass(frozen=True)
class TubeWallThermalConductivityAuthority:
    authority_id: str
    material_id: str
    thermal_conductivity_w_m_k: Decimal
    evaluation_temperature_k: Decimal
    evaluation_context_id: str
    evaluation_basis: str
    applicability_authority_hash: str
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
            "material_id",
            "evaluation_context_id",
            "evaluation_basis",
            "source_id",
            "source_version",
            "source_location",
            "source_class",
            "permission_status",
            "approval_status",
        ):
            _text(getattr(self, name), f"conductivity.{name}")
        if type(self.thermal_conductivity_w_m_k) is not Decimal:
            raise ValueError("conductivity.thermal_conductivity_w_m_k must be Decimal")
        if type(self.evaluation_temperature_k) is not Decimal:
            raise ValueError("conductivity.evaluation_temperature_k must be Decimal")
        object.__setattr__(
            self,
            "evidence_refs",
            _strings(self.evidence_refs, "conductivity.evidence_refs", allow_empty=False),
        )
        _hash(self.applicability_authority_hash, "conductivity.applicability_authority_hash")
        _hash(self.authority_hash, "conductivity.authority_hash")


@dataclass(frozen=True)
class _FoulingAuthorityBase:
    authority_id: str
    side: str
    fouling_resistance_m2_k_w: Decimal
    reference_surface: str
    fluid_service_id: str
    source_id: str
    source_version: str
    source_location: str
    source_class: str
    permission_status: str
    approval_status: str
    evidence_refs: tuple[str, ...]
    authority_hash: str
    resistance_units: str = "m2_K_per_W"
    applicability: str = "EXPLICIT_APPROVED_AUTHORITY"

    def _validate_common(self, expected_side: str, expected_surface: str) -> None:
        for name in (
            "authority_id",
            "side",
            "reference_surface",
            "fluid_service_id",
            "source_id",
            "source_version",
            "source_location",
            "source_class",
            "permission_status",
            "approval_status",
            "resistance_units",
            "applicability",
        ):
            _text(getattr(self, name), f"fouling.{name}")
        if self.side != expected_side:
            raise ValueError(f"fouling.side must be {expected_side}")
        if self.reference_surface != expected_surface:
            raise ValueError(f"fouling.reference_surface must be {expected_surface}")
        if type(self.fouling_resistance_m2_k_w) is not Decimal:
            raise ValueError("fouling resistance must be Decimal")
        if not self.fouling_resistance_m2_k_w.is_finite() or self.fouling_resistance_m2_k_w < 0:
            raise ValueError("fouling resistance must be finite and non-negative")
        object.__setattr__(
            self,
            "evidence_refs",
            _strings(self.evidence_refs, "fouling.evidence_refs", allow_empty=False),
        )
        _hash(self.authority_hash, "fouling.authority_hash")

    @property
    def resistance_value_m2_k_w(self) -> Decimal:
        return self.fouling_resistance_m2_k_w


@dataclass(frozen=True)
class InsideFoulingResistanceAuthority(_FoulingAuthorityBase):
    def __post_init__(self) -> None:
        self._validate_common("INSIDE", "INNER_TUBE_SURFACE")


@dataclass(frozen=True)
class OutsideFoulingResistanceAuthority(_FoulingAuthorityBase):
    def __post_init__(self) -> None:
        self._validate_common("OUTSIDE", "OUTER_TUBE_SURFACE")


@dataclass(frozen=True)
class Task037Request:
    schema_version: str
    task037_version: str
    implementation_software_version: str
    wall_material_authority: TubeWallMaterialAuthority
    wall_thermal_conductivity_authority: TubeWallThermalConductivityAuthority
    inside_fouling_authority: InsideFoulingResistanceAuthority
    outside_fouling_authority: OutsideFoulingResistanceAuthority
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != REQUEST_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {REQUEST_SCHEMA_VERSION!r}")
        if self.task037_version != TASK037_VERSION:
            raise ValueError(f"task037_version must be {TASK037_VERSION!r}")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError(
                "implementation_software_version must be the frozen TASK037 implementation token"
            )
        if type(self.wall_material_authority) is not TubeWallMaterialAuthority:
            raise ValueError("wall_material_authority has wrong type")
        if type(self.wall_thermal_conductivity_authority) is not (
            TubeWallThermalConductivityAuthority
        ):
            raise ValueError("wall_thermal_conductivity_authority has wrong type")
        if type(self.inside_fouling_authority) is not InsideFoulingResistanceAuthority:
            raise ValueError("inside_fouling_authority has wrong type")
        if type(self.outside_fouling_authority) is not OutsideFoulingResistanceAuthority:
            raise ValueError("outside_fouling_authority has wrong type")
        object.__setattr__(
            self, "evidence_refs", _strings(self.evidence_refs, "request.evidence_refs")
        )


@dataclass(frozen=True)
class Task037Provenance:
    task_id: str
    source_definition_issue: int
    source_definition_revision: str
    source_definition_review_audit_comment: int
    design_issue: int
    design_revision: str
    implementation_software_version: str
    request_hash: str
    task021_layout_hash: str
    task025_result_hash: str
    task025_hydraulic_authority_hash: str
    tube_geometry_snapshot_hash: str
    heat_transfer_length_hash: str
    task025_internal_heat_transfer_surface_area_m2: Decimal
    task025_area_quantum_m2: Decimal
    task025_area_rounding_mode: str
    producer_area_precision_policy_id: str
    producer_area_precision_policy_hash: str
    producer_precision_limitation_disclosed: bool
    producer_precision_threshold_defined: bool
    wall_material_authority_hash: str
    wall_conductivity_authority_hash: str
    inside_fouling_authority_hash: str
    outside_fouling_authority_hash: str
    surface_transform_authority_hash: str
    wall_resistance_authority_hash: str
    source_identity_hashes: tuple[str, ...]
    producer_edges: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    provenance_hash: str

    def __post_init__(self) -> None:
        _text(self.task_id, "provenance.task_id")
        if type(self.source_definition_issue) is not int:
            raise ValueError("provenance.source_definition_issue must be int")
        _text(self.source_definition_revision, "provenance.source_definition_revision")
        if type(self.source_definition_review_audit_comment) is not int:
            raise ValueError("provenance.source_definition_review_audit_comment must be int")
        if type(self.design_issue) is not int:
            raise ValueError("provenance.design_issue must be int")
        _text(self.design_revision, "provenance.design_revision")
        _text(self.implementation_software_version, "provenance.implementation_software_version")
        for name in (
            "request_hash",
            "task021_layout_hash",
            "task025_result_hash",
            "task025_hydraulic_authority_hash",
            "tube_geometry_snapshot_hash",
            "heat_transfer_length_hash",
            "producer_area_precision_policy_hash",
            "wall_material_authority_hash",
            "wall_conductivity_authority_hash",
            "inside_fouling_authority_hash",
            "outside_fouling_authority_hash",
            "surface_transform_authority_hash",
            "wall_resistance_authority_hash",
            "provenance_hash",
        ):
            _hash(getattr(self, name), f"provenance.{name}")
        for name in ("task025_internal_heat_transfer_surface_area_m2", "task025_area_quantum_m2"):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise ValueError(f"provenance.{name} must be finite Decimal")
        _text(self.task025_area_rounding_mode, "provenance.task025_area_rounding_mode")
        _text(
            self.producer_area_precision_policy_id, "provenance.producer_area_precision_policy_id"
        )
        if type(self.producer_precision_limitation_disclosed) is not bool:
            raise ValueError("provenance.producer_precision_limitation_disclosed must be bool")
        if type(self.producer_precision_threshold_defined) is not bool:
            raise ValueError("provenance.producer_precision_threshold_defined must be bool")
        for name in (
            "source_identity_hashes",
            "producer_edges",
            "evidence_refs",
            "deferred_capabilities",
        ):
            object.__setattr__(self, name, _strings(getattr(self, name), f"provenance.{name}"))


@dataclass(frozen=True)
class Task037SuccessResult:
    schema_version: str
    task037_version: str
    implementation_software_version: str
    request_hash: str
    task021_identity: FrozenIdentity
    task025_identity: FrozenIdentity
    task025_hydraulic_authority_hash: str
    tube_geometry_snapshot_hash: str
    heat_transfer_length_hash: str
    tube_side_film_reference_surface: str
    overall_u_reference_surface: str
    outer_to_inner_area_ratio: Decimal
    surface_transform_authority_hash: str
    wall_material_authority_hash: str
    wall_conductivity_authority_hash: str
    wall_bundle_conduction_resistance_k_w: Decimal
    wall_resistance_outer_surface_m2_k_w: Decimal
    inside_fouling_authority: InsideFoulingResistanceAuthority
    outside_fouling_authority: OutsideFoulingResistanceAuthority
    fouling_authority_ledger: tuple[str, ...]
    applicability_ledger: tuple[str, ...]
    completeness_ledger: tuple[str, ...]
    warnings: tuple[str, ...]
    blockers: tuple[Any, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task037Provenance
    result_hash: str
    result_id: str

    def __post_init__(self) -> None:
        if self.schema_version != RESULT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {RESULT_SCHEMA_VERSION!r}")
        if self.task037_version != TASK037_VERSION:
            raise ValueError(f"task037_version must be {TASK037_VERSION!r}")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError("implementation_software_version is not frozen")
        for name in (
            "request_hash",
            "task025_hydraulic_authority_hash",
            "tube_geometry_snapshot_hash",
            "heat_transfer_length_hash",
            "surface_transform_authority_hash",
            "wall_material_authority_hash",
            "wall_conductivity_authority_hash",
            "result_hash",
        ):
            _hash(getattr(self, name), f"result.{name}")
        if type(self.task021_identity) is not FrozenIdentity:
            raise ValueError("result.task021_identity must be FrozenIdentity")
        if type(self.task025_identity) is not FrozenIdentity:
            raise ValueError("result.task025_identity must be FrozenIdentity")
        if type(self.inside_fouling_authority) is not InsideFoulingResistanceAuthority:
            raise ValueError(
                "result.inside_fouling_authority must be InsideFoulingResistanceAuthority"
            )
        if type(self.outside_fouling_authority) is not OutsideFoulingResistanceAuthority:
            raise ValueError(
                "result.outside_fouling_authority must be OutsideFoulingResistanceAuthority"
            )
        if type(self.provenance) is not Task037Provenance:
            raise ValueError("result.provenance must be Task037Provenance")
        for name in (
            "outer_to_inner_area_ratio",
            "wall_bundle_conduction_resistance_k_w",
            "wall_resistance_outer_surface_m2_k_w",
        ):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise ValueError(f"result.{name} must be finite Decimal")
        for name in (
            "fouling_authority_ledger",
            "applicability_ledger",
            "completeness_ledger",
            "warnings",
            "blockers",
            "deferred_capabilities",
        ):
            value = getattr(self, name)
            if type(value) is not tuple:
                raise ValueError(f"result.{name} must be tuple")
            if any(type(item) is not str or not item for item in value if name != "blockers"):
                raise ValueError(f"result.{name} must contain non-empty str entries")
        if any(type(item) is not BlockerEntry for item in self.blockers):
            raise ValueError("result.blockers must contain BlockerEntry entries")
        if self.blockers != () or self.warnings != ():
            raise ValueError("valid TASK037 result must have empty blockers and warnings")
        if self.deferred_capabilities != DEFERRED_CAPABILITIES:
            raise ValueError("result.deferred_capabilities are not frozen")
        if type(self.result_id) is not str or not self.result_id:
            raise ValueError("result.result_id must be non-empty str")
        try:
            result_uuid = UUID(self.result_id)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("result.result_id must be UUID text") from exc
        if result_uuid.version != 5 or result_uuid.variant != "specified in RFC 4122":
            raise ValueError("result.result_id must be RFC 4122 UUIDv5")


@dataclass(frozen=True)
class Task037TypedBlockedResult:
    schema_version: str
    task037_version: str
    implementation_software_version: str
    failure_stage: str
    request_hash: str | None
    task021_identity: FrozenIdentity | None
    task025_identity: FrozenIdentity | None
    task025_hydraulic_authority_hash: str | None
    tube_geometry_snapshot_hash: str | None
    heat_transfer_length_hash: str | None
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task037Provenance | None
    blocked_result_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != TYPED_BLOCKED_RESULT_SCHEMA_VERSION:
            raise ValueError("typed blocked schema_version is not frozen")
        if self.task037_version != TASK037_VERSION:
            raise ValueError("typed blocked task037_version is not frozen")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError("typed blocked implementation token is not frozen")
        _text(self.failure_stage, "typed_blocked.failure_stage")
        if self.request_hash is not None:
            _hash(self.request_hash, "typed_blocked.request_hash")
        for name in (
            "task025_hydraulic_authority_hash",
            "tube_geometry_snapshot_hash",
            "heat_transfer_length_hash",
        ):
            if getattr(self, name) is not None:
                _hash(getattr(self, name), f"typed_blocked.{name}")
        if self.task021_identity is not None and type(self.task021_identity) is not FrozenIdentity:
            raise ValueError("typed_blocked.task021_identity has wrong type")
        if self.task025_identity is not None and type(self.task025_identity) is not FrozenIdentity:
            raise ValueError("typed_blocked.task025_identity has wrong type")
        if not isinstance(self.blockers, tuple) or not self.blockers:
            raise ValueError("typed blocked result requires blocker tuple")
        if any(type(item) is not BlockerEntry for item in self.blockers):
            raise ValueError("typed blocked blockers have wrong type")
        object.__setattr__(self, "warnings", _strings(self.warnings, "typed_blocked.warnings"))
        object.__setattr__(
            self,
            "deferred_capabilities",
            _strings(self.deferred_capabilities, "typed_blocked.deferred_capabilities"),
        )
        if self.deferred_capabilities != DEFERRED_CAPABILITIES:
            raise ValueError("typed blocked deferred capabilities are not frozen")
        _hash(self.blocked_result_hash, "typed_blocked.blocked_result_hash")


@dataclass(frozen=True)
class Task037RawBoundaryBlockedResult:
    schema_version: str
    task037_version: str
    implementation_software_version: str
    raw_request_projection: FrozenRawProjection
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    blocked_result_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION:
            raise ValueError("raw boundary schema_version is not frozen")
        if self.task037_version != TASK037_VERSION:
            raise ValueError("raw boundary task037_version is not frozen")
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError("raw boundary implementation token is not frozen")
        if type(self.raw_request_projection) is not FrozenRawProjection:
            raise ValueError("raw_request_projection has wrong type")
        if not isinstance(self.blockers, tuple) or not self.blockers:
            raise ValueError("raw boundary requires blocker tuple")
        if any(type(item) is not BlockerEntry for item in self.blockers):
            raise ValueError("raw boundary blockers have wrong type")
        object.__setattr__(self, "warnings", _strings(self.warnings, "raw_boundary.warnings"))
        object.__setattr__(
            self,
            "deferred_capabilities",
            _strings(self.deferred_capabilities, "raw_boundary.deferred_capabilities"),
        )
        if self.deferred_capabilities != DEFERRED_CAPABILITIES:
            raise ValueError("raw boundary deferred capabilities are not frozen")
        _hash(self.blocked_result_hash, "raw_boundary.blocked_result_hash")


@dataclass(frozen=True)
class Task037ValidationResult:
    status: str
    success_result: Task037SuccessResult | None = None
    blocked_result: Task037TypedBlockedResult | None = None
    raw_boundary_blocked_result: Task037RawBoundaryBlockedResult | None = None

    def __post_init__(self) -> None:
        branches = (self.success_result, self.blocked_result, self.raw_boundary_blocked_result)
        if self.status not in {"VALID", "BLOCKED"}:
            raise ValueError("status must be VALID or BLOCKED")
        if sum(branch is not None for branch in branches) != 1:
            raise ValueError("exactly one result branch must be populated")
        if self.status == "VALID" and self.success_result is None:
            raise ValueError("VALID requires success_result")
        if self.status == "BLOCKED" and self.success_result is not None:
            raise ValueError("BLOCKED cannot contain success_result")

    @property
    def result(
        self,
    ) -> Task037SuccessResult | Task037TypedBlockedResult | Task037RawBoundaryBlockedResult:
        return self.success_result or self.blocked_result or self.raw_boundary_blocked_result  # type: ignore[return-value]

    @property
    def typed_blocked_result(self) -> Task037TypedBlockedResult | None:
        return self.blocked_result

    @property
    def warnings(self) -> tuple[Any, ...]:
        return self.result.warnings

    @property
    def blockers(self) -> tuple[Any, ...]:
        return self.result.blockers


Task037Result: TypeAlias = Task037SuccessResult
Task037BlockedResult: TypeAlias = Task037TypedBlockedResult
Task037RawBlockedResult: TypeAlias = Task037RawBoundaryBlockedResult

__all__ = [
    "BlockerEntry",
    "FrozenIdentity",
    "FrozenRawProjection",
    "InsideFoulingResistanceAuthority",
    "OutsideFoulingResistanceAuthority",
    "Task037BlockedResult",
    "Task037Provenance",
    "Task037RawBlockedResult",
    "Task037RawBoundaryBlockedResult",
    "Task037Request",
    "Task037Result",
    "Task037SuccessResult",
    "Task037TypedBlockedResult",
    "Task037ValidationResult",
    "TubeWallMaterialAuthority",
    "TubeWallThermalConductivityAuthority",
    "WarningEntry",
]
