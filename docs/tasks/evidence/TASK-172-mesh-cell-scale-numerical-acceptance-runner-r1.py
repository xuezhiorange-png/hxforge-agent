"""Deterministic R96 numerical-profile scale-applicability experiment.

This evidence-only runner reuses the frozen R94 numerical review kernel and
the R95 pure synthetic-cell constructor. It evaluates only H01-H08 dyadic
scale-training cases plus the one predeclared R95 diagnostic. It has no
production imports or network access. The K01-K05 holdout builder is
serialization-only; no code path in this runner solves those cases.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import CoolProp
import numpy as np
import scipy
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

R94_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-independent-review-runner-r1.py"
)
R94_HOLDOUT_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-independent-review-holdout-r1.json"
)
R95_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r1.py"
)
R95_EVIDENCE_PATH = ROOT / ("docs/tasks/evidence/TASK-172-mesh-convergence-qualification-r1.json")
RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-results-r1.json"
)
HOLDOUT_OUTPUT_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-cell-scale-numerical-acceptance-holdout-input-r1.json"
)

EXPECTED_PREDECESSOR_HEAD = "28770ce03a1a21496cfd5b0ea4ba8e32e78328ff"
EXPECTED_R94_HOLDOUT_CANONICAL_HASH = (
    "a82da762b4c70ac2c7adf412d417a5e979603b37074c5cf246cce4e3c85c99f2"
)
EXPECTED_R94_PROFILE_CANONICAL_HASH = (
    "654dc963b6ca5a8fb934d9b2224c551c4e4329a4d8b7a5ce436c0e2488f4f4a4"
)
EXPECTED_R95_DIAGNOSTIC_HASH = "3f0608628c841fbff21b224e14b2846e7872cc13ac2251b59434b2b3d6daeea4"
EXPECTED_TRAINING_INPUT_HASH = "431967d2f7cbdb78027472bbabe0ba5b7edfbb328e6c5144f9acdb7e4323f6a8"

BASELINE_PROFILE: dict[str, Any] = {
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
    "c_round": 0.5,
}

SCALE_TEXTS = ("1", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64", "1/128", "1/256")
CANDIDATE_CHANGES: tuple[tuple[str, float, float], ...] = (
    ("P0_FROZEN_R94", 0.5, 1e-12),
    ("P1_ACCEPTANCE_EXTENSION", 1.0, 1e-12),
    ("P2_TIGHTER_XTOL_1E13", 0.5, 1e-13),
    ("P3_TIGHTER_XTOL_1E14", 0.5, 1e-14),
)

R95_EXPECTED = {
    "initial_seed": [2.468070807205436, 298.9167859807297, 298.67985118323793],
    "solution": [2.4641998406554912, 298.91618424834616, 298.6796210636432],
    "residuals_W": [
        2.0605739337042905e-13,
        -3.3173463975799677e-13,
        2.0472512574087887e-13,
    ],
    "bounds_c05_W": [
        1.699451104588476e-13,
        5.929811771063023e-13,
        1.185817589901431e-12,
    ],
    "nfev": 4,
    "callback_count": 16,
    "solver_status": 3,
}

T_MIN_K = 298.15
T_MAX_K = 300.0
BASE_AREA_I_M2 = 0.04
BASE_AREA_O_M2 = 0.055
SCALAR_ORACLE_FIXTURES = ("H01", "H02", "H04", "H05")
SCALAR_ORACLE_FRACTIONS = ("1", "1/8", "1/256")


def load_evidence_runner(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load evidence runner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def add_canonical_hash(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["canonical_hash"] = canonical_sha256(result)
    return result


def fraction(value: str) -> Fraction:
    return Fraction(value)


def candidate_profile(candidate_id: str, c_round: float, xtol: float) -> dict[str, Any]:
    profile = dict(BASELINE_PROFILE)
    profile["c_round"] = c_round
    profile["xtol"] = xtol
    profile["candidate_id"] = candidate_id
    return profile


def frozen_input_bundle() -> tuple[dict[str, Any], dict[str, Any], ModuleType, ModuleType]:
    holdout_source = read_json(R94_HOLDOUT_PATH)
    holdout_matrix = holdout_source["holdout_matrix"]
    if canonical_sha256(holdout_matrix) != EXPECTED_R94_HOLDOUT_CANONICAL_HASH:
        raise RuntimeError("R94 H01-H08 holdout matrix hash mismatch")
    if canonical_sha256(holdout_source["frozen_profile"]) != EXPECTED_R94_PROFILE_CANONICAL_HASH:
        raise RuntimeError("R94 frozen numerical profile hash mismatch")
    if holdout_source["frozen_profile"] != BASELINE_PROFILE:
        raise RuntimeError("R94 profile differs from the R96 frozen baseline")

    r94 = load_evidence_runner(R94_RUNNER_PATH, "task172_r96_r94_review_runner")
    if float(r94.C_ROUND) != 0.5:
        raise RuntimeError("R94 evidence runner C_ROUND is not the frozen 0.5 value")
    r95 = load_evidence_runner(R95_RUNNER_PATH, "task172_r96_r95_mesh_runner")

    profile_rows = [
        candidate_profile(candidate_id, c_round, xtol)
        for candidate_id, c_round, xtol in CANDIDATE_CHANGES
    ]
    cases: list[dict[str, Any]] = []
    for base in holdout_matrix["fixtures"]:
        for scale_text in SCALE_TEXTS:
            scale = fraction(scale_text)
            cases.append(
                {
                    "case_id": f"{base['case_id']}@{scale_text}",
                    "base_case_id": base["case_id"],
                    "scale_fraction_exact": scale_text,
                    "area_i_m2": BASE_AREA_I_M2 * float(scale),
                    "area_o_m2": BASE_AREA_O_M2 * float(scale),
                    "wall_resistance_K_W": float(base["total_resistance_base_K_W"])
                    * float(base["resistance_fractions"]["wall"])
                    / float(scale),
                    "bulk_and_correlation_inputs_unchanged": True,
                    "base_case": base,
                }
            )
    matrix = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_R1",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "reference_matrix_path": str(R94_HOLDOUT_PATH.relative_to(ROOT)),
        "reference_matrix_canonical_hash": EXPECTED_R94_HOLDOUT_CANONICAL_HASH,
        "frozen_profile_canonical_hash": EXPECTED_R94_PROFILE_CANONICAL_HASH,
        "reference_area_i_m2": BASE_AREA_I_M2,
        "reference_area_o_m2": BASE_AREA_O_M2,
        "scale_fractions_exact": list(SCALE_TEXTS),
        "base_case_count": len(holdout_matrix["fixtures"]),
        "scale_count": len(SCALE_TEXTS),
        "expected_scale_training_case_count": 72,
        "scale_cases": cases,
        "candidate_profiles": profile_rows,
        "candidate_case_evaluation_count": len(cases) * len(profile_rows),
        "scale_oracle": {
            "q_hc_f_W": "f * q_hc_reference_W",
            "T_wall_inner_f_K": "T_wall_inner_reference_K",
            "T_wall_outer_f_K": "T_wall_outer_reference_K",
        },
        "residual_policy_class": "METHOD_SENSITIVITY_DERIVED_PROJECT_ACCEPTANCE_RULE",
        "residual_policy_is_formal_error_bound": False,
        "randomness_used": False,
        "network_calls": False,
        "mesh_threshold_selection": False,
        "holdout_k01_k05_execution": False,
    }
    expected = read_json(R95_EVIDENCE_PATH)["first_blocking_local_trial"]
    if (
        expected["fixture_id"] != "M01"
        or expected["cell_count"] != 8
        or expected["cell_interval_exact"] != ["1/4", "3/8"]
        or expected["cell_fraction_exact"] != "1/8"
    ):
        raise RuntimeError("R95 diagnostic identity does not match the frozen failure")
    return holdout_source, matrix, r94, r95


def verify_expected_training_hash(matrix: dict[str, Any], *, allow_freeze: bool) -> str:
    observed = canonical_sha256(matrix)
    if allow_freeze and EXPECTED_TRAINING_INPUT_HASH == "TO_BE_FROZEN_BEFORE_NUMERICAL_RUN":
        return observed
    if observed != EXPECTED_TRAINING_INPUT_HASH:
        raise RuntimeError(
            "training matrix differs from pre-frozen R96 hash: "
            f"expected {EXPECTED_TRAINING_INPUT_HASH}, observed {observed}"
        )
    return observed


def scaled_case(r94: ModuleType, base: dict[str, Any], scale_text: str) -> Any:
    reference = r94.make_holdout_case(base, BASE_AREA_I_M2, BASE_AREA_O_M2)
    scale = float(fraction(scale_text))
    return replace(
        reference,
        case_id=f"{base['case_id']}@{scale_text}",
        family="R96_DYADIC_SCALE_TRAINING",
        area_i_m2=reference.area_i_m2 * scale,
        area_o_m2=reference.area_o_m2 * scale,
        wall_resistance_K_W=reference.wall_resistance_K_W / scale,
    )


def exact_oracle_scale(case: Any, base_oracle: dict[str, Any], scale_text: str) -> dict[str, float]:
    scale = float(fraction(scale_text))
    return {
        "q_hc_W": scale * float(base_oracle["q_hc_W"]),
        "T_wall_inner_K": float(base_oracle["T_wall_inner_K"]),
        "T_wall_outer_K": float(base_oracle["T_wall_outer_K"]),
    }


def solve_profile(r94: ModuleType, case: Any, profile: dict[str, Any]) -> dict[str, Any]:
    seed = np.asarray(r94.direct_seed(case), dtype=float)
    q_scale = abs(float(seed[0]))
    delta_t = abs(float(case.delta_t_K))
    callback_cap = int(profile["residual_callback_cap"])
    max_nfev = int(profile["max_nfev"])
    call_count = 0
    if q_scale == 0.0 or delta_t == 0.0:
        return {
            "case_id": str(case.case_id),
            "accepted": False,
            "failure_class": "ZERO_DUTY_EXACT_BRANCH_REQUIRED",
            "initial_seed": [float(value) for value in seed],
        }

    def callback(values: np.ndarray) -> np.ndarray:
        nonlocal call_count
        call_count += 1
        if call_count > callback_cap:
            raise r94.ReviewFailure("SOLVER_RESOURCE_EXHAUSTION_CALLBACK_CAP")
        return np.asarray(r94.physical_residual(case, values), dtype=float) / q_scale

    options = {
        "method": str(profile["method"]),
        "loss": str(profile["loss"]),
        "ftol": float(profile["ftol"]),
        "xtol": float(profile["xtol"]),
        "gtol": float(profile["gtol"]),
        "jac": str(profile["jacobian"]),
        "diff_step": float(profile["diff_step"]),
        "x_scale": [abs(float(seed[0])), delta_t, delta_t],
        "max_nfev": max_nfev,
        "bounds": (
            np.asarray([-np.inf, T_MIN_K, T_MIN_K], dtype=float),
            np.asarray([np.inf, T_MAX_K, T_MAX_K], dtype=float),
        ),
        "tr_solver": str(profile["tr_solver"]),
        "tr_options": dict(profile["tr_options"]),
        "f_scale": float(profile["f_scale"]),
        "jac_sparsity": profile["jac_sparsity"],
    }
    try:
        output = least_squares(callback, seed, **options)
        x = np.asarray(output.x, dtype=float)
        residuals = np.asarray(r94.physical_residual(case, x), dtype=float)
        base_bounds, _ = r94.candidate_c_bounds(case, x)
        if float(r94.C_ROUND) != 0.5:
            raise RuntimeError("R94 base C_ROUND changed during the experiment")
        bounds = [float(value) * float(profile["c_round"]) / 0.5 for value in base_bounds]
        ratios = [
            abs(float(value)) / float(bound) if float(bound) > 0.0 else math.inf
            for value, bound in zip(residuals, bounds, strict=True)
        ]
        domain_valid = bool(
            np.all(np.isfinite(x))
            and T_MIN_K <= float(x[1]) <= T_MAX_K
            and T_MIN_K <= float(x[2]) <= T_MAX_K
            and np.all(np.isfinite(residuals))
        )
        resource_cap_hit = bool(int(output.status) == 0 or call_count > callback_cap)
        accepted = bool(
            output.success
            and int(output.status) > 0
            and int(output.nfev) <= max_nfev
            and not resource_cap_hit
            and domain_valid
            and all(value <= 1.0 for value in ratios)
        )
        failure_class = (
            "NONE"
            if accepted
            else "SOLVER_RESOURCE_EXHAUSTION"
            if resource_cap_hit
            else "SOLVER_TERMINATED_RESIDUAL_UNACCEPTED"
            if output.success and any(value > 1.0 for value in ratios)
            else "FINAL_STATE_DOMAIN_INVALID"
            if not domain_valid
            else "NOT_CONVERGED"
        )
        return {
            "case_id": str(case.case_id),
            "initial_seed": [float(value) for value in seed],
            "solution": [float(value) for value in x],
            "q_hc_W": float(x[0]),
            "q_ts_W": float(case.s_ts * float(x[0])),
            "T_wall_inner_K": float(x[1]),
            "T_wall_outer_K": float(x[2]),
            "physical_residuals_W": [float(value) for value in residuals],
            "candidate_c_bounds_W": bounds,
            "residual_to_bound_ratios": ratios,
            "max_residual_to_bound_ratio": max(ratios),
            "solver_success": bool(output.success),
            "solver_status": int(output.status),
            "solver_message": str(output.message),
            "nfev": int(output.nfev),
            "njev": None if output.njev is None else int(output.njev),
            "residual_callback_count": call_count,
            "resource_cap_hit": resource_cap_hit,
            "domain_valid": domain_valid,
            "accepted": accepted,
            "failure_class": failure_class,
            "profile": profile,
        }
    except r94.ReviewFailure as failure:
        return {
            "case_id": str(case.case_id),
            "initial_seed": [float(value) for value in seed],
            "accepted": False,
            "failure_class": str(failure),
            "resource_cap_hit": "RESOURCE_EXHAUSTION" in str(failure),
            "domain_valid": False,
            "profile": profile,
        }


def percentile_nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return float(ordered[index])


def candidate_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios = [
        float(row["max_residual_to_bound_ratio"])
        for row in rows
        if row.get("max_residual_to_bound_ratio") is not None
        and math.isfinite(float(row["max_residual_to_bound_ratio"]))
    ]
    q_errors = [
        float(row["oracle_errors"]["q_hc_W"])
        for row in rows
        if row.get("oracle_errors", {}).get("q_hc_W") is not None
        and math.isfinite(float(row["oracle_errors"]["q_hc_W"]))
    ]
    twi_errors = [
        float(row["oracle_errors"]["T_wall_inner_K"])
        for row in rows
        if row.get("oracle_errors", {}).get("T_wall_inner_K") is not None
        and math.isfinite(float(row["oracle_errors"]["T_wall_inner_K"]))
    ]
    two_errors = [
        float(row["oracle_errors"]["T_wall_outer_K"])
        for row in rows
        if row.get("oracle_errors", {}).get("T_wall_outer_K") is not None
        and math.isfinite(float(row["oracle_errors"]["T_wall_outer_K"]))
    ]
    nfev = [int(row["nfev"]) for row in rows if row.get("nfev") is not None]
    callbacks = [
        int(row["residual_callback_count"])
        for row in rows
        if row.get("residual_callback_count") is not None
    ]
    return {
        "accepted_count": sum(bool(row["accepted"]) for row in rows),
        "case_count": len(rows),
        "all_pass": len(rows) == 72 and all(bool(row["accepted"]) for row in rows),
        "max_residual_to_bound_ratio": max(ratios) if ratios else None,
        "p95_case_max_residual_to_bound_ratio_nearest_rank": percentile_nearest_rank(ratios, 0.95),
        "max_q_oracle_error_W": max(q_errors) if q_errors else None,
        "max_twi_oracle_error_K": max(twi_errors) if twi_errors else None,
        "max_two_oracle_error_K": max(two_errors) if two_errors else None,
        "max_nfev": max(nfev) if nfev else None,
        "max_callback_count": max(callbacks) if callbacks else None,
        "resource_cap_hit_count": sum(bool(row.get("resource_cap_hit")) for row in rows),
        "all_domains_valid": all(bool(row.get("domain_valid")) for row in rows),
        "all_oracle_errors_finite": bool(
            len(q_errors) == len(rows)
            and len(twi_errors) == len(rows)
            and len(two_errors) == len(rows)
        ),
        "result_matrix_canonical_hash": canonical_sha256({"rows": rows}),
    }


def make_r95_diagnostic_case(r94: ModuleType, r95: ModuleType) -> Any:
    return r95.make_r94_case(
        r94,
        "M01",
        float(Fraction(5, 16)),
        Fraction(1, 8),
        cell_identity="R95-M01-PRIMARY-N8-CELL-1/4-3/8",
    )


def r95_diagnostic_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    p0 = next(row for row in rows if row["candidate_id"] == "P0_FROZEN_R94")
    expected = R95_EXPECTED
    exact_match = bool(
        p0["initial_seed"] == expected["initial_seed"]
        and p0["solution"] == expected["solution"]
        and p0["physical_residuals_W"] == expected["residuals_W"]
        and p0["candidate_c_bounds_W"] == expected["bounds_c05_W"]
        and p0["nfev"] == expected["nfev"]
        and p0["residual_callback_count"] == expected["callback_count"]
        and p0["solver_status"] == expected["solver_status"]
    )
    return {
        "classification": "KNOWN_REMEDIATION_DIAGNOSTIC_NOT_INDEPENDENT_HOLDOUT",
        "fixture_id": "M01",
        "sequence_id": "PRIMARY",
        "cell_count": 8,
        "cell_interval_exact": ["1/4", "3/8"],
        "cell_fraction_exact": "1/8",
        "exact_p0_diagnostic_reproduced": exact_match,
        "p0_solver_success": bool(p0["solver_success"]),
        "p0_residual_acceptance_pass": bool(p0["accepted"]),
        "p0_residual_to_bound_ratios": p0["residual_to_bound_ratios"],
        "r95_mesh_mapping_error": False,
        "r95_property_domain_error": False,
        "r95_solver_resource_exhaustion": False,
        "r95_residual_acceptance_scale_failure": bool(p0["solver_success"] and not p0["accepted"]),
        "candidate_evaluations": rows,
    }


def run_scalar_scale_oracles(
    r94: ModuleType, holdout_matrix: dict[str, Any], references: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    by_id = {str(row["case_id"]): row for row in holdout_matrix["fixtures"]}
    for case_id in SCALAR_ORACLE_FIXTURES:
        for scale_text in SCALAR_ORACLE_FRACTIONS:
            case = scaled_case(r94, by_id[case_id], scale_text)
            oracle = cast(dict[str, Any], r94.scalar_oracle(case, grid_count=4097))
            exact = exact_oracle_scale(case, references[case_id], scale_text)
            errors = {
                "q_hc_W": abs(float(oracle["q_hc_W"]) - exact["q_hc_W"]),
                "T_wall_inner_K": abs(float(oracle["T_wall_inner_K"]) - exact["T_wall_inner_K"]),
                "T_wall_outer_K": abs(float(oracle["T_wall_outer_K"]) - exact["T_wall_outer_K"]),
            }
            output.append(
                {
                    "case_id": case_id,
                    "scale_fraction_exact": scale_text,
                    "strict_sign_change": bool(oracle["strict_sign_change"]),
                    "strict_monotonicity": str(oracle["strict_monotonicity"]),
                    "brentq_converged": bool(oracle["brentq_converged"]),
                    "oracle_solution": {
                        "q_hc_W": float(oracle["q_hc_W"]),
                        "T_wall_inner_K": float(oracle["T_wall_inner_K"]),
                        "T_wall_outer_K": float(oracle["T_wall_outer_K"]),
                    },
                    "exact_scale_oracle": exact,
                    "absolute_errors": errors,
                    "all_errors_finite": all(math.isfinite(value) for value in errors.values()),
                    "production_scalar_reduction_selected": False,
                    "non_dyadic_holdout_used": False,
                }
            )
    return output


def make_future_holdout(profile: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = [
        {
            "case_id": "K01",
            "case_class": "DUAL_ACTIVE_TUBE_HOT",
            "tube_bulk_K": 299.70,
            "shell_bulk_K": 298.70,
            "s_ts": 1,
            "pressure_Pa": 101325,
            "reynolds": 25000,
            "total_resistance_base_K_W": "0.060",
            "resistance_fractions": {"tube_film": "0.70", "wall": "0.20", "shell_film": "0.10"},
            "tube_c3_active": True,
            "shell_jmu_active": True,
        },
        {
            "case_id": "K02",
            "case_class": "DUAL_ACTIVE_SHELL_HOT",
            "tube_bulk_K": 298.70,
            "shell_bulk_K": 299.70,
            "s_ts": -1,
            "pressure_Pa": 100000,
            "reynolds": 75000,
            "total_resistance_base_K_W": "0.055",
            "resistance_fractions": {"tube_film": "0.10", "wall": "0.20", "shell_film": "0.70"},
            "tube_c3_active": True,
            "shell_jmu_active": True,
        },
        {
            "case_id": "K03",
            "case_class": "DUAL_ACTIVE_NEAR_ZERO",
            "tube_bulk_K": 299.6004,
            "shell_bulk_K": 299.6000,
            "s_ts": 1,
            "pressure_Pa": 101325,
            "reynolds": 30000,
            "total_resistance_base_K_W": "0.078",
            "resistance_fractions": {"tube_film": "0.20", "wall": "0.60", "shell_film": "0.20"},
            "tube_c3_active": True,
            "shell_jmu_active": True,
        },
        {
            "case_id": "K04",
            "case_class": "TUBE_C3_ONLY",
            "tube_bulk_K": 299.65,
            "shell_bulk_K": 298.85,
            "s_ts": 1,
            "pressure_Pa": 100000,
            "reynolds": 6000,
            "total_resistance_base_K_W": "0.050",
            "resistance_fractions": {"tube_film": "0.15", "wall": "0.25", "shell_film": "0.60"},
            "tube_c3_active": True,
            "shell_jmu_active": False,
        },
        {
            "case_id": "K05",
            "case_class": "DUAL_ACTIVE_NEGATIVE_Q",
            "tube_bulk_K": 298.75,
            "shell_bulk_K": 299.65,
            "s_ts": 1,
            "pressure_Pa": 101325,
            "reynolds": 300000,
            "total_resistance_base_K_W": "0.055",
            "resistance_fractions": {"tube_film": "0.55", "wall": "0.30", "shell_film": "0.15"},
            "tube_c3_active": True,
            "shell_jmu_active": True,
        },
    ]
    for case in cases:
        fractions = case["resistance_fractions"]
        if sum(Fraction(value) for value in fractions.values()) != 1:
            raise RuntimeError(f"invalid exact resistance partition in {case['case_id']}")
        if not T_MIN_K <= case["tube_bulk_K"] <= T_MAX_K:
            raise RuntimeError(f"tube bulk state outside frozen property domain: {case['case_id']}")
        if not T_MIN_K <= case["shell_bulk_K"] <= T_MAX_K:
            raise RuntimeError(
                f"shell bulk state outside frozen property domain: {case['case_id']}"
            )
        if not 100000 <= case["pressure_Pa"] <= 101325:
            raise RuntimeError(f"pressure outside frozen property domain: {case['case_id']}")
        if not 3000 < case["reynolds"] < 5000000:
            raise RuntimeError(f"Re outside frozen C3 domain: {case['case_id']}")
        if not case["total_resistance_base_K_W"]:
            raise RuntimeError(f"missing synthetic fixture resistance: {case['case_id']}")
    value = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_R1",
        "holdout_id": "R96-NON-DYADIC-INDEPENDENT-REVIEW-HOLDOUT-R1",
        "holdout_lifecycle": "FROZEN_NOT_EXECUTED",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY_NOT_ENGINEERING_AUTHORITY",
        "base_area_i_m2": BASE_AREA_I_M2,
        "base_area_o_m2": BASE_AREA_O_M2,
        "scale_fractions_exact": ["1/3", "1/6", "1/12", "1/24", "1/48", "1/96"],
        "case_count": 5,
        "scale_count": 6,
        "expected_future_case_count": 30,
        "future_cases": cases,
        "property_profile": {
            "fluid": "PURE_ORDINARY_WATER",
            "backend": "HEOS",
            "backend_version": "CoolProp 8.0.0",
            "reference_state": "DEF",
            "phase": "STABLE_SINGLE_PHASE_LIQUID",
            "temperature_domain_K": [298.15, 300.0],
            "pressure_domain_Pa": [100000, 101325],
            "tube_c3_reynolds_domain_open": [3000, 5000000],
        },
        "selected_candidate_id": profile["candidate_id"],
        "selected_candidate_profile": profile,
        "selected_candidate_profile_canonical_hash": canonical_sha256(profile),
        "execution_controls": {
            "holdout_executed": False,
            "property_backend_called_for_holdout": False,
            "solver_called_for_holdout": False,
            "independent_review_required_before_execution": True,
        },
        "case_parameters_are_engineering_authority": False,
    }
    return add_canonical_hash(value)


def run_primary() -> dict[str, Any]:
    holdout_source, matrix, r94, r95 = frozen_input_bundle()
    matrix_hash = verify_expected_training_hash(matrix, allow_freeze=False)
    if EXPECTED_TRAINING_INPUT_HASH == "TO_BE_FROZEN_BEFORE_NUMERICAL_RUN":
        raise RuntimeError("R96 training input hash must be frozen in this runner before execution")

    references: dict[str, dict[str, Any]] = {}
    baseline_replays: dict[str, dict[str, Any]] = {}
    base_rows = holdout_source["holdout_matrix"]["fixtures"]
    for base in base_rows:
        case = r94.make_holdout_case(
            base,
            float(holdout_source["holdout_matrix"]["area_i_m2"]),
            float(holdout_source["holdout_matrix"]["area_o_m2"]),
        )
        oracle = cast(dict[str, Any], r94.scalar_oracle(case, grid_count=4097))
        if not (
            oracle["brentq_converged"]
            and oracle["strict_sign_change"]
            and oracle["strict_monotonicity"] in {"INCREASING", "DECREASING"}
        ):
            raise RuntimeError(f"f=1 independent oracle failed: {base['case_id']}")
        references[str(base["case_id"])] = oracle
        baseline_replays[str(base["case_id"])] = {
            "independent_scalar_oracle": {
                "q_hc_W": float(oracle["q_hc_W"]),
                "T_wall_inner_K": float(oracle["T_wall_inner_K"]),
                "T_wall_outer_K": float(oracle["T_wall_outer_K"]),
                "bracket_K": oracle["bracket_K"],
                "strict_monotonicity": oracle["strict_monotonicity"],
            },
            "oracle_converged": bool(oracle["brentq_converged"]),
        }

    candidate_results: list[dict[str, Any]] = []
    all_cases: list[dict[str, Any]] = []
    for base in base_rows:
        for scale_text in SCALE_TEXTS:
            case = scaled_case(r94, base, scale_text)
            expected = exact_oracle_scale(case, references[str(base["case_id"])], scale_text)
            all_cases.append(
                {
                    "case": case,
                    "base_case_id": str(base["case_id"]),
                    "scale_fraction_exact": scale_text,
                    "oracle": expected,
                }
            )

    for candidate_id, c_round, xtol in CANDIDATE_CHANGES:
        profile = candidate_profile(candidate_id, c_round, xtol)
        rows: list[dict[str, Any]] = []
        for item in all_cases:
            solved = solve_profile(r94, item["case"], profile)
            row = dict(solved)
            row["base_case_id"] = item["base_case_id"]
            row["scale_fraction_exact"] = item["scale_fraction_exact"]
            if "q_hc_W" in row:
                oracle = item["oracle"]
                row["scale_oracle"] = oracle
                row["oracle_errors"] = {
                    "q_hc_W": abs(float(row["q_hc_W"]) - oracle["q_hc_W"]),
                    "T_wall_inner_K": abs(float(row["T_wall_inner_K"]) - oracle["T_wall_inner_K"]),
                    "T_wall_outer_K": abs(float(row["T_wall_outer_K"]) - oracle["T_wall_outer_K"]),
                }
            else:
                row["oracle_errors"] = {
                    "q_hc_W": None,
                    "T_wall_inner_K": None,
                    "T_wall_outer_K": None,
                }
            rows.append(row)
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "profile": profile,
                "profile_canonical_hash": canonical_sha256(profile),
                "rows": rows,
                "summary": candidate_summary(rows),
            }
        )

    diagnostic_case = make_r95_diagnostic_case(r94, r95)
    diagnostic_results: list[dict[str, Any]] = []
    for candidate_id, c_round, xtol in CANDIDATE_CHANGES:
        profile = candidate_profile(candidate_id, c_round, xtol)
        diagnostic_results.append(
            {"candidate_id": candidate_id, **solve_profile(r94, diagnostic_case, profile)}
        )
    diagnostic = r95_diagnostic_audit(diagnostic_results)

    scalar_oracle_replays = run_scalar_scale_oracles(
        r94, holdout_source["holdout_matrix"], references
    )

    eligible: list[dict[str, Any]] = []
    for candidate in candidate_results:
        diagnostic_row = next(
            row for row in diagnostic_results if row["candidate_id"] == candidate["candidate_id"]
        )
        summary = candidate["summary"]
        can_select = bool(
            summary["all_pass"]
            and diagnostic_row["accepted"]
            and summary["all_domains_valid"]
            and summary["all_oracle_errors_finite"]
            and summary["resource_cap_hit_count"] == 0
        )
        candidate["diagnostic_pass"] = bool(diagnostic_row["accepted"])
        candidate["eligible"] = can_select
        if can_select:
            eligible.append(candidate)

    selected: dict[str, Any] | None = None
    selection_rationale = "NO_PREDECLARED_CANDIDATE_PASSED_ALL_REQUIRED_CASES"
    if eligible:
        by_candidate = {item["candidate_id"]: item for item in eligible}
        p1 = by_candidate.get("P1_ACCEPTANCE_EXTENSION")
        if p1 is not None:
            p1_summary = cast(dict[str, Any], p1["summary"])
            comparable_and_no_work_increase = True
            compared: list[str] = []
            for other in eligible:
                if other["candidate_id"] == p1["candidate_id"]:
                    continue
                other_summary = cast(dict[str, Any], other["summary"])
                no_worse_accuracy = all(
                    float(p1_summary[key]) <= float(other_summary[key])
                    for key in (
                        "max_q_oracle_error_W",
                        "max_twi_oracle_error_K",
                        "max_two_oracle_error_K",
                    )
                )
                no_more_work = all(
                    int(p1_summary[key]) <= int(other_summary[key])
                    for key in ("max_nfev", "max_callback_count")
                )
                compared.append(
                    f"{other['candidate_id']}:no_worse_accuracy={no_worse_accuracy},"
                    f"no_more_work={no_more_work}"
                )
                if not (no_worse_accuracy and no_more_work):
                    comparable_and_no_work_increase = False
            if comparable_and_no_work_increase:
                selected = p1
                selection_rationale = (
                    "PROJECT_SELECTION_POLICY: P1 preserves all reviewed solver controls; "
                    "its measured maximum oracle errors and evaluation/callback costs are "
                    "componentwise no worse than other eligible profiles. Compared: "
                    + ("; ".join(compared) if compared else "no other eligible profile")
                )
        if selected is None:
            eligible_sorted = sorted(
                eligible,
                key=lambda item: (
                    int(item["summary"]["max_nfev"]),
                    int(item["summary"]["max_callback_count"]),
                    float(item["summary"]["max_q_oracle_error_W"]),
                    float(item["summary"]["max_twi_oracle_error_K"]),
                    float(item["summary"]["max_two_oracle_error_K"]),
                    CANDIDATE_CHANGES.index(
                        (
                            item["candidate_id"],
                            float(item["profile"]["c_round"]),
                            float(item["profile"]["xtol"]),
                        )
                    ),
                ),
            )
            selected = eligible_sorted[0]
            selection_rationale = (
                "PROJECT_SELECTION_POLICY: P1 did not satisfy the predeclared measured "
                "accuracy/work dominance condition; choose the eligible profile with "
                "lowest worst-case evaluations, then callbacks, then oracle errors."
            )

    selected_replay: dict[str, Any] | None = None
    holdout_record: dict[str, Any] | None = None
    study_result = "BLOCKED_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION"
    if selected is not None:
        selected_rows = cast(list[dict[str, Any]], selected["rows"])
        replay_rows: list[dict[str, Any]] = []
        profile = cast(dict[str, Any], selected["profile"])
        for item in all_cases:
            solved = solve_profile(r94, item["case"], profile)
            row = dict(solved)
            row["base_case_id"] = item["base_case_id"]
            row["scale_fraction_exact"] = item["scale_fraction_exact"]
            row["scale_oracle"] = item["oracle"]
            row["oracle_errors"] = {
                "q_hc_W": abs(float(row["q_hc_W"]) - item["oracle"]["q_hc_W"]),
                "T_wall_inner_K": abs(
                    float(row["T_wall_inner_K"]) - item["oracle"]["T_wall_inner_K"]
                ),
                "T_wall_outer_K": abs(
                    float(row["T_wall_outer_K"]) - item["oracle"]["T_wall_outer_K"]
                ),
            }
            replay_rows.append(row)
        first_bytes = canonical_json_bytes({"rows": selected_rows})
        replay_bytes = canonical_json_bytes({"rows": replay_rows})
        same_result_bytes = first_bytes == replay_bytes
        same_result_hash = canonical_sha256({"rows": selected_rows}) == canonical_sha256(
            {"rows": replay_rows}
        )
        selected_replay = {
            "runtime_id": "PRIMARY_SAME_PROCESS_RUNTIME_REPLAY",
            "candidate_id": selected["candidate_id"],
            "repeat_case_count": len(replay_rows),
            "same_input_same_result_bytes": same_result_bytes,
            "same_input_same_result_hash": same_result_hash,
            "primary_matrix_canonical_hash": canonical_sha256({"rows": selected_rows}),
            "replay_matrix_canonical_hash": canonical_sha256({"rows": replay_rows}),
            "replay_all_accepted": all(bool(row["accepted"]) for row in replay_rows),
        }
        if not (same_result_bytes and same_result_hash and selected_replay["replay_all_accepted"]):
            raise RuntimeError("selected profile same-runtime deterministic replay failed")
        holdout_record = make_future_holdout(profile)
        write_json(HOLDOUT_OUTPUT_PATH, holdout_record)
        study_result = "MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_CANDIDATE_COMPLETED"

    result = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CELL_SCALE_NUMERICAL_ACCEPTANCE_EXTENSION_R1",
        "study_result": study_result,
        "previous_head_sha": EXPECTED_PREDECESSOR_HEAD,
        "input_matrix": matrix,
        "input_matrix_canonical_hash": matrix_hash,
        "input_matrix_hash_verified_before_numerical_execution": True,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "coolprop": str(CoolProp.__version__),
            "platform": sys.platform,
            "machine": platform.platform(),
        },
        "frozen_r94_profile": BASELINE_PROFILE,
        "base_case_reference_replay": {
            "case_count": len(baseline_replays),
            "all_f8_oracles_converged": all(
                bool(row["oracle_converged"]) for row in baseline_replays.values()
            ),
            "cases": baseline_replays,
        },
        "scale_training": {
            "base_case_count": len(base_rows),
            "scale_count": len(SCALE_TEXTS),
            "scale_case_count": len(all_cases),
            "candidate_profile_count": len(candidate_results),
            "candidate_evaluation_count": sum(len(item["rows"]) for item in candidate_results),
            "exact_identity": {
                "bound": True,
                "area_i_f": "f*A_i_1",
                "area_o_f": "f*A_o_1",
                "wall_resistance_f": "R_wall_1/f",
                "G_i_G_wall_G_o_f": "f*(G_i_1,G_wall_1,G_o_1)",
                "q_hc_f": "f*q_hc_1",
                "T_wall_inner_f": "T_wall_inner_1",
                "T_wall_outer_f": "T_wall_outer_1",
                "requires_same_admitted_property_correlation_branch": True,
            },
            "candidate_policies": candidate_results,
        },
        "r95_known_failure_diagnostic": diagnostic,
        "independent_scalar_oracle_scale_replays": {
            "scope": "DYADIC_TRAINING_CASES_ONLY",
            "production_scalar_reduction_selected": False,
            "non_dyadic_holdout_executed": False,
            "replay_count": len(scalar_oracle_replays),
            "all_converged_and_finite": all(
                row["brentq_converged"] and row["all_errors_finite"]
                for row in scalar_oracle_replays
            ),
            "rows": scalar_oracle_replays,
        },
        "selection": {
            "eligible_candidates": [item["candidate_id"] for item in eligible],
            "selected_candidate_id": None if selected is None else selected["candidate_id"],
            "selected_profile": None if selected is None else selected["profile"],
            "selected_profile_canonical_hash": None
            if selected is None
            else selected["profile_canonical_hash"],
            "rationale": selection_rationale,
            "project_selection_policy": [
                "prefer preserving the already reviewed solver controls",
                "among equally successful policies prefer lower evaluation/callback cost",
                "do not select a looser acceptance rule solely because it passes",
                (
                    "P1 dominance comparison uses componentwise observed max oracle errors "
                    "and costs, with no extra numeric tolerance"
                ),
            ],
            "p1_pre_authorized": False,
        },
        "same_runtime_selected_profile_replay": selected_replay,
        "future_non_dyadic_holdout": {
            "path": str(HOLDOUT_OUTPUT_PATH.relative_to(ROOT)),
            "canonical_hash": None if holdout_record is None else holdout_record["canonical_hash"],
            "frozen": holdout_record is not None,
            "executed": False,
            "future_case_count": None if holdout_record is None else 30,
            "independent_review_required_before_execution": True,
        },
        "governance": {
            "r94_modified": False,
            "r95_modified": False,
            "production_code_changed": False,
            "production_solver_executed": False,
            "mesh_threshold_sensitivity_performed": False,
            "full_r95_mesh_matrix_rerun": False,
            "non_dyadic_holdout_executed": False,
            "property_backend_called_for_future_holdout": False,
            "new_authority_self_approval": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
        },
    }
    return add_canonical_hash(result)


def run_selected_secondary() -> dict[str, Any]:
    if not RESULTS_PATH.is_file() or not HOLDOUT_OUTPUT_PATH.is_file():
        raise RuntimeError("primary result and frozen holdout must exist before secondary replay")
    prior = read_json(RESULTS_PATH)
    if prior["input_matrix_canonical_hash"] != EXPECTED_TRAINING_INPUT_HASH:
        raise RuntimeError("secondary runtime observed a changed training matrix")
    selected_id = prior["selection"]["selected_candidate_id"]
    if selected_id is None:
        raise RuntimeError("no selected profile is available for cross-runtime replay")
    frozen_holdout = read_json(HOLDOUT_OUTPUT_PATH)
    if frozen_holdout["execution_controls"]["holdout_executed"] is not False:
        raise RuntimeError("holdout was marked executed before independent review")
    if canonical_sha256(frozen_holdout) != frozen_holdout["canonical_hash"]:
        raise RuntimeError("frozen holdout hash invalid before secondary replay")

    source, matrix, r94, _r95 = frozen_input_bundle()
    matrix_hash = verify_expected_training_hash(matrix, allow_freeze=False)
    if matrix_hash != prior["input_matrix_canonical_hash"]:
        raise RuntimeError("secondary runtime scale-training matrix hash mismatch")
    profile = cast(dict[str, Any], prior["selection"]["selected_profile"])
    references: dict[str, dict[str, Any]] = {}
    cases: list[tuple[Any, dict[str, Any], str]] = []
    for base in source["holdout_matrix"]["fixtures"]:
        reference_case = r94.make_holdout_case(base, BASE_AREA_I_M2, BASE_AREA_O_M2)
        oracle = cast(dict[str, Any], r94.scalar_oracle(reference_case, grid_count=4097))
        references[str(base["case_id"])] = oracle
        for scale_text in SCALE_TEXTS:
            cases.append((scaled_case(r94, base, scale_text), oracle, scale_text))
    rows: list[dict[str, Any]] = []
    for case, oracle, scale_text in cases:
        solved = solve_profile(r94, case, profile)
        scale = float(fraction(scale_text))
        expected = {
            "q_hc_W": scale * float(oracle["q_hc_W"]),
            "T_wall_inner_K": float(oracle["T_wall_inner_K"]),
            "T_wall_outer_K": float(oracle["T_wall_outer_K"]),
        }
        row = dict(solved)
        row["base_case_id"] = str(case.case_id).split("@", maxsplit=1)[0]
        row["scale_fraction_exact"] = scale_text
        row["scale_oracle"] = expected
        row["oracle_errors"] = {
            "q_hc_W": abs(float(row["q_hc_W"]) - expected["q_hc_W"]),
            "T_wall_inner_K": abs(float(row["T_wall_inner_K"]) - expected["T_wall_inner_K"]),
            "T_wall_outer_K": abs(float(row["T_wall_outer_K"]) - expected["T_wall_outer_K"]),
        }
        rows.append(row)
    summary = candidate_summary(rows)
    replay_record = {
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "coolprop": str(CoolProp.__version__),
            "platform": sys.platform,
            "machine": platform.platform(),
        },
        "candidate_id": selected_id,
        "profile_canonical_hash": canonical_sha256(profile),
        "input_matrix_canonical_hash": matrix_hash,
        "case_count": len(rows),
        "summary": summary,
        "result_matrix_canonical_hash": canonical_sha256({"rows": rows}),
        "result_matrix_bytes_sha256": hashlib.sha256(
            canonical_json_bytes({"rows": rows})
        ).hexdigest(),
        "all_pass": bool(summary["all_pass"]),
        "holdout_executed": False,
    }
    prior["secondary_runtime_replay"] = replay_record
    primary_hash = prior["selection"]["selected_profile_canonical_hash"]
    primary_selected = next(
        item
        for item in prior["scale_training"]["candidate_policies"]
        if item["candidate_id"] == selected_id
    )
    primary_result_hash = primary_selected["summary"]["result_matrix_canonical_hash"]
    replay_record["same_numeric_matrix_canonical_hash_as_primary"] = (
        replay_record["result_matrix_canonical_hash"] == primary_result_hash
    )
    replay_record["same_profile_hash_as_primary"] = (
        replay_record["profile_canonical_hash"] == primary_hash
    )
    prior["canonical_hash"] = "PENDING"
    prior = add_canonical_hash(prior)
    write_json(RESULTS_PATH, prior)
    return prior


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-inputs", action="store_true")
    mode.add_argument("--run-primary", action="store_true")
    mode.add_argument("--replay-selected-secondary", action="store_true")
    args = parser.parse_args()

    _source, matrix, _r94, _r95 = frozen_input_bundle()
    if args.freeze_inputs:
        print(
            json.dumps(
                {
                    "training_input_matrix_canonical_hash": canonical_sha256(matrix),
                    "base_case_count": 8,
                    "scale_count": 9,
                    "scale_case_count": len(matrix["scale_cases"]),
                    "candidate_count": len(matrix["candidate_profiles"]),
                    "candidate_evaluation_count": matrix["candidate_case_evaluation_count"],
                    "numerical_solve_performed": False,
                    "non_dyadic_holdout_executed": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.run_primary:
        result = run_primary()
        write_json(RESULTS_PATH, result)
        print(
            json.dumps(
                {
                    "study_result": result["study_result"],
                    "input_matrix_canonical_hash": result["input_matrix_canonical_hash"],
                    "selected_candidate_id": result["selection"]["selected_candidate_id"],
                    "selected_profile_canonical_hash": result["selection"][
                        "selected_profile_canonical_hash"
                    ],
                    "holdout_canonical_hash": result["future_non_dyadic_holdout"]["canonical_hash"],
                    "results_canonical_hash": result["canonical_hash"],
                    "candidate_summaries": [
                        {"candidate_id": row["candidate_id"], **row["summary"]}
                        for row in result["scale_training"]["candidate_policies"]
                    ],
                    "r95_diagnostic": {
                        "reproduced": result["r95_known_failure_diagnostic"][
                            "exact_p0_diagnostic_reproduced"
                        ],
                        "p0_ratio": result["r95_known_failure_diagnostic"][
                            "p0_residual_to_bound_ratios"
                        ],
                    },
                    "selected_same_runtime_replay": result["same_runtime_selected_profile_replay"],
                },
                sort_keys=True,
            )
        )
        return 0
    result = run_selected_secondary()
    print(
        json.dumps(
            {
                "study_result": result["study_result"],
                "secondary_runtime_replay": result["secondary_runtime_replay"],
                "results_canonical_hash": result["canonical_hash"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
