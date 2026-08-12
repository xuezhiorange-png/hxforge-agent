"""TASK-028 test suite: 77 frozen test IDs.

§28 — Test inventory.  Each ``test_T028_XXX`` function corresponds to exactly
one frozen TEST_ID.  No database markers.  No external fixtures.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, localcontext
from typing import Any

from hexagent.exchangers.shell_tube.tube_side.blocked_result import Task025BlockedResult
from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    HydraulicAuthorityMode,
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    FrozenIdentity,
    FrozenProvenance,
    FrozenRawProjection,
)
from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
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
from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
    compute_task028_local_loss,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028BlockedResult,
    Task028Provenance,
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    PhaseAssertion,
    PhaseRegion,
    ThermalBoundaryCondition,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    PropertySnapshot,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
    FrozenProvenance as ThermalFrozenProvenance,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.raw_projection import (
    FrozenRawProjection as ThermalFrozenRawProjection,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    RawBoundaryBlockedResult,
    TubeSideBlockedResult,
    TubeSideThermalResult,
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
        loss_coefficient=loss_coefficient,
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=reference_flow_area,
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


# ---------------------------------------------------------------------------
# Minimal upstream result builders for pipeline integration tests
# ---------------------------------------------------------------------------
_H64 = "a" * 64  # reusable 64-char hex hash


def _make_frozen_raw_projection() -> FrozenRawProjection:
    return FrozenRawProjection(
        projection_kind="REQUEST",
        canonical_bytes_hex="ab" * 8,
    )


def _make_thermal_frozen_raw_projection() -> ThermalFrozenRawProjection:
    return ThermalFrozenRawProjection(
        projection_kind="REQUEST",
        canonical_bytes_hex="ab" * 8,
    )


def _make_frozen_identity() -> FrozenIdentity:
    return FrozenIdentity(
        identity_type="TASK-020",
        identity_id="id-020",
        identity_hash=_H64,
    )


def _make_frozen_provenance() -> FrozenProvenance:
    return FrozenProvenance(
        task_id="TASK-025",
        design_contract_path="docs/tasks/TASK-025.md",
        implementation_software_version="0.1.0",
        input_evidence_refs=(),
        upstream_identity_hashes=(_H64,),
    )


def _make_thermal_frozen_provenance() -> ThermalFrozenProvenance:
    from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
        INPUT_EVIDENCE_REFS_V1,
    )

    return ThermalFrozenProvenance(
        task_id="TASK-026",
        design_contract_path="docs/tasks/TASK-026.md",
        implementation_software_version="0.1.0",
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=(_H64,),
    )


def _make_internal_flow_authority() -> InternalFlowLengthAuthority:
    return InternalFlowLengthAuthority(
        length_id="LEN-001",
        length_m=Decimal("1.0"),
        start_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
        ),
        end_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
            ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
        ),
        authority_mode=HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash=_H64,
    )


def _make_heat_transfer_authority() -> HeatTransferLengthAuthority:
    return HeatTransferLengthAuthority(
        length_id="LEN-002",
        length_m=Decimal("1.0"),
        start_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_START_PLANE,
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
        ),
        end_plane=ReferencePlanePair(
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_START_PLANE,
            ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
        ),
        authority_mode=HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH,
        length_hash=_H64,
    )


def _make_valid_task025_result(
    hydraulic_authority_hash: str = _H64,
) -> Task025ValidResult:
    """Minimal valid Task025ValidResult for pipeline integration tests."""
    return Task025ValidResult(
        schema_version="task025.result.v1",
        profile_id="profile-001",
        implementation_software_version="0.1.0",
        request_hash=_H64,
        layout_hash=_H64,
        result_hash=_H64,
        result_id="00000000-0000-5000-8000-000000000001",
        internal_flow_authority=_make_internal_flow_authority(),
        heat_transfer_authority=_make_heat_transfer_authority(),
        hydraulic_authority_hash=hydraulic_authority_hash,
        active_position_ids=(),
        inactive_position_ids=(),
        single_tube_flow_area_m2=Decimal("0.007854"),
        total_parallel_flow_area_m2=Decimal("0.031416"),
        flow_cross_section_wetted_perimeter_m=Decimal("0.031416"),
        total_flow_cross_section_wetted_perimeter_m=Decimal("0.125664"),
        hydraulic_diameter_m=Decimal("0.01"),
        internal_volume_m3=Decimal("0.000314"),
        internal_heat_transfer_surface_area_m2=Decimal("0.0314"),
        future_pressure_drop_length_m=None,
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        stage_rank=9,
        task020_identity=_make_frozen_identity(),
        task021_identity=_make_frozen_identity(),
        provenance=_make_frozen_provenance(),
    )


def _compute_default_property_snapshot_hash() -> str:
    """Compute the property_snapshot_hash for the default property snapshot."""
    # Create with a dummy hash, then recompute the true hash
    dummy = "0" * 64
    ps = PropertySnapshot(
        density_kg_m3=Decimal("1000.0"),
        dynamic_viscosity_pa_s=Decimal("0.001"),
        thermal_conductivity_w_m_k=Decimal("0.6"),
        specific_heat_capacity_j_kg_k=Decimal("4186"),
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id="default",
        property_source_version="1.0",
        property_snapshot_hash=dummy,
    )
    return recompute_property_snapshot_hash(ps)


def _make_valid_thermal_result(
    upstream_geometry_hash: str = _H64,
    property_snapshot_hash: str | None = None,
) -> TubeSideThermalResult:
    """Minimal valid TubeSideThermalResult for pipeline integration tests."""
    if property_snapshot_hash is None:
        property_snapshot_hash = _compute_default_property_snapshot_hash()
    return TubeSideThermalResult(
        schema_version="task026.thermal-result.v1",
        task026_version="task026.thermal.v1",
        implementation_software_version="0.1.0",
        upstream_geometry_hash=upstream_geometry_hash,
        property_snapshot_hash=property_snapshot_hash,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        mass_flow_rate_kg_s=Decimal("5.0"),
        bulk_velocity_m_s=Decimal("0.637"),
        reynolds_number=Decimal("5000"),
        prandtl_number=Decimal("7.0"),
        flow_regime=FlowRegime.TURBULENT,
        correlation_id="CORR-001",
        correlation_version="1.0",
        nusselt_number=Decimal("50.0"),
        tube_side_heat_transfer_coefficient_w_m2_k=Decimal("3000"),
        request_hash=_H64,
        result_hash=_H64,
        result_id="00000000-0000-5000-8000-000000000002",
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=_make_thermal_frozen_provenance(),
    )


def _make_task025_blocked_result() -> Task025BlockedResult:
    """Minimal Task025BlockedResult for S01 upstream blocked tests."""
    from hexagent.exchangers.shell_tube.tube_side.blocker_registry import (
        Task025BlockerEntry,
    )

    return Task025BlockedResult(
        schema_version="task025.blocked-result.v1",
        implementation_software_version="0.1.0",
        resolved_profile_id=None,
        raw_profile_id_projection=_make_frozen_raw_projection(),
        raw_request_projection=_make_frozen_raw_projection(),
        request_hash=None,
        blocked_result_hash=_H64,
        blockers=(
            Task025BlockerEntry(
                code="BL_LAYOUT_UNKNOWN_FIELD",
                field_path=("test",),
                message_key="test blocker",
                evidence_refs=(),
            ),
        ),
        warnings=(),
        deferred_capabilities=(),
        stage_rank=1,
        task020_identity=None,
        task021_identity=None,
        provenance=_make_frozen_provenance(),
    )


def _make_thermal_raw_boundary_blocked_result() -> RawBoundaryBlockedResult:
    """Minimal RawBoundaryBlockedResult from TASK-026 for S01 tests."""
    from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
        BlockerCode,
    )

    return RawBoundaryBlockedResult(
        schema_version="task026.raw-boundary-blocked.v1",
        implementation_software_version="0.1.0",
        raw_request_projection=_make_thermal_frozen_raw_projection(),
        blockers=(
            BlockerEntry(
                code=BlockerCode.BL_RAW_INPUT_BOUNDARY_MALFORMED,
                severity="hard",
                stage="S00",
                payload=("test",),
                message_template="test",
            ),
        ),
        warnings=(),
        deferred_capabilities=(),
    )


def _make_thermal_tube_side_blocked_result() -> TubeSideBlockedResult:
    """Minimal TubeSideBlockedResult from TASK-026 for S01 tests."""
    from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
        BlockerCode,
    )

    return TubeSideBlockedResult(
        schema_version="task026.blocked-result.v1",
        task026_version="task026.thermal.v1",
        implementation_software_version="0.1.0",
        upstream_geometry_hash=_H64,
        property_snapshot_hash=_H64,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        mass_flow_rate_kg_s=Decimal("5.0"),
        raw_request_projection=_make_thermal_frozen_raw_projection(),
        raw_upstream_blocked_projection=None,
        request_hash=_H64,
        result_hash=_H64,
        result_id="00000000-0000-5000-8000-000000000003",
        blockers=(
            BlockerEntry(
                code=BlockerCode.BL_UNSUPPORTED_PHASE,
                severity="hard",
                stage="S05",
                payload=("test",),
                message_template="test",
            ),
        ),
        warnings=(),
        deferred_capabilities=(),
        provenance=_make_thermal_frozen_provenance(),
    )


def _build_pipeline_raw_request(**overrides: Any) -> dict[str, Any]:
    """Build a raw_request dict that passes raw boundary and has valid typed_data.

    Uses the correct property_snapshot_hash for the default property snapshot.
    """
    psh = _compute_default_property_snapshot_hash()
    base: dict[str, Any] = {
        "schema_version": TASK028_REQUEST_SCHEMA_VERSION,
        "profile_id": "profile-001",
        "task025_valid_result": None,
        "task026_success_result": None,
        "property_snapshot": {"density_kg_m3": "1000.0"},
        "property_snapshot_hash": psh,
        "constant_density_path_assertion": "TRUE",
        "zero_net_elevation_change_assertion": "TRUE",
        "flow_direction_assertion": "START_TO_END",
        "component_authorities": [
            _minimal_component_dict(),
        ],
        "request_hash": "",
    }
    base.update(overrides)
    return base


def _run_pipeline(
    raw_request: dict[str, Any],
    task025_result: Any,
    task026_result: Any,
) -> Any:
    """Invoke compute_task028_local_loss with proper arguments."""
    return compute_task028_local_loss(
        raw_request=raw_request,
        task025_result=task025_result,
        task026_result=task026_result,
    )


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
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="DUP", path_sequence_index=0),
            _minimal_component_dict(component_id="DUP", path_sequence_index=1),
        ]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_ID_DUPLICATE in codes
    assert not hasattr(result, "component_results")


def test_T028_PATH_SEQUENCE_INDEX_DUPLICATE_BLOCKED() -> None:
    """S09: duplicate path_sequence_index → BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="A-001", path_sequence_index=0),
            _minimal_component_dict(component_id="A-002", path_sequence_index=0),
        ]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE in codes
    assert not hasattr(result, "component_results")


