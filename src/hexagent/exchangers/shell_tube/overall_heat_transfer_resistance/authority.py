"""Admission and public-upstream replay checks for TASK-037."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_layout import (
    AuthorityFailure as Task021AuthorityFailure,
)
from hexagent.exchangers.shell_tube.tube_layout import (
    verify_geometry_snapshot,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    TubeLayout,
)
from hexagent.exchangers.shell_tube.tube_side import (
    FrozenIdentity,
    FrozenProvenance,
    HeatTransferLengthAuthority,
    Task025BlockedResult,
    Task025ValidResult,
    heat_transfer_authority_length_hash,
)
from hexagent.exchangers.shell_tube.tube_side import (
    result_hash as task025_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side import (
    result_id as task025_result_id,
)

from .canonical import (
    surface_transform_authority_hash,
    wall_resistance_authority_hash,
)
from .decimal_math import validate_nonnegative_finite_decimal, validate_positive_finite_decimal
from .models import (
    InsideFoulingResistanceAuthority,
    OutsideFoulingResistanceAuthority,
    TubeWallMaterialAuthority,
    TubeWallThermalConductivityAuthority,
)
from .schema import (
    ENGINEERING_SOURCE_ID,
    ENGINEERING_SOURCE_LOCATION_WALL,
    ENGINEERING_SOURCE_LOCATIONS,
    OVERALL_U_REFERENCE_SURFACE,
    PRODUCER_AREA_PRECISION_POLICY_HASH,
    SOURCE_FORMULA_IDENTITY,
    TASK025_AREA_QUANTUM_M2,
    TUBE_SIDE_FILM_REFERENCE_SURFACE,
    WALL_BUNDLE_NUMERICAL_BASIS,
)

_WALL_SOURCE_PERMISSION: dict[str, str] = {
    "PUBLIC_DOMAIN": "PUBLIC_USE_PERMITTED",
    "OPEN_LICENSE": "OPEN_LICENSE_ADMITTED",
    "USER_PROVIDED_LICENSED_SUMMARY": "USER_LICENSED_ADMITTED",
    "INTERNAL_ENGINEERING_RULE": "INTERNAL_USE_AUTHORIZED",
    "DERIVED_ENGINEERING_RULE": "INTERNAL_USE_AUTHORIZED",
    "REFERENCE_ONLY_RESTRICTED_STANDARD": "RESTRICTED_REFERENCE_AUTHORIZED",
    "VENDOR_PERMISSIONED": "VENDOR_PERMISSION_ADMITTED",
}
_FOULING_SOURCE_CLASSES = frozenset(
    {
        "PROJECT_SPECIFICATION",
        "CUSTOMER_SPECIFICATION",
        "APPROVED_STANDARD",
        "APPROVED_VENDOR_DOCUMENT",
        "APPROVED_ENGINEERING_BASIS",
    }
)


def is_sha256_hex(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _is_non_empty_string(value: object) -> bool:
    return type(value) is str and bool(value)


def _is_non_empty_string_tuple(value: object) -> bool:
    return (
        type(value) is tuple and bool(value) and all(_is_non_empty_string(item) for item in value)
    )


def validate_material_authority(authority: Any) -> tuple[bool, str]:
    if type(authority) is not TubeWallMaterialAuthority:
        return False, "material_authority_type_invalid"
    for name in (
        "authority_id",
        "material_id",
        "material_grade",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
    ):
        if not _is_non_empty_string(getattr(authority, name, None)):
            return False, f"material_{name}_invalid"
    if not _is_non_empty_string_tuple(authority.evidence_refs):
        return False, "material_evidence_refs_invalid"
    if not is_sha256_hex(authority.authority_hash):
        return False, "material_authority_hash_invalid"
    expected_permission = _WALL_SOURCE_PERMISSION.get(authority.source_class)
    if expected_permission is None or authority.permission_status != expected_permission:
        return False, "material_source_permission_not_admitted"
    if authority.approval_status != "APPROVED":
        return False, "material_authority_not_approved"
    return True, "PASS"


def validate_conductivity_authority(
    authority: Any,
    material: Any,
) -> tuple[bool, str]:
    if type(authority) is not TubeWallThermalConductivityAuthority:
        return False, "conductivity_authority_type_invalid"
    if type(material) is not TubeWallMaterialAuthority:
        return False, "material_authority_type_invalid"
    for name in (
        "authority_id",
        "material_id",
        "evaluation_context_id",
        "evaluation_basis",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
    ):
        if not _is_non_empty_string(getattr(authority, name, None)):
            return False, f"conductivity_{name}_invalid"
    if not _is_non_empty_string_tuple(authority.evidence_refs):
        return False, "conductivity_evidence_refs_invalid"
    if not is_sha256_hex(authority.authority_hash) or not is_sha256_hex(
        authority.applicability_authority_hash
    ):
        return False, "conductivity_authority_hash_invalid"
    expected_permission = _WALL_SOURCE_PERMISSION.get(authority.source_class)
    if expected_permission is None or authority.permission_status != expected_permission:
        return False, "conductivity_source_permission_not_admitted"
    if authority.approval_status != "APPROVED":
        return False, "conductivity_authority_not_approved"
    try:
        validate_positive_finite_decimal(
            authority.thermal_conductivity_w_m_k, "thermal_conductivity_w_m_k"
        )
        validate_positive_finite_decimal(
            authority.evaluation_temperature_k, "evaluation_temperature_k"
        )
    except (TypeError, ValueError):
        return False, "conductivity_scalar_invalid"
    if authority.material_id != material.material_id:
        return False, "conductivity_material_id_mismatch"
    return True, "PASS"


def validate_fouling_authority(authority: Any, *, side: str) -> tuple[bool, str]:
    expected_type = (
        InsideFoulingResistanceAuthority if side == "INSIDE" else OutsideFoulingResistanceAuthority
    )
    expected_surface = "INNER_TUBE_SURFACE" if side == "INSIDE" else "OUTER_TUBE_SURFACE"
    if type(authority) is not expected_type:
        return False, "fouling_authority_type_invalid"
    for name in (
        "authority_id",
        "side",
        "reference_surface",
        "fluid_service_id",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
        "resistance_units",
        "applicability",
    ):
        if not _is_non_empty_string(getattr(authority, name, None)):
            return False, f"fouling_{name}_invalid"
    if not _is_non_empty_string_tuple(authority.evidence_refs):
        return False, "fouling_evidence_refs_invalid"
    if authority.side != side or authority.reference_surface != expected_surface:
        return False, "fouling_reference_surface_invalid"
    if authority.source_class not in _FOULING_SOURCE_CLASSES:
        return False, "fouling_source_class_invalid"
    if authority.permission_status not in {
        "PUBLIC_USE_PERMITTED",
        "OPEN_LICENSE_ADMITTED",
        "USER_LICENSED_ADMITTED",
        "INTERNAL_USE_AUTHORIZED",
        "RESTRICTED_REFERENCE_AUTHORIZED",
        "VENDOR_PERMISSION_ADMITTED",
        "ADMITTED",
    }:
        return False, "fouling_permission_invalid"
    if authority.approval_status != "APPROVED":
        return False, "fouling_authority_not_approved"
    try:
        validate_nonnegative_finite_decimal(
            authority.fouling_resistance_m2_k_w, "fouling_resistance_m2_k_w"
        )
    except (TypeError, ValueError):
        return False, "fouling_resistance_invalid"
    if not is_sha256_hex(authority.authority_hash):
        return False, "fouling_authority_hash_invalid"
    return True, "PASS"


def validate_task021_layout(layout: Any) -> tuple[bool, str]:
    if type(layout) is not TubeLayout:
        return False, "task021_type_invalid"
    if layout.schema_version != "task021.tube-layout.v1":
        return False, "task021_schema_invalid"
    if not isinstance(layout.layout_id, str) or not layout.layout_id:
        return False, "task021_layout_id_invalid"
    if not is_sha256_hex(layout.layout_hash):
        return False, "task021_layout_hash_invalid"
    geometry = layout.tube_geometry
    if type(geometry) is not ApprovedTubeGeometrySnapshot:
        return False, "task021_geometry_invalid"
    if not is_sha256_hex(geometry.snapshot_hash):
        return False, "task021_geometry_snapshot_hash_invalid"
    for name in ("inner_diameter_m", "outer_diameter_m", "wall_thickness_m"):
        if type(getattr(geometry, name)) is not str or not getattr(geometry, name):
            return False, f"task021_geometry_{name}_invalid"
    try:
        verify_geometry_snapshot(geometry)
    except (Task021AuthorityFailure, ArithmeticError, TypeError, ValueError, AttributeError):
        return False, "task021_geometry_snapshot_identity_mismatch"
    return True, "PASS"


def replay_task025_valid_result(result: Any) -> tuple[bool, str]:
    """Replay only Task025's public result identity and area protection."""

    if type(result) is Task025BlockedResult:
        return False, "task025_blocked"
    if type(result) is not Task025ValidResult:
        return False, "task025_type_invalid"
    try:
        if result.schema_version != "task025.result.v1":
            return False, "task025_schema_invalid"
        if type(result.stage_rank) is not int or result.stage_rank != 9:
            return False, "task025_stage_rank_invalid"
        if result.warnings != ():
            return False, "task025_warnings_nonempty"
        if result.blockers != ():
            return False, "task025_blockers_nonempty"
        if type(result.heat_transfer_authority) is not HeatTransferLengthAuthority:
            return False, "task025_heat_transfer_authority_invalid"
        if type(result.provenance) is not FrozenProvenance:
            return False, "task025_provenance_invalid"
        if not _is_non_empty_string_tuple(result.active_position_ids):
            return False, "task025_active_position_ids_invalid"
        if type(result.inactive_position_ids) is not tuple or any(
            not _is_non_empty_string(item) for item in result.inactive_position_ids
        ):
            return False, "task025_inactive_position_ids_invalid"
        active_ids = result.active_position_ids
        inactive_ids = result.inactive_position_ids
        if len(set(active_ids)) != len(active_ids):
            return False, "task025_active_position_ids_duplicate"
        if len(set(inactive_ids)) != len(inactive_ids):
            return False, "task025_inactive_position_ids_duplicate"
        if set(active_ids).intersection(inactive_ids):
            return False, "task025_position_partition_overlap"
        validate_positive_finite_decimal(
            result.heat_transfer_authority.length_m,
            "task025.heat_transfer_authority.length_m",
        )
        expected_length_hash = heat_transfer_authority_length_hash(
            result.heat_transfer_authority.length_m,
            result.heat_transfer_authority.start_plane,
            result.heat_transfer_authority.end_plane,
            result.heat_transfer_authority.authority_mode,
        )
        if expected_length_hash != result.heat_transfer_authority.length_hash:
            return False, "task025_heat_transfer_length_hash_mismatch"
        validate_positive_finite_decimal(
            result.internal_heat_transfer_surface_area_m2,
            "task025.internal_heat_transfer_surface_area_m2",
        )
        public_area = result.internal_heat_transfer_surface_area_m2
        if public_area.quantize(TASK025_AREA_QUANTUM_M2) != public_area:
            return False, "task025_public_area_noncanonical"
        if task025_result_hash(result) != result.result_hash:
            return False, "task025_result_hash_mismatch"
        if task025_result_id(result.result_hash) != result.result_id:
            return False, "task025_result_id_mismatch"
        if not is_sha256_hex(result.hydraulic_authority_hash):
            return False, "task025_hydraulic_authority_hash_invalid"
        if type(result.heat_transfer_authority.length_hash) is not str or not is_sha256_hex(
            result.heat_transfer_authority.length_hash
        ):
            return False, "task025_heat_transfer_length_hash_invalid"
    except (ArithmeticError, TypeError, ValueError, AttributeError):
        return False, "task025_public_result_invalid"
    return True, "PASS"


