"""Replay existing geometry and area producers, preserving native identities."""

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.baffle_geometry import validate_request
from hexagent.exchangers.shell_tube.baffle_geometry.models import BaffleGeometry
from hexagent.exchangers.shell_tube.baffle_geometry.schema import parse_request
from hexagent.exchangers.shell_tube.models import ConstructionFamily
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_outer_to_inner_area_ratio,
)
from hexagent.exchangers.shell_tube.tube_side.scheduler import evaluate_task025
from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult

from .canonical import number
from .errors import Code, Failure
from .models import NativeIdentity


def replay(
    baffle_request: Any, area_request: Any, expected: NativeIdentity
) -> tuple[BaffleGeometry, Task025ValidResult, str]:
    # The native public boundaries own raw admission, source validation,
    # provenance replay and geometry equations. No synthetic replacement result.
    baffle = validate_request(baffle_request)
    if baffle.geometry is None or baffle.blockers:
        raise Failure(Code.UPSTREAM_IDENTITY_MISMATCH, "task024")
    g = baffle.geometry
    parsed = parse_request(baffle_request)
    if parsed.configuration.component_tokens.shell != "E":
        raise Failure(Code.UNSUPPORTED_TOPOLOGY, "shell_type")
    if (
        g.construction_family != ConstructionFamily.FIXED_TUBESHEET.value
        or g.shell_pass_count != 1
        or g.tube_pass_count != 1
    ):
        raise Failure(Code.UNSUPPORTED_TOPOLOGY, "configuration")
    area = evaluate_task025(area_request)
    if type(area) is not Task025ValidResult:
        raise Failure(Code.UPSTREAM_IDENTITY_MISMATCH, "task025_area")
    actual = NativeIdentity(
        configuration_id=g.task020_configuration_id,
        configuration_hash=g.task020_configuration_hash,
        layout_id=g.task021_layout_id,
        layout_hash=g.task021_layout_hash,
        bundle_id=g.task022_geometry_id,
        bundle_hash=g.task022_geometry_hash,
        baffle_id=g.geometry_id,
        baffle_hash=g.geometry_hash,
        area_result_id=area.result_id,
        area_result_hash=area.result_hash,
    )
    if actual != expected or area.layout_hash != g.task021_layout_hash:
        raise Failure(Code.UPSTREAM_IDENTITY_MISMATCH, "native_identity")
    # TASK025 admitted active length must cover precisely the mapped axial span.
    length = number(str(area.heat_transfer_authority.length_m))
    if length != number(g.axial_span.axial_end_coordinate_m) - number(
        g.axial_span.axial_start_coordinate_m
    ):
        raise Failure(Code.INVALID_PHYSICAL_MAPPING, "heat_transfer_length")
    # Existing TASK037 cylindrical area transform, not a new area equation.
    ratio = compute_outer_to_inner_area_ratio(
        area.hydraulic_diameter_m, Decimal(g.tube_outer_diameter_m)
    )
    return g, area, str(ratio)
