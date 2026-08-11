"""Hash computation: authority hash, request hash, result hashes, UUID5 generation.

§13.2, §13.3, §21 — UUID contract.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    RESULT_ID_NAME_PREFIX,
    RESULT_ID_NAMESPACE,
    canonicalize_authority,
    canonicalize_blocked_result_hash,
    canonicalize_raw_boundary_blocked_hash,
    canonicalize_request_hash,
    canonicalize_success_result_hash,
)

RESULT_ID_NAMESPACE_UUID: Final[uuid.UUID] = uuid.UUID(RESULT_ID_NAMESPACE)


def compute_authority_hash(
    component_id: str,
    component_type: str,
    flow_direction_assertion: str,
    loss_coefficient: str,
    loss_coefficient_convention: str,
    reference_flow_area_m2: str,
    multiplicity: int,
    upstream_reference_plane: str,
    downstream_reference_plane: str,
    geometry_evidence_refs: tuple[str, ...],
    coefficient_source_id: str,
    coefficient_source_version: str,
    coefficient_source_location: str,
    coefficient_permission_status: str,
    coefficient_source_evidence_refs: tuple[str, ...],
    caller_supplied_authority_hash: str,
) -> str:
    """§13.2 — Compute 16-field authority canonical SHA-256 hex."""
    _, sha256_hex = canonicalize_authority(
        component_id=component_id,
        component_type=component_type,
        flow_direction_assertion=flow_direction_assertion,
        loss_coefficient=loss_coefficient,
        loss_coefficient_convention=loss_coefficient_convention,
        reference_flow_area_m2=reference_flow_area_m2,
        multiplicity=multiplicity,
        upstream_reference_plane=upstream_reference_plane,
        downstream_reference_plane=downstream_reference_plane,
        geometry_evidence_refs=geometry_evidence_refs,
        coefficient_source_id=coefficient_source_id,
        coefficient_source_version=coefficient_source_version,
        coefficient_source_location=coefficient_source_location,
        coefficient_permission_status=coefficient_permission_status,
        coefficient_source_evidence_refs=coefficient_source_evidence_refs,
        caller_supplied_authority_hash=caller_supplied_authority_hash,
    )
    return sha256_hex


def compute_request_hash(
    schema_version: str,
    profile_id: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    constant_density_assertion: str,
    zero_elevation_assertion: str,
    flow_direction_assertion: str,
    component_authority_hashes: tuple[str, ...],
) -> str:
    """§14.2 — Compute request hash from 10 semantic fields."""
    return canonicalize_request_hash(
        schema_version=schema_version,
        profile_id=profile_id,
        task025_result_hash=task025_result_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        constant_density_assertion=constant_density_assertion,
        zero_elevation_assertion=zero_elevation_assertion,
        flow_direction_assertion=flow_direction_assertion,
        component_authority_hashes=component_authority_hashes,
    )


def compute_success_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str,
    task025_hydraulic_authority_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    component_result_hashes: tuple[str, ...],
    total_irreversible_pressure_loss_pa: str,
    warnings: tuple[str, ...],
    blockers: tuple[Any, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Any,
) -> str:
    """§13.2 — Compute success result hash (self-excludes result_hash, result_id)."""
    return canonicalize_success_result_hash(
        schema_version=schema_version,
        profile_id=profile_id,
        request_hash=request_hash,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        component_result_hashes=component_result_hashes,
        total_irreversible_pressure_loss_pa=total_irreversible_pressure_loss_pa,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=deferred_capabilities,
        provenance=provenance,
    )


def compute_blocked_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str,
    task025_hydraulic_authority_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    raw_request_projection: Any,
    raw_upstream_blocked_projection: Any,
    warnings: tuple[str, ...],
    blockers: tuple[Any, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Any,
) -> str:
    """§14.2 — Compute blocked result hash (self-excludes result_hash, result_id)."""
    return canonicalize_blocked_result_hash(
        schema_version=schema_version,
        profile_id=profile_id,
        request_hash=request_hash,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        raw_request_projection=raw_request_projection,
        raw_upstream_blocked_projection=raw_upstream_blocked_projection,
        warnings=warnings,
        blockers=blockers,
        deferred_capabilities=deferred_capabilities,
        provenance=provenance,
    )


def compute_raw_boundary_blocked_hash(
    raw_request_projection: Any,
    blockers: tuple[Any, ...],
    warnings: tuple[str, ...],
    deferred_capabilities: tuple[str, ...],
    schema_version: str,
    implementation_software_version: str,
) -> str:
    """§16 — Compute raw boundary blocked hash (6 fields, NOT a public field)."""
    return canonicalize_raw_boundary_blocked_hash(
        raw_request_projection=raw_request_projection,
        blockers=blockers,
        warnings=warnings,
        deferred_capabilities=deferred_capabilities,
        schema_version=schema_version,
        implementation_software_version=implementation_software_version,
    )


def compute_result_id(result_hash: str) -> str:
    """§15.2 — Derive canonical UUID5 from result hash."""
    name = RESULT_ID_NAME_PREFIX + result_hash
    return str(uuid.uuid5(RESULT_ID_NAMESPACE_UUID, name))


__all__ = [
    "compute_authority_hash",
    "compute_request_hash",
    "compute_success_result_hash",
    "compute_blocked_result_hash",
    "compute_raw_boundary_blocked_hash",
    "compute_result_id",
    "RESULT_ID_NAMESPACE_UUID",
]