def validate_task021_task025_binding(layout: Any, result: Any) -> tuple[bool, str]:
    if type(layout) is not TubeLayout or type(result) is not Task025ValidResult:
        return False, "binding_input_type_invalid"
    try:
        if result.layout_hash != layout.layout_hash:
            return False, "layout_hash_mismatch"
        identity = result.task021_identity
        if type(identity) is not FrozenIdentity:
            return False, "task025_task021_identity_type_invalid"
        if (
            identity.identity_type != "task021.tube-layout.v1"
            or identity.identity_id != layout.layout_id
            or identity.identity_hash != layout.layout_hash
        ):
            return False, "task025_task021_identity_mismatch"
        if layout.layout_hash not in result.provenance.upstream_identity_hashes:
            return False, "task025_provenance_layout_identity_missing"
        if type(result.active_position_ids) is not tuple or not result.active_position_ids:
            return False, "active_position_ids_empty"
        if type(result.inactive_position_ids) is not tuple:
            return False, "inactive_position_ids_invalid"
        all_ids = result.active_position_ids + result.inactive_position_ids
        if any(not _is_non_empty_string(item) for item in all_ids):
            return False, "position_ids_invalid"
        if len(set(all_ids)) != len(all_ids):
            return False, "position_partition_duplicate"
        if not set(result.active_position_ids).isdisjoint(result.inactive_position_ids):
            return False, "position_partition_overlap"
        if type(result.heat_transfer_authority) is not HeatTransferLengthAuthority:
            return False, "heat_transfer_authority_invalid"
        validate_positive_finite_decimal(
            result.heat_transfer_authority.length_m,
            "task025.heat_transfer_authority.length_m",
        )
    except AttributeError:
        return False, "task025_provenance_invalid"
    except (TypeError, ValueError):
        return False, "task025_binding_invalid"
    return True, "PASS"


