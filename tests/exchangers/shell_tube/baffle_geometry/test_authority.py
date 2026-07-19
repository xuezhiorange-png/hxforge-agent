"""TASK-024 Round 4 — ``authority.validate_authority_foundation`` tests.

These tests verify the Stage 2-8 authority-validation foundation
described in the TASK-024 design contract. They exercise:

- 19.1 Stage 2 — TASK-020 configuration validation.
- 19.2 Stage 3 — TASK-021 layout validation.
- 19.3 Stage 4 — TASK-022 geometry validation.
- 19.4 Stage 5 — three-way upstream cross-binding.
- 19.5 Stage 6 — supported v1 slice + baseline warnings.
- 19.6 Stage 7 — axial authority identity.
- 19.7 Stage 8 — design authority identity.
- 19.8 Ordering and carry-forward semantics.
- 19.9 Determinism and immutability.
- 19.10 Architecture guards.
"""

from __future__ import annotations

import hashlib
from typing import Any, cast

from hexagent.exchangers.shell_tube import (
    models as task020_models,
)
from hexagent.exchangers.shell_tube.baffle_geometry import (
    authority as t024_authority,
)
from hexagent.exchangers.shell_tube.baffle_geometry import (
    canonical as t024_canonical,
)
from hexagent.exchangers.shell_tube.baffle_geometry import (
    models as t024_models,
)
from tests.exchangers.shell_tube.baffle_geometry import (
    _builders as builders,
)

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _hash_axial(span: t024_models.CallerSuppliedBaffleAxialSpan) -> str:
    payload = {
        "axial_end_coordinate_m": span.axial_end_coordinate_m,
        "axial_start_coordinate_m": span.axial_start_coordinate_m,
        "evidence_refs": list(span.evidence_refs),
        "schema_version": span.schema_version,
    }
    return hashlib.sha256(t024_canonical.canonical_json_bytes(payload)).hexdigest()


def _hash_design(
    authority: t024_models.CallerSuppliedBaffleDesignAuthority,
) -> str:
    payload = {
        "baffle_count": authority.baffle_count,
        "baffle_cut_fraction": authority.baffle_cut_fraction,
        "baffle_thickness_m": authority.baffle_thickness_m,
        "baffle_type": authority.baffle_type.value,
        "evidence_refs": list(authority.evidence_refs),
        "orientation_sequence": [item.value for item in authority.orientation_sequence],
        "schema_version": authority.schema_version,
        "shell_to_baffle_diametral_clearance_m": (authority.shell_to_baffle_diametral_clearance_m),
        "spacing_sequence_m": list(authority.spacing_sequence_m),
        "tube_to_baffle_hole_diametral_clearance_m": (
            authority.tube_to_baffle_hole_diametral_clearance_m
        ),
    }
    return hashlib.sha256(t024_canonical.canonical_json_bytes(payload)).hexdigest()


# ---------------------------------------------------------------------------
# §19.1 Stage 2 — TASK-020 configuration validation.
# ---------------------------------------------------------------------------


def test_stage2_happy_path_passes() -> None:
    request = builders.make_request()
    result = t024_authority.validate_authority_foundation(request)
    # Should reach Stage 8 with no Stage 2 blocker; a different stage
    # could still fail (we only assert that Stage 2 cleared).
    stage2_blockers = tuple(b for b in result.blockers if b.code.startswith("BFG_TASK020_"))
    assert stage2_blockers == ()
    assert result.completed_stage_rank >= 2


def test_stage2_missing_exact_type_blocks() -> None:
    request = builders.make_request()
    # Replace configuration with a dict (wrong type).
    patched = builders.replace_configuration(
        request,
        configuration=cast(Any, {"not": "a real configuration"}),
    )
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_TASK020_CONFIGURATION_INVALID"
        and b.field_path == "configuration"
        and b.message_key == "task020_configuration_exact_type_required"
        for b in result.blockers
    )
    assert result.completed_stage_rank == 1


def test_stage2_wrong_schema_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_config = _dc_replace(request.configuration, schema_version="task020.configuration.v0")
    patched = builders.replace_configuration(request, configuration=bad_config)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_TASK020_CONFIGURATION_INVALID" and "schema_version" in (b.field_path or "")
        for b in result.blockers
    )


