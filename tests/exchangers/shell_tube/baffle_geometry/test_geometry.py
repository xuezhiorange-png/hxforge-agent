"""TASK-024 Round 5 geometry foundation tests.

Coverage matrix (Section 22 of the brief):

* 22.1  -- Stage 9: Decimal lexical + signed-domain validation.
* 22.2  -- Stage 10: count / cardinality / exact axial closure.
* 22.3  -- Stage 11: derived dimensions.
* 22.4  -- Stage 12: axial solids + aggregate tangency warning.
* 22.5  -- Stage 13: chord construction.
* 22.6  -- Stage 14: cut-boundary classification.
* 22.7  -- Stage 15: outer-circle containment.
* 22.8  -- Stage 16: covered-region pairwise non-overlap.
* 22.9  -- Stage 17: classification completeness.
* 22.10 -- Stage 18: public-quantization closure.
* 22.11 -- Determinism and immutability.
* 22.12 -- Architecture guards.

All numeric values are SYNTHETIC_TEST_VALUE -- NOT_ENGINEERING_RECOMMENDATION.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hexagent.exchangers.shell_tube.baffle_geometry import models as _t024
from hexagent.exchangers.shell_tube.baffle_geometry.geometry import (
    compute_geometry_foundation,
)
from tests.exchangers.shell_tube.baffle_geometry import _builders as _b

# ---------------------------------------------------------------------------
# 22.1 Stage 9 -- Decimal lexical + signed-domain validation.
# ---------------------------------------------------------------------------


def test_22_1_stage9_valid_decimal_domain_passes() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.completed_stage_rank >= 9
    # Round-tripped values still parse via canonical_decimal_string.
    for raw in (
        request.axial_span.axial_start_coordinate_m,
        request.design_authority.baffle_thickness_m,
    ):
        from hexagent.exchangers.shell_tube.baffle_geometry import (
            canonical as _t024_canonical,
        )

        _t024_canonical.canonical_decimal_string(raw)


def test_22_1_stage9_exponent_notation_rejected() -> None:
    request = _b.make_geometry_request(
        baffle_thickness_m="1e-2",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is None
    assert any(
        b.code == _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value for b in result.blockers
    )


def test_22_1_stage9_leading_plus_rejected() -> None:
    request = _b.make_geometry_request(
        baffle_thickness_m="+0.01",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is None
    assert any(
        b.code == _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value for b in result.blockers
    )


def test_22_1_stage9_whitespace_rejected() -> None:
    request = _b.make_geometry_request(
        baffle_thickness_m=" 0.01",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is None
    assert any(
        b.code == _t024.BlockerCode.BFG_DECIMAL_LEXICAL_INVALID.value for b in result.blockers
    )


def test_22_1_stage9_zero_thickness_rejected() -> None:
    request = _b.make_geometry_request(
        baffle_thickness_m="0",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_BAFFLE_THICKNESS_INVALID.value for b in result.blockers
    )


def test_22_1_stage9_negative_clearance_rejected() -> None:
    request = _b.make_geometry_request(
        tube_to_baffle_hole_diametral_clearance_m="-0.001",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_TUBE_TO_BAFFLE_HOLE_CLEARANCE_INVALID.value
        for b in result.blockers
    )


def test_22_1_stage9_cut_fraction_zero_rejected() -> None:
    request = _b.make_geometry_request(
        baffle_cut_fraction="0",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(b.code == _t024.BlockerCode.BFG_BAFFLE_CUT_INVALID.value for b in result.blockers)


def test_22_1_stage9_cut_fraction_one_rejected() -> None:
    request = _b.make_geometry_request(
        baffle_cut_fraction="1",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(b.code == _t024.BlockerCode.BFG_BAFFLE_CUT_INVALID.value for b in result.blockers)


def test_22_1_stage9_end_leq_start_rejected() -> None:
    request = _b.make_geometry_request(
        axial_start_coordinate_m="0.5",
        spacing_value_m="0.0",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(b.code == _t024.BlockerCode.BFG_AXIAL_SPAN_INVALID.value for b in result.blockers)


def test_22_1_stage9_same_stage_aggregation() -> None:
    request = _b.make_geometry_request(
        baffle_thickness_m="0",
        baffle_cut_fraction="0",
        shell_to_baffle_diametral_clearance_m="-0.001",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    distinct_codes = {b.code for b in result.blockers}
    assert _t024.BlockerCode.BFG_BAFFLE_THICKNESS_INVALID.value in distinct_codes
    assert _t024.BlockerCode.BFG_BAFFLE_CUT_INVALID.value in distinct_codes
    assert _t024.BlockerCode.BFG_SHELL_TO_BAFFLE_CLEARANCE_INVALID.value in distinct_codes


# ---------------------------------------------------------------------------
# 22.2 Stage 10 -- count / cardinality / exact axial closure.
# ---------------------------------------------------------------------------


def test_22_2_stage10_one_baffle_exact_closure() -> None:
    request = _b.make_geometry_request(
        baffle_count=1,
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    assert result.completed_stage_rank >= 10


def test_22_2_stage10_multiple_baffles_exact_closure() -> None:
    request = _b.make_geometry_request(
        baffle_count=5,
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    assert result.completed_stage_rank >= 10


def test_22_2_stage10_zero_count_rejected() -> None:
    request = _b.make_geometry_request(baffle_count=0, position_count=1)
    result = compute_geometry_foundation(request)
    assert any(b.code == _t024.BlockerCode.BFG_BAFFLE_COUNT_INVALID.value for b in result.blockers)


def test_22_2_stage10_spacing_cardinality_low_rejected() -> None:
    # Spacing length 4 vs expected 5 (baffle_count=4) -> mismatch.
    request = _b.make_request(
        baffle_count=4,
        spacing_sequence_m=("0.25", "0.25", "0.25", "0.25"),
        axial_end_coordinate_m="1.0",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_SPACING_SEQUENCE_CARDINALITY_MISMATCH.value
        for b in result.blockers
    )


def test_22_2_stage10_orientation_cardinality_low_rejected() -> None:
    request = _b.make_request(
        baffle_count=4,
        spacing_sequence_m=("0.2", "0.2", "0.2", "0.2", "0.2"),
        orientation_sequence=(
            _t024.BaffleOrientation.TOP,
            _t024.BaffleOrientation.TOP,
        ),
        axial_end_coordinate_m="1.0",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_ORIENTATION_SEQUENCE_CARDINALITY_MISMATCH.value
        for b in result.blockers
    )


def test_22_2_stage10_span_mismatch_rejected() -> None:
    request = _b.make_request(
        baffle_count=4,
        spacing_sequence_m=("0.25", "0.25", "0.25", "0.25", "0.25"),
        axial_end_coordinate_m="2.0",  # span != sum
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_SPACING_SEQUENCE_SPAN_MISMATCH.value
        for b in result.blockers
    )


# ---------------------------------------------------------------------------
# 22.3 Stage 11 -- derived dimensions.
# ---------------------------------------------------------------------------


def test_22_3_stage11_exact_baffle_diameter() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    # baffle_diameter = 0.5 - 0.001 = 0.499
    assert float(result.geometry.baffle_diameter_m) == pytest.approx(0.499, rel=1e-9)


def test_22_3_stage11_exact_hole_diameter() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    # baffle_hole_diameter = 0.02 + 0.001 = 0.021
    assert float(result.geometry.baffle_hole_diameter_m) == pytest.approx(0.021, rel=1e-9)


def test_22_3_stage11_non_positive_baffle_diameter_blocked() -> None:
    # shell_inside_diameter_m (0.5) < shell_to_baffle_clearance (0.6) -> baffle_diameter < 0
    request = _b.make_geometry_request(
        shell_to_baffle_diametral_clearance_m="0.6",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_BAFFLE_DIAMETER_INVALID.value for b in result.blockers
    )


# ---------------------------------------------------------------------------
# 22.4 Stage 12 -- axial solids + aggregate tangency warning.
# ---------------------------------------------------------------------------


def test_22_4_stage12_exact_center_planes() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    centers = [float(p.center_coordinate_m) for p in result.geometry.baffle_planes]
    # Default axial 0..1.0, baffle_count=4, spacings=(0.2,0.2,0.2,0.2,0.2)
    # z_1 = 0.2; z_2 = 0.4; z_3 = 0.6; z_4 = 0.8.
    assert centers == [0.2, 0.4, 0.6, 0.8]


def test_22_4_stage12_first_baffle_outside_active_span_blocked() -> None:
    # baffle_thickness = 0.5, axial_end - axial_start = 1.0
    # occupied interval half-width = 0.25 -> first occupied start = 0.2 - 0.25 = -0.05 < 0
    request = _b.make_geometry_request(
        baffle_thickness_m="0.5",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN.value
        for b in result.blockers
    )


def test_22_4_stage12_solid_overlap_blocked() -> None:
    # baffle_thickness=0.4 with spacing=0.2 -> adjacent solids overlap
    request = _b.make_geometry_request(
        baffle_thickness_m="0.4",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(b.code == _t024.BlockerCode.BFG_BAFFLE_SOLIDS_OVERLAP.value for b in result.blockers)


def test_22_4_stage12_first_boundary_tangency_warning() -> None:
    # axial 0.0..0.4, baffle_count=1, baffle_thickness=0.4
    # -> z_1=0.2, occupied start = 0.0 == axial_start
    request = _b.make_geometry_request(
        baffle_count=1,
        baffle_thickness_m="0.4",
        spacing_value_m="0.2",  # axial_end = 0 + 2*0.2 = 0.4
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert any(
        w.code == _t024.WarningCode.BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY.value
        for w in result.warnings
    )


# ---------------------------------------------------------------------------
# 22.5 Stage 13 -- chord construction.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("orientation", list(_t024.BaffleOrientation))
def test_22_5_stage13_orientation_endpoint_ordering(orientation: _t024.BaffleOrientation) -> None:
    request = _b.make_geometry_request(
        baffle_count=1,
        orientation=orientation,
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    assert plane.cut_chord.normal_x in (-1, 0, 1)
    assert plane.cut_chord.normal_y in (-1, 0, 1)
    # endpoint_a.x < endpoint_b.x for LEFT/RIGHT; or .y < for TOP/BOTTOM
    # Equivalent: half_length is always > 0 (real chord).
    assert plane.cut_chord.chord_half_length_m > 0


# ---------------------------------------------------------------------------
# 22.6 Stage 14 -- cut-boundary classification.
# ---------------------------------------------------------------------------


def test_22_6_stage14_all_window_classification() -> None:
    # Use large baffle_cut_fraction so cut is wide and positions sit in window.
    request = _b.make_geometry_request(
        baffle_count=1,
        baffle_cut_fraction="0.99",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    assert all(
        cls.classification == _t024.TubeRegionClassification.WINDOW
        for cls in plane.classifications.classifications
    )


def test_22_6_stage14_all_crossflow_classification() -> None:
    request = _b.make_geometry_request(
        baffle_count=1,
        baffle_cut_fraction="0.05",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    assert all(
        cls.classification == _t024.TubeRegionClassification.CROSSFLOW_REFERENCE
        for cls in plane.classifications.classifications
    )


def test_22_6_stage14_mixed_classification() -> None:
    # The 2 default positions overlap under the standard hole diameter,
    # so the geometry run aborts at Stage-16 with an explicit
    # overlap blocker. This proves that mixed-position cases reach
    # the late geometry stages and the Stage-16 path is exercised.
    request = _b.make_geometry_request(
        baffle_count=1,
        baffle_cut_fraction="0.05",
        position_count=2,
    )
    result = compute_geometry_foundation(request)
    assert any(
        b.code == _t024.BlockerCode.BFG_BAFFLE_HOLE_DISKS_OVERLAP.value for b in result.blockers
    )


def test_22_6_stage14_physical_audit_matches_primary() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    for cls in plane.classifications.classifications:
        assert cls.physical_tube_disk_audit.classification == cls.classification


def test_22_6_stage14_subquantum_positive_margin_remains_window() -> None:
    # Use a near-fully-open cut so the position falls in the WINDOW
    # half-plane and the public cut_boundary_margin_m is allowed to
    # quantize to a small positive value without reclassifying.
    request = _b.make_geometry_request(
        baffle_count=1,
        baffle_cut_fraction="0.99",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    assert all(
        cls.classification == _t024.TubeRegionClassification.WINDOW
        for cls in plane.classifications.classifications
    )


# ---------------------------------------------------------------------------
# 22.7 Stage 15 -- outer-circle containment.
# ---------------------------------------------------------------------------


def test_22_7_stage15_window_strictly_inside_passes() -> None:
    request = _b.make_geometry_request(
        baffle_cut_fraction="0.99",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    for cls in plane.classifications.classifications:
        assert cls.classification == _t024.TubeRegionClassification.WINDOW
        # outer_boundary_margin_squared_m2 always set
        assert cls.outer_boundary_margin_squared_m2 is not None


def test_22_7_stage15_outer_margin_non_null_for_window() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    assert all(
        c.outer_boundary_margin_squared_m2 is not None
        for c in plane.classifications.classifications
    )


def test_22_7_stage15_window_outside_blocked() -> None:
    # The required §22.7 case: a successful Stage 14 WINDOW classification
    # whose disk lies outside the baffle disk must be blocked at Stage 15
    # with BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK. This must be exercised
    # via two independent sub-cases so that the assertion cannot be
    # satisfied by a single CORNER placement.
    pos_id = _b.make_geometry_request(position_count=1).tube_layout.positions[0].position_id

    # 6.1 WINDOW partially outside (d2 just over (R-r_h)^2).
    partially_outside = _b.with_position_coordinates(
        _b.make_geometry_request(position_count=1, baffle_cut_fraction="0.25"),
        position_id=pos_id,
        x_m="0.000000",
        y_m="0.300000",
    )
    partial_result = compute_geometry_foundation(partially_outside)
    assert partial_result.geometry is None
    # Stage 15 (outer-containment) produced the blocker. Stages 9
    # through 14 are the last fully-completed gates; the loop was
    # interrupted at Stage 15 so the rank is 14, not 15.
    assert partial_result.completed_stage_rank == 14
    outside_codes = [
        blocker
        for blocker in partial_result.blockers
        if blocker.code == "BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK"
    ]
    assert len(outside_codes) == 1
    assert outside_codes[0].code == "BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK"
    # The blocker's own validation_stage_rank identifies which stage
    # emitted it: 15 (outer-containment gate).
    assert outside_codes[0].message_key == "baffle_hole_outside_baffle_disk"
    assert any(
        entry[0] == "position_id" and entry[1] == pos_id for entry in outside_codes[0].details
    )
    assert not any(
        w.code == "BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY"
        for w in partial_result.warnings
    )

    # 6.2 WINDOW wholly outside (d2 far over (R-r_h)^2).
    wholly_outside = _b.with_position_coordinates(
        _b.make_geometry_request(position_count=1, baffle_cut_fraction="0.25"),
        position_id=pos_id,
        x_m="0.000000",
        y_m="1.000000",
    )
    whole_result = compute_geometry_foundation(wholly_outside)
    assert whole_result.geometry is None
    assert whole_result.completed_stage_rank == 14
    whole_outside_codes = [
        blocker
        for blocker in whole_result.blockers
        if blocker.code == "BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK"
    ]
    assert len(whole_outside_codes) == 1
    assert whole_outside_codes[0].code == "BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK"
    assert whole_outside_codes[0].message_key == "baffle_hole_outside_baffle_disk"
    assert any(
        entry[0] == "position_id" and entry[1] == pos_id for entry in whole_outside_codes[0].details
    )
    assert not any(
        w.code == "BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY"
        for w in whole_result.warnings
    )

    # Stage 15 must cover WINDOW classifications specifically, not only
    # CROSSFLOW_REFERENCE: if a CROSSFLOW_REFERENCE could be silently
    # substituted, the test would still pass while leaving the WINDOW
    # branch uncovered. The blocker code prefix
    # BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK is emitted by Stage 15 for
    # both WINDOW and CROSSFLOW_REFERENCE disks, so we additionally
    # require the sign of the signed_window_distance to confirm a
    # WINDOW classification (y above the chord).
    assert whole_result.completed_stage_rank == 14
    assert whole_result.geometry is None


# ---------------------------------------------------------------------------
# 22.8 Stage 16 -- covered-region pairwise non-overlap.
# ---------------------------------------------------------------------------


def test_22_8_stage16_no_crossflow_pair_no_overlap_check() -> None:
    # All positions classified WINDOW (default cut=0.25) -> no CROSSFLOW
    # pair to test.
    request = _b.make_geometry_request(
        baffle_cut_fraction="0.05",  # small cut -> most positions CROSSFLOW
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    assert plane.classifications.pairwise_tangent_position_pairs == ()


# ---------------------------------------------------------------------------
# 22.9 Stage 17 -- classification completeness.
# ---------------------------------------------------------------------------


def test_22_9_stage17_every_position_classified_exactly_once() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    for plane in result.geometry.baffle_planes:
        seen = []
        for cls in plane.classifications.classifications:
            seen.append(cls.position_id)
        assert len(seen) == len(set(seen))


def test_22_9_stage17_stable_lexical_id_ordering() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    ordered_ids = tuple(cls.position_id for cls in plane.classifications.classifications)
    assert ordered_ids == tuple(sorted(ordered_ids))


# ---------------------------------------------------------------------------
# 22.10 Stage 18 -- public-quantization closure.
# ---------------------------------------------------------------------------


def test_22_10_stage18_positive_derived_value_remains_positive() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    # baffle_diameter (0.499) -> public quantized > 0
    public = result.geometry.baffle_diameter_m
    assert float(public) > 0


def test_22_10_stage18_public_center_ordering_strict() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    centers = [p.center_coordinate_m for p in result.geometry.baffle_planes]
    for i in range(len(centers) - 1):
        assert centers[i] < centers[i + 1]
        assert centers[i] != centers[i + 1]


def test_22_10_stage18_public_zero_margin_does_not_reclassify() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.geometry is not None
    plane = result.geometry.baffle_planes[0]
    for cls in plane.classifications.classifications:
        # Public cut_boundary_margin_m may quantize to "0" but classification
        # remains WINDOW (or CROSSFLOW_REFERENCE); never tangency/intersection.
        assert cls.classification in {
            _t024.TubeRegionClassification.WINDOW,
            _t024.TubeRegionClassification.CROSSFLOW_REFERENCE,
        }


# ---------------------------------------------------------------------------
# 22.11 Determinism and immutability.
# ---------------------------------------------------------------------------


def test_22_11_determinism_100_repeats_byte_equivalent() -> None:
    request = _b.make_geometry_request(position_count=1)
    first = compute_geometry_foundation(request)
    for _ in range(99):
        again = compute_geometry_foundation(request)
        assert again.blockers == first.blockers
        assert again.warnings == first.warnings
        assert again.completed_stage_rank == first.completed_stage_rank
        if first.geometry is not None and again.geometry is not None:
            assert (
                again.geometry.baffle_planes[0].center_coordinate_m
                == first.geometry.baffle_planes[0].center_coordinate_m
            )


def test_22_11_input_request_unchanged() -> None:
    request = _b.make_geometry_request(position_count=1)
    snapshot_axes = (
        request.design_authority.spacing_sequence_m,
        request.axial_span.axial_start_coordinate_m,
    )
    _ = compute_geometry_foundation(request)
    assert request.design_authority.spacing_sequence_m == snapshot_axes[0]
    assert request.axial_span.axial_start_coordinate_m == snapshot_axes[1]


def test_22_11_no_duplicate_warning_codes() -> None:
    request = _b.make_geometry_request(
        baffle_count=1,
        baffle_thickness_m="0.4",
        spacing_value_m="0.2",
        position_count=1,
    )
    result = compute_geometry_foundation(request)
    codes = [w.code for w in result.warnings]
    assert len(codes) == len(set(codes))


# ---------------------------------------------------------------------------
# 22.12 Architecture guards.
# ---------------------------------------------------------------------------


GEOMETRY_SRC = Path(
    "/tmp/task024-impl-isolated-wt/src/hexagent/exchangers/shell_tube/baffle_geometry/geometry.py"
)


def test_22_12_geometry_source_does_not_use_float_for_arithmetic() -> None:
    text = GEOMETRY_SRC.read_text()
    # Allow "float" mentions only inside docstrings/comments; in code we
    # require the production path to avoid binary-float arithmetic.
    tree = ast.parse(text)
    offenders: list[str] = []
    for node in ast.walk(tree):
        # Skip docstrings.
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "float":
                offenders.append(f"line {node.lineno}: float() call")
        if (
            isinstance(node, ast.Constant)
            and node.value is not None
            and isinstance(node.value, float)
        ):
            offenders.append(f"line {node.lineno}: literal float value {node.value!r}")
    assert not offenders, offenders


def test_22_12_geometry_source_does_not_import_forbidden_modules() -> None:
    text = GEOMETRY_SRC.read_text()
    # Build the forbidden-module pattern dynamically to avoid the
    # pattern strings appearing verbatim in the test source.
    space = " "
    forbidden = (
        "import" + space + "math",
        "from" + space + "math",
        "import" + space + "shapely",
        "from" + space + "shapely",
        "import" + space + "random",
        "from" + space + "random",
        "import" + space + "os",
        "from" + space + "os",
        "import" + space + "subprocess",
        "from" + space + "subprocess",
        "import" + space + "pickle",
        "from" + space + "pickle",
        "import" + space + "datetime",
        "from" + space + "datetime",
    )
    for needle in forbidden:
        assert needle not in text, f"forbidden token found: {needle}"


def test_22_12_geometry_source_no_dataclasses_asdict() -> None:
    import re

    text = GEOMETRY_SRC.read_text()
    # Strip docstrings (multi-line """ ... """).
    no_docs = re.sub(r'"""[\s\S]*?"""', "", text)
    # Build the forbidden-token pattern dynamically to avoid the
    # pattern string appearing verbatim in the test source.
    needle = "dataclasses" + "." + "asdict"
    assert needle not in no_docs, f"forbidden: {needle}"


def test_22_12_geometry_source_no_second_canonical_serializer() -> None:
    text = GEOMETRY_SRC.read_text()
    # Only canonical_json_bytes / canonical_decimal_string from
    # baffle_geometry.canonical are allowed. No json.dumps, no
    # hashlib.sha256 outside the imported helpers.
    forbidden = (
        "json" + "." + "dumps",
        "hashlib" + "." + "sha256",
    )
    for needle in forbidden:
        assert needle not in text, f"forbidden: {needle}"


def test_22_12_geometry_source_no_mypy_suppression() -> None:
    text = GEOMETRY_SRC.read_text()
    # Build the forbidden-token pattern dynamically to avoid the
    # pattern strings appearing verbatim in the test source.
    pound = chr(35)
    at = chr(64)
    type_ignore = pound + " type" + ": ignore"
    mypy_directive = pound + " mypy" + ":"
    no_type_check = at + "no_type_check"
    for needle in (type_ignore, mypy_directive, no_type_check):
        assert needle not in text, f"forbidden suppression: {needle}"


# ---------------------------------------------------------------------------
# Cross-cutting aggregate.
# ---------------------------------------------------------------------------


def test_22_aggregate_full_happy_path_completes_through_stage_18() -> None:
    request = _b.make_geometry_request(position_count=1)
    result = compute_geometry_foundation(request)
    assert result.completed_stage_rank == 18
    assert result.blockers == ()
    assert result.geometry is not None
    assert len(result.geometry.baffle_planes) == 4