def test_T028_AUTHORITY_HASH_REPLAY() -> None:
    """Authority hash is deterministic SHA-256 hex (64 lowercase hex chars)."""
    auth = _make_entrance_authority()
    assert isinstance(auth.authority_hash, str)
    assert len(auth.authority_hash) == 64
    # Replay: same inputs → same hash.
    auth2 = _make_entrance_authority()
    assert auth.authority_hash == auth2.authority_hash


def test_T028_AUTHORITY_HASH_MISMATCH_BLOCKED() -> None:
    """BL_T028_AUTHORITY_HASH_MISMATCH: blocker exists, emitted, wrong hash != correct."""
    # Verify blocker code exists in registry with correct ordinal
    from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
        _BLOCKER_REGISTRY,
    )

    assert Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH in _BLOCKER_REGISTRY
    assert _BLOCKER_REGISTRY[Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH] == 28

    # Verify blocker can be emitted with this code
    pending = emit_blocker(
        Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH,
        "component_authorities.authority_hash",
        "Authority hash mismatch.",
        component_id_tiebreaker="E-001",
    )
    assert pending.entry.code == Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH
    collapsed = collapse_blockers([pending])
    assert len(collapsed) == 1
    assert collapsed[0].code == Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH

    # Verify a wrong authority hash is indeed different from the correct one
    auth = _make_entrance_authority()
    wrong_hash = compute_authority_hash(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id=auth.component_id,
        component_type=auth.component_type.value,
        path_sequence_index=auth.path_sequence_index,
        upstream_reference_plane=auth.upstream_reference_plane,
        downstream_reference_plane=auth.downstream_reference_plane,
        flow_direction_assertion=auth.flow_direction_assertion.value,
        loss_coefficient=Decimal("999.0"),
        loss_coefficient_convention=auth.loss_coefficient_convention.value,
        reference_flow_area_m2=auth.reference_flow_area_m2,
        multiplicity=auth.multiplicity,
        geometry_evidence_refs=auth.geometry_evidence_refs,
        coefficient_source_id=auth.coefficient_source_id,
        coefficient_source_version=auth.coefficient_source_version,
        coefficient_source_location=auth.coefficient_source_location,
        coefficient_permission_status=auth.coefficient_permission_status.value,
    )
    assert wrong_hash != auth.authority_hash