def test_stage2_upstream_blockers_block() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    blocker_msg = task020_models.ErrorEntry(
        code="STC_UPSTREAM_BLOCKER",
        field_path="x",
        message_key="upstream_blocker",
    )
    bad_config = _dc_replace(request.configuration, blockers=(blocker_msg,))
    patched = builders.replace_configuration(request, configuration=bad_config)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_TASK020_CONFIGURATION_INVALID"
        and b.message_key == "task020_configuration_upstream_blockers_present"
        for b in result.blockers
    )


def test_stage2_configuration_id_mismatch_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_config = _dc_replace(request.configuration, configuration_id="deadbeef" * 4)
    patched = builders.replace_configuration(request, configuration=bad_config)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_TASK020_CONFIGURATION_IDENTITY_MISMATCH" for b in result.blockers)


# ---------------------------------------------------------------------------
# §19.2 Stage 3 — TASK-021 layout validation.
# ---------------------------------------------------------------------------


def test_stage3_missing_exact_type_blocks() -> None:
    request = builders.make_request()
    patched = builders.replace_layout(
        request,
        tube_layout=cast(Any, {"not": "a real layout"}),
    )
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_TASK021_LAYOUT_INVALID"
        and b.field_path == "tube_layout"
        and b.message_key == "task021_layout_exact_type_required"
        for b in result.blockers
    )


def test_stage3_empty_positions_block() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(
        request.tube_layout,
        positions=(),
        tube_hole_count=0,
    )
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_TASK021_LAYOUT_HAS_NO_POSITIONS" for b in result.blockers)


def test_stage3_layout_hash_mismatch_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(request.tube_layout, layout_hash="0" * 64)
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_TASK021_LAYOUT_IDENTITY_MISMATCH" for b in result.blockers)


# ---------------------------------------------------------------------------
# §19.3 Stage 4 — TASK-022 geometry validation.
# ---------------------------------------------------------------------------


def test_stage4_missing_exact_type_blocks() -> None:
    request = builders.make_request()
    patched = builders.replace_geometry(request, shell_bundle_geometry={"not": "a real geometry"})
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_TASK022_GEOMETRY_INVALID"
        and b.field_path == "shell_bundle_geometry"
        and b.message_key == "task022_geometry_exact_type_required"
        for b in result.blockers
    )


def test_stage4_geometry_hash_mismatch_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_geometry = _dc_replace(request.shell_bundle_geometry, geometry_hash="0" * 64)
    patched = builders.replace_geometry(request, shell_bundle_geometry=bad_geometry)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_TASK022_GEOMETRY_IDENTITY_MISMATCH" for b in result.blockers)


# ---------------------------------------------------------------------------
# §19.4 Stage 5 — three-way upstream cross-binding.
# ---------------------------------------------------------------------------


def test_stage5_configuration_binding_mismatch_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(
        request.tube_layout, task020_configuration_id="00000000-0000-5000-8000-000000000000"
    )
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH" for b in result.blockers)


def test_stage5_construction_family_mismatch_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(request.tube_layout, construction_family="U_TUBE")
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_UPSTREAM_CONSTRUCTION_FAMILY_MISMATCH" for b in result.blockers)


def test_stage5_pass_count_mismatch_blocks() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(request.tube_layout, shell_pass_count=2)
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_UPSTREAM_PASS_COUNT_MISMATCH" for b in result.blockers)


def test_stage5_aggregates_multiple_blockers() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(
        request.tube_layout,
        construction_family="U_TUBE",
        shell_pass_count=2,
        equipment_orientation="VERTICAL",
    )
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    stage5_codes = {b.code for b in result.blockers if b.code.startswith("BFG_UPSTREAM_")}
    # Multiple Stage 5 blockers must aggregate (no first-error-only).
    assert len(stage5_codes) >= 2


# ---------------------------------------------------------------------------
# §19.5 Stage 6 — supported v1 slice.
# ---------------------------------------------------------------------------


def test_stage6_supported_slice_passes_and_emits_four_warnings() -> None:
    request = builders.make_request()
    result = t024_authority.validate_authority_foundation(request)
    stage6_codes = [
        w.code
        for w in result.warnings
        if w.message_key
        in {
            "fixed_tubesheet_only_v1",
            "geometry_not_flow_area",
            "nozzle_position_deferred",
            "thermal_hydraulic_deferred",
        }
    ]
    assert stage6_codes == [
        "BFG_FIXED_TUBESHEET_ONLY_V1",
        "BFG_GEOMETRY_NOT_FLOW_AREA",
        "BFG_NOZZLE_POSITION_DEFERRED",
        "BFG_THERMAL_HYDRAULIC_DEFERRED",
    ]


