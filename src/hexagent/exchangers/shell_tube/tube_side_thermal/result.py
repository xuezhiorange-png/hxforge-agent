"""TASK-026 result and blocked result schemas.

R8 implementation. The success result (R6-R7 §8.1) is a 23-field
record; the blocked result (R6-R7 §8.2) is a 17-field record. The
two schemas share schema_version, task026_version,
implementation_software_version, upstream_geometry_hash,
property_snapshot_hash, thermal_boundary_condition,
phase_assertion, mass_flow_rate_kg_s, request_hash, result_hash,
result_id, blockers, warnings, deferred_capabilities, provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    PhaseAssertion,
    ThermalBoundaryCondition,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
    FrozenProvenance,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.raw_projection import (
    FrozenRawProjection,
)

# R6-R7 §8.1 — Success result (23 fields).
SUCCESS_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task026_version",
    "implementation_software_version",
    "upstream_geometry_hash",
    "property_snapshot_hash",
    "thermal_boundary_condition",
    "phase_assertion",
    "mass_flow_rate_kg_s",
    "bulk_velocity_m_s",
    "reynolds_number",
    "prandtl_number",
    "flow_regime",
    "correlation_id",
    "correlation_version",
    "nusselt_number",
    "tube_side_heat_transfer_coefficient_w_m2_k",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)

SUCCESS_FIELD_COUNT: int = 23

# R6-R7 §8.2 — Blocked result (17 fields).
BLOCKED_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task026_version",
    "implementation_software_version",
    "upstream_geometry_hash",
    "property_snapshot_hash",
    "thermal_boundary_condition",
    "phase_assertion",
    "mass_flow_rate_kg_s",
    "raw_request_projection",
    "raw_upstream_blocked_projection",
    "request_hash",
    "result_hash",
    "result_id",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
)

BLOCKED_FIELD_COUNT: int = 17

# R6-R7 §9.4 — success result hash fields (21 self-excluding).
SUCCESS_RESULT_HASH_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task026_version",
    "implementation_software_version",
    "upstream_geometry_hash",
    "property_snapshot_hash",
    "thermal_boundary_condition",
    "phase_assertion",
    "mass_flow_rate_kg_s",
    "bulk_velocity_m_s",
    "reynolds_number",
    "prandtl_number",
    "flow_regime",
    "correlation_id",
    "correlation_version",
    "nusselt_number",
    "tube_side_heat_transfer_coefficient_w_m2_k",
    "request_hash",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)

SUCCESS_RESULT_HASH_NAMESPACE: str = "task026.success-result.v1"

# R6-R7 §9.4 — success result hash kind tags (21).
SUCCESS_RESULT_HASH_KIND_TAGS: tuple[bytes, ...] = (
    # KIND_STRING, KIND_STRING, KIND_STRING, KIND_STRING, KIND_STRING,
    # KIND_ENUM, KIND_ENUM, KIND_DECIMAL, KIND_DECIMAL, KIND_DECIMAL,
    # KIND_DECIMAL, KIND_ENUM, KIND_STRING, KIND_STRING, KIND_DECIMAL,
    # KIND_DECIMAL, KIND_STRING, KIND_TUPLE, KIND_TUPLE, KIND_TUPLE,
    # KIND_RECORD
    b"STRING",
    b"STRING",
    b"STRING",
    b"STRING",
    b"STRING",
    b"ENUM",
    b"ENUM",
    b"DECIMAL",
    b"DECIMAL",
    b"DECIMAL",
    b"DECIMAL",
    b"ENUM",
    b"STRING",
    b"STRING",
    b"DECIMAL",
    b"DECIMAL",
    b"STRING",
    b"TUPLE",
    b"TUPLE",
    b"TUPLE",
    b"RECORD",
)

# R6-R7 §9.5 — blocked result hash fields (15).
BLOCKED_RESULT_HASH_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task026_version",
    "implementation_software_version",
    "upstream_geometry_hash",
    "property_snapshot_hash",
    "thermal_boundary_condition",
    "phase_assertion",
    "mass_flow_rate_kg_s",
    "raw_request_projection",
    "raw_upstream_blocked_projection",
    "request_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
)

BLOCKED_RESULT_HASH_NAMESPACE: str = "task026.blocked-result.v1"

# R6-R7 §9.5 — blocked result hash kind tags (15).
BLOCKED_RESULT_HASH_KIND_TAGS: tuple[bytes, ...] = (
    # KIND_STRING, KIND_STRING, KIND_STRING, KIND_STRING, KIND_STRING,
    # KIND_ENUM, KIND_ENUM, KIND_DECIMAL, KIND_RAW_PROJECTION, KIND_RAW_PROJECTION,
    # KIND_STRING, KIND_TUPLE, KIND_TUPLE, KIND_TUPLE, KIND_RECORD
    b"STRING",
    b"STRING",
    b"STRING",
    b"STRING",
    b"STRING",
    b"ENUM",
    b"ENUM",
    b"DECIMAL",
    b"RAW_PROJECTION",
    b"RAW_PROJECTION",
    b"STRING",
    b"TUPLE",
    b"TUPLE",
    b"TUPLE",
    b"RECORD",
)

# R6-R7 §9.6.1 — raw boundary blocked result hash fields (6).
RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS: tuple[str, ...] = (
    "raw_request_projection",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "schema_version",
    "implementation_software_version",
)

RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE: str = "task026.raw-boundary-blocked-result.v1"

RAW_BOUNDARY_BLOCKED_RESULT_HASH_KIND_TAGS: tuple[bytes, ...] = (
    # KIND_RAW_PROJECTION, KIND_TUPLE, KIND_TUPLE, KIND_TUPLE, KIND_STRING,
    # KIND_STRING
    b"RAW_PROJECTION",
    b"TUPLE",
    b"TUPLE",
    b"TUPLE",
    b"STRING",
    b"STRING",
)

# R6-R7 §9.8 — self-reference exclusion.
SUCCESS_RESULT_HASH_EXCLUDED: tuple[str, ...] = ("result_hash", "result_id")
BLOCKED_RESULT_HASH_EXCLUDED: tuple[str, ...] = ("result_hash", "result_id")


@dataclass(frozen=True)
class TubeSideThermalResult:
    """R6-R7 §8.1 — 23-field success result value object."""

    schema_version: str
    task026_version: str
    implementation_software_version: str
    upstream_geometry_hash: str
    property_snapshot_hash: str
    thermal_boundary_condition: ThermalBoundaryCondition
    phase_assertion: PhaseAssertion
    mass_flow_rate_kg_s: Decimal
    bulk_velocity_m_s: Decimal
    reynolds_number: Decimal
    prandtl_number: Decimal
    flow_regime: FlowRegime
    correlation_id: str
    correlation_version: str
    nusselt_number: Decimal
    tube_side_heat_transfer_coefficient_w_m2_k: Decimal
    request_hash: str
    result_hash: str
    result_id: str
    warnings: tuple[str, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: FrozenProvenance


@dataclass(frozen=True)
class TubeSideBlockedResult:
    """R6-R7 §8.2 — 17-field blocked result value object."""

    schema_version: str
    task026_version: str
    implementation_software_version: str
    upstream_geometry_hash: str
    property_snapshot_hash: str
    thermal_boundary_condition: ThermalBoundaryCondition
    phase_assertion: PhaseAssertion
    mass_flow_rate_kg_s: Decimal
    raw_request_projection: FrozenRawProjection
    raw_upstream_blocked_projection: FrozenRawProjection
    request_hash: str
    result_hash: str
    result_id: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: FrozenProvenance


@dataclass(frozen=True)
class RawBoundaryBlockedResult:
    """R6-R7 §2.1 — S00 raw boundary blocked result."""

    schema_version: str
    implementation_software_version: str
    raw_request_projection: FrozenRawProjection
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]


__all__ = [
    "SUCCESS_RESULT_FIELDS",
    "SUCCESS_FIELD_COUNT",
    "BLOCKED_RESULT_FIELDS",
    "BLOCKED_FIELD_COUNT",
    "SUCCESS_RESULT_HASH_FIELDS",
    "SUCCESS_RESULT_HASH_KIND_TAGS",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "BLOCKED_RESULT_HASH_FIELDS",
    "BLOCKED_RESULT_HASH_KIND_TAGS",
    "BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_KIND_TAGS",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE",
    "SUCCESS_RESULT_HASH_EXCLUDED",
    "BLOCKED_RESULT_HASH_EXCLUDED",
    "TubeSideThermalResult",
    "TubeSideBlockedResult",
    "RawBoundaryBlockedResult",
]