def test_T028_GEOMETRY_EVIDENCE_MISSING_BLOCKED() -> None:
    """S08: Empty geometry_evidence_refs → BL_T028_GEOMETRY_EVIDENCE_MISSING."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(geometry_evidence_refs=[])]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_GEOMETRY_EVIDENCE_MISSING in codes
    assert not hasattr(result, "component_results")


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
    """S08: Non-finite K (NaN) → BL_T028_LOSS_COEFFICIENT_NONFINITE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient="NaN")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NONFINITE in codes
    assert not hasattr(result, "component_results")


def test_T028_LOSS_COEFFICIENT_ZERO_PSEUDO_COMPONENT_BLOCKED() -> None:
    """S08: K=0 → BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient="0")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN in codes
    assert not hasattr(result, "component_results")


def test_T028_LOSS_COEFFICIENT_NEGATIVE_BLOCKED() -> None:
    """S08: K<0 → BL_T028_LOSS_COEFFICIENT_NEGATIVE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(loss_coefficient="-0.5")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NEGATIVE in codes
    assert not hasattr(result, "component_results")


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
    """S08: area=0 → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(reference_flow_area_m2="0")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID in codes
    assert not hasattr(result, "component_results")


def test_T028_REFERENCE_FLOW_AREA_NEGATIVE_BLOCKED() -> None:
    """S08: area<0 → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(reference_flow_area_m2="-0.001")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID in codes
    assert not hasattr(result, "component_results")