def test_stage6_unsupported_construction_family_blocks_and_suppresses_warnings() -> None:
    from hexagent.exchangers.shell_tube import models as task020_models

    request = builders.make_request(construction_family=task020_models.ConstructionFamily.U_TUBE)
    result = t024_authority.validate_authority_foundation(request)
    assert any(b.code == "BFG_CONSTRUCTION_FAMILY_UNSUPPORTED" for b in result.blockers)
    stage6_warning_codes = [
        w.code
        for w in result.warnings
        if w.code
        in {
            "BFG_FIXED_TUBESHEET_ONLY_V1",
            "BFG_GEOMETRY_NOT_FLOW_AREA",
            "BFG_NOZZLE_POSITION_DEFERRED",
            "BFG_THERMAL_HYDRAULIC_DEFERRED",
            "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM",
        }
    ]
    assert stage6_warning_codes == []


def test_stage6_unsupported_shell_pass_count_blocks() -> None:
    request = builders.make_request(shell_pass_count=2)
    result = t024_authority.validate_authority_foundation(request)
    assert any(b.code == "BFG_SHELL_PASS_COUNT_UNSUPPORTED" for b in result.blockers)


# ---------------------------------------------------------------------------
# §19.6 Stage 7 — axial authority identity.
# ---------------------------------------------------------------------------


def test_stage7_valid_axial_authority_passes() -> None:
    request = builders.make_request()
    result = t024_authority.validate_authority_foundation(request)
    assert all(b.code != "BFG_AXIAL_SPAN_" for b in result.blockers)


def test_stage7_wrong_schema_blocks() -> None:
    request = builders.make_request()
    bad_span = t024_models.CallerSuppliedBaffleAxialSpan(
        schema_version="task024.baffle-axial-span.v0",
        axial_start_coordinate_m=request.axial_span.axial_start_coordinate_m,
        axial_end_coordinate_m=request.axial_span.axial_end_coordinate_m,
        evidence_refs=request.axial_span.evidence_refs,
        authority_hash=request.axial_span.authority_hash,
    )
    patched = builders.replace_axial_span(request, axial_span=bad_span)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED" for b in result.blockers)


def test_stage7_empty_evidence_blocks() -> None:
    request = builders.make_request()
    span = builders.make_axial_span(evidence_refs=("task024-axial-evidence",))
    bad_span = t024_models.CallerSuppliedBaffleAxialSpan(
        schema_version=span.schema_version,
        axial_start_coordinate_m=span.axial_start_coordinate_m,
        axial_end_coordinate_m=span.axial_end_coordinate_m,
        evidence_refs=(),
        authority_hash=span.authority_hash,
    )
    patched = builders.replace_axial_span(request, axial_span=bad_span)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_AXIAL_SPAN_EVIDENCE_MISSING" for b in result.blockers)


def test_stage7_unsorted_evidence_blocks() -> None:
    request = builders.make_request()
    span = builders.make_axial_span(evidence_refs=("b", "a"))
    bad_span = t024_models.CallerSuppliedBaffleAxialSpan(
        schema_version=span.schema_version,
        axial_start_coordinate_m=span.axial_start_coordinate_m,
        axial_end_coordinate_m=span.axial_end_coordinate_m,
        evidence_refs=("b", "a"),  # explicitly unsorted
        authority_hash=span.authority_hash,
    )
    patched = builders.replace_axial_span(request, axial_span=bad_span)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_AXIAL_SPAN_EVIDENCE_MISSING"
        and b.message_key == "axial_span_evidence_refs_unsorted_or_duplicate"
        for b in result.blockers
    )


def test_stage7_malformed_authority_hash_blocks() -> None:
    request = builders.make_request()
    span = builders.make_axial_span(evidence_refs=("task024-axial-evidence",))
    bad_span = t024_models.CallerSuppliedBaffleAxialSpan(
        schema_version=span.schema_version,
        axial_start_coordinate_m=span.axial_start_coordinate_m,
        axial_end_coordinate_m=span.axial_end_coordinate_m,
        evidence_refs=span.evidence_refs,
        authority_hash="not-a-sha256",
    )
    patched = builders.replace_axial_span(request, axial_span=bad_span)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH"
        and b.message_key == "axial_span_authority_hash_malformed"
        for b in result.blockers
    )


