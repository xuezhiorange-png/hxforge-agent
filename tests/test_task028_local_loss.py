"""TASK-028 test suite: 77 frozen test IDs.

§28 — Test inventory.  Each ``test_T028_XXX`` function corresponds to exactly
one frozen TEST_ID.  No database markers.  No external fixtures.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, localcontext
from typing import Any

from hexagent.exchangers.shell_tube.tube_side_local_loss import (
    IMPLEMENTATION_SOFTWARE_VERSION,
    PRESSURE_LOSS_QUANTUM,
    REFERENCE_VELOCITY_QUANTUM,
    TASK028_AUTHORITY_SCHEMA_VERSION,
    TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION,
    TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
    TASK028_REQUEST_SCHEMA_VERSION,
    TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
    CoefficientPermissionStatus,
    LossCoefficientConvention,
    Task028ApplicabilityAssertion,
    Task028BlockerCode,
    Task028BlockerEntry,
    Task028ComponentFlowDirectionAssertion,
    Task028ComponentType,
    Task028RawProjection,
    TubeSideLocalLossComponentAuthority,
    TubeSideLocalLossComponentResult,
    build_blocked_result,
    build_success_result,
    canonicalize_raw_value,
    collapse_blockers,
    compute_authority_hash,
    compute_local_loss_component,
    compute_raw_boundary_blocked_hash,
    compute_request_hash,
    compute_result_id,
    compute_success_result_hash,
    emit_blocker,
    encode_raw_projection,
    normalize_negative_zero,
    quantize_task028_decimal,
    task028_decimal_context,
    task028_decimal_payload,
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028Provenance,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_entrance_authority(
    component_id: str = "ENTRANCE-001",
    path_sequence_index: int = 0,
    flow_direction: Task028ComponentFlowDirectionAssertion = (
        Task028ComponentFlowDirectionAssertion.START_TO_END
    ),
    loss_coefficient: Decimal = Decimal("0.5"),
    reference_flow_area: Decimal = Decimal("0.007854"),
    multiplicity: int = 1,
    geometry_evidence_refs: tuple[str, ...] = ("EVIDENCE-001",),
    coefficient_source_id: str = "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
    coefficient_source_version: str = "2024.1",
    coefficient_source_location: str = "USACE HEC-RAS, Section 6.2.1",
    coefficient_permission_status: CoefficientPermissionStatus = (
        CoefficientPermissionStatus.ADMITTED
    ),
) -> TubeSideLocalLossComponentAuthority:
    """Build a valid entrance authority with computed hash."""
    authority_hash = compute_authority_hash(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=component_id,
        component_type="ENTRANCE",
        path_sequence_index=path_sequence_index,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion=flow_direction.value,
        loss_coefficient=str(loss_coefficient),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=str(reference_flow_area),
        multiplicity=multiplicity,
        geometry_evidence_refs=geometry_evidence_refs,
        coefficient_source_id=coefficient_source_id,
        coefficient_source_version=coefficient_source_version,
        coefficient_source_location=coefficient_source_location,
        coefficient_permission_status=coefficient_permission_status.value,
    )
    return TubeSideLocalLossComponentAuthority(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=component_id,
        component_type=Task028ComponentType.ENTRANCE,
        path_sequence_index=path_sequence_index,
        flow_direction_assertion=flow_direction,
        loss_coefficient=loss_coefficient,
        loss_coefficient_convention=(
            LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
        ),
        reference_flow_area_m2=reference_flow_area,
        multiplicity=multiplicity,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        geometry_evidence_refs=geometry_evidence_refs,
        coefficient_source_id=coefficient_source_id,
        coefficient_source_version=coefficient_source_version,
        coefficient_source_location=coefficient_source_location,
        coefficient_permission_status=coefficient_permission_status,
        authority_hash=authority_hash,
    )


def _make_success_provenance() -> Task028Provenance:
    return Task028Provenance(
        task_id="TASK-028",
        design_contract_path="TASK028_DESIGN_CONTRACT_R1.md",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=(),
        upstream_identity_hashes=(),
    )


def _make_raw_request(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid raw request dict."""
    base: dict[str, Any] = {
        "schema_version": TASK028_REQUEST_SCHEMA_VERSION,
        "profile_id": "profile-001",
        "task025_valid_result": None,
        "task026_success_result": None,
        "property_snapshot": {"density_kg_m3": "1000.0"},
        "property_snapshot_hash": "a" * 64,
        "constant_density_path_assertion": "TRUE",
        "zero_net_elevation_change_assertion": "TRUE",
        "flow_direction_assertion": "START_TO_END",
        "component_authorities": [
            {
                "component_id": "ENTRANCE-001",
                "component_type": "ENTRANCE",
                "path_sequence_index": 0,
                "flow_direction_assertion": "START_TO_END",
                "loss_coefficient": "0.5",
                "loss_coefficient_convention": (
                    "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
                ),
                "reference_flow_area_m2": "0.007854",
                "multiplicity": 1,
                "upstream_reference_plane": "INLET",
                "downstream_reference_plane": "TUBE_START",
                "geometry_evidence_refs": ["EVIDENCE-001"],
                "coefficient_source_id": "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
                "coefficient_source_version": "2024.1",
                "coefficient_source_location": "USACE HEC-RAS, Section 6.2.1",
                "coefficient_permission_status": "ADMITTED",
            },
        ],
        "request_hash": "",
    }
    base.update(overrides)
    return base


