"""Frozen Eq. 15-17 operation and input-domain coverage."""

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.formulas import FormulaCalculationError
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.schema import parse_request
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def test_b038_sspd_formula_input_invalid(monkeypatch):
    raw = make_valid_raw_request()
    identity = validation_module.replay_task032_and_upstreams(parse_request(raw))
    identity.flow["shell_side_mass_velocity_kg_m2_s"] = "0"
    monkeypatch.setattr(validation_module, "replay_task032_and_upstreams", lambda _: identity)
    result = validate_request(raw)
    assert "SSPD_FORMULA_INPUT_INVALID" in {item.code for item in result.blockers}


def test_b039_sspd_decimal_ln_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_LN_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_LN_FAILURE" in {item.code for item in result.blockers}


def test_b040_sspd_decimal_exp_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_EXP_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_EXP_FAILURE" in {item.code for item in result.blockers}


def test_b041_sspd_decimal_power_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_POWER_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_POWER_FAILURE" in {item.code for item in result.blockers}


def test_b042_sspd_pressure_drop_calculation_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F14_PRESSURE_DROP")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_PRESSURE_DROP_CALCULATION_FAILURE" in {item.code for item in result.blockers}
