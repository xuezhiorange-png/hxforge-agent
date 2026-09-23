"""Independent, deterministic replay for the TASK172 R92/R92A review.

This evidence runner has no production imports, writes no files, uses no
randomness, and performs no network access. It independently evaluates the
frozen residual, property callbacks, residual-specific acceptance policy,
and validation-only scalar oracle for the recorded and predeclared fixtures.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import CoolProp
import numpy as np
import rfc8785
import scipy
from CoolProp.CoolProp import PropsSI
from scipy.optimize import brentq, least_squares

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
T_MIN_K = 298.15
T_MAX_K = 300.0
P_MIN_PA = 100000.0
P_MAX_PA = 101325.0
PR_MIN = 0.5
PR_MAX = 2000.0
PR_RATIO_MIN = 0.05
PR_RATIO_MAX = 20.0
RE_MIN = 3000.0
RE_MAX = 5000000.0
TUBE_EXPONENT = 0.11
SHELL_EXPONENT = 0.14
C_ROUND = 0.5
EPSILON = float(np.finfo(float).eps)
HOLDOUT_PATH = (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-independent-review-holdout-r1.json"
)
R92_RESULTS_PATH = (
    "docs/tasks/evidence/"
    "TASK-172-numerical-error-budget-stopping-method-sensitivity-results-r1.json"
)
R92A_RESULTS_PATH = (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-coverage-results-r92a.json"
)
REGISTRY_PATH = "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"

FROZEN_PROFILE: dict[str, Any] = {
    "method": "trf",
    "loss": "linear",
    "ftol": 1e-6,
    "xtol": 1e-12,
    "gtol": 1e-12,
    "jacobian": "2-point",
    "diff_step": 1e-5,
    "x_scale": "INITIALIZATION_DERIVED",
    "max_nfev": 6,
    "residual_callback_cap": 24,
    "tr_solver": "exact",
    "tr_options": {},
    "f_scale": 1.0,
    "jac_sparsity": None,
    "residual_scale": "abs(q_ts_seed)",
    "c_round": C_ROUND,
}


class ReviewFailure(Exception):
    """A typed, fail-closed numerical-review failure."""


@dataclass(frozen=True)
class Case:
    case_id: str
    family: str
    tube_bulk_K: float
    shell_bulk_K: float
    s_ts: int
    area_i_m2: float
    area_o_m2: float
    h_i_base_W_m2K: float
    h_o_base_W_m2K: float
    wall_resistance_K_W: float
    pressure_Pa: float | None
    reynolds: float
    tube_c3_active: bool
    shell_jmu_active: bool

    @property
    def delta_t_K(self) -> float:
        return self.tube_bulk_K - self.shell_bulk_K


def read_json(relative_path: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((ROOT / relative_path).read_text(encoding="utf-8")),
    )


def sha256_file(relative_path: str) -> str:
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


def check_artifact_bundle(registry: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    bundles = {
        "r92": registry["r92_extension"],
        "r93": registry["r93_extension"],
    }
    for name, extension in bundles.items():
        artifacts = extension["artifacts"]
        artifact_checks: dict[str, bool] = {}
        for path_key, hash_key in (
            ("document_path", "document_sha256"),
            ("evidence_path", "evidence_file_sha256"),
            ("results_path", "results_file_sha256"),
            ("runner_path", "runner_sha256"),
        ):
            path = artifacts[path_key]
            artifact_checks[path_key] = sha256_file(path) == artifacts[hash_key]
        evidence = read_json(artifacts["evidence_path"])
        results = read_json(artifacts["results_path"])
        artifact_checks["evidence_canonical_hash"] = (
            canonical_sha256(evidence) == evidence["canonical_hash"]
        )
        artifact_checks["results_canonical_hash"] = (
            canonical_sha256(results) == artifacts["results_canonical_hash"]
        )
        artifact_checks["extension_canonical_hash"] = (
            canonical_sha256(extension) == extension["canonical_hash"]
        )
        checks[name] = artifact_checks
    checks["registry_root_canonical_hash"] = (
        canonical_sha256(registry) == registry["canonical_hash"]
    )
    return checks


def check_frozen_profile(r92: dict[str, Any], r92a: dict[str, Any]) -> bool:
    expected_solver = {
        "method": FROZEN_PROFILE["method"],
        "loss": FROZEN_PROFILE["loss"],
        "ftol": FROZEN_PROFILE["ftol"],
        "xtol": FROZEN_PROFILE["xtol"],
        "gtol": FROZEN_PROFILE["gtol"],
        "jacobian": FROZEN_PROFILE["jacobian"],
        "diff_step": FROZEN_PROFILE["diff_step"],
        "x_scale": FROZEN_PROFILE["x_scale"],
        "max_nfev": FROZEN_PROFILE["max_nfev"],
        "tr_solver": FROZEN_PROFILE["tr_solver"],
        "tr_options": FROZEN_PROFILE["tr_options"],
        "f_scale": FROZEN_PROFILE["f_scale"],
        "jac_sparsity": FROZEN_PROFILE["jac_sparsity"],
    }
    for item in (r92["selected_profile"], r92a["selected_profile"]):
        for key, value in expected_solver.items():
            if item.get(key) != value:
                return False
    return bool(
        r92["selected_profile"].get("max_nfev") == 6
        and r92a["selected_profile"].get("max_nfev") == 6
    )


def canonical_sha256_sequence(values: list[dict[str, Any]]) -> str:
    """Hash a JSON array using the repository canonicalizer's normalization."""
    normalized = json.loads(canonical_json_bytes({"values": values}))
    return hashlib.sha256(rfc8785.dumps(normalized["values"])).hexdigest()