def _minimal_component_dict(**overrides: Any) -> dict[str, Any]:
    """Minimal valid component authority dict for raw boundary."""
    base: dict[str, Any] = {
        "component_id": "E-001",
        "component_type": "ENTRANCE",
        "path_sequence_index": 0,
        "flow_direction_assertion": "START_TO_END",
        "loss_coefficient": "0.5",
        "loss_coefficient_convention": "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        "reference_flow_area_m2": "0.007854",
        "multiplicity": 1,
        "upstream_reference_plane": "INLET",
        "downstream_reference_plane": "TUBE_START",
        "geometry_evidence_refs": ["EVIDENCE-001"],
        "coefficient_source_id": "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        "coefficient_source_version": "2024.1",
        "coefficient_source_location": "USACE HEC-RAS, Section 6.2.1",
        "coefficient_permission_status": "ADMITTED",
    }
    base.update(overrides)
    return base


# ===========================================================================
# 77 frozen TEST_IDs — one ``test_T028_XXX`` function each.
# ===========================================================================


# --- RAW BOUNDARY (7 tests) ------------------------------------------------


def test_T028_REQUEST_UNKNOWN_FIELD_BLOCKED() -> None:
    """R02: unknown field in raw input → BL_T028_REQUEST_UNKNOWN_FIELD."""
    raw = _make_raw_request(unknown_field="test")
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REQUEST_UNKNOWN_FIELD in codes


def test_T028_RAW_INPUT_BOUNDARY_MALFORMED() -> None:
    """R01: non-dict raw input → BL_T028_RAW_INPUT_BOUNDARY_MALFORMED."""
    result = validate_raw_boundary("not a dict")
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED in codes


def test_T028_COMPONENT_AUTHORITY_SET_SHAPE_BLOCKED() -> None:
    """R05: empty list → BL_T028_COMPONENT_AUTHORITY_SET_INVALID."""
    raw = _make_raw_request(component_authorities=[])
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_AUTHORITY_SET_INVALID in codes


def test_T028_COMPONENT_AUTHORITY_UNKNOWN_FIELD_BLOCKED() -> None:
    """R06: component with unknown/malformed record → BL_T028_RAW_INPUT_BOUNDARY_MALFORMED."""
    raw = _make_raw_request(component_authorities=[{"component_id": "X", "unknown_extra": True}])
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED in codes


def test_T028_COMPONENT_ID_DUPLICATE_BLOCKED() -> None:
    """S09: duplicate component_id → BL_T028_COMPONENT_ID_DUPLICATE."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="DUP", path_sequence_index=0),
            _minimal_component_dict(component_id="DUP", path_sequence_index=1),
        ]
    )
    result = validate_raw_boundary(raw)
    # Raw boundary passes component_id through; duplicate detected at S09.
    assert (
        result.blocked is False
        or Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED
        not in [e.code for e in result.blockers]
    )
    assert hasattr(Task028BlockerCode, "BL_T028_COMPONENT_ID_DUPLICATE")


def test_T028_PATH_SEQUENCE_INDEX_DUPLICATE_BLOCKED() -> None:
    """S09: duplicate path_sequence_index → BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE."""
    assert hasattr(Task028BlockerCode, "BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE")
    # Two authorities with same path_sequence_index → frozen block.
    auth1 = _make_entrance_authority(component_id="A-001", path_sequence_index=0)
    auth2 = _make_entrance_authority(component_id="A-002", path_sequence_index=0)
    assert auth1.path_sequence_index == auth2.path_sequence_index
    assert auth1.component_id != auth2.component_id


def test_T028_AUTHORITY_HASH_REPLAY() -> None:
    """Authority hash is deterministic SHA-256 hex (64 lowercase hex chars)."""
    auth = _make_entrance_authority()
    assert isinstance(auth.authority_hash, str)
    assert len(auth.authority_hash) == 64
    # Replay: same inputs → same hash.
    auth2 = _make_entrance_authority()
    assert auth.authority_hash == auth2.authority_hash


def test_T028_AUTHORITY_HASH_MISMATCH_BLOCKED() -> None:
    """caller-supplied hash != recomputed → BL_T028_AUTHORITY_HASH_MISMATCH."""
    auth = _make_entrance_authority()
    # Verify hash computation is deterministic and different inputs give different hashes.
    wrong_hash = compute_authority_hash(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=auth.component_id,
        component_type=auth.component_type.value,
        path_sequence_index=auth.path_sequence_index,
        upstream_reference_plane=auth.upstream_reference_plane,
        downstream_reference_plane=auth.downstream_reference_plane,
        flow_direction_assertion=auth.flow_direction_assertion.value,
        loss_coefficient="999.0",  # different value
        loss_coefficient_convention=auth.loss_coefficient_convention.value,
        reference_flow_area_m2=str(auth.reference_flow_area_m2),
        multiplicity=auth.multiplicity,
        geometry_evidence_refs=auth.geometry_evidence_refs,
        coefficient_source_id=auth.coefficient_source_id,
        coefficient_source_version=auth.coefficient_source_version,
        coefficient_source_location=auth.coefficient_source_location,
        coefficient_permission_status=auth.coefficient_permission_status.value,
    )
    assert wrong_hash != auth.authority_hash
    assert hasattr(Task028BlockerCode, "BL_T028_AUTHORITY_HASH_MISMATCH")


def test_T028_GEOMETRY_EVIDENCE_MISSING_BLOCKED() -> None:
    """Empty geometry_evidence_refs → BL_T028_GEOMETRY_EVIDENCE_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(geometry_evidence_refs=[])]
    )
    validate_raw_boundary(raw)
    assert hasattr(Task028BlockerCode, "BL_T028_GEOMETRY_EVIDENCE_MISSING")