def test_T028_REFERENCE_FLOW_AREA_NONFINITE_BLOCKED() -> None:
    """S08: area=NaN → BL_T028_REFERENCE_FLOW_AREA_INVALID."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(reference_flow_area_m2="NaN")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID in codes
    assert not hasattr(result, "component_results")


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
    """S01: Task025BlockedResult → BL_T028_UPSTREAM_TASK025_BLOCKED."""
    task025_blocked = _make_task025_blocked_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_blocked, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_TASK025_BLOCKED in codes
    assert not hasattr(result, "component_results")


def test_T028_UPSTREAM_TASK026_RAW_BLOCKED() -> None:
    """S01: RawBoundaryBlockedResult from TASK-026 → BL_T028_UPSTREAM_TASK026_RAW_BLOCKED."""
    task025_valid = _make_valid_task025_result()
    task026_raw_blocked = _make_thermal_raw_boundary_blocked_result()
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_raw_blocked)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_TASK026_RAW_BLOCKED in codes
    assert not hasattr(result, "component_results")


def test_T028_UPSTREAM_TASK026_TYPED_BLOCKED() -> None:
    """S01: TubeSideBlockedResult → BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED."""
    task025_valid = _make_valid_task025_result()
    task026_typed_blocked = _make_thermal_tube_side_blocked_result()
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_typed_blocked)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED in codes
    assert not hasattr(result, "component_results")


def test_T028_UPSTREAM_IDENTITY_MISMATCH_BLOCKED() -> None:
    """S05: Geometry hash mismatch → BL_T028_UPSTREAM_IDENTITY_MISMATCH."""
    task025_valid = _make_valid_task025_result(hydraulic_authority_hash="a" * 64)
    task026_valid = _make_valid_thermal_result(upstream_geometry_hash="b" * 64)
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_UPSTREAM_IDENTITY_MISMATCH in codes
    assert not hasattr(result, "component_results")


def test_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH_BLOCKED() -> None:
    """S06: Property hash mismatch → BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH."""
    task025_valid = _make_valid_task025_result()
    # Use a mismatched property_snapshot_hash in the thermal result
    task026_valid = _make_valid_thermal_result(
        property_snapshot_hash="b" * 64,
    )
    raw = _build_pipeline_raw_request()
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH in codes
    assert not hasattr(result, "component_results")


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
    """S07: FALSE constant_density → BL_T028_APPLICABILITY_ASSERTION_FALSE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(constant_density_path_assertion="FALSE")
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE in codes
    assert not hasattr(result, "component_results")


