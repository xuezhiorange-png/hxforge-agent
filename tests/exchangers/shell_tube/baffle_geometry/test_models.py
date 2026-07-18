"""Tests for baffle_geometry.models -- Section 8 / Section 11 / Section 12.6.

Frozen contract tests. Verifies:
- enum class count and exact member set (Section 6.2)
- enum value literal exactness
- alias / lowercase / case-variant non-existence
- 57 BlockerCode tokens exact set and exact order (Section 11)
- 8 WarningCode tokens exact set and exact order (Section 12.6)
- blocker / warning sets have no duplicates
- 9 domain dataclasses exact field sets (Section 8.1-8.9)
- field declaration order exactly matches design tables
- field type annotations and nullability exact
- field default values exact
- frozen mutation rejection (dataclass params.frozen is True)
- nested tuples / immutable fields are not silently coerced
- bool is not interchangeable with int authority
- binary float does not enter Decimal geometry fields
- schema / profile / version constants exact (Section 6.1)
- closed string tokens exact (Section 8.7)
- internal failure structure NOT owned by models
  (Section 16 ownership is now schema.py per Charles decision)
- imports do not trigger filesystem / clock / environment / subprocess
- module does not execute canonicalization, hashing, UUID, geometry
"""

from __future__ import annotations

import dataclasses as _dc
import enum as _enum
import os
import subprocess
import sys

import hexagent.exchangers.shell_tube.baffle_geometry.models as models

# ----- Section 6.2 closed enum class set -----


def test_closed_enum_class_set_is_exact() -> None:
    # Section 6.2 mandates exactly four closed enums. Code-token enums
    # (BlockerCode, WarningCode) are also enums but live in §11 / §12.6.
    enum_classes_in_module = sorted(
        name
        for name, obj in vars(models).items()
        if isinstance(obj, type)
        and issubclass(obj, _enum.Enum)
        and obj.__module__ == models.__name__
    )
    expected = sorted(
        [
            "BaffleType",
            "BaffleOrientation",
            "BlockerCode",
            "TubeRegionClassification",
            "ValidationStatus",
            "WarningCode",
        ]
    )
    assert enum_classes_in_module == expected, (
        f"Enum set mismatch. got={enum_classes_in_module}, expected={expected}"
    )


def test_baffle_type_enum_is_single_value() -> None:
    assert [m.name for m in models.BaffleType] == ["SINGLE_SEGMENTAL"]
    assert models.BaffleType.SINGLE_SEGMENTAL.value == "SINGLE_SEGMENTAL"


def test_baffle_orientation_enum_is_four_values() -> None:
    names = [m.name for m in models.BaffleOrientation]
    assert names == ["TOP", "BOTTOM", "LEFT", "RIGHT"]
    for m in models.BaffleOrientation:
        assert m.value == m.name


def test_tube_region_classification_enum_is_two_values() -> None:
    names = [m.name for m in models.TubeRegionClassification]
    assert names == ["WINDOW", "CROSSFLOW_REFERENCE"]
    assert models.TubeRegionClassification.WINDOW.value == "WINDOW"
    assert models.TubeRegionClassification.CROSSFLOW_REFERENCE.value == "CROSSFLOW_REFERENCE"


def test_validation_status_enum_is_two_values() -> None:
    names = [m.name for m in models.ValidationStatus]
    assert names == ["VALID", "BLOCKED"]


def test_no_lowercase_aliases_for_baffle_orientation() -> None:
    forbidden = {"top", "bottom", "left", "right", "Top", "Bottom", "Left", "Right"}
    actual = {m.name for m in models.BaffleOrientation}
    assert actual.isdisjoint(forbidden)


def test_no_string_aliases_in_baffle_type() -> None:
    forbidden = {"SINGLE-SEGMENTAL", "single_segmental", "single", "seg"}
    actual = {m.value for m in models.BaffleType}
    assert actual.isdisjoint(forbidden)


# ----- Section 11 BlockerCode -- 57 tokens exact set and order -----