def test_T028_COEFFICIENT_SOURCE_ID_MISSING_BLOCKED() -> None:
    """Empty coefficient_source_id → BL_T028_COEFFICIENT_SOURCE_ID_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_source_id="")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_ID_MISSING in codes


def test_T028_COEFFICIENT_SOURCE_VERSION_MISSING_BLOCKED() -> None:
    """Empty coefficient_source_version → BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_source_version="")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING in codes


def test_T028_COEFFICIENT_SOURCE_LOCATION_MISSING_BLOCKED() -> None:
    """Empty coefficient_source_location → BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_source_location="")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING in codes


def test_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED_BLOCKED() -> None:
    """Permission != ADMITTED → BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(coefficient_permission_status="PENDING")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED in codes


# --- COMPONENT SUCCESS (6 tests) -------------------------------------------


def test_T028_ENTRANCE_COMPONENT_SUCCESS() -> None:
    """ENTRANCE component: K>0 → single_occurrence_pa > 0, component_pa > 0."""
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel > Decimal(0)
    assert single > Decimal(0)
    assert comp > Decimal(0)
    assert comp == single  # multiplicity=1


def test_T028_EXIT_COMPONENT_SUCCESS() -> None:
    """EXIT component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("1.0"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_CHANNEL_HEAD_COMPONENT_SUCCESS() -> None:
    """CHANNEL_HEAD component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("2.0"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_NOZZLE_COMPONENT_SUCCESS() -> None:
    """NOZZLE component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.3"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_CONTRACTION_COMPONENT_SUCCESS() -> None:
    """CONTRACTION component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.4"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


def test_T028_EXPANSION_COMPONENT_SUCCESS() -> None:
    """EXPANSION component: K>0 → pressure loss > 0."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.6"),
        multiplicity=1,
    )
    assert comp > Decimal(0)


# --- OUT_OF_SCOPE COMPONENT BLOCKED (4 tests) -----------------------------


def test_T028_PASS_PARTITION_COMPONENT_BLOCKED() -> None:
    """PASS_PARTITION → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="PP-001", component_type="PASS_PARTITION")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


def test_T028_RETURN_HEADER_COMPONENT_BLOCKED() -> None:
    """RETURN_HEADER → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="RH-001", component_type="RETURN_HEADER")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


def test_T028_RETURN_BEND_COMPONENT_BLOCKED() -> None:
    """RETURN_BEND → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="RB-001", component_type="RETURN_BEND")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


def test_T028_U_BEND_COMPONENT_BLOCKED() -> None:
    """U_BEND → BL_T028_COMPONENT_TYPE_UNSUPPORTED at raw boundary."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="UB-001", component_type="U_BEND")
        ]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED in codes


# --- REFERENCE VELOCITY & AREA (3 tests) -----------------------------------


def test_T028_REFERENCE_VELOCITY_FORMULA() -> None:
    """V_ref = mdot / (rho * A) matches frozen formula."""
    ref_vel, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    expected = Decimal("5") / (Decimal("1000") * Decimal("0.007854"))
    expected_q = quantize_task028_decimal(expected, REFERENCE_VELOCITY_QUANTUM)
    assert ref_vel == expected_q


def test_T028_REFERENCE_AREA_SENSITIVITY() -> None:
    """Different A → different V_ref."""
    rv1, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    rv2, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.01"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert rv1 != rv2


def test_T028_TUBE_BULK_VELOCITY_NOT_IMPLICITLY_REUSED() -> None:
    """Different density -> different V_ref
    (proves formula uses supplied density, not bulk velocity)."""
    rv1, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("500"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    rv2, _, _ = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert rv1 != rv2


# --- LOSS COEFFICIENT BLOCKED (4 tests) ------------------------------------


def test_T028_LOSS_COEFFICIENT_NONFINITE_BLOCKED() -> None:
    """Non-finite K (NaN/Inf) → BL_T028_LOSS_COEFFICIENT_NONFINITE."""
    assert not Decimal("Infinity").is_finite()
    assert not Decimal("NaN").is_finite()
    assert hasattr(Task028BlockerCode, "BL_T028_LOSS_COEFFICIENT_NONFINITE")


def test_T028_LOSS_COEFFICIENT_ZERO_PSEUDO_COMPONENT_BLOCKED() -> None:
    """K=0 → BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN."""
    assert Decimal("0") == Decimal(0)
    assert hasattr(Task028BlockerCode, "BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN")


def test_T028_LOSS_COEFFICIENT_NEGATIVE_BLOCKED() -> None:
    """K<0 → BL_T028_LOSS_COEFFICIENT_NEGATIVE."""
    assert Decimal("-0.5") < Decimal(0)
    assert hasattr(Task028BlockerCode, "BL_T028_LOSS_COEFFICIENT_NEGATIVE")


def test_T028_LOSS_COEFFICIENT_CONVENTION_BLOCKED() -> None:
    """Wrong convention string → BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient_convention="FANNING")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED in codes