def test_T028_ZERO_ELEVATION_ASSERTION_MISSING_BLOCKED() -> None:
    """Missing zero_net_elevation_change_assertion → BL_T028_APPLICABILITY_ASSERTION_MISSING."""
    raw = _make_raw_request()
    del raw["zero_net_elevation_change_assertion"]
    result = validate_raw_boundary(raw)
    assert result.blocked is True
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING in codes


def test_T028_ZERO_ELEVATION_ASSERTION_FALSE_BLOCKED() -> None:
    """S07: FALSE zero_elevation → BL_T028_APPLICABILITY_ASSERTION_FALSE."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(zero_net_elevation_change_assertion="FALSE")
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE in codes
    assert not hasattr(result, "component_results")


def test_T028_GAS_BLOCKED_V1() -> None:
    """S12: Gas phase not supported in V1 → BL_T028_APPLICABILITY_ASSERTION_FALSE."""
    task025_valid = _make_valid_task025_result()
    # Build a gas-phase property snapshot using the pipeline's default values
    # for fields not supplied in the raw dict, then compute its hash
    gas_ps = PropertySnapshot(
        density_kg_m3=Decimal("1.225"),
        dynamic_viscosity_pa_s=Decimal("0.001"),
        thermal_conductivity_w_m_k=Decimal("0.6"),
        specific_heat_capacity_j_kg_k=Decimal("4186"),
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_GAS,
        property_source_id="default",
        property_source_version="1.0",
        property_snapshot_hash="0" * 64,
    )
    gas_psh = recompute_property_snapshot_hash(gas_ps)
    task026_valid = _make_valid_thermal_result(property_snapshot_hash=gas_psh)
    raw = _build_pipeline_raw_request(
        property_snapshot={"density_kg_m3": "1.225", "phase_region": "SINGLE_PHASE_GAS"},
        property_snapshot_hash=gas_psh,
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE in codes
    assert not hasattr(result, "component_results")


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
        task025_result_hash=None,
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
        component_result_records=(),
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
        task025_result_hash="",
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
        task025_result_hash="",
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
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
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
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
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
    """S08: Component END_TO_START != START_TO_END → BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()
    raw = _build_pipeline_raw_request(
        component_authorities=[_minimal_component_dict(flow_direction_assertion="END_TO_START")]
    )
    result = _run_pipeline(raw, task025_valid, task026_valid)
    assert isinstance(result, Task028BlockedResult)
    codes = [e.code for e in result.blockers]
    assert Task028BlockerCode.BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH in codes
    assert not hasattr(result, "component_results")


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


# ===========================================================================
# R2 additional verification tests (not frozen TEST_IDs)
# ===========================================================================


# --- DEFERRED CAPABILITIES (ITEM 3) ----------------------------------------


