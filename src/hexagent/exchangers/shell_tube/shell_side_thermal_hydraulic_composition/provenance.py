"""Deterministic provenance graph for the TASK-035 composition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .canonical import (
    PROVENANCE_NAMESPACE,
    hash_projection,
    provenance_hash,
    provenance_prehash_projection,
)
from .schema import (
    APPLICABILITY_PROFILE_ID,
    COMPLETENESS_PROFILE_ID,
    DEFERRED_CAPABILITIES,
    FIRST_SLICE_PROFILE_ID,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROVENANCE_FIELDS,
    PROVENANCE_PREHASH_FIELDS,
    SOURCE_DEFINITION_CORRECTION_CHAIN,
    SOURCE_DEFINITION_ISSUE,
)

PRODUCER_EDGE_COUNT = 4
SELF_EDGE_COUNT = 0
PROVENANCE_FIELD_COUNT = len(PROVENANCE_FIELDS)
PROVENANCE_PREHASH_FIELD_COUNT = len(PROVENANCE_PREHASH_FIELDS)


def producer_edges(
    *,
    task031_geometry_hash: str | None,
    task031_geometry_id: str | None,
    task032_result_hash: str | None,
    task032_result_id: str | None,
    task033_result_hash: str | None,
    task033_result_id: str | None,
    task034_result_hash: str | None,
    task034_result_id: str | None,
) -> tuple[tuple[tuple[str, Any], ...], ...]:
    """Return the exact four directed producer edges in frozen order."""

    rows = (
        (
            "TASK031",
            "GEOMETRY",
            task031_geometry_hash,
            task031_geometry_id,
        ),
        ("TASK032", "RESULT", task032_result_hash, task032_result_id),
        ("TASK033", "RESULT", task033_result_hash, task033_result_id),
        ("TASK034", "RESULT", task034_result_hash, task034_result_id),
    )
    return tuple(
        (
            ("producer_task", task),
            ("consumer_task", "TASK035"),
            ("producer_primary_identity_kind", kind),
            ("producer_primary_hash", primary_hash),
            ("producer_primary_id", primary_id),
        )
        for task, kind, primary_hash, primary_id in rows
    )


def _value(source: Mapping[str, Any], name: str) -> Any:
    return source.get(name)


def build_provenance_prehash(values: Mapping[str, Any]) -> dict[str, Any]:
    """Build a complete 35-field provenance prehash projection.

    The caller supplies only accepted public evidence.  Missing values are
    represented by ``None`` for blocked results rather than being omitted.
    """

    edge_values = values.get("producer_edges")
    if edge_values is None:
        edge_values = producer_edges(
            task031_geometry_hash=_value(values, "task031_geometry_hash"),
            task031_geometry_id=_value(values, "task031_geometry_id"),
            task032_result_hash=_value(values, "task032_result_hash"),
            task032_result_id=_value(values, "task032_result_id"),
            task033_result_hash=_value(values, "task033_result_hash"),
            task033_result_id=_value(values, "task033_result_id"),
            task034_result_hash=_value(values, "task034_result_hash"),
            task034_result_id=_value(values, "task034_result_id"),
        )
    prehash: dict[str, Any] = {
        "task_id": values.get("task_id", "TASK035"),
        "profile_id": values.get("profile_id"),
        "first_slice_profile_id": values.get("first_slice_profile_id", FIRST_SLICE_PROFILE_ID),
        "implementation_software_version": values.get(
            "implementation_software_version", IMPLEMENTATION_SOFTWARE_VERSION
        ),
        "request_hash": values.get("request_hash"),
        "task031_request_hash": values.get("task031_request_hash"),
        "task031_geometry_hash": values.get("task031_geometry_hash"),
        "task031_geometry_id": values.get("task031_geometry_id"),
        "task021_layout_hash": values.get("task021_layout_hash"),
        "task021_layout_id": values.get("task021_layout_id"),
        "task024_geometry_hash": values.get("task024_geometry_hash"),
        "task024_geometry_id": values.get("task024_geometry_id"),
        "task032_request_hash": values.get("task032_request_hash"),
        "task032_result_hash": values.get("task032_result_hash"),
        "task032_result_id": values.get("task032_result_id"),
        "task033_request_hash": values.get("task033_request_hash"),
        "task033_result_hash": values.get("task033_result_hash"),
        "task033_result_id": values.get("task033_result_id"),
        "task033_correlation_id": values.get("task033_correlation_id"),
        "task034_request_hash": values.get("task034_request_hash"),
        "task034_result_hash": values.get("task034_result_hash"),
        "task034_result_id": values.get("task034_result_id"),
        "task034_correlation_id": values.get("task034_correlation_id"),
        "task020_configuration_hash": values.get("task020_configuration_hash"),
        "task020_configuration_id": values.get("task020_configuration_id"),
        "property_snapshot_hash": values.get("property_snapshot_hash"),
        "mass_flow_authority_hash": values.get("mass_flow_authority_hash"),
        "applicability_profile_id": values.get(
            "applicability_profile_id", APPLICABILITY_PROFILE_ID
        ),
        "completeness_profile_id": values.get("completeness_profile_id", COMPLETENESS_PROFILE_ID),
        "producer_edges": edge_values,
        "warnings": values.get("warnings", ()),
        "deferred_capabilities": values.get("deferred_capabilities", DEFERRED_CAPABILITIES),
        "evidence_refs": values.get("evidence_refs", ()),
        "source_definition_issue": values.get("source_definition_issue", SOURCE_DEFINITION_ISSUE),
        "source_definition_correction_chain": values.get(
            "source_definition_correction_chain", SOURCE_DEFINITION_CORRECTION_CHAIN
        ),
    }
    return {field: prehash.get(field) for field in PROVENANCE_PREHASH_FIELDS}


def finalize_provenance(prehash: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    """Hash the 35-field preimage and append the final hash field."""

    normalized = build_provenance_prehash(prehash)
    digest = hash_projection(PROVENANCE_NAMESPACE, provenance_prehash_projection(normalized))
    return tuple((field, normalized[field]) for field in PROVENANCE_PREHASH_FIELDS) + (
        ("provenance_hash", digest),
    )


def build_provenance(values: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    return finalize_provenance(build_provenance_prehash(values))


def verify_provenance(provenance: Any) -> bool:
    """Return whether an ordered provenance tuple has the frozen shape/hash."""

    if not isinstance(provenance, (tuple, list)) or len(provenance) != PROVENANCE_FIELD_COUNT:
        return False
    if any(
        not isinstance(item, (tuple, list)) or len(item) != 2 or type(item[0]) is not str
        for item in provenance
    ):
        return False
    fields = tuple(item[0] for item in provenance)
    if fields != PROVENANCE_FIELDS:
        return False
    expected = provenance_hash(provenance)
    last_value: object = provenance[-1][1]
    return isinstance(last_value, str) and last_value == expected


__all__ = [
    "PRODUCER_EDGE_COUNT",
    "PROVENANCE_FIELD_COUNT",
    "PROVENANCE_PREHASH_FIELD_COUNT",
    "SELF_EDGE_COUNT",
    "build_provenance",
    "build_provenance_prehash",
    "finalize_provenance",
    "producer_edges",
    "verify_provenance",
]
