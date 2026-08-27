"""Real public TASK-031 -> TASK-032 -> TASK-033 -> TASK-034 regression."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as validate_task031,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import (
    validate_request as validate_task034,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    _actual_task031_request,
    _actual_task032_chain,
    _actual_task033_chain,
    _task034_request_from_chain,
)


def test_task031_to_task034_public_producer_replay() -> None:
    task031_raw_request = _actual_task031_request()
    original_task031_raw_request = deepcopy(task031_raw_request)

    task031_validation = validate_task031(task031_raw_request)
    assert task031_validation.status.value == "VALID"
    assert task031_validation.geometry is not None
    actual_task031_request_hash = task031_validation.geometry.request_hash
    actual_task031_geometry_id = task031_validation.geometry.geometry_id
    actual_task031_geometry_hash = task031_validation.geometry.geometry_hash

    task032_raw_request, _, task032_validation = _actual_task032_chain(task031_validation)
    assert task032_validation.status.value == "VALID"
    assert task032_validation.flow_state is not None
    actual_task032_request_hash = task032_validation.flow_state.request_hash
    actual_task032_result_hash = task032_validation.flow_state.result_hash
    actual_task032_result_id = task032_validation.flow_state.result_id

    task033_raw_request, task033_validation = _actual_task033_chain(
        task032_raw_request, task032_validation
    )
    assert task033_validation.status.value == "VALID"
    assert task033_validation.heat_transfer is not None
    actual_task033_request_hash = task033_validation.heat_transfer.request_hash
    actual_task033_result_hash = task033_validation.heat_transfer.result_hash
    actual_task033_result_id = task033_validation.heat_transfer.result_id

    task034_raw_request = _task034_request_from_chain(
        original_task031_raw_request,
        task031_validation,
        task032_raw_request,
        task032_validation,
        task033_raw_request,
        task033_validation,
    )
    assert task031_raw_request == original_task031_raw_request
    assert "provenance_pre_hash" not in original_task031_raw_request["tube_layout"]

    task031_geometry = task031_validation.geometry
    assert "shell_inside_diameter_m" not in task031_geometry.__dict__
    expected_shell_inside_diameter = original_task031_raw_request["baffle_geometry_result"][
        "geometry"
    ]["shell_inside_diameter_m"]
    assert Decimal(task034_raw_request["shell_inside_diameter_m"]) == Decimal(
        expected_shell_inside_diameter
    )
    assert task034_raw_request["task031_request_hash"] == actual_task031_request_hash
    assert task034_raw_request["task031_geometry_id"] == actual_task031_geometry_id
    assert task034_raw_request["task031_geometry_hash"] == actual_task031_geometry_hash
    assert task034_raw_request["task032_request_hash"] == actual_task032_request_hash
    assert task034_raw_request["task032_result_hash"] == actual_task032_result_hash
    assert task034_raw_request["task032_result_id"] == actual_task032_result_id
    assert task034_raw_request["task033_request_hash"] == actual_task033_request_hash
    assert task034_raw_request["task033_result_hash"] == actual_task033_result_hash
    assert task034_raw_request["task033_result_id"] == actual_task033_result_id

    task034_validation = validate_task034(task034_raw_request)
    assert task034_validation.status.value == "VALID"
    assert task034_validation.pressure_drop is not None
    task034_result = task034_validation.pressure_drop
    assert task034_result.task031_request_hash == actual_task031_request_hash
    assert task034_result.task033_request_hash == actual_task033_request_hash
    assert task034_result.task033_result_hash == actual_task033_result_hash
    assert task034_result.task033_result_id == actual_task033_result_id
    assert task034_result.modeled_shell_side_pressure_drop_pa > 0
