"""Authority admission and cross-producer joins for TASK-038."""

from __future__ import annotations

from typing import Any

from .canonical import (
    cross_producer_compatibility_hash,
    engineering_source_identity_hash,
    service_binding_hash,
)
from .models import EngineeringSourceIdentity, TubeSideServiceBindingAuthority
from .schema import (
    OVERALL_U_REFERENCE_SURFACE,
    SHELL_SIDE_FILM_REFERENCE_SURFACE,
    TUBE_SIDE_FILM_REFERENCE_SURFACE,
)


def is_sha256_hex(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _text(value: object) -> bool:
    return type(value) is str and bool(value)


def validate_service_binding(value: Any) -> tuple[bool, str]:
    if type(value) is not TubeSideServiceBindingAuthority:
        return False, "service_binding_type_invalid"
    if value.approval_status != "APPROVED":
        return False, "service_binding_not_approved"
    if value.source_class != "APPROVED_ENGINEERING_BASIS":
        return False, "service_binding_source_class_invalid"
    if value.permission_status != "INTERNAL_USE_AUTHORIZED":
        return False, "service_binding_permission_invalid"
    if not value.evidence_refs:
        return False, "service_binding_evidence_refs_empty"
    if not is_sha256_hex(value.task026_result_hash):
        return False, "service_binding_task026_hash_invalid"
    if not is_sha256_hex(value.task026_property_snapshot_hash):
        return False, "service_binding_property_hash_invalid"
    if service_binding_hash(value) != value.authority_hash:
        return False, "service_binding_hash_mismatch"
    return True, "PASS"


def validate_engineering_source(value: Any) -> tuple[bool, str]:
    if type(value) is not EngineeringSourceIdentity:
        return False, "engineering_source_type_invalid"
    if not value.source_locations:
        return False, "engineering_source_locations_empty"
    if not _text(value.source_id) or not _text(value.source_version):
        return False, "engineering_source_identity_invalid"
    return True, engineering_source_identity_hash(value)


def _identity(value: Any, field: str) -> Any:
    return getattr(value, field)


def validate_cross_producer_joins(
    task025: Any,
    task026: Any,
    task035: Any,
    task037: Any,
    binding: TubeSideServiceBindingAuthority,
) -> tuple[bool, str]:
    """Evaluate frozen J01-J17 joins without numerical stream equality."""

    try:
        task025_task021 = task025.task021_identity
        task025_task020 = task025.task020_identity
        task037_task021 = task037.task021_identity
        task037_task025 = task037.task025_identity
        checks = (
            task026.upstream_geometry_hash == task025.hydraulic_authority_hash,
            task037.task025_hydraulic_authority_hash == task025.hydraulic_authority_hash,
            task037_task025.identity_hash == task025.result_hash,
            task037_task025.identity_id == task025.result_id,
            task037_task021.identity_id == task025_task021.identity_id,
            task037_task021.identity_hash == task025_task021.identity_hash == task025.layout_hash,
            task035.task021_layout_id == task037_task021.identity_id,
            task035.task021_layout_hash == task037_task021.identity_hash,
            task035.task020_configuration_id == task025_task020.identity_id,
            task035.task020_configuration_hash == task025_task020.identity_hash,
            task035.heat_transfer_surface == OVERALL_U_REFERENCE_SURFACE,
            task037.overall_u_reference_surface == OVERALL_U_REFERENCE_SURFACE,
            task037.tube_side_film_reference_surface == TUBE_SIDE_FILM_REFERENCE_SURFACE,
            binding.task026_result_hash == task026.result_hash,
            binding.task026_property_snapshot_hash == task026.property_snapshot_hash,
            task037.inside_fouling_authority.fluid_service_id == binding.tube_side_fluid_service_id,
            task037.outside_fouling_authority.fluid_service_id == task035.shell_side_fluid_id,
        )
    except (AttributeError, TypeError):
        return False, "cross_producer_join_input_invalid"
    return (True, "PASS") if all(checks) else (False, "cross_producer_join_mismatch")


def build_cross_producer_projection(
    task025: Any,
    task026: Any,
    task035: Any,
    task037: Any,
    binding: TubeSideServiceBindingAuthority,
) -> dict[str, Any]:
    return {
        "task025_result_hash": task025.result_hash,
        "task026_result_hash": task026.result_hash,
        "task035_result_hash": task035.result_hash,
        "task037_result_hash": task037.result_hash,
        "tube_side_service_binding_authority_hash": binding.authority_hash,
        "task025_hydraulic_authority_hash": task025.hydraulic_authority_hash,
        "task021_layout_id": task025.task021_identity.identity_id,
        "task021_layout_hash": task025.task021_identity.identity_hash,
        "task020_configuration_id": task025.task020_identity.identity_id,
        "task020_configuration_hash": task025.task020_identity.identity_hash,
        "task026_property_snapshot_hash": task026.property_snapshot_hash,
        "task035_shell_side_fluid_id": task035.shell_side_fluid_id,
        "task037_inside_fouling_fluid_service_id": (
            task037.inside_fouling_authority.fluid_service_id
        ),
        "task037_outside_fouling_fluid_service_id": (
            task037.outside_fouling_authority.fluid_service_id
        ),
        "tube_side_film_reference_surface": task037.tube_side_film_reference_surface,
        "shell_side_film_reference_surface": SHELL_SIDE_FILM_REFERENCE_SURFACE,
        "overall_u_reference_surface": task037.overall_u_reference_surface,
    }


def cross_producer_hash(
    task025: Any, task026: Any, task035: Any, task037: Any, binding: TubeSideServiceBindingAuthority
) -> str:
    return cross_producer_compatibility_hash(
        build_cross_producer_projection(task025, task026, task035, task037, binding)
    )


__all__ = [
    "build_cross_producer_projection",
    "cross_producer_hash",
    "is_sha256_hex",
    "validate_cross_producer_joins",
    "validate_engineering_source",
    "validate_service_binding",
]