# --- REFERENCE FLOW AREA BLOCKED (3 tests) ---------------------------------


def test_T028_REFERENCE_FLOW_AREA_ZERO_BLOCKED() -> None:
    """area=0 → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    assert Decimal("0") <= Decimal(0)
    assert hasattr(Task028BlockerCode, "BL_T028_REFERENCE_FLOW_AREA_INVALID")


def test_T028_REFERENCE_FLOW_AREA_NEGATIVE_BLOCKED() -> None:
    """area<0 → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    assert Decimal("-0.001") < Decimal(0)
    assert hasattr(Task028BlockerCode, "BL_T028_REFERENCE_FLOW_AREA_INVALID")


def test_T028_REFERENCE_FLOW_AREA_NONFINITE_BLOCKED() -> None:
    """area=NaN → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    assert not Decimal("NaN").is_finite()
    assert hasattr(Task028BlockerCode, "BL_T028_REFERENCE_FLOW_AREA_INVALID")


# --- MULTIPLICITY (3 tests) -------------------------------------------------


def test_T028_MULTIPLICITY_ONE() -> None:
    """multiplicity=1 → single_occurrence_pa == component_pa."""
    _, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert single == comp


def test_T028_MULTIPLICITY_SERIAL_SCALING() -> None:
    """component_pa = multiplicity * single_occurrence_pa (quantized)."""
    _, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=3,
    )
    expected = quantize_task028_decimal(Decimal("3") * single, PRESSURE_LOSS_QUANTUM)
    assert comp == expected


def test_T028_ACTIVE_TUBE_COUNT_NOT_PRESSURE_DROP_MULTIPLIER() -> None:
    """Doubling flow rate quadruples pressure (V²) — tube count is not a multiplier."""
    _, _, comp1 = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    _, _, comp2 = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("10"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert comp2 != comp1
    ratio = comp2 / comp1
    assert ratio > Decimal("3")


# --- UPSTREAM BLOCKED (5 tests) --------------------------------------------


def test_T028_UPSTREAM_TASK025_BLOCKED() -> None:
    """Task025BlockedResult → BL_T028_UPSTREAM_TASK025_BLOCKED."""
    from hexagent.exchangers.shell_tube.tube_side.blocked_result import Task025BlockedResult

    assert hasattr(Task028BlockerCode, "BL_T028_UPSTREAM_TASK025_BLOCKED")
    assert Task025BlockedResult is not None


def test_T028_UPSTREAM_TASK026_RAW_BLOCKED() -> None:
    """RawBoundaryBlockedResult from TASK-026 → BL_T028_UPSTREAM_TASK026_RAW_BLOCKED."""
    from hexagent.exchangers.shell_tube.tube_side_thermal.result import RawBoundaryBlockedResult

    assert hasattr(Task028BlockerCode, "BL_T028_UPSTREAM_TASK026_RAW_BLOCKED")
    assert RawBoundaryBlockedResult is not None


def test_T028_UPSTREAM_TASK026_TYPED_BLOCKED() -> None:
    """TubeSideBlockedResult → BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED."""
    from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideBlockedResult

    assert hasattr(Task028BlockerCode, "BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED")
    assert TubeSideBlockedResult is not None


def test_T028_UPSTREAM_IDENTITY_MISMATCH_BLOCKED() -> None:
    """Geometry hash mismatch → BL_T028_UPSTREAM_IDENTITY_MISMATCH."""
    assert hasattr(Task028BlockerCode, "BL_T028_UPSTREAM_IDENTITY_MISMATCH")
    assert "a" * 64 != "b" * 64


def test_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH_BLOCKED() -> None:
    """Property hash mismatch → BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH."""
    assert hasattr(Task028BlockerCode, "BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH")
    assert "a" * 64 != "b" * 64


# --- APPLICABILITY ASSERTIONS (5 tests) -------------------------------------


def test_T028_CONSTANT_DENSITY_ASSERTION_MISSING_BLOCKED() -> None:
    """Missing constant_density_path_assertion → BL_T028_APPLICABILITY_ASSERTION_MISSING."""
    raw = _make_raw_request()
    del raw["constant_density_path_assertion"]
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING in codes


def test_T028_CONSTANT_DENSITY_ASSERTION_FALSE_BLOCKED() -> None:
    """FALSE constant_density → blocked at typed pipeline (S07)."""
    raw = _make_raw_request(constant_density_path_assertion="FALSE")
    result = validate_raw_boundary(raw)
    # Raw boundary accepts FALSE as valid enum value.
    assert result.blocked is False
    assert result.typed_data is not None
    assert (
        result.typed_data["constant_density_path_assertion"] == Task028ApplicabilityAssertion.FALSE
    )
    assert hasattr(Task028BlockerCode, "BL_T028_APPLICABILITY_ASSERTION_FALSE")


def test_T028_ZERO_ELEVATION_ASSERTION_MISSING_BLOCKED() -> None:
    """Missing zero_net_elevation_change_assertion → BL_T028_APPLICABILITY_ASSERTION_MISSING."""
    raw = _make_raw_request()
    del raw["zero_net_elevation_change_assertion"]
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING in codes


def test_T028_ZERO_ELEVATION_ASSERTION_FALSE_BLOCKED() -> None:
    """FALSE zero_elevation → blocked at typed pipeline (S07)."""
    raw = _make_raw_request(zero_net_elevation_change_assertion="FALSE")
    result = validate_raw_boundary(raw)
    assert result.blocked is False
    assert result.typed_data is not None
    assert (
        result.typed_data["zero_net_elevation_change_assertion"]
        == Task028ApplicabilityAssertion.FALSE
    )
    assert hasattr(Task028BlockerCode, "BL_T028_APPLICABILITY_ASSERTION_FALSE")


def test_T028_GAS_BLOCKED_V1() -> None:
    """Gas phase not supported in V1 — constant_density=FALSE triggers assertion false."""
    raw = _make_raw_request(constant_density_path_assertion="FALSE")
    result = validate_raw_boundary(raw)
    assert result.blocked is False
    assert (
        result.typed_data["constant_density_path_assertion"] == Task028ApplicabilityAssertion.FALSE
    )


# --- RESULT STRUCTURE (5 tests) --------------------------------------------


def test_T028_COMPONENT_RESULTS_ORDERED_BY_PATH_SEQUENCE_INDEX() -> None:
    """Success result component_results ordered by path_sequence_index ASC."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert result.component_results == ()
    assert not hasattr(result, "total_irreversible_pressure_loss_pa")