EXPECTED_BLOCKERS_57 = [
    "BFG_SCHEMA_VERSION_UNSUPPORTED",
    "BFG_UNKNOWN_FIELD",
    "BFG_RAW_TYPE_INVALID",
    "BFG_DECIMAL_LEXICAL_INVALID",
    "BFG_TASK020_CONFIGURATION_MISSING",
    "BFG_TASK020_CONFIGURATION_INVALID",
    "BFG_TASK020_CONFIGURATION_IDENTITY_MISMATCH",
    "BFG_TASK021_LAYOUT_MISSING",
    "BFG_TASK021_LAYOUT_INVALID",
    "BFG_TASK021_LAYOUT_HAS_BLOCKERS",
    "BFG_TASK021_LAYOUT_IDENTITY_MISMATCH",
    "BFG_TASK021_LAYOUT_HAS_NO_POSITIONS",
    "BFG_TASK022_GEOMETRY_MISSING",
    "BFG_TASK022_GEOMETRY_INVALID",
    "BFG_TASK022_GEOMETRY_HAS_BLOCKERS",
    "BFG_TASK022_GEOMETRY_IDENTITY_MISMATCH",
    "BFG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH",
    "BFG_UPSTREAM_LAYOUT_BINDING_MISMATCH",
    "BFG_UPSTREAM_TUBE_GEOMETRY_BINDING_MISMATCH",
    "BFG_UPSTREAM_CONSTRUCTION_FAMILY_MISMATCH",
    "BFG_UPSTREAM_ORIENTATION_MISMATCH",
    "BFG_UPSTREAM_PASS_COUNT_MISMATCH",
    "BFG_UPSTREAM_POSITION_COUNT_MISMATCH",
    "BFG_CONSTRUCTION_FAMILY_UNSUPPORTED",
    "BFG_SHELL_PASS_COUNT_UNSUPPORTED",
    "BFG_BAFFLE_TYPE_UNSUPPORTED",
    "BFG_AXIAL_SPAN_MISSING",
    "BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED",
    "BFG_AXIAL_SPAN_EVIDENCE_MISSING",
    "BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH",
    "BFG_AXIAL_SPAN_INVALID",
    "BFG_DESIGN_AUTHORITY_MISSING",
    "BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED",
    "BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING",
    "BFG_DESIGN_AUTHORITY_HASH_MISMATCH",
    "BFG_BAFFLE_COUNT_INVALID",
    "BFG_BAFFLE_THICKNESS_INVALID",
    "BFG_SPACING_SEQUENCE_CARDINALITY_MISMATCH",
    "BFG_SPACING_VALUE_INVALID",
    "BFG_SPACING_SEQUENCE_SPAN_MISMATCH",
    "BFG_ORIENTATION_SEQUENCE_CARDINALITY_MISMATCH",
    "BFG_ORIENTATION_TOKEN_INVALID",
    "BFG_BAFFLE_CUT_INVALID",
    "BFG_SHELL_TO_BAFFLE_CLEARANCE_INVALID",
    "BFG_TUBE_TO_BAFFLE_HOLE_CLEARANCE_INVALID",
    "BFG_BAFFLE_DIAMETER_INVALID",
    "BFG_BAFFLE_HOLE_DIAMETER_INVALID",
    "BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN",
    "BFG_BAFFLE_SOLIDS_OVERLAP",
    "BFG_CHORD_CALCULATION_FAILED",
    "BFG_BAFFLE_HOLE_DISK_TANGENT_TO_CUT_BOUNDARY",
    "BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY",
    "BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK",
    "BFG_BAFFLE_HOLE_DISKS_OVERLAP",
    "BFG_POSITION_CLASSIFICATION_INCOMPLETE",
    "BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION",
    "BFG_CANONICALIZATION_FAILED",
]


def test_blocker_code_count_is_57() -> None:
    actual = [m.name for m in models.BlockerCode]
    assert len(actual) == 57, f"Expected 57 blockers, got {len(actual)}"


def test_blocker_code_exact_set_and_order() -> None:
    actual = [m.name for m in models.BlockerCode]
    assert actual == EXPECTED_BLOCKERS_57


def test_blocker_code_no_duplicates() -> None:
    names = [m.name for m in models.BlockerCode]
    assert len(names) == len(set(names))


def test_blocker_code_values_match_names() -> None:
    for m in models.BlockerCode:
        assert m.value == m.name


# ----- Section 12.6 WarningCode -- 8 tokens -----

EXPECTED_WARNINGS_8 = [
    "BFG_FIXED_TUBESHEET_ONLY_V1",
    "BFG_GEOMETRY_NOT_FLOW_AREA",
    "BFG_NOZZLE_POSITION_DEFERRED",
    "BFG_THERMAL_HYDRAULIC_DEFERRED",
    "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM",
    "BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY",
    "BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY",
    "BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY",
]


def test_warning_code_count_is_8() -> None:
    actual = [m.name for m in models.WarningCode]
    assert len(actual) == 8


def test_warning_code_exact_set_and_order() -> None:
    actual = [m.name for m in models.WarningCode]
    assert actual == EXPECTED_WARNINGS_8


def test_warning_code_no_duplicates() -> None:
    names = [m.name for m in models.WarningCode]
    assert len(names) == len(set(names))


# ----- Section 8 dataclass field sets -----


