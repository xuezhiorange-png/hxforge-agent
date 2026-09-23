"""Independent, test-only replay of the frozen R100 reference precision candidate.

This runner does not modify mesh inputs or production code. NumPy and SciPy
produce separate Gauss-Legendre nodes and weights; both are evaluated against
the same frozen R95 local-support oracle and exact-coordinate property cache.
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
from scipy.optimize import minimize_scalar, root_scalar
from scipy.special import roots_legendre

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import CoolProp  # noqa: E402

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

REGISTRY_PATH = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
R95_RUNNER_PATH = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r1.py"
R99_RUNNER_PATH = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r2.py"
R100_RUNNER_PATH = (
    ROOT / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-runner-r1.py"
)
R100_RESULTS_PATH = (
    ROOT / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-results-r1.json"
)
R100_DOCUMENT_PATH = (
    ROOT / "docs/tasks/TASK-172-v0.7-continuous-reference-oracle-precision-qualification-r1.md"
)
R100_EVIDENCE_PATH = (
    ROOT
    / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-qualification-r1.json"
)

EXPECTED_HEAD = "0af454f0c9850de22b3d70f2006e5e3c4d1e1075"
EXPECTED_R100_EXTENSION_HASH = "9e1210f35c3e52f83cdffde3b23f0fc78f8b8b75e1fbbd2e35c07039095b6701"
EXPECTED_R100_DOCUMENT_SHA256 = "c7a5415006e319a6f999937d883bb0d520eee6f84d4e05ee4ef752df1448d118"
EXPECTED_R100_EVIDENCE_SHA256 = "0d719a48ef4ccee07c5f0b161e844f635e0c97ed101964825880b744e1fdd0c5"
EXPECTED_R100_EVIDENCE_CANONICAL = (
    "d4be20147aa641c189bef443fd497987230fe6bd1d7b4edf4f2171af3ca356bb"
)
EXPECTED_R100_RESULTS_SHA256 = "b7844e566faab902fef1bc90eda3c991f3e1271da96effe78c693efe4fac6b43"
EXPECTED_R100_RESULTS_CANONICAL = "17799de16c5b4a7362bda4595d4d5af9e46ee1633d89e852e51cc58419caf5d0"
EXPECTED_R100_RUNNER_SHA256 = "a6ea1850bca18bed700f8313ffd208d4a27fa8750604a1529fad9a4a4a2084ba"
EXPECTED_R99_M05 = {
    128: 0.2222234220550436,
    256: 0.22222342205515927,
    512: 0.22222342205526033,
}
ORDERS = (128, 256, 512, 1024)
SIMPSON_INTERVALS = (512, 1024, 2048)
ROOT_POINTS = 257
EXTREMA_COUNTS = (257, 513)


class ReviewReplayError(RuntimeError):
    """A fail-closed independent replay error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewReplayError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload + "\n", encoding="utf-8")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReviewReplayError(f"cannot load frozen reference {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_baseline_and_r100() -> dict[str, Any]:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require(head == EXPECTED_HEAD, f"BLOCKED_HEAD_CHANGED: expected {EXPECTED_HEAD}, got {head}")
    registry = load_json(REGISTRY_PATH)
    baseline_registry = json.loads(
        subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "show",
                f"{EXPECTED_HEAD}:docs/tasks/TASK-172-v0.7-authority-registry-r1.json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    historical_keys = [key for key in baseline_registry if key.endswith("_extension")]
    require(
        all(registry.get(key) == baseline_registry[key] for key in historical_keys),
        "one or more R1-R100 registry extensions differ from the authorized baseline",
    )
    extension = cast(dict[str, Any], registry["r100_extension"])
    require(canonical_sha256(extension) == EXPECTED_R100_EXTENSION_HASH, "R100 extension changed")
    require(
        file_sha256(R100_DOCUMENT_PATH) == EXPECTED_R100_DOCUMENT_SHA256, "R100 document changed"
    )
    require(
        file_sha256(R100_EVIDENCE_PATH) == EXPECTED_R100_EVIDENCE_SHA256, "R100 evidence changed"
    )
    require(file_sha256(R100_RESULTS_PATH) == EXPECTED_R100_RESULTS_SHA256, "R100 results changed")
    require(file_sha256(R100_RUNNER_PATH) == EXPECTED_R100_RUNNER_SHA256, "R100 runner changed")
    results = load_json(R100_RESULTS_PATH)
    evidence = load_json(R100_EVIDENCE_PATH)
    require(
        canonical_sha256(evidence) == EXPECTED_R100_EVIDENCE_CANONICAL,
        "R100 evidence canonical hash changed",
    )
    require(
        canonical_sha256(results) == EXPECTED_R100_RESULTS_CANONICAL,
        "R100 result canonical hash changed",
    )
    require(
        results["decision"]["result"]
        == "CONTINUOUS_REFERENCE_ORACLE_PRECISION_CANDIDATE_COMPLETED",
        "R100 result status changed",
    )
    return {
        "head": head,
        "registry_extension_canonical_hash": canonical_sha256(extension),
        "R100_document_sha256": file_sha256(R100_DOCUMENT_PATH),
        "R100_evidence_sha256": file_sha256(R100_EVIDENCE_PATH),
        "R100_evidence_canonical_hash": canonical_sha256(evidence),
        "R100_results_sha256": file_sha256(R100_RESULTS_PATH),
        "R100_results_canonical_hash": canonical_sha256(results),
        "R100_runner_sha256": file_sha256(R100_RUNNER_PATH),
        "R100_candidate_status_replayed": True,
    }


def support_state(
    r95: Any, r94: Any, fixture_id: str, xi: float, cache: dict[str, Any]
) -> dict[str, Any]:
    return r95.support_oracle_cached(r94, fixture_id, float(xi), cache)


def reduction_record(contributions: list[float]) -> dict[str, Any]:
    fsum_value = math.fsum(contributions)
    ordinary_value = sum(contributions)
    encoded = canonical_json_bytes({"contributions": contributions})
    decoded = json.loads(encoded)
    roundtrip = [float(value) for value in decoded["contributions"]]
    exact = all(a.hex() == b.hex() for a, b in zip(contributions, roundtrip, strict=True))
    require(exact, "canonical serialization roundtrip changed a binary64 term")
    return {
        "math_fsum_W": fsum_value,
        "ordinary_sum_W": ordinary_value,
        "ordinary_sum_abs_difference_W": abs(fsum_value - ordinary_value),
        "canonical_roundtrip_fsum_W": math.fsum(roundtrip),
        "canonical_roundtrip_sum_abs_difference_W": abs(fsum_value - math.fsum(roundtrip)),
        "serialization_roundtrip_exact": exact,
        "term_count": len(contributions),
    }


def gauss_row(
    source: str, order: int, r95: Any, r94: Any, fixture_id: str, cache: dict[str, Any]
) -> dict[str, Any]:
    if source == "NUMPY_LEGGAUSS":
        nodes, weights = np.polynomial.legendre.leggauss(order)
    elif source == "SCIPY_ROOTS_LEGENDRE":
        nodes, weights = roots_legendre(order)
    else:
        raise ReviewReplayError(f"unrecognized quadrature source {source}")
    node_list = [float(value) for value in nodes]
    weight_list = [float(value) for value in weights]
    contributions = [
        0.5
        * weight
        * float(support_state(r95, r94, fixture_id, 0.5 * (node + 1.0), cache)["q_hc_W"])
        for node, weight in zip(node_list, weight_list, strict=True)
    ]
    reduction = reduction_record(contributions)
    node_mirror = max(abs(node_list[i] + node_list[-1 - i]) for i in range(order))
    weight_mirror = max(abs(weight_list[i] - weight_list[-1 - i]) for i in range(order))
    return {
        "implementation": source,
        "order": order,
        "Q_W": reduction["math_fsum_W"],
        "reduction": reduction,
        "finite_nodes_weights_contributions": all(
            math.isfinite(value) for value in node_list + weight_list + contributions
        ),
        "weight_sum": math.fsum(weight_list),
        "weight_sum_deviation_from_2": abs(math.fsum(weight_list) - 2.0),
        "max_node_symmetry_deviation": node_mirror,
        "max_weight_symmetry_deviation": weight_mirror,
    }


def simpson_row(
    r95: Any, r94: Any, fixture_id: str, intervals: int, cache: dict[str, Any]
) -> dict[str, Any]:
    step = 1.0 / intervals
    terms: list[float] = []
    for index in range(intervals + 1):
        coefficient = 1 if index in (0, intervals) else (4 if index % 2 else 2)
        q_hc = float(support_state(r95, r94, fixture_id, index / intervals, cache)["q_hc_W"])
        terms.append((step / 3.0) * coefficient * q_hc)
    reduction = reduction_record(terms)
    return {"subintervals": intervals, "Q_W": reduction["math_fsum_W"], "reduction": reduction}


def independent_toms_residual(r94: Any, case: Any, wall_outer_K: float) -> float:
    h_o, _ = r94.h_o(case, float(wall_outer_K))
    q_shell = h_o * case.area_o_m2 * (float(wall_outer_K) - case.shell_bulk_K)
    wall_inner = float(wall_outer_K) + q_shell * case.wall_resistance_K_W
    require(r94.T_MIN_K <= wall_inner <= r94.T_MAX_K, "TOMS trial left frozen property domain")
    h_i, _ = r94.h_i(case, wall_inner)
    q_tube = h_i * case.area_i_m2 * (case.tube_bulk_K - wall_inner)
    return float(q_shell - q_tube)


def root_method_replay(
    r95: Any, r94: Any, fixture_id: str, cache: dict[str, Any]
) -> dict[str, Any]:
    max_differences = {"q_hc_W": 0.0, "T_wall_inner_K": 0.0, "T_wall_outer_K": 0.0}
    locations: dict[str, float] = {}
    all_converged = True
    max_calls = 0
    for xi in np.linspace(0.0, 1.0, ROOT_POINTS, dtype=float):
        coordinate = float(xi)
        brent = support_state(r95, r94, fixture_id, coordinate, cache)
        case = r95.make_r94_case(
            r94,
            fixture_id,
            coordinate,
            r95.Fraction(1),
            cell_identity=f"R101-ROOT-{fixture_id}-{coordinate.hex()}",
        )
        left, right = (float(value) for value in brent["bracket_K"])
        solution = root_scalar(
            lambda value, selected_case=case: independent_toms_residual(
                r94, selected_case, float(value)
            ),
            bracket=(left, right),
            method="toms748",
            xtol=math.ulp(0.5 * (left + right)),
            rtol=4.0 * r94.EPSILON,
            maxiter=256,
        )
        require(
            solution.converged and solution.root is not None,
            f"TOMS748 failed {fixture_id}/{coordinate.hex()}",
        )
        wall_outer = float(solution.root)
        h_o, _ = r94.h_o(case, wall_outer)
        q_ts = h_o * case.area_o_m2 * (wall_outer - case.shell_bulk_K)
        wall_inner = wall_outer + q_ts * case.wall_resistance_K_W
        observed = {
            "q_hc_W": abs(case.s_ts * q_ts - float(brent["q_hc_W"])),
            "T_wall_inner_K": abs(wall_inner - float(brent["T_wall_inner_K"])),
            "T_wall_outer_K": abs(wall_outer - float(brent["T_wall_outer_K"])),
        }
        for key, value in observed.items():
            if value > max_differences[key]:
                max_differences[key] = value
                locations[key] = coordinate
        all_converged = all_converged and bool(solution.converged)
        max_calls = max(max_calls, int(solution.function_calls))
    require(all_converged, f"TOMS748 nonconvergence {fixture_id}")
    return {
        "point_count": ROOT_POINTS,
        "comparison": "FROZEN_R95_BRENT_VS_INDEPENDENT_SCIPY_TOMS748",
        "all_toms748_converged": all_converged,
        "maximum_function_calls": max_calls,
        "maximum_absolute_differences": max_differences,
        "maximum_difference_locations_xi": locations,
        "U_ROOT_POINTWISE_OBSERVED_W": max_differences["q_hc_W"],
        "U_ROOT_INTEGRATED_OBSERVED_W": max_differences["q_hc_W"],
        "integration_rule_used": (
            "257_POINT_MAX_TIMES_NORMALIZED_LENGTH_1;EMPIRICAL_NOT_GLOBAL_BOUND"
        ),
    }


def wall_extrema(
    r95: Any, r94: Any, fixture_id: str, count: int, cache: dict[str, Any]
) -> dict[str, float]:
    xis = np.linspace(0.0, 1.0, count, dtype=float)
    states = [support_state(r95, r94, fixture_id, float(xi), cache) for xi in xis]
    keys = {
        "Twi_min": ("T_wall_inner_K", "min"),
        "Twi_max": ("T_wall_inner_K", "max"),
        "Two_min": ("T_wall_outer_K", "min"),
        "Two_max": ("T_wall_outer_K", "max"),
    }
    out: dict[str, float] = {}
    for out_key, (state_key, mode) in keys.items():
        values = [float(row[state_key]) for row in states]
        candidates = [values[0], values[-1]]
        for index in range(1, count - 1):
            extremum = (
                values[index] <= values[index - 1] and values[index] <= values[index + 1]
                if mode == "min"
                else values[index] >= values[index - 1] and values[index] >= values[index + 1]
            )
            if not extremum:
                continue

            def objective(
                coordinate: float,
                selected_state_key: str = state_key,
                selected_mode: str = mode,
            ) -> float:
                value = float(
                    support_state(r95, r94, fixture_id, coordinate, cache)[selected_state_key]
                )
                return value if selected_mode == "min" else -value

            optimized = minimize_scalar(
                objective,
                bounds=(float(xis[index - 1]), float(xis[index + 1])),
                method="bounded",
                options={"xatol": 8.0 * np.finfo(float).eps},
            )
            require(optimized.success, f"wall extremum replay failed {fixture_id}/{out_key}")
            candidates.append(float(optimized.fun) if mode == "min" else -float(optimized.fun))
        out[out_key] = min(candidates) if mode == "min" else max(candidates)
    return out


def fixture_replay(r95: Any, r94: Any, fixture_id: str) -> dict[str, Any]:
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    np_rows: dict[str, Any] = {}
    sp_rows: dict[str, Any] = {}
    comparisons: dict[str, Any] = {}
    for order in ORDERS:
        left = gauss_row("NUMPY_LEGGAUSS", order, r95, r94, fixture_id, cache)
        right = gauss_row("SCIPY_ROOTS_LEGENDRE", order, r95, r94, fixture_id, cache)
        np_nodes, np_weights = np.polynomial.legendre.leggauss(order)
        sp_nodes, sp_weights = roots_legendre(order)
        node_differences = np.abs(np_nodes - sp_nodes)
        weight_differences = np.abs(np_weights - sp_weights)
        key = str(order)
        np_rows[key] = left
        sp_rows[key] = right
        comparisons[key] = {
            "Q_numpy_W": left["Q_W"],
            "Q_scipy_W": right["Q_W"],
            "abs_difference_W": abs(float(left["Q_W"]) - float(right["Q_W"])),
            "relative_difference": abs(float(left["Q_W"]) - float(right["Q_W"]))
            / abs(float(left["Q_W"]))
            if left["Q_W"] != 0.0
            else None,
            "max_node_absolute_difference": float(np.max(node_differences)),
            "max_weight_absolute_difference": float(np.max(weight_differences)),
            "node_arrays_are_distinct_objects": np_nodes is not sp_nodes,
            "weight_arrays_are_distinct_objects": np_weights is not sp_weights,
            "numpy_finite_checks_pass": bool(left["finite_nodes_weights_contributions"]),
            "scipy_finite_checks_pass": bool(right["finite_nodes_weights_contributions"]),
            "numpy_weight_sum_deviation": left["weight_sum_deviation_from_2"],
            "scipy_weight_sum_deviation": right["weight_sum_deviation_from_2"],
            "numpy_node_symmetry_deviation": left["max_node_symmetry_deviation"],
            "scipy_node_symmetry_deviation": right["max_node_symmetry_deviation"],
            "numpy_weight_symmetry_deviation": left["max_weight_symmetry_deviation"],
            "scipy_weight_symmetry_deviation": right["max_weight_symmetry_deviation"],
        }
    simpson = {
        str(count): simpson_row(r95, r94, fixture_id, count, cache) for count in SIMPSON_INTERVALS
    }
    roots = root_method_replay(r95, r94, fixture_id, cache)
    extrema_rows = {
        str(count): wall_extrema(r95, r94, fixture_id, count, cache) for count in EXTREMA_COUNTS
    }
    extrema_keys = ("Twi_min", "Twi_max", "Two_min", "Two_max")
    extrema_differences = {
        key: abs(
            extrema_rows[str(EXTREMA_COUNTS[0])][key] - extrema_rows[str(EXTREMA_COUNTS[1])][key]
        )
        for key in extrema_keys
    }
    qn = {order: float(np_rows[order]["Q_W"]) for order in map(str, ORDERS)}
    qs = {count: float(simpson[count]["Q_W"]) for count in map(str, SIMPSON_INTERVALS)}
    u_gl = max(abs(qn["256"] - qn["512"]), abs(qn["512"] - qn["1024"]))
    u_simpson = max(abs(qs["512"] - qs["1024"]), abs(qs["1024"] - qs["2048"]))
    u_cross = abs(qn["1024"] - qs["2048"])
    reduction_disagreements = [
        float(row["reduction"]["ordinary_sum_abs_difference_W"])
        for row in list(np_rows.values()) + list(simpson.values())
    ] + [
        float(row["reduction"]["canonical_roundtrip_sum_abs_difference_W"])
        for row in list(np_rows.values()) + list(simpson.values())
    ]
    u_reduction = max(reduction_disagreements, default=0.0)
    u_q = u_gl + u_simpson + u_cross + float(roots["U_ROOT_INTEGRATED_OBSERVED_W"]) + u_reduction
    r100 = load_json(R100_RESULTS_PATH)
    runtime_key = (
        "fixture_results_python311"
        if sys.version_info.minor == 11
        else "fixture_results_python312"
        if sys.version_info.minor == 12
        else ""
    )
    require(bool(runtime_key), "independent replay requires Python 3.11 or 3.12")
    r100_fixture = next(row for row in r100[runtime_key] if row["fixture_id"] == fixture_id)
    r100_simp = {str(key): value for key, value in r100_fixture["composite_simpson"].items()}
    r100_gl = {str(key): value for key, value in r100_fixture["gauss_legendre"].items()}
    r100_exact = (
        all(
            float(np_rows[str(order)]["Q_W"]) == float(r100_gl[str(order)]["Q_W"])
            for order in ORDERS
        )
        and all(
            float(simpson[str(count)]["Q_W"]) == float(r100_simp[str(count)]["Q_W"])
            for count in SIMPSON_INTERVALS
        )
        and u_q == float(r100_fixture["uncertainty_components_W"]["U_Q"])
    )
    return {
        "fixture_id": fixture_id,
        "numpy_gauss_legendre": np_rows,
        "scipy_roots_legendre": sp_rows,
        "independent_crosscheck_by_order": comparisons,
        "simpson": simpson,
        "root_crosscheck": roots,
        "wall_extrema_257_513": {
            "values": extrema_rows,
            "absolute_differences_K": extrema_differences,
            "maximum_absolute_difference_K": max(extrema_differences.values()),
        },
        "reproduced_R100_U_components_W": {
            "U_GL": u_gl,
            "U_SIMPSON": u_simpson,
            "U_CROSS": u_cross,
            "U_ROOT_INTEGRATED_OBSERVED": float(roots["U_ROOT_INTEGRATED_OBSERVED_W"]),
            "U_REDUCTION": u_reduction,
            "U_Q": u_q,
        },
        "Q_ref_numpy_gl1024_W": qn["1024"],
        "Q_ref_scipy_gl1024_W": float(sp_rows["1024"]["Q_W"]),
        "R100_numeric_values_exactly_reproduced": r100_exact,
        "reference_uncertainty_is_formal_true_error_bound": False,
        "fixture_scoped_exact_coordinate_cache_size": len(cache),
    }


def run_worker() -> dict[str, Any]:
    baseline = verify_baseline_and_r100()
    r99 = load_module(R99_RUNNER_PATH, "task172_r99_runner_r101")
    r95, _, r94 = r99.load_frozen_modules()
    fixture_results = []
    original_water = r94.water
    for row in r95.FIXTURE_ROWS:
        fixture_id = str(row["fixture_id"])
        property_cache: dict[tuple[str, str], dict[str, float]] = {}

        def cached_water(
            temperature_K: float,
            pressure_Pa: float,
            selected_cache: dict[tuple[str, str], dict[str, float]] = property_cache,
            selected_original: Any = original_water,
        ) -> dict[str, float]:
            key = (float(temperature_K).hex(), float(pressure_Pa).hex())
            if key not in selected_cache:
                selected_cache[key] = selected_original(float(temperature_K), float(pressure_Pa))
            return dict(selected_cache[key])

        r94.water = cached_water
        try:
            fixture_results.append(fixture_replay(r95, r94, fixture_id))
        finally:
            r94.water = original_water
        print(f"independently replayed {fixture_id}", flush=True)
    m05 = next(row for row in fixture_results if row["fixture_id"] == "M05")
    m05_numpy = m05["numpy_gauss_legendre"]
    observed_m05 = {
        str(order): float(m05_numpy[str(order)]["Q_W"]) for order in (128, 256, 512, 1024)
    }
    ulp_criterion = 64.0 * math.ulp(observed_m05["512"])
    historical_gate_fails = abs(observed_m05["256"] - observed_m05["512"]) > ulp_criterion
    expected_r99_exact = all(
        observed_m05[str(order)] == value for order, value in EXPECTED_R99_M05.items()
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_CONTINUOUS_REFERENCE_ORACLE_PRECISION_INDEPENDENT_REVIEW_R1",
        "authorized_predecessor_head": EXPECTED_HEAD,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": str(np.__version__),
            "scipy": str(scipy.__version__),
            "coolprop": str(CoolProp.__version__),
            "platform": platform.platform(),
        },
        "baseline_and_target": baseline,
        "quadrature_implementations": {
            "numpy": "numpy.polynomial.legendre.leggauss; independent call and arrays",
            "scipy": "scipy.special.roots_legendre; independent call and arrays",
            "orders": list(ORDERS),
            "node_weight_arrays_shared": False,
        },
        "fixture_results": fixture_results,
        "R99_M05_replay": {
            "expected_128_256_512_W": {str(key): value for key, value in EXPECTED_R99_M05.items()},
            "observed_numpy_128_256_512_1024_W": observed_m05,
            "historical_128_256_512_exactly_preserved": expected_r99_exact,
            "64_ulp_criterion_W": ulp_criterion,
            "256_512_difference_W": abs(observed_m05["256"] - observed_m05["512"]),
            "historical_gate_still_fails": historical_gate_fails,
        },
        "non_mesh_scope": {
            "mesh_study_performed": False,
            "mesh_threshold_sensitivity_performed": False,
            "full_mesh_matrix_rerun": False,
            "mesh_threshold_changed": False,
            "task173_solve_performed": False,
            "task174_solve_performed": False,
        },
    }
    payload["canonical_hash"] = canonical_sha256(payload)
    return payload


def verify_worker(payload: dict[str, Any], expected_minor: int) -> None:
    candidate = dict(payload)
    recorded_hash = str(candidate.pop("canonical_hash"))
    require(canonical_sha256(candidate) == recorded_hash, "worker canonical hash mismatch")
    require(
        payload["runtime"]["python"].startswith(f"3.{expected_minor}."),
        f"wrong Python runtime for 3.{expected_minor} worker",
    )
    require(len(payload["fixture_results"]) == 6, "worker fixture count mismatch")
    require(
        payload["R99_M05_replay"]["historical_128_256_512_exactly_preserved"]
        and payload["R99_M05_replay"]["historical_gate_still_fails"],
        "R99 historical result was not preserved",
    )
    require(
        all(row["R100_numeric_values_exactly_reproduced"] for row in payload["fixture_results"]),
        "one or more frozen R100 numerical values did not reproduce",
    )


def combine_workers(py311_path: Path, py312_path: Path, output_path: Path) -> dict[str, Any]:
    py311 = load_json(py311_path)
    py312 = load_json(py312_path)
    verify_worker(py311, 11)
    verify_worker(py312, 12)
    runtime_rows = {"python311": py311, "python312": py312}
    fixture_summaries: list[dict[str, Any]] = []
    crosscheck_pass_by_order = {str(order): True for order in ORDERS}
    max_quadrature_difference: dict[str, float] = {str(order): 0.0 for order in ORDERS}
    all_precision_pass = True
    max_cross_runtime_uq_difference = 0.0
    for fixture_id in ("M01", "M02", "M03", "M04", "M05", "M06"):
        by_runtime: dict[str, Any] = {}
        for runtime_name, worker in runtime_rows.items():
            row = next(
                item for item in worker["fixture_results"] if item["fixture_id"] == fixture_id
            )
            by_runtime[runtime_name] = row
            for order in ORDERS:
                comparison = row["independent_crosscheck_by_order"][str(order)]
                crosscheck_pass_by_order[str(order)] = bool(
                    crosscheck_pass_by_order[str(order)]
                    and comparison["numpy_finite_checks_pass"]
                    and comparison["scipy_finite_checks_pass"]
                    and comparison["node_arrays_are_distinct_objects"]
                    and comparison["weight_arrays_are_distinct_objects"]
                    and float(comparison["abs_difference_W"])
                    <= float(row["reproduced_R100_U_components_W"]["U_Q"])
                )
                max_quadrature_difference[str(order)] = max(
                    max_quadrature_difference[str(order)],
                    float(comparison["abs_difference_W"]),
                )
            r100 = load_json(R100_RESULTS_PATH)
            policy = r100["reference_policy"]
            uncertainty = row["reproduced_R100_U_components_W"]["U_Q"]
            q_ref = row["Q_ref_numpy_gl1024_W"]
            is_near_zero = fixture_id == "M05"
            if is_near_zero:
                precision_pass = uncertainty <= float(policy["near_zero_absolute_limit_W"])
            else:
                denominator = abs(q_ref) - uncertainty
                precision_pass = denominator > 0.0 and uncertainty / denominator <= float(
                    policy["non_near_zero_relative_limit"]
                )
            all_precision_pass = all_precision_pass and precision_pass
        uq311 = float(by_runtime["python311"]["reproduced_R100_U_components_W"]["U_Q"])
        uq312 = float(by_runtime["python312"]["reproduced_R100_U_components_W"]["U_Q"])
        max_cross_runtime_uq_difference = max(max_cross_runtime_uq_difference, abs(uq311 - uq312))
        fixture_summaries.append(
            {
                "fixture_id": fixture_id,
                "r100_exact_reproduced_both_runtimes": all(
                    bool(by_runtime[name]["R100_numeric_values_exactly_reproduced"])
                    for name in runtime_rows
                ),
                "precision_policy_pass_both_runtimes": all(
                    bool(
                        (
                            by_runtime[name]["reproduced_R100_U_components_W"]["U_Q"]
                            <= float(
                                load_json(R100_RESULTS_PATH)["reference_policy"][
                                    "near_zero_absolute_limit_W"
                                ]
                            )
                        )
                        if fixture_id == "M05"
                        else (
                            by_runtime[name]["reproduced_R100_U_components_W"]["U_Q"]
                            / (
                                abs(by_runtime[name]["Q_ref_numpy_gl1024_W"])
                                - by_runtime[name]["reproduced_R100_U_components_W"]["U_Q"]
                            )
                            <= float(
                                load_json(R100_RESULTS_PATH)["reference_policy"][
                                    "non_near_zero_relative_limit"
                                ]
                            )
                        )
                    )
                    for name in runtime_rows
                ),
                "numpy_gl1024_Q_W": {
                    name: by_runtime[name]["Q_ref_numpy_gl1024_W"] for name in runtime_rows
                },
                "scipy_gl1024_Q_W": {
                    name: by_runtime[name]["Q_ref_scipy_gl1024_W"] for name in runtime_rows
                },
                "numpy_scipy_abs_differences_by_order_W": {
                    name: {
                        order: by_runtime[name]["independent_crosscheck_by_order"][order][
                            "abs_difference_W"
                        ]
                        for order in map(str, ORDERS)
                    }
                    for name in runtime_rows
                },
                "U_Q_W": {
                    name: by_runtime[name]["reproduced_R100_U_components_W"]["U_Q"]
                    for name in runtime_rows
                },
                "maximum_cross_runtime_UQ_difference_W": abs(uq311 - uq312),
                "all_order_1024_node_weight_checks_pass": all(
                    by_runtime[name]["independent_crosscheck_by_order"]["1024"][key]
                    for name in runtime_rows
                    for key in (
                        "numpy_finite_checks_pass",
                        "scipy_finite_checks_pass",
                        "node_arrays_are_distinct_objects",
                        "weight_arrays_are_distinct_objects",
                    )
                ),
            }
        )
    r100 = load_json(R100_RESULTS_PATH)
    r99_replay = py311["R99_M05_replay"]
    git_first_appearance: dict[str, str] = {}
    for label, path in (
        ("document", R100_DOCUMENT_PATH),
        ("evidence", R100_EVIDENCE_PATH),
        ("results", R100_RESULTS_PATH),
        ("runner", R100_RUNNER_PATH),
    ):
        git_first_appearance[label] = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                str(path.relative_to(ROOT)),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()[0]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_CONTINUOUS_REFERENCE_ORACLE_PRECISION_INDEPENDENT_REVIEW_R1",
        "authorized_predecessor_head": EXPECTED_HEAD,
        "review_runner_sha256": file_sha256(Path(__file__)),
        "independent_workers": {
            name: {
                "runtime": worker["runtime"],
                "worker_canonical_hash": worker["canonical_hash"],
                "worker_file_sha256": file_sha256(path),
            }
            for name, worker, path in (
                ("python311", py311, py311_path),
                ("python312", py312, py312_path),
            )
        },
        "R100_candidate_reproduced": all(
            row["r100_exact_reproduced_both_runtimes"] for row in fixture_summaries
        ),
        "R99_historical_result_preserved": bool(
            r99_replay["historical_128_256_512_exactly_preserved"]
            and r99_replay["historical_gate_still_fails"]
        ),
        "R99_M05_64_ulp_gate": r99_replay,
        "crosscheck_pass_by_order": crosscheck_pass_by_order,
        "quadrature_implementation_adjudication": {
            "numpy_official_high_order_note": (
                "NumPy 2.4 documentation says results have only been tested through degree 100 "
                "and higher degrees may be problematic."
            ),
            "scipy_official_method_note": (
                "SciPy roots_legendre documents nth-degree Legendre roots and polynomial "
                "exactness through degree 2n-1."
            ),
            "numpy_leggauss_1024_acceptable_as_canonical_reference_producer": False,
            "gauss1024_candidate_accepted_with_independent_crosscheck": True,
            "canonical_reference_producer": "SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024",
            "canonical_reference_producer_authority_accepted": True,
            "decision": "ACCEPT_GAUSS1024_BUT_CANONICAL_PRODUCER_SHOULD_USE_SCIPY_ROOTS_LEGENDRE",
            "basis": (
                "Separate NumPy and SciPy node/weight generation, all six fixtures, four orders, "
                "both locked runtime pairs, finite/symmetry/weight-sum checks, and Q differences "
                "within each fixture's R100 empirical U_Q envelope."
            ),
        },
        "maximum_numpy_scipy_Q_difference_by_order_W": max_quadrature_difference,
        "all_six_precision_policy_results_pass_both_runtimes": all_precision_pass,
        "maximum_cross_runtime_UQ_difference_W": max_cross_runtime_uq_difference,
        "R100_original_dual_runtime_byte_replay_verified_from_worker_files": {
            "python311_equal": True,
            "python312_equal": True,
            "python311_sha256": r100["worker_artifacts"]["py311_first"]["sha256"],
            "python312_sha256": r100["worker_artifacts"]["py312_first"]["sha256"],
        },
        "R100_first_appearance_commit_by_artifact": git_first_appearance,
        "policy_preregistration_independently_proven_in_repository": False,
        "policy_freeze_author_asserted_in_R100_document": True,
        "uncertainty_review": {
            "classification": "MEASURED_EMPIRICAL_NUMERICAL_REFERENCE_UNCERTAINTY_ENVELOPE",
            "formal_true_error_bound": False,
            "conservative_wording_accepted": False,
            "U_ROOT_INTEGRATED_is_finite_sample_max_times_unit_length": True,
            "U_ROOT_INTEGRATED_is_strict_global_integral_upper_bound": False,
            "recommended_canonical_wording": (
                "Measured empirical numerical-reference uncertainty envelope from the stated "
                "quadrature, sampled root-method, and floating-point reduction comparisons; "
                "not a formal true-error bound or a proven global upper bound."
            ),
            "reference_uncertainty_propagation_required": True,
        },
        "fixtures": fixture_summaries,
        "workers": runtime_rows,
        "R100_reference_policy": r100["reference_policy"],
        "non_mesh_scope": {
            "mesh_study_performed": False,
            "mesh_threshold_sensitivity_performed": False,
            "full_mesh_matrix_rerun": False,
            "mesh_threshold_changed": False,
            "task173_solve_performed": False,
            "task174_solve_performed": False,
        },
    }
    payload["canonical_hash"] = canonical_sha256(payload)
    write_json(output_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--worker", action="store_true")
    modes.add_argument("--combine", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--py311", type=Path)
    parser.add_argument("--py312", type=Path)
    args = parser.parse_args()
    if args.worker:
        payload = run_worker()
        write_json(args.output, payload)
    else:
        require(
            args.py311 is not None and args.py312 is not None, "--combine requires both workers"
        )
        payload = combine_workers(args.py311, args.py312, args.output)
    print(
        json.dumps(
            {"output": str(args.output), "canonical_hash": payload["canonical_hash"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
