"""V08-01 general user design case validation and solver handoff tests."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2
from prototypes.v08_general_user_case import (
    V08UserCaseValidationError,
    V08ValidationCode,
    load_general_user_design_case_json,
    validate_and_build_solver_handoff,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_V07_330KW = _FIXTURES / "v07_live_acceptance_user_case.json"
_V08_EXAMPLE = _FIXTURES / "v08_user_case_no_geometry.json"


def _load_v08(path: Path = _V08_EXAMPLE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _handoff_for(payload: dict):
    case = load_general_user_design_case_json(json.dumps(payload))
    return validate_and_build_solver_handoff(case, CoolPropProvider())


def test_v08_schema_accepts_case_without_equipment_geometry() -> None:
    result = _handoff_for(_load_v08())
    assert "candidate_constraints" not in result.normalized.input_snapshot_dict()
    assert result.handoff.geometry_required_for_full_design is True
    assert result.handoff.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    assert result.handoff.thermal_binding is not None
    assert result.handoff.consumable_parameters["target_duty_w"] == "250000"


def test_v08_unit_conversion_kw_kpa_degC() -> None:
    payload = _load_v08()
    payload["target_heat_duty"] = {"value": 0.25, "unit": "MW"}
    payload["max_tube_side_pressure_drop"] = {"value": 40000, "unit": "Pa"}
    result = _handoff_for(payload)
    assert result.normalized.target_duty_w == Decimal("250000")
    assert result.normalized.max_tube_side_pressure_drop_pa == Decimal("40000")


def _mutate_target_duty(p: dict) -> None:
    p.pop("target_heat_duty", None)
    p["target_duty_w"] = "200000"


@pytest.mark.parametrize(
    ("field", "mutator"),
    [
        ("target_duty_w", _mutate_target_duty),
        (
            "tube_mass_flow",
            lambda p: p["tube_side"].update({"mass_flow": {"value": 16.0, "unit": "kg/s"}}),
        ),
        (
            "shell_mass_flow",
            lambda p: p["shell_side"].update({"mass_flow": {"value": 22.0, "unit": "kg/s"}}),
        ),
        (
            "tube_temperature",
            lambda p: p["tube_side"].update({"inlet_temperature": {"value": 42, "unit": "degC"}}),
        ),
        (
            "tube_dp",
            lambda p: p.update({"max_tube_side_pressure_drop": {"value": 55, "unit": "kPa"}}),
        ),
    ],
)
def test_v08_metamorphic_consumed_parameters_change(field: str, mutator) -> None:
    base = _handoff_for(_load_v08())
    base_bundle = {
        **base.handoff.consumable_parameters,
        **base.handoff.pressure_limits_pa,
    }
    alt_payload = copy.deepcopy(_load_v08())
    mutator(alt_payload)
    alt = _handoff_for(alt_payload)
    alt_bundle = {**alt.handoff.consumable_parameters, **alt.handoff.pressure_limits_pa}
    assert alt_bundle != base_bundle, f"expected solver inputs to change when varying {field}"


def test_v08_rejects_thermodynamically_impossible_duty() -> None:
    payload = _load_v08()
    payload["target_heat_duty"] = {"value": 5, "unit": "MW"}
    with pytest.raises(V08UserCaseValidationError) as exc:
        _handoff_for(payload)
    codes = {issue.code for issue in exc.value.issues}
    assert V08ValidationCode.THERMODYNAMICALLY_INFEASIBLE in codes


def test_v08_rejects_invalid_hot_cold_order() -> None:
    payload = _load_v08()
    payload["tube_side"]["inlet_temperature"] = {"value": 30, "unit": "degC"}
    payload["shell_side"]["inlet_temperature"] = {"value": 40, "unit": "degC"}
    with pytest.raises((V08UserCaseValidationError, ValidationError)):
        _handoff_for(payload)


def test_v08_rejects_out_of_envelope_temperature() -> None:
    payload = _load_v08()
    payload["tube_side"]["inlet_temperature_k"] = "250"
    payload["tube_side"].pop("inlet_temperature", None)
    with pytest.raises((V08UserCaseValidationError, ValidationError)):
        _handoff_for(payload)


def test_v08_330kw_equivalent_handoff_matches_live_acceptance_case() -> None:
    v07_case: GeneralEngineeringCaseV2 = load_general_engineering_case_json(  # type: ignore[assignment]
        _V07_330KW.read_text(encoding="utf-8")
    )
    assert isinstance(v07_case, GeneralEngineeringCaseV2)
    v08_payload = {
        "schema_version": "hxforge.general-user-design-case.v1",
        "engineering_case_id": "v08-330kw-regression-user-case",
        "exchanger_type": v07_case.exchanger_type,
        "tube_side": v07_case.tube_side.model_dump(mode="json"),
        "shell_side": v07_case.shell_side.model_dump(mode="json"),
        "target_duty_w": str(v07_case.target_duty_w),
        "max_tube_side_pressure_drop_pa": str(v07_case.max_tube_side_pressure_drop_pa),
        "max_shell_side_pressure_drop_pa": str(v07_case.max_shell_side_pressure_drop_pa),
        "notes": "Mapped from frozen V07 live acceptance case without geometry fields.",
    }
    result = _handoff_for(v08_payload)
    consumable = result.handoff.consumable_parameters
    assert Decimal(consumable["target_duty_w"]) == Decimal("330000")
    assert Decimal(consumable["tube_mass_flow_kg_s"]) == Decimal("12")
    assert Decimal(consumable["shell_mass_flow_kg_s"]) == Decimal("20")
    assert Decimal(consumable["tube_inlet_temperature_k"]) == Decimal("310")
    assert Decimal(consumable["shell_inlet_temperature_k"]) == Decimal("295")
    assert result.handoff.pressure_limits_pa["max_tube_side_pressure_drop_pa"] == "1150"
    assert result.handoff.normalized_input_hash
    assert result.handoff.property_provider_identity["provider_class"] == "CoolPropProvider"


def test_hxforge_330kw_strict_dp_fixture_identity() -> None:
    path = _FIXTURES / "v08_user_case_hxforge_330kw_strict_dp.json"
    result = _handoff_for(json.loads(path.read_text(encoding="utf-8")))
    assert result.normalized.engineering_case_id == "HXFORGE_330KW_STRICT_DP"
    assert result.normalized.target_duty_w == Decimal("330000")
    assert result.normalized.tube_side.inlet_temperature_k == Decimal("310")
    assert result.normalized.shell_side.inlet_temperature_k == Decimal("295")
    assert result.handoff.pressure_limits_pa["max_tube_side_pressure_drop_pa"] == "1150"
    assert result.handoff.consumable_parameters["target_duty_w"] == "330000"


def test_v07_330kw_fixture_still_loads_with_geometry_constraints() -> None:
    """Regression guard: V07 acceptance JSON and applicability rules remain unchanged."""
    case = load_general_engineering_case_json(_V07_330KW.read_text(encoding="utf-8"))
    status, detail = case.applicability_status()
    assert status == "IN_SCOPE", detail
    assert case.target_duty_w == Decimal("330000")


_DESIGN_ENVELOPE_FIELDS = (
    "max_shell_inside_diameter_m",
    "min_shell_inside_diameter_m",
    "max_tube_length_m",
    "min_tube_length_m",
    "max_overall_length_m",
)


def _payload_with_design_envelope(**fields: object) -> dict:
    payload = _load_v08()
    payload["design_envelope"] = {"provenance_note": "validation test", **fields}
    return payload


@pytest.mark.parametrize("field", _DESIGN_ENVELOPE_FIELDS)
def test_v08_design_envelope_rejects_negative_dimension(field: str) -> None:
    payload = _payload_with_design_envelope(**{field: "-0.5"})
    with pytest.raises((ValidationError, V08UserCaseValidationError)):
        _handoff_for(payload)


@pytest.mark.parametrize("field", _DESIGN_ENVELOPE_FIELDS)
def test_v08_design_envelope_rejects_zero_dimension(field: str) -> None:
    payload = _payload_with_design_envelope(**{field: "0"})
    with pytest.raises((ValidationError, V08UserCaseValidationError)):
        _handoff_for(payload)


@pytest.mark.parametrize(
    ("field", "raw_value"),
    [
        (field, bad)
        for field in _DESIGN_ENVELOPE_FIELDS
        for bad in ("NaN", "Infinity", "-Infinity", "nan", "inf")
    ],
)
def test_v08_design_envelope_rejects_non_finite_literals(field: str, raw_value: str) -> None:
    payload = _payload_with_design_envelope(**{field: raw_value})
    with pytest.raises((ValidationError, V08UserCaseValidationError)):
        _handoff_for(payload)


def test_v08_design_envelope_rejects_min_shell_exceeds_max_shell() -> None:
    payload = _payload_with_design_envelope(
        min_shell_inside_diameter_m="1.0",
        max_shell_inside_diameter_m="0.8",
    )
    with pytest.raises((ValidationError, V08UserCaseValidationError)) as exc:
        _handoff_for(payload)
    err = exc.value
    if isinstance(err, V08UserCaseValidationError):
        assert any("min_shell" in issue.message for issue in err.issues)
    else:
        assert "min_shell_inside_diameter_m" in str(err)


def test_v08_design_envelope_rejects_min_tube_length_exceeds_max() -> None:
    payload = _payload_with_design_envelope(
        min_tube_length_m="6.0",
        max_tube_length_m="4.0",
    )
    with pytest.raises((ValidationError, V08UserCaseValidationError)):
        _handoff_for(payload)


def test_v08_design_envelope_accepts_equal_min_max_bounds() -> None:
    payload = _payload_with_design_envelope(
        min_shell_inside_diameter_m="0.9",
        max_shell_inside_diameter_m="0.9",
        min_tube_length_m="5.0",
        max_tube_length_m="5.0",
    )
    result = _handoff_for(payload)
    assert result.normalized.design_envelope is not None
    assert result.handoff.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"


def test_v08_design_envelope_all_none_omitted_passes() -> None:
    payload = _load_v08()
    payload.pop("design_envelope", None)
    result = _handoff_for(payload)
    assert result.normalized.design_envelope is None


def test_v08_design_envelope_accepts_valid_positive_bounds() -> None:
    payload = _payload_with_design_envelope(
        min_shell_inside_diameter_m="0.4",
        max_shell_inside_diameter_m="1.2",
        min_tube_length_m="3.0",
        max_tube_length_m="6.5",
        max_overall_length_m="7.0",
    )
    result = _handoff_for(payload)
    env = result.normalized.design_envelope
    assert env is not None
    assert env.max_overall_length_m == Decimal("7.0")


def test_v08_design_envelope_invalid_value_never_reaches_solver_handoff() -> None:
    payload = _payload_with_design_envelope(max_tube_length_m="-1")
    with pytest.raises((ValidationError, V08UserCaseValidationError)):
        validate_and_build_solver_handoff(
            load_general_user_design_case_json(json.dumps(payload)),
            CoolPropProvider(),
        )


def test_v08_design_envelope_rejects_non_numeric_string() -> None:
    payload = _payload_with_design_envelope(max_shell_inside_diameter_m="not-a-number")
    with pytest.raises(ValidationError):
        load_general_user_design_case_json(json.dumps(payload))
