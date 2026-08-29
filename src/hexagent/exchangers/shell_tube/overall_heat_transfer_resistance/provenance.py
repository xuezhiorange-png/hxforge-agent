"""Self-edge-free TASK-037 provenance construction and replay."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .canonical import provenance_bytes
from .canonical import provenance_hash as replay_provenance_hash
from .models import Task037Provenance
from .schema import (
    DEFERRED_CAPABILITIES,
    DESIGN_CONTRACT_PATH,
    DESIGN_ISSUE,
    DESIGN_REVISION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROVENANCE_FIELDS,
    PROVENANCE_PREHASH_FIELDS,
    SELF_EDGE_COUNT,
    SOURCE_DEFINITION_ISSUE,
    SOURCE_DEFINITION_REVIEW_AUDIT_COMMENT,
    SOURCE_DEFINITION_REVISION,
    TASK_ID,
)

PRODUCER_EDGE_COUNT = 5
PROVENANCE_FIELD_COUNT = len(PROVENANCE_FIELDS)
PROVENANCE_PREHASH_FIELD_COUNT = len(PROVENANCE_PREHASH_FIELDS)


def producer_edges() -> tuple[str, ...]:
    """Return the only five directed producer edges in frozen order."""

    return (
        "TASK021->TASK025",
        "TASK025->TASK037",
        "TASK037.surface->TASK037.wall",
        "TASK037.wall->TASK037.provenance",
        "TASK037.provenance->TASK037.result",
    )


def _value(values: Mapping[str, Any], name: str, default: Any = None) -> Any:
    return values.get(name, default)


def build_provenance_prehash(values: Mapping[str, Any]) -> dict[str, Any]:
    """Return the complete 30-field provenance preimage mapping."""

    result = {
        "task_id": _value(values, "task_id", TASK_ID),
        "source_definition_issue": _value(
            values, "source_definition_issue", SOURCE_DEFINITION_ISSUE
        ),
        "source_definition_revision": _value(
            values, "source_definition_revision", SOURCE_DEFINITION_REVISION
        ),
        "source_definition_review_audit_comment": _value(
            values, "source_definition_review_audit_comment", SOURCE_DEFINITION_REVIEW_AUDIT_COMMENT
        ),
        "design_issue": _value(values, "design_issue", DESIGN_ISSUE),
        "design_revision": _value(values, "design_revision", DESIGN_REVISION),
        "implementation_software_version": _value(
            values, "implementation_software_version", IMPLEMENTATION_SOFTWARE_VERSION
        ),
        "request_hash": _value(values, "request_hash"),
        "task021_layout_hash": _value(values, "task021_layout_hash"),
        "task025_result_hash": _value(values, "task025_result_hash"),
        "task025_hydraulic_authority_hash": _value(values, "task025_hydraulic_authority_hash"),
        "tube_geometry_snapshot_hash": _value(values, "tube_geometry_snapshot_hash"),
        "heat_transfer_length_hash": _value(values, "heat_transfer_length_hash"),
        "task025_internal_heat_transfer_surface_area_m2": _value(
            values, "task025_internal_heat_transfer_surface_area_m2"
        ),
        "task025_area_quantum_m2": _value(values, "task025_area_quantum_m2"),
        "task025_area_rounding_mode": _value(values, "task025_area_rounding_mode"),
        "producer_area_precision_policy_id": _value(values, "producer_area_precision_policy_id"),
        "producer_area_precision_policy_hash": _value(
            values, "producer_area_precision_policy_hash"
        ),
        "producer_precision_limitation_disclosed": _value(
            values, "producer_precision_limitation_disclosed"
        ),
        "producer_precision_threshold_defined": _value(
            values, "producer_precision_threshold_defined"
        ),
        "wall_material_authority_hash": _value(values, "wall_material_authority_hash"),
        "wall_conductivity_authority_hash": _value(values, "wall_conductivity_authority_hash"),
        "inside_fouling_authority_hash": _value(values, "inside_fouling_authority_hash"),
        "outside_fouling_authority_hash": _value(values, "outside_fouling_authority_hash"),
        "surface_transform_authority_hash": _value(values, "surface_transform_authority_hash"),
        "wall_resistance_authority_hash": _value(values, "wall_resistance_authority_hash"),
        "source_identity_hashes": _value(values, "source_identity_hashes", ()),
        "producer_edges": _value(values, "producer_edges", producer_edges()),
        "evidence_refs": _value(values, "evidence_refs", ()),
        "deferred_capabilities": _value(values, "deferred_capabilities", DEFERRED_CAPABILITIES),
    }
    return {field: result[field] for field in PROVENANCE_PREHASH_FIELDS}


def build_provenance(values: Mapping[str, Any]) -> Task037Provenance:
    """Build a frozen provenance record and append its terminal hash."""

    prehash = build_provenance_prehash(values)
    provisional = Task037Provenance(**prehash, provenance_hash="0" * 64)
    digest = replay_provenance_hash(provisional)
    return replace(provisional, provenance_hash=digest)


def provenance_to_fields(provenance: Task037Provenance) -> tuple[tuple[str, Any], ...]:
    if type(provenance) is not Task037Provenance:
        raise TypeError("provenance must be Task037Provenance")
    return tuple((field, getattr(provenance, field)) for field in PROVENANCE_FIELDS)


def verify_provenance(provenance: Any) -> bool:
    if type(provenance) is not Task037Provenance:
        return False
    return provenance.provenance_hash == replay_provenance_hash(provenance)


def provenance_hash(provenance: Task037Provenance) -> str:
    return replay_provenance_hash(provenance)


__all__ = [
    "DESIGN_CONTRACT_PATH",
    "PRODUCER_EDGE_COUNT",
    "PROVENANCE_FIELD_COUNT",
    "PROVENANCE_FIELDS",
    "PROVENANCE_PREHASH_FIELD_COUNT",
    "PROVENANCE_PREHASH_FIELDS",
    "SELF_EDGE_COUNT",
    "build_provenance",
    "build_provenance_prehash",
    "provenance_bytes",
    "provenance_hash",
    "provenance_to_fields",
    "producer_edges",
    "verify_provenance",
]
