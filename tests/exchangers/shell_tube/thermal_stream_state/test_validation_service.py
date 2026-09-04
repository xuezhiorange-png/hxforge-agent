"""End-to-end TASK160 validation and fail-closed branch tests."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.thermal_stream_state.errors import BlockerCode
from hexagent.exchangers.shell_tube.thermal_stream_state.models import (
    FailureStage,
    ValidationStatus,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.service import (
    compute_heat_capacity_rate,
    validate_request,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.validation import resolve_thermal_roles

from .test_ingress_models import make_r607_raw


def _codes(raw: dict[str, object]) -> tuple[str, ...]:
    return tuple(item.code for item in validate_request(raw).blockers)


def _stream_copy(raw: dict[str, object], index: int = 0) -> dict[str, object]:
    return deepcopy(raw["stream_records"])[index]  # type: ignore[index,return-value]


def _replace_stream(raw: dict[str, object], index: int, **changes: object) -> dict[str, object]:
    streams = deepcopy(raw["stream_records"])  # type: ignore[arg-type]
    stream = dict(streams[index])
    stream.update(changes)
    streams[index] = stream
    raw["stream_records"] = streams
    return raw


def test_explicit_two_stream_request_is_valid_and_computes_only_cdot() -> None:
    result = validate_request(make_r607_raw())
    assert result.status is ValidationStatus.VALID
    assert result.valid is not None
    assert result.valid.c_dot_hot_W_K == Decimal("10450.0")
    assert result.valid.c_dot_cold_W_K == Decimal("4375.00")
    assert {item.thermal_role.value for item in result.valid.stream_records} == {"HOT", "COLD"}
    assert result.valid.blockers == ()


def test_roles_follow_inlet_temperature_not_side_or_sequence_position() -> None:
    raw = make_r607_raw()
    raw["stream_records"] = list(reversed(raw["stream_records"]))  # type: ignore[arg-type]
    result = validate_request(raw)
    assert result.valid is not None
    by_id = {item.stream_id: item.thermal_role.value for item in result.valid.stream_records}
    assert by_id == {"stream-tube-A": "HOT", "stream-shell-B": "COLD"}


def test_equal_inlet_temperatures_return_typed_blocked_result() -> None:
    raw = make_r607_raw()
    _replace_stream(raw, 1, inlet_temperature_K="390.15")
    result = validate_request(raw)
    assert result.status is ValidationStatus.TYPED_BLOCKED
    assert result.typed_blocked is not None
    assert result.typed_blocked.failure_stage is FailureStage.STRICT_VALIDATION
    assert BlockerCode.B010.value in _codes(raw)
    assert result.typed_blocked.provenance.graph is not None


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("stream_id", "B005"),
        ("fluid_or_service_identity", "B006"),
        ("phase_assertion", "B007"),
        ("mass_flow_kg_s", "B011"),
    ],
)
def test_raw_missing_stream_authority_returns_raw_blocked(field: str, code: str) -> None:
    raw = make_r607_raw()
    _replace_stream(raw, 0, **{field: None})
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert code in _codes(raw)
    assert result.raw_boundary_blocked is not None


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("property_snapshot", "B015"),
        ("property_source_identity", "B013"),
        ("property_source_version", "B014"),
        ("property_snapshot_identity", "B015"),
        ("property_evaluation_context", "B016"),
    ],
)
def test_raw_missing_property_authority_returns_raw_blocked(field: str, code: str) -> None:
    raw = make_r607_raw()
    if field == "property_snapshot":
        _replace_stream(raw, 0, property_snapshot=None)
    else:
        snapshot = _stream_copy(raw)["property_snapshot"]
        snapshot = dict(snapshot)  # type: ignore[arg-type]
        snapshot[field] = None
        _replace_stream(raw, 0, property_snapshot=snapshot)
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert code in _codes(raw)


def test_raw_missing_provenance_returns_raw_blocked() -> None:
    raw = make_r607_raw()
    _replace_stream(raw, 0, provenance=None)
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.B018.value in _codes(raw)


def test_invalid_stream_count_is_raw_blocked() -> None:
    raw = make_r607_raw()
    raw["stream_records"] = [raw["stream_records"][0]]  # type: ignore[index]
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.B001.value in _codes(raw)


@pytest.mark.parametrize("side", ["TUBE_SIDE", "SHELL_SIDE"])
def test_duplicate_side_binding_is_raw_blocked(side: str) -> None:
    raw = make_r607_raw()
    _replace_stream(raw, 1 if side == "TUBE_SIDE" else 0, side_binding=side)
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert (BlockerCode.B002.value if side == "TUBE_SIDE" else BlockerCode.B003.value) in _codes(
        raw
    )


def test_missing_envelope_is_raw_blocked() -> None:
    raw = make_r607_raw(envelope_authority=None)
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.B021.value in _codes(raw)


def test_required_inlet_pressure_is_raw_blocked() -> None:
    raw = make_r607_raw()
    _replace_stream(raw, 1, inlet_pressure_Pa_absolute=None)
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.B017.value in _codes(raw)


def test_invalid_adapter_vocabulary_is_raw_blocked() -> None:
    raw = make_r607_raw()
    adapters = deepcopy(raw["adapter_evidence"])  # type: ignore[arg-type]
    adapters[0] = dict(adapters[0])
    adapters[0]["admitted_fields"] = ["mass_flow_kg_s"]
    raw["adapter_evidence"] = adapters
    result = validate_request(raw)
    assert result.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.B019.value in _codes(raw)


def test_raw_boundary_projection_and_blocked_identity_are_present() -> None:
    result = validate_request(make_r607_raw(stream_records=None))
    assert result.raw_boundary_blocked is not None
    blocked = result.raw_boundary_blocked
    assert blocked.raw_request_projection_hash
    assert len(blocked.blocked_result_hash) == 64
    assert blocked.blocked_result_id.version == 5


def test_cdot_service_uses_decimal_without_downstream_metrics() -> None:
    assert compute_heat_capacity_rate(Decimal("2.5"), Decimal("4180")) == Decimal("10450")
    assert compute_heat_capacity_rate(Decimal("1.25"), Decimal("3500")) == Decimal("4375.00")


def test_role_resolver_rejects_unvalidated_or_wrong_stage_objects() -> None:
    with pytest.raises(ValueError):
        resolve_thermal_roles(object(), object())  # type: ignore[arg-type]
