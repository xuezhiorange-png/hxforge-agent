"""Frozen Eq. 15-17 operation and input-domain coverage."""

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.decimal_quantization import (
    quantize_public_pressure_drop,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.formulas import (
    FormulaCalculationError,
    evaluate_friction_and_wall_correction,
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

    monkeypatch.setattr(validation_module, "evaluate_friction_and_wall_correction", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_LN_FAILURE" in {item.code for item in result.blockers}
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S13"


def test_b040_sspd_decimal_exp_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_EXP_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_friction_and_wall_correction", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_DECIMAL_EXP_FAILURE" in {item.code for item in result.blockers}
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S13"


def test_b041_sspd_decimal_power_failure(monkeypatch):
    def fail(**_kwargs):
        raise FormulaCalculationError("F13_DECIMAL_POWER_FAILURE")

    monkeypatch.setattr(validation_module, "evaluate_friction_and_wall_correction", fail)
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
        evaluate_friction_and_wall_correction(
            Re_s=Decimal("-1"),
            mu_b=Decimal("0.001"),
            mu_w=Decimal("0.00082"),
        )
    except FormulaCalculationError as failure:
        assert failure.operation == "F13_DECIMAL_LN_FAILURE"
    else:
        raise AssertionError("invalid Reynolds input did not fail in the real formula path")


def test_s14_is_raw_only_and_requires_explicit_s13_and_s15_composition():
    correction = evaluate_friction_and_wall_correction(
        Re_s=Decimal("12000"),
        mu_b=Decimal("0.001"),
        mu_w=Decimal("0.00082"),
    )
    evaluation = evaluate_pressure_drop(
        G_s=Decimal("1250"),
        rho_s=Decimal("998"),
        D_s=Decimal("1.2"),
        D_e=Decimal("0.041"),
        N_b=12,
        f_s=correction.f_s,
        phi_s=correction.phi_s,
        mu_ratio=correction.mu_ratio,
    )
    assert evaluation.public is None
    assert quantize_public_pressure_drop(evaluation.raw) == Decimal("86505.427")


def test_s09_runtime_target_is_verify_wall_property_authority(monkeypatch):
    calls = []
    original = validation_module.verify_wall_property_authority

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "verify_wall_property_authority", spy)
    result = validate_request(make_valid_raw_request())
    assert calls
    assert result.status == "VALID"


def test_s12_runtime_target_is_validate_engineering_inputs(monkeypatch):
    calls = []
    original = validation_module.validate_engineering_inputs

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "validate_engineering_inputs", spy)
    result = validate_request(make_valid_raw_request())
    assert calls
    assert result.status == "VALID"


def test_s13_runtime_target_is_evaluate_friction_and_wall_correction(monkeypatch):
    calls = []
    original = validation_module.evaluate_friction_and_wall_correction

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "evaluate_friction_and_wall_correction", spy)
    result = validate_request(make_valid_raw_request())
    assert calls
    assert result.status == "VALID"


def test_s14_runtime_target_is_evaluate_pressure_drop(monkeypatch):
    calls = []
    original = validation_module.evaluate_pressure_drop

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "evaluate_pressure_drop", spy)
    result = validate_request(make_valid_raw_request())
    assert calls
    assert result.status == "VALID"


def test_s15_runtime_target_is_quantize_public_pressure_drop(monkeypatch):
    calls = []
    original = validation_module.quantize_public_pressure_drop

    def spy(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(validation_module, "quantize_public_pressure_drop", spy)
    result = validate_request(make_valid_raw_request())
    assert calls
    assert result.status == "VALID"