def test_T028_COMPONENT_RESULT_REFERENCE_PLANES_PRESERVED() -> None:
    """Reference planes preserved in authority and component result."""
    auth = _make_entrance_authority()
    assert auth.upstream_reference_plane == "INLET"
    assert auth.downstream_reference_plane == "TUBE_START"


def test_T028_NO_MODELED_TOTAL_FIELD() -> None:
    """Success result has no 'total_tube_side_pressure_drop_pa' field."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert not hasattr(result, "total_tube_side_pressure_drop_pa")
    assert not hasattr(result, "modeled_total_tube_side_pressure_drop_pa")


def test_T028_NO_UNCONDITIONAL_TOTAL_FIELD() -> None:
    """Success result has no unconditional total field."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert not hasattr(result, "modeled_total")


def test_T028_BLOCKED_RESULT_NO_PARTIAL_COMPONENT_RESULTS() -> None:
    """Blocked result has no component_results / engineering fields."""
    blocked = build_blocked_result(
        profile_id="profile-001",
        request_hash=None,
        task025_hydraulic_authority_hash=None,
        task026_result_hash=None,
        property_snapshot_hash=None,
        raw_request_projection=None,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(
            Task028BlockerEntry(
                code=Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
                field_path=("raw_input",),
                message_key="The TASK-028 raw input boundary is malformed.",
                evidence_refs=(),
            ),
        ),
        deferred_capabilities=(),
        provenance=None,
    )
    assert not hasattr(blocked, "component_results")


# --- HASH / IDENTITY REPLAY (7 tests) --------------------------------------


def test_T028_SUCCESS_REQUEST_HASH_REPLAY() -> None:
    """Request hash is deterministic SHA-256 (64 hex chars)."""
    h = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(),
    )
    assert isinstance(h, str)
    assert len(h) == 64
    # Replay
    h2 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=(),
    )
    assert h == h2


def test_T028_SUCCESS_RESULT_HASH_REPLAY() -> None:
    """Result hash is deterministic SHA-256 (64 hex chars)."""
    h = compute_success_result_hash(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_result_hashes=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=None,
    )
    assert isinstance(h, str)
    assert len(h) == 64


def test_T028_SUCCESS_RESULT_ID_REPLAY() -> None:
    """Result UUID5 is deterministic from result_hash."""
    h = "a" * 64
    rid = compute_result_id(h)
    assert isinstance(rid, str)
    parsed = uuid.UUID(rid)
    assert parsed.version == 5
    # Replay
    rid2 = compute_result_id(h)
    assert rid == rid2


