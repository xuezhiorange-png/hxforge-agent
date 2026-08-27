"""TASK-034 success contract and actual public upstream fixture."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_flow_state import (
    validate_request as validate_task032,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash as task032_mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
    parse_request as parse_task032_request,
)
from hexagent.exchangers.shell_tube.shell_side_heat_transfer import (
    validate_request as validate_task033,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as validate_task031,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.canonical import (
    shell_type_authority_hash,
    wall_property_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.engineering_authority_snapshot import (
    CORRELATION_ID,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    PROFILE_ID,
    REQUEST_SCHEMA_VERSION,
)
from tests.exchangers.shell_tube.shell_side_flow_state import (
    make_valid_raw_request as make_task032_raw,
)
from tests.exchangers.shell_tube.shell_side_hydraulic_geometry.test_validation import (
    _resync_task021_layout_identity,
    _resync_task024_geometry_identity,
    base_fixture_v1,
)


def _public(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _public(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    return value


def _task031_public_result(validation_result: Any) -> dict[str, Any]:
    return {
        "status": validation_result.status.value,
        "geometry": _public(validation_result.geometry),
        "warnings": _public(validation_result.warnings),
        "blockers": _public(validation_result.blockers),
        "deferred_capabilities": list(validation_result.deferred_capabilities),
        "blocked_result_hash": validation_result.blocked_result_hash,
    }


def _task032_request_evidence(raw_request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": raw_request["schema_version"],
        "profile_id": raw_request["profile_id"],
        "task031_result": deepcopy(raw_request["task031_result"]),
        "property_snapshot_hash": raw_request["property_snapshot_hash"],
        "property_snapshot": deepcopy(raw_request["property_snapshot"]),
        "mass_flow_authority": deepcopy(raw_request["mass_flow_authority"]),
        "evidence_refs": deepcopy(raw_request["evidence_refs"]),
    }


def _actual_task031_request() -> dict[str, Any]:
    request = deepcopy(base_fixture_v1())
    # TASK-034's first slice is frozen for triangular pitch.  This remains a
    # caller-owned TASK-031 public request; the producer validates it and the
    # resulting identities are resynchronized through the public contract.
    request["tube_layout"]["layout_rule_authority"]["pattern_family"] = "TRIANGULAR"
    _resync_task021_layout_identity(request)
    _resync_task024_geometry_identity(request)
    return request


def _actual_task032_chain(
    task031_validation: Any,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    task032_request = make_task032_raw()
    task032_request["task031_result"] = _task031_public_result(task031_validation)
    geometry = task032_request["task031_result"]["geometry"]
    authority = task032_request["mass_flow_authority"]
    authority["task020_configuration_id"] = geometry["task020_configuration_id"]
    authority["task020_configuration_hash"] = geometry["task020_configuration_hash"]
    authority["task031_geometry_id"] = geometry["geometry_id"]
    authority["task031_geometry_hash"] = geometry["geometry_hash"]
    authority["authority_hash"] = task032_mass_flow_authority_hash(
        parse_task032_request(task032_request).mass_flow_authority
    )
    validation_result = validate_task032(task032_request)
    assert validation_result.status.value == "VALID"
    assert validation_result.flow_state is not None
    return (
        task032_request,
        _task032_request_evidence(task032_request),
        validation_result,
    )


def _actual_task033_chain(
    task032_request: dict[str, Any], task032_validation: Any
) -> tuple[dict[str, Any], Any]:
    assert task032_validation.flow_state is not None
    task033_request = {
        "schema_version": "task033.shell-side-heat-transfer-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_heat_transfer.v1",
        "task032_flow_state": _public(task032_validation.flow_state),
        "task032_request_evidence": _task032_request_evidence(task032_request),
        "evidence_refs": ["t033-request-z", "t033-request-a"],
    }
    validation_result = validate_task033(task033_request)
    assert validation_result.status.value == "VALID"
    assert validation_result.heat_transfer is not None
    return task033_request, validation_result


def _task034_request_from_chain(
    task031_request: dict[str, Any],
    task031_validation: Any,
    task032_request: dict[str, Any],
    task032_validation: Any,
    task033_request: dict[str, Any],
    task033_validation: Any,
) -> dict[str, Any]:
    assert task031_validation.geometry is not None
    assert task033_validation.heat_transfer is not None

    task031_geometry = _public(task031_validation.geometry)
    task031_request_hash_value = task031_geometry["request_hash"]
    task033_result = _public(task033_validation.heat_transfer)
    task033_upstream = {
        "task033_request_evidence": deepcopy(task033_request),
        "task033_validation_result": {
            "status": task033_validation.status.value,
            "heat_transfer": task033_result,
            "blocked_result": None,
            "raw_boundary_blocked_result": None,
        },
    }

    baffle_geometry = task031_request["baffle_geometry_result"]["geometry"]
    design_authority = baffle_geometry["design_authority"]
    tube_layout = task031_request["tube_layout"]
    layout_rule = tube_layout["layout_rule_authority"]
    tube_geometry = tube_layout["tube_geometry"]
    configuration_id = task031_geometry["task020_configuration_id"]
    configuration_hash = task031_geometry["task020_configuration_hash"]
    shell_authority = {
        "schema_version": "task034.shell-type-authority.v2",
        "shell_type": "E_SHELL",
        "task020_configuration_id": configuration_id,
        "task020_configuration_hash": configuration_hash,
        "authority_source_id": "TASK034-CALLER-SHELL-TYPE",
        "authority_source_version": "v1",
        "authority_record_id": "CASE-034-SHELL-TYPE",
        "evidence_refs": ["task034-shell-type-evidence"],
    }
    shell_authority["authority_hash"] = shell_type_authority_hash(shell_authority)
    flow = _public(task032_validation.flow_state)
    raw: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "task033_upstream_evidence": task033_upstream,
        "task031_request_evidence": deepcopy(task031_request),
        "shell_type_authority": shell_authority,
        "task031_request_hash": task031_request_hash_value,
        "shell_inside_diameter_m": baffle_geometry["shell_inside_diameter_m"],
        "baffle_count": design_authority["baffle_count"],
        "uniform_spacing_sequence_m": design_authority["spacing_sequence_m"],
        "tube_pitch_m": layout_rule["pitch_m"],
        "tube_outer_diameter_m": tube_geometry["outer_diameter_m"],
        "pattern_family": layout_rule["pattern_family"],
        "shell_side_wall_dynamic_viscosity_pa_s": "0.00082",
        "wall_property_schema_version": "task034.wall-property.v2",
        "wall_property_source_id": "fixture-wall",
        "wall_property_source_version": "v1",
        "wall_property_evidence_refs": ["wall-fixture"],
        "wall_property_snapshot_hash": "wall-snapshot",
        "wall_property_authority_hash": "",
        "correlation_id": CORRELATION_ID,
        "shell_side_case_id": flow["shell_side_case_id"],
        "shell_side_stream_id": flow["shell_side_stream_id"],
        "shell_side_fluid_id": flow["shell_side_fluid_id"],
        "task020_configuration_id": flow["task020_configuration_id"],
        "task020_configuration_hash": flow["task020_configuration_hash"],
        "task031_geometry_id": task031_geometry["geometry_id"],
        "task031_geometry_hash": task031_geometry["geometry_hash"],
        "task032_request_hash": flow["request_hash"],
        "task032_result_id": flow["result_id"],
        "task032_result_hash": flow["result_hash"],
        "task033_request_hash": task033_result["request_hash"],
        "task033_result_id": task033_result["result_id"],
        "task033_result_hash": task033_result["result_hash"],
        "property_snapshot_hash": flow["property_snapshot_hash"],
        "mass_flow_authority_hash": flow["mass_flow_authority_hash"],
        "evidence_refs": ["task034-fixture"],
    }
    raw["wall_property_authority_hash"] = wall_property_authority_hash(raw)
    assert "provenance_pre_hash" not in raw["task031_request_evidence"]["tube_layout"]
    assert (
        _task032_request_evidence(task032_request)["task031_result"]["geometry"] == task031_geometry
    )
    return raw


def build_actual_public_chain() -> dict[str, Any]:
    """Execute the public upstream boundaries and assemble one TASK034 request."""
    task031_request = _actual_task031_request()
    task031_validation = validate_task031(task031_request)
    assert task031_validation.status.value == "VALID"
    assert task031_validation.geometry is not None
    task032_request, _, task032_validation = _actual_task032_chain(task031_validation)
    task033_request, task033_validation = _actual_task033_chain(task032_request, task032_validation)
    task034_request = _task034_request_from_chain(
        task031_request,
        task031_validation,
        task032_request,
        task032_validation,
        task033_request,
        task033_validation,
    )
    return {
        "task031_request": task031_request,
        "task031_validation": task031_validation,
        "task032_request": task032_request,
        "task032_validation": task032_validation,
        "task033_request": task033_request,
        "task033_validation": task033_validation,
        "task034_request": task034_request,
    }


def make_valid_raw_request() -> dict[str, Any]:
    """Build TASK034 input from actual TASK031, TASK032, and TASK033 execution."""
    return deepcopy(build_actual_public_chain()["task034_request"])


def copy_request() -> dict[str, Any]:
    return deepcopy(make_valid_raw_request())


def test_x001_success_nominal_liquid() -> None:
    result = validate_request(make_valid_raw_request())
    assert result.status.value == "VALID"
    assert result.pressure_drop is not None
    assert result.pressure_drop.modeled_shell_side_pressure_drop_pa > 0


def test_x006_physical_boundary_no_double_count() -> None:
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None
    assert dict(result.physical_boundary_context)["total_shell_side_pressure_drop"] is False


def test_x007_success_hash_self_exclusion() -> None:
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None and result.result_hash and result.result_id


def test_x010_c5_schema_contract() -> None:
    result = validate_request(make_valid_raw_request()).pressure_drop
    assert result is not None
    assert len(fields(result)) == 45
