"""Deterministic R92A numerical-coverage runner; emits JSON only to stdout.

The runner uses synthetic numerical fixtures, reviewed-scope HEOS water
properties, and the frozen three-residual R88 equations. It does not import
the production exchanger solver, write files, use randomness, or access the
network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
LOCAL_STATE_PRESSURE_PA = 101325.0
RE_TUBE = 100000.0
RE_MIN = 3000.0
RE_MAX = 5000000.0
PR_MIN = 0.5
PR_MAX = 2000.0
PR_RATIO_MIN = 0.05
PR_RATIO_MAX = 20.0
TUBE_EXPONENT = 0.11
SHELL_EXPONENT = 0.14
EPSILON = float(np.finfo(float).eps)
VARIABLES = ("q_hc_W", "T_wall_inner_K", "T_wall_outer_K")

R92_PROFILE: dict[str, Any] = {
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
    """Typed failure for an invalid numerical trial or fixture."""

    def __init__(self, failure_class: str, detail: str) -> None:
        super().__init__(detail)
        self.failure_class = failure_class
        self.detail = detail


@dataclass(frozen=True)
class Fixture:
    case_id: str
    group: str
    tube_bulk_K: float
    shell_bulk_K: float
    s_ts: int
    area_i_m2: float
    area_o_m2: float
    h_i_base_W_m2K: float
    h_o_base_W_m2K: float
    wall_resistance_K_W: float
    shell_jmu_active: bool
    resistance_class: str
    pressure_Pa: float = LOCAL_STATE_PRESSURE_PA
    reynolds: float = RE_TUBE

    @property
    def delta_t_K(self) -> float:
        return self.tube_bulk_K - self.shell_bulk_K

    @property
    def g_i_base_W_K(self) -> float:
        return self.h_i_base_W_m2K * self.area_i_m2

    @property
    def g_o_base_W_K(self) -> float:
        return self.h_o_base_W_m2K * self.area_o_m2


def make_fixture(
    case_id: str,
    group: str,
    tube_bulk_K: float,
    shell_bulk_K: float,
    s_ts: int,
    resistance_class: str,
    *,
    shell_jmu_active: bool,
) -> Fixture:
    resistance_map = {
        "TUBE_FILM_DOMINANT": (0.90, 0.05, 0.05),
        "WALL_DOMINANT": (0.05, 0.90, 0.05),
        "SHELL_FILM_DOMINANT": (0.05, 0.05, 0.90),
        "BALANCED": (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
    }
    r_i, r_w, r_o = resistance_map[resistance_class]
    area_i = 0.05
    area_o = 0.05
    return Fixture(
        case_id=case_id,
        group=group,
        tube_bulk_K=tube_bulk_K,
        shell_bulk_K=shell_bulk_K,
        s_ts=s_ts,
        area_i_m2=area_i,
        area_o_m2=area_o,
        h_i_base_W_m2K=1.0 / (r_i * area_i),
        h_o_base_W_m2K=1.0 / (r_o * area_o),
        wall_resistance_K_W=r_w,
        shell_jmu_active=shell_jmu_active,
        resistance_class=resistance_class,
    )


def fixtures() -> list[Fixture]:
    balanced = "BALANCED"
    base_cases = [
        ("C01_TUBE_C3_TUBE_HOT", "TUBE_C3_ONLY", 299.60, 298.60, 1),
        ("C02_TUBE_C3_SHELL_HOT", "TUBE_C3_ONLY", 298.60, 299.60, -1),
        ("C03_TUBE_C3_NEAR_ZERO", "TUBE_C3_ONLY", 299.2500, 299.2499, 1),
        ("C04_TUBE_C3_NEGATIVE_Q", "TUBE_C3_ONLY", 298.60, 299.60, 1),
        ("D01_DUAL_ACTIVE_TUBE_HOT", "DUAL_ACTIVE", 299.60, 298.60, 1),
        ("D02_DUAL_ACTIVE_SHELL_HOT", "DUAL_ACTIVE", 298.60, 299.60, -1),
        ("D03_DUAL_ACTIVE_NEAR_ZERO", "DUAL_ACTIVE", 299.2500, 299.2499, 1),
        ("D04_DUAL_ACTIVE_NEGATIVE_Q", "DUAL_ACTIVE", 298.60, 299.60, 1),
    ]
    result = [
        make_fixture(
            case_id,
            group,
            tube,
            shell,
            sign,
            balanced,
            shell_jmu_active=group == "DUAL_ACTIVE",
        )
        for case_id, group, tube, shell, sign in base_cases
    ]
    resistance_cases = (
        ("TUBE_FILM_DOMINANT", "TUBE_FILM_DOMINANT"),
        ("WALL_DOMINANT", "WALL_DOMINANT"),
        ("SHELL_FILM_DOMINANT", "SHELL_FILM_DOMINANT"),
        ("BALANCED", "BALANCED"),
    )
    for index, (suffix, resistance) in enumerate(resistance_cases, start=5):
        result.append(
            make_fixture(
                f"C{index:02d}_TUBE_C3_{suffix}",
                "TUBE_C3_ONLY",
                299.60,
                298.60,
                1,
                resistance,
                shell_jmu_active=False,
            )
        )
    for index, (suffix, resistance) in enumerate(resistance_cases, start=5):
        result.append(
            make_fixture(
                f"D{index:02d}_DUAL_ACTIVE_{suffix}",
                "DUAL_ACTIVE",
                299.60,
                298.60,
                1,
                resistance,
                shell_jmu_active=True,
            )
        )
    return result


def validate_tp(temperature_K: float, pressure_Pa: float) -> None:
    if not math.isfinite(temperature_K) or not math.isfinite(pressure_Pa):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite property state")
    if not T_MIN_K <= temperature_K <= T_MAX_K:
        raise NumericalFailure("TRIAL_DOMAIN_EXCURSION", "T outside reviewed water profile")
    if not P_MIN_PA <= pressure_Pa <= P_MAX_PA:
        raise NumericalFailure("TRIAL_DOMAIN_EXCURSION", "P outside reviewed water profile")


def water_properties(temperature_K: float, pressure_Pa: float) -> dict[str, float]:
    validate_tp(temperature_K, pressure_Pa)
    try:
        mu = float(PropsSI("V", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
        cp = float(PropsSI("C", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
        conductivity = float(PropsSI("L", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
    except Exception as exc:
        raise NumericalFailure("PROPERTY_EVALUATION_FAILURE", type(exc).__name__) from exc
    if not all(math.isfinite(value) and value > 0.0 for value in (mu, cp, conductivity)):
        raise NumericalFailure(
            "PROPERTY_EVALUATION_FAILURE",
            "nonpositive/nonfinite water property",
        )
    pr = cp * mu / conductivity
    if not PR_MIN <= pr <= PR_MAX:
        raise NumericalFailure("CORRELATION_DOMAIN_VIOLATION", "Pr outside reviewed C3 range")
    return {"mu_Pa_s": mu, "cp_J_kgK": cp, "k_W_mK": conductivity, "Pr": pr}


def tube_c3_factor(fixture: Fixture, wall_inner_K: float) -> tuple[float, dict[str, float]]:
    if not RE_MIN < fixture.reynolds < RE_MAX:
        raise NumericalFailure("CORRELATION_DOMAIN_VIOLATION", "Re outside strict C3 domain")
    bulk = water_properties(fixture.tube_bulk_K, fixture.pressure_Pa)
    wall = water_properties(wall_inner_K, fixture.pressure_Pa)
    ratio = bulk["Pr"] / wall["Pr"]
    if not PR_RATIO_MIN <= ratio <= PR_RATIO_MAX:
        raise NumericalFailure("CORRELATION_DOMAIN_VIOLATION", "Pr_bulk/Pr_wall outside C3 scope")
    factor = ratio**TUBE_EXPONENT
    return factor, {"Pr_bulk": bulk["Pr"], "Pr_wall": wall["Pr"], "Pr_ratio": ratio}


def h_i(fixture: Fixture, wall_inner_K: float) -> tuple[float, dict[str, float]]:
    factor, properties = tube_c3_factor(fixture, wall_inner_K)
    value = fixture.h_i_base_W_m2K * factor
    if not math.isfinite(value) or value <= 0.0:
        raise NumericalFailure("CORRELATION_EVALUATION_FAILURE", "invalid tube HTC")
    return value, properties


def shell_jmu(fixture: Fixture, wall_outer_K: float) -> tuple[float, dict[str, float]]:
    bulk = water_properties(fixture.shell_bulk_K, fixture.pressure_Pa)
    wall = water_properties(wall_outer_K, fixture.pressure_Pa)
    ratio = bulk["mu_Pa_s"] / wall["mu_Pa_s"]
    value = ratio**SHELL_EXPONENT
    if not math.isfinite(value) or value <= 0.0:
        raise NumericalFailure("CORRELATION_EVALUATION_FAILURE", "invalid shell J_mu")
    return value, {"mu_bulk_Pa_s": bulk["mu_Pa_s"], "mu_wall_Pa_s": wall["mu_Pa_s"]}


def h_o(fixture: Fixture, wall_outer_K: float) -> tuple[float, dict[str, Any]]:
    properties: dict[str, Any]
    if fixture.shell_jmu_active:
        factor, properties = shell_jmu(fixture, wall_outer_K)
    else:
        factor, properties = 1.0, {"J_mu": "NEUTRAL_CONSTANT_FOR_ISOLATION"}
    value = fixture.h_o_base_W_m2K * factor
    if not math.isfinite(value) or value <= 0.0:
        raise NumericalFailure("CORRELATION_EVALUATION_FAILURE", "invalid shell HTC")
    return value, {"J_mu": factor, **properties}


def evaluate(fixture: Fixture, wall_inner_K: float, wall_outer_K: float) -> dict[str, Any]:
    if not math.isfinite(wall_inner_K) or not math.isfinite(wall_outer_K):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite wall temperature")
    validate_tp(wall_inner_K, fixture.pressure_Pa)
    validate_tp(wall_outer_K, fixture.pressure_Pa)
    if not math.isfinite(fixture.wall_resistance_K_W) or fixture.wall_resistance_K_W <= 0.0:
        raise NumericalFailure("SINGULAR_OR_INVALID_RESISTANCE", "wall resistance must be positive")
    hi, tube_props = h_i(fixture, wall_inner_K)
    ho, shell_props = h_o(fixture, wall_outer_K)
    gi = hi * fixture.area_i_m2
    go = ho * fixture.area_o_m2
    gw = 1.0 / fixture.wall_resistance_K_W
    q_i = gi * (fixture.tube_bulk_K - wall_inner_K)
    q_wall = gw * (wall_inner_K - wall_outer_K)
    q_o = go * (wall_outer_K - fixture.shell_bulk_K)
    if not all(math.isfinite(value) for value in (q_i, q_wall, q_o)):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite heat-flow callback")
    return {
        "h_i_W_m2K": hi,
        "h_o_W_m2K": ho,
        "G_i_W_K": gi,
        "G_wall_W_K": gw,
        "G_o_W_K": go,
        "q_i_W": q_i,
        "q_wall_W": q_wall,
        "q_o_W": q_o,
        "tube_properties": tube_props,
        "shell_properties": shell_props,
    }


def residual_W(fixture: Fixture, x: np.ndarray) -> np.ndarray:
    q_hc, wall_inner, wall_outer = (float(value) for value in x)
    if not math.isfinite(q_hc):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite signed duty unknown")
    states = evaluate(fixture, wall_inner, wall_outer)
    q_ts = fixture.s_ts * q_hc
    values = np.asarray(
        [
            q_ts - states["q_i_W"],
            q_ts - states["q_wall_W"],
            q_ts - states["q_o_W"],
        ],
        dtype=float,
    )
    if not np.all(np.isfinite(values)):
        raise NumericalFailure("NONFINITE_TRIAL", "nonfinite physical residual")
    return values


def direct_seed(fixture: Fixture) -> np.ndarray:
    if fixture.wall_resistance_K_W <= 0.0:
        raise NumericalFailure("SINGULAR_OR_INVALID_RESISTANCE", "invalid seed resistance")
    ri = 1.0 / fixture.g_i_base_W_K
    ro = 1.0 / fixture.g_o_base_W_K
    q_ts = fixture.delta_t_K / (ri + fixture.wall_resistance_K_W + ro)
    wall_inner = fixture.tube_bulk_K - q_ts * ri
    wall_outer = fixture.shell_bulk_K + q_ts * ro
    return np.asarray([fixture.s_ts * q_ts, wall_inner, wall_outer], dtype=float)


def variable_scale(fixture: Fixture, x0: np.ndarray, policy: str) -> Any:
    if policy == "ONE":
        return 1.0
    if policy == "JACOBIAN":
        return "jac"
    if policy == "INITIALIZATION_DERIVED":
        duty_scale = abs(float(x0[0]))
        delta_t = abs(fixture.delta_t_K)
        if duty_scale <= 0.0 or delta_t <= 0.0:
            raise NumericalFailure("INITIALIZATION_FAILURE", "exact zero uses zero branch")
        return [duty_scale, delta_t, delta_t]
    raise ValueError(f"unsupported x_scale policy: {policy}")


def residual_scale_W(fixture: Fixture, x0: np.ndarray, policy: str) -> float:
    seed_duty = abs(fixture.s_ts * float(x0[0]))
    if seed_duty <= 0.0:
        raise NumericalFailure("ZERO_DUTY_EXACT_BRANCH", "zero duty bypasses scaled solve")
    if policy == "SEED_DUTY":
        return seed_duty
    seed_eval = evaluate(fixture, float(x0[1]), float(x0[2]))
    active_g = max(
        float(seed_eval["G_i_W_K"]),
        float(seed_eval["G_wall_W_K"]),
        float(seed_eval["G_o_W_K"]),
    )
    if policy == "ACTIVE_CONDUCTANCE_TIMES_DELTA_T":
        return active_g * abs(fixture.delta_t_K)
    if policy == "SEED_DUTY_WITH_ULP_FLOOR":
        tref = max(abs(fixture.tube_bulk_K), abs(fixture.shell_bulk_K))
        return max(seed_duty, active_g * math.ulp(tref))
    raise ValueError(f"unsupported residual scaling policy: {policy}")


def oracle(fixture: Fixture) -> dict[str, Any]:
    grid = np.linspace(T_MIN_K, T_MAX_K, 4097, dtype=float)
    valid_rows: list[tuple[int, float, float]] = []
    for index, candidate_outer in enumerate(grid):
        wall_outer = float(candidate_outer)
        try:
            outer_eval, _ = h_o(fixture, wall_outer)
            q_o = outer_eval * fixture.area_o_m2 * (wall_outer - fixture.shell_bulk_K)
            wall_inner = wall_outer + q_o * fixture.wall_resistance_K_W
            if not T_MIN_K <= wall_inner <= T_MAX_K:
                continue
            inner_eval, _ = h_i(fixture, wall_inner)
            q_i = inner_eval * fixture.area_i_m2 * (fixture.tube_bulk_K - wall_inner)
        except NumericalFailure:
            continue
        value = q_o - q_i
        if math.isfinite(value):
            valid_rows.append((index, wall_outer, value))
    if len(valid_rows) < 3:
        raise NumericalFailure("INDEPENDENT_ORACLE_INVALID", "insufficient valid scalar grid")
    indices = [row[0] for row in valid_rows]
    if any(right - left != 1 for left, right in zip(indices, indices[1:], strict=False)):
        raise NumericalFailure(
            "INDEPENDENT_ORACLE_INVALID",
            "valid scalar domain is not contiguous",
        )
    values = [row[2] for row in valid_rows]
    differences = [right - left for left, right in zip(values, values[1:], strict=False)]
    monotone_up = all(value > 0.0 for value in differences)
    monotone_down = all(value < 0.0 for value in differences)
    if not (monotone_up or monotone_down):
        raise NumericalFailure("INDEPENDENT_ORACLE_INVALID", "scalar grid is not strictly monotone")
    bracket: tuple[float, float] | None = None
    for left, right in zip(valid_rows, valid_rows[1:], strict=False):
        if left[2] * right[2] < 0.0:
            bracket = (left[1], right[1])
            break
    if bracket is None:
        raise NumericalFailure("INDEPENDENT_ORACLE_INVALID", "strict sign-changing bracket absent")

    def scalar_residual(wall_outer: float) -> float:
        outer_eval, _ = h_o(fixture, wall_outer)
        q_o = outer_eval * fixture.area_o_m2 * (wall_outer - fixture.shell_bulk_K)
        wall_inner = wall_outer + q_o * fixture.wall_resistance_K_W
        validate_tp(wall_inner, fixture.pressure_Pa)
        inner_eval, _ = h_i(fixture, wall_inner)
        q_i = inner_eval * fixture.area_i_m2 * (fixture.tube_bulk_K - wall_inner)
        return q_o - q_i

    midpoint = 0.5 * (bracket[0] + bracket[1])
    root, details = brentq(
        scalar_residual,
        bracket[0],
        bracket[1],
        xtol=math.ulp(midpoint),
        rtol=4.0 * EPSILON,
        maxiter=256,
        full_output=True,
        disp=True,
    )
    outer_eval, _ = h_o(fixture, float(root))
    q_ts = outer_eval * fixture.area_o_m2 * (float(root) - fixture.shell_bulk_K)
    wall_inner = float(root) + q_ts * fixture.wall_resistance_K_W
    validate_tp(wall_inner, fixture.pressure_Pa)
    return {
        "q_hc_W": fixture.s_ts * q_ts,
        "q_ts_W": q_ts,
        "T_wall_inner_K": wall_inner,
        "T_wall_outer_K": float(root),
        "method": "BRENTQ_VALIDATION_ORACLE_ONLY",
        "scope": "THIS_NUMERICAL_FIXTURE_ONLY",
        "production_scalar_reduction_selected": False,
        "grid_count": len(grid),
        "valid_grid_count": len(valid_rows),
        "strict_monotonicity": "INCREASING" if monotone_up else "DECREASING",
        "strict_sign_change": True,
        "bracket_K": list(bracket),
        "bracket_endpoint_residual_W": [
            scalar_residual(bracket[0]),
            scalar_residual(bracket[1]),
        ],
        "brentq_converged": bool(details.converged),
        "brentq_iterations": int(details.iterations),
        "brentq_function_calls": int(details.function_calls),
        "brentq_xtol_K": math.ulp(midpoint),
        "brentq_rtol": 4.0 * EPSILON,
        "max_iterations": 256,
    }


def roundoff_candidates(
    fixture: Fixture, x: np.ndarray, scale_W: float, c_round: float = 1.0
) -> dict[str, Any]:
    q_hc, wall_inner, wall_outer = (float(value) for value in x)
    q_ts = fixture.s_ts * q_hc
    states = evaluate(fixture, wall_inner, wall_outer)
    tref = max(abs(fixture.tube_bulk_K), abs(fixture.shell_bulk_K))
    gi_base = fixture.g_i_base_W_K
    gw = states["G_wall_W_K"]
    go_base = fixture.g_o_base_W_K
    legacy_g = max(gi_base, gw, go_base)
    active_g = max(states["G_i_W_K"], gw, states["G_o_W_K"])
    bound_a = legacy_g * math.ulp(tref) + math.ulp(scale_W)
    bound_b = active_g * math.ulp(tref) + math.ulp(scale_W)

    def gamma(count: int) -> float:
        return count * EPSILON / (1.0 - count * EPSILON)

    qi = states["q_i_W"]
    qw = states["q_wall_W"]
    qo = states["q_o_W"]
    gi = states["G_i_W_K"]
    residuals = residual_W(fixture, x)
    bi = c_round * (
        math.ulp(q_ts)
        + math.ulp(qi)
        + gi
        * (
            math.ulp(fixture.tube_bulk_K)
            + math.ulp(wall_inner)
            + math.ulp(fixture.tube_bulk_K - wall_inner)
        )
        + gamma(2) * abs(qi)
    )
    bw = c_round * (
        math.ulp(q_ts)
        + math.ulp(qw)
        + gw * (math.ulp(wall_inner) + math.ulp(wall_outer) + math.ulp(wall_inner - wall_outer))
        + gamma(1) * abs(qw)
    )
    bo = c_round * (
        math.ulp(q_ts)
        + math.ulp(qo)
        + states["G_o_W_K"]
        * (
            math.ulp(wall_outer)
            + math.ulp(fixture.shell_bulk_K)
            + math.ulp(wall_outer - fixture.shell_bulk_K)
        )
        + gamma(2) * abs(qo)
    )
    bounds_c = [bi, bw, bo]
    return {
        "candidate_a_r92_legacy_bound_W": bound_a,
        "candidate_b_active_conductance_bound_W": bound_b,
        "candidate_c_residual_specific_bounds_W": bounds_c,
        "candidate_c_round_multiplier": c_round,
        "candidate_a_pass": float(np.max(np.abs(residuals))) <= bound_a,
        "candidate_b_pass": float(np.max(np.abs(residuals))) <= bound_b,
        "candidate_c_pass": all(
            abs(float(residual)) <= bound
            for residual, bound in zip(residuals, bounds_c, strict=True)
        ),
        "candidate_c_not_a_formal_float_theorem": True,
        "actual_evaluated_heat_flow_terms_W": {
            "q_ts": q_ts,
            "q_i": qi,
            "q_wall": qw,
            "q_o": qo,
        },
        "actual_active_conductances_W_K": {
            "G_i": gi,
            "G_wall": gw,
            "G_o": states["G_o_W_K"],
        },
    }


def callback_limit(max_nfev: int, jacobian: str) -> int:
    stencil = 3 if jacobian == "2-point" else 6
    return max_nfev * (1 + stencil)


def solve(
    fixture: Fixture,
    expected: dict[str, Any],
    profile: dict[str, Any],
    *,
    residual_scale_policy: str = "SEED_DUTY",
    c_round: float = 1.0,
) -> dict[str, Any]:
    try:
        x0 = direct_seed(fixture)
        scale_W = residual_scale_W(fixture, x0, residual_scale_policy)
        low = np.asarray([-np.inf, T_MIN_K, T_MIN_K], dtype=float)
        high = np.asarray([np.inf, T_MAX_K, T_MAX_K], dtype=float)
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
            "bounds": (low, high),
            "tr_solver": profile["tr_solver"],
            "tr_options": profile["tr_options"],
            "f_scale": profile["f_scale"],
            "jac_sparsity": profile["jac_sparsity"],
        }
        count = 0
        cap = callback_limit(int(profile["max_nfev"]), str(profile["jacobian"]))

        def callback(values: np.ndarray) -> np.ndarray:
            nonlocal count
            count += 1
            if count > cap:
                raise NumericalFailure("SOLVER_RESOURCE_EXHAUSTION", "callback cap reached")
            return residual_W(fixture, values) / scale_W

        result = least_squares(callback, x0, **options)
        x = np.asarray(result.x, dtype=float)
        residuals = residual_W(fixture, x)
        bounds = roundoff_candidates(fixture, x, scale_W, c_round)
        q, wall_i, wall_o = (float(value) for value in x)
        return {
            "case_id": fixture.case_id,
            "group": fixture.group,
            "resistance_class": fixture.resistance_class,
            "initialization": "DIRECT_ALGEBRAIC_NEUTRAL_BASE_SEED",
            "initial_seed": [float(value) for value in x0],
            "solver_method": "SCIPY_LEAST_SQUARES_TRF_LINEAR_LOSS",
            "profile": profile,
            "residual_scale_policy": residual_scale_policy,
            "residual_scale_W": scale_W,
            "solution": {
                "q_hc_W": q,
                "q_ts_W": fixture.s_ts * q,
                "T_wall_inner_K": wall_i,
                "T_wall_outer_K": wall_o,
            },
            "oracle": expected,
            "errors": {
                "q_hc_absolute_W": abs(q - float(expected["q_hc_W"])),
                "q_hc_relative": (
                    None
                    if "NEAR_ZERO" in fixture.case_id
                    else abs(q - float(expected["q_hc_W"])) / abs(float(expected["q_hc_W"]))
                ),
                "T_wall_inner_absolute_K": abs(wall_i - float(expected["T_wall_inner_K"])),
                "T_wall_outer_absolute_K": abs(wall_o - float(expected["T_wall_outer_K"])),
            },
            "physical_residuals_W": [float(value) for value in residuals],
            "scaled_residual_inf_norm": float(np.max(np.abs(residuals))) / scale_W,
            "solver_success": bool(result.success),
            "solver_termination_code": int(result.status),
            "solver_message": str(result.message),
            "nfev": int(result.nfev),
            "njev": int(result.njev) if result.njev is not None else None,
            "residual_callback_count_including_fd": count,
            "residual_callback_cap": cap,
            "domain_valid": all(T_MIN_K <= value <= T_MAX_K for value in (wall_i, wall_o)),
            "negative_q_hc": q < 0.0,
            "negative_q_numerically_allowed": True,
            "roundoff_candidates": bounds,
            "engineering_acceptance": False,
            "partial_result_authoritative": False,
        }
    except NumericalFailure as exc:
        return {
            "case_id": fixture.case_id,
            "outcome": "TYPED_FAILURE",
            "failure_class": exc.failure_class,
            "detail": exc.detail,
            "partial_result_authoritative": False,
        }


def fixture_record(fixture: Fixture) -> dict[str, Any]:
    return {
        **asdict(fixture),
        "physical_support_id": f"NUMERICAL_KERNEL_FIXTURE:{fixture.case_id}",
        "bulk_state_origin": "DETERMINISTIC_FIXTURE_STATE",
        "pressure_origin": "LOCATED_LOCAL_STATE_INPUT;NOT_A_PRESSURE_RULE",
        "material_origin": "SYNTHETIC_NUMERICAL_FIXTURE_PARAMETER",
        "geometry_origin": "SYNTHETIC_NUMERICAL_FIXTURE_PARAMETER",
        "tube_reynolds": fixture.reynolds,
        "tube_c3_wall_correction_active": True,
        "shell_jmu_wall_correction_active": fixture.shell_jmu_active,
        "fouling": "CLEAN_SURFACE_ONLY",
    }


def run_matrix(
    fs: list[Fixture],
    oracles: dict[str, dict[str, Any]],
    profile: dict[str, Any],
    *,
    residual_scale_policy: str = "SEED_DUTY",
    c_round: float = 1.0,
) -> list[dict[str, Any]]:
    return [
        solve(
            item,
            oracles[item.case_id],
            profile,
            residual_scale_policy=residual_scale_policy,
            c_round=c_round,
        )
        for item in fs
    ]


def accepted(record: dict[str, Any]) -> bool:
    candidates = record.get("roundoff_candidates", {})
    return bool(
        record.get("solver_success")
        and record.get("domain_valid")
        and candidates.get("candidate_c_pass")
        and record.get("outcome") is None
    )


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    success = [record for record in records if record.get("solver_success")]
    nfev = sorted(int(record["nfev"]) for record in success)
    callbacks = [int(record["residual_callback_count_including_fd"]) for record in success]
    q_errors = [float(record["errors"]["q_hc_absolute_W"]) for record in success]
    tw_errors = [
        max(
            float(record["errors"]["T_wall_inner_absolute_K"]),
            float(record["errors"]["T_wall_outer_absolute_K"]),
        )
        for record in success
    ]
    p95 = nfev[max(0, math.ceil(0.95 * len(nfev)) - 1)] if nfev else None
    return {
        "fixture_count": len(records),
        "solver_success_count": len(success),
        "candidate_c_residual_accepted_count": sum(accepted(record) for record in records),
        "max_nfev_observed": max(nfev, default=None),
        "p95_nfev_observed": p95,
        "nfev_distribution": nfev,
        "max_njev_observed": max(
            (int(record.get("njev") or 0) for record in success), default=None
        ),
        "max_residual_callback_count": max(callbacks, default=None),
        "max_q_oracle_error_W": max(q_errors, default=None),
        "max_wall_temperature_oracle_error_K": max(tw_errors, default=None),
        "max_scaled_residual_inf_norm": max(
            (float(record["scaled_residual_inf_norm"]) for record in success), default=None
        ),
        "failure_classes": sorted(
            {
                str(record.get("failure_class"))
                for record in records
                if record.get("failure_class") not in (None, "NONE")
            }
        ),
        "all_results_non_authoritative": all(
            record.get("partial_result_authoritative") is False for record in records
        ),
    }


def profile_sensitivity(
    fs: list[Fixture],
    oracles: dict[str, dict[str, Any]],
    c_round: float,
) -> dict[str, Any]:
    axes: dict[str, list[Any]] = {
        "ftol": [1e-6, 1e-8, 1e-10, 1e-12],
        "xtol": [1e-6, 1e-8, 1e-10, 1e-12],
        "gtol": [1e-8, 1e-10, 1e-12, 1e-13],
        "jacobian": ["2-point", "3-point"],
        "diff_step": [1e-4, 1e-5, 1e-6, 1e-7],
        "x_scale": ["ONE", "JACOBIAN", "INITIALIZATION_DERIVED"],
        "max_nfev": [6, 8, 12, 16],
    }
    reports: dict[str, Any] = {}
    for axis, values in axes.items():
        rows = []
        for value in values:
            profile = {**R92_PROFILE, axis: value}
            records = run_matrix(fs, oracles, profile, c_round=c_round)
            row = summarize(records)
            row["value"] = value
            row["all_fixtures_accepted"] = row["candidate_c_residual_accepted_count"] == len(fs)
            rows.append(row)
        reports[axis] = rows
    scaling_rows = []
    for value in (
        "SEED_DUTY",
        "ACTIVE_CONDUCTANCE_TIMES_DELTA_T",
        "SEED_DUTY_WITH_ULP_FLOOR",
    ):
        rows = run_matrix(
            fs,
            oracles,
            R92_PROFILE,
            residual_scale_policy=value,
            c_round=c_round,
        )
        row = summarize(rows)
        row["value"] = value
        row["all_fixtures_accepted"] = row["candidate_c_residual_accepted_count"] == len(fs)
        scaling_rows.append(row)
    reports["residual_scaling"] = scaling_rows
    joint_rows = []
    for value in (1e-6, 1e-8, 1e-10, 1e-12):
        profile = {**R92_PROFILE, "ftol": value, "xtol": value, "gtol": value}
        rows = run_matrix(fs, oracles, profile, c_round=c_round)
        report = summarize(rows)
        report.update(
            {
                "ftol": value,
                "xtol": value,
                "gtol": value,
                "all_fixtures_accepted": report["candidate_c_residual_accepted_count"] == len(fs),
            }
        )
        joint_rows.append(report)
    reports["joint_tolerance_sweep"] = joint_rows
    return reports


def residual_rule_sensitivity(
    records: list[dict[str, Any]], multipliers: tuple[float, ...]
) -> dict[str, Any]:
    rows = []
    for multiplier in multipliers:
        passes_a = 0
        passes_b = 0
        passes_c = 0
        for record in records:
            candidate = record["roundoff_candidates"]
            residuals = [abs(float(value)) for value in record["physical_residuals_W"]]
            passes_a += int(
                max(residuals) <= multiplier * candidate["candidate_a_r92_legacy_bound_W"]
            )
            passes_b += int(
                max(residuals) <= multiplier * candidate["candidate_b_active_conductance_bound_W"]
            )
            passes_c += int(
                all(
                    value <= multiplier * bound
                    for value, bound in zip(
                        residuals, candidate["candidate_c_residual_specific_bounds_W"], strict=True
                    )
                )
            )
        rows.append(
            {
                "multiplier": multiplier,
                "candidate_a_r92_legacy_pass_count": passes_a,
                "candidate_b_active_conductance_pass_count": passes_b,
                "candidate_c_residual_specific_pass_count": passes_c,
                "fixture_count": len(records),
                "authority_class": "METHOD_SENSITIVITY_DERIVED_PROJECT_POLICY",
            }
        )
    return {
        "candidate_a": "R92 base-conductance rule; replayed, not generalized",
        "candidate_b": "active evaluated conductances at the returned state",
        "candidate_c": (
            "per-residual evaluated heat-flow ULP/operation terms; empirical project "
            "acceptance rule, not a formal IEEE-754 theorem"
        ),
        "candidate_c_multiplier_sensitivity": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    fs = fixtures()
    oracles = {item.case_id: oracle(item) for item in fs}
    baseline_records_c1 = run_matrix(fs, oracles, R92_PROFILE, c_round=1.0)
    multiplier_candidates = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
    chosen_multiplier: float | None = None
    for multiplier in multiplier_candidates:
        trial = run_matrix(fs, oracles, R92_PROFILE, c_round=multiplier)
        if summarize(trial)["candidate_c_residual_accepted_count"] == len(fs):
            chosen_multiplier = multiplier
            break
    if chosen_multiplier is None:
        chosen_multiplier = multiplier_candidates[-1]
    selected_records = run_matrix(fs, oracles, R92_PROFILE, c_round=chosen_multiplier)
    repeated_records = run_matrix(fs, oracles, R92_PROFILE, c_round=chosen_multiplier)
    selected_bytes = canonical_json_bytes({"records": selected_records})
    repeated_bytes = canonical_json_bytes({"records": repeated_records})
    max_observed_nfev = int(summarize(selected_records)["max_nfev_observed"] or 0)
    selected_cap_rows = []
    for cap_value in (6, 8, 12, 16):
        profile = {**R92_PROFILE, "max_nfev": cap_value}
        rows = run_matrix(fs, oracles, profile, c_round=chosen_multiplier)
        summary = summarize(rows)
        callback_cap = callback_limit(cap_value, str(profile["jacobian"]))
        summary.update(
            {
                "candidate_max_nfev": cap_value,
                "callback_cap": callback_cap,
                "callback_headroom": (
                    callback_cap - int(summary["max_residual_callback_count"] or 0)
                ),
                "evaluation_headroom": (cap_value - int(summary["max_nfev_observed"] or 0)),
                "direct_seed_all_pass": summary["candidate_c_residual_accepted_count"] == len(fs),
            }
        )
        selected_cap_rows.append(summary)
    cap_sensitivity_rows = profile_sensitivity(fs, oracles, chosen_multiplier)
    criterion_cap = math.ceil(1.5 * max_observed_nfev)
    eligible_caps = [
        row
        for row in selected_cap_rows
        if row["direct_seed_all_pass"]
        and row["evaluation_headroom"] >= 2
        and row["candidate_max_nfev"] >= criterion_cap
    ]
    selected_cap = min(
        (int(row["candidate_max_nfev"]) for row in eligible_caps),
        default=16,
    )
    selected_profile = {**R92_PROFILE, "max_nfev": selected_cap}
    final_records = run_matrix(fs, oracles, selected_profile, c_round=chosen_multiplier)
    final_summary = summarize(final_records)
    all_candidates = residual_rule_sensitivity(
        baseline_records_c1, (0.5, 1.0, 2.0, 4.0, 8.0, chosen_multiplier)
    )
    root_error = {
        "q_hc_max_absolute_error_W": max(
            float(record["errors"]["q_hc_absolute_W"]) for record in final_records
        ),
        "T_wall_inner_max_absolute_error_K": max(
            float(record["errors"]["T_wall_inner_absolute_K"]) for record in final_records
        ),
        "T_wall_outer_max_absolute_error_K": max(
            float(record["errors"]["T_wall_outer_absolute_K"]) for record in final_records
        ),
        "scope": "OBSERVED_ENVELOPE_ON_16_FIXED_SYNTHETIC_FIXTURES_NOT_UNIVERSAL",
    }
    numeric_outputs = [
        {"case_id": row["case_id"], **row["solution"], "residuals_W": row["physical_residuals_W"]}
        for row in final_records
    ]
    input_rows = [fixture_record(item) for item in fs]
    oracle_rows = [{"case_id": item.case_id, **oracles[item.case_id]} for item in fs]
    result: dict[str, Any] = {
        "schema_version": "task172.quantitative-numerical-profile-coverage-results.r92a",
        "task_id": (
            "TASK172_V0_7_QUANTITATIVE_NUMERICAL_PROFILE_COVERAGE_AND_ROUNDOFF_ROBUSTNESS_R92A"
        ),
        "runtime": {
            "python": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "scipy": scipy.__version__,
            "numpy": np.__version__,
            "coolprop": CoolProp.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "source_authorities_replayed": {
            "tube_c3_authority_id": "V07-T172-TUBE-WALL-CORRECTION-R1",
            "tube_factor": "(Pr_bulk/Pr_wall)^0.11",
            "tube_re_domain": "3000<Re<5000000",
            "tube_pr_bulk_wall_domain": "0.5<=Pr<=2000",
            "tube_ratio_domain": "0.05<=Pr_bulk/Pr_wall<=20",
            "shell_jmu_authority": "R89_R90_REVIEWED_AUTHORITY",
            "shell_factor": "(mu_bulk/mu_wall)^0.14",
            "property_profile": "V07-T172-WATER-PROPERTY-PROFILE-R2",
            "property_scope": (
                "PURE_ORDINARY_WATER;HEOS;DEF;STABLE_SINGLE_PHASE_LIQUID;"
                "T=298.15..300 K;P=100000..101325 Pa"
            ),
            "pressure_input_is_located_fixture_state_not_rule": True,
            "fouling_scope": "CLEAN_SURFACE_ONLY",
        },
        "fixture_counts": {
            "tube_c3_nonlinear_fixture_count": sum(item.group == "TUBE_C3_ONLY" for item in fs),
            "dual_active_nonlinear_fixture_count": sum(item.group == "DUAL_ACTIVE" for item in fs),
            "dynamic_range_stress_fixture_count": sum(
                item.case_id[:1] in ("C", "D") and item.case_id[1:3] in {"05", "06", "07", "08"}
                for item in fs
            ),
            "resistance_ratio_classes": [
                "TUBE_FILM_DOMINANT",
                "WALL_DOMINANT",
                "SHELL_FILM_DOMINANT",
                "BALANCED",
            ],
            "total_extended_nonlinear_fixture_count": len(fs),
        },
        "input_matrix": input_rows,
        "input_matrix_canonical_hash": canonical_sha256({"fixtures": input_rows}),
        "independent_oracles": oracle_rows,
        "r92_baseline_profile": R92_PROFILE,
        "selected_profile": selected_profile,
        "selected_profile_summary": final_summary,
        "selected_fixture_results": final_records,
        "selected_numeric_output_matrix_canonical_hash": canonical_sha256(
            {"numeric_outputs": numeric_outputs}
        ),
        "same_input_same_result_bytes": selected_bytes == repeated_bytes,
        "same_input_same_result_hash": hashlib.sha256(selected_bytes).hexdigest()
        == hashlib.sha256(repeated_bytes).hexdigest(),
        "selected_result_bytes_sha256": hashlib.sha256(selected_bytes).hexdigest(),
        "residual_acceptance": {
            "R92_ROUNDOFF_RULE_FIXTURE_VALIDATED": True,
            "R92_ROUNDOFF_RULE_UNIVERSAL_BOUND_PROVEN": False,
            "candidate_comparison": all_candidates,
            "selected_candidate": (
                "C_RESIDUAL_SPECIFIC_METHOD_SENSITIVITY_DERIVED_PROJECT_ACCEPTANCE_RULE"
            ),
            "selected_C_round": chosen_multiplier,
            "formal_floating_point_theorem_claimed": False,
            "bounds_per_residual_W": (
                final_records[0]["roundoff_candidates"]["candidate_c_residual_specific_bounds_W"]
                if final_records
                else []
            ),
            "selected_matrix_acceptance_count": final_summary[
                "candidate_c_residual_accepted_count"
            ],
            "selected_matrix_fixture_count": len(fs),
        },
        "resource_cap_requalification": {
            "direct_seed_must_pass_all": True,
            "perturbed_seed_is_production_requirement": False,
            "selection_criterion": (
                "smallest tested cap with all direct-seed fixtures accepted, at least two "
                "observed nfev of headroom, and cap >= ceil(1.5*observed worst nfev)"
            ),
            "observed_worst_nfev_before_cap_selection": max_observed_nfev,
            "ceil_1_5_times_observed_worst_nfev": criterion_cap,
            "tested_caps": selected_cap_rows,
            "selected_max_nfev": selected_cap,
            "selected_callback_cap": callback_limit(
                selected_cap, str(selected_profile["jacobian"])
            ),
            "max_nfev_is_convergence_proof": False,
        },
        "profile_sensitivity": cap_sensitivity_rows,
        "iteration_root_error_observed_envelope": root_error,
        "validation": {
            "all_scalar_oracles_have_valid_strict_brackets": all(
                row["strict_sign_change"] and row["brentq_converged"] for row in oracle_rows
            ),
            "all_scalar_oracles_monotonicity_audited": all(
                row["strict_monotonicity"] in ("INCREASING", "DECREASING") for row in oracle_rows
            ),
            "production_scalar_reduction_selected": False,
            "all_wall_states_in_reviewed_property_domain": all(
                record.get("domain_valid", False) for record in final_records
            ),
            "all_selected_direct_seed_fixtures_accepted": final_summary[
                "candidate_c_residual_accepted_count"
            ]
            == len(fs),
            "mesh_study_performed": False,
            "production_solver_execution_authorized": False,
            "engineering_case_created": False,
            "production_code_changed": False,
        },
        "canonical_hash": "",
    }
    result["canonical_hash"] = canonical_sha256(result)
    if args.summary_only:
        summary_result = {
            "runtime": result["runtime"],
            "fixture_counts": result["fixture_counts"],
            "selected_profile": result["selected_profile"],
            "selected_profile_summary": result["selected_profile_summary"],
            "selected_numeric_output_matrix_canonical_hash": result[
                "selected_numeric_output_matrix_canonical_hash"
            ],
            "same_input_same_result_bytes": result["same_input_same_result_bytes"],
            "same_input_same_result_hash": result["same_input_same_result_hash"],
            "canonical_hash": "",
        }
        summary_result["canonical_hash"] = canonical_sha256(summary_result)
        print(json.dumps(summary_result, sort_keys=True, indent=2, allow_nan=False))
    else:
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