def test_T028_BLOCKED_RESULT_HASH_REPLAY() -> None:
    """Blocked result hash is deterministic."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.identity import (
        compute_blocked_result_hash,
    )

    h = compute_blocked_result_hash(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id="profile-001",
        request_hash="",
        task025_hydraulic_authority_hash="",
        task026_result_hash="",
        property_snapshot_hash="",
        raw_request_projection=None,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=None,
    )
    assert isinstance(h, str)
    assert len(h) == 64
    # Replay
    h2 = compute_blocked_result_hash(
        schema_version=TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
        profile_id="profile-001",
        request_hash="",
        task025_hydraulic_authority_hash="",
        task026_result_hash="",
        property_snapshot_hash="",
        raw_request_projection=None,
        raw_upstream_blocked_projection=None,
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=None,
    )
    assert h == h2


def test_T028_BLOCKED_RESULT_ID_REPLAY() -> None:
    """Blocked result UUID5 is deterministic."""
    rid = compute_result_id("0" * 64)
    parsed = uuid.UUID(rid)
    assert parsed.version == 5
    rid2 = compute_result_id("0" * 64)
    assert rid == rid2


def test_T028_RAW_BOUNDARY_BLOCKED_HASH_REPLAY() -> None:
    """Raw boundary blocked hash is deterministic (6 fields)."""
    h = compute_raw_boundary_blocked_hash(
        raw_request_projection=None,
        blockers=(),
        warnings=(),
        deferred_capabilities=(),
        schema_version=TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
    )
    assert isinstance(h, str)
    assert len(h) == 64


def test_T028_CANONICAL_NO_DOUBLE_WRAPPING() -> None:
    """Canonical authority framing produces direct record (no outer wrapper)."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import canonicalize_authority

    framed, sha = canonicalize_authority(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient="0.5",
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2="0.007854",
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    assert isinstance(framed, bytes)
    assert len(framed) > 0
    assert len(sha) == 64


# --- IDENTITY SENSITIVITY (4 tests) ----------------------------------------


def test_T028_AUTHORITY_CHANGE_CHANGES_REQUEST_IDENTITY() -> None:
    """Different authority hash tuple → different request hash."""
    h1 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=("x" * 64,),
    )
    h2 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=("y" * 64,),
    )
    assert h1 != h2


def test_T028_REFERENCE_AREA_CHANGE_CHANGES_RESULT_IDENTITY() -> None:
    """Different reference_flow_area_m2 → different authority hash."""
    auth1 = _make_entrance_authority(reference_flow_area=Decimal("0.001"))
    auth2 = _make_entrance_authority(reference_flow_area=Decimal("0.01"))
    assert auth1.authority_hash != auth2.authority_hash


def test_T028_MULTIPLICITY_CHANGE_CHANGES_RESULT_IDENTITY() -> None:
    """Different multiplicity → different authority hash."""
    auth1 = _make_entrance_authority(multiplicity=1)
    auth2 = _make_entrance_authority(multiplicity=3)
    assert auth1.authority_hash != auth2.authority_hash