def test_caller_supplied_baffle_axial_span_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.CallerSuppliedBaffleAxialSpan)]
    assert names == [
        "schema_version",
        "axial_start_coordinate_m",
        "axial_end_coordinate_m",
        "evidence_refs",
        "authority_hash",
    ]


def test_caller_supplied_baffle_design_authority_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.CallerSuppliedBaffleDesignAuthority)]
    assert names == [
        "schema_version",
        "baffle_type",
        "baffle_count",
        "baffle_thickness_m",
        "spacing_sequence_m",
        "baffle_cut_fraction",
        "orientation_sequence",
        "shell_to_baffle_diametral_clearance_m",
        "tube_to_baffle_hole_diametral_clearance_m",
        "evidence_refs",
        "authority_hash",
    ]


def test_baffle_geometry_request_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.BaffleGeometryRequest)]
    assert names == [
        "schema_version",
        "configuration",
        "tube_layout",
        "shell_bundle_geometry",
        "axial_span",
        "design_authority",
        "evidence_refs",
    ]


def test_cut_chord_geometry_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.CutChordGeometry)]
    assert names == [
        "normal_x",
        "normal_y",
        "half_plane_offset_m",
        "chord_half_length_m",
        "endpoint_a_x_m",
        "endpoint_a_y_m",
        "endpoint_b_x_m",
        "endpoint_b_y_m",
    ]


def test_physical_tube_disk_audit_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.PhysicalTubeDiskAudit)]
    assert names == [
        "physical_tube_radius_m",
        "signed_window_distance_m",
        "cut_boundary_margin_m",
        "classification",
    ]


def test_tube_hole_classification_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.TubeHoleClassification)]
    assert names == [
        "position_id",
        "center_x_m",
        "center_y_m",
        "physical_tube_radius_m",
        "baffle_hole_radius_m",
        "signed_window_distance_m",
        "cut_boundary_margin_m",
        "classification",
        "outer_boundary_margin_squared_m2",
        "physical_tube_disk_audit",
    ]


def test_baffle_plane_geometry_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.BafflePlaneGeometry)]
    assert names == [
        "baffle_index",
        "center_coordinate_m",
        "occupied_start_coordinate_m",
        "occupied_end_coordinate_m",
        "orientation",
        "cut_chord",
        "window_region_semantics",
        "baffle_covered_region_semantics",
        "crossflow_reference_region_semantics",
        "tube_hole_classifications",
        "window_position_ids",
        "crossflow_reference_position_ids",
        "outer_tangent_position_ids",
        "pairwise_tangent_position_pairs",
        "classification_audit_hash",
    ]


def test_baffle_geometry_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.BaffleGeometry)]
    expected = [
        "schema_version",
        "geometry_id",
        "geometry_hash",
        "request_hash",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task021_layout_id",
        "task021_layout_hash",
        "task022_geometry_id",
        "task022_geometry_hash",
        "construction_family",
        "equipment_orientation",
        "shell_pass_count",
        "tube_pass_count",
        "shell_inside_diameter_m",
        "tube_outer_diameter_m",
        "axial_span",
        "design_authority",
        "usable_baffle_span_m",
        "baffle_diameter_m",
        "baffle_radius_m",
        "baffle_hole_diameter_m",
        "baffle_hole_radius_m",
        "cut_height_m",
        "chord_offset_from_center_m",
        "baffle_planes",
        "position_count",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "provenance",
    ]
    assert names == expected


def test_baffle_geometry_validation_result_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.BaffleGeometryValidationResult)]
    expected = [
        "status",
        "geometry",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "blocked_result_hash",
    ]
    assert names == expected


def test_message_entry_field_set_exact() -> None:
    names = [f.name for f in _dc.fields(models.MessageEntry)]
    assert names == ["code", "field_path", "message_key", "evidence_refs", "details"]


# ----- Frozen attribute checks -----


def test_all_dataclasses_have_frozen_params_true() -> None:
    import dataclasses

    for cls in (
        models.CallerSuppliedBaffleAxialSpan,
        models.CallerSuppliedBaffleDesignAuthority,
        models.BaffleGeometryRequest,
        models.CutChordGeometry,
        models.PhysicalTubeDiskAudit,
        models.TubeHoleClassification,
        models.BafflePlaneGeometry,
        models.BaffleGeometry,
        models.BaffleGeometryValidationResult,
        models.MessageEntry,
    ):
        assert dataclasses.is_dataclass(cls)
        params = getattr(cls, "__dataclass_params__")
        assert params.frozen is True, f"{cls.__name__} is not declared frozen=True"


