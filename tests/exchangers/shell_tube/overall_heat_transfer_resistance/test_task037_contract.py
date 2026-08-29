"""TASK037 controlled-implementation contract tests."""

from __future__ import annotations

import inspect
from dataclasses import replace
from decimal import Decimal

import hexagent.exchangers.shell_tube.tube_side as tube_side
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance import (
    DEFERRED_CAPABILITIES,
    IMPLEMENTATION_SOFTWARE_VERSION,
    R7_FINAL_RUNTIME_DESIGN_AUTHORITY,
    REQUEST_SCHEMA_VERSION,
    TASK025_PUBLIC_AREA_PRECISION_POLICY_ID,
    TASK025_PUBLIC_AREA_QUANTUM_M2,
    TASK025_PUBLIC_AREA_ROUNDING_MODE,
    TASK037_VERSION,
    BlockerCode,
    InsideFoulingResistanceAuthority,
    OutsideFoulingResistanceAuthority,
    Task037Request,
    TubeWallMaterialAuthority,
    TubeWallThermalConductivityAuthority,
    compute_wall_resistance,
    evaluate_task037,
    producer_area_precision_policy_hash,
    project_raw_value,
    success_result_hash,
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.canonical import (
    provenance_bytes,
    provenance_hash,
    result_id_from_hash,
    surface_transform_authority_bytes,
    surface_transform_authority_hash,
    wall_resistance_authority_bytes,
    wall_resistance_authority_hash,
)
from tests.exchangers.shell_tube.overall_heat_transfer_resistance import (
    task037_frozen_vectors as vectors,
)
from tests.exchangers.shell_tube.overall_heat_transfer_resistance.task037_frozen_vectors import (
    APPLICABILITY_LEDGER,
    COMPLETENESS_LEDGER,
    INSIDE_FOULING,
    POLICY_HASH,
    PROVENANCE_HASH_A,
    PROVENANCE_HASH_B,
    REQUEST_HASH_A,
    REQUEST_HASH_B,
    RESULT_HASH_A,
    RESULT_HASH_B,
    RESULT_ID_A,
    RESULT_ID_B,
    SURFACE,
    SURFACE_HASH,
    WALL,
    WALL_HASH,
    provenance_fixture,
    result_fixture,
)
from tests.exchangers.shell_tube.tube_side.test_a09_scheduler import _request_input
from tests.fixtures.shell_and_tube.tube_side.task020_configurations import config_a
from tests.fixtures.shell_and_tube.tube_side.task021_layouts import layout_a


def test_r7_static_surface_and_wall_literals_are_primary_oracles() -> None:
    assert len(surface_transform_authority_bytes(SURFACE)) == 1041
    assert surface_transform_authority_hash(SURFACE) == SURFACE_HASH
    assert len(wall_resistance_authority_bytes(WALL)) == 1724
    assert wall_resistance_authority_hash(WALL) == WALL_HASH
    assert producer_area_precision_policy_hash() == POLICY_HASH


def test_r7_static_downstream_literals_and_uuid5_are_exact() -> None:
    provenance_a = provenance_fixture(REQUEST_HASH_A, PROVENANCE_HASH_A)
    provenance_b = provenance_fixture(REQUEST_HASH_B, PROVENANCE_HASH_B)
    result_a = result_fixture(REQUEST_HASH_A, provenance_a)
    result_b = result_fixture(REQUEST_HASH_B, provenance_b)
    assert len(provenance_bytes(provenance_a)) == 3234
    assert len(provenance_bytes(provenance_b)) == 3234
    assert provenance_hash(provenance_a) == PROVENANCE_HASH_A
    assert provenance_hash(provenance_b) == PROVENANCE_HASH_B
    assert len(vectors.result_fixture(REQUEST_HASH_A, provenance_a)) > 0
    assert success_result_hash(result_a) == RESULT_HASH_A
    assert result_id_from_hash(RESULT_HASH_A) == RESULT_ID_A
    assert success_result_hash(result_b) == RESULT_HASH_B
    assert result_id_from_hash(RESULT_HASH_B) == RESULT_ID_B


def test_request_variant_preserves_surface_and_wall_but_changes_downstream() -> None:
    provenance_a = provenance_fixture(REQUEST_HASH_A, PROVENANCE_HASH_A)
    provenance_b = provenance_fixture(REQUEST_HASH_B, PROVENANCE_HASH_B)
    result_a = result_fixture(REQUEST_HASH_A, provenance_a)
    result_b = result_fixture(REQUEST_HASH_B, provenance_b)
    assert surface_transform_authority_hash(SURFACE) == surface_transform_authority_hash(SURFACE)
    assert wall_resistance_authority_hash(WALL) == wall_resistance_authority_hash(WALL)
    assert provenance_hash(provenance_a) != provenance_hash(provenance_b)
    assert success_result_hash(result_a) != success_result_hash(result_b)
    assert result_id_from_hash(RESULT_HASH_A) != result_id_from_hash(RESULT_HASH_B)


def test_wall_engineering_uses_public_area_only() -> None:
    signature = inspect.signature(compute_wall_resistance)
    assert "task025_internal_heat_transfer_surface_area_m2" in signature.parameters
    assert "heat_transfer_length_m" not in signature.parameters
    assert "active_position_count" not in signature.parameters
    outputs = compute_wall_resistance(
        Decimal("0.020"), Decimal("0.024"), Decimal("16"), Decimal("0.0314159265")
    )
    assert outputs.outer_to_inner_area_ratio == Decimal("1.200000000000000")
    assert outputs.wall_bundle_conduction_resistance_k_w == Decimal("0.003627172128641")
    assert outputs.wall_resistance_outer_surface_m2_k_w == Decimal("0.000136741167595")


def test_source_r3_precision_policy_is_explicit() -> None:
    assert TASK025_PUBLIC_AREA_QUANTUM_M2 == "1E-10"
    assert TASK025_PUBLIC_AREA_ROUNDING_MODE == "ROUND_HALF_EVEN"
    assert TASK025_PUBLIC_AREA_PRECISION_POLICY_ID.endswith("accept-positive-v1")
    assert DEFERRED_CAPABILITIES == (
        "OVERALL_U",
        "UA",
        "LMTD",
        "HEAT_DUTY",
        "OUTLET_TEMPERATURES",
        "FULL_EXCHANGER_THERMAL_RATING",
    )
    assert R7_FINAL_RUNTIME_DESIGN_AUTHORITY == "R7_FINAL_FROZEN"


def test_raw_boundary_does_not_execute_hostile_object_protocols() -> None:
    class Hostile:
        def __repr__(self) -> str:
            raise AssertionError("repr must not be called")

        def __iter__(self):
            raise AssertionError("iteration must not be called")

        @property
        def value(self) -> str:
            raise AssertionError("property must not be called")

    projection = project_raw_value(Hostile())
    assert projection.projection_kind == "task037.raw-boundary.v1"
    result = evaluate_task037(Hostile(), Hostile(), Hostile())
    assert result.status == "BLOCKED"
    assert result.raw_boundary_blocked_result is not None
    assert result.raw_boundary_blocked_result.blockers[0].code == BlockerCode.RAW_INPUT_TYPE_INVALID


def test_static_ledgers_remain_ordered() -> None:
    assert APPLICABILITY_LEDGER[0] == "A01_TASK021_VALID=PASS"
    assert APPLICABILITY_LEDGER[-1] == "A10_OUTSIDE_FOULING_AUTHORITY_ADMISSIBLE=PASS"
    assert COMPLETENESS_LEDGER[0] == "C01_SURFACE_BASIS_AUTHORITY_COMPLETE=PASS"
    assert INSIDE_FOULING["reference_surface"] == "INNER_TUBE_SURFACE"


def test_actual_production_binding_reaches_valid_result() -> None:
    """Run TASK025 and TASK037 through their public production boundaries."""

    layout = layout_a()
    layout = replace(
        layout,
        tube_geometry=replace(layout.tube_geometry, inner_diameter_m="0.012"),
    )
    task025_result = tube_side.evaluate_task025(_request_input(config_a(), layout))
    assert isinstance(task025_result, tube_side.Task025ValidResult)

    material = TubeWallMaterialAuthority(
        "MAT-001",
        "MAT-001",
        "FIXTURE-GRADE",
        "FIXTURE-MATERIAL",
        "R1",
        "FIXTURE",
        "PUBLIC_DOMAIN",
        "PUBLIC_USE_PERMITTED",
        "APPROVED",
        ("fixture",),
        "a" * 64,
    )
    conductivity = TubeWallThermalConductivityAuthority(
        "COND-001",
        "MAT-001",
        Decimal("16"),
        Decimal("300"),
        "FIXTURE",
        "FIXTURE",
        "c" * 64,
        "FIXTURE-CONDUCTIVITY",
        "R1",
        "FIXTURE",
        "PUBLIC_DOMAIN",
        "PUBLIC_USE_PERMITTED",
        "APPROVED",
        ("fixture",),
        "b" * 64,
    )
    inside = InsideFoulingResistanceAuthority(
        "IN-001",
        "INSIDE",
        Decimal("0.0001"),
        "INNER_TUBE_SURFACE",
        "FIXTURE-IN",
        "FIXTURE-FOULING",
        "R1",
        "FIXTURE",
        "PROJECT_SPECIFICATION",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("fixture",),
        "d" * 64,
    )
    outside = OutsideFoulingResistanceAuthority(
        "OUT-001",
        "OUTSIDE",
        Decimal("0.0002"),
        "OUTER_TUBE_SURFACE",
        "FIXTURE-OUT",
        "FIXTURE-FOULING",
        "R1",
        "FIXTURE",
        "PROJECT_SPECIFICATION",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("fixture",),
        "e" * 64,
    )
    request = Task037Request(
        REQUEST_SCHEMA_VERSION,
        TASK037_VERSION,
        IMPLEMENTATION_SOFTWARE_VERSION,
        material,
        conductivity,
        inside,
        outside,
        ("fixture",),
    )

    result = evaluate_task037(request, layout, task025_result)
    assert result.status == "VALID"
    assert result.success_result is not None
    assert verify_task037_success_identity(result.success_result)
