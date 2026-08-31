"""Runtime provenance construction for TASK-038."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .canonical import provenance_hash
from .models import Task038Provenance
from .schema import (
    BASE_MAIN_SHA,
    BASE_MAIN_TREE,
    BASELINE_REPAIR_GOVERNANCE_COMMENT_ID,
    DEFERRED_CAPABILITIES,
    DESIGN_ISSUE,
    DESIGN_REVISION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PRODUCER_AREA_PRECISION_POLICY_HASH,
    SOURCE_DEFINITION_ISSUE,
    SOURCE_DEFINITION_REVISION,
    TASK025_AREA_QUANTUM_M2,
    TASK025_AREA_ROUNDING_MODE,
    TASK025_PRODUCER_AREA_PRECISION_POLICY_ID,
    TASK_ID,
)

PROVENANCE_PREHASH_FIELD_COUNT = 42
PROVENANCE_FIELD_COUNT = 43
SELF_EDGE_COUNT = 0


def producer_edges(
    task025_result_hash: str,
    task026_result_hash: str,
    task035_result_hash: str,
    task037_result_hash: str,
) -> tuple[str, ...]:
    """Return the stable producer lineage labels used by callers."""

    return (
        f"TASK025->{task025_result_hash}",
        f"TASK026->{task026_result_hash}",
        f"TASK035->{task035_result_hash}",
        f"TASK037->{task037_result_hash}",
    )


def build_provenance(
    *,
    request_hash: str,
    task025_result_hash: str,
    task025_result_id: str,
    task025_hydraulic_authority_hash: str,
    task026_result_hash: str,
    task026_result_id: str,
    task026_property_snapshot_hash: str,
    task035_result_hash: str,
    task035_result_id: str,
    task035_shell_side_fluid_id: str,
    task037_result_hash: str,
    task037_result_id: str,
    task037_surface_transform_authority_hash: str,
    task037_inside_fouling_authority_hash: str,
    task037_outside_fouling_authority_hash: str,
    tube_side_service_binding_authority_hash: str,
    engineering_source_identity_hashes: tuple[str, ...],
    cross_producer_compatibility_hash: str,
    resistance_composition_authority_hash: str,
    outer_area_projection_authority_hash: str,
    ua_composition_authority_hash: str,
    overall_u_reference_surface: str,
    modeled_overall_heat_transfer_coefficient_w_m2_k: Any,
    outer_tube_surface_effective_area_m2: Any,
    modeled_ua_w_k: Any,
    evidence_refs: tuple[str, ...],
    task037_task025_area_quantum_m2: Any = TASK025_AREA_QUANTUM_M2,
    task037_task025_area_rounding_mode: str = TASK025_AREA_ROUNDING_MODE,
    task037_producer_area_precision_policy_id: str = TASK025_PRODUCER_AREA_PRECISION_POLICY_ID,
    task037_producer_area_precision_policy_hash: str = PRODUCER_AREA_PRECISION_POLICY_HASH,
    task037_producer_precision_limitation_disclosed: bool = True,
    task037_producer_precision_threshold_defined: bool = False,
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES,
) -> Task038Provenance:
    provisional = Task038Provenance(
        task_id=TASK_ID,
        source_definition_issue=SOURCE_DEFINITION_ISSUE,
        source_definition_revision=SOURCE_DEFINITION_REVISION,
        design_issue=DESIGN_ISSUE,
        design_revision=DESIGN_REVISION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        base_main_sha=BASE_MAIN_SHA,
        base_main_tree=BASE_MAIN_TREE,
        baseline_repair_governance_comment_id=BASELINE_REPAIR_GOVERNANCE_COMMENT_ID,
        request_hash=request_hash,
        task025_result_hash=task025_result_hash,
        task025_result_id=task025_result_id,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task026_result_hash=task026_result_hash,
        task026_result_id=task026_result_id,
        task026_property_snapshot_hash=task026_property_snapshot_hash,
        task035_result_hash=task035_result_hash,
        task035_result_id=task035_result_id,
        task035_shell_side_fluid_id=task035_shell_side_fluid_id,
        task037_result_hash=task037_result_hash,
        task037_result_id=task037_result_id,
        task037_surface_transform_authority_hash=task037_surface_transform_authority_hash,
        task037_inside_fouling_authority_hash=task037_inside_fouling_authority_hash,
        task037_outside_fouling_authority_hash=task037_outside_fouling_authority_hash,
        task037_task025_area_quantum_m2=task037_task025_area_quantum_m2,
        task037_task025_area_rounding_mode=task037_task025_area_rounding_mode,
        task037_producer_area_precision_policy_id=task037_producer_area_precision_policy_id,
        task037_producer_area_precision_policy_hash=task037_producer_area_precision_policy_hash,
        task037_producer_precision_limitation_disclosed=task037_producer_precision_limitation_disclosed,
        task037_producer_precision_threshold_defined=task037_producer_precision_threshold_defined,
        tube_side_service_binding_authority_hash=tube_side_service_binding_authority_hash,
        engineering_source_identity_hashes=engineering_source_identity_hashes,
        cross_producer_compatibility_hash=cross_producer_compatibility_hash,
        resistance_composition_authority_hash=resistance_composition_authority_hash,
        outer_area_projection_authority_hash=outer_area_projection_authority_hash,
        ua_composition_authority_hash=ua_composition_authority_hash,
        overall_u_reference_surface=overall_u_reference_surface,
        modeled_overall_heat_transfer_coefficient_w_m2_k=modeled_overall_heat_transfer_coefficient_w_m2_k,
        outer_tube_surface_effective_area_m2=outer_tube_surface_effective_area_m2,
        modeled_ua_w_k=modeled_ua_w_k,
        evidence_refs=evidence_refs,
        deferred_capabilities=deferred_capabilities,
        provenance_hash="0" * 64,
    )
    return replace(provisional, provenance_hash=provenance_hash(provisional))


def build_provenance_prehash(**kwargs: Any) -> bytes:
    from .canonical import provenance_preimage_bytes

    return provenance_preimage_bytes(build_provenance(**kwargs))


def provenance_to_fields(value: Task038Provenance) -> tuple[tuple[str, Any], ...]:
    return tuple((field, getattr(value, field)) for field in value.__dataclass_fields__)


def verify_provenance(value: Any) -> bool:
    return type(value) is Task038Provenance and provenance_hash(value) == value.provenance_hash


__all__ = [
    "PROVENANCE_FIELD_COUNT",
    "PROVENANCE_PREHASH_FIELD_COUNT",
    "SELF_EDGE_COUNT",
    "build_provenance",
    "build_provenance_prehash",
    "producer_edges",
    "provenance_to_fields",
    "verify_provenance",
]
