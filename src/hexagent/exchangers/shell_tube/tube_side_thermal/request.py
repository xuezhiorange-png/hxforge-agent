"""TASK-026 typed request.

R8 implementation. The 10-field TubeSideThermalRequest (R6-R7 §3.1)
carries the typed inputs from S00 raw factory through to S15 hash
finalization. The phase_assertion must agree with the embedded
property_snapshot.phase_region (R6-R7 §3.4 S03 invariant).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    ACCEPTED_PHASE_ASSERTIONS,
    ACCEPTED_THERMAL_BOUNDARY_CONDITIONS,
    PhaseAssertion,
    ThermalBoundaryCondition,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    PropertySnapshot,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
    INPUT_EVIDENCE_REFS_V1,
    FrozenProvenance,
)

# R6-R7 §3.1 — exactly 10 fields:
REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task026_version",
    "implementation_software_version",
    "property_snapshot_hash",
    "property_snapshot",
    "phase_assertion",
    "thermal_boundary_condition",
    "mass_flow_rate_kg_s",
    "deferred_capabilities",
    "provenance",
)

REQUEST_FIELD_COUNT: int = 10

# R6-R7 §9.2 — request hash fields (10, all non-None).
REQUEST_HASH_FIELDS: tuple[str, ...] = REQUEST_FIELDS

REQUEST_HASH_NAMESPACE: str = "task026.request.v1"

# R6-R7 §9.2 — kind tags per request field (10).
REQUEST_HASH_KIND_TAGS: tuple[bytes, ...] = (
    # KIND_STRING, KIND_STRING, KIND_STRING, KIND_STRING, KIND_RECORD,
    # KIND_ENUM, KIND_ENUM, KIND_DECIMAL, KIND_TUPLE, KIND_RECORD
    b"STRING",
    b"STRING",
    b"STRING",
    b"STRING",
    b"RECORD",
    b"ENUM",
    b"ENUM",
    b"DECIMAL",
    b"TUPLE",
    b"RECORD",
)

# Frozen schema / version identifiers.
SCHEMA_VERSION: str = "task026-r7.schema.v1"
TASK026_VERSION: str = "task026.v1"
IMPLEMENTATION_SOFTWARE_VERSION: str = "task026-local-impl-r8"

# R6-R7 §1.3 — 17 deferred capabilities (verbatim).
DEFERRED_CAPABILITIES_V1: tuple[str, ...] = (
    "SHELL_SIDE_NOT_COMPUTABLE",
    "OVERALL_U_NOT_COMPUTABLE",
    "UA_NOT_COMPUTABLE",
    "LMTD_NOT_COMPUTABLE",
    "EFFECTIVENESS_NOT_COMPUTABLE",
    "HEAT_DUTY_NOT_COMPUTABLE",
    "OUTLET_TEMPERATURES_NOT_COMPUTABLE",
    "PRESSURE_DROP_NOT_COMPUTABLE",
    "TWO_PHASE_NOT_COMPUTABLE",
    "PROPERTY_DATABASE_NOT_COMPUTABLE",
    "NETWORK_PROPERTY_LOOKUP_NOT_COMPUTABLE",
    "API_NOT_COMPUTABLE",
    "CLI_NOT_COMPUTABLE",
    "PERSISTENCE_NOT_COMPUTABLE",
    "REPORT_GENERATION_NOT_COMPUTABLE",
    "WALL_VISCOSITY_CORRECTION_NOT_COMPUTABLE",
    "ITERATIVE_WALL_TEMPERATURE_NOT_COMPUTABLE",
)

DEFERRED_CAPABILITY_COUNT: int = 17


@dataclass(frozen=True)
class TubeSideThermalRequest:
    """R6-R7 §3.1 — 10-field typed request value object."""

    schema_version: str
    task026_version: str
    implementation_software_version: str
    property_snapshot_hash: str
    property_snapshot: PropertySnapshot
    phase_assertion: PhaseAssertion
    thermal_boundary_condition: ThermalBoundaryCondition
    mass_flow_rate_kg_s: Decimal
    deferred_capabilities: tuple[str, ...]
    provenance: FrozenProvenance

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {SCHEMA_VERSION!r}; got {self.schema_version!r}"
            )
        if self.task026_version != TASK026_VERSION:
            raise ValueError(
                f"task026_version must be {TASK026_VERSION!r}; got {self.task026_version!r}"
            )
        if self.implementation_software_version != IMPLEMENTATION_SOFTWARE_VERSION:
            raise ValueError(
                f"implementation_software_version must be {IMPLEMENTATION_SOFTWARE_VERSION!r}; "
                f"got {self.implementation_software_version!r}"
            )
        if (
            not isinstance(self.property_snapshot_hash, str)
            or len(self.property_snapshot_hash) != 64
        ):
            raise ValueError("property_snapshot_hash must be 64-hex string")
        if any(c not in "0123456789abcdef" for c in self.property_snapshot_hash):
            raise ValueError("property_snapshot_hash must be lowercase hex")
        if self.phase_assertion not in ACCEPTED_PHASE_ASSERTIONS:
            raise ValueError(
                f"phase_assertion must be one of "
                f"{[p.value for p in ACCEPTED_PHASE_ASSERTIONS]}; "
                f"got {self.phase_assertion!r}"
            )
        if self.thermal_boundary_condition not in ACCEPTED_THERMAL_BOUNDARY_CONDITIONS:
            raise ValueError(
                f"thermal_boundary_condition must be one of "
                f"{[c.value for c in ACCEPTED_THERMAL_BOUNDARY_CONDITIONS]}; "
                f"got {self.thermal_boundary_condition!r}"
            )
        if not isinstance(self.mass_flow_rate_kg_s, Decimal):
            raise ValueError("mass_flow_rate_kg_s must be Decimal")
        if self.mass_flow_rate_kg_s <= Decimal(0):
            raise ValueError(
                f"mass_flow_rate_kg_s must be strictly positive; got {self.mass_flow_rate_kg_s!s}"
            )
        if not isinstance(self.deferred_capabilities, tuple):
            raise ValueError("deferred_capabilities must be tuple")
        if self.deferred_capabilities != DEFERRED_CAPABILITIES_V1:
            raise ValueError("deferred_capabilities must be the frozen 17-tuple from R6-R7 §1.3")
        # R6-R7 §3.4 — phase_assertion must equal phase_region.
        if self.phase_assertion.value != self.property_snapshot.phase_region.value:
            raise ValueError(
                "phase_assertion must equal property_snapshot.phase_region "
                f"(R6-R7 §3.4 S03 invariant); got assertion={self.phase_assertion.value} "
                f"region={self.property_snapshot.phase_region.value}"
            )
        # R6-R7 §3.4 — property_snapshot_hash cross-check.
        if self.property_snapshot_hash != self.property_snapshot.property_snapshot_hash:
            raise ValueError(
                "property_snapshot_hash must equal property_snapshot.property_snapshot_hash "
                "(R6-R7 §3.4 S03 invariant)"
            )
        # Validate upstream_identity_hashes non-empty (R6-R7 §17.1).
        if len(self.provenance.upstream_identity_hashes) == 0:
            raise ValueError("provenance.upstream_identity_hashes must be non-empty")
        if self.provenance.input_evidence_refs != INPUT_EVIDENCE_REFS_V1:
            raise ValueError("provenance.input_evidence_refs must be the frozen 6-tuple")


def field_count() -> int:
    return REQUEST_FIELD_COUNT


__all__ = [
    "REQUEST_FIELDS",
    "REQUEST_FIELD_COUNT",
    "REQUEST_HASH_FIELDS",
    "REQUEST_HASH_KIND_TAGS",
    "REQUEST_HASH_NAMESPACE",
    "SCHEMA_VERSION",
    "TASK026_VERSION",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "DEFERRED_CAPABILITIES_V1",
    "DEFERRED_CAPABILITY_COUNT",
    "TubeSideThermalRequest",
    "field_count",
]
