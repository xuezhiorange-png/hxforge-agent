"""TASK037 controlled-implementation contract tests."""

from __future__ import annotations

import inspect
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import hexagent.exchangers.shell_tube.tube_side as tube_side
from hexagent.exchangers.shell_tube import validate_request as validate_task020_request
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance import (
    BLOCKER_COUNT,
    BLOCKER_REGISTRY,
    COMPLETENESS_ROWS,
    DEFERRED_CAPABILITIES,
    ENGINEERING_SOURCE_ID,
    ENGINEERING_SOURCE_LOCATION_WALL,
    ENGINEERING_SOURCE_LOCATIONS,
    FOULING_AUTHORITY_FIELDS,
    FROZEN_IDENTITY_FIELDS,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII,
    PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII_BYTES,
    PRODUCER_AREA_PRECISION_POLICY_HASH,
    PRODUCER_AREA_PRECISION_POLICY_ID,
    PROVENANCE_FIELDS,
    PROVENANCE_PREHASH_FIELDS,
    R7_FINAL_RUNTIME_DESIGN_AUTHORITY,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_FIELDS,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    SELF_EDGE_COUNT,
    SUCCESS_RESULT_FIELDS,
    SURFACE_TRANSFORM_FIELDS,
    TASK025_AREA_QUANTUM_M2,
    TASK025_AREA_ROUNDING_MODE,
    TASK025_PUBLIC_AREA_PRECISION_POLICY_ID,
    TASK025_PUBLIC_AREA_QUANTUM_M2,
    TASK025_PUBLIC_AREA_ROUNDING_MODE,
    TASK037_VERSION,
    TASK037_WARNING_CODE_COUNT,
    TASK037_WARNING_REGISTRY,
    TYPED_BLOCKED_RESULT_SCHEMA_VERSION,
    UUID_NAME_PREFIX,
    UUID_NAMESPACE,
    WALL_RESISTANCE_FIELDS,
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
    typed_blocked_result_hash,
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.canonical import (
    frame_record,
    frame_string_tuple,
    frame_value,
    provenance_bytes,
    provenance_hash,
    result_id_from_hash,
    sha256_hex,
    surface_transform_authority_bytes,
    surface_transform_authority_hash,
    wall_resistance_authority_bytes,
    wall_resistance_authority_hash,
)
from hexagent.exchangers.shell_tube.tube_layout import ValidationStatus
from hexagent.exchangers.shell_tube.tube_layout import validate_request as validate_task021_request
from hexagent.exchangers.shell_tube.tube_side import heat_transfer_authority_length_hash
from scripts.release_demo.v0_1_task020_to_task026 import (
    _build_t020_request,
    _build_t021_request,
)
from tests.exchangers.shell_tube.overall_heat_transfer_resistance import (
    task037_frozen_vectors as vectors,
)
from tests.exchangers.shell_tube.overall_heat_transfer_resistance.task037_frozen_vectors import (
    APPLICABILITY_LEDGER,
    CANONICAL_CODEC_PROBES,
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


def _production_inputs():
    task020_result = validate_task020_request(_build_t020_request())
    assert task020_result.status.value == "VALID"
    assert task020_result.configuration is not None
    payload = _build_t021_request(task020_result.configuration)
    task021_result = validate_task021_request(
        payload,
        software_version="0.1.0",
        git_commit="task037-public-replay",
    )
    assert task021_result.status is ValidationStatus.VALID
    assert task021_result.layout is not None
    return task020_result.configuration, task021_result.layout


def _production_layout():
    return _production_inputs()[1]


def _production_task025():
    config, layout = _production_inputs()
    result = tube_side.evaluate_task025(_request_input(config, layout))
    assert isinstance(result, tube_side.Task025ValidResult)
    return layout, result


def _task037_request(evidence_refs: tuple[str, ...] = ("fixture",)) -> Task037Request:
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
    return Task037Request(
        REQUEST_SCHEMA_VERSION,
        TASK037_VERSION,
        IMPLEMENTATION_SOFTWARE_VERSION,
        material,
        conductivity,
        inside,
        outside,
        evidence_refs,
    )


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
    surface_variant = dict(SURFACE)
    wall_variant = dict(WALL)
    assert (
        surface_transform_authority_hash(SURFACE)
        == surface_transform_authority_hash(surface_variant)
        == SURFACE_HASH
    )
    assert (
        wall_resistance_authority_hash(WALL)
        == wall_resistance_authority_hash(wall_variant)
        == WALL_HASH
    )
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


def test_frozen_schema_and_policy_inventory_is_exact() -> None:
    assert REQUEST_FIELDS == (
        "schema_version",
        "task037_version",
        "implementation_software_version",
        "wall_material_authority",
        "wall_thermal_conductivity_authority",
        "inside_fouling_authority",
        "outside_fouling_authority",
        "evidence_refs",
    )
    assert SURFACE_TRANSFORM_FIELDS == (
        "task021_layout_hash",
        "task025_result_hash",
        "task025_hydraulic_authority_hash",
        "tube_geometry_snapshot_hash",
        "tube_inner_diameter_m",
        "tube_outer_diameter_m",
        "tube_side_film_reference_surface",
        "overall_u_reference_surface",
        "outer_to_inner_area_ratio",
        "engineering_source_id",
        "engineering_source_locations",
    )
    assert tuple(WALL) == WALL_RESISTANCE_FIELDS
    assert FOULING_AUTHORITY_FIELDS == (
        "authority_id",
        "reference_surface",
        "resistance_value_m2_k_w",
        "resistance_units",
        "fluid_service_id",
        "source_id",
        "source_version",
        "source_location",
        "permission_status",
        "approval_status",
        "applicability",
        "authority_hash",
    )
    assert FROZEN_IDENTITY_FIELDS == ("identity_type", "identity_id", "identity_hash")
    assert len(SUCCESS_RESULT_FIELDS) == 23
    assert len(PROVENANCE_FIELDS) == 31
    assert len(PROVENANCE_PREHASH_FIELDS) == 30
    assert len(COMPLETENESS_ROWS) == 6
    assert RESULT_SCHEMA_VERSION == "task037.success-result.v1"
    assert TYPED_BLOCKED_RESULT_SCHEMA_VERSION == "task037.typed-blocked-result.v1"
    assert RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION == "task037.raw-boundary-blocked-result.v1"
    assert UUID_NAMESPACE == "a0370000-0000-5000-8000-000000000037"
    assert UUID_NAME_PREFIX == "task037-result-v1::"
    assert SURFACE["engineering_source_id"] == ENGINEERING_SOURCE_ID
    assert SURFACE["engineering_source_locations"] == ENGINEERING_SOURCE_LOCATIONS
    assert WALL["engineering_source_id"] == ENGINEERING_SOURCE_ID
    assert WALL["engineering_source_location"] == ENGINEERING_SOURCE_LOCATION_WALL
    assert Decimal("1E-10") == TASK025_AREA_QUANTUM_M2
    assert TASK025_AREA_ROUNDING_MODE == "ROUND_HALF_EVEN"
    assert PRODUCER_AREA_PRECISION_POLICY_ID == TASK025_PUBLIC_AREA_PRECISION_POLICY_ID
    assert len(PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII.encode("ascii")) == (
        PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII_BYTES
    )
    assert producer_area_precision_policy_hash() == PRODUCER_AREA_PRECISION_POLICY_HASH
    assert len(BLOCKER_REGISTRY) == BLOCKER_COUNT == 22
    assert TASK037_WARNING_CODE_COUNT == 0
    assert TASK037_WARNING_REGISTRY == ()
    assert SELF_EDGE_COUNT == 0


def test_ten_static_codec_framing_probes_match_frozen_bytes_and_hashes() -> None:
    computed = {
        "none": frame_value("NONE", b""),
        "bool_true": frame_value("BOOL_TRUE", b""),
        "bool_false": frame_value("BOOL_FALSE", b""),
        "int": frame_value("INT", b"-7"),
        "string_utf8": frame_value("STRING", "hé".encode()),
        "decimal": frame_value("DECIMAL", b"1E-10"),
        "enum": frame_value("ENUM", b"INNER_TUBE_SURFACE"),
        "tuple_utf8": frame_value("TUPLE", frame_string_tuple(("a", "é"))),
        "record": frame_record("probe.v1", (("value", b"STRING", b"v"),)),
        "nested_record": frame_value(
            "RECORD", frame_record("nested.v1", (("value", b"STRING", b"v"),))
        ),
    }
    assert len(CANONICAL_CODEC_PROBES) == 10
    for name, expected_hex, expected_hash in CANONICAL_CODEC_PROBES:
        encoded = computed[name]
        assert encoded.hex() == expected_hex
        assert sha256_hex(encoded) == expected_hash


def test_gv06_low_scale_public_area_precision_vector_is_static() -> None:
    outputs = compute_wall_resistance(
        Decimal("0.001"), Decimal("0.0012"), Decimal("16"), Decimal("1E-10")
    )
    assert outputs.wall_bundle_conduction_resistance_k_w == vectors.GV06_WALL_BUNDLE
    assert Decimal("90679.303112398787371") == vectors.GV06_SOURCE_DIRECT_REFERENCE
    assert (
        Decimal(
            "-0.37168146928204135230747132334409942316056612012497883580501108153843671874275820027439303493157658642"
        )
        == vectors.GV06_RELATIVE_DIVERGENCE
    )


def test_noncanonical_task025_public_area_blocks_at_s03() -> None:
    layout, task025_result = _production_task025()
    noncanonical = replace(
        task025_result,
        internal_heat_transfer_surface_area_m2=Decimal("0.03141592651"),
    )
    result = evaluate_task037(_task037_request(), layout, noncanonical)
    assert result.status == "BLOCKED"
    assert result.blocked_result is not None
    blocked = result.blocked_result
    assert blocked.failure_stage == "S03_TASK025_UPSTREAM_VALIDATION"
    assert len(blocked.blockers) == 1
    assert blocked.blockers[0].code == "T037_TASK025_AREA_QUANTUM_NONCANONICAL"
    assert blocked.blockers[0].field_path == (
        "task025_result.internal_heat_transfer_surface_area_m2"
    )
    assert blocked.blocked_result_hash == typed_blocked_result_hash(blocked)


def test_typed_task025_blocker_is_forwarded_without_synthetic_success() -> None:
    layout = _production_layout()
    task025_blocked = tube_side.evaluate_task025(None)
    assert isinstance(task025_blocked, tube_side.Task025BlockedResult)
    result = evaluate_task037(_task037_request(), layout, task025_blocked)
    assert result.status == "BLOCKED"
    assert result.typed_blocked_result is not None
    blocked = result.typed_blocked_result
    assert blocked.failure_stage == "S03_TASK025_UPSTREAM_VALIDATION"
    assert blocked.blockers[0].code == "T037_TASK025_BLOCKED"
    assert blocked.blockers[0].field_path == "task025_result"
    assert blocked.blocked_result_hash == typed_blocked_result_hash(blocked)


def test_shadow_heat_transfer_length_does_not_change_numeric_authority() -> None:
    layout, task025_result = _production_task025()
    original_request = _task037_request(("fixture-a",))
    shadow_length = Decimal("0.75")
    shadow_authority = replace(
        task025_result.heat_transfer_authority,
        length_m=shadow_length,
        length_hash=heat_transfer_authority_length_hash(
            shadow_length,
            task025_result.heat_transfer_authority.start_plane,
            task025_result.heat_transfer_authority.end_plane,
            task025_result.heat_transfer_authority.authority_mode,
        ),
    )
    shadow_task025_result = replace(
        task025_result,
        heat_transfer_authority=shadow_authority,
    )
    original = evaluate_task037(original_request, layout, task025_result)
    shadow = evaluate_task037(original_request, layout, shadow_task025_result)
    assert original.status == shadow.status == "VALID"
    assert original.success_result is not None
    assert shadow.success_result is not None
    original_result = original.success_result
    shadow_result = shadow.success_result
    assert original_result.surface_transform_authority_hash == (
        shadow_result.surface_transform_authority_hash
    )
    assert original_result.wall_bundle_conduction_resistance_k_w == (
        shadow_result.wall_bundle_conduction_resistance_k_w
    )
    assert original_result.wall_resistance_outer_surface_m2_k_w == (
        shadow_result.wall_resistance_outer_surface_m2_k_w
    )
    assert original_result.outer_to_inner_area_ratio == shadow_result.outer_to_inner_area_ratio
    assert original_result.provenance.heat_transfer_length_hash != (
        shadow_result.provenance.heat_transfer_length_hash
    )
    assert original_result.result_hash != shadow_result.result_hash
    assert original_result.result_id != shadow_result.result_id


def test_identity_verifier_replays_without_engineering_recomputation() -> None:
    layout, task025_result = _production_task025()
    result = evaluate_task037(_task037_request(), layout, task025_result)
    assert result.success_result is not None
    with patch(
        "hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation.compute_wall_resistance",
        side_effect=AssertionError("engineering must not be rerun by verifier"),
    ):
        assert verify_task037_success_identity(result.success_result)


def test_task021_geometry_snapshot_tamper_blocks_before_engineering() -> None:
    layout, task025_result = _production_task025()

    for field_name, tampered_value in (
        ("inner_diameter_m", "0.015"),
        ("outer_diameter_m", "0.021"),
        ("wall_thickness_m", "0.0021"),
    ):
        tampered_geometry = replace(
            layout.tube_geometry,
            **{field_name: tampered_value},
        )
        tampered_layout = replace(layout, tube_geometry=tampered_geometry)
        with (
            patch(
                "hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation.build_surface_projection",
                side_effect=AssertionError("surface transform must not run"),
            ),
            patch(
                "hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation.compute_wall_resistance",
                side_effect=AssertionError("wall resistance must not run"),
            ),
        ):
            result = evaluate_task037(_task037_request(), tampered_layout, task025_result)

        assert result.status == "BLOCKED"
        assert result.typed_blocked_result is not None
        assert result.typed_blocked_result.failure_stage == "S02_TASK021_UPSTREAM_VALIDATION"
        assert result.typed_blocked_result.blockers[0].code == BlockerCode.TASK021_INVALID
        assert result.typed_blocked_result.blockers[0].message_key == (
            "task021_geometry_snapshot_identity_mismatch"
        )


def test_ci_manifest_registers_task037_contract_and_static_vectors() -> None:
    manifest = Path("ci-shard-manifest.yml").read_text(encoding="utf-8")
    assert (
        manifest.count(
            "tests/exchangers/shell_tube/overall_heat_transfer_resistance/test_task037_contract.py"
        )
        == 1
    )
    assert (
        manifest.count(
            "tests/exchangers/shell_tube/overall_heat_transfer_resistance/task037_frozen_vectors.py"
        )
        == 1
    )


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

    layout, task025_result = _production_task025()

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