def geometry_decimals(layout: TubeLayout) -> tuple[Decimal, Decimal, Decimal]:
    geometry = layout.tube_geometry
    try:
        inner = Decimal(geometry.inner_diameter_m)
        outer = Decimal(geometry.outer_diameter_m)
        wall = Decimal(geometry.wall_thickness_m)
    except Exception as exc:
        raise ValueError("TASK021 geometry dimensions are not Decimal strings") from exc
    validate_positive_finite_decimal(inner, "tube_inner_diameter_m")
    validate_positive_finite_decimal(outer, "tube_outer_diameter_m")
    validate_positive_finite_decimal(wall, "wall_thickness_m")
    if outer <= inner:
        raise ValueError("outer diameter must exceed inner diameter")
    if wall != (outer - inner) / Decimal(2):
        raise ValueError("wall thickness is inconsistent with tube diameters")
    return inner, outer, wall


def build_surface_projection(layout: TubeLayout, result: Task025ValidResult) -> dict[str, Any]:
    inner, outer, _ = geometry_decimals(layout)
    return {
        "task021_layout_hash": layout.layout_hash,
        "task025_result_hash": result.result_hash,
        "task025_hydraulic_authority_hash": result.hydraulic_authority_hash,
        "tube_geometry_snapshot_hash": layout.tube_geometry.snapshot_hash,
        "tube_inner_diameter_m": inner,
        "tube_outer_diameter_m": outer,
        "tube_side_film_reference_surface": TUBE_SIDE_FILM_REFERENCE_SURFACE,
        "overall_u_reference_surface": OVERALL_U_REFERENCE_SURFACE,
        "outer_to_inner_area_ratio": outer / inner,
        "engineering_source_id": ENGINEERING_SOURCE_ID,
        "engineering_source_locations": ENGINEERING_SOURCE_LOCATIONS,
    }


