"""Frozen Eq. 15-17 operation and input-domain coverage."""

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.formulas import (
    FormulaCalculationError,
    evaluate_pressure_drop,
)
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
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S13"


def test_b040_sspd_decimal_exp_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_EXP_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_EXP_FAILURE" in {item.code for item in result.blockers}
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S13"


def test_b041_sspd_decimal_power_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_POWER_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_POWER_FAILURE" in {item.code for item in result.blockers}
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S13"


def test_b042_sspd_pressure_drop_calculation_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F14_PRESSURE_DROP")

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_PRESSURE_DROP_CALCULATION_FAILURE" in {item.code for item in result.blockers}
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S14"


def test_real_formula_operation_failure_routes_to_friction_stage():
    try:
        evaluate_pressure_drop(
            Re_s=Decimal("-1"),
            G_s=Decimal("1200"),
            rho_s=Decimal("998"),
            D_s=Decimal("1.2"),
            D_e=Decimal("0.041"),
            N_b=12,
            mu_b=Decimal("0.001"),
            mu_w=Decimal("0.00082"),
        )
    except FormulaCalculationError as failure:
        assert failure.operation == "F13_DECIMAL_LN_FAILURE"
    else:
        raise AssertionError("invalid Reynolds input did not fail in the real formula path")