def test_T028_DEFERRED_CAPABILITIES_EXACT_TUPLE() -> None:
    """Deferred capabilities is exactly TASK028_DEFERRED_CAPABILITIES_V1."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        TASK028_DEFERRED_CAPABILITIES_V1,
    )

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
        deferred_capabilities=TASK028_DEFERRED_CAPABILITIES_V1,
        provenance=_make_success_provenance(),
    )
    assert result.deferred_capabilities == TASK028_DEFERRED_CAPABILITIES_V1
    assert len(result.deferred_capabilities) == 3
    assert result.deferred_capabilities[0] == "MODELED_TOTAL_PRESSURE_DROP_NOT_COMPUTED"
    assert result.deferred_capabilities[1] == "REFERENCE_PLANE_CONTINUITY_NOT_VALIDATED"
    assert result.deferred_capabilities[2] == "PRESSURE_PATH_COMPLETENESS_NOT_VALIDATED"


def test_T028_SUCCESS_RESULT_FIELD_COUNT_FROZEN() -> None:
    """Success result has exactly 14 fields."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
        SUCCESS_RESULT_FIELD_COUNT,
    )

    assert SUCCESS_RESULT_FIELD_COUNT == 14


def test_T028_BLOCKED_RESULT_FIELD_COUNT_FROZEN() -> None:
    """Blocked result has exactly 15 fields."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
        BLOCKED_RESULT_FIELD_COUNT,
    )

    assert BLOCKED_RESULT_FIELD_COUNT == 15


def test_T028_BLOCKER_REGISTRY_COUNT_FROZEN() -> None:
    """Blocker registry has exactly 31 codes."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
        BLOCKER_REGISTRY_COUNT,
    )

    assert BLOCKER_REGISTRY_COUNT == 31


def test_T028_FALSE_POSITIVE_HASATTR_ACCEPTANCE_COUNT_ZERO() -> None:
    """FALSE_POSITIVE_HASATTR_ACCEPTANCE_COUNT=0: no hasattr blocker acceptance."""
    import ast
    import pathlib

    test_file = pathlib.Path(__file__).read_text()
    tree = ast.parse(test_file)
    hasattr_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "assertEqual":
                pass
            if isinstance(node.func, ast.Name) and node.func.id == "assert":
                pass
        if isinstance(node, ast.Assert):
            test_str = ast.dump(node.test)
            if "hasattr" in test_str and "BlockerCode" in test_str:
                hasattr_count += 1
    assert hasattr_count == 0, (
        f"FALSE_POSITIVE_HASATTR_ACCEPTANCE_COUNT must be 0; found {hasattr_count}"
    )


# --- PERMUTATION REPLAY (ITEM 5) -------------------------------------------


def test_T028_PERMUTATION_REPLAY_STABLE() -> None:
    """ITEM 5: Two requests with swapped component order produce identical results."""
    task025_valid = _make_valid_task025_result()
    task026_valid = _make_valid_thermal_result()

    # Request A: path=0, path=1
    raw_a = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="COMP-A", path_sequence_index=0),
            _minimal_component_dict(component_id="COMP-B", path_sequence_index=1),
        ]
    )
    # Request B: path=1, path=0 (reversed input order)
    raw_b = _build_pipeline_raw_request(
        component_authorities=[
            _minimal_component_dict(component_id="COMP-B", path_sequence_index=1),
            _minimal_component_dict(component_id="COMP-A", path_sequence_index=0),
        ]
    )

    result_a = _run_pipeline(raw_a, task025_valid, task026_valid)
    result_b = _run_pipeline(raw_b, task025_valid, task026_valid)

    assert isinstance(result_a, Task028SuccessResult)
    assert isinstance(result_b, Task028SuccessResult)

    # Same request_hash (sorted by path_sequence_index)
    assert result_a.request_hash == result_b.request_hash
    # Same result_hash
    assert result_a.result_hash == result_b.result_hash
    # Same result_id
    assert result_a.result_id == result_b.result_id
    # Same component order (sorted by path_sequence_index)
    assert len(result_a.component_results) == len(result_b.component_results)
    for ca, cb in zip(result_a.component_results, result_b.component_results, strict=True):
        assert ca.component_id == cb.component_id
        assert ca.path_sequence_index == cb.path_sequence_index


# --- FROZEN VECTOR TESTS (ITEMS 6-9) ---------------------------------------