def build_wall_projection(
    *,
    surface_hash: str,
    result: Task025ValidResult,
    material: TubeWallMaterialAuthority,
    conductivity: TubeWallThermalConductivityAuthority,
    wall_bundle_conduction_resistance_k_w: Decimal,
    wall_resistance_outer_surface_m2_k_w: Decimal,
) -> dict[str, Any]:
    return {
        "surface_transform_authority_hash": surface_hash,
        "task025_result_hash": result.result_hash,
        "task025_hydraulic_authority_hash": result.hydraulic_authority_hash,
        "task025_internal_heat_transfer_surface_area_m2": (
            result.internal_heat_transfer_surface_area_m2
        ),
        "task025_area_quantum_m2": Decimal("1E-10"),
        "task025_area_rounding_mode": "ROUND_HALF_EVEN",
        "producer_area_precision_policy_id": (
            "task037.task025-public-area-authority.accept-positive-v1"
        ),
        "producer_area_precision_policy_hash": PRODUCER_AREA_PRECISION_POLICY_HASH,
        "producer_precision_limitation_disclosed": True,
        "producer_precision_threshold_defined": False,
        "wall_bundle_numerical_basis": WALL_BUNDLE_NUMERICAL_BASIS,
        "wall_material_authority_hash": material.authority_hash,
        "wall_conductivity_authority_hash": conductivity.authority_hash,
        "wall_bundle_conduction_resistance_k_w": wall_bundle_conduction_resistance_k_w,
        "wall_resistance_outer_surface_m2_k_w": wall_resistance_outer_surface_m2_k_w,
        "engineering_source_id": ENGINEERING_SOURCE_ID,
        "engineering_source_location": ENGINEERING_SOURCE_LOCATION_WALL,
        "source_formula_identity": SOURCE_FORMULA_IDENTITY,
        "thin_wall_approximation_used": False,
    }


__all__ = [
    "build_surface_projection",
    "build_wall_projection",
    "geometry_decimals",
    "is_sha256_hex",
    "replay_task025_valid_result",
    "surface_transform_authority_hash",
    "validate_conductivity_authority",
    "validate_fouling_authority",
    "validate_material_authority",
    "validate_task021_layout",
    "validate_task021_task025_binding",
    "validate_task025_valid_result",
    "wall_resistance_authority_hash",
]


def validate_task025_valid_result(result: Any) -> tuple[bool, str]:
    return replay_task025_valid_result(result)
