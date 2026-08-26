"""TASK-035 frozen public-boundary, composition, and identity tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition import (
    validate_request,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.canonical import (
    canonical_bytes,
    request_canonical_projection,
    request_hash,
    result_id,
    success_result_canonical_projection,
    success_result_hash,
    task031_geometry_hash,
    task031_geometry_id,
    task032_result_id,
    task032_success_hash,
    task033_result_id,
    task033_success_hash,
    task034_result_id,
    task034_success_hash,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.provenance import (
    verify_provenance,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.schema import (
    APPLICABILITY_PROFILE_ID,
    COMPLETENESS_CLASSIFICATION_UNIVERSE,
    COMPLETENESS_PROFILE_ID,
    DEFERRED_CAPABILITIES,
    PROFILE_ID,
    PROVENANCE_FIELDS,
    REQUEST_SCHEMA_VERSION,
    TASK031_GEOMETRY_FIELDS,
    TASK032_SUCCESS_RESULT_FIELDS,
    TASK032_TYPED_BLOCKED_RESULT_FIELDS,
    TASK033_SUCCESS_RESULT_FIELDS,
    TASK033_TYPED_BLOCKED_RESULT_FIELDS,
    TASK034_SUCCESS_RESULT_FIELDS,
    TASK034_TYPED_BLOCKED_RESULT_FIELDS,
)


def _hex(digit: str) -> str:
    return digit * 64


def _geometry() -> dict[str, Any]:
    geometry: dict[str, Any] = {
        "schema_version": "task031.shell-side-hydraulic-geometry.v1",
        "geometry_id": "",
        "geometry_hash": "",
        "request_hash": _hex("1"),
        "task020_configuration_id": "configuration-001",
        "task020_configuration_hash": _hex("2"),
        "task021_layout_id": "layout-001",
        "task021_layout_hash": _hex("3"),
        "task022_geometry_id": "tube-geometry-001",
        "task022_geometry_hash": _hex("4"),
        "task024_geometry_id": "baffle-geometry-001",
        "task024_geometry_hash": _hex("5"),
        "engineering_authority_id": "task031-authority-001",
        "engineering_authority_hash": _hex("6"),
        "formula_a_id": "TASK031_FORMULA_A_V1",
        "formula_b_id": "TASK031_FORMULA_B_V1",
        "pattern_family": "TRIANGULAR_30_DEG",
        "flow_region_identity": "CENTRAL_CROSSFLOW_SCREENING",
        "central_inter_baffle_spacing_m": "0.100",
        "central_crossflow_flow_area_m2": "0.010",
        "shell_side_equivalent_hydraulic_diameter_m": "0.020",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "provenance": [],
    }
    assert tuple(geometry) == TASK031_GEOMETRY_FIELDS
    geometry["geometry_hash"] = task031_geometry_hash(geometry)
    geometry["geometry_id"] = task031_geometry_id(geometry["geometry_hash"])
    return geometry


def _flow(geometry: dict[str, Any]) -> dict[str, Any]:
    flow: dict[str, Any] = {
        "schema_version": "task032.shell-side-flow-state.v1",
        "profile_id": "hxforge.shell_tube.shell_side_flow_state.v1",
        "implementation_software_version": "task032.shell-side-flow-state-impl-v1",
        "shell_side_case_id": "case-001",
        "shell_side_stream_id": "stream-001",
        "shell_side_fluid_id": "fluid-001",
        "task020_configuration_id": geometry["task020_configuration_id"],
        "task020_configuration_hash": geometry["task020_configuration_hash"],
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": _hex("7"),
        "mass_flow_authority_hash": _hex("8"),
        "engineering_authority_id": "task032-authority-001",
        "engineering_authority_hash": _hex("9"),
        "flow_model": "SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING",
        "phase_region": "SINGLE_PHASE_LIQUID",
        "rheology_model": "NEWTONIAN",
        "shell_side_mass_flow_rate_kg_s": "1.000",
        "shell_side_mass_velocity_kg_m2_s": "100.000",
        "shell_side_bulk_velocity_m_s": "2.000",
        "shell_side_reynolds_number": "4000.000",
        "shell_side_prandtl_number": "5.000",
        "request_hash": _hex("a"),
        "result_hash": "",
        "result_id": "",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "provenance": [],
    }
    assert tuple(flow) == TASK032_SUCCESS_RESULT_FIELDS
    flow["result_hash"] = task032_success_hash(flow)
    flow["result_id"] = task032_result_id(flow["result_hash"])
    return flow


def _heat(geometry: dict[str, Any], flow: dict[str, Any]) -> dict[str, Any]:
    heat: dict[str, Any] = {
        "schema_version": "task033.shell-side-heat-transfer.v1",
        "profile_id": "hxforge.shell_tube.shell_side_heat_transfer.v1",
        "first_slice_profile_id": (
            "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_KHARAJI_2021_EQ58_"
            "OUTER_TUBE_SURFACE_HTC_SCREENING_V1"
        ),
        "implementation_software_version": "task033.shell-side-heat-transfer-impl-v1",
        "shell_side_case_id": flow["shell_side_case_id"],
        "shell_side_stream_id": flow["shell_side_stream_id"],
        "shell_side_fluid_id": flow["shell_side_fluid_id"],
        "task020_configuration_id": geometry["task020_configuration_id"],
        "task020_configuration_hash": geometry["task020_configuration_hash"],
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": flow["property_snapshot_hash"],
        "mass_flow_authority_hash": flow["mass_flow_authority_hash"],
        "task032_request_hash": flow["request_hash"],
        "task032_result_hash": flow["result_hash"],
        "task032_result_id": flow["result_id"],
        "correlation_id": "TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1",
        "engineering_source_authority_record_id": "task033-authority-001",
        "heat_transfer_surface": "OUTER_TUBE_SURFACE",
        "modeled_shell_side_heat_transfer_coefficient_w_m2_k": "125.000",
        "request_hash": _hex("b"),
        "result_hash": "",
        "result_id": "",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "applicability_context": [
            ["flow_region_identity", "CENTRAL_CROSSFLOW_SCREENING"],
            ["phase_region", "SINGLE_PHASE_LIQUID"],
            ["rheology_model", "NEWTONIAN"],
        ],
        "provenance": [],
    }
    assert tuple(heat) == TASK033_SUCCESS_RESULT_FIELDS
    heat["result_hash"] = task033_success_hash(heat)
    heat["result_id"] = task033_result_id(heat["result_hash"])
    return heat


def _pressure(
    geometry: dict[str, Any], flow: dict[str, Any], heat: dict[str, Any]
) -> dict[str, Any]:
    pressure: dict[str, Any] = {
        "schema_version": "task034.shell-side-pressure-drop-success.v1",
        "profile_id": "hxforge.shell_tube.shell_side_pressure_drop.v1",
        "first_slice_profile_id": (
            "TASK034_KERN_BAYRAM_SEVILGEN_2017_EQ15_EQ16_EQ17_WALL_VISCOSITY_CORRECTION_V1"
        ),
        "implementation_software_version": "task034.shell-side-pressure-drop-impl-v1",
        "shell_side_case_id": flow["shell_side_case_id"],
        "shell_side_stream_id": flow["shell_side_stream_id"],
        "shell_side_fluid_id": flow["shell_side_fluid_id"],
        "task020_configuration_id": geometry["task020_configuration_id"],
        "task020_configuration_hash": geometry["task020_configuration_hash"],
        "task031_request_hash": geometry["request_hash"],
        "task031_geometry_id": geometry["geometry_id"],
        "task031_geometry_hash": geometry["geometry_hash"],
        "property_snapshot_hash": flow["property_snapshot_hash"],
        "mass_flow_authority_hash": flow["mass_flow_authority_hash"],
        "task032_request_hash": flow["request_hash"],
        "task032_result_hash": flow["result_hash"],
        "task032_result_id": flow["result_id"],
        "task033_request_hash": heat["request_hash"],
        "task033_result_hash": heat["result_hash"],
        "task033_result_id": heat["result_id"],
        "correlation_id": (
            "TASK034_KERN_BAYRAM_SEVILGEN_2017_EQ15_EQ16_EQ17_WALL_VISCOSITY_CORRECTION_V1"
        ),
        "engineering_source_authority_record_id": "task034-authority-001",
        "source_id": "TASK034_SOURCE_V1",
        "source_version": "TASK034_SOURCE_VERSION_1",
        "source_location": "TASK034_SOURCE_LOCATION_1",
        "wall_property_schema_version": "wall-property.v1",
        "wall_property_source_id": "wall-source-001",
        "wall_property_source_version": "wall-source-version-1",
        "wall_property_snapshot_hash": _hex("c"),
        "wall_property_authority_hash": _hex("d"),
        "modeled_shell_side_pressure_drop_pa": "10.000",
        "request_hash": _hex("e"),
        "result_hash": "",
        "result_id": "",
        "warnings": [],
        "blockers": [],
        "deferred_capabilities": [],
        "applicability_context": [
            ["flow_region_identity", "CENTRAL_CROSSFLOW_SCREENING"],
            ["phase_region", "SINGLE_PHASE_LIQUID"],
            ["rheology_model", "NEWTONIAN"],
        ],
        "physical_boundary_context": [
            ["construction_family", "SHELL_AND_TUBE"],
            ["physical_boundary_profile", "CENTRAL_CROSSFLOW_SHELL_SIDE_MODELED_DP"],
            ["shell_pass_count", "1"],
        ],
        "provenance": [],
    }
    assert tuple(pressure) == TASK034_SUCCESS_RESULT_FIELDS
    pressure["result_hash"] = task034_success_hash(pressure)
    pressure["result_id"] = task034_result_id(pressure["result_hash"])
    return pressure


def _valid_request() -> dict[str, Any]:
    geometry = _geometry()
    flow = _flow(geometry)
    heat = _heat(geometry, flow)
    pressure = _pressure(geometry, flow, heat)
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "task031_result": {
            "status": "VALID",
            "geometry": geometry,
            "warnings": [],
            "blockers": [],
            "deferred_capabilities": [],
            "blocked_result_hash": None,
        },
        "task032_result": {
            "status": "VALID",
            "flow_state": flow,
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "task033_result": {
            "status": "VALID",
            "heat_transfer": heat,
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "task034_result": {
            "status": "VALID",
            "pressure_drop": pressure,
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
        "evidence_refs": ["task035-test-evidence"],
    }


def _typed_blocked_payload(
    fields: tuple[str, ...], schema_version: str, hash_field: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {field: None for field in fields}
    payload.update(
        {
            "schema_version": schema_version,
            "profile_id": "upstream-profile.v1",
            "implementation_software_version": "upstream-impl-v1",
            "failure_stage": "S01",
            "blockers": [{"code": "UPSTREAM_BLOCKED"}],
            "warnings": [],
            "deferred_capabilities": [],
            "provenance": [],
        }
    )
    payload[hash_field] = _hex("f")
    if "result_id" in fields:
        payload["result_id"] = "upstream-blocked-result-id"
    return payload


def _codes(result: Any) -> tuple[str, ...]:
    return tuple(entry.code for entry in result.blockers)


def _rebuild_task033(request: dict[str, Any]) -> None:
    payload = request["task033_result"]["heat_transfer"]
    payload["result_hash"] = task033_success_hash(payload)
    payload["result_id"] = task033_result_id(payload["result_hash"])


def _rebuild_task034(request: dict[str, Any]) -> None:
    payload = request["task034_result"]["pressure_drop"]
    payload["result_hash"] = task034_success_hash(payload)
    payload["result_id"] = task034_result_id(payload["result_hash"])


def test_T035_001_raw_boundary_deterministic_projection() -> None:
    """Raw-boundary projection is bounded, typed, and repeatable."""

    raw = {"unexpected": "value"}
    first = validate_request(raw)
    second = validate_request(raw)
    assert first.raw_boundary_blocked_result is not None
    assert second.raw_boundary_blocked_result is not None
    assert first.raw_boundary_blocked_result.raw_request_projection == (
        second.raw_boundary_blocked_result.raw_request_projection
    )
    assert first.raw_boundary_blocked_result.blocked_result_hash == (
        second.raw_boundary_blocked_result.blocked_result_hash
    )
    assert _codes(first) == ("SSTHC_UNKNOWN_FIELD",)


def test_T035_002_request_schema_profile() -> None:
    """The seven-field request rejects unsupported schema and profile identities."""

    request = _valid_request()
    request["schema_version"] = "unsupported.v1"
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_SCHEMA_VERSION_UNSUPPORTED",)

    request = _valid_request()
    request["profile_id"] = "unsupported-profile.v1"
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_PROFILE_ID_UNSUPPORTED",)


def test_T035_003_TASK031_success_contract() -> None:
    """A valid TASK031 public geometry envelope is accepted and replayed."""

    result = validate_request(_valid_request())
    assert result.success_result is not None
    assert result.success_result.task031_geometry_id
    assert result.success_result.task031_geometry_hash


def test_T035_004_TASK031_blocked_propagation() -> None:
    """A structurally valid TASK031 blocked branch cannot compose success."""

    request = _valid_request()
    request["task031_result"] = {
        "status": "BLOCKED",
        "geometry": None,
        "warnings": [],
        "blockers": [{"code": "SSHG_UPSTREAM_BLOCKED"}],
        "deferred_capabilities": [],
        "blocked_result_hash": _hex("f"),
    }
    result = validate_request(request)
    assert result.success_result is None
    assert _codes(result) == ("SSTHC_TASK031_RESULT_BLOCKED",)


def test_T035_005_TASK032_success_contract() -> None:
    """A valid TASK032 flow-state envelope is accepted."""

    result = validate_request(_valid_request())
    assert result.success_result is not None
    assert result.success_result.task032_result_id
    assert result.success_result.property_snapshot_hash == _hex("7")


def test_T035_006_TASK032_blocked_propagation() -> None:
    """A structurally valid TASK032 blocked branch is fail-closed."""

    request = _valid_request()
    request["task032_result"] = {
        "status": "BLOCKED",
        "flow_state": None,
        "blocked_result": _typed_blocked_payload(
            TASK032_TYPED_BLOCKED_RESULT_FIELDS,
            "task032.shell-side-flow-state-blocked.v1",
            "result_hash",
        ),
        "raw_boundary_blocked_result": None,
    }
    result = validate_request(request)
    assert result.success_result is None
    assert _codes(result) == ("SSTHC_TASK032_RESULT_BLOCKED",)


def test_T035_007_TASK033_success_contract() -> None:
    """A valid TASK033 heat-transfer envelope is accepted."""

    result = validate_request(_valid_request())
    assert result.success_result is not None
    assert result.success_result.heat_transfer_surface == "OUTER_TUBE_SURFACE"
    assert result.success_result.task033_correlation_id


def test_T035_008_TASK033_blocked_propagation() -> None:
    """A structurally valid TASK033 blocked branch is fail-closed."""

    request = _valid_request()
    request["task033_result"] = {
        "status": "BLOCKED",
        "heat_transfer": None,
        "blocked_result": _typed_blocked_payload(
            TASK033_TYPED_BLOCKED_RESULT_FIELDS,
            "task033.shell-side-heat-transfer-blocked.v1",
            "blocked_result_hash",
        ),
        "raw_boundary_blocked_result": None,
    }
    result = validate_request(request)
    assert result.success_result is None
    assert _codes(result) == ("SSTHC_TASK033_RESULT_BLOCKED",)


def test_T035_009_TASK034_success_contract() -> None:
    """A valid TASK034 pressure-drop envelope is accepted."""

    result = validate_request(_valid_request())
    assert result.success_result is not None
    assert result.success_result.modeled_shell_side_pressure_drop_pa == "10.000"
    assert result.success_result.task034_correlation_id


def test_T035_010_TASK034_blocked_propagation() -> None:
    """A structurally valid TASK034 blocked branch is fail-closed."""

    request = _valid_request()
    request["task034_result"] = {
        "status": "BLOCKED",
        "pressure_drop": None,
        "blocked_result": _typed_blocked_payload(
            TASK034_TYPED_BLOCKED_RESULT_FIELDS,
            "task034.shell-side-pressure-drop-blocked.v1",
            "blocked_result_hash",
        ),
        "raw_boundary_blocked_result": None,
    }
    result = validate_request(request)
    assert result.success_result is None
    assert _codes(result) == ("SSTHC_TASK034_RESULT_BLOCKED",)


def test_T035_011_TASK034_to_TASK033_identity_replay() -> None:
    """TASK034 replay of TASK033 identity is owned by S10."""

    request = _valid_request()
    request["task034_result"]["pressure_drop"]["task033_result_id"] = "wrong-id"
    _rebuild_task034(request)
    result = validate_request(request)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S10"
    assert _codes(result) == ("SSTHC_TASK034_IDENTITY_MISMATCH",)


def test_T035_012_TASK033_TASK034_to_TASK032_identity_replay() -> None:
    """TASK033 and TASK034 replay of TASK032 are owned at S08 and S10."""

    request = _valid_request()
    request["task033_result"]["heat_transfer"]["task032_result_id"] = "wrong-id"
    _rebuild_task033(request)
    result = validate_request(request)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S08"
    assert _codes(result) == ("SSTHC_TASK033_IDENTITY_MISMATCH",)

    request = _valid_request()
    request["task034_result"]["pressure_drop"]["task032_result_id"] = "wrong-id"
    _rebuild_task034(request)
    result = validate_request(request)
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S10"
    assert _codes(result) == ("SSTHC_TASK034_IDENTITY_MISMATCH",)


def test_T035_013_TASK031_TASK021_TASK024_configuration_ancestry() -> None:
    """Configuration and geometry ancestry joins remain an aggregate stage."""

    request = _valid_request()
    request["task034_result"]["pressure_drop"]["task020_configuration_id"] = "other"
    request["task034_result"]["pressure_drop"]["task020_configuration_hash"] = _hex("0")
    _rebuild_task034(request)
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_CONFIGURATION_MISMATCH",)


def test_T035_014_property_snapshot_and_mass_flow_identity_join() -> None:
    """PropertySnapshot and mass-flow authority identities must join exactly."""

    request = _valid_request()
    request["task034_result"]["pressure_drop"]["property_snapshot_hash"] = _hex("0")
    _rebuild_task034(request)
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_PROPERTY_SNAPSHOT_MISMATCH",)

    request = _valid_request()
    request["task034_result"]["pressure_drop"]["mass_flow_authority_hash"] = _hex("0")
    _rebuild_task034(request)
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_MASS_FLOW_AUTHORITY_MISMATCH",)


def test_T035_015_case_stream_fluid_join() -> None:
    """Case, stream, and fluid identities are cross-producer joins."""

    request = _valid_request()
    request["task034_result"]["pressure_drop"]["shell_side_case_id"] = "other-case"
    _rebuild_task034(request)
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_CASE_IDENTITY_MISMATCH",)


def test_T035_016_producer_profile_compatibility() -> None:
    """Producer profile and first-slice authorities are independently checked."""

    request = _valid_request()
    request["task033_result"]["heat_transfer"]["first_slice_profile_id"] = "wrong-profile"
    _rebuild_task033(request)
    request["task034_result"]["pressure_drop"]["task033_result_hash"] = request["task033_result"][
        "heat_transfer"
    ]["result_hash"]
    request["task034_result"]["pressure_drop"]["task033_result_id"] = request["task033_result"][
        "heat_transfer"
    ]["result_id"]
    _rebuild_task034(request)
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_PROFILE_COMPATIBILITY_MISMATCH",)


def test_T035_017_applicability_intersection() -> None:
    """Producer-specific applicability contexts must intersect without fallback."""

    request = _valid_request()
    context = request["task034_result"]["pressure_drop"]["applicability_context"]
    context[1][1] = "SINGLE_PHASE_GAS"
    _rebuild_task034(request)
    result = validate_request(request)
    assert _codes(result) == ("SSTHC_APPLICABILITY_INCOMPATIBLE",)


def test_T035_018_completeness_success_ledger() -> None:
    """Success records the exact required-producer and profile ledgers."""

    result = validate_request(_valid_request())
    assert result.success_result is not None
    ledger = dict(result.success_result.completeness_ledger)
    assert ledger["classification_universe"] == COMPLETENESS_CLASSIFICATION_UNIVERSE
    assert dict(ledger["required_producers"]) == {
        "TASK031": "DELIVERED_AND_PRESENT",
        "TASK032": "DELIVERED_AND_PRESENT",
        "TASK033": "DELIVERED_AND_PRESENT",
        "TASK034": "DELIVERED_AND_PRESENT",
    }
    assert ledger["applicability_profile_id"] == APPLICABILITY_PROFILE_ID
    assert ledger["completeness_profile_id"] == COMPLETENESS_PROFILE_ID
    assert ledger["deferred_capabilities"] == DEFERRED_CAPABILITIES


def test_T035_019_completeness_blocked_not_applicable_propagation() -> None:
    """A blocked required producer never becomes a partial composition success."""

    request = _valid_request()
    request["task034_result"] = {
        "status": "BLOCKED",
        "pressure_drop": None,
        "blocked_result": _typed_blocked_payload(
            TASK034_TYPED_BLOCKED_RESULT_FIELDS,
            "task034.shell-side-pressure-drop-blocked.v1",
            "blocked_result_hash",
        ),
        "raw_boundary_blocked_result": None,
    }
    result = validate_request(request)
    assert result.status.value == "BLOCKED"
    assert result.success_result is None
    assert result.blocked_result is not None


def test_T035_020_canonical_hash_result_id_graph() -> None:
    """Request/result hashes and UUID result identities replay deterministically."""

    request = _valid_request()
    result = validate_request(request)
    assert result.success_result is not None
    success = result.success_result
    assert success.request_hash == request_hash(request)
    assert success.result_hash == success_result_hash(success)
    assert success.result_id == result_id(success.result_hash)
    assert success.result_hash == success_result_hash(deepcopy(success))


def test_T035_021_provenance_dag_and_no_self_edge() -> None:
    """Provenance has the frozen ordered fields and four directed producer edges."""

    result = validate_request(_valid_request())
    assert result.success_result is not None
    provenance = result.success_result.provenance
    assert tuple(field for field, _value in provenance) == PROVENANCE_FIELDS
    assert verify_provenance(provenance)
    values = dict(provenance)
    edges = values["producer_edges"]
    assert len(edges) == 4
    assert tuple(edge[1][1] for edge in edges) == (
        "TASK035",
        "TASK035",
        "TASK035",
        "TASK035",
    )
    assert all(edge[0][1] != "TASK035" for edge in edges)


def test_T035_022_python311_python312_repeat_run_canonical_byte_identity() -> None:
    """The same request produces identical canonical bytes on every repeat run."""

    request = _valid_request()
    first_request_bytes = canonical_bytes(
        "task035.request.v1", request_canonical_projection(request)
    )
    second_request_bytes = canonical_bytes(
        "task035.request.v1", request_canonical_projection(deepcopy(request))
    )
    assert first_request_bytes == second_request_bytes
    first = validate_request(request).success_result
    second = validate_request(deepcopy(request)).success_result
    assert first is not None and second is not None
    assert canonical_bytes(
        "task035.success-result.v1", success_result_canonical_projection(first)
    ) == canonical_bytes("task035.success-result.v1", success_result_canonical_projection(second))