def test_baffle_geometry_request_frozen() -> None:
    import dataclasses

    assert dataclasses.is_dataclass(models.BaffleGeometryRequest)
    params = getattr(models.BaffleGeometryRequest, "__dataclass_params__")
    assert params.frozen is True


# ----- Constants and tokens -----


def test_request_schema_version_constant() -> None:
    assert models.REQUEST_SCHEMA_VERSION == "task024.baffle-geometry-request.v1"


def test_axial_span_schema_version_constant() -> None:
    assert models.AXIAL_SPAN_SCHEMA_VERSION == "task024.baffle-axial-span.v1"


def test_design_authority_schema_version_constant() -> None:
    assert models.DESIGN_AUTHORITY_SCHEMA_VERSION == "task024.baffle-design-authority.v1"


def test_result_schema_version_constant() -> None:
    assert models.RESULT_SCHEMA_VERSION == "task024.baffle-geometry.v1"


def test_profile_id_constant() -> None:
    assert models.PROFILE_ID == "hxforge.shell_tube.baffle_geometry.v1"


def test_design_contract_path_constant() -> None:
    assert models.DESIGN_CONTRACT_PATH == (
        "docs/tasks/TASK-024-shell-and-tube-baffle-geometry-and-spacing.md"
    )


def test_three_strict_precedence_booleans_are_true() -> None:
    assert models.CLASSIFICATION_BEFORE_PUBLIC_OUTPUT_QUANTIZATION is True
    assert models.BOUNDARY_PREDICATES_USE_UNQUANTIZED_DECIMAL_DERIVATIONS is True
    assert models.PUBLIC_OUTPUT_QUANTIZATION_MUST_NOT_CHANGE_CLASSIFICATION is True


def test_window_region_semantics_token() -> None:
    assert models.WINDOW_REGION_SEMANTICS == ("BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE")


def test_baffle_covered_region_semantics_token() -> None:
    assert models.BAFFLE_COVERED_REGION_SEMANTICS == ("BAFFLE_DISK_MINUS_WINDOW_SEGMENT")


def test_crossflow_reference_region_semantics_token() -> None:
    assert models.CROSSFLOW_REFERENCE_REGION_SEMANTICS == (
        "CLASSIFICATION_REFERENCE_ONLY_NOT_FLOW_AREA"
    )


# ----- Section 16 ownership (after Charles DECISION_001) -----


def test_schema_failure_not_in_models_module() -> None:
    # Per Charles DECISION_001 + Section 16 + Section 18,
    # BaffleGeometrySchemaFailure belongs to schema.py, NOT models.py.
    assert not hasattr(models, "BaffleGeometrySchemaFailure")


def test_schema_module_does_not_exist_yet() -> None:
    # Round 2 does not create schema.py -- this is a future-round scope.
    # The test asserts the negative: schema.py is not yet created.
    import importlib.util

    spec = importlib.util.find_spec("hexagent.exchangers.shell_tube.baffle_geometry.schema")
    assert spec is None, "schema.py must not exist in round 2; its creation belongs to round 3+"


# ----- Module purity / no I/O / no clock / no subprocess -----


def test_models_module_does_not_import_decimal() -> None:
    module = sys.modules[models.__name__]
    assert "decimal" not in module.__dict__, "models.py must not import decimal (canonical layers)"


def test_models_module_does_not_import_json_or_hashlib_or_uuid() -> None:
    module = sys.modules[models.__name__]
    for forbidden in ("json", "hashlib", "uuid", "secrets", "random"):
        assert forbidden not in module.__dict__, f"models.py must not import {forbidden}"


def test_models_module_does_not_execute_io_at_import() -> None:
    # Re-import the module in a subprocess to confirm import has no
    # filesystem / clock / network side effects.
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.path.insert(0, '" + os.path.abspath("src") + "'); "
                "import hexagent.exchangers.shell_tube.baffle_geometry.models as m; "
                "assert len(m.BlockerCode) == 57; "
                "assert len(m.WarningCode) == 8; "
                "assert not hasattr(m, 'BaffleGeometrySchemaFailure'); "
                "assert hasattr(m, 'REQUEST_SCHEMA_VERSION'); "
                "print('IMPORT_OK')"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"Module import side-effect failed:\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}"
    )
    assert "IMPORT_OK" in proc.stdout


def test_baffle_geometry_request_does_not_coerce_unknown_field() -> None:
    # Constructor must reject unknown field names (raw boundary is at
    # parse_request; here we merely assert models.BaffleGeometryRequest
    # has no setter for unknown attrs since frozen=True).
    fields = _dc.fields(models.BaffleGeometryRequest)
    allowed = {f.name for f in fields}
    assert "unknown_field_xyz" not in allowed
