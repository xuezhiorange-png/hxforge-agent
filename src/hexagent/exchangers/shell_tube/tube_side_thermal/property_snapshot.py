"""TASK-026 property snapshot.

R8 implementation. The 10-field PropertySnapshot (R6-R7 §3.2) is a
typed record carrying the upstream property provider's six DECIMAL
scalars, two STRING scalars (source_id, source_version), one ENUM
scalar (phase_region), and one self-referential 64-hex SHA-256.

The 9-field hash projection (R6-R7 §3.3) excludes the
property_snapshot_hash field. The S03 invariant (R6-R7 §3.4) is
that three independent sources of the same hash must agree:

  recomputed_property_snapshot_hash == property_snapshot.property_snapshot_hash
   == request.property_snapshot_hash

The recomputation is a canonical 9-field frame_record under
namespace "task026.property-snapshot.v1" using the hash_kind tags
declared in R6-R7 §9.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    ACCEPTED_PHASE_REGIONS,
    PhaseRegion,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_STRING,
    composite_hash,
    decimal_payload,
    enum_payload,
    string_payload,
)

# R6-R7 §3.2 — exactly 10 fields:
PROPERTY_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "density_kg_m3",
    "dynamic_viscosity_pa_s",
    "thermal_conductivity_w_m_k",
    "specific_heat_capacity_j_kg_k",
    "bulk_temperature_k",
    "bulk_pressure_pa",
    "phase_region",
    "property_source_id",
    "property_source_version",
    "property_snapshot_hash",
)

# R6-R7 §3.3 — 9-field hash projection (exclude property_snapshot_hash).
PROPERTY_SNAPSHOT_HASH_FIELDS: tuple[str, ...] = (
    "density_kg_m3",
    "dynamic_viscosity_pa_s",
    "thermal_conductivity_w_m_k",
    "specific_heat_capacity_j_kg_k",
    "bulk_temperature_k",
    "bulk_pressure_pa",
    "phase_region",
    "property_source_id",
    "property_source_version",
)

# R6-R7 §9.3 — kind tags for the 9 hash projection fields.
PROPERTY_SNAPSHOT_HASH_KIND_TAGS: tuple[bytes, ...] = (
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_STRING,
    KIND_STRING,
)

# R6-R7 §9.7.1 — full 10-field sub-record kind tags (H1-R1 addendum).
PROPERTY_SNAPSHOT_SUBRECORD_KIND_TAGS: tuple[bytes, ...] = (
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_STRING,
    KIND_STRING,
    KIND_STRING,
)

PROPERTY_SNAPSHOT_NAMESPACE: str = "task026.property-snapshot.v1"


@dataclass(frozen=True)
class PropertySnapshot:
    """R6-R7 §3.2 — Typed 10-field property snapshot value object."""

    density_kg_m3: Decimal
    dynamic_viscosity_pa_s: Decimal
    thermal_conductivity_w_m_k: Decimal
    specific_heat_capacity_j_kg_k: Decimal
    bulk_temperature_k: Decimal
    bulk_pressure_pa: Decimal
    phase_region: PhaseRegion
    property_source_id: str
    property_source_version: str
    property_snapshot_hash: str

    def __post_init__(self) -> None:
        # Validate PhaseRegion membership.
        if self.phase_region not in ACCEPTED_PHASE_REGIONS:
            raise ValueError(
                f"phase_region must be one of "
                f"{[r.value for r in ACCEPTED_PHASE_REGIONS]}; "
                f"got {self.phase_region!r}"
            )
        # Validate 64-hex self-hash.
        if not isinstance(self.property_snapshot_hash, str):
            raise ValueError("property_snapshot_hash must be str")
        if len(self.property_snapshot_hash) != 64:
            raise ValueError(
                f"property_snapshot_hash must be 64 hex chars; "
                f"got len={len(self.property_snapshot_hash)}"
            )
        if any(c not in "0123456789abcdef" for c in self.property_snapshot_hash):
            raise ValueError("property_snapshot_hash must be lowercase hexadecimal")
        # Validate six DECIMAL scalars are positive (R6-R7 §6.1 / §6.3
        # require positive physical properties; BL_PROPERTY_FIELD_NON_POSITIVE
        # is emitted at S02 if any scalar is non-positive).
        for fname, val in (
            ("density_kg_m3", self.density_kg_m3),
            ("dynamic_viscosity_pa_s", self.dynamic_viscosity_pa_s),
            ("thermal_conductivity_w_m_k", self.thermal_conductivity_w_m_k),
            ("specific_heat_capacity_j_kg_k", self.specific_heat_capacity_j_kg_k),
        ):
            if not isinstance(val, Decimal):
                raise ValueError(f"{fname} must be Decimal; got {type(val).__name__}")
            if val <= Decimal(0):
                raise ValueError(f"{fname} must be strictly positive; got {val!s}")
        # bulk_temperature_k and bulk_pressure_pa must be positive (physical)
        for fname, val in (
            ("bulk_temperature_k", self.bulk_temperature_k),
            ("bulk_pressure_pa", self.bulk_pressure_pa),
        ):
            if not isinstance(val, Decimal):
                raise ValueError(f"{fname} must be Decimal; got {type(val).__name__}")
            if val <= Decimal(0):
                raise ValueError(f"{fname} must be strictly positive; got {val!s}")
        # Validate source strings are non-empty.
        if not isinstance(self.property_source_id, str) or not self.property_source_id:
            raise ValueError("property_source_id must be non-empty str")
        if not isinstance(self.property_source_version, str) or not self.property_source_version:
            raise ValueError("property_source_version must be non-empty str")


def _field_payload(name: str, snapshot: PropertySnapshot) -> bytes:
    """Return the canonical payload bytes for a single field name."""
    if name == "density_kg_m3":
        return decimal_payload(snapshot.density_kg_m3)
    if name == "dynamic_viscosity_pa_s":
        return decimal_payload(snapshot.dynamic_viscosity_pa_s)
    if name == "thermal_conductivity_w_m_k":
        return decimal_payload(snapshot.thermal_conductivity_w_m_k)
    if name == "specific_heat_capacity_j_kg_k":
        return decimal_payload(snapshot.specific_heat_capacity_j_kg_k)
    if name == "bulk_temperature_k":
        return decimal_payload(snapshot.bulk_temperature_k)
    if name == "bulk_pressure_pa":
        return decimal_payload(snapshot.bulk_pressure_pa)
    if name == "phase_region":
        return enum_payload(snapshot.phase_region)
    if name == "property_source_id":
        return string_payload(snapshot.property_source_id)
    if name == "property_source_version":
        return string_payload(snapshot.property_source_version)
    raise ValueError(f"unknown property_snapshot field: {name}")


def _kind_tag_for(name: str) -> bytes:
    """Return the canonical KIND_* tag for the given field name."""
    if name in (
        "density_kg_m3",
        "dynamic_viscosity_pa_s",
        "thermal_conductivity_w_m_k",
        "specific_heat_capacity_j_kg_k",
        "bulk_temperature_k",
        "bulk_pressure_pa",
    ):
        return KIND_DECIMAL
    if name == "phase_region":
        return KIND_ENUM
    if name in ("property_source_id", "property_source_version"):
        return KIND_STRING
    raise ValueError(f"unknown property_snapshot field: {name}")


def recompute_property_snapshot_hash(snapshot: PropertySnapshot) -> str:
    """R6-R7 §3.3 / §9.3 — SHA-256 of the 9-field frame_record.

    Excludes property_snapshot_hash (the self-reference). The kind
    tags are fixed in PROPERTY_SNAPSHOT_HASH_KIND_TAGS.
    """
    fields: list[tuple[str, bytes, bytes]] = []
    for i, name in enumerate(PROPERTY_SNAPSHOT_HASH_FIELDS):
        kind = PROPERTY_SNAPSHOT_HASH_KIND_TAGS[i]
        payload = _field_payload(name, snapshot)
        fields.append((name, kind, payload))
    return composite_hash(PROPERTY_SNAPSHOT_NAMESPACE, fields)


def field_count() -> int:
    return 10


def hash_field_count() -> int:
    return 9


__all__ = [
    "PROPERTY_SNAPSHOT_FIELDS",
    "PROPERTY_SNAPSHOT_HASH_FIELDS",
    "PROPERTY_SNAPSHOT_HASH_KIND_TAGS",
    "PROPERTY_SNAPSHOT_SUBRECORD_KIND_TAGS",
    "PROPERTY_SNAPSHOT_NAMESPACE",
    "PropertySnapshot",
    "recompute_property_snapshot_hash",
    "field_count",
    "hash_field_count",
]