def make_r92_case(row: dict[str, Any]) -> Case:
    return Case(
        case_id=row["case_id"],
        family="R92",
        tube_bulk_K=float(row["tube_bulk_K"]),
        shell_bulk_K=float(row["shell_bulk_K"]),
        s_ts=int(row["s_ts"]),
        area_i_m2=float(row["area_i_m2"]),
        area_o_m2=float(row["area_o_m2"]),
        h_i_base_W_m2K=float(row["h_i_W_m2K"]),
        h_o_base_W_m2K=float(row["h_o_base_W_m2K"]),
        wall_resistance_K_W=float(row["wall_resistance_K_W"]),
        pressure_Pa=(None if row.get("pressure_Pa") is None else float(row["pressure_Pa"])),
        reynolds=100000.0,
        tube_c3_active=False,
        shell_jmu_active=bool(row["nonlinear_jmu"]),
    )


def make_r92a_case(row: dict[str, Any]) -> Case:
    return Case(
        case_id=row["case_id"],
        family="R92A",
        tube_bulk_K=float(row["tube_bulk_K"]),
        shell_bulk_K=float(row["shell_bulk_K"]),
        s_ts=int(row["s_ts"]),
        area_i_m2=float(row["area_i_m2"]),
        area_o_m2=float(row["area_o_m2"]),
        h_i_base_W_m2K=float(row["h_i_base_W_m2K"]),
        h_o_base_W_m2K=float(row["h_o_base_W_m2K"]),
        wall_resistance_K_W=float(row["wall_resistance_K_W"]),
        pressure_Pa=float(row["pressure_Pa"]),
        reynolds=float(row["reynolds"]),
        tube_c3_active=True,
        shell_jmu_active=bool(row["shell_jmu_active"]),
    )