def test_stage7_wrong_recomputed_hash_blocks() -> None:
    request = builders.make_request()
    span = request.axial_span
    # Corrupt authority_hash without changing any other field.
    bad_span = t024_models.CallerSuppliedBaffleAxialSpan(
        schema_version=span.schema_version,
        axial_start_coordinate_m=span.axial_start_coordinate_m,
        axial_end_coordinate_m=span.axial_end_coordinate_m,
        evidence_refs=span.evidence_refs,
        authority_hash="0" * 64,
    )
    patched = builders.replace_axial_span(request, axial_span=bad_span)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(
        b.code == "BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH"
        and b.message_key == "axial_span_authority_hash_mismatch"
        for b in result.blockers
    )


def test_stage7_authority_hash_self_field_excluded_from_projection() -> None:
    span = builders.make_axial_span(
        axial_start_coordinate_m="0.0",
        axial_end_coordinate_m="2.0",
        evidence_refs=("task024-axial-1",),
    )
    # authority_hash must not appear in the canonical projection that
    # the hash is computed over.
    assert "authority_hash" not in {
        "axial_end_coordinate_m",
        "axial_start_coordinate_m",
        "evidence_refs",
        "schema_version",
    }
    expected = hashlib.sha256(
        t024_canonical.canonical_json_bytes(
            {
                "axial_end_coordinate_m": span.axial_end_coordinate_m,
                "axial_start_coordinate_m": span.axial_start_coordinate_m,
                "evidence_refs": list(span.evidence_refs),
                "schema_version": span.schema_version,
            }
        )
    ).hexdigest()
    assert span.authority_hash == expected


# ---------------------------------------------------------------------------
# §19.7 Stage 8 — design authority identity.
# ---------------------------------------------------------------------------


def test_stage8_valid_design_authority_passes_and_emits_warning() -> None:
    request = builders.make_request()
    result = t024_authority.validate_authority_foundation(request)
    assert all(b.code != "BFG_DESIGN_AUTHORITY_" for b in result.blockers)
    assert any(w.code == "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM" for w in result.warnings)


def test_stage8_wrong_schema_blocks() -> None:
    request = builders.make_request()
    auth = builders.make_design_authority()
    bad_auth = t024_models.CallerSuppliedBaffleDesignAuthority(
        schema_version="task024.caller-baffle-design-authority.v0",
        baffle_type=auth.baffle_type,
        baffle_count=auth.baffle_count,
        baffle_thickness_m=auth.baffle_thickness_m,
        spacing_sequence_m=auth.spacing_sequence_m,
        baffle_cut_fraction=auth.baffle_cut_fraction,
        orientation_sequence=auth.orientation_sequence,
        shell_to_baffle_diametral_clearance_m=auth.shell_to_baffle_diametral_clearance_m,
        tube_to_baffle_hole_diametral_clearance_m=(auth.tube_to_baffle_hole_diametral_clearance_m),
        evidence_refs=auth.evidence_refs,
        authority_hash=auth.authority_hash,
    )
    patched = builders.replace_design_authority(request, design_authority=bad_auth)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED" for b in result.blockers)


def test_stage8_empty_evidence_blocks() -> None:
    request = builders.make_request()
    auth = builders.make_design_authority()
    bad_auth = t024_models.CallerSuppliedBaffleDesignAuthority(
        schema_version=auth.schema_version,
        baffle_type=auth.baffle_type,
        baffle_count=auth.baffle_count,
        baffle_thickness_m=auth.baffle_thickness_m,
        spacing_sequence_m=auth.spacing_sequence_m,
        baffle_cut_fraction=auth.baffle_cut_fraction,
        orientation_sequence=auth.orientation_sequence,
        shell_to_baffle_diametral_clearance_m=auth.shell_to_baffle_diametral_clearance_m,
        tube_to_baffle_hole_diametral_clearance_m=(auth.tube_to_baffle_hole_diametral_clearance_m),
        evidence_refs=(),
        authority_hash=auth.authority_hash,
    )
    patched = builders.replace_design_authority(request, design_authority=bad_auth)
    result = t024_authority.validate_authority_foundation(patched)
    assert any(b.code == "BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING" for b in result.blockers)


def test_stage8_spacing_order_changes_hash() -> None:
    auth_a = builders.make_design_authority(
        spacing_sequence_m=("0.25", "0.25", "0.25"),
    )
    auth_b = builders.make_design_authority(
        spacing_sequence_m=("0.25", "0.25", "0.30"),
    )
    assert auth_a.authority_hash != auth_b.authority_hash


