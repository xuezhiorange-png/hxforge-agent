"""Test-only R100 continuous-reference precision qualification.

Replays frozen R95 local scalar-oracle fixtures and R99 evidence without
changing mesh inputs, production code, or solver policy. It compares
Gauss-Legendre with independently implemented composite Simpson integration
and Brent with TOMS748 local roots. Memoization is exact-input, fixture-scoped
and only avoids repeating deterministic property-provider calls.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np
import scipy
from scipy.optimize import root_scalar

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import CoolProp  # noqa: E402

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

REGISTRY_PATH = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
R99_EVIDENCE_PATH = ROOT / ("docs/tasks/evidence/TASK-172-mesh-convergence-qualification-r2.json")
R99_RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-results-r2.json"
)
R99_DOCUMENT_PATH = ROOT / "docs/tasks/TASK-172-v0.7-mesh-convergence-qualification-r2.md"
R99_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r2.py"
)

AUTHORIZED_PREDECESSOR_HEAD = "bc940cb8abe74ec33c56935a2a2a0b60ff628c8a"
R99_REGISTRY_ROOT_HASH = "72b1e6519fca031b54ec21169bb71de5f6bacea4658ef1de348bd9e89a3b6057"
R99_EXTENSION_HASH = "004f8d19ffd85b0d1429e3d2da298676d953c40fa61635a8a8144a3117a0a934"
R99_EVIDENCE_CANONICAL_HASH = "3c91208769e5d261e6f87ba047d5e0ed26d9c17681d1c8a1cc366638613c468e"
R99_RESULTS_CANONICAL_HASH = "cf7c1567dffa1cf84c679e94a18a5f6f18701cc85ad312e1d744d45b4610ba3e"
R95_INPUT_MATRIX_HASH = "b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8"
EXPECTED_M05_GAUSS = {
    "128": 0.2222234220550436,
    "256": 0.22222342205515927,
    "512": 0.22222342205526033,
}
GAUSS_ORDERS = (128, 256, 512, 1024)
SIMPSON_INTERVALS = (512, 1024, 2048)
ROOT_AUDIT_POINTS = 257
WALL_SAMPLE_COUNTS = (257, 513)
ORACLE_TO_MESH_SEPARATION_FACTOR = 1.0e-3
NON_NEAR_ZERO_RELATIVE_LIMIT = 1.0e-8
NEAR_ZERO_ABSOLUTE_LIMIT_W = 1.0e-8
WALL_REFERENCE_STABILITY_CRITERION_K = 1.0e-8


class QualificationError(RuntimeError):
    """Typed error for an incomplete or invalid reference qualification."""


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise QualificationError(detail)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, value: dict[str, Any]) -> bytes:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise QualificationError(f"cannot load frozen runner {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_predecessor() -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    observed = completed.stdout.strip()
    require(
        observed == AUTHORIZED_PREDECESSOR_HEAD,
        f"BLOCKED_HEAD_CHANGED: expected {AUTHORIZED_PREDECESSOR_HEAD}, got {observed}",
    )
    return observed


def verify_history(r99_runner: Any) -> dict[str, Any]:
    registry = read_json(REGISTRY_PATH)
    require(canonical_sha256(registry) == R99_REGISTRY_ROOT_HASH, "R99 registry root changed")
    extension = cast(dict[str, Any], registry["r99_extension"])
    require(canonical_sha256(extension) == R99_EXTENSION_HASH, "R99 extension changed")
    require(
        extension["result"] == "BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2",
        "R99 result is not the frozen blocked finding",
    )
    artifacts = cast(dict[str, Any], extension["artifacts"])
    for path, key in (
        (R99_DOCUMENT_PATH, "document_sha256"),
        (R99_EVIDENCE_PATH, "evidence_file_sha256"),
        (R99_RESULTS_PATH, "results_file_sha256"),
        (R99_RUNNER_PATH, "runner_sha256"),
    ):
        require(file_sha256(path) == artifacts[key], f"R99 artifact hash mismatch: {path.name}")
    r99_evidence = read_json(R99_EVIDENCE_PATH)
    r99_results = read_json(R99_RESULTS_PATH)
    require(
        canonical_sha256(r99_evidence) == R99_EVIDENCE_CANONICAL_HASH,
        "R99 evidence canonical hash changed",
    )
    require(
        canonical_sha256(r99_results) == R99_RESULTS_CANONICAL_HASH,
        "R99 results canonical hash changed",
    )
    require(
        r99_evidence["result"] == "BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2",
        "R99 evidence result mismatch",
    )
    blocker = cast(dict[str, Any], r99_evidence["continuous_oracle_blocker"])
    require(
        blocker["blocking_predicate"] == "FROZEN_GAUSS_REFERENCE_STABILITY_PASS_FOR_M05=false",
        "R99 sole blocker predicate changed",
    )
    for order, expected in EXPECTED_M05_GAUSS.items():
        require(
            float(blocker["Q_ref_W"][order]) == expected,
            f"R99 historical M05 Gauss-{order} value changed",
        )
    r95_extension = cast(dict[str, Any], registry["r95_extension"])
    r98_extension = cast(dict[str, Any], registry["r98_extension"])
    require(
        canonical_sha256(r95_extension) == r99_runner.R95_EXTENSION_HASH,
        "R95 registry extension changed",
    )
    require(
        canonical_sha256(r98_extension) == r99_runner.R98_EXTENSION_HASH,
        "R98 registry extension changed",
    )
    for frozen_extension, paths in (
        (
            r95_extension,
            (
                r99_runner.R95_DOCUMENT_PATH,
                r99_runner.R95_EVIDENCE_PATH,
                r99_runner.R95_RESULTS_PATH,
                r99_runner.R95_RUNNER_PATH,
            ),
        ),
        (
            r98_extension,
            (
                r99_runner.R98_DOCUMENT_PATH,
                r99_runner.R98_EVIDENCE_PATH,
                r99_runner.R98_RESULTS_PATH,
                r99_runner.R98_RUNNER_PATH,
            ),
        ),
    ):
        frozen_artifacts = cast(dict[str, Any], frozen_extension["artifacts"])
        for path, key in zip(
            paths,
            ("document_sha256", "evidence_file_sha256", "results_file_sha256", "runner_sha256"),
            strict=True,
        ):
            require(
                file_sha256(path) == frozen_artifacts[key],
                f"historical artifact hash mismatch: {path.name}",
            )
    r95_evidence = read_json(r99_runner.R95_EVIDENCE_PATH)
    r95_results = read_json(r99_runner.R95_RESULTS_PATH)
    r98_evidence = read_json(r99_runner.R98_EVIDENCE_PATH)
    r98_results = read_json(r99_runner.R98_RESULTS_PATH)
    require(
        canonical_sha256(r95_evidence) == r95_extension["artifacts"]["evidence_canonical_hash"],
        "R95 evidence canonical hash changed",
    )
    require(
        canonical_sha256(r95_results) == r99_runner.R95_RESULTS_CANONICAL_HASH,
        "R95 results canonical hash changed",
    )
    require(
        canonical_sha256(r98_evidence) == r99_runner.R98_EVIDENCE_CANONICAL_HASH,
        "R98 evidence canonical hash changed",
    )
    require(
        canonical_sha256(r98_results) == r99_runner.R98_RESULTS_CANONICAL_HASH,
        "R98 results canonical hash changed",
    )
    r95, r98, r94 = r99_runner.load_frozen_modules()
    matrix = r95.fixture_input_matrix()
    require(
        canonical_sha256(matrix) == R95_INPUT_MATRIX_HASH,
        "R95 frozen input matrix changed",
    )
    require(
        tuple(matrix["comparison"]["threshold_grid"]["duty_relative"])
        == ("1e-2", "1e-3", "1e-4", "1e-5"),
        "R95 threshold grid changed",
    )
    require(
        float(r98.EXPECTED_PROFILE["c_round"]) == 1.0,
        "R98 effective C_round overlay changed",
    )
    require(
        canonical_sha256(r98.EXPECTED_PROFILE) == r99_runner.R98_PROFILE_HASH,
        "R98 effective profile hash changed",
    )
    return {
        "registry_root_canonical_hash": R99_REGISTRY_ROOT_HASH,
        "r99_extension_canonical_hash": canonical_sha256(extension),
        "r99_evidence_canonical_hash": canonical_sha256(r99_evidence),
        "r99_results_canonical_hash": canonical_sha256(r99_results),
        "r95_input_matrix_canonical_hash": canonical_sha256(matrix),
        "r98_effective_c_round": 1.0,
        "frozen_mesh_threshold_grid": ["1e-2", "1e-3", "1e-4", "1e-5"],
        "historical_R99_payloads_verified": True,
        "frozen_mesh_policy_changed": False,
    }


def pointwise_role_domain_audit(r95: Any, fixture_id: str) -> dict[str, Any]:
    xi_values = np.linspace(0.0, 1.0, 4097, dtype=float)
    tube = [r95.evaluate_temperature(fixture_id, "tube", float(xi)) for xi in xi_values]
    shell = [r95.evaluate_temperature(fixture_id, "shell", float(xi)) for xi in xi_values]
    row = r95.fixture_row(fixture_id)
    role = str(row["hot_side"])
    signed = [
        t_value - s_value if role == "TUBE" else s_value - t_value
        for t_value, s_value in zip(tube, shell, strict=True)
    ]
    pressure_tube = float(row["pressure_tube_formula_Pa"])
    pressure_shell = float(row["pressure_shell_formula_Pa"])
    valid = (
        min(tube + shell) >= 298.15
        and max(tube + shell) <= 300.0
        and 100000.0 <= pressure_tube <= 101325.0
        and 100000.0 <= pressure_shell <= 101325.0
        and pressure_tube == pressure_shell
        and 3000.0 < float(row["reynolds_tube"]) < 5000000.0
        and min(signed) > 0.0
    )
    require(valid, f"pointwise role/domain audit failed for {fixture_id}")
    return {
        "explicit_hot_side": role,
        "sample_count": len(xi_values),
        "minimum_signed_hot_minus_cold_delta_K": min(signed),
        "local_role_crossover": False,
        "global_temperature_ranges_overlap": not (min(tube) > max(shell) or min(shell) > max(tube)),
        "all_sampled_states_in_reviewed_domain": True,
    }


def install_exact_fixture_scoped_property_cache(r94: Any) -> dict[str, Any]:
    original = r94.water
    samples = ((298.15, 100000.0), (299.0, 100000.0), (300.0, 101325.0))
    sample_checks: list[dict[str, Any]] = []
    for temperature, pressure in samples:
        first = original(temperature, pressure)
        second = original(temperature, pressure)
        sample_checks.append(
            {
                "temperature_K": temperature,
                "pressure_Pa": pressure,
                "bit_exact": first == second
                and all(float(first[key]).hex() == float(second[key]).hex() for key in first),
            }
        )
    require(all(row["bit_exact"] for row in sample_checks), "property provider replay not exact")
    stats: dict[str, Any] = {"calls": 0, "hits": 0, "misses": 0, "cache": {}}

    def cached_water(temperature_K: float, pressure_Pa: float) -> dict[str, float]:
        stats["calls"] += 1
        key = (float(temperature_K).hex(), float(pressure_Pa).hex())
        cache = cast(dict[tuple[str, str], dict[str, float]], stats["cache"])
        if key not in cache:
            stats["misses"] += 1
            cache[key] = original(float(temperature_K), float(pressure_Pa))
        else:
            stats["hits"] += 1
        return dict(cache[key])

    r94.water = cached_water
    return {
        "stats": stats,
        "sample_checks": sample_checks,
        "cache_policy": "EXACT_BINARY64_T_P_KEYS_FIXTURE_SCOPED_NO_INTERPOLATION",
    }


def quadrature_reduction(
    contributions: list[float],
) -> dict[str, Any]:
    fsum_value = math.fsum(contributions)
    ordinary_value = sum(contributions)
    encoded = canonical_json_bytes({"contributions": contributions})
    decoded = json.loads(encoded)
    roundtrip = [float(value) for value in decoded["contributions"]]
    roundtrip_exact = all(
        original.hex() == copied.hex()
        for original, copied in zip(contributions, roundtrip, strict=True)
    )
    require(roundtrip_exact, "canonical serialization changed a quadrature contribution")
    roundtrip_sum = math.fsum(roundtrip)
    return {
        "term_count": len(contributions),
        "math_fsum_W": fsum_value,
        "ordinary_sum_W": ordinary_value,
        "ordinary_sum_disagreement_W": abs(fsum_value - ordinary_value),
        "canonical_roundtrip_fsum_W": roundtrip_sum,
        "serialization_sum_disagreement_W": abs(fsum_value - roundtrip_sum),
        "individual_float_roundtrip_exact": roundtrip_exact,
    }


def integrate_gauss(
    r95: Any,
    r94: Any,
    fixture_id: str,
    order: int,
    cache: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    nodes, weights = np.polynomial.legendre.leggauss(order)
    contributions = [
        0.5
        * float(weight)
        * float(
            r95.support_oracle_cached(
                r94,
                fixture_id,
                0.5 * (float(node) + 1.0),
                cache,
            )["q_hc_W"]
        )
        for node, weight in zip(nodes, weights, strict=True)
    ]
    reduction = quadrature_reduction(contributions)
    return {
        "order": order,
        "Q_W": reduction["math_fsum_W"],
        "reduction": reduction,
    }


def integrate_simpson(
    r95: Any,
    r94: Any,
    fixture_id: str,
    intervals: int,
    cache: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    step = 1.0 / intervals
    contributions: list[float] = []
    for index in range(intervals + 1):
        xi = index / intervals
        coefficient = 1 if index in (0, intervals) else (4 if index % 2 else 2)
        q_hc = float(r95.support_oracle_cached(r94, fixture_id, xi, cache)["q_hc_W"])
        contributions.append((step / 3.0) * coefficient * q_hc)
    reduction = quadrature_reduction(contributions)
    return {
        "subinterval_count": intervals,
        "sample_count": intervals + 1,
        "Q_W": reduction["math_fsum_W"],
        "reduction": reduction,
    }


def scalar_residual(r94: Any, case: Any, wall_outer_K: float) -> float:
    ho, _ = r94.h_o(case, float(wall_outer_K))
    q_shell = ho * case.area_o_m2 * (float(wall_outer_K) - case.shell_bulk_K)
    wall_inner = float(wall_outer_K) + q_shell * case.wall_resistance_K_W
    require(
        r94.T_MIN_K <= wall_inner <= r94.T_MAX_K,
        f"inner-wall trial outside property domain at {wall_outer_K!r}",
    )
    hi, _ = r94.h_i(case, wall_inner)
    q_tube = hi * case.area_i_m2 * (case.tube_bulk_K - wall_inner)
    return float(q_shell - q_tube)


def crosscheck_root_methods(
    r95: Any,
    r94: Any,
    fixture_id: str,
    cache: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    xi_values = np.linspace(0.0, 1.0, ROOT_AUDIT_POINTS, dtype=float)
    max_differences = {"q_hc_W": 0.0, "T_wall_inner_K": 0.0, "T_wall_outer_K": 0.0}
    max_locations: dict[str, float] = {}
    max_nfev = 0
    all_converged = True
    for xi in xi_values:
        coordinate = float(xi)
        brent = r95.support_oracle_cached(r94, fixture_id, coordinate, cache)
        case = r95.make_r94_case(
            r94,
            fixture_id,
            coordinate,
            r95.Fraction(1),
            cell_identity=f"R100-ROOT-AUDIT-{fixture_id}-{coordinate.hex()}",
        )
        left, right = (float(value) for value in brent["bracket_K"])
        midpoint = 0.5 * (left + right)

        def independent_residual(value: float, *, selected_case: Any = case) -> float:
            return scalar_residual(r94, selected_case, float(value))

        solution = root_scalar(
            independent_residual,
            bracket=(left, right),
            method="toms748",
            xtol=math.ulp(midpoint),
            rtol=4.0 * r94.EPSILON,
            maxiter=256,
        )
        require(
            solution.converged and solution.root is not None,
            f"TOMS748 failed at {fixture_id}/{coordinate.hex()}",
        )
        wall_outer = float(solution.root)
        ho, _ = r94.h_o(case, wall_outer)
        q_ts = ho * case.area_o_m2 * (wall_outer - case.shell_bulk_K)
        wall_inner = wall_outer + q_ts * case.wall_resistance_K_W
        q_hc = case.s_ts * q_ts
        require(
            all(math.isfinite(value) for value in (q_hc, wall_inner, wall_outer))
            and r94.T_MIN_K <= wall_inner <= r94.T_MAX_K
            and r94.T_MIN_K <= wall_outer <= r94.T_MAX_K,
            f"TOMS748 returned invalid state at {fixture_id}/{coordinate.hex()}",
        )
        compared = {
            "q_hc_W": abs(q_hc - float(brent["q_hc_W"])),
            "T_wall_inner_K": abs(wall_inner - float(brent["T_wall_inner_K"])),
            "T_wall_outer_K": abs(wall_outer - float(brent["T_wall_outer_K"])),
        }
        for key, difference in compared.items():
            if difference > max_differences[key]:
                max_differences[key] = difference
                max_locations[key] = coordinate
        all_converged = all_converged and bool(solution.converged)
        max_nfev = max(max_nfev, int(solution.function_calls))
    require(all_converged, f"root method cross-check did not converge for {fixture_id}")
    return {
        "validation_only_method": "TOMS748",
        "production_scalar_reduction_selected": False,
        "point_count": ROOT_AUDIT_POINTS,
        "all_brackets_validated_by_frozen_Brent_oracle": True,
        "all_TOMS748_roots_converged": True,
        "max_function_calls": max_nfev,
        "maximum_absolute_differences": max_differences,
        "maximum_difference_locations_xi": max_locations,
        "q_hc_difference_used_as_U_ROOT_POINTWISE_W": max_differences["q_hc_W"],
        "U_ROOT_INTEGRATED_W": max_differences["q_hc_W"],
        "integrated_root_uncertainty_assumption": "NORMALIZED_SUPPORT_LENGTH_IS_ONE",
        "formal_true_error_bound": False,
    }


def wall_extrema_replay(
    r95: Any,
    r94: Any,
    fixture_id: str,
    cache: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    samples: dict[str, Any] = {}
    for count in WALL_SAMPLE_COUNTS:
        samples[str(count)] = r95.wall_extrema_for_grid(fixture_id, count, cache, r94)
    keys = ("Twi_min", "Twi_max", "Two_min", "Two_max")
    differences = {
        key: abs(
            float(samples[str(WALL_SAMPLE_COUNTS[0])][key]["value_K"])
            - float(samples[str(WALL_SAMPLE_COUNTS[1])][key]["value_K"])
        )
        for key in keys
    }
    max_difference = max(differences.values())
    return {
        "sample_counts": list(WALL_SAMPLE_COUNTS),
        "differences_K": differences,
        "maximum_difference_K": max_difference,
        "criterion_K": WALL_REFERENCE_STABILITY_CRITERION_K,
        "pass": max_difference <= WALL_REFERENCE_STABILITY_CRITERION_K,
    }


def compute_fixture(r95: Any, r94: Any, fixture_id: str) -> dict[str, Any]:
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    domain = pointwise_role_domain_audit(r95, fixture_id)
    gauss = {
        str(order): integrate_gauss(r95, r94, fixture_id, order, cache) for order in GAUSS_ORDERS
    }
    simpson = {
        str(intervals): integrate_simpson(r95, r94, fixture_id, intervals, cache)
        for intervals in SIMPSON_INTERVALS
    }
    root_crosscheck = crosscheck_root_methods(r95, r94, fixture_id, cache)
    wall_stability = wall_extrema_replay(r95, r94, fixture_id, cache)
    q_gl = {order: float(row["Q_W"]) for order, row in gauss.items()}
    q_simpson = {count: float(row["Q_W"]) for count, row in simpson.items()}
    u_gl = max(
        abs(q_gl["256"] - q_gl["512"]),
        abs(q_gl["512"] - q_gl["1024"]),
    )
    u_simpson = max(
        abs(q_simpson["512"] - q_simpson["1024"]),
        abs(q_simpson["1024"] - q_simpson["2048"]),
    )
    u_cross = abs(q_gl["1024"] - q_simpson["2048"])
    u_root = float(root_crosscheck["U_ROOT_INTEGRATED_W"])
    reductions = [
        float(row["reduction"]["ordinary_sum_disagreement_W"])
        for row in list(gauss.values()) + list(simpson.values())
    ] + [
        float(row["reduction"]["serialization_sum_disagreement_W"])
        for row in list(gauss.values()) + list(simpson.values())
    ]
    u_reduction = max(reductions, default=0.0)
    u_q = u_gl + u_simpson + u_cross + u_root + u_reduction
    q_ref = q_gl["1024"]
    near_zero = bool(r95.fixture_row(fixture_id)["near_zero_duty"])
    if near_zero:
        denominator_lower: float | None = None
        observed_metric = u_q
        limit = NEAR_ZERO_ABSOLUTE_LIMIT_W
        criterion = u_q <= limit
        metric = "ABSOLUTE_W"
    else:
        denominator_lower = abs(q_ref) - u_q
        observed_metric = u_q / denominator_lower if denominator_lower > 0.0 else math.inf
        limit = NON_NEAR_ZERO_RELATIVE_LIMIT
        criterion = denominator_lower > 0.0 and observed_metric <= limit
        metric = "RELATIVE"
    reduction_rows = [row["reduction"] for row in list(gauss.values()) + list(simpson.values())]
    require(
        all(bool(row["individual_float_roundtrip_exact"]) for row in reduction_rows),
        f"serialization roundtrip failed for {fixture_id}",
    )
    all_pass = bool(criterion and wall_stability["pass"])
    return {
        "fixture_id": fixture_id,
        "near_zero_duty": near_zero,
        "pointwise_role_domain_audit": domain,
        "gauss_legendre": gauss,
        "composite_simpson": simpson,
        "Q_ref_W": q_ref,
        "continuous_duty_reference_producer": "GAUSS_LEGENDRE_ORDER_1024",
        "uncertainty_components_W": {
            "U_GL": u_gl,
            "U_SIMPSON": u_simpson,
            "U_CROSS": u_cross,
            "U_ROOT_POINTWISE": float(
                root_crosscheck["q_hc_difference_used_as_U_ROOT_POINTWISE_W"]
            ),
            "U_ROOT_INTEGRATED": u_root,
            "U_REDUCTION": u_reduction,
            "U_Q": u_q,
        },
        "precision_policy": {
            "metric": metric,
            "denominator_lower_W": denominator_lower,
            "observed": observed_metric,
            "required_limit": limit,
            "pass": criterion,
        },
        "root_method_crosscheck": root_crosscheck,
        "wall_extrema_stability": wall_stability,
        "reference_uncertainty_is_formal_true_error_bound": False,
        "fixture_pass": all_pass,
        "oracle_node_cache": {
            "unique_support_nodes": len(cache),
            "fixture_scoped": True,
            "exact_binary64_coordinate_keys": True,
        },
    }


def runtime_metadata() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "numpy": str(np.__version__),
        "scipy": str(scipy.__version__),
        "coolprop": str(CoolProp.__version__),
        "platform": platform.platform(),
    }


def run_worker() -> dict[str, Any]:
    predecessor = verify_predecessor()
    r99_runner = load_module(
        ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r2.py",
        "task172_r99_runner_r100",
    )
    history = verify_history(r99_runner)
    r95, _, r94 = r99_runner.load_frozen_modules()
    require(
        canonical_sha256(r95.fixture_input_matrix()) == R95_INPUT_MATRIX_HASH,
        "frozen R95 input matrix replay failed",
    )
    cache_metadata = install_exact_fixture_scoped_property_cache(r94)
    fixture_results: list[dict[str, Any]] = []
    for row in r95.FIXTURE_ROWS:
        fixture_id = str(row["fixture_id"])
        cache = cast(dict[tuple[str, str], dict[str, float]], cache_metadata["stats"]["cache"])
        cache.clear()
        fixture_results.append(compute_fixture(r95, r94, fixture_id))
        print(f"qualified continuous reference fixture {fixture_id}", flush=True)
    m05 = next(row for row in fixture_results if row["fixture_id"] == "M05")
    observed_m05 = {
        order: float(m05["gauss_legendre"][order]["Q_W"]) for order in ("128", "256", "512")
    }
    historical_exact = {
        order: observed_m05[order] == expected for order, expected in EXPECTED_M05_GAUSS.items()
    }
    historical_criterion = 64.0 * math.ulp(observed_m05["512"])
    observed_historical_gate = abs(observed_m05["256"] - observed_m05["512"]) > historical_criterion
    stats = cache_metadata["stats"]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_CONTINUOUS_REFERENCE_ORACLE_PRECISION_QUALIFICATION_R1",
        "authorized_predecessor_head": predecessor,
        "runtime": runtime_metadata(),
        "runner_sha256": file_sha256(Path(__file__)),
        "upstream_replay": history,
        "fixture_results": fixture_results,
        "historical_M05_replay": {
            "expected_R99_Q_GL_W": EXPECTED_M05_GAUSS,
            "observed_Q_GL_W": observed_m05,
            "exact_values_match": historical_exact,
            "historical_64_ulp_criterion_W": historical_criterion,
            "historical_gate_still_fails": observed_historical_gate,
        },
        "property_callback_memoization": {
            "policy": cache_metadata["cache_policy"],
            "representative_provider_replays": cache_metadata["sample_checks"],
            "calls": int(stats["calls"]),
            "hits": int(stats["hits"]),
            "misses": int(stats["misses"]),
            "no_interpolation_or_state_averaging": True,
        },
        "mesh_policy": {
            "mesh_threshold_sensitivity_performed": False,
            "full_mesh_matrix_rerun": False,
            "mesh_sequences_changed": False,
            "mesh_thresholds_changed": False,
            "mesh_convergence_status_adjudicated": False,
            "task173_or_task174_solve_performed": False,
        },
    }
    payload["canonical_hash"] = canonical_sha256(payload)
    return payload


def cross_runtime_differences(py311: dict[str, Any], py312: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    keys = ("Q_ref_W", "U_GL", "U_SIMPSON", "U_CROSS", "U_ROOT_INTEGRATED", "U_REDUCTION", "U_Q")
    for fixture311, fixture312 in zip(
        py311["fixture_results"], py312["fixture_results"], strict=True
    ):
        fixture_id = str(fixture311["fixture_id"])
        output[fixture_id] = {}
        for key in keys:
            left = (
                float(fixture311["Q_ref_W"])
                if key == "Q_ref_W"
                else float(fixture311["uncertainty_components_W"][key])
            )
            right = (
                float(fixture312["Q_ref_W"])
                if key == "Q_ref_W"
                else float(fixture312["uncertainty_components_W"][key])
            )
            output[fixture_id][key] = {
                "python311": left,
                "python312": right,
                "absolute_difference": abs(left - right),
                "exactly_equal": left == right,
            }
    return output


def combine_workers(
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    worker_bytes = {key: path.read_bytes() for key, path in paths.items()}
    workers = {key: json.loads(value) for key, value in worker_bytes.items()}
    require(
        worker_bytes["py311_first"] == worker_bytes["py311_repeat"],
        "Python 3.11 deterministic full-reference replay differs byte-for-byte",
    )
    require(
        worker_bytes["py312_first"] == worker_bytes["py312_repeat"],
        "Python 3.12 deterministic full-reference replay differs byte-for-byte",
    )
    py311 = cast(dict[str, Any], workers["py311_first"])
    py312 = cast(dict[str, Any], workers["py312_first"])
    require(py311["runtime"]["python"].startswith("3.11."), "Python 3.11 worker runtime mismatch")
    require(py312["runtime"]["python"].startswith("3.12."), "Python 3.12 worker runtime mismatch")
    fixtures311 = cast(list[dict[str, Any]], py311["fixture_results"])
    fixtures312 = cast(list[dict[str, Any]], py312["fixture_results"])
    all_pass = (
        len(fixtures311) == 6
        and len(fixtures312) == 6
        and all(bool(row["fixture_pass"]) for row in fixtures311 + fixtures312)
    )
    exact_historical = all(
        bool(value)
        for value in cast(
            dict[str, bool], py311["historical_M05_replay"]["exact_values_match"]
        ).values()
    )
    historical_gate = bool(py311["historical_M05_replay"]["historical_gate_still_fails"])
    runtime_replay = {
        "python311": py311["runtime"],
        "python312": py312["runtime"],
        "python311_full_qualification_repeated_bytes_equal": True,
        "python311_full_qualification_repeated_sha256_equal": sha256_bytes(
            worker_bytes["py311_first"]
        )
        == sha256_bytes(worker_bytes["py311_repeat"]),
        "python312_full_qualification_repeated_bytes_equal": True,
        "python312_full_qualification_repeated_sha256_equal": sha256_bytes(
            worker_bytes["py312_first"]
        )
        == sha256_bytes(worker_bytes["py312_repeat"]),
        "cross_runtime_exact_equality_required": False,
        "cross_runtime_differences": cross_runtime_differences(py311, py312),
    }
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_CONTINUOUS_REFERENCE_ORACLE_PRECISION_QUALIFICATION_R1",
        "authorized_predecessor_head": AUTHORIZED_PREDECESSOR_HEAD,
        "historical_R99_M05_64_ulp_gate_reproduced": historical_gate,
        "historical_M05_Gauss_128_256_512_reproduced_exactly": exact_historical,
        "final_result_ulp_only_is_total_continuous_reference_error_bound": False,
        "R95_64_ulp_rule_status": (
            "HISTORICAL_REFERENCE_STABILITY_HEURISTIC_NOT_TOTAL_ORACLE_ERROR_BOUND"
        ),
        "reference_policy": {
            "classification": "PROJECT_REFERENCE_PRECISION_POLICY",
            "oracle_to_mesh_threshold_separation_factor": ORACLE_TO_MESH_SEPARATION_FACTOR,
            "non_near_zero_relative_limit": NON_NEAR_ZERO_RELATIVE_LIMIT,
            "near_zero_absolute_limit_W": NEAR_ZERO_ABSOLUTE_LIMIT_W,
            "wall_reference_stability_criterion_K": WALL_REFERENCE_STABILITY_CRITERION_K,
            "independent_quadrature_family_count": 2,
            "gauss_orders": list(GAUSS_ORDERS),
            "composite_simpson_subintervals": list(SIMPSON_INTERVALS),
            "local_root_validation_method": "TOMS748",
            "production_scalar_reduction_selected": False,
            "uncertainty_definition": "U_Q=U_GL+U_SIMPSON+U_CROSS+U_ROOT_INTEGRATED+U_REDUCTION",
            "uncertainty_classification": "MEASURED_CONSERVATIVE_NUMERICAL_REFERENCE_UNCERTAINTY",
            "oracle_uncertainty_is_formal_true_error_bound": False,
            "reference_uncertainty_propagation_required": True,
            "continuous_duty_reference_producer": "GAUSS_LEGENDRE_ORDER_1024",
        },
        "fixture_results_python311": fixtures311,
        "fixture_results_python312": fixtures312,
        "wall_reference_policy_changed": False,
        "all_six_fixtures_pass_both_runtimes": all_pass,
        "runtime_replay": runtime_replay,
        "decision": {
            "result": (
                "CONTINUOUS_REFERENCE_ORACLE_PRECISION_CANDIDATE_COMPLETED"
                if all_pass and historical_gate and exact_historical
                else "BLOCKED_CONTINUOUS_REFERENCE_ORACLE_PRECISION_QUALIFICATION"
            ),
            "continuous_reference_oracle_precision_policy_bound": bool(
                all_pass and historical_gate and exact_historical
            ),
            "lifecycle": (
                "PROPOSED_AUTHORITY_REVIEW_PENDING"
                if all_pass and historical_gate and exact_historical
                else "NONE"
            ),
            "mesh_convergence_canonical_blocker_removed": False,
            "effective_remaining_task172_entry_blocker_count": 1,
            "task172_entry_authority_complete": False,
            "next_gate": (
                "AUTHORIZE_TASK172_CONTINUOUS_REFERENCE_ORACLE_PRECISION_INDEPENDENT_REVIEW_R1_ONLY"
                if all_pass and historical_gate and exact_historical
                else "NONE_UNTIL_SEPARATELY_AUTHORIZED"
            ),
        },
        "governance": {
            "production_code_changed": False,
            "task172_implementation_started": False,
            "reference_oracle_numerical_experiment_performed": True,
            "mesh_study_performed": False,
            "mesh_threshold_sensitivity_performed": False,
            "full_mesh_matrix_rerun": False,
            "task173_or_task174_solve_performed": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
            "stop": True,
        },
        "worker_artifacts": {
            key: {"sha256": sha256_bytes(value), "byte_identical_repeat": True}
            for key, value in worker_bytes.items()
        },
    }
    result["canonical_hash"] = canonical_sha256(result)
    write_json(output_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--worker", action="store_true")
    modes.add_argument("--combine", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--py311-first", type=Path)
    parser.add_argument("--py311-repeat", type=Path)
    parser.add_argument("--py312-first", type=Path)
    parser.add_argument("--py312-repeat", type=Path)
    args = parser.parse_args()
    try:
        if args.worker:
            payload = run_worker()
            write_json(args.output, payload)
            print(
                json.dumps(
                    {
                        "output": str(args.output),
                        "runtime": payload["runtime"],
                        "fixture_passes": {
                            row["fixture_id"]: row["fixture_pass"]
                            for row in payload["fixture_results"]
                        },
                        "canonical_hash": payload["canonical_hash"],
                    },
                    sort_keys=True,
                    indent=2,
                    allow_nan=False,
                ),
                flush=True,
            )
            return 0
        inputs = {
            "py311_first": args.py311_first,
            "py311_repeat": args.py311_repeat,
            "py312_first": args.py312_first,
            "py312_repeat": args.py312_repeat,
        }
        require(
            all(path is not None for path in inputs.values()), "--combine needs four worker files"
        )
        result = combine_workers(
            cast(dict[str, Path], inputs),
            args.output,
        )
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "decision": result["decision"],
                    "canonical_hash": result["canonical_hash"],
                },
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ),
            flush=True,
        )
        return 0
    except Exception as exc:
        print(f"R100_QUALIFICATION_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
