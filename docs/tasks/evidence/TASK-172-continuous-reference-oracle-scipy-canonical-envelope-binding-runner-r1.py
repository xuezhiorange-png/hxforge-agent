"""Rebuild the reviewed continuous-reference envelope on canonical SciPy GL.

Test-only deterministic replay. It consumes frozen R95 local-support fixture
definitions and R101 reference callbacks; it does not run a mesh study, call a
production solver, access the network, or modify production state.
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
from scipy.special import roots_legendre

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import CoolProp  # noqa: E402

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

TASK_ID = "TASK172_CONTINUOUS_REFERENCE_ORACLE_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION_R1"
EXPECTED_HEAD = "566d85d88bdc44c2cc7cb67789690878c669ef0f"
REGISTRY_PATH = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
R100_DOC = (
    ROOT / "docs/tasks/TASK-172-v0.7-continuous-reference-oracle-precision-qualification-r1.md"
)
R100_EVIDENCE = (
    ROOT
    / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-qualification-r1.json"
)
R100_RESULTS = (
    ROOT / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-results-r1.json"
)
R100_RUNNER = (
    ROOT / "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-runner-r1.py"
)
R101_DOC = (
    ROOT / "docs/tasks/TASK-172-v0.7-continuous-reference-oracle-precision-independent-review-r1.md"
)
R101_EVIDENCE = ROOT / (
    "docs/tasks/evidence/TASK-172-continuous-reference-oracle-precision-independent-review-r1.json"
)
R101_RESULTS = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-continuous-reference-oracle-precision-independent-review-results-r1.json"
)
R101_RUNNER = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-continuous-reference-oracle-precision-independent-review-runner-r1.py"
)

EXPECTED_R100 = {
    "document_sha256": "c7a5415006e319a6f999937d883bb0d520eee6f84d4e05ee4ef752df1448d118",
    "evidence_file_sha256": "0d719a48ef4ccee07c5f0b161e844f635e0c97ed101964825880b744e1fdd0c5",
    "evidence_canonical_hash": "d4be20147aa641c189bef443fd497987230fe6bd1d7b4edf4f2171af3ca356bb",
    "results_file_sha256": "b7844e566faab902fef1bc90eda3c991f3e1271da96effe78c693efe4fac6b43",
    "results_canonical_hash": "17799de16c5b4a7362bda4595d4d5af9e46ee1633d89e852e51cc58419caf5d0",
    "runner_sha256": "a6ea1850bca18bed700f8313ffd208d4a27fa8750604a1529fad9a4a4a2084ba",
    "extension_canonical_hash": "9e1210f35c3e52f83cdffde3b23f0fc78f8b8b75e1fbbd2e35c07039095b6701",
}
EXPECTED_R101 = {
    "document_sha256": "2a026ed5f99b3b8efd88dd076ab14df88a28a462fcb7cbe49444a9df304ca192",
    "evidence_file_sha256": "da5165ad2010d073cbda92b57034890b4d299a31933ea3e08bebd3aea162bcff",
    "evidence_canonical_hash": "e7e62f8137ac78bf3b2ddb74fdd13889e3f9040ca58516b2d5403fc3fed4b18a",
    "results_file_sha256": "fa992216fbc15cccc84c93b59a39a5ff70c64543b7828a679d7ca2d231f404b0",
    "results_canonical_hash": "94ff0a74b53e6c57c0f08a16625f59cea5c8246c9825ed734e7be352173dd032",
    "runner_sha256": "2ac6dea8e6fa619d524de7b507b184196e4a29cb82020e65b4678eb978f2648c",
    "extension_canonical_hash": "fc4265c2f2db3bcda49dc032a5d5cd6065a79a1e26f31f2ea40cbaed0fde0b3c",
    "registry_root_canonical_hash": (
        "e3ff00e9aae448bdc4a8b43273aeb62dc8a84633ee997682cad59799a411798f"
    ),
}
ORDERS = (128, 256, 512, 1024)
SIMPSON_INTERVALS = (512, 1024, 2048)
FIXTURE_IDS = ("M01", "M02", "M03", "M04", "M05", "M06")


class ReplayError(RuntimeError):
    """Fail-closed replay or provenance error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReplayError(f"cannot load frozen module {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_historical_bindings() -> dict[str, Any]:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require(head == EXPECTED_HEAD, f"BLOCKED_HEAD_CHANGED: expected {EXPECTED_HEAD}, got {head}")
    registry = read_json(REGISTRY_PATH)
    baseline = json.loads(
        subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{EXPECTED_HEAD}:{REGISTRY_PATH.relative_to(ROOT)}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    require(
        canonical_sha256(baseline) == EXPECTED_R101["registry_root_canonical_hash"],
        "R101 predecessor registry root mismatch",
    )
    for key, value in baseline.items():
        if key.endswith("_extension"):
            require(registry.get(key) == value, f"historical extension changed: {key}")
    require(
        canonical_sha256(registry["r100_extension"]) == EXPECTED_R100["extension_canonical_hash"],
        "R100 extension changed",
    )
    require(
        canonical_sha256(registry["r101_extension"]) == EXPECTED_R101["extension_canonical_hash"],
        "R101 extension changed",
    )
    require(
        registry["r101_extension"]["independent_review"]["canonical_reference_producer"]
        == "SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024",
        "R101 canonical producer finding mismatch",
    )
    for label, paths, expected in (
        ("R100", (R100_DOC, R100_EVIDENCE, R100_RESULTS, R100_RUNNER), EXPECTED_R100),
        ("R101", (R101_DOC, R101_EVIDENCE, R101_RESULTS, R101_RUNNER), EXPECTED_R101),
    ):
        for path, field in zip(
            paths,
            ("document_sha256", "evidence_file_sha256", "results_file_sha256", "runner_sha256"),
            strict=True,
        ):
            require(
                file_sha256(path) == expected[field],
                f"{label} immutable artifact changed: {path.name}",
            )
    r100_evidence = read_json(R100_EVIDENCE)
    r100_results = read_json(R100_RESULTS)
    r101_evidence = read_json(R101_EVIDENCE)
    r101_results = read_json(R101_RESULTS)
    require(
        canonical_sha256(r100_evidence) == EXPECTED_R100["evidence_canonical_hash"],
        "R100 evidence canonical hash mismatch",
    )
    require(
        canonical_sha256(r100_results) == EXPECTED_R100["results_canonical_hash"],
        "R100 results canonical hash mismatch",
    )
    require(
        canonical_sha256(r101_evidence) == EXPECTED_R101["evidence_canonical_hash"],
        "R101 evidence canonical hash mismatch",
    )
    require(
        canonical_sha256(r101_results) == EXPECTED_R101["results_canonical_hash"],
        "R101 results canonical hash mismatch",
    )
    require(
        r101_evidence["result"] == "PASS_CONTINUOUS_REFERENCE_ORACLE_PRECISION_INDEPENDENT_REVIEW",
        "R101 review result mismatch",
    )
    require(
        r101_evidence["lifecycle_and_blockers"]["continuous_reference_oracle_precision_lifecycle"]
        == "REVIEWED_AUTHORITY",
        "R101 lifecycle mismatch",
    )
    return {
        "authorized_head": head,
        "historical_extensions_unchanged": True,
        "R100_artifact_hashes_verified": True,
        "R101_artifact_hashes_verified": True,
        "R100_extension_canonical_hash": EXPECTED_R100["extension_canonical_hash"],
        "R101_extension_canonical_hash": EXPECTED_R101["extension_canonical_hash"],
        "R101_registry_root_canonical_hash": EXPECTED_R101["registry_root_canonical_hash"],
        "R101_reviewed_authority_preserved": True,
    }


def reduction_metrics(contributions: list[float]) -> dict[str, Any]:
    fsum_value = math.fsum(contributions)
    ordinary_value = sum(contributions)
    encoded = canonical_json_bytes({"contributions": contributions})
    decoded = json.loads(encoded)
    roundtrip = [float(value) for value in decoded["contributions"]]
    exactly_roundtrips = all(
        left.hex() == right.hex() for left, right in zip(contributions, roundtrip, strict=True)
    )
    roundtrip_fsum = math.fsum(roundtrip)
    return {
        "contribution_count": len(contributions),
        "contribution_vector_canonical_hash": canonical_sha256({"contributions": contributions}),
        "math_fsum_W": fsum_value,
        "ordinary_sum_W": ordinary_value,
        "ordinary_sum_abs_difference_W": abs(fsum_value - ordinary_value),
        "canonical_roundtrip_fsum_W": roundtrip_fsum,
        "canonical_roundtrip_sum_abs_difference_W": abs(fsum_value - roundtrip_fsum),
        "serialization_roundtrip_exact": exactly_roundtrips,
        "all_contributions_finite": all(math.isfinite(value) for value in contributions),
    }


def scipy_gauss_row(
    r101: Any, r95: Any, r94: Any, fixture_id: str, order: int, cache: dict[Any, Any]
) -> dict[str, Any]:
    nodes, weights = roots_legendre(order)
    contributions = [
        0.5
        * float(weight)
        * float(
            r101.support_state(r95, r94, fixture_id, 0.5 * (float(node) + 1.0), cache)["q_hc_W"]
        )
        for node, weight in zip(nodes, weights, strict=True)
    ]
    reduction = reduction_metrics(contributions)
    return {
        "producer": "SCIPY_SPECIAL_ROOTS_LEGENDRE",
        "order": order,
        "Q_W": reduction["math_fsum_W"],
        "reduction": reduction,
        "weight_sum": math.fsum(float(value) for value in weights),
        "weight_sum_deviation_from_2": abs(math.fsum(float(value) for value in weights) - 2.0),
        "finite_nodes_weights_contributions": all(
            math.isfinite(float(value)) for value in list(nodes) + list(weights) + contributions
        ),
    }


def simpson_row(
    r101: Any, r95: Any, r94: Any, fixture_id: str, intervals: int, cache: dict[Any, Any]
) -> dict[str, Any]:
    step = 1.0 / intervals
    contributions: list[float] = []
    for index in range(intervals + 1):
        coefficient = 1 if index in (0, intervals) else (4 if index % 2 else 2)
        q_hc = float(r101.support_state(r95, r94, fixture_id, index / intervals, cache)["q_hc_W"])
        contributions.append((step / 3.0) * coefficient * q_hc)
    return {
        "producer": "FROZEN_COMPOSITE_SIMPSON",
        "subintervals": intervals,
        "Q_W": math.fsum(contributions),
        "reduction": reduction_metrics(contributions),
    }


def expected_r101_fixture(
    results: dict[str, Any], runtime_key: str, fixture_id: str
) -> dict[str, Any]:
    return next(
        row
        for row in results["workers"][runtime_key]["fixture_results"]
        if row["fixture_id"] == fixture_id
    )


def worker_replay() -> dict[str, Any]:
    historical = validate_historical_bindings()
    r101 = load_module(R101_RUNNER, "task172_r101_runner_r102")
    r99 = load_module(r101.R99_RUNNER_PATH, "task172_r99_runner_r102")
    r95, _, r94 = r99.load_frozen_modules()
    r101_results = read_json(R101_RESULTS)
    r100_results = read_json(R100_RESULTS)
    original_water = r94.water
    fixtures: list[dict[str, Any]] = []
    r99_m05_values: dict[str, float] = {}

    for fixture_id in FIXTURE_IDS:
        cache: dict[Any, Any] = {}
        property_cache: dict[Any, Any] = {}

        def cached_water(
            temperature_K: float,
            pressure_Pa: float,
            selected_cache: dict[Any, Any] = property_cache,
            selected_original: Any = original_water,
        ) -> dict[str, float]:
            key = (float(temperature_K).hex(), float(pressure_Pa).hex())
            if key not in selected_cache:
                selected_cache[key] = selected_original(float(temperature_K), float(pressure_Pa))
            return dict(selected_cache[key])

        r94.water = cached_water
        try:
            scipy_rows = {
                str(order): scipy_gauss_row(r101, r95, r94, fixture_id, order, cache)
                for order in ORDERS
            }
            simpson_rows = {
                str(count): simpson_row(r101, r95, r94, fixture_id, count, cache)
                for count in (512, 1024, 2048)
            }
            root_row = r101.root_method_replay(r95, r94, fixture_id, cache)

            # Recreate R99's historic M05 NumPy values solely as a preserved
            # historical check; they never enter the effective SciPy envelope.
            if fixture_id == "M05":
                for order in (128, 256, 512, 1024):
                    nodes, weights = np.polynomial.legendre.leggauss(order)
                    terms = [
                        0.5
                        * float(weight)
                        * float(
                            r101.support_state(
                                r95, r94, fixture_id, 0.5 * (float(node) + 1.0), cache
                            )["q_hc_W"]
                        )
                        for node, weight in zip(nodes, weights, strict=True)
                    ]
                    r99_m05_values[str(order)] = math.fsum(terms)
        finally:
            r94.water = original_water

        q_scipy = {order: float(scipy_rows[order]["Q_W"]) for order in map(str, ORDERS)}
        q_simpson = {count: float(simpson_rows[count]["Q_W"]) for count in ("512", "1024", "2048")}
        u_gl = max(abs(q_scipy["256"] - q_scipy["512"]), abs(q_scipy["512"] - q_scipy["1024"]))
        u_simpson = max(
            abs(q_simpson["512"] - q_simpson["1024"]),
            abs(q_simpson["1024"] - q_simpson["2048"]),
        )
        u_cross = abs(q_scipy["1024"] - q_simpson["2048"])
        reduction_rows = [row["reduction"] for row in scipy_rows.values()] + [
            row["reduction"] for row in simpson_rows.values()
        ]
        reduction_discrepancies = [
            float(row["ordinary_sum_abs_difference_W"]) for row in reduction_rows
        ] + [float(row["canonical_roundtrip_sum_abs_difference_W"]) for row in reduction_rows]
        u_reduction = max(reduction_discrepancies, default=0.0)
        u_root = float(root_row["U_ROOT_INTEGRATED_OBSERVED_W"])
        u_q = u_gl + u_simpson + u_cross + u_root + u_reduction
        q_ref = q_scipy["1024"]
        denominator_lower = abs(q_ref) - u_q
        if fixture_id == "M05":
            canonical_metric = u_q
            precision_pass = u_q <= 1e-8
            metric_type = "ABSOLUTE_W"
        else:
            canonical_metric = u_q / denominator_lower if denominator_lower > 0.0 else None
            precision_pass = (
                denominator_lower > 0.0
                and canonical_metric is not None
                and canonical_metric <= 1e-8
            )
            metric_type = "RELATIVE"

        previous_row = expected_r101_fixture(
            r101_results, "python311" if sys.version_info.minor == 11 else "python312", fixture_id
        )
        previous_components = previous_row["root_crosscheck"]
        root_match = (
            u_root == float(previous_components["U_ROOT_INTEGRATED_OBSERVED_W"])
            and root_row["maximum_absolute_differences"]
            == previous_components["maximum_absolute_differences"]
            and root_row["maximum_difference_locations_xi"]
            == previous_components["maximum_difference_locations_xi"]
        )
        require(root_match, f"root comparison differs from R101 frozen replay: {fixture_id}")

        r100_fixture = next(
            row
            for row in r100_results[
                "fixture_results_python311"
                if sys.version_info.minor == 11
                else "fixture_results_python312"
            ]
            if row["fixture_id"] == fixture_id
        )
        simpson_match = all(
            float(simpson_rows[count]["Q_W"])
            == float(r100_fixture["composite_simpson"][count]["Q_W"])
            for count in simpson_rows
        )
        scipy_reference_match = all(
            float(scipy_rows[order]["Q_W"])
            == float(previous_row["scipy_roots_legendre"][order]["Q_W"])
            for order in scipy_rows
        )
        require(simpson_match, f"frozen Simpson replay differs from R100: {fixture_id}")
        require(scipy_reference_match, f"SciPy sequence differs from R101 replay: {fixture_id}")
        require(
            all(row["reduction"]["serialization_roundtrip_exact"] for row in scipy_rows.values()),
            "SciPy contribution serialization roundtrip changed a term",
        )
        require(
            all(row["reduction"]["serialization_roundtrip_exact"] for row in simpson_rows.values()),
            "Simpson contribution serialization roundtrip changed a term",
        )
        require(
            all(row["finite_nodes_weights_contributions"] for row in scipy_rows.values()),
            "non-finite SciPy quadrature contribution",
        )

        fixtures.append(
            {
                "fixture_id": fixture_id,
                "canonical_reference_producer": "SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024",
                "scipy_gauss_legendre": scipy_rows,
                "frozen_composite_simpson": simpson_rows,
                "root_comparison": root_row,
                "canonical_uncertainty_components_W": {
                    "U_GL_CANONICAL": u_gl,
                    "U_SIMPSON": u_simpson,
                    "U_CROSS_CANONICAL": u_cross,
                    "U_ROOT_INTEGRATED_EMPIRICAL": u_root,
                    "U_REDUCTION_CANONICAL": u_reduction,
                    "U_Q_CANONICAL": u_q,
                },
                "Q_REF_CANONICAL_W": q_ref,
                "denominator_lower_W": denominator_lower,
                "canonical_precision_metric": canonical_metric,
                "canonical_precision_metric_type": metric_type,
                "precision_pass": bool(precision_pass),
                "frozen_Simpson_replay_exact": simpson_match,
                "R101_SciPy_sequence_replay_exact": scipy_reference_match,
                "root_empirical_discrepancy_matches_R101": root_match,
                "contribution_reduction_inputs": {
                    "series": [
                        {"family": "SCIPY_GAUSS_LEGENDRE", "order": int(key), **row["reduction"]}
                        for key, row in scipy_rows.items()
                    ]
                    + [
                        {
                            "family": "FROZEN_COMPOSITE_SIMPSON",
                            "subintervals": int(key),
                            **row["reduction"],
                        }
                        for key, row in simpson_rows.items()
                    ]
                },
            }
        )
        print(f"replayed canonical SciPy envelope {fixture_id}", flush=True)

    expected_r99 = {
        "128": 0.2222234220550436,
        "256": 0.22222342205515927,
        "512": 0.22222342205526033,
    }
    r99_values_exact = all(r99_m05_values[key] == value for key, value in expected_r99.items())
    r99_criterion = 64.0 * math.ulp(r99_m05_values["512"])
    r99_difference = abs(r99_m05_values["256"] - r99_m05_values["512"])
    r99_still_fails = r99_difference > r99_criterion
    require(r99_values_exact and r99_still_fails, "R99 historical M05 values/gate changed")
    runtime_name = (
        "python311"
        if sys.version_info.minor == 11
        else "python312"
        if sys.version_info.minor == 12
        else "unsupported"
    )
    require(runtime_name != "unsupported", "only Python 3.11 and 3.12 are authorized runtimes")
    return {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "authorized_predecessor_head": EXPECTED_HEAD,
        "runtime_name": runtime_name,
        "runtime": {
            "python": sys.version.split()[0],
            "numpy": str(np.__version__),
            "scipy": str(scipy.__version__),
            "coolprop": str(CoolProp.__version__),
            "platform": platform.platform(),
        },
        "historical_binding_audit": historical,
        "canonical_producer": "SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024",
        "numpy_role": "HISTORICAL_AND_INDEPENDENT_CROSSCHECK_ONLY",
        "precision_policy": {
            "oracle_to_mesh_threshold_separation_factor": 1e-3,
            "non_near_zero_reference_relative_limit": 1e-8,
            "M05_reference_absolute_limit_W": 1e-8,
            "wall_reference_stability_criterion_K": 1e-8,
            "retuned": False,
            "pre_run_policy_freeze_author_asserted": True,
            "pre_run_policy_freeze_independently_proven": False,
        },
        "R99_historical_replay": {
            "result": "BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2",
            "M05_numpy_values_historical_only_W": r99_m05_values,
            "expected_GL128_GL256_GL512_W": expected_r99,
            "historical_values_exactly_reproduced": r99_values_exact,
            "64_ulp_criterion_W": r99_criterion,
            "GL256_GL512_difference_W": r99_difference,
            "64_ulp_gate_still_fails": r99_still_fails,
        },
        "fixtures": fixtures,
        "all_six_fixtures_pass": all(row["precision_pass"] for row in fixtures),
        "mesh_study_performed": False,
        "mesh_threshold_sensitivity_performed": False,
        "full_mesh_matrix_rerun": False,
        "mesh_threshold_changed": False,
        "mesh_convergence_adjudicated": False,
        "production_code_changed": False,
        "task172_implementation_started": False,
    }


def verify_worker(payload: dict[str, Any], expected_minor: int) -> None:
    recorded = str(payload.get("canonical_hash", ""))
    candidate = dict(payload)
    candidate.pop("canonical_hash", None)
    require(
        bool(recorded) and canonical_sha256(candidate) == recorded, "worker canonical hash mismatch"
    )
    require(
        payload["runtime"]["python"].startswith(f"3.{expected_minor}."), "worker runtime mismatch"
    )
    require(
        payload["all_six_fixtures_pass"], f"precision profile failed for Python 3.{expected_minor}"
    )
    require(
        payload["R99_historical_replay"]["64_ulp_gate_still_fails"],
        "R99 historical gate was altered",
    )


def combine_workers(py311_path: Path, py312_path: Path, output_path: Path) -> dict[str, Any]:
    workers = {"python311": read_json(py311_path), "python312": read_json(py312_path)}
    verify_worker(workers["python311"], 11)
    verify_worker(workers["python312"], 12)
    fixture_matrix: list[dict[str, Any]] = []
    for fixture_id in FIXTURE_IDS:
        rows = {
            name: next(item for item in worker["fixtures"] if item["fixture_id"] == fixture_id)
            for name, worker in workers.items()
        }
        fixture_matrix.append(
            {
                "fixture_id": fixture_id,
                "python311_pass": rows["python311"]["precision_pass"],
                "python312_pass": rows["python312"]["precision_pass"],
                "pass_both_runtimes": rows["python311"]["precision_pass"]
                and rows["python312"]["precision_pass"],
                "Q_REF_CANONICAL_W": {name: row["Q_REF_CANONICAL_W"] for name, row in rows.items()},
                "U_Q_CANONICAL_W": {
                    name: row["canonical_uncertainty_components_W"]["U_Q_CANONICAL"]
                    for name, row in rows.items()
                },
                "canonical_metric": {
                    name: row["canonical_precision_metric"] for name, row in rows.items()
                },
                "canonical_metric_type": {
                    name: row["canonical_precision_metric_type"] for name, row in rows.items()
                },
            }
        )
    all_pass = all(row["pass_both_runtimes"] for row in fixture_matrix)
    r99_replays_identical = (
        workers["python311"]["R99_historical_replay"]
        == workers["python312"]["R99_historical_replay"]
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "authorized_predecessor_head": EXPECTED_HEAD,
        "canonical_reference_producer": "SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024",
        "numpy_leggauss_role": "HISTORICAL_AND_INDEPENDENT_CROSSCHECK_ONLY",
        "scipy_roots_legendre_role": "CANONICAL_REFERENCE_PRODUCER",
        "uncertainty_classification": "MEASURED_EMPIRICAL_NUMERICAL_REFERENCE_UNCERTAINTY_ENVELOPE",
        "formal_true_error_bound": False,
        "conservative_wording_accepted": False,
        "reference_uncertainty_propagation_required": True,
        "uncertainty_wording": (
            "Measured empirical numerical-reference uncertainty envelope from the stated "
            "quadrature, sampled root-method, and floating-point reduction comparisons; not "
            "a formal true-error bound or a proven global upper bound."
        ),
        "precision_policy_retuned": False,
        "pre_run_policy_freeze_author_asserted": True,
        "pre_run_policy_freeze_independently_proven": False,
        "workers": {
            name: {
                "runtime": worker["runtime"],
                "file_sha256": file_sha256(path),
                "canonical_hash": worker["canonical_hash"],
                "worker_result": worker,
            }
            for name, worker, path in (
                ("python311", workers["python311"], py311_path),
                ("python312", workers["python312"], py312_path),
            )
        },
        "fixtures": fixture_matrix,
        "all_six_fixtures_pass_both_runtimes": all_pass,
        "R99_historical_result_preserved": r99_replays_identical,
        "R99_M05_64_ulp_gate_reproduced": all(
            worker["R99_historical_replay"]["64_ulp_gate_still_fails"]
            for worker in workers.values()
        ),
        "mesh_study_performed": False,
        "mesh_threshold_sensitivity_performed": False,
        "full_mesh_matrix_rerun": False,
        "mesh_threshold_changed": False,
        "mesh_convergence_adjudicated": False,
        "production_code_changed": False,
        "task172_implementation_started": False,
        "decision": "PASS_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION"
        if all_pass and r99_replays_identical
        else "BLOCKED_SCIPY_CANONICAL_ENVELOPE_BINDING_CORRECTION",
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
        payload = worker_replay()
        payload["canonical_hash"] = canonical_sha256(payload)
        write_json(args.output, payload)
    else:
        require(
            args.py311 is not None and args.py312 is not None,
            "--combine requires both runtime workers",
        )
        payload = combine_workers(args.py311, args.py312, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "canonical_hash": payload["canonical_hash"],
                "decision": payload.get("decision", "WORKER_COMPLETE"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