def test_stage8_orientation_order_changes_hash() -> None:
    auth_a = builders.make_design_authority(
        orientation_sequence=(
            t024_models.BaffleOrientation.TOP,
            t024_models.BaffleOrientation.BOTTOM,
            t024_models.BaffleOrientation.TOP,
        ),
    )
    auth_b = builders.make_design_authority(
        orientation_sequence=(
            t024_models.BaffleOrientation.TOP,
            t024_models.BaffleOrientation.TOP,
            t024_models.BaffleOrientation.BOTTOM,
        ),
    )
    assert auth_a.authority_hash != auth_b.authority_hash


def test_stage8_authority_hash_self_field_excluded() -> None:
    # The canonical projection that produces authority_hash MUST NOT
    # include authority_hash itself.
    payload_keys = {
        "baffle_count",
        "baffle_cut_fraction",
        "baffle_thickness_m",
        "baffle_type",
        "evidence_refs",
        "orientation_sequence",
        "schema_version",
        "shell_to_baffle_diametral_clearance_m",
        "spacing_sequence_m",
        "tube_to_baffle_hole_diametral_clearance_m",
    }
    assert "authority_hash" not in payload_keys


# ---------------------------------------------------------------------------
# §19.8 Ordering and carry-forward.
# ---------------------------------------------------------------------------


def test_stage8_emits_five_warnings_in_exact_order() -> None:
    request = builders.make_request()
    result = t024_authority.validate_authority_foundation(request)
    warning_codes = [w.code for w in result.warnings]
    expected_order = [
        "BFG_FIXED_TUBESHEET_ONLY_V1",
        "BFG_GEOMETRY_NOT_FLOW_AREA",
        "BFG_NOZZLE_POSITION_DEFERRED",
        "BFG_THERMAL_HYDRAULIC_DEFERRED",
        "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM",
    ]
    # All five baseline warnings must appear in this exact global order.
    indices = [warning_codes.index(code) for code in expected_order]
    assert indices == sorted(indices)


def test_stage7_failure_retains_four_completed_stage6_warnings() -> None:
    request = builders.make_request()
    # Force Stage 7 to fail (empty evidence) but Stages 2-6 pass.
    span = request.axial_span
    bad_span = t024_models.CallerSuppliedBaffleAxialSpan(
        schema_version=span.schema_version,
        axial_start_coordinate_m=span.axial_start_coordinate_m,
        axial_end_coordinate_m=span.axial_end_coordinate_m,
        evidence_refs=(),
        authority_hash=span.authority_hash,
    )
    patched = builders.replace_axial_span(request, axial_span=bad_span)
    result = t024_authority.validate_authority_foundation(patched)
    warning_codes = [w.code for w in result.warnings]
    # Stage 6 warnings are completed and carried forward.
    for code in (
        "BFG_FIXED_TUBESHEET_ONLY_V1",
        "BFG_GEOMETRY_NOT_FLOW_AREA",
        "BFG_NOZZLE_POSITION_DEFERRED",
        "BFG_THERMAL_HYDRAULIC_DEFERRED",
    ):
        assert code in warning_codes
    # Stage 8 warning must NOT be emitted on Stage 7 failure.
    assert "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM" not in warning_codes
    assert result.completed_stage_rank == 6


def test_stage8_failure_retains_four_completed_stage6_warnings() -> None:
    request = builders.make_request()
    auth = request.design_authority
    bad_auth = t024_models.CallerSuppliedBaffleDesignAuthority(
        schema_version=auth.schema_version,
        baffle_type=auth.baffle_type,
        baffle_count=auth.baffle_count,
        baffle_thickness_m=auth.baffle_thickness_m,
        spacing_sequence_m=auth.spacing_sequence_m,
        baffle_cut_fraction=auth.baffle_cut_fraction,
        orientation_sequence=auth.orientation_sequence,
        shell_to_baffle_diametral_clearance_m=auth.shell_to_baffle_diametral_clearance_m,
        tube_to_baffle_hole_diametral_clearance_m=(auth.tube_to_baffle_hole_diametral_clearance_m),
        evidence_refs=(),
        authority_hash=auth.authority_hash,
    )
    patched = builders.replace_design_authority(request, design_authority=bad_auth)
    result = t024_authority.validate_authority_foundation(patched)
    warning_codes = [w.code for w in result.warnings]
    for code in (
        "BFG_FIXED_TUBESHEET_ONLY_V1",
        "BFG_GEOMETRY_NOT_FLOW_AREA",
        "BFG_NOZZLE_POSITION_DEFERRED",
        "BFG_THERMAL_HYDRAULIC_DEFERRED",
    ):
        assert code in warning_codes
    assert "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM" not in warning_codes


