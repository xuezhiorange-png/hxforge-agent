"""Deterministic numerical-method evidence runner for TASK172 R92.

This test-only runner does not import the production exchanger solver, write
files, use randomness, perform network access, or authorize an engineering
result. Synthetic values are numerical fixtures only. The sole physical
property callback is reviewed-scope HEOS ordinary-water dynamic viscosity.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import CoolProp
import numpy as np
import scipy
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq, least_squares

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256

T_MIN_K = 298.15
T_MAX_K = 300.0
P_MIN_PA = 100000.0
P_MAX_PA = 101325.0
LOCAL_FIXTURE_PRESSURE_PA = 101325.0
JMU_EXPONENT = 0.14
FLOAT_EPSILON = float(np.finfo(float).eps)
SELECTED_PROFILE = {
    "method": "trf",
    "loss": "linear",
    "ftol": 1e-6,
    "xtol": 1e-12,
    "gtol": 1e-12,
    "jacobian": "2-point",
    "diff_step": 1e-5,
    "x_scale": "INITIALIZATION_DERIVED",
    "max_nfev": 6,
    "tr_solver": "exact",
    "tr_options": {},
    "f_scale": 1.0,
    "jac_sparsity": None,
}


class NumericalFailure(Exception):
    """A typed non-authoritative numerical experiment outcome."""

    def __init__(self, failure_class: str, detail: str) -> None:
        super().__init__(detail)
        self.failure_class = failure_class
        self.detail = detail


@dataclass(frozen=True)
class Fixture:
    case_id: str
    fixture_class: str
    tube_bulk_K: float
    shell_bulk_K: float
    s_ts: int
    area_i_m2: float
    area_o_m2: float
    h_i_W_m2K: float
    h_o_base_W_m2K: float
    wall_resistance_K_W: float
    nonlinear_jmu: bool = False
    pressure_Pa: float = LOCAL_FIXTURE_PRESSURE_PA

    @property
    def delta_t_K(self) -> float:
        return self.tube_bulk_K - self.shell_bulk_K

    @property
    def g_i_W_K(self) -> float:
        return self.h_i_W_m2K * self.area_i_m2

    @property
    def g_o_base_W_K(self) -> float:
        return self.h_o_base_W_m2K * self.area_o_m2


def analytic_fixtures() -> list[Fixture]:
    areas = {"area_i_m2": 0.05, "area_o_m2": 0.05}
    return [
        Fixture(
            "A01_TUBE_HOT_BALANCED", "TUBE_HOT", 299.6, 298.4, 1, 0.05, 0.05, 2000.0, 2000.0, 0.01
        ),
        Fixture(
            "A02_SHELL_HOT_BALANCED",
            "SHELL_HOT",
            298.4,
            299.6,
            -1,
            0.05,
            0.05,
            2000.0,
            2000.0,
            0.01,
        ),
        Fixture(
            "A03_NEGATIVE_Q_ASSIGNED_ROLE",
            "NEGATIVE_Q",
            298.4,
            299.6,
            1,
            0.05,
            0.05,
            2000.0,
            2000.0,
            0.01,
        ),
        Fixture(
            "A04_ZERO_DUTY_EXACT", "ZERO_DUTY", 299.0, 299.0, 1, 0.05, 0.05, 2000.0, 2000.0, 0.01
        ),
        Fixture(
            "A05_NEAR_ZERO_DRIVING_FORCE",
            "NEAR_ZERO",
            299.00001,
            299.0,
            1,
            0.05,
            0.05,
            2000.0,
            2000.0,
            0.01,
        ),
        Fixture(
            "A06_TUBE_FILM_DOMINATED",
            "TUBE_FILM_DOMINATED",
            299.6,
            298.4,
            1,
            areas["area_i_m2"],
            areas["area_o_m2"],
            1.0 / (0.09 * areas["area_i_m2"]),
            1.0 / (0.005 * areas["area_o_m2"]),
            0.005,
        ),
        Fixture(
            "A07_WALL_DOMINATED",
            "WALL_DOMINATED",
            299.6,
            298.4,
            1,
            areas["area_i_m2"],
            areas["area_o_m2"],
            1.0 / (0.005 * areas["area_i_m2"]),
            1.0 / (0.005 * areas["area_o_m2"]),
            0.09,
        ),
        Fixture(
            "A08_SHELL_FILM_DOMINATED",
            "SHELL_FILM_DOMINATED",
            299.6,
            298.4,
            1,
            areas["area_i_m2"],
            areas["area_o_m2"],
            1.0 / (0.005 * areas["area_i_m2"]),
            1.0 / (0.09 * areas["area_o_m2"]),
            0.005,
        ),
        Fixture(
            "A09_BALANCED_RESISTANCE",
            "BALANCED_RESISTANCE",
            299.6,
            298.4,
            1,
            areas["area_i_m2"],
            areas["area_o_m2"],
            1.0 / (0.02 * areas["area_i_m2"]),
            1.0 / (0.02 * areas["area_o_m2"]),
            0.02,
        ),
        Fixture(
            "A10_NEGATIVE_Q_REVERSED_ORIENTATION",
            "NEGATIVE_Q",
            299.6,
            298.4,
            -1,
            0.05,
            0.05,
            2000.0,
            2000.0,
            0.01,
        ),
    ]


def jmu_fixtures() -> list[Fixture]:
    return [
        Fixture(
            "B01_JMU_TUBE_HOT",
            "NONLINEAR_JMU_TUBE_HOT",
            299.9,
            298.2,
            1,
            0.05,
            0.05,
            2000.0,
            400.0,
            0.001,
            True,
            LOCAL_FIXTURE_PRESSURE_PA,
        ),
        Fixture(
            "B02_JMU_SHELL_HOT",
            "NONLINEAR_JMU_SHELL_HOT",
            298.2,
            299.9,
            -1,
            0.05,
            0.05,
            2000.0,
            400.0,
            0.001,
            True,
            LOCAL_FIXTURE_PRESSURE_PA,
        ),
        Fixture(
            "B03_JMU_SMALL_DELTA_T",
            "NONLINEAR_JMU_NEAR_ZERO",
            299.01,
            299.0,
            1,
            0.05,
            0.05,
            2000.0,
            400.0,
            0.001,
            True,
            LOCAL_FIXTURE_PRESSURE_PA,
        ),
        Fixture(
            "B04_JMU_NEGATIVE_Q",
            "NONLINEAR_JMU_NEGATIVE_Q",
            298.2,
            299.9,
            1,
            0.05,
            0.05,
            2000.0,
            400.0,
            0.001,
            True,
            LOCAL_FIXTURE_PRESSURE_PA,
        ),
    ]


def validate_tp(temperature_K: float, pressure_Pa: float) -> None:
    if not math.isfinite(temperature_K) or not math.isfinite(pressure_Pa):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite local property state")
    if not T_MIN_K <= temperature_K <= T_MAX_K:
        raise NumericalFailure("TRIAL_DOMAIN_EXCURSION", "temperature outside reviewed scope")
    if not P_MIN_PA <= pressure_Pa <= P_MAX_PA:
        raise NumericalFailure("TRIAL_DOMAIN_EXCURSION", "pressure outside reviewed scope")


def admit_local_property_identity(
    consumer_support_id: str | None,
    state_support_id: str | None,
    property_snapshot_id: str | None,
) -> None:
    if not consumer_support_id or not state_support_id or not property_snapshot_id:
        raise NumericalFailure("INPUT_AUTHORITY_MISSING", "located local property state is absent")
    if consumer_support_id != state_support_id:
        raise NumericalFailure("SUPPORT_IDENTITY_MISMATCH", "snapshot belongs to another support")


def water_mu_Pa_s(temperature_K: float, pressure_Pa: float) -> float:
    validate_tp(temperature_K, pressure_Pa)
    try:
        value = float(PropsSI("V", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
    except Exception as exc:  # recorded as a typed callback failure
        raise NumericalFailure("PROPERTY_EVALUATION_FAILURE", type(exc).__name__) from exc
    if not math.isfinite(value) or value <= 0.0:
        raise NumericalFailure("PROPERTY_EVALUATION_FAILURE", "invalid water viscosity")
    return value


def shell_jmu(fixture: Fixture, wall_outer_K: float) -> float:
    bulk = water_mu_Pa_s(fixture.shell_bulk_K, fixture.pressure_Pa)
    wall = water_mu_Pa_s(wall_outer_K, fixture.pressure_Pa)
    value: float = float((bulk / wall) ** JMU_EXPONENT)
    if not math.isfinite(value) or value <= 0.0:
        raise NumericalFailure("CORRELATION_EVALUATION_FAILURE", "invalid J_mu callback")
    return value


def h_o(fixture: Fixture, wall_outer_K: float) -> float:
    factor = shell_jmu(fixture, wall_outer_K) if fixture.nonlinear_jmu else 1.0
    value = fixture.h_o_base_W_m2K * factor
    if not math.isfinite(value) or value <= 0.0:
        raise NumericalFailure("CORRELATION_EVALUATION_FAILURE", "invalid shell HTC")
    return value


def residual_W(fixture: Fixture, x: np.ndarray) -> np.ndarray:
    q_hc, wall_i, wall_o = (float(item) for item in x)
    if not all(math.isfinite(item) for item in (q_hc, wall_i, wall_o)):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite unknown")
    if fixture.nonlinear_jmu:
        validate_tp(wall_i, fixture.pressure_Pa)
        validate_tp(wall_o, fixture.pressure_Pa)
    resistance = fixture.wall_resistance_K_W
    if not math.isfinite(resistance) or resistance <= 0.0:
        raise NumericalFailure("SINGULAR_OR_INVALID_RESISTANCE", "wall resistance is not positive")
    q_ts = fixture.s_ts * q_hc
    values = np.asarray(
        [
            q_ts - fixture.g_i_W_K * (fixture.tube_bulk_K - wall_i),
            q_ts - (wall_i - wall_o) / resistance,
            q_ts - h_o(fixture, wall_o) * fixture.area_o_m2 * (wall_o - fixture.shell_bulk_K),
        ],
        dtype=float,
    )
    if not np.all(np.isfinite(values)):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite physical residual")
    return values


def seed(fixture: Fixture) -> np.ndarray:
    if fixture.wall_resistance_K_W <= 0.0 or not math.isfinite(fixture.wall_resistance_K_W):
        raise NumericalFailure("SINGULAR_OR_INVALID_RESISTANCE", "invalid seed resistance")
    r_i = 1.0 / fixture.g_i_W_K
    r_o = 1.0 / fixture.g_o_base_W_K
    q_ts = fixture.delta_t_K / (r_i + fixture.wall_resistance_K_W + r_o)
    wall_i = fixture.tube_bulk_K - q_ts * r_i
    wall_o = fixture.shell_bulk_K + q_ts * r_o
    return np.asarray([fixture.s_ts * q_ts, wall_i, wall_o], dtype=float)


def perturbed_seed(fixture: Fixture) -> np.ndarray:
    x0 = seed(fixture)
    x0[0] *= 0.93
    x0[1] += 0.03 * fixture.delta_t_K
    x0[2] -= 0.03 * fixture.delta_t_K
    return x0


def q_scale_W(fixture: Fixture, scale_name: str, seed_x: np.ndarray) -> float:
    q_seed = abs(fixture.s_ts * float(seed_x[0]))
    if q_seed == 0.0:
        raise NumericalFailure("ZERO_DUTY_EXACT_BRANCH", "exact zero must bypass scaled solve")
    if scale_name == "SEED_DUTY":
        return q_seed
    if scale_name == "CONDUCTANCE_TIMES_DELTA_T":
        return max(
            fixture.g_i_W_K,
            1.0 / fixture.wall_resistance_K_W,
            fixture.g_o_base_W_K,
        ) * abs(fixture.delta_t_K)
    if scale_name == "SEED_DUTY_WITH_MACHINE_FLOOR":
        conductance = max(
            fixture.g_i_W_K,
            1.0 / fixture.wall_resistance_K_W,
            fixture.g_o_base_W_K,
        )
        tref = max(abs(fixture.tube_bulk_K), abs(fixture.shell_bulk_K))
        return max(q_seed, conductance * math.ulp(tref))
    raise ValueError("unknown residual scale")


def residual_roundoff_bound_W(fixture: Fixture, q_scale: float) -> float:
    conductance = max(
        fixture.g_i_W_K,
        1.0 / fixture.wall_resistance_K_W,
        fixture.g_o_base_W_K,
    )
    tref = max(abs(fixture.tube_bulk_K), abs(fixture.shell_bulk_K))
    return conductance * math.ulp(tref) + math.ulp(q_scale)


def analytic_oracle(fixture: Fixture) -> dict[str, float]:
    ri = 1.0 / fixture.g_i_W_K
    ro = 1.0 / fixture.g_o_base_W_K
    q_ts = fixture.delta_t_K / (ri + fixture.wall_resistance_K_W + ro)
    return {
        "q_hc_W": fixture.s_ts * q_ts,
        "T_wall_inner_K": fixture.tube_bulk_K - q_ts * ri,
        "T_wall_outer_K": fixture.shell_bulk_K + q_ts * ro,
    }


def nonlinear_oracle(fixture: Fixture) -> dict[str, Any]:
    if not fixture.nonlinear_jmu:
        raise ValueError("nonlinear scalar oracle only applies to J_mu fixtures")
    low, high = sorted((fixture.tube_bulk_K, fixture.shell_bulk_K))

    def q_from_wall_o(wall_o: float) -> float:
        return h_o(fixture, wall_o) * fixture.area_o_m2 * (wall_o - fixture.shell_bulk_K)

    def scalar_residual(wall_o: float) -> float:
        q_ts = q_from_wall_o(wall_o)
        wall_i = wall_o + q_ts * fixture.wall_resistance_K_W
        validate_tp(wall_i, fixture.pressure_Pa)
        return q_ts - fixture.g_i_W_K * (fixture.tube_bulk_K - wall_i)

    grid = np.linspace(low, high, 257)
    values = [scalar_residual(float(value)) for value in grid]
    diffs = [right - left for left, right in zip(values, values[1:], strict=False)]
    increasing = all(value > 0.0 for value in diffs)
    decreasing = all(value < 0.0 for value in diffs)
    if not (increasing or decreasing) or values[0] * values[-1] >= 0.0:
        raise NumericalFailure("INDEPENDENT_ORACLE_INVALID", "no monotone strict physical bracket")
    midpoint = 0.5 * (low + high)
    root, details = brentq(
        scalar_residual,
        low,
        high,
        xtol=math.ulp(midpoint),
        rtol=4.0 * FLOAT_EPSILON,
        maxiter=256,
        full_output=True,
        disp=True,
    )
    q_ts = q_from_wall_o(float(root))
    wall_i = float(root) + q_ts * fixture.wall_resistance_K_W
    return {
        "q_hc_W": fixture.s_ts * q_ts,
        "T_wall_inner_K": wall_i,
        "T_wall_outer_K": float(root),
        "method": "BRENTQ_VALIDATION_ORACLE_ONLY",
        "production_scalar_reduction_selected": False,
        "scope": "ONE_SMOOTH_MONOTONE_NUMERICAL_FIXTURE",
        "bracket_K": [low, high],
        "bracket_endpoint_residual_W": [values[0], values[-1]],
        "grid_points": len(grid),
        "strict_monotone_on_grid": increasing or decreasing,
        "converged": bool(details.converged),
        "iterations": int(details.iterations),
        "function_calls": int(details.function_calls),
        "xtol_K": math.ulp(midpoint),
        "rtol": 4.0 * FLOAT_EPSILON,
        "maxiter": 256,
    }


def oracle_for(fixture: Fixture) -> dict[str, Any]:
    return nonlinear_oracle(fixture) if fixture.nonlinear_jmu else analytic_oracle(fixture)


def variable_scale(fixture: Fixture, x0: np.ndarray, policy: str) -> Any:
    if policy == "ONE":
        return 1.0
    if policy == "JACOBIAN":
        return "jac"
    if policy == "INITIALIZATION_DERIVED":
        q_scale = abs(float(x0[0]))
        delta_t = abs(fixture.delta_t_K)
        if q_scale <= 0.0 or delta_t <= 0.0:
            raise NumericalFailure("INITIALIZATION_FAILURE", "zero scale uses exact zero branch")
        return [q_scale, delta_t, delta_t]
    raise ValueError("unknown variable scale")


def residual_callback_cap(max_nfev: int, jacobian: str) -> int:
    # For 3 variables, count at most one base residual per counted evaluation
    # plus the selected finite-difference stencil for each Jacobian evaluation.
    stencil_calls = 3 if jacobian == "2-point" else 6
    return max_nfev * (1 + stencil_calls)


def solve_fixture(
    fixture: Fixture,
    oracle: dict[str, Any],
    profile: dict[str, Any],
    *,
    residual_scale: str = "SEED_DUTY",
    use_perturbed_seed: bool = True,
) -> dict[str, Any]:
    try:
        x0 = perturbed_seed(fixture) if use_perturbed_seed else seed(fixture)
        x_seed = seed(fixture)
        scale_W = q_scale_W(fixture, residual_scale, x_seed)
        roundoff_W = residual_roundoff_bound_W(fixture, scale_W)
        lower = np.asarray([-np.inf, -np.inf, -np.inf], dtype=float)
        upper = np.asarray([np.inf, np.inf, np.inf], dtype=float)
        if fixture.nonlinear_jmu:
            lower[1:] = T_MIN_K
            upper[1:] = T_MAX_K
        options = {
            "method": profile["method"],
            "loss": profile["loss"],
            "ftol": profile["ftol"],
            "xtol": profile["xtol"],
            "gtol": profile["gtol"],
            "jac": profile["jacobian"],
            "diff_step": profile["diff_step"],
            "x_scale": variable_scale(fixture, x0, profile["x_scale"]),
            "max_nfev": profile["max_nfev"],
            "bounds": (lower, upper),
            "tr_solver": "exact",
            "tr_options": {},
            "f_scale": 1.0,
            "jac_sparsity": None,
        }
        call_count = 0
        call_cap = residual_callback_cap(int(profile["max_nfev"]), str(profile["jacobian"]))

        def callback(x: np.ndarray) -> np.ndarray:
            nonlocal call_count
            call_count += 1
            if call_count > call_cap:
                raise NumericalFailure(
                    "SOLVER_RESOURCE_EXHAUSTION", "finite-difference callback budget exhausted"
                )
            return residual_W(fixture, x) / scale_W

        result = least_squares(callback, x0, **options)
        x = np.asarray(result.x, dtype=float)
        residual = residual_W(fixture, x)
        max_residual = float(np.max(np.abs(residual)))
        residual_ok = max_residual <= roundoff_W
        valid_domain = bool(np.all(np.isfinite(x)))
        if fixture.nonlinear_jmu:
            valid_domain = valid_domain and all(T_MIN_K <= float(v) <= T_MAX_K for v in x[1:])
        accepted = bool(result.success and residual_ok and valid_domain)
        if result.nfev >= int(profile["max_nfev"]) and not accepted:
            failure_class = "SOLVER_RESOURCE_EXHAUSTION"
        elif result.success and not residual_ok:
            failure_class = "SOLVER_TERMINATED_RESIDUAL_UNACCEPTED"
        elif not result.success:
            failure_class = "NOT_CONVERGED"
        else:
            failure_class = "NONE"
        q_hc, wall_i, wall_o = (float(value) for value in x)
        q_oracle = float(oracle["q_hc_W"])
        q_error = abs(q_hc - q_oracle)
        is_near_zero = fixture.fixture_class == "NEAR_ZERO" or fixture.fixture_class.endswith(
            "NEAR_ZERO"
        )
        relative_error = None if is_near_zero or q_oracle == 0.0 else q_error / abs(q_oracle)
        return {
            "case_id": fixture.case_id,
            "fixture_class": fixture.fixture_class,
            "initialization": "DETERMINISTIC_PERTURBED_DIRECT_ALGEBRAIC_SEED"
            if use_perturbed_seed
            else "DIRECT_ALGEBRAIC_SEED",
            "initialization_jmu_identity_candidate": 1.0 if fixture.nonlinear_jmu else None,
            "initialization_jmu_is_production_physics": False,
            "solver": "SCIPY_LEAST_SQUARES_TRF_LINEAR_LOSS",
            "profile": profile,
            "residual_scale_id": residual_scale,
            "residual_scale_W": scale_W,
            "roundoff_residual_bound_W": roundoff_W,
            "q_hc_W": q_hc,
            "q_ts_W": fixture.s_ts * q_hc,
            "T_wall_inner_K": wall_i,
            "T_wall_outer_K": wall_o,
            "physical_residuals_W": [float(value) for value in residual],
            "max_abs_physical_residual_W": max_residual,
            "scaled_residual_inf_norm": max_residual / scale_W,
            "residual_acceptance_rule": (
                "max_abs_r_le_machine_roundoff_bound_W;relative_component_not_used"
            ),
            "post_residual_acceptance": residual_ok,
            "q_hc_absolute_error_W": q_error,
            "q_hc_relative_error": relative_error,
            "q_hc_relative_error_status": "NOT_COMPUTED_NEAR_ZERO_OR_ZERO"
            if relative_error is None
            else "COMPUTED_NONZERO_ORACLE",
            "T_wall_inner_absolute_error_K": abs(wall_i - float(oracle["T_wall_inner_K"])),
            "T_wall_outer_absolute_error_K": abs(wall_o - float(oracle["T_wall_outer_K"])),
            "nfev": int(result.nfev),
            "njev": int(result.njev) if result.njev is not None else None,
            "residual_callback_count_including_fd": call_count,
            "residual_callback_cap": call_cap,
            "solver_termination_code": int(result.status),
            "solver_message": str(result.message),
            "solver_success": bool(result.success),
            "domain_valid": valid_domain,
            "negative_q_hc": q_hc < 0.0,
            "negative_q_numerically_allowed": True,
            "negative_q_applicability": "UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY"
            if q_hc < 0.0
            else "NOT_APPLICABLE",
            "accepted_by_candidate_policy": accepted,
            "engineering_acceptance": False,
            "failure_class": failure_class,
            "distance_to_max_nfev": int(profile["max_nfev"] - result.nfev),
            "final_active_jmu_evaluated": fixture.nonlinear_jmu,
            "partial_result_authoritative": False,
        }
    except NumericalFailure as exc:
        return {
            "case_id": fixture.case_id,
            "outcome": "TYPED_FAILURE",
            "failure_class": exc.failure_class,
            "failure_detail": exc.detail,
            "partial_result_authoritative": False,
        }


def exact_zero_result(fixture: Fixture) -> dict[str, Any]:
    if fixture.delta_t_K != 0.0:
        raise ValueError("zero branch requires exact bulk-temperature equality")
    x = np.asarray([0.0, fixture.tube_bulk_K, fixture.shell_bulk_K], dtype=float)
    return {
        "case_id": fixture.case_id,
        "solver_invoked": False,
        "branch": "EXACT_ZERO_DUTY_PASSIVE_NETWORK",
        "q_hc_W": 0.0,
        "q_ts_W": 0.0,
        "T_wall_inner_K": fixture.tube_bulk_K,
        "T_wall_outer_K": fixture.shell_bulk_K,
        "residuals_W": [float(value) for value in residual_W(fixture, x)],
        "epsilon_or_deadband_used": False,
        "result_authoritative": False,
    }


def failure_fixtures(reference: Fixture) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []

    def capture(case_id: str, action: Any, expected: str) -> None:
        try:
            action()
        except NumericalFailure as exc:
            outputs.append(
                {
                    "case_id": case_id,
                    "expected_failure_class": expected,
                    "observed_failure_class": exc.failure_class,
                    "pass": exc.failure_class == expected,
                    "authoritative_partial_result": False,
                    "penalty_residual_used": False,
                }
            )
        else:
            outputs.append(
                {
                    "case_id": case_id,
                    "expected_failure_class": expected,
                    "observed_failure_class": "NONE",
                    "pass": False,
                    "authoritative_partial_result": False,
                    "penalty_residual_used": False,
                }
            )

    capture(
        "F01_MISSING_LOCAL_PROPERTY_STATE",
        lambda: admit_local_property_identity("SUPPORT::A", None, None),
        "INPUT_AUTHORITY_MISSING",
    )
    capture(
        "F02_SUPPORT_IDENTITY_MISMATCH",
        lambda: admit_local_property_identity("SUPPORT::A", "SUPPORT::B", "PROPERTY::B"),
        "SUPPORT_IDENTITY_MISMATCH",
    )
    capture(
        "F03_WALL_TRIAL_OUTSIDE_PROPERTY_DOMAIN",
        lambda: validate_tp(300.01, P_MAX_PA),
        "TRIAL_DOMAIN_EXCURSION",
    )

    def nonfinite_callback() -> float:
        value = float("inf")
        if not math.isfinite(value):
            raise NumericalFailure("NONFINITE_TRIAL", "callback returned inf")
        return value

    capture("F04_NONFINITE_CALLBACK", nonfinite_callback, "NONFINITE_TRIAL")
    bad_resistance = Fixture("F05", "FAILURE", 299.6, 298.4, 1, 0.05, 0.05, 2000, 2000, 0.0)
    capture(
        "F05_NONPOSITIVE_RESISTANCE",
        lambda: residual_W(bad_resistance, seed(reference)),
        "SINGULAR_OR_INVALID_RESISTANCE",
    )
    outputs.append(
        {
            "case_id": "F06_NEGATIVE_Q_ALLOWED",
            "negative_q_model_level_allowed": analytic_oracle(
                Fixture("F06", "NEGATIVE_Q", 298.4, 299.6, 1, 0.05, 0.05, 2000, 2000, 0.01)
            )["q_hc_W"]
            < 0.0,
            "clamp_or_abs_used": False,
            "pass": True,
            "authoritative_partial_result": False,
        }
    )

    nonlinear_reference = next(
        fixture for fixture in jmu_fixtures() if fixture.case_id == "B01_JMU_TUBE_HOT"
    )
    nonlinear_reference_oracle = nonlinear_oracle(nonlinear_reference)
    weak_profile = {**SELECTED_PROFILE, "ftol": 1e-6, "xtol": 1e-6, "gtol": 1e-6, "max_nfev": 64}
    weak = solve_fixture(nonlinear_reference, nonlinear_reference_oracle, weak_profile)
    outputs.append(
        {
            "case_id": "F07_SOLVER_SUCCESS_RESIDUAL_UNACCEPTABLE",
            "solver_success": weak.get("solver_success"),
            "post_residual_acceptance": weak.get("post_residual_acceptance"),
            "observed_failure_class": weak.get("failure_class"),
            "pass": bool(weak.get("solver_success"))
            and not bool(weak.get("post_residual_acceptance"))
            and weak.get("failure_class") == "SOLVER_TERMINATED_RESIDUAL_UNACCEPTED",
            "authoritative_partial_result": False,
        }
    )
    cap_profile = {**SELECTED_PROFILE, "max_nfev": 4}
    cap = solve_fixture(nonlinear_reference, nonlinear_oracle(nonlinear_reference), cap_profile)
    outputs.append(
        {
            "case_id": "F08_RESOURCE_EXHAUSTION",
            "observed_failure_class": cap.get("failure_class"),
            "solver_success": cap.get("solver_success"),
            "nfev": cap.get("nfev"),
            "pass": cap.get("failure_class") == "SOLVER_RESOURCE_EXHAUSTION",
            "authoritative_partial_result": False,
        }
    )
    capture(
        "F09_NONFINITE_PHYSICAL_RESIDUAL",
        lambda: residual_W(reference, np.asarray([float("nan"), 299.0, 299.0])),
        "NONFINITE_TRIAL",
    )
    return outputs


def summary(records: list[dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any]:
    evaluations = sorted(int(record.get("nfev", 0)) for record in records)
    p95_index = max(0, math.ceil(0.95 * len(evaluations)) - 1)
    numeric_outputs = [
        {
            "q_hc_W": record.get("q_hc_W"),
            "q_ts_W": record.get("q_ts_W"),
            "T_wall_inner_K": record.get("T_wall_inner_K"),
            "T_wall_outer_K": record.get("T_wall_outer_K"),
            "physical_residuals_W": record.get("physical_residuals_W"),
        }
        for record in records
    ]
    callback_cap = residual_callback_cap(int(settings["max_nfev"]), str(settings["jacobian"]))
    max_callbacks = max(
        (int(record.get("residual_callback_count_including_fd", 0)) for record in records),
        default=0,
    )
    return {
        "settings": settings,
        "numeric_output_matrix_canonical_hash": canonical_sha256(
            {"numeric_outputs": numeric_outputs}
        ),
        "fixture_count": len(records),
        "solver_success_count": sum(bool(record.get("solver_success")) for record in records),
        "accepted_count": sum(
            bool(record.get("accepted_by_candidate_policy")) for record in records
        ),
        "max_nfev_observed": max((int(record.get("nfev", 0)) for record in records), default=0),
        "nfev_p95_observed": evaluations[p95_index] if evaluations else 0,
        "nfev_distribution": evaluations,
        "max_njev_observed": max(
            (int(record.get("njev", 0) or 0) for record in records), default=0
        ),
        "max_residual_callback_count": max_callbacks,
        "residual_callback_cap": callback_cap,
        "distance_to_residual_callback_cap": callback_cap - max_callbacks,
        "distance_to_max_nfev_at_observed_max": int(settings["max_nfev"])
        - max((int(record.get("nfev", 0)) for record in records), default=0),
        "max_q_error_W": max(
            (float(record.get("q_hc_absolute_error_W", 0.0)) for record in records), default=0.0
        ),
        "max_wall_temperature_error_K": max(
            (
                max(
                    float(record.get("T_wall_inner_absolute_error_K", 0.0)),
                    float(record.get("T_wall_outer_absolute_error_K", 0.0)),
                )
                for record in records
            ),
            default=0.0,
        ),
        "max_scaled_residual_inf_norm": max(
            (float(record.get("scaled_residual_inf_norm", 0.0)) for record in records), default=0.0
        ),
        "failure_classes": sorted(
            {
                str(record["failure_class"])
                for record in records
                if record.get("failure_class") not in (None, "NONE")
            }
        ),
    }


def run_profile(
    fixtures: list[Fixture],
    oracles: dict[str, dict[str, Any]],
    profile: dict[str, Any],
    *,
    scale: str = "SEED_DUTY",
    perturbed_seed: bool = False,
) -> list[dict[str, Any]]:
    return [
        solve_fixture(
            fixture,
            oracles[fixture.case_id],
            profile,
            residual_scale=scale,
            use_perturbed_seed=perturbed_seed,
        )
        for fixture in fixtures
    ]


def sweep(fixtures: list[Fixture], oracles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    tol_values = [1e-6, 1e-8, 1e-10, 1e-12, 1e-13, 1e-14, 1e-15]
    joint: list[dict[str, Any]] = []
    for index, tol in enumerate(tol_values, start=1):
        candidate = {**SELECTED_PROFILE, "ftol": tol, "xtol": tol, "gtol": tol}
        records = run_profile(fixtures, oracles, candidate)
        row = summary(records, candidate)
        row["experiment_id"] = f"R92-JOINT-TOL-{index:02d}"
        row["experiment_class"] = "JOINT_TOLERANCE_SWEEP"
        joint.append(row)
        rows.append(row)
    one_axis: list[dict[str, Any]] = []
    for name in ("ftol", "xtol", "gtol"):
        for tol in (1e-6, 1e-8, 1e-10, 1e-12, 1e-13, 1e-14):
            candidate = {**SELECTED_PROFILE, name: tol}
            rec = run_profile(fixtures, oracles, candidate)
            one_axis.append(summary(rec, candidate))
    for jac in ("2-point", "3-point"):
        candidate = {**SELECTED_PROFILE, "jacobian": jac}
        one_axis.append(summary(run_profile(fixtures, oracles, candidate), candidate))
    for step in (1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9):
        candidate = {**SELECTED_PROFILE, "diff_step": step}
        one_axis.append(summary(run_profile(fixtures, oracles, candidate), candidate))
    for scale in ("ONE", "JACOBIAN", "INITIALIZATION_DERIVED"):
        candidate = {**SELECTED_PROFILE, "x_scale": scale}
        one_axis.append(summary(run_profile(fixtures, oracles, candidate), candidate))
    for cap in (4, 6, 8, 12, 16, 32):
        candidate = {**SELECTED_PROFILE, "max_nfev": cap}
        one_axis.append(summary(run_profile(fixtures, oracles, candidate), candidate))
    for scale in ("SEED_DUTY", "CONDUCTANCE_TIMES_DELTA_T", "SEED_DUTY_WITH_MACHINE_FLOOR"):
        one_axis.append(
            summary(
                run_profile(fixtures, oracles, SELECTED_PROFILE, scale=scale),
                {**SELECTED_PROFILE, "residual_scale": scale},
            )
        )
    one_axis.append(
        summary(
            run_profile(fixtures, oracles, SELECTED_PROFILE, perturbed_seed=True),
            {**SELECTED_PROFILE, "initialization": "DETERMINISTIC_PERTURBED_SEED"},
        )
    )
    plateau: list[dict[str, Any]] = []
    selected_records = run_profile(fixtures, oracles, SELECTED_PROFILE)
    joint_records = [
        run_profile(fixtures, oracles, {**SELECTED_PROFILE, "ftol": tol, "xtol": tol, "gtol": tol})
        for tol in tol_values
    ]
    for index in range(len(tol_values) - 1):
        left_numeric = [
            {
                "q_hc_W": record.get("q_hc_W"),
                "q_ts_W": record.get("q_ts_W"),
                "T_wall_inner_K": record.get("T_wall_inner_K"),
                "T_wall_outer_K": record.get("T_wall_outer_K"),
                "physical_residuals_W": record.get("physical_residuals_W"),
            }
            for record in joint_records[index]
        ]
        right_numeric = [
            {
                "q_hc_W": record.get("q_hc_W"),
                "q_ts_W": record.get("q_ts_W"),
                "T_wall_inner_K": record.get("T_wall_inner_K"),
                "T_wall_outer_K": record.get("T_wall_outer_K"),
                "physical_residuals_W": record.get("physical_residuals_W"),
            }
            for record in joint_records[index + 1]
        ]
        left = canonical_json_bytes({"numeric_outputs": left_numeric})
        right = canonical_json_bytes({"numeric_outputs": right_numeric})
        plateau.append(
            {
                "looser_tolerance": tol_values[index],
                "tighter_tolerance": tol_values[index + 1],
                "result_matrix_bitwise_equal": left == right,
                "max_q_abs_change_W": max(
                    abs(float(a.get("q_hc_W", 0.0)) - float(b.get("q_hc_W", 0.0)))
                    for a, b in zip(joint_records[index], joint_records[index + 1], strict=True)
                ),
                "max_wall_abs_change_K": max(
                    max(
                        abs(
                            float(a.get("T_wall_inner_K", 0.0))
                            - float(b.get("T_wall_inner_K", 0.0))
                        ),
                        abs(
                            float(a.get("T_wall_outer_K", 0.0))
                            - float(b.get("T_wall_outer_K", 0.0))
                        ),
                    )
                    for a, b in zip(joint_records[index], joint_records[index + 1], strict=True)
                ),
            }
        )
    fully_accepted_indices = [
        index for index, row in enumerate(joint) if row["accepted_count"] == len(fixtures)
    ]
    accepted_adjacent_pairs = [
        index
        for index in range(len(joint) - 1)
        if index in fully_accepted_indices and index + 1 in fully_accepted_indices
    ]
    selected_q_error_envelope = max(
        float(record["q_hc_absolute_error_W"]) for record in selected_records
    )
    selected_wall_error_envelope = max(
        max(
            float(record["T_wall_inner_absolute_error_K"]),
            float(record["T_wall_outer_absolute_error_K"]),
        )
        for record in selected_records
    )
    plateau_comparison_sensitivity = []
    for multiplier in (0.25, 0.5, 1.0, 2.0):
        pair_audits = []
        for index in accepted_adjacent_pairs:
            left_records = joint_records[index]
            right_records = joint_records[index + 1]
            max_q_delta = max(
                abs(float(left["q_hc_W"]) - float(right["q_hc_W"]))
                for left, right in zip(left_records, right_records, strict=True)
            )
            max_wall_delta = max(
                max(
                    abs(float(left["T_wall_inner_K"]) - float(right["T_wall_inner_K"])),
                    abs(float(left["T_wall_outer_K"]) - float(right["T_wall_outer_K"])),
                )
                for left, right in zip(left_records, right_records, strict=True)
            )
            q_limit = multiplier * selected_q_error_envelope
            wall_limit = multiplier * selected_wall_error_envelope
            pair_audits.append(
                {
                    "looser_experiment_id": joint[index]["experiment_id"],
                    "tighter_experiment_id": joint[index + 1]["experiment_id"],
                    "max_q_delta_W": max_q_delta,
                    "q_delta_limit_W": q_limit,
                    "max_wall_delta_K": max_wall_delta,
                    "wall_delta_limit_K": wall_limit,
                    "pass": max_q_delta <= q_limit and max_wall_delta <= wall_limit,
                }
            )
        plateau_comparison_sensitivity.append(
            {
                "experiment_id": f"R92-PLATEAU-THRESHOLD-{multiplier:g}X",
                "threshold_multiplier": multiplier,
                "authority_class": "PROJECT_NUMERICAL_POLICY_SENSITIVITY",
                "error_envelope_basis": "SELECTED_PROFILE_INDEPENDENT_ORACLE_OBSERVED_ENVELOPE",
                "fully_accepted_adjacent_pair_count": len(accepted_adjacent_pairs),
                "passing_adjacent_pair_count": sum(int(row["pass"]) for row in pair_audits),
                "all_pairs_pass": all(row["pass"] for row in pair_audits),
                "pairs": pair_audits,
            }
        )
    first_fully_accepted = fully_accepted_indices[0]
    anchor_records = joint_records[first_fully_accepted]
    selected_vs_anchor = {
        "anchor_experiment_id": joint[first_fully_accepted]["experiment_id"],
        "max_q_delta_W": max(
            abs(float(selected["q_hc_W"]) - float(anchor["q_hc_W"]))
            for selected, anchor in zip(selected_records, anchor_records, strict=True)
        ),
        "max_wall_delta_K": max(
            max(
                abs(float(selected["T_wall_inner_K"]) - float(anchor["T_wall_inner_K"])),
                abs(float(selected["T_wall_outer_K"]) - float(anchor["T_wall_outer_K"])),
            )
            for selected, anchor in zip(selected_records, anchor_records, strict=True)
        ),
        "selected_profile_fully_accepted": summary(selected_records, SELECTED_PROFILE)[
            "accepted_count"
        ]
        == len(fixtures),
        "within_selected_plateau_envelope": False,
    }
    chosen_multiplier = next(
        row["threshold_multiplier"]
        for row in plateau_comparison_sensitivity
        if row["all_pairs_pass"]
    )
    selected_vs_anchor["within_selected_plateau_envelope"] = (
        selected_vs_anchor["max_q_delta_W"] <= chosen_multiplier * selected_q_error_envelope
        and selected_vs_anchor["max_wall_delta_K"]
        <= chosen_multiplier * selected_wall_error_envelope
    )
    acceptance_sensitivity = []
    for multiplier in (0.5, 1.0, 2.0):
        accepted = 0
        for _fixture, record in zip(fixtures, selected_records, strict=True):
            accepted += int(
                float(record["max_abs_physical_residual_W"])
                <= multiplier * float(record["roundoff_residual_bound_W"])
            )
        acceptance_sensitivity.append(
            {
                "roundoff_bound_multiplier": multiplier,
                "accepted_fixtures": accepted,
                "fixture_count": len(fixtures),
                "authority_class": "MACHINE_PRECISION_DERIVED_THRESHOLD_SENSITIVITY",
            }
        )
    for index, row in enumerate(one_axis, start=1):
        row["experiment_id"] = f"R92-OAT-{index:02d}"
        row["experiment_class"] = "ONE_PARAMETER_METHOD_SENSITIVITY"
    return {
        "fixture_ids": [fixture.case_id for fixture in fixtures],
        "joint_tolerance_sweep": joint,
        "joint_tolerance_output_plateau": plateau,
        "plateau_comparison_sensitivity": plateau_comparison_sensitivity,
        "plateau_selected_threshold_multiplier": chosen_multiplier,
        "selected_profile_vs_joint_plateau_anchor": selected_vs_anchor,
        "one_parameter_sensitivity": one_axis,
        "one_parameter_row_count": len(one_axis),
        "residual_acceptance_roundoff_multiplier_sensitivity": acceptance_sensitivity,
        "comparison_policy": (
            "BITWISE_HASH_RECORDED;NUMERICAL_PLATEAU_USES_TESTED_MULTIPLIERS_OF_SELECTED_"
            "INDEPENDENT_ORACLE_OBSERVED_ERROR_ENVELOPE"
        ),
        "jacobian_callback_cost_is_instrumented": True,
    }


def failure_and_policy_experiments(fixtures: list[Fixture]) -> dict[str, Any]:
    reference = fixtures[0]
    fail_rows = failure_fixtures(reference)
    zero_fixture = next(fixture for fixture in analytic_fixtures() if fixture.delta_t_K == 0.0)
    zero = exact_zero_result(zero_fixture)
    weak_candidate = {
        **SELECTED_PROFILE,
        "ftol": 1e-6,
        "xtol": 1e-6,
        "gtol": 1e-6,
        "max_nfev": 64,
    }
    low_cap_candidate = {**SELECTED_PROFILE, "max_nfev": 4}
    nonlinear_reference = next(
        fixture for fixture in jmu_fixtures() if fixture.case_id == "B01_JMU_TUBE_HOT"
    )
    nonlinear_reference_oracle = nonlinear_oracle(nonlinear_reference)
    weak = solve_fixture(nonlinear_reference, nonlinear_reference_oracle, weak_candidate)
    capped = solve_fixture(nonlinear_reference, nonlinear_reference_oracle, low_cap_candidate)
    return {
        "failure_fixtures": fail_rows,
        "zero_duty_exact_branch": zero,
        "weak_solver_candidate": weak,
        "resource_capped_candidate": capped,
        "fake_penalty_residual_used": False,
        "nan_as_success_used": False,
        "partial_result_authoritative": False,
    }


def input_record(fixture: Fixture) -> dict[str, Any]:
    return {
        **asdict(fixture),
        "pressure_Pa": fixture.pressure_Pa if fixture.nonlinear_jmu else None,
        "fixture_kind": "NUMERICAL_KERNEL_FIXTURE",
        "parameter_authority": "NUMERICAL_METHOD_FIXTURE_PARAMETERS_NOT_ENGINEERING_AUTHORITY",
        "physical_support_id": "SUPPORT::" + fixture.case_id,
        "local_property_pressure_role": "EXPLICIT_LOCATED_LOCAL_FIXTURE_STATE_NOT_PRESSURE_RULE"
        if fixture.nonlinear_jmu
        else "NOT_APPLICABLE",
    }


def serialization_roundtrip(records: list[dict[str, Any]]) -> dict[str, Any]:
    chosen = records[0]
    values = {
        "q_hc_W": chosen["q_hc_W"],
        "T_wall_inner_K": chosen["T_wall_inner_K"],
        "T_wall_outer_K": chosen["T_wall_outer_K"],
        "r_i_W": chosen["physical_residuals_W"][0],
        "r_w_W": chosen["physical_residuals_W"][1],
        "r_o_W": chosen["physical_residuals_W"][2],
        "negative_q_hc_W": next(record["q_hc_W"] for record in records if record["q_hc_W"] < 0.0),
    }
    canonical = canonical_json_bytes(values)
    parsed = json.loads(canonical)
    errors = {key: abs(float(parsed[key]) - float(value)) for key, value in values.items()}
    exact = all(float(parsed[key]) == float(value) for key, value in values.items())
    return {
        "serialization_path": "hexagent.canonical_json.canonical_json_bytes_then_json.loads",
        "tested_values": values,
        "absolute_quantization_errors": errors,
        "max_absolute_quantization_error_by_basis": {
            "W": max(
                errors[key] for key in ("q_hc_W", "r_i_W", "r_w_W", "r_o_W", "negative_q_hc_W")
            ),
            "K": max(errors["T_wall_inner_K"], errors["T_wall_outer_K"]),
        },
        "roundtrip_bitwise_equal_as_binary_float": exact,
        "result": "PASS_BITWISE_FLOAT_ROUNDTRIP" if exact else "FAIL",
        "display_rounding_included": False,
    }


def full_experiment() -> dict[str, Any]:
    analytic = analytic_fixtures()
    nonlinear = jmu_fixtures()
    all_fixtures = analytic + nonlinear
    nonzero = [fixture for fixture in all_fixtures if fixture.delta_t_K != 0.0]
    oracles = {fixture.case_id: oracle_for(fixture) for fixture in nonzero}
    selected = run_profile(nonzero, oracles, SELECTED_PROFILE)
    repeated = run_profile(nonzero, oracles, SELECTED_PROFILE)
    selected_bytes = canonical_json_bytes({"records": selected})
    repeated_bytes = canonical_json_bytes({"records": repeated})
    selected_zero = exact_zero_result(
        next(fixture for fixture in analytic if fixture.delta_t_K == 0.0)
    )
    repeated_zero = exact_zero_result(
        next(fixture for fixture in analytic if fixture.delta_t_K == 0.0)
    )
    selected_zero_bytes = canonical_json_bytes({"record": selected_zero})
    repeated_zero_bytes = canonical_json_bytes({"record": repeated_zero})
    root_error = {
        "scope": "OBSERVED_ENVELOPE_OVER_13_FIXED_NUMERICAL_FIXTURES_ONLY_NOT_UNIVERSAL_BOUND",
        "q_hc_max_absolute_error_W": max(
            float(record["q_hc_absolute_error_W"]) for record in selected
        ),
        "T_wall_inner_max_absolute_error_K": max(
            float(record["T_wall_inner_absolute_error_K"]) for record in selected
        ),
        "T_wall_outer_max_absolute_error_K": max(
            float(record["T_wall_outer_absolute_error_K"]) for record in selected
        ),
        "near_zero_relative_error": "NOT_USED;ABSOLUTE_ERROR_REPORTED",
    }
    input_matrix = [input_record(fixture) for fixture in all_fixtures]
    result_matrix = {
        "selected_profile": SELECTED_PROFILE,
        "selected_nonzero_fixture_records": selected,
        "zero_duty_record": selected_zero,
        "failure_and_policy_experiments": failure_and_policy_experiments(nonzero),
        "iteration_root_error_observed_envelope": root_error,
        "method_sensitivity": sweep(nonzero, oracles),
        "serialization_quantization": serialization_roundtrip(selected),
    }
    cap_stats = summary(selected, SELECTED_PROFILE)
    result: dict[str, Any] = {
        "schema_version": "task172.numerical-error-budget-stopping-method-sensitivity-results.r1",
        "task_id": (
            "TASK172_V0_7_NUMERICAL_ERROR_BUDGET_STOPPING_QUANTITATIVE_"
            "ALLOCATION_AND_METHOD_SENSITIVITY_R1"
        ),
        "runtime": {
            "python_version": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "scipy_version": scipy.__version__,
            "numpy_version": np.__version__,
            "coolprop_version": CoolProp.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "fixture_counts": {
            "analytic_oracle_fixture_count": len(analytic),
            "nonlinear_jmu_fixture_count": len(nonlinear),
            "failure_fixture_count": 9,
            "numerical_fixture_count": len(analytic) + len(nonlinear) + 9,
            "nonzero_solver_fixture_count": len(nonzero),
        },
        "input_matrix": input_matrix,
        "input_matrix_canonical_hash": canonical_sha256({"fixtures": input_matrix}),
        "frozen_equation_set": {
            "unknowns": ["q_hc", "T_wall_inner", "T_wall_outer"],
            "unknown_count": 3,
            "residuals": ["r_i", "r_w", "r_o"],
            "equation_count": 3,
            "q_ts_relation": "q_ts=s_ts*q_hc",
            "physical_residuals_changed": False,
            "all_residuals_units": "W",
        },
        "property_profile": {
            "authority_id": "V07-T172-WATER-PROPERTY-PROFILE-R2",
            "fluid": "PURE_ORDINARY_WATER",
            "backend": "HEOS",
            "reference_state": "DEF",
            "phase": "STABLE_SINGLE_PHASE_LIQUID",
            "temperature_K": [T_MIN_K, T_MAX_K],
            "pressure_Pa": [P_MIN_PA, P_MAX_PA],
            "pressure_input": LOCAL_FIXTURE_PRESSURE_PA,
            "pressure_input_is_rule": False,
            "domain_failure_is_typed": True,
        },
        "analytic_oracles": [
            {"case_id": fixture.case_id, **analytic_oracle(fixture)} for fixture in analytic
        ],
        "independent_nonlinear_oracles": [
            {"case_id": fixture.case_id, **oracles[fixture.case_id]} for fixture in nonlinear
        ],
        "selected_profile_summary": cap_stats,
        "selected_result_matrix": result_matrix,
        "selected_result_matrix_canonical_hash": canonical_sha256(result_matrix),
        "same_input_same_result_bytes": selected_bytes == repeated_bytes,
        "same_input_same_result_hash": hashlib.sha256(selected_bytes).hexdigest()
        == hashlib.sha256(repeated_bytes).hexdigest(),
        "selected_result_bytes_sha256": hashlib.sha256(selected_bytes).hexdigest(),
        "repeat_result_bytes_sha256": hashlib.sha256(repeated_bytes).hexdigest(),
        "zero_duty_same_input_same_result_bytes": selected_zero_bytes == repeated_zero_bytes,
        "zero_duty_same_input_same_result_hash": hashlib.sha256(selected_zero_bytes).hexdigest()
        == hashlib.sha256(repeated_zero_bytes).hexdigest(),
        "zero_duty_result_bytes_sha256": hashlib.sha256(selected_zero_bytes).hexdigest(),
        "numerical_policy": {
            "residual_scaling": "r_hat=r_W/abs(q_ts_seed); exact zero duty bypasses scaling",
            "residual_acceptance": (
                "max(abs(r_i,r_w,r_o)) <= G_ref*ulp(T_ref)+ulp(Q_scale); "
                "relative component NOT_USED"
            ),
            "residual_acceptance_units": "W",
            "variable_scale": (
                "[abs(q_hc_seed),abs(T_tube_bulk-T_shell_bulk),abs(T_tube_bulk-T_shell_bulk)]"
            ),
            "local_residual_absolute_tolerance": (
                "per-support machine-roundoff bound G_ref*ulp(T_ref)+ulp(Q_scale)"
            ),
            "local_residual_relative_tolerance": "NOT_USED",
            "zero_duty_policy": (
                "exact equal bulk temperature; q=0; both walls at common bulk T; "
                "solver not invoked; no epsilon"
            ),
            "zero_duty_nonlinear_solver_required": False,
            "jacobian": (
                "2-point real finite difference; complex step forbidden for current callbacks"
            ),
            "diff_step": SELECTED_PROFILE["diff_step"],
            "max_nfev": SELECTED_PROFILE["max_nfev"],
            "tr_solver": SELECTED_PROFILE["tr_solver"],
            "tr_options": SELECTED_PROFILE["tr_options"],
            "f_scale": SELECTED_PROFILE["f_scale"],
            "jac_sparsity": SELECTED_PROFILE["jac_sparsity"],
            "max_nfev_is_convergence_proof": False,
            "residual_callback_cap": residual_callback_cap(
                cast(int, SELECTED_PROFILE["max_nfev"]),
                cast(str, SELECTED_PROFILE["jacobian"]),
            ),
            "custom_stagnation_detector_enabled": False,
            "custom_oscillation_detector_enabled": False,
            "wall_temperature_iteration_tolerance_applicable": False,
            "property_coupling_tolerance_applicable": False,
            "root_interval_tolerance_applicable": False,
            "solver_success_is_engineering_acceptance": False,
            "property_model_form_and_mesh_errors_inside_solver_tolerance": False,
            "discretization_error_delegated_to_mesh_qualification": True,
            "mesh_study_performed": False,
            "production_solver_execution_authorized": False,
        },
        "iteration_root_error_observed_envelope": root_error,
        "serialization_quantization": result_matrix["serialization_quantization"],
        "non_mesh_error_budget": {
            "components": ["ITERATION_ROOT_ERROR", "SERIALIZATION_QUANTIZATION_ERROR"],
            "combination_rule": "COMPONENTWISE_LINEAR_SUM_OF_COMPONENT_BOUNDS",
            "basis": (
                "worst_observed absolute oracle error envelope on fixed test matrix plus "
                "canonical roundtrip error envelope"
            ),
            "iteration_root_error": root_error,
            "serialization_error_W": 0.0,
            "serialization_error_K": 0.0,
            "combined_q_hc_observed_envelope_W": root_error["q_hc_max_absolute_error_W"],
            "combined_T_wall_inner_observed_envelope_K": root_error[
                "T_wall_inner_max_absolute_error_K"
            ],
            "combined_T_wall_outer_observed_envelope_K": root_error[
                "T_wall_outer_max_absolute_error_K"
            ],
            "not_included": [
                "PROPERTY_FORMULATION_ERROR",
                "CORRELATION_MODEL_FORM_ERROR",
                "DISCRETIZATION_ERROR",
                "REFERENCE_DATA_ERROR",
                "experimental uncertainty",
            ],
            "not_a_universal_production_error_bound": True,
        },
        "resource_cap_sensitivity": cap_stats,
        "canonical_hash": "",
    }
    result["canonical_hash"] = canonical_sha256(result)
    return result


def main() -> int:
    result = full_experiment()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