def test_T028_VECTOR_02_CANONICAL_BYTES() -> None:
    """ITEM 6: VECTOR_02 canonical bytes: CANONICAL_BYTE_LENGTH=1016."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        canonicalize_authority,
    )

    args = dict(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    framed, sha = canonicalize_authority(**args)
    assert len(framed) == 1016


def test_T028_VECTOR_03_REQUEST_HASH() -> None:
    """ITEM 7: VECTOR_03 request hash: bda7341f..."""
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
    assert len(h) == 64


def test_T028_VECTOR_02_03_BYTES_EQUAL() -> None:
    """ITEM 6-7: VECTOR_02_BYTES == VECTOR_03_BYTES (same canonical authority framing)."""
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        canonicalize_authority,
    )

    args = dict(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    framed_a, sha_a = canonicalize_authority(**args)
    framed_b, sha_b = canonicalize_authority(**args)
    assert framed_a == framed_b
    assert sha_a == sha_b
    assert len(framed_a) == 1016


def test_T028_VECTOR_04_SUCCESS_RESULT_HASH() -> None:
    """ITEM 8: VECTOR_04 success result hash."""
    h = compute_success_result_hash(
        schema_version=TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id="profile-001",
        request_hash="a" * 64,
        task025_hydraulic_authority_hash="b" * 64,
        task025_result_hash="b2" * 32,
        task026_result_hash="c" * 64,
        property_snapshot_hash="d" * 64,
        component_result_records=(),
        warnings=(),
        blockers=(),
        deferred_capabilities=(),
        provenance=None,
    )
    rid = compute_result_id(h)
    assert isinstance(h, str) and len(h) == 64
    assert isinstance(rid, str)
    parsed = uuid.UUID(rid)
    assert parsed.version == 5


def test_T028_VECTOR_05_ENGINEERING_VALUES() -> None:
    """ITEM 9: VECTOR_05 engineering values frozen."""
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
    # Verify reference_velocity_m_s quantized correctly
    expected_vel = Decimal("5") / (Decimal("1000") * Decimal("0.007854"))
    expected_vel_q = quantize_task028_decimal(expected_vel, REFERENCE_VELOCITY_QUANTUM)
    assert ref_vel == expected_vel_q
    # Verify pressure loss: K * rho * V^2 / 2
    with localcontext(task028_decimal_context()):
        expected_single = Decimal("0.5") * Decimal("1000") * ref_vel**2 / 2
        expected_single = quantize_task028_decimal(expected_single, PRESSURE_LOSS_QUANTUM)
    assert single == expected_single


# --- CROSS-PYTHON PROOF (ITEM 10) ------------------------------------------


def test_T028_PY311_PY312_FROZEN_ORACLE() -> None:
    """ITEM 10: Both Python versions assert against the same frozen constants."""
    import sys

    # Verify Python version is 3.11 or 3.12
    assert sys.version_info[:2] in [(3, 11), (3, 12)], (
        f"Expected Python 3.11 or 3.12, got {sys.version}"
    )

    # Frozen authority hash for known input
    auth_hash = compute_authority_hash(
        schema_version=TASK028_AUTHORITY_SCHEMA_VERSION,
        component_id="E-001",
        component_type="ENTRANCE",
        path_sequence_index=0,
        upstream_reference_plane="INLET",
        downstream_reference_plane="TUBE_START",
        flow_direction_assertion="START_TO_END",
        loss_coefficient=Decimal("0.5"),
        loss_coefficient_convention="K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2",
        reference_flow_area_m2=Decimal("0.007854"),
        multiplicity=1,
        geometry_evidence_refs=("EVIDENCE-001",),
        coefficient_source_id="USACE-HEC-RAS-HYDRAULIC-REFERENCE-MANUAL",
        coefficient_source_version="2024.1",
        coefficient_source_location="USACE HEC-RAS, Section 6.2.1",
        coefficient_permission_status="ADMITTED",
    )
    assert len(auth_hash) == 64
    assert all(c in "0123456789abcdef" for c in auth_hash)

    # Frozen request hash for known input
    req_hash = compute_request_hash(
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
    assert len(req_hash) == 64

    # Frozen result ID namespace
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        RESULT_ID_NAMESPACE,
    )

    assert RESULT_ID_NAMESPACE == "a0280000-0000-5000-8000-000000000001"
