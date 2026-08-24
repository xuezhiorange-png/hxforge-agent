"""TASK033 fixture builders and model contract checks."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_flow_state import (
    validate_request as validate_task032,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
    primitive,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import (
    parse_request as parse_task032_request,
)
from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from hexagent.exchangers.shell_tube.shell_side_heat_transfer.canonical import (
    mass_flow_authority_hash as task033_mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_heat_transfer.canonical import (
    task032_request_hash,
    task032_result_id,
    task032_success_hash,
    task033_request_hash,
)
from hexagent.exchangers.shell_tube.shell_side_heat_transfer.models import (
    FLOW_STATE_EVIDENCE_FIELDS,
    REQUEST_EVIDENCE_FIELDS,
    REQUEST_FIELDS,
    SUCCESS_RESULT_FIELDS,
    TYPED_BLOCKED_RESULT_FIELDS,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import PhaseRegion, PropertySnapshot
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    recompute_property_snapshot_hash,
)
from tests.exchangers.shell_tube.shell_side_flow_state import (
    make_valid_raw_request as make_task032_raw,
)
from tests.exchangers.shell_tube.shell_side_flow_state import (
    with_mass_flow,
)


def _rebind_phase(raw: dict[str, Any], phase: str) -> None:
    snapshot = raw["property_snapshot"]
    typed = PropertySnapshot(
        density_kg_m3=Decimal(snapshot["density_kg_m3"]),
        dynamic_viscosity_pa_s=Decimal(snapshot["dynamic_viscosity_pa_s"]),
        thermal_conductivity_w_m_k=Decimal(snapshot["thermal_conductivity_w_m_k"]),
        specific_heat_capacity_j_kg_k=Decimal(snapshot["specific_heat_capacity_j_kg_k"]),
        bulk_temperature_k=Decimal(snapshot["bulk_temperature_k"]),
        bulk_pressure_pa=Decimal(snapshot["bulk_pressure_pa"]),
        phase_region=PhaseRegion(phase),
        property_source_id=snapshot["property_source_id"],
        property_source_version=snapshot["property_source_version"],
        property_snapshot_hash="0" * 64,
    )
    snapshot_hash = recompute_property_snapshot_hash(typed)
    snapshot["phase_region"] = phase
    snapshot["property_snapshot_hash"] = snapshot_hash
    raw["property_snapshot_hash"] = snapshot_hash
    raw["mass_flow_authority"]["property_snapshot_hash"] = snapshot_hash
    parsed = parse_task032_request(raw)
    raw["mass_flow_authority"]["authority_hash"] = mass_flow_authority_hash(
        parsed.mass_flow_authority
    )


def make_valid_raw_request(
    *, mass_flow: str = "60.0000000", phase: str = "SINGLE_PHASE_LIQUID"
) -> dict[str, Any]:
    task032_raw = with_mass_flow(make_task032_raw(), mass_flow)
    if phase != "SINGLE_PHASE_LIQUID":
        _rebind_phase(task032_raw, phase)
    upstream = validate_task032(task032_raw)
    assert upstream.flow_state is not None
    flow_state = primitive(asdict(upstream.flow_state))
    return {
        "schema_version": "task033.shell-side-heat-transfer-request.v1",
        "profile_id": "hxforge.shell_tube.shell_side_heat_transfer.v1",
        "task032_flow_state": flow_state,
        "task032_request_evidence": {
            "schema_version": task032_raw["schema_version"],
            "profile_id": task032_raw["profile_id"],
            "task031_result": deepcopy(task032_raw["task031_result"]),
            "property_snapshot_hash": task032_raw["property_snapshot_hash"],
            "property_snapshot": deepcopy(task032_raw["property_snapshot"]),
            "mass_flow_authority": deepcopy(task032_raw["mass_flow_authority"]),
            "evidence_refs": deepcopy(task032_raw["evidence_refs"]),
        },
        "evidence_refs": ["t033-request-z", "t033-request-a"],
    }


def copy_request(**kwargs: str) -> dict[str, Any]:
    return deepcopy(make_valid_raw_request(**kwargs))


def valid_result(**kwargs: str) -> Any:
    return validate_request(make_valid_raw_request(**kwargs))


def refresh_task032_identity(
    raw: dict[str, Any], *, refresh_mass_authority: bool = False
) -> dict[str, Any]:
    """Rebind only the accepted TASK032 identity after a test mutation."""
    parsed = __import__(
        "hexagent.exchangers.shell_tube.shell_side_heat_transfer.schema",
        fromlist=["parse_request"],
    ).parse_request(raw)
    if refresh_mass_authority:
        authority_hash = task033_mass_flow_authority_hash(
            parsed.task032_request_evidence.mass_flow_authority
        )
        raw["task032_request_evidence"]["mass_flow_authority"]["authority_hash"] = authority_hash
        raw["task032_flow_state"]["mass_flow_authority_hash"] = authority_hash
        parsed = __import__(
            "hexagent.exchangers.shell_tube.shell_side_heat_transfer.schema",
            fromlist=["parse_request"],
        ).parse_request(raw)
    request_hash_value = task032_request_hash(parsed.task032_request_evidence)
    raw["task032_flow_state"]["request_hash"] = request_hash_value
    parsed = __import__(
        "hexagent.exchangers.shell_tube.shell_side_heat_transfer.schema",
        fromlist=["parse_request"],
    ).parse_request(raw)
    result_hash_value = task032_success_hash(parsed.task032_flow_state)
    raw["task032_flow_state"]["result_hash"] = result_hash_value
    raw["task032_flow_state"]["result_id"] = task032_result_id(result_hash_value)
    return raw


def refresh_geometry_identity(raw: dict[str, Any]) -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.shell_side_heat_transfer.canonical import (
        task031_geometry_hash,
        task031_geometry_id,
    )

    geometry = raw["task032_request_evidence"]["task031_result"]["geometry"]
    geometry_hash = task031_geometry_hash(geometry)
    geometry_id = task031_geometry_id(geometry_hash)
    geometry["geometry_hash"] = geometry_hash
    geometry["geometry_id"] = geometry_id
    raw["task032_request_evidence"]["mass_flow_authority"]["task031_geometry_hash"] = geometry_hash
    raw["task032_request_evidence"]["mass_flow_authority"]["task031_geometry_id"] = geometry_id
    raw["task032_flow_state"]["task031_geometry_hash"] = geometry_hash
    raw["task032_flow_state"]["task031_geometry_id"] = geometry_id
    return refresh_task032_identity(raw, refresh_mass_authority=True)


def test_models_frozen_field_orders() -> None:
    assert len(REQUEST_FIELDS) == 5
    assert len(FLOW_STATE_EVIDENCE_FIELDS) == 29
    assert len(REQUEST_EVIDENCE_FIELDS) == 7
    assert len(SUCCESS_RESULT_FIELDS) == 28
    assert len(TYPED_BLOCKED_RESULT_FIELDS) == 22
    result = valid_result()
    assert result.heat_transfer is not None
    assert (
        task033_request_hash(
            __import__(
                "hexagent.exchangers.shell_tube.shell_side_heat_transfer.schema",
                fromlist=["parse_request"],
            ).parse_request(make_valid_raw_request())
        )
        == result.heat_transfer.request_hash
    )
