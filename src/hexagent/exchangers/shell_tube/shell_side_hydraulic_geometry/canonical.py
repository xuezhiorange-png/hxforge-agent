# ruff: noqa: E501
"""Canonical serialization and identity helpers for TASK-031."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_EVEN
from typing import Any

from hexagent.exchangers.shell_tube.baffle_geometry import models as task024_models
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout

from .engineering_authority_snapshot import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
)
from .formulas import DECIMAL_PRECISION
from .models import (
    DEFERRED_CAPABILITIES,
    FLOW_REGION_IDENTITY,
    FORMULA_A_ID,
    FORMULA_B_ID,
    RESULT_SCHEMA_VERSION,
    EngineeringAuthorityRequestBinding,
    MessageEntry,
    ShellSideHydraulicGeometry,
    ShellSideHydraulicGeometryRequest,
)

CanonicalizationError = task021_canonical.CanonicalizationError
PublicCanonicalDomainError = task021_canonical.PublicCanonicalDomainError
FrozenJsonArray = task021_canonical.FrozenJsonArray
FrozenJsonObject = task021_canonical.FrozenJsonObject

parse_decimal = task021_canonical.parse_decimal
decimal_string = task021_canonical.decimal_string
canonical_json = task021_canonical.canonical_json
sha256_hex = task021_canonical.sha256_hex
dataclass_to_mapping = task021_canonical.dataclass_to_mapping
to_primitive = task021_canonical.to_primitive
canonical_raw_json_or_none = task021_canonical.canonical_raw_json_or_none
freeze_known_fragment = task021_canonical.freeze_known_fragment
internal_frozen_to_primitive = task021_canonical.internal_frozen_to_primitive

GEOMETRY_URN_PREFIX = "urn:hxforge:task031:shell-side-hydraulic-geometry:v1:"
IMPLEMENTATION_SOFTWARE_VERSION = "task031.minimal-compute-v1"
GIT_COMMIT = "832f0474be4fc2270476af453fafad553d5915b3"

PROVENANCE_FIELD_ORDER: tuple[str, ...] = (
    "task_id",
    "design_contract_path",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task021_layout_id",
    "task021_layout_hash",
    "task022_geometry_id",
    "task022_geometry_hash",
    "task024_geometry_id",
    "task024_geometry_hash",
    "engineering_authority_profile_id",
    "engineering_authority_hash",
    "formula_a_id",
    "formula_b_id",
    "source_authority_freeze_issue",
    "source_authority_freeze_comment_id",
    "source_ids",
    "pattern_family",
    "flow_region_identity",
    "software_version",
    "git_commit",
    "request_hash",
    "warnings",
    "deferred_capabilities",
    "provenance_hash",
)


def geometry_id(geometry_hash: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, GEOMETRY_URN_PREFIX + geometry_hash))


def message_to_primitive(entry: MessageEntry) -> dict[str, Any]:
    return {
        "code": entry.code,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
        "details": [[key, value] for key, value in entry.details],
    }


def message_sort_key(
    entry: MessageEntry,
    *,
    stage_rank: int = 0,
) -> tuple[int, str, str, str, str, str]:
    return (
        stage_rank,
        entry.code,
        entry.field_path or "",
        entry.message_key,
        sha256_hex(list(entry.details)),
        sha256_hex(list(entry.evidence_refs)),
    )


def warning_sort_key(entry: MessageEntry) -> tuple[str, str, str, str, str]:
    return (
        entry.code,
        entry.field_path or "",
        entry.message_key,
        sha256_hex(list(entry.details)),
        sha256_hex(list(entry.evidence_refs)),
    )


def sort_blockers(
    entries: Iterable[MessageEntry],
    *,
    stage_by_identity: Mapping[int, int] | None = None,
) -> tuple[MessageEntry, ...]:
    ranks = stage_by_identity or {}
    return tuple(
        sorted(
            entries, key=lambda entry: message_sort_key(entry, stage_rank=ranks.get(id(entry), 0))
        )
    )


def sort_warnings(entries: Iterable[MessageEntry]) -> tuple[MessageEntry, ...]:
    return tuple(sorted(entries, key=warning_sort_key))


def engineering_authority_request_binding(
    binding: EngineeringAuthorityRequestBinding,
) -> list[list[Any]]:
    return [
        ["schema_version", binding.schema_version],
        ["authority_profile_id", binding.authority_profile_id],
        ["authority_hash", binding.authority_hash],
        ["evidence_refs", list(binding.evidence_refs)],
    ]


def tube_layout_public_projection(layout: TubeLayout) -> dict[str, Any]:
    from .authority import layout_hash_payload

    return layout_hash_payload(layout)


def task024_result_binding_projection(
    result: task024_models.BaffleGeometryValidationResult,
) -> list[Any]:
    status = result.status.value
    if status == "BLOCKED" or result.geometry is None:
        return [status, None]
    geometry = result.geometry
    design = geometry.design_authority
    return [
        status,
        geometry.schema_version,
        geometry.geometry_id,
        geometry.geometry_hash,
        geometry.request_hash,
        geometry.task020_configuration_id,
        geometry.task020_configuration_hash,
        geometry.task021_layout_id,
        geometry.task021_layout_hash,
        geometry.task022_geometry_id,
        geometry.task022_geometry_hash,
        geometry.construction_family,
        geometry.shell_pass_count,
        geometry.shell_inside_diameter_m,
        geometry.tube_outer_diameter_m,
        design.schema_version,
        design.baffle_type.value,
        design.baffle_count,
        list(design.spacing_sequence_m),
        design.authority_hash,
    ]


def request_canonical_projection(request: ShellSideHydraulicGeometryRequest) -> list[Any]:
    return [
        request.schema_version,
        tube_layout_public_projection(request.tube_layout),
        task024_result_binding_projection(request.baffle_geometry_result),
        engineering_authority_request_binding(request.engineering_authority),
        list(request.evidence_refs),
    ]


def request_hash(request: ShellSideHydraulicGeometryRequest) -> str:
    return sha256_hex(request_canonical_projection(request))


def success_geometry_canonical_projection(geometry: ShellSideHydraulicGeometry) -> list[Any]:
    provenance_dict = dict(geometry.provenance)
    return [
        geometry.schema_version,
        geometry.request_hash,
        geometry.task020_configuration_id,
        geometry.task020_configuration_hash,
        geometry.task021_layout_id,
        geometry.task021_layout_hash,
        geometry.task022_geometry_id,
        geometry.task022_geometry_hash,
        geometry.task024_geometry_id,
        geometry.task024_geometry_hash,
        geometry.pattern_family,
        geometry.central_inter_baffle_spacing_m,
        geometry.central_crossflow_flow_area_m2,
        geometry.shell_side_equivalent_hydraulic_diameter_m,
        geometry.flow_region_identity,
        geometry.engineering_authority_id,
        geometry.engineering_authority_hash,
        geometry.formula_a_id,
        geometry.formula_b_id,
        [message_to_primitive(item) for item in geometry.warnings],
        list(geometry.deferred_capabilities),
        provenance_prehash_from_mapping(provenance_dict),
    ]


def provenance_prehash_from_mapping(mapping: Mapping[str, Any]) -> list[Any]:
    if "freeze_comment_id" in mapping:
        freeze_comment_id = mapping["freeze_comment_id"]
    else:
        freeze_comment_id = mapping["source_authority_freeze_comment_id"]
    return [
        mapping["task_id"],
        mapping["design_contract_path"],
        mapping["task020_configuration_id"],
        mapping["task020_configuration_hash"],
        mapping["task021_layout_id"],
        mapping["task021_layout_hash"],
        mapping["task022_geometry_id"],
        mapping["task022_geometry_hash"],
        mapping["task024_geometry_id"],
        mapping["task024_geometry_hash"],
        mapping["engineering_authority_profile_id"],
        mapping["engineering_authority_hash"],
        mapping["formula_a_id"],
        mapping["formula_b_id"],
        freeze_comment_id,
        list(mapping["source_ids"]),
        mapping["pattern_family"],
        mapping["flow_region_identity"],
        mapping["software_version"],
        mapping["git_commit"],
        mapping["request_hash"],
        mapping["warnings"],
        list(mapping["deferred_capabilities"]),
    ]


def provenance_prehash_projection(
    *,
    request: ShellSideHydraulicGeometryRequest,
    request_hash_value: str,
    warnings: tuple[MessageEntry, ...],
    pattern_family: str,
) -> dict[str, Any]:
    layout = request.tube_layout
    geometry = request.baffle_geometry_result.geometry
    assert geometry is not None
    from .engineering_authority_snapshot import FREEZE_COMMENT_ID, SOURCE_IDS

    return {
        "task_id": "TASK031",
        "design_contract_path": "docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md",
        "task020_configuration_id": layout.task020_configuration_id,
        "task020_configuration_hash": layout.task020_configuration_hash,
        "task021_layout_id": layout.layout_id,
        "task021_layout_hash": layout.layout_hash,
        "task022_geometry_id": geometry.task022_geometry_id,
        "task022_geometry_hash": geometry.task022_geometry_hash,
        "task024_geometry_id": geometry.geometry_id,
        "task024_geometry_hash": geometry.geometry_hash,
        "engineering_authority_profile_id": request.engineering_authority.authority_profile_id,
        "engineering_authority_hash": ENGINEERING_AUTHORITY_HASH,
        "formula_a_id": FORMULA_A_ID,
        "formula_b_id": FORMULA_B_ID,
        "freeze_comment_id": FREEZE_COMMENT_ID,
        "source_ids": list(SOURCE_IDS),
        "pattern_family": pattern_family,
        "flow_region_identity": FLOW_REGION_IDENTITY,
        "software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "git_commit": GIT_COMMIT,
        "request_hash": request_hash_value,
        "warnings": [message_to_primitive(item) for item in warnings],
        "deferred_capabilities": list(DEFERRED_CAPABILITIES),
    }


def final_provenance_tuple(prehash: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    provenance_hash = sha256_hex(provenance_prehash_from_mapping(prehash))
    final = {
        "task_id": prehash["task_id"],
        "design_contract_path": prehash["design_contract_path"],
        "task020_configuration_id": prehash["task020_configuration_id"],
        "task020_configuration_hash": prehash["task020_configuration_hash"],
        "task021_layout_id": prehash["task021_layout_id"],
        "task021_layout_hash": prehash["task021_layout_hash"],
        "task022_geometry_id": prehash["task022_geometry_id"],
        "task022_geometry_hash": prehash["task022_geometry_hash"],
        "task024_geometry_id": prehash["task024_geometry_id"],
        "task024_geometry_hash": prehash["task024_geometry_hash"],
        "engineering_authority_profile_id": prehash["engineering_authority_profile_id"],
        "engineering_authority_hash": prehash["engineering_authority_hash"],
        "formula_a_id": prehash["formula_a_id"],
        "formula_b_id": prehash["formula_b_id"],
        "source_authority_freeze_issue": 181,
        "source_authority_freeze_comment_id": prehash["freeze_comment_id"],
        "source_ids": list(prehash["source_ids"]),
        "pattern_family": prehash["pattern_family"],
        "flow_region_identity": prehash["flow_region_identity"],
        "software_version": prehash["software_version"],
        "git_commit": prehash["git_commit"],
        "request_hash": prehash["request_hash"],
        "warnings": prehash["warnings"],
        "deferred_capabilities": list(prehash["deferred_capabilities"]),
        "provenance_hash": provenance_hash,
    }
    if set(final.keys()) != set(PROVENANCE_FIELD_ORDER):
        raise CanonicalizationError("provenance field set mismatch")
    return tuple((key, final[key]) for key in PROVENANCE_FIELD_ORDER)


def blocked_result_hash(
    *,
    failure_stage: int,
    normalized_context: Any,
    raw_failing_field: Any,
    warnings: tuple[MessageEntry, ...],
    blockers: tuple[MessageEntry, ...],
) -> str:
    payload = [
        RESULT_SCHEMA_VERSION,
        failure_stage,
        normalized_context,
        canonical_raw_json_or_none(raw_failing_field),
        [message_to_primitive(item) for item in warnings],
        [message_to_primitive(item) for item in blockers],
        list(DEFERRED_CAPABILITIES),
    ]
    return sha256_hex(payload)


__all__ = [
    "CanonicalizationError",
    "DECIMAL_PRECISION",
    "ENGINEERING_AUTHORITY_HASH",
    "ENGINEERING_AUTHORITY_ID",
    "FrozenJsonArray",
    "FrozenJsonObject",
    "GIT_COMMIT",
    "GEOMETRY_URN_PREFIX",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "PROVENANCE_FIELD_ORDER",
    "PublicCanonicalDomainError",
    "ROUND_HALF_EVEN",
    "blocked_result_hash",
    "canonical_json",
    "canonical_raw_json_or_none",
    "dataclass_to_mapping",
    "decimal_string",
    "engineering_authority_request_binding",
    "final_provenance_tuple",
    "freeze_known_fragment",
    "geometry_id",
    "internal_frozen_to_primitive",
    "message_sort_key",
    "message_to_primitive",
    "parse_decimal",
    "provenance_prehash_from_mapping",
    "provenance_prehash_projection",
    "request_canonical_projection",
    "request_hash",
    "sha256_hex",
    "sort_blockers",
    "sort_warnings",
    "success_geometry_canonical_projection",
    "task024_result_binding_projection",
    "to_primitive",
    "tube_layout_public_projection",
    "warning_sort_key",
]