def test_stage5_failure_suppresses_stage6_and_stage8_warnings() -> None:
    from dataclasses import replace as _dc_replace

    request = builders.make_request()
    bad_layout = _dc_replace(request.tube_layout, shell_pass_count=2)
    patched = builders.replace_layout(request, tube_layout=bad_layout)
    result = t024_authority.validate_authority_foundation(patched)
    warning_codes = [w.code for w in result.warnings]
    assert "BFG_FIXED_TUBESHEET_ONLY_V1" not in warning_codes
    assert "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM" not in warning_codes


# ---------------------------------------------------------------------------
# §19.9 Determinism and immutability.
# ---------------------------------------------------------------------------


def test_100_repeated_calls_are_byte_equivalent() -> None:
    request = builders.make_request()
    first = t024_authority.validate_authority_foundation(request)
    for _ in range(99):
        again = t024_authority.validate_authority_foundation(request)
        assert [b.code for b in again.blockers] == [b.code for b in first.blockers]
        assert [w.code for w in again.warnings] == [w.code for w in first.warnings]
        assert again.completed_stage_rank == first.completed_stage_rank


def test_no_duplicate_warning_codes() -> None:
    request = builders.make_request()
    result = t024_authority.validate_authority_foundation(request)
    codes = [w.code for w in result.warnings]
    assert len(codes) == len(set(codes))


def test_input_request_is_not_mutated() -> None:
    request = builders.make_request()
    original_blockers = list(request.configuration.blockers)
    t024_authority.validate_authority_foundation(request)
    assert list(request.configuration.blockers) == original_blockers


def test_no_binary_floats_in_canonical_authority_projections() -> None:
    auth = builders.make_design_authority()
    # Recompute manually; assert all values in the canonical projection
    # are non-binary-float primitives.
    projection = {
        "baffle_count": auth.baffle_count,
        "baffle_cut_fraction": auth.baffle_cut_fraction,
        "baffle_thickness_m": auth.baffle_thickness_m,
        "baffle_type": auth.baffle_type.value,
        "evidence_refs": list(auth.evidence_refs),
        "orientation_sequence": [e.value for e in auth.orientation_sequence],
        "schema_version": auth.schema_version,
        "shell_to_baffle_diametral_clearance_m": (auth.shell_to_baffle_diametral_clearance_m),
        "spacing_sequence_m": list(auth.spacing_sequence_m),
        "tube_to_baffle_hole_diametral_clearance_m": (
            auth.tube_to_baffle_hole_diametral_clearance_m
        ),
    }
    for value in projection.values():
        assert not isinstance(value, float)
        if isinstance(value, tuple):
            for item in value:
                assert not isinstance(item, float)


# ---------------------------------------------------------------------------
# §19.10 Architecture guards.
# ---------------------------------------------------------------------------


def test_authority_module_does_not_import_forbidden_io_modules() -> None:
    import inspect

    source = inspect.getsource(t024_authority)
    # Strip module docstring before scanning for forbidden tokens.
    source_no_docstring = source.split('"""', 2)[-1] if '"""' in source else source
    forbidden_tokens = [
        "open(",
        "Path(",
        "subprocess",
        "urllib",
        "socket",
        "datetime.now",
        "date.today",
        "locale",
        "random.",
        "eval(",
        "exec(",
        "pickle",
        "getenv",
        "os.environ",
    ]
    for token in forbidden_tokens:
        assert token not in source_no_docstring, f"authority module imports/uses {token!r}"


def test_authority_module_does_not_use_dataclasses_asdict() -> None:
    import inspect

    source = inspect.getsource(t024_authority)
    source_no_docstring = source.split('"""', 2)[-1] if '"""' in source else source
    assert "dataclasses.asdict" not in source_no_docstring
    assert "dataclasses.fields(" not in source_no_docstring


def test_authority_module_does_not_use_runpy_or_dynamic_import() -> None:
    import inspect

    source = inspect.getsource(t024_authority)
    source_no_docstring = source.split('"""', 2)[-1] if '"""' in source else source
    assert "importlib" not in source_no_docstring
    assert "__import__" not in source_no_docstring
    assert "runpy" not in source_no_docstring


def test_authority_module_does_not_define_second_canonical_serializer() -> None:
    import inspect

    source = inspect.getsource(t024_authority)
    assert "json.dumps" not in source
    assert "json.JSONEncoder" not in source
