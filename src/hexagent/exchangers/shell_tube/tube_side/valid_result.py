"""TASK-025 valid result schema.

§6.2 / §6.2.1 — Task025ValidResult exact public field tuple and types.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    FrozenIdentity,
    FrozenProvenance,
)

# §6.2 — TASK025_VALID_RESULT_FIELDS tuple (27 fields, exact order).
TASK025_VALID_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "request_hash",
    "layout_hash",
    "result_hash",
    "result_id",
    "internal_flow_authority",
    "heat_transfer_authority",
    "hydraulic_authority_hash",
    "active_position_ids",
    "inactive_position_ids",
    "single_tube_flow_area_m2",
    "total_parallel_flow_area_m2",
    "flow_cross_section_wetted_perimeter_m",
    "total_flow_cross_section_wetted_perimeter_m",
    "hydraulic_diameter_m",
    "internal_volume_m3",
    "internal_heat_transfer_surface_area_m2",
    "future_pressure_drop_length_m",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "stage_rank",
    "task020_identity",
    "task021_identity",
    "provenance",
)


DEFERRED_CAPABILITIES_V1: tuple[str, ...] = (
    "SHELL_DIAMETER_NOT_COMPUTABLE",
    "BAFFLE_DESIGN_NOT_COMPUTABLE",
    "PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE",
    "THERMAL_RATING_NOT_COMPUTABLE",
    "KERN_SCREENING_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "PRESSURE_DROP_NOT_COMPUTABLE",
    "THERMAL_EXPANSION_NOT_COMPUTABLE",
    "MECHANICAL_BOUNDARY_NOT_COMPUTABLE",
    "MATERIAL_SELECTION_NOT_COMPUTABLE",
    "MASS_NOT_COMPUTABLE",
    "COST_NOT_COMPUTABLE",
    "OPTIMIZATION_NOT_COMPUTABLE",
    "API_NOT_COMPUTABLE",
    "REPORT_NOT_COMPUTABLE",
    "GOLDEN_VALIDATION_NOT_COMPUTABLE",
)


_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")


def _validate_hash(value: str, field_path: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_path} must be a 64-character string")
    if any(c not in _HEX_DIGITS for c in value):
        raise ValueError(f"{field_path} must be lowercase hexadecimal")
    return value


@dataclass(frozen=True)
class Task025ValidResult:
    """§6.2 / §6.2.1 — TASK-025 unique valid-result value object."""

    schema_version: str
    profile_id: str
    implementation_software_version: str
    request_hash: str
    layout_hash: str
    result_hash: str
    result_id: str
    internal_flow_authority: InternalFlowLengthAuthority
    heat_transfer_authority: HeatTransferLengthAuthority
    hydraulic_authority_hash: str
    active_position_ids: tuple[str, ...]
    inactive_position_ids: tuple[str, ...]
    single_tube_flow_area_m2: Decimal
    total_parallel_flow_area_m2: Decimal
    flow_cross_section_wetted_perimeter_m: Decimal
    total_flow_cross_section_wetted_perimeter_m: Decimal
    hydraulic_diameter_m: Decimal
    internal_volume_m3: Decimal
    internal_heat_transfer_surface_area_m2: Decimal
    future_pressure_drop_length_m: Decimal | None
    warnings: tuple[str, ...]
    blockers: tuple[Any, ...]
    deferred_capabilities: tuple[str, ...]
    stage_rank: int
    task020_identity: FrozenIdentity
    task021_identity: FrozenIdentity
    provenance: FrozenProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("schema_version must be non-empty str")
        if self.schema_version != "task025.result.v1":
            raise ValueError(
                f"schema_version must be 'task025.result.v1'; got {self.schema_version!r}"
            )
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ValueError("profile_id must be non-empty str")
        if not isinstance(self.implementation_software_version, str):
            raise ValueError("implementation_software_version must be str")
        _validate_hash(self.request_hash, "request_hash")
        _validate_hash(self.layout_hash, "layout_hash")
        _validate_hash(self.result_hash, "result_hash")
        if not isinstance(self.result_id, str):
            raise ValueError("result_id must be str")
        if not isinstance(self.internal_flow_authority, InternalFlowLengthAuthority):
            raise ValueError("internal_flow_authority must be InternalFlowLengthAuthority")
        if not isinstance(self.heat_transfer_authority, HeatTransferLengthAuthority):
            raise ValueError("heat_transfer_authority must be HeatTransferLengthAuthority")
        _validate_hash(self.hydraulic_authority_hash, "hydraulic_authority_hash")
        if not isinstance(self.active_position_ids, (tuple, list)):
            raise ValueError("active_position_ids must be tuple/list of str")
        if not isinstance(self.inactive_position_ids, (tuple, list)):
            raise ValueError("inactive_position_ids must be tuple/list of str")
        object.__setattr__(self, "active_position_ids", tuple(self.active_position_ids))
        object.__setattr__(self, "inactive_position_ids", tuple(self.inactive_position_ids))
        if not isinstance(self.warnings, tuple):
            raise ValueError("warnings must be a tuple (use ())")
        if self.warnings != ():
            raise ValueError("v1 warnings must be ()")
        if not isinstance(self.blockers, tuple):
            raise ValueError("blockers must be a tuple (use ())")
        if self.blockers != ():
            raise ValueError("valid result blockers must be ()")
        if not isinstance(self.deferred_capabilities, tuple):
            raise ValueError("deferred_capabilities must be tuple of str")
        object.__setattr__(self, "deferred_capabilities", tuple(self.deferred_capabilities))
        if not isinstance(self.stage_rank, int) or self.stage_rank != 9:
            raise ValueError(f"stage_rank must be 9; got {self.stage_rank!r}")
        if not isinstance(self.task020_identity, FrozenIdentity):
            raise ValueError("task020_identity must be FrozenIdentity")
        if not isinstance(self.task021_identity, FrozenIdentity):
            raise ValueError("task021_identity must be FrozenIdentity")
        if not isinstance(self.provenance, FrozenProvenance):
            raise ValueError("provenance must be FrozenProvenance")
        if not isinstance(self.future_pressure_drop_length_m, (Decimal, type(None))):
            raise ValueError("future_pressure_drop_length_m must be Decimal or None")


__all__ = [
    "Task025ValidResult",
    "TASK025_VALID_RESULT_FIELDS",
    "DEFERRED_CAPABILITIES_V1",
]