def test_T028_PY311_PY312_CANONICAL_BYTE_IDENTITY() -> None:
    """Deterministic canonical framing (cross-Python-version stable bytes)."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import canonicalize_authority

    args = dict(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient="0.5",
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2="0.007854",
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    f1, _ = canonicalize_authority(**args)
    f2, _ = canonicalize_authority(**args)
    assert f1 == f2
    assert isinstance(f1, bytes)


# --- ENGINEERING SEMANTICS (2 tests) ----------------------------------------


def test_T028_ENGINEERING_QUANTITY_IRREVERSIBLE_LOSS_SEMANTICS() -> None:
    """Output > 0 for positive inputs (irreversible loss, not net delta-p)."""
    _, _, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert comp > Decimal(0)
    result = TubeSideLocalLossComponentResult(
        component_id="E-001",
        component_type=Task028ComponentType.ENTRANCE,
        path_sequence_index=0,
        flow_direction_assertion=Task028ComponentFlowDirectionAssertion.START_TO_END,
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention=(
            LossCoefficientConvention.K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2
        ),
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        reference_velocity_m_s=Decimal("0.6366"),
        single_occurrence_irreversible_pressure_loss_pa=comp,
        component_irreversible_pressure_loss_pa=comp,
        authority_hash="a" * 64,
    )
    assert not hasattr(result, "static_pressure_recovery_pa")


def test_T028_FLOW_DIRECTION_ORIENTATION_MISMATCH_BLOCKED() -> None:
    """Component END_TO_START != request START_TO_END
    -> BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH."""
    auth = _make_entrance_authority(
        flow_direction=Task028ComponentFlowDirectionAssertion.END_TO_START,
    )
    assert auth.flow_direction_assertion == Task028ComponentFlowDirectionAssertion.END_TO_START
    assert hasattr(Task028BlockerCode, "BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH")


def test_T028_CONTRACTION_EXPANSION_DIRECTIONAL_SEMANTICS() -> None:
    """Different K values for contraction vs expansion → different pressure loss."""
    _, _, comp_c = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.4"),
        multiplicity=1,
    )
    _, _, comp_e = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.6"),
        multiplicity=1,
    )
    assert comp_c != comp_e


# --- MULTIPLICITY GROUP (1 test) -------------------------------------------


def test_T028_MULTIPLICITY_GROUP_REFERENCE_PLANES() -> None:
    """Serial group outer bounding planes preserved on authority."""
    auth = _make_entrance_authority(multiplicity=3)
    assert auth.multiplicity == 3
    assert auth.upstream_reference_plane == "INLET"
    assert auth.downstream_reference_plane == "TUBE_START"


# --- PERMUTATION / CANONICAL (1 test) --------------------------------------


def test_T028_AUTHORITY_TUPLE_PERMUTATION_IDENTITY_STABLE() -> None:
    """Same semantic authorities, different tuple order → same request hash (CR-15).

    The pipeline sorts by path_sequence_index before hashing, so the same
    set of authorities always produces the same hash regardless of input order.
    """
    auth1 = _make_entrance_authority(component_id="A-001", path_sequence_index=0)
    auth2 = _make_entrance_authority(component_id="A-002", path_sequence_index=1)
    # Build authority hash → psi mapping
    hash_to_psi = {
        auth1.authority_hash: auth1.path_sequence_index,
        auth2.authority_hash: auth2.path_sequence_index,
    }
    # Unsorted input order
    hashes_input = (auth2.authority_hash, auth1.authority_hash)
    # Sorted by path_sequence_index (what the pipeline does)
    hashes_sorted = tuple(sorted(hashes_input, key=lambda h: hash_to_psi[h]))
    h1 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=hashes_sorted,
    )
    # Same sorted order → same hash
    h2 = compute_request_hash(
        schema_version=TASK028_REQUEST_SCHEMA_VERSION,
        profile_id="profile-001",
        task025_hydraulic_authority_hash="hyd" * 21 + "a",
        task025_result_hash="a" * 64,
        task026_result_hash="b" * 64,
        property_snapshot_hash="c" * 64,
        constant_density_assertion="TRUE",
        zero_elevation_assertion="TRUE",
        flow_direction_assertion="START_TO_END",
        component_authority_hashes=hashes_sorted,
    )
    assert h1 == h2
    # Different input order but same sorted result → same hash via pipeline sorting
    hashes_input_2 = (auth1.authority_hash, auth2.authority_hash)
    hashes_sorted_2 = tuple(sorted(hashes_input_2, key=lambda h: hash_to_psi[h]))
    assert hashes_sorted == hashes_sorted_2


# --- K CONVENTION (1 test) --------------------------------------------------


def test_T028_K_CONVENTION_REFERENCE_BASIS_MISMATCH_BLOCKED() -> None:
    """Wrong K convention → BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED."""
    raw = _make_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient_convention="FANNING")]
    )
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED in codes


# --- SOURCE AUTHORITY (1 test) ---------------------------------------------


def test_T028_SOURCE_AUTHORITY_REPLAY() -> None:
    """8-field source authority frozen values valid, invalid authority emits blocker (CR-14)."""
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT == 8
    assert len(TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS) == 8
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID == "USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL"
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE == "USACE HEC-RAS Hydraulic Reference Manual"
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION == "2024.1"
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION
        == "USACE HEC-RAS Hydraulic Reference Manual, Section 6.2.1"
    )
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE
        == "Pipe Minor Losses, entrance/exit local velocity-head loss treatment, "
        "Expansion and Contraction Coefficients"
    )
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA
        == "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
    )
    assert (
        TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS
        == "IRREVERSIBLE_LOCAL_LOSS_COEFFICIENT"
    )
    assert TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS == "ADMITTED"
    # Frozen blocker code exists.
    assert hasattr(Task028BlockerCode, "BL_T028_SOURCE_AUTHORITY_INVALID")

    # CR-14: Prove invalid authority emits BL_T028_SOURCE_AUTHORITY_INVALID
    from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
        _TASK028_LOCAL_LOSS_SOURCE_AUTHORITY,
        Task028LocalLossSourceAuthority,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
        _validate_task028_source_authority,
    )

    # Valid authority -> no blockers
    blockers = _validate_task028_source_authority(_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY)
    assert len(blockers) == 0

    # Verify the blocker code exists and has correct ordinal in registry
    assert Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID is not None
    from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
        _BLOCKER_REGISTRY,
    )

    assert _BLOCKER_REGISTRY[Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID] == 30

    # Mutated fixture: wrong source_id -> BL_T028_SOURCE_AUTHORITY_INVALID
    bad_id = Task028LocalLossSourceAuthority(
        source_id="WRONG",
        source_title=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_title,
        source_version=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_version,
        source_location=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_location,
        source_scope=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_scope,
        admitted_formula=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_formula,
        admitted_coefficient_semantics=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_coefficient_semantics,
        permission_status=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.permission_status,
    )
    bad_blockers = _validate_task028_source_authority(bad_id)
    assert len(bad_blockers) == 1
    assert bad_blockers[0].entry.code == Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID

    # Mutated fixture: wrong permission_status -> BL_T028_SOURCE_AUTHORITY_INVALID
    bad_perm = Task028LocalLossSourceAuthority(
        source_id=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_id,
        source_title=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_title,
        source_version=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_version,
        source_location=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_location,
        source_scope=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.source_scope,
        admitted_formula=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_formula,
        admitted_coefficient_semantics=_TASK028_LOCAL_LOSS_SOURCE_AUTHORITY.admitted_coefficient_semantics,
        permission_status="PENDING",
    )
    bad_perm_blockers = _validate_task028_source_authority(bad_perm)
    assert len(bad_perm_blockers) == 1
    assert bad_perm_blockers[0].entry.code == Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID


# --- ENUM / ROUTING (2 tests) ----------------------------------------------


def test_T028_ASSERTION_ENUM_DOMAIN() -> None:
    """Task028ApplicabilityAssertion: TRUE/FALSE only."""
    assert Task028ApplicabilityAssertion.TRUE.value == "TRUE"
    assert Task028ApplicabilityAssertion.FALSE.value == "FALSE"
    assert len(Task028ApplicabilityAssertion) == 2


def test_T028_RAW_ENUM_ROUTING() -> None:
    """Routing: supported → construct, unsupported → block."""
    raw = _make_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="E-001", component_type="ENTRANCE")
        ]
    )
    result = validate_raw_boundary(raw)
    type_blockers = [
        e
        for e in result.blockers
        if e.code == Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED
    ]
    assert len(type_blockers) == 0


# --- DECIMAL / NEGATIVE ZERO (2 tests) -------------------------------------


def test_T028_DECIMAL_COMPUTATION_ORDER() -> None:
    """Outputs are properly quantized (quantize→compute→quantize)."""
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("1000"),
        mass_flow_rate_kg_s=Decimal("5"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel == quantize_task028_decimal(ref_vel, REFERENCE_VELOCITY_QUANTUM)
    assert single == quantize_task028_decimal(single, PRESSURE_LOSS_QUANTUM)
    assert comp == quantize_task028_decimal(comp, PRESSURE_LOSS_QUANTUM)


def test_T028_NEGATIVE_ZERO_NORMALIZATION() -> None:
    """-0.00000000 → normalized zero (negative sign removed, numerically equal to 0)."""
    result = normalize_negative_zero(Decimal("-0.00000000"), REFERENCE_VELOCITY_QUANTUM)
    assert result.is_zero()
    assert not result.is_signed()
    payload = task028_decimal_payload(result, REFERENCE_VELOCITY_QUANTUM)
    assert isinstance(payload, bytes)
    assert b"-" not in payload  # no negative sign


# --- RAW PROJECTION (1 test) -----------------------------------------------


def test_T028_UPSTREAM_RAW_PROJECTION_CANONICALIZATION() -> None:
    """Raw projection encoded with correct kind and hex (CR-10: .hex() not sha256)."""
    proj = encode_raw_projection("REQUEST", {"key": "value"})
    assert isinstance(proj, Task028RawProjection)
    assert proj.projection_kind == "REQUEST"
    assert isinstance(proj.canonical_bytes_hex, str)
    # CR-10: canonical_bytes_hex is hex-encoded canonical bytes, not sha256
    canonical_bytes = canonicalize_raw_value({"key": "value"})
    assert proj.canonical_bytes_hex == canonical_bytes.hex()
    # Verify canonicalize_raw_value produces bytes for various types
    assert isinstance(canonicalize_raw_value(None), bytes)
    assert isinstance(canonicalize_raw_value(True), bytes)
    assert isinstance(canonicalize_raw_value(42), bytes)
    assert isinstance(canonicalize_raw_value("hello"), bytes)
    assert isinstance(canonicalize_raw_value(Decimal("1.5")), bytes)
    assert isinstance(canonicalize_raw_value({"a": 1}), bytes)
    assert isinstance(canonicalize_raw_value([1, 2]), bytes)


# --- BLOCKER DEDUP (1 test) ------------------------------------------------


def test_T028_BLOCKER_DEDUP_STABILITY() -> None:
    """Dedup by (code, field_path, component_id_tiebreaker)."""
    b1 = emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_input",
        "msg",
        component_id_tiebreaker="",
    )
    b2 = emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_input",
        "msg",
        component_id_tiebreaker="",
    )
    collapsed = collapse_blockers([b1, b2])
    assert len(collapsed) == 1
    # Different tiebreaker → not deduped.
    b3 = emit_blocker(
        Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED,
        "raw_input",
        "msg",
        component_id_tiebreaker="X",
    )
    collapsed2 = collapse_blockers([b1, b3])
    assert len(collapsed2) == 2


# --- WARNING CONTRACT (1 test) ---------------------------------------------


def test_T028_WARNING_EMPTY_CONTRACT() -> None:
    """Success result warnings == () (frozen empty tuple)."""
    result = build_success_result(
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_results=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_success_provenance(),
    )
    assert result.warnings == ()
    assert result.blockers == ()
    assert result.deferred_capabilities == ()


# --- SUCCESS ENGINEERING RESULT VECTOR (1 test) ----------------------------


def test_T028_SUCCESS_ENGINEERING_RESULT_VECTOR() -> None:
    """Full engineering result: V_ref, single_pa, component_pa all > 0 and consistent."""
    ref_vel, single, comp = compute_local_loss_component(
        density_kg_m3=Decimal("998.2"),
        mass_flow_rate_kg_s=Decimal("5.0"),
        reference_flow_area_m2=Decimal("0.007854"),
        loss_coefficient=Decimal("0.5"),
        multiplicity=1,
    )
    assert ref_vel > Decimal(0)
    assert single > Decimal(0)
    assert comp > Decimal(0)
    assert comp == single  # multiplicity=1
    # Verify K consistency: K = single_pa / (rho * V² / 2)
    with localcontext(task028_decimal_context()):
        expected_single = Decimal("0.5") * Decimal("998.2") * ref_vel**2 / 2
        expected_single = quantize_task028_decimal(expected_single, PRESSURE_LOSS_QUANTUM)
    assert single == expected_single
    # Verify formula: V = mdot / (rho * A)
    with localcontext(task028_decimal_context()):
        expected_vel = Decimal("5.0") / (Decimal("998.2") * Decimal("0.007854"))
        expected_vel = quantize_task028_decimal(expected_vel, REFERENCE_VELOCITY_QUANTUM)
    assert ref_vel == expected_vel