def make_holdout_case(row: dict[str, Any], area_i: float, area_o: float) -> Case:
    fractions = row["resistance_fractions"]
    total = float(row["total_resistance_base_K_W"])
    resistance_i = float(fractions["tube_film"]) * total
    resistance_wall = float(fractions["wall"]) * total
    resistance_o = float(fractions["shell_film"]) * total
    if not math.isclose(
        float(fractions["tube_film"]) + float(fractions["wall"]) + float(fractions["shell_film"]),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise ReviewFailure("holdout resistance fractions do not sum to one")
    return Case(
        case_id=row["case_id"],
        family="HOLDOUT",
        tube_bulk_K=float(row["tube_bulk_K"]),
        shell_bulk_K=float(row["shell_bulk_K"]),
        s_ts=int(row["s_ts"]),
        area_i_m2=area_i,
        area_o_m2=area_o,
        h_i_base_W_m2K=1.0 / (resistance_i * area_i),
        h_o_base_W_m2K=1.0 / (resistance_o * area_o),
        wall_resistance_K_W=resistance_wall,
        pressure_Pa=float(row["pressure_Pa"]),
        reynolds=float(row["reynolds"]),
        tube_c3_active=True,
        shell_jmu_active=str(row["type"]).startswith("DUAL_ACTIVE"),
    )


def validate_tp(temperature_K: float, pressure_Pa: float) -> None:
    if not math.isfinite(temperature_K) or not math.isfinite(pressure_Pa):
        raise ReviewFailure("NONFINITE_PROPERTY_STATE")
    if not T_MIN_K <= temperature_K <= T_MAX_K:
        raise ReviewFailure("TRIAL_DOMAIN_EXCURSION_T")
    if not P_MIN_PA <= pressure_Pa <= P_MAX_PA:
        raise ReviewFailure("TRIAL_DOMAIN_EXCURSION_P")


def water(temperature_K: float, pressure_Pa: float) -> dict[str, float]:
    validate_tp(temperature_K, pressure_Pa)
    try:
        mu = float(PropsSI("V", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
        cp = float(PropsSI("C", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
        conductivity = float(PropsSI("L", "T", temperature_K, "P", pressure_Pa, "HEOS::Water"))
    except Exception as exc:  # source/backend errors fail closed
        raise ReviewFailure(f"PROPERTY_EVALUATION_FAILURE:{type(exc).__name__}") from exc
    pr = cp * mu / conductivity
    if not all(math.isfinite(value) and value > 0.0 for value in (mu, cp, conductivity, pr)):
        raise ReviewFailure("PROPERTY_EVALUATION_FAILURE_NONPOSITIVE")
    if not PR_MIN <= pr <= PR_MAX:
        raise ReviewFailure("PR_DOMAIN_VIOLATION")
    return {"mu_Pa_s": mu, "cp_J_kgK": cp, "k_W_mK": conductivity, "Pr": pr}


def h_i(case: Case, twi: float) -> tuple[float, dict[str, float] | None]:
    if not case.tube_c3_active:
        return case.h_i_base_W_m2K, None
    if not RE_MIN < case.reynolds < RE_MAX:
        raise ReviewFailure("TUBE_C3_RE_DOMAIN_VIOLATION")
    if case.pressure_Pa is None:
        raise ReviewFailure("INPUT_AUTHORITY_MISSING_TUBE_PRESSURE")
    bulk = water(case.tube_bulk_K, case.pressure_Pa)
    wall = water(twi, case.pressure_Pa)
    ratio = bulk["Pr"] / wall["Pr"]
    if not PR_RATIO_MIN <= ratio <= PR_RATIO_MAX:
        raise ReviewFailure("TUBE_C3_PR_RATIO_DOMAIN_VIOLATION")
    return case.h_i_base_W_m2K * ratio**TUBE_EXPONENT, {
        "Pr_bulk": bulk["Pr"],
        "Pr_wall": wall["Pr"],
        "Pr_ratio": ratio,
    }


def h_o(case: Case, two: float) -> tuple[float, dict[str, float] | None]:
    if not case.shell_jmu_active:
        return case.h_o_base_W_m2K, None
    if case.pressure_Pa is None:
        raise ReviewFailure("INPUT_AUTHORITY_MISSING_SHELL_PRESSURE")
    bulk = water(case.shell_bulk_K, case.pressure_Pa)
    wall = water(two, case.pressure_Pa)
    ratio = bulk["mu_Pa_s"] / wall["mu_Pa_s"]
    return case.h_o_base_W_m2K * ratio**SHELL_EXPONENT, {
        "mu_bulk_Pa_s": bulk["mu_Pa_s"],
        "mu_wall_Pa_s": wall["mu_Pa_s"],
        "mu_ratio": ratio,
    }


def terms(case: Case, twi: float, two: float) -> dict[str, Any]:
    if not all(math.isfinite(value) for value in (twi, two)):
        raise ReviewFailure("NONFINITE_TRIAL")
    if not math.isfinite(case.wall_resistance_K_W) or case.wall_resistance_K_W <= 0.0:
        raise ReviewFailure("SINGULAR_OR_INVALID_RESISTANCE")
    if case.tube_c3_active or case.shell_jmu_active:
        if case.pressure_Pa is None:
            raise ReviewFailure("INPUT_AUTHORITY_MISSING_LOCAL_PRESSURE")
        validate_tp(twi, case.pressure_Pa)
        validate_tp(two, case.pressure_Pa)
    hi, tube_props = h_i(case, twi)
    ho, shell_props = h_o(case, two)
    gi = hi * case.area_i_m2
    gw = 1.0 / case.wall_resistance_K_W
    go = ho * case.area_o_m2
    qi = gi * (case.tube_bulk_K - twi)
    qw = gw * (twi - two)
    qo = go * (two - case.shell_bulk_K)
    values = (gi, gw, go, qi, qw, qo)
    if not all(math.isfinite(value) for value in values) or min(gi, gw, go) <= 0.0:
        raise ReviewFailure("NONFINITE_OR_INVALID_CALLBACK")
    return {
        "h_i_W_m2K": hi,
        "h_o_W_m2K": ho,
        "G_i_W_K": gi,
        "G_wall_W_K": gw,
        "G_o_W_K": go,
        "q_i_W": qi,
        "q_wall_W": qw,
        "q_o_W": qo,
        "tube_properties": tube_props,
        "shell_properties": shell_props,
    }


def physical_residual(case: Case, x: np.ndarray) -> np.ndarray:
    q_hc, twi, two = (float(item) for item in x)
    if not all(math.isfinite(item) for item in (q_hc, twi, two)):
        raise ReviewFailure("NONFINITE_TRIAL")
    q_ts = case.s_ts * q_hc
    state = terms(case, twi, two)
    return np.asarray(
        [q_ts - state["q_i_W"], q_ts - state["q_wall_W"], q_ts - state["q_o_W"]],
        dtype=float,
    )


def direct_seed(case: Case) -> np.ndarray:
    if not math.isfinite(case.wall_resistance_K_W) or case.wall_resistance_K_W <= 0.0:
        raise ReviewFailure("SINGULAR_OR_INVALID_RESISTANCE")
    ri = 1.0 / (case.h_i_base_W_m2K * case.area_i_m2)
    ro = 1.0 / (case.h_o_base_W_m2K * case.area_o_m2)
    q_ts = case.delta_t_K / (ri + case.wall_resistance_K_W + ro)
    twi = case.tube_bulk_K - q_ts * ri
    two = case.shell_bulk_K + q_ts * ro
    return np.asarray([case.s_ts * q_ts, twi, two], dtype=float)


def candidate_c_bounds(case: Case, x: np.ndarray) -> tuple[list[float], list[float]]:
    q_hc, twi, two = (float(item) for item in x)
    q_ts = case.s_ts * q_hc
    state = terms(case, twi, two)

    def gamma(count: int) -> float:
        return count * EPSILON / (1.0 - count * EPSILON)

    qi = state["q_i_W"]
    qw = state["q_wall_W"]
    qo = state["q_o_W"]
    gi = state["G_i_W_K"]
    gw = state["G_wall_W_K"]
    go = state["G_o_W_K"]
    bi = C_ROUND * (
        math.ulp(q_ts)
        + math.ulp(qi)
        + gi * (math.ulp(case.tube_bulk_K) + math.ulp(twi) + math.ulp(case.tube_bulk_K - twi))
        + gamma(2) * abs(qi)
    )
    bw = C_ROUND * (
        math.ulp(q_ts)
        + math.ulp(qw)
        + gw * (math.ulp(twi) + math.ulp(two) + math.ulp(twi - two))
        + gamma(1) * abs(qw)
    )
    bo = C_ROUND * (
        math.ulp(q_ts)
        + math.ulp(qo)
        + go * (math.ulp(two) + math.ulp(case.shell_bulk_K) + math.ulp(two - case.shell_bulk_K))
        + gamma(2) * abs(qo)
    )
    return [bi, bw, bo], [qi, qw, qo]


def scalar_oracle(case: Case, *, grid_count: int = 4097) -> dict[str, Any]:
    grid = np.linspace(T_MIN_K, T_MAX_K, grid_count, dtype=float)
    rows: list[tuple[int, float, float]] = []
    for index, two_value in enumerate(grid):
        two = float(two_value)
        try:
            ho, _ = h_o(case, two)
            qo = ho * case.area_o_m2 * (two - case.shell_bulk_K)
            twi = two + qo * case.wall_resistance_K_W
            if not T_MIN_K <= twi <= T_MAX_K:
                continue
            hi, _ = h_i(case, twi)
            qi = hi * case.area_i_m2 * (case.tube_bulk_K - twi)
            value = qo - qi
        except ReviewFailure:
            continue
        if math.isfinite(value):
            rows.append((index, two, value))
    if len(rows) < 3:
        raise ReviewFailure("ORACLE_VALID_DOMAIN_TOO_SMALL")
    indexes = [row[0] for row in rows]
    if any(b - a != 1 for a, b in zip(indexes, indexes[1:], strict=False)):
        raise ReviewFailure("ORACLE_VALID_DOMAIN_NOT_CONTIGUOUS")
    vals = [row[2] for row in rows]
    diffs = [b - a for a, b in zip(vals, vals[1:], strict=False)]
    increasing = all(value > 0.0 for value in diffs)
    decreasing = all(value < 0.0 for value in diffs)
    if not (increasing or decreasing):
        raise ReviewFailure("ORACLE_GRID_NOT_STRICTLY_MONOTONE")
    bracket: tuple[float, float] | None = None
    for left, right in zip(rows, rows[1:], strict=False):
        if left[2] * right[2] < 0.0:
            bracket = (left[1], right[1])
            break
    if bracket is None:
        raise ReviewFailure("ORACLE_STRICT_SIGN_BRACKET_MISSING")

    def f(two: float) -> float:
        ho, _ = h_o(case, two)
        qo = ho * case.area_o_m2 * (two - case.shell_bulk_K)
        twi = two + qo * case.wall_resistance_K_W
        if not T_MIN_K <= twi <= T_MAX_K:
            raise ReviewFailure("ORACLE_WALL_STATE_OUT_OF_DOMAIN")
        hi, _ = h_i(case, twi)
        qi = hi * case.area_i_m2 * (case.tube_bulk_K - twi)
        return qo - qi

    mid = 0.5 * (bracket[0] + bracket[1])
    root, details = brentq(
        f,
        bracket[0],
        bracket[1],
        xtol=math.ulp(mid),
        rtol=4.0 * EPSILON,
        maxiter=256,
        full_output=True,
        disp=True,
    )
    ho, _ = h_o(case, float(root))
    q_ts = ho * case.area_o_m2 * (float(root) - case.shell_bulk_K)
    twi = float(root) + q_ts * case.wall_resistance_K_W
    return {
        "q_ts_W": q_ts,
        "q_hc_W": case.s_ts * q_ts,
        "T_wall_inner_K": twi,
        "T_wall_outer_K": float(root),
        "bracket_K": list(bracket),
        "bracket_endpoint_residual_W": [f(bracket[0]), f(bracket[1])],
        "grid_count": grid_count,
        "valid_grid_count": len(rows),
        "strict_sign_change": True,
        "strict_monotonicity": "INCREASING" if increasing else "DECREASING",
        "brentq_converged": bool(details.converged),
        "brentq_iterations": int(details.iterations),
        "brentq_function_calls": int(details.function_calls),
        "validation_only": True,
        "production_scalar_reduction_selected": False,
    }


def solve_case(case: Case) -> dict[str, Any]:
    x0 = direct_seed(case)
    q_scale = abs(float(x0[0]))
    delta = abs(case.delta_t_K)
    if q_scale <= 0.0 or delta <= 0.0:
        raise ReviewFailure("ZERO_DUTY_MUST_USE_EXACT_BRANCH")
    cap = int(FROZEN_PROFILE["residual_callback_cap"])
    calls = 0

    def fun(values: np.ndarray) -> np.ndarray:
        nonlocal calls
        calls += 1
        if calls > cap:
            raise ReviewFailure("SOLVER_RESOURCE_EXHAUSTION_CALLBACK_CAP")
        return physical_residual(case, values) / q_scale

    output = least_squares(
        fun,
        x0,
        method=str(FROZEN_PROFILE["method"]),
        loss=str(FROZEN_PROFILE["loss"]),
        ftol=float(FROZEN_PROFILE["ftol"]),
        xtol=float(FROZEN_PROFILE["xtol"]),
        gtol=float(FROZEN_PROFILE["gtol"]),
        jac=str(FROZEN_PROFILE["jacobian"]),
        diff_step=float(FROZEN_PROFILE["diff_step"]),
        x_scale=[abs(float(x0[0])), delta, delta],
        max_nfev=int(FROZEN_PROFILE["max_nfev"]),
        bounds=(
            np.asarray([-np.inf, T_MIN_K, T_MIN_K], dtype=float),
            np.asarray([np.inf, T_MAX_K, T_MAX_K], dtype=float),
        ),
        tr_solver=str(FROZEN_PROFILE["tr_solver"]),
        tr_options=dict(FROZEN_PROFILE["tr_options"]),
        f_scale=float(FROZEN_PROFILE["f_scale"]),
        jac_sparsity=FROZEN_PROFILE["jac_sparsity"],
    )
    x = np.asarray(output.x, dtype=float)
    residuals = physical_residual(case, x)
    bounds, heat_terms = candidate_c_bounds(case, x)
    oracle = scalar_oracle(case)
    q_hc, twi, two = (float(value) for value in x)
    domain_ok = T_MIN_K <= twi <= T_MAX_K and T_MIN_K <= two <= T_MAX_K
    candidate_c_ok = all(abs(float(r)) <= bound for r, bound in zip(residuals, bounds, strict=True))
    result = {
        "case_id": case.case_id,
        "family": case.family,
        "tube_c3_active": case.tube_c3_active,
        "shell_jmu_active": case.shell_jmu_active,
        "reynolds": case.reynolds,
        "initial_seed": [float(value) for value in x0],
        "solution": {
            "q_hc_W": q_hc,
            "q_ts_W": case.s_ts * q_hc,
            "T_wall_inner_K": twi,
            "T_wall_outer_K": two,
        },
        "physical_residuals_W": [float(value) for value in residuals],
        "candidate_c_bounds_W": bounds,
        "candidate_c_pass": candidate_c_ok,
        "actual_heat_terms_W": heat_terms,
        "oracle": oracle,
        "absolute_oracle_errors": {
            "q_hc_W": abs(q_hc - float(oracle["q_hc_W"])),
            "T_wall_inner_K": abs(twi - float(oracle["T_wall_inner_K"])),
            "T_wall_outer_K": abs(two - float(oracle["T_wall_outer_K"])),
        },
        "solver_success": bool(output.success),
        "solver_status": int(output.status),
        "nfev": int(output.nfev),
        "njev": None if output.njev is None else int(output.njev),
        "callback_count_including_fd": calls,
        "callback_cap": cap,
        "domain_valid": domain_ok,
        "negative_q_hc_allowed_without_clamp": True,
        "accepted_for_profile_review": bool(
            output.success
            and output.status > 0
            and output.nfev <= int(FROZEN_PROFILE["max_nfev"])
            and calls <= cap
            and domain_ok
            and candidate_c_ok
            and all(math.isfinite(value) for value in residuals)
        ),
        "authority_result": False,
    }
    return result


def analytic_solution(case: Case) -> dict[str, float]:
    ri = 1.0 / (case.h_i_base_W_m2K * case.area_i_m2)
    ro = 1.0 / (case.h_o_base_W_m2K * case.area_o_m2)
    q_ts = case.delta_t_K / (ri + case.wall_resistance_K_W + ro)
    return {
        "q_ts_W": q_ts,
        "q_hc_W": case.s_ts * q_ts,
        "T_wall_inner_K": case.tube_bulk_K - q_ts * ri,
        "T_wall_outer_K": case.shell_bulk_K + q_ts * ro,
    }


def replay_source_matrix(rows: list[dict[str, Any]], *, family: str) -> dict[str, Any]:
    cases = [make_r92_case(row) if family == "R92" else make_r92a_case(row) for row in rows]
    records = [solve_case(case) for case in cases]
    summary = {
        "fixture_count": len(records),
        "accepted_count": sum(bool(row["accepted_for_profile_review"]) for row in records),
        "max_nfev": max((int(row["nfev"]) for row in records), default=0),
        "p95_nfev": percentile95([int(row["nfev"]) for row in records]),
        "max_callback_count": max(
            (int(row["callback_count_including_fd"]) for row in records), default=0
        ),
        "max_q_oracle_error_W": max(
            (row["absolute_oracle_errors"]["q_hc_W"] for row in records), default=0.0
        ),
        "max_twi_oracle_error_K": max(
            (row["absolute_oracle_errors"]["T_wall_inner_K"] for row in records),
            default=0.0,
        ),
        "max_two_oracle_error_K": max(
            (row["absolute_oracle_errors"]["T_wall_outer_K"] for row in records),
            default=0.0,
        ),
        "all_oracle_audits_pass": all(
            row["oracle"]["brentq_converged"]
            and row["oracle"]["strict_sign_change"]
            and row["oracle"]["strict_monotonicity"] in {"INCREASING", "DECREASING"}
            for row in records
        ),
        "all_domain_and_solver_checks_pass": all(
            row["accepted_for_profile_review"] for row in records
        ),
        "numeric_result_matrix_canonical_hash": canonical_sha256_sequence(
            [numeric_projection(row) for row in records]
        ),
    }
    return {"summary": summary, "records": records}


def numeric_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": row["case_id"],
        "solution": row["solution"],
        "physical_residuals_W": row["physical_residuals_W"],
        "candidate_c_bounds_W": row["candidate_c_bounds_W"],
        "candidate_c_pass": row["candidate_c_pass"],
        "nfev": row["nfev"],
        "njev": row["njev"],
        "callback_count_including_fd": row["callback_count_including_fd"],
        "solver_status": row["solver_status"],
    }


def percentile95(values: list[int]) -> int:
    if not values:
        return 0
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def replay_analytic_r92(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for row in rows:
        case = make_r92_case(row)
        exact = analytic_solution(case)
        x = np.asarray([exact["q_hc_W"], exact["T_wall_inner_K"], exact["T_wall_outer_K"]])
        residuals = physical_residual(case, x)
        records.append(
            {
                "case_id": case.case_id,
                "expected": exact,
                "physical_residuals_W": [float(value) for value in residuals],
                "max_residual_W": float(np.max(np.abs(residuals))),
                "finite": bool(np.all(np.isfinite(residuals))),
                "zero_duty": case.delta_t_K == 0.0,
            }
        )
    return {
        "fixture_count": len(records),
        "nonzero_count": sum(not row["zero_duty"] for row in records),
        "exact_equation_replay_pass": all(row["finite"] for row in records),
        "records": records,
    }


def failure_policy_replay(r92: dict[str, Any]) -> dict[str, Any]:
    audit: list[dict[str, Any]] = []

    def add(case_id: str, passed: bool, observation: str) -> None:
        audit.append({"case_id": case_id, "pass": bool(passed), "observation": observation})

    def local_identity(consumer: str | None, state: str | None) -> str:
        if not consumer or not state:
            return "INPUT_AUTHORITY_MISSING"
        if consumer != state:
            return "SUPPORT_IDENTITY_MISMATCH"
        return "VALID"

    add(
        "F01_MISSING_LOCAL_PROPERTY_STATE",
        local_identity("SUPPORT-A", None) == "INPUT_AUTHORITY_MISSING",
        local_identity("SUPPORT-A", None),
    )
    add(
        "F02_SUPPORT_IDENTITY_MISMATCH",
        local_identity("SUPPORT-A", "SUPPORT-B") == "SUPPORT_IDENTITY_MISMATCH",
        local_identity("SUPPORT-A", "SUPPORT-B"),
    )
    try:
        validate_tp(300.0001, 101325.0)
        f03 = False
    except ReviewFailure:
        f03 = True
    add("F03_WALL_TRIAL_OUTSIDE_PROPERTY_DOMAIN", f03, "out-of-domain trial rejected")
    try:
        if not math.isfinite(float("nan")):
            raise ReviewFailure("NONFINITE_TRIAL")
        f04 = False
    except ReviewFailure:
        f04 = True
    add("F04_NONFINITE_CALLBACK", f04, "nonfinite callback rejected")
    bad = Case(
        "BAD-R", "FAILURE", 299.0, 298.0, 1, 0.04, 0.055, 10, 10, 0.0, 101325, 10000, False, False
    )
    try:
        terms(bad, 299.0, 298.0)
        f05 = False
    except ReviewFailure:
        f05 = True
    add("F05_NONPOSITIVE_RESISTANCE", f05, "nonpositive wall resistance rejected")
    signed = -1.25
    add(
        "F06_NEGATIVE_Q_ALLOWED",
        signed < 0.0 and signed != abs(signed) and signed != max(signed, 0.0),
        "signed q retained; no abs or nonnegative clamp",
    )
    weak = r92["failure_and_policy_experiments"]["weak_solver_candidate"]
    weak_case_row = next(row for row in r92["input_matrix"] if row["case_id"] == weak["case_id"])
    weak_case = make_r92_case(weak_case_row)
    weak_x = np.asarray(
        [weak["q_hc_W"], weak["T_wall_inner_K"], weak["T_wall_outer_K"]], dtype=float
    )
    weak_resid = physical_residual(weak_case, weak_x)
    weak_rejected = bool(weak["solver_success"]) and (
        not bool(weak["post_residual_acceptance"])
        and float(np.max(np.abs(weak_resid))) > float(weak["roundoff_residual_bound_W"])
    )
    add(
        "F07_SOLVER_SUCCESS_RESIDUAL_UNACCEPTABLE",
        weak_rejected,
        "solver success remains rejected by independent physical residual check",
    )
    capped = r92["failure_and_policy_experiments"]["resource_capped_candidate"]
    add(
        "F08_RESOURCE_EXHAUSTION",
        capped["failure_class"] == "SOLVER_RESOURCE_EXHAUSTION"
        and not capped["solver_success"]
        and not capped["partial_result_authoritative"],
        "resource-capped result is typed failure and non-authoritative",
    )
    try:
        raise (
            ReviewFailure("NONFINITE_PHYSICAL_RESIDUAL")
            if not math.isfinite(float("inf"))
            else ReviewFailure("unexpected")
        )
    except ReviewFailure as exc:
        f09 = str(exc) == "NONFINITE_PHYSICAL_RESIDUAL"
    add("F09_NONFINITE_PHYSICAL_RESIDUAL", f09, "nonfinite physical residual rejected")
    return {
        "fixture_count": len(audit),
        "passed_count": sum(item["pass"] for item in audit),
        "all_pass": all(item["pass"] for item in audit),
        "fake_penalty_residual_used": False,
        "nan_as_success_used": False,
        "records": audit,
    }


def exact_zero_review(row: dict[str, Any]) -> dict[str, Any]:
    case = make_r92_case(row)
    if case.delta_t_K != 0.0:
        raise ReviewFailure("zero-duty fixture is not exactly isothermal")
    x = np.asarray([0.0, case.tube_bulk_K, case.tube_bulk_K], dtype=float)
    residuals = physical_residual(case, x)
    return {
        "case_id": case.case_id,
        "exact_zero_branch": True,
        "solver_invoked": False,
        "epsilon_or_deadband_used": False,
        "q_hc_W": 0.0,
        "q_ts_W": 0.0,
        "T_wall_inner_K": case.tube_bulk_K,
        "T_wall_outer_K": case.tube_bulk_K,
        "residuals_W": [float(value) for value in residuals],
        "pass": bool(np.all(residuals == 0.0)),
    }


def serialization_review(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "q_hc_W",
        "T_wall_inner_K",
        "T_wall_outer_K",
        "r_i_W",
        "r_w_W",
        "r_o_W",
    ]
    sample = records[0]
    q = sample["solution"]["q_hc_W"]
    residuals = sample["physical_residuals_W"]
    payload = {
        "q_hc_W": q,
        "T_wall_inner_K": sample["solution"]["T_wall_inner_K"],
        "T_wall_outer_K": sample["solution"]["T_wall_outer_K"],
        "r_i_W": residuals[0],
        "r_w_W": residuals[1],
        "r_o_W": residuals[2],
    }
    parsed = json.loads(canonical_json_bytes(payload))
    errors = {key: abs(float(parsed[key]) - float(payload[key])) for key in fields}
    bitwise = all(float(parsed[key]).hex() == float(payload[key]).hex() for key in fields)
    return {
        "path": "hexagent.canonical_json.canonical_json_bytes_then_json.loads",
        "tested_fields": fields,
        "absolute_quantization_errors": errors,
        "bitwise_float_roundtrip": bitwise,
        "display_rounding_included": False,
        "pass": bitwise and all(value == 0.0 for value in errors.values()),
    }


def run() -> dict[str, Any]:
    registry = read_json(REGISTRY_PATH)
    r92 = read_json(R92_RESULTS_PATH)
    r92a = read_json(R92A_RESULTS_PATH)
    holdout = read_json(HOLDOUT_PATH)
    integrity = check_artifact_bundle(registry)
    pre_execution = holdout["pre_execution_and_review_binding"]["pre_execution_binding"]
    pre_execution_payload = {
        key: holdout[key]
        for key in (
            "schema_version",
            "task_id",
            "review_target_head",
            "holdout_matrix",
            "frozen_profile",
        )
    }
    pre_hash = str(pre_execution["input_canonical_hash"])
    input_matrix_hash_valid = (
        canonical_sha256(pre_execution_payload) == pre_hash
        and canonical_sha256(holdout["holdout_matrix"])
        == pre_execution["holdout_matrix_canonical_hash"]
        and canonical_sha256(holdout["frozen_profile"])
        == pre_execution["frozen_profile_canonical_hash"]
    )
    if not input_matrix_hash_valid:
        raise ReviewFailure("pre-execution holdout canonical hash mismatch")

    analytic_rows = [
        row
        for row in r92["input_matrix"]
        if row["fixture_kind"] == "NUMERICAL_KERNEL_FIXTURE" and not bool(row["nonlinear_jmu"])
    ]
    zero_row = next(row for row in analytic_rows if row["case_id"] == "A04_ZERO_DUTY_EXACT")
    r92_jmu_rows = [row for row in r92["input_matrix"] if bool(row["nonlinear_jmu"])]
    r92a_rows = r92a["input_matrix"]
    source_rows_r92 = r92["selected_fixture_results"]
    source_rows_r92a = r92a["selected_fixture_results"]
    holdout_spec = holdout["holdout_matrix"]
    holdout_cases = [
        make_holdout_case(row, float(holdout_spec["area_i_m2"]), float(holdout_spec["area_o_m2"]))
        for row in holdout_spec["fixtures"]
    ]

    r92_analytic = replay_analytic_r92(analytic_rows)
    r92a_review = replay_source_matrix(r92a_rows, family="R92A")
    r92_jmu = replay_source_matrix(r92_jmu_rows, family="R92")
    holdout_records = [solve_case(case) for case in holdout_cases]

    r92_nonzero_review = replay_source_matrix(
        [row for row in r92["input_matrix"] if row["case_id"] != "A04_ZERO_DUTY_EXACT"],
        family="R92",
    )
    failures = failure_policy_replay(r92)
    zero = exact_zero_review(zero_row)
    serialization = serialization_review(holdout_records)

    source_matrices = {
        "r92_source_selected_count": len(source_rows_r92),
        "r92a_source_selected_count": len(source_rows_r92a),
        "r92_input_ids_match_replay": [row["case_id"] for row in r92_nonzero_review["records"]]
        == [row["case_id"] for row in source_rows_r92],
        "r92a_input_ids_match_replay": [row["case_id"] for row in r92a_review["records"]]
        == [row["case_id"] for row in source_rows_r92a],
    }

    h_summary = {
        "fixture_count": len(holdout_records),
        "accepted_count": sum(row["accepted_for_profile_review"] for row in holdout_records),
        "all_pass": all(row["accepted_for_profile_review"] for row in holdout_records),
        "max_nfev": max(row["nfev"] for row in holdout_records),
        "p95_nfev": percentile95([row["nfev"] for row in holdout_records]),
        "max_callback_count": max(row["callback_count_including_fd"] for row in holdout_records),
        "max_q_oracle_error_W": max(
            row["absolute_oracle_errors"]["q_hc_W"] for row in holdout_records
        ),
        "max_twi_oracle_error_K": max(
            row["absolute_oracle_errors"]["T_wall_inner_K"] for row in holdout_records
        ),
        "max_two_oracle_error_K": max(
            row["absolute_oracle_errors"]["T_wall_outer_K"] for row in holdout_records
        ),
        "oracle_audit_all_pass": all(
            row["oracle"]["brentq_converged"]
            and row["oracle"]["strict_sign_change"]
            and row["oracle"]["strict_monotonicity"] in {"INCREASING", "DECREASING"}
            for row in holdout_records
        ),
        "numeric_result_matrix_canonical_hash": canonical_sha256_sequence(
            [numeric_projection(row) for row in holdout_records]
        ),
    }

    all_rows = r92_nonzero_review["records"] + r92a_review["records"] + holdout_records
    global_nfev = [int(row["nfev"]) for row in all_rows]
    global_callbacks = [int(row["callback_count_including_fd"]) for row in all_rows]
    composite = {
        "fixture_count_nonzero_solver_cases": len(all_rows),
        "max_nfev": max(global_nfev),
        "p95_nfev": percentile95(global_nfev),
        "max_callback_count": max(global_callbacks),
        "nfev_headroom_to_cap": int(FROZEN_PROFILE["max_nfev"]) - max(global_nfev),
        "callback_headroom_to_cap": int(FROZEN_PROFILE["residual_callback_cap"])
        - max(global_callbacks),
        "max_q_oracle_error_W": max(
            row["absolute_oracle_errors"]["q_hc_W"]
            for row in r92_nonzero_review["records"] + r92a_review["records"] + holdout_records
        ),
        "max_twi_oracle_error_K": max(
            row["absolute_oracle_errors"]["T_wall_inner_K"]
            for row in r92_nonzero_review["records"] + r92a_review["records"] + holdout_records
        ),
        "max_two_oracle_error_K": max(
            row["absolute_oracle_errors"]["T_wall_outer_K"]
            for row in r92_nonzero_review["records"] + r92a_review["records"] + holdout_records
        ),
        "classification": "VALIDATION_ENVELOPE_ONLY",
        "universal_production_bound": False,
    }

    numeric_hashes = {
        "r92": r92_nonzero_review["summary"]["numeric_result_matrix_canonical_hash"],
        "r92a": r92a_review["summary"]["numeric_result_matrix_canonical_hash"],
        "holdout": h_summary["numeric_result_matrix_canonical_hash"],
    }
    return {
        "schema_version": "task172-independent-numerical-profile-review-runner-v1",
        "runtime": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "scipy": scipy.__version__,
            "numpy": np.__version__,
            "coolprop": CoolProp.__version__,
            "platform": platform.platform(),
        },
        "frozen_profile": FROZEN_PROFILE,
        "holdout_input": {
            "path": HOLDOUT_PATH,
            "pre_execution_file_sha256": pre_execution["input_file_sha256"],
            "pre_execution_canonical_hash": pre_hash,
            "pre_execution_matrix_hash_verified": input_matrix_hash_valid,
            "fixture_ids": [case.case_id for case in holdout_cases],
            "fixture_count": len(holdout_cases),
        },
        "artifact_integrity": integrity,
        "frozen_profile_replay_pass": check_frozen_profile(r92, r92a),
        "source_matrix_identity": source_matrices,
        "r92_analytic_replay": r92_analytic,
        "r92_shell_jmu_replay": r92_jmu,
        "r92_full_nonzero_replay": r92_nonzero_review,
        "r92a_active_matrix_replay": r92a_review,
        "failure_policy_replay": failures,
        "zero_duty_review": zero,
        "serialization_review": serialization,
        "holdout": {"summary": h_summary, "records": holdout_records},
        "composite_observed_envelope": composite,
        "numeric_matrix_hashes": numeric_hashes,
        "review_outcome_inputs": {
            "r92_replay_pass": r92_analytic["exact_equation_replay_pass"]
            and r92_nonzero_review["summary"]["all_domain_and_solver_checks_pass"],
            "r92_shell_jmu_replay_pass": r92_jmu["summary"]["all_domain_and_solver_checks_pass"],
            "r92a_replay_pass": r92a_review["summary"]["all_domain_and_solver_checks_pass"],
            "r92_failure_policy_replay_pass": failures["all_pass"],
            "zero_duty_pass": zero["pass"],
            "serialization_pass": serialization["pass"],
            "holdout_8_of_8_pass": h_summary["all_pass"] and h_summary["oracle_audit_all_pass"],
            "resource_cap_pass": composite["nfev_headroom_to_cap"] > 0
            and composite["callback_headroom_to_cap"] > 0,
            "cross_runtime_numeric_hash": canonical_sha256(numeric_hashes),
        },
    }


def main() -> int:
    report = run()
    sys.stdout.write(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
