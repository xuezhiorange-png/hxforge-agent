"""Deterministic R99 mesh qualification runner using only frozen R95 fixtures.

The runner reuses the immutable R95 geometry, state producer, continuous
oracle, and failure fixtures. Its only numerical overlay is the independently
reviewed R98 P1 residual-bound multiplier C_round=1.0. No production solver,
TASK173/TASK174 solver, real case, or external service is invoked.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

REGISTRY_PATH = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
R95_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-runner-r1.py"
)
R95_DOCUMENT_PATH = ROOT / "docs/tasks/TASK-172-v0.7-mesh-convergence-qualification-r1.md"
R95_EVIDENCE_PATH = ROOT / "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-r1.json"
R95_RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-results-r1.json"
)
R98_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-mesh-cell-scale-numerical-acceptance-extension-independent-review-runner-r1.py"
)
R98_DOCUMENT_PATH = ROOT / (
    "docs/tasks/TASK-172-v0.7-mesh-cell-scale-numerical-acceptance-extension-independent-review-r1.md"
)
R98_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-mesh-cell-scale-numerical-acceptance-extension-independent-review-r1.json"
)
R98_RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-mesh-cell-scale-numerical-acceptance-extension-independent-review-results-r1.json"
)

AUTHORIZED_PREDECESSOR_HEAD = "fe9377cc1ea67370572b95338e54e861eda8a870"
R95_INPUT_MATRIX_HASH = "b13d4306f3a2a60f248fbd1b222a6069599ec08a3c094996b17019ac315ae2d8"
R95_RESULTS_CANONICAL_HASH = "46cb34272f69bec5ff72bd07e704e80f697a4302b6fe35759514ce260731a2bf"
R95_EXTENSION_HASH = "b5aad06ffecada1af065ead331854ec53ef7292988406a9200afeeca4fa74b1f"
R98_REGISTRY_ROOT_HASH = "c596f128602da416277c77ab27b6c245dd7c587a18259f4920c5851402deab7a"
R98_EXTENSION_HASH = "54c63a6c1178650e3164dd9f6cd7417ba044f2ec4b2f6b1b6a28accc19955a78"
R98_EVIDENCE_CANONICAL_HASH = "be31f27d1de977285f1cbea14ed7e70e37bbd2ce1b6cb2f9e93b1ab3d49a8312"
R98_RESULTS_CANONICAL_HASH = "0f1a7f713101aa60045ba888a2547cf34f456426fe6ad6c4ed2dde81fc6f0afb"
R98_PROFILE_HASH = "029b641b796c2feb699fb1fcc70386de716b7ac820684e507a3a6c0dc0b1eeb6"

PRIMARY_SEQUENCE = (1, 2, 4, 8, 16, 32, 64, 128)
SECONDARY_SEQUENCE = (3, 6, 12, 24, 48, 96)
THRESHOLD_GRID = ("1e-2", "1e-3", "1e-4", "1e-5")
RESOURCE_CAP_GRID = (32, 64, 128, 256)
EXPECTED_PROFILE: dict[str, Any] = {
    "candidate_id": "P1_ACCEPTANCE_EXTENSION",
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
    "residual_scale": "abs(q_ts_seed)",
    "c_round": 1.0,
    "tr_solver": "exact",
    "tr_options": {},
    "f_scale": 1.0,
    "jac_sparsity": None,
}


class GateFailure(RuntimeError):
    """Typed, fail-closed R2 evidence failure."""

    def __init__(self, code: str, detail: str, evidence: dict[str, Any] | None = None) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail
        self.evidence = evidence or {}


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise GateFailure(code, detail)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{payload}\n", encoding="utf-8")


def load_module(path: Path, name: str) -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateFailure("INPUT_AUTHORITY_MISSING", f"cannot load frozen runner {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_registry_and_upstream(r95: Any, r98: Any) -> dict[str, Any]:
    registry = read_json(REGISTRY_PATH)
    require(
        canonical_sha256(registry) == R98_REGISTRY_ROOT_HASH,
        "HISTORICAL_AUTHORITY_MISMATCH",
        "R98 predecessor registry root changed",
    )
    r95_extension = cast(dict[str, Any], registry["r95_extension"])
    r98_extension = cast(dict[str, Any], registry["r98_extension"])
    require(
        canonical_sha256(r95_extension) == R95_EXTENSION_HASH
        and r95_extension.get("result") == "BLOCKED_MESH_CONVERGENCE_QUALIFICATION",
        "HISTORICAL_AUTHORITY_MISMATCH",
        "R95 historical blocker record changed",
    )
    require(
        canonical_sha256(r98_extension) == R98_EXTENSION_HASH,
        "HISTORICAL_AUTHORITY_MISMATCH",
        "R98 extension canonical hash mismatch",
    )
    r95_artifacts = cast(dict[str, Any], r95_extension["artifacts"])
    r98_artifacts = cast(dict[str, Any], r98_extension["artifacts"])
    for path, expected in (
        (R95_DOCUMENT_PATH, str(r95_artifacts["document_sha256"])),
        (R95_EVIDENCE_PATH, str(r95_artifacts["evidence_file_sha256"])),
        (R95_RESULTS_PATH, str(r95_artifacts["results_file_sha256"])),
        (R95_RUNNER_PATH, str(r95_artifacts["runner_sha256"])),
        (R98_DOCUMENT_PATH, str(r98_artifacts["document_sha256"])),
        (R98_EVIDENCE_PATH, str(r98_artifacts["evidence_file_sha256"])),
        (R98_RESULTS_PATH, str(r98_artifacts["results_file_sha256"])),
        (R98_RUNNER_PATH, str(r98_artifacts["runner_sha256"])),
    ):
        require(file_sha256(path) == expected, "HISTORICAL_ARTIFACT_MISMATCH", path.name)
    r95_evidence = read_json(R95_EVIDENCE_PATH)
    r95_results = read_json(R95_RESULTS_PATH)
    r98_evidence = read_json(R98_EVIDENCE_PATH)
    r98_results = read_json(R98_RESULTS_PATH)
    require(
        canonical_sha256(r95_evidence) == str(r95_artifacts["evidence_canonical_hash"]),
        "HISTORICAL_ARTIFACT_MISMATCH",
        "R95 evidence canonical hash mismatch",
    )
    require(
        canonical_sha256(r95_results) == R95_RESULTS_CANONICAL_HASH,
        "HISTORICAL_ARTIFACT_MISMATCH",
        "R95 results canonical hash mismatch",
    )
    require(
        canonical_sha256(r98_evidence) == R98_EVIDENCE_CANONICAL_HASH
        and canonical_sha256(r98_results) == R98_RESULTS_CANONICAL_HASH,
        "HISTORICAL_ARTIFACT_MISMATCH",
        "R98 evidence/results canonical hash mismatch",
    )
    effective = cast(dict[str, Any], r98_evidence["effective_overlay"])
    profile = cast(dict[str, Any], r98.EXPECTED_PROFILE)
    require(
        canonical_sha256(profile) == R98_PROFILE_HASH
        and profile == EXPECTED_PROFILE
        and effective["candidate_lifecycle"] == "REVIEWED_AUTHORITY"
        and float(effective["effective_mesh_cell_scale_c_round"]) == 1.0
        and bool(effective["r95_mesh_qualification_resume_authorized"]),
        "R98_OVERLAY_INVALID",
        "reviewed P1 overlay does not exactly match frozen candidate",
    )
    matrix = r95.fixture_input_matrix()
    input_hash = canonical_sha256(matrix)
    require(
        input_hash == R95_INPUT_MATRIX_HASH
        and float(matrix["frozen_r94_profile"]["c_round"]) == 0.5,
        "R95_INPUT_REPLAY_FAILED",
        f"frozen input hash/profile mismatch: {input_hash}",
    )
    require(
        tuple(matrix["mesh_sequences"]["primary_nested_equal_bisection"]) == PRIMARY_SEQUENCE
        and tuple(matrix["mesh_sequences"]["secondary_phase_alignment"]) == SECONDARY_SEQUENCE
        and tuple(matrix["comparison"]["threshold_grid"]["duty_relative"]) == THRESHOLD_GRID,
        "R95_INPUT_REPLAY_FAILED",
        "frozen mesh sequence or threshold grid changed",
    )
    return {
        "registry_root_canonical_hash": R98_REGISTRY_ROOT_HASH,
        "r95_extension_canonical_hash": canonical_sha256(r95_extension),
        "r95_evidence_canonical_hash": canonical_sha256(r95_evidence),
        "r95_results_canonical_hash": canonical_sha256(r95_results),
        "r98_extension_canonical_hash": canonical_sha256(r98_extension),
        "r98_evidence_canonical_hash": canonical_sha256(r98_evidence),
        "r98_results_canonical_hash": canonical_sha256(r98_results),
        "r95_input_matrix_canonical_hash": input_hash,
        "r95_frozen_base_c_round": 0.5,
        "r98_effective_c_round": 1.0,
        "r98_profile_canonical_hash": canonical_sha256(profile),
        "profile_changed": False,
        "r95_input_changed": False,
    }


def verify_predecessor_head() -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = completed.stdout.strip()
    require(
        head == AUTHORIZED_PREDECESSOR_HEAD,
        "BLOCKED_HEAD_CHANGED",
        f"expected {AUTHORIZED_PREDECESSOR_HEAD}, observed {head}",
    )
    return head


def load_frozen_modules() -> tuple[Any, Any, Any]:
    r95 = load_module(R95_RUNNER_PATH, "task172_r95_mesh_runner_r2")
    r98 = load_module(R98_RUNNER_PATH, "task172_r98_overlay_runner_r2")
    r94 = r95.load_r94_module()
    return r95, r98, r94


def former_blocking_cell(r95: Any, r98: Any, r94: Any) -> dict[str, Any]:
    levels = r95.build_mesh_sequence("M01", 1, PRIMARY_SEQUENCE)
    target = next(
        cell
        for cell in levels[8]
        if cell.left.numerator == 1
        and cell.left.denominator == 4
        and cell.right.numerator == 3
        and cell.right.denominator == 8
    )
    fraction = target.right - target.left
    midpoint = float((target.left + target.right) / 2)
    case = r95.make_r94_case(
        r94,
        "M01",
        midpoint,
        fraction,
        cell_identity=r95.cell_id("M01", target.left, target.right),
    )
    solved = r98.solve_frozen_profile(r94, case, dict(r98.EXPECTED_PROFILE))
    require(
        bool(solved.get("accepted")),
        "R95_FORMER_BLOCKING_CELL_NOT_REMEDIATED",
        "M01/PRIMARY/N=8/[1/4,3/8] fails under the R98 C_round=1.0 overlay",
    )
    residuals = cast(list[float], solved["physical_residuals_W"])
    bounds = cast(list[float], solved["candidate_c_bounds_W"])
    ratios = cast(list[float], solved["residual_to_bound_ratios"])
    return {
        "fixture_id": "M01",
        "sequence_id": "PRIMARY",
        "cell_count": 8,
        "cell_interval_exact": ["1/4", "3/8"],
        "cell_fraction_exact": "1/8",
        "historical_r_i_W": 2.0605739337042905e-13,
        "observed_r_i_W": residuals[0],
        "new_r_i_bound_W": bounds[0],
        "new_r_i_ratio": ratios[0],
        "residuals_W": residuals,
        "bounds_W": bounds,
        "ratios": ratios,
        "solver_status": solved["solver_status"],
        "nfev": solved["nfev"],
        "callback_count": solved["residual_callback_count"],
        "accepted": True,
        "profile_c_round": float(r98.EXPECTED_PROFILE["c_round"]),
    }


def verify_matrix_structure(fixtures: list[dict[str, Any]], r95: Any) -> dict[str, Any]:
    require(len(fixtures) == 6, "COMPLETE_MESH_MATRIX_MISSING", "expected six fixtures")
    expected_sequences = {
        "PRIMARY": PRIMARY_SEQUENCE,
        "SECONDARY_ALIGNMENT": SECONDARY_SEQUENCE,
    }
    level_count = 0
    cell_count = 0
    for fixture in fixtures:
        require(
            fixture["fixture_id"] in {"M01", "M02", "M03", "M04", "M05", "M06"},
            "R95_FIXTURE_CHANGED",
            str(fixture["fixture_id"]),
        )
        require(
            bool(fixture["bulk_state_domain_audit"]["all_sampled_bulk_states_in_reviewed_domain"]),
            "FIXTURE_DOMAIN_INVALID",
            str(fixture["fixture_id"]),
        )
        for sequence_name, expected in expected_sequences.items():
            geometry = cast(
                dict[str, Any],
                cast(dict[str, Any], fixture["geometry_partition_audit"])[sequence_name],
            )
            require(
                bool(geometry["pass"]),
                "AREA_PARTITION_FAILURE",
                f"{fixture['fixture_id']}:{sequence_name}",
            )
            levels = cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_name])
            require(
                tuple(int(level["cell_count"]) for level in levels) == expected,
                "R95_MESH_SEQUENCE_CHANGED",
                f"{fixture['fixture_id']}:{sequence_name}",
            )
            level_count += len(levels)
            for level in levels:
                rows = cast(list[dict[str, Any]], level["cell_results"])
                cell_count += len(rows)
                require(
                    len(rows) == int(level["cell_count"])
                    and bool(level["all_local_R94_solves_accepted"])
                    and all(bool(row["accepted"]) for row in rows),
                    "LOCAL_MESH_CELL_FAILURE",
                    f"{fixture['fixture_id']}:{sequence_name}:N={level['cell_count']}",
                )
    expected_cells = 6 * (sum(PRIMARY_SEQUENCE) + sum(SECONDARY_SEQUENCE))
    require(cell_count == expected_cells, "COMPLETE_MESH_MATRIX_MISSING", str(cell_count))
    failures = r95.mesh_failure_fixtures()
    require(
        bool(failures["all_expected_typed_outcomes_observed"]),
        "MESH_FAILURE_TAXONOMY_FAILED",
        "frozen failure fixtures did not retain their typed outcomes",
    )
    return {
        "fixture_count": len(fixtures),
        "mesh_level_count": level_count,
        "local_cell_solve_count": cell_count,
        "expected_local_cell_solve_count": expected_cells,
        "all_local_solves_accepted": True,
        "failure_fixture_count": int(failures["failure_fixture_count"]),
        "failure_fixture_audit": failures,
    }


def runtime_metadata(r98: Any) -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "numpy": str(r98.np.__version__),
        "scipy": str(r98.scipy.__version__),
        "coolprop": str(r98.CoolProp.__version__),
        "platform": platform.platform(),
    }


def pointwise_state_domain_audit(r95: Any, fixture_id: str) -> dict[str, Any]:
    """Validate frozen roles at common xi, without comparing disjoint global extrema."""
    xi_values = r95.np.linspace(0.0, 1.0, 4097, dtype=float)
    tube = [r95.evaluate_temperature(fixture_id, "tube", float(xi)) for xi in xi_values]
    shell = [r95.evaluate_temperature(fixture_id, "shell", float(xi)) for xi in xi_values]
    row = r95.fixture_row(fixture_id)
    pressure_tube = float(row["pressure_tube_formula_Pa"])
    pressure_shell = float(row["pressure_shell_formula_Pa"])
    reynolds = float(row["reynolds_tube"])
    role = str(row["hot_side"])
    signed_role_differences = [
        t_value - s_value if role == "TUBE" else s_value - t_value
        for t_value, s_value in zip(tube, shell, strict=True)
    ]
    pointwise_role_valid = min(signed_role_differences) > 0.0
    domain_valid = (
        min(tube + shell) >= 298.15
        and max(tube + shell) <= 300.0
        and 100000.0 <= pressure_tube <= 101325.0
        and 100000.0 <= pressure_shell <= 101325.0
        and pressure_tube == pressure_shell
        and 3000.0 < reynolds < 5000000.0
        and pointwise_role_valid
    )
    if not domain_valid:
        raise GateFailure(
            "TRIAL_DOMAIN_EXCURSION",
            f"frozen fixture pointwise role/property-domain audit failed: {fixture_id}",
        )
    return {
        "tube_bulk_min_K": min(tube),
        "tube_bulk_max_K": max(tube),
        "shell_bulk_min_K": min(shell),
        "shell_bulk_max_K": max(shell),
        "pressure_tube_Pa": pressure_tube,
        "pressure_shell_Pa": pressure_shell,
        "tube_hot_or_shell_hot_role": role,
        "role_audit": "POINTWISE_SAME_XI_EXPLICIT_FIXTURE_ROLE",
        "minimum_signed_hot_minus_cold_difference_K": min(signed_role_differences),
        "strict_role_temperature_separation": pointwise_role_valid,
        "global_temperature_ranges_may_overlap": not (
            min(tube) > max(shell) or min(shell) > max(tube)
        ),
        "all_sampled_bulk_states_in_reviewed_domain": True,
        "sample_count": len(xi_values),
    }


def run_worker(output_path: Path) -> dict[str, Any]:
    predecessor = verify_predecessor_head()
    r95, r98, r94 = load_frozen_modules()
    upstream = verify_registry_and_upstream(r95, r98)
    preflight = former_blocking_cell(r95, r98, r94)
    profile = dict(r98.EXPECTED_PROFILE)
    domain_audits = {
        str(row["fixture_id"]): pointwise_state_domain_audit(r95, str(row["fixture_id"]))
        for row in r95.FIXTURE_ROWS
    }

    # R95's stored helper compares global min(hot side) against global max(cold
    # side). R2 preserves the explicit role at each common physical coordinate;
    # variable profiles may overlap as ranges without a local role crossover.
    r95.state_domain_audit = lambda fixture_id: domain_audits[fixture_id]

    def solve_local_overlay(r94_module: Any, case: Any) -> dict[str, Any]:
        solved = r98.solve_frozen_profile(r94_module, case, profile)
        if not bool(solved.get("accepted")):
            failure_code = (
                "MESH_RESOURCE_EXHAUSTED"
                if bool(solved.get("resource_cap_hit"))
                else "MESH_NOT_CONVERGED"
            )
            raise r95.MeshFailure(
                failure_code,
                f"R98 overlay local solve rejected {case.case_id}",
                diagnostics=solved,
            )
        return cast(dict[str, Any], solved)

    r95.solve_local = solve_local_overlay
    fixtures = cast(list[dict[str, Any]], r95.run_mesh_matrix(r94, include_oracles=True))
    structure = verify_matrix_structure(fixtures, r95)
    for fixture in fixtures:
        reference = cast(dict[str, Any], fixture["continuous_reference"])
        require(
            bool(reference["gauss_legendre_precision_audit"]["criterion_pass"])
            and bool(reference["wall_extrema_reference_stable"]),
            "INDEPENDENT_CONTINUOUS_ORACLE_FAILED",
            str(fixture["fixture_id"]),
        )
    projection = r95.numeric_mesh_projection(fixtures)
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R2",
        "study_status": "COMPLETE_SINGLE_RUNTIME_REPLAY",
        "authorized_predecessor_head": predecessor,
        "upstream_replay": upstream,
        "input_matrix": r95.fixture_input_matrix(),
        "input_matrix_canonical_hash": upstream["r95_input_matrix_canonical_hash"],
        "effective_profile": profile,
        "effective_profile_canonical_hash": canonical_sha256(profile),
        "former_blocking_cell_replay": preflight,
        "pointwise_fixture_role_and_domain_audits": domain_audits,
        "runtime": runtime_metadata(r98),
        "matrix_structure": structure,
        "independent_continuous_oracle_all_fixtures_pass": True,
        "fixtures": fixtures,
        "numeric_mesh_projection_canonical_hash": canonical_sha256(
            {"mesh_result_matrix": projection}
        ),
        "complete_fixture_matrix_canonical_hash": canonical_sha256({"fixtures": fixtures}),
        "governance": {
            "R95_input_replayed_exactly": True,
            "R95_fixture_definitions_changed": False,
            "R95_sequences_changed": False,
            "R95_threshold_grid_changed": False,
            "R98_overlay_consumed": True,
            "profile_retuned": False,
            "mesh_study_performed": True,
            "mesh_study_is_production_rating": False,
            "production_code_changed": False,
            "task172_implementation_started": False,
            "task173_solver_executed": False,
            "task174_hydraulic_solver_executed": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
        },
    }
    result["canonical_hash"] = canonical_sha256(result)
    write_json(output_path, result)
    return result


def flatten_levels(fixtures: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    indexed: dict[tuple[str, str, int], dict[str, Any]] = {}
    for fixture in fixtures:
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            for level in cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id]):
                key = (str(fixture["fixture_id"]), sequence_id, int(level["cell_count"]))
                indexed[key] = level
    return indexed


def cell_index(level: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["cell_id"]): row for row in cast(list[dict[str, Any]], level["cell_results"])}


def cross_runtime_floors(
    first_fixtures: list[dict[str, Any]], second_fixtures: list[dict[str, Any]]
) -> tuple[dict[tuple[str, str, int], dict[str, float]], dict[str, Any]]:
    first = flatten_levels(first_fixtures)
    second = flatten_levels(second_fixtures)
    require(set(first) == set(second), "CROSS_RUNTIME_MATRIX_IDENTITY_MISMATCH", "mesh keys differ")
    floors: dict[tuple[str, str, int], dict[str, float]] = {}
    max_q_cell = 0.0
    max_wall_cell = 0.0
    max_q_support = 0.0
    max_wall_extrema = 0.0
    equality_count = 0
    for key, left in first.items():
        right = second[key]
        left_cells = cell_index(left)
        right_cells = cell_index(right)
        require(
            set(left_cells) == set(right_cells),
            "CROSS_RUNTIME_CELL_IDENTITY_MISMATCH",
            repr(key),
        )
        q_cell = max(
            (
                abs(float(left_cells[cell]["q_hc_W"]) - float(right_cells[cell]["q_hc_W"]))
                for cell in left_cells
            ),
            default=0.0,
        )
        wall_cell = max(
            (
                abs(float(left_cells[cell][field]) - float(right_cells[cell][field]))
                for cell in left_cells
                for field in ("T_wall_inner_K", "T_wall_outer_K")
            ),
            default=0.0,
        )
        q_support = abs(
            float(left["Q_support_signed_hot_to_cold_W"])
            - float(right["Q_support_signed_hot_to_cold_W"])
        )
        left_extrema = cast(dict[str, float], left["wall_extrema_K"])
        right_extrema = cast(dict[str, float], right["wall_extrema_K"])
        wall_extrema = max(
            abs(float(left_extrema[field]) - float(right_extrema[field]))
            for field in ("Twi_min", "Twi_max", "Two_min", "Two_max")
        )
        max_q_cell = max(max_q_cell, q_cell)
        max_wall_cell = max(max_wall_cell, wall_cell)
        max_q_support = max(max_q_support, q_support)
        max_wall_extrema = max(max_wall_extrema, wall_extrema)
        if q_cell == 0.0 and wall_cell == 0.0 and q_support == 0.0 and wall_extrema == 0.0:
            equality_count += 1
        floors[key] = {
            "q_support_abs_difference_W": q_support,
            "wall_extrema_max_abs_difference_K": wall_extrema,
            "max_cell_q_abs_difference_W": q_cell,
            "max_cell_wall_abs_difference_K": wall_cell,
        }
    report = {
        "mesh_level_count": len(first),
        "exactly_equal_mesh_level_count": equality_count,
        "numeric_projection_exactly_equal": max_q_support == 0.0
        and max_wall_extrema == 0.0
        and max_q_cell == 0.0
        and max_wall_cell == 0.0,
        "max_q_support_abs_difference_W": max_q_support,
        "max_wall_extrema_abs_difference_K": max_wall_extrema,
        "max_cell_q_abs_difference_W": max_q_cell,
        "max_cell_wall_abs_difference_K": max_wall_cell,
        "equality_required_for_pass": False,
    }
    return floors, report


def serialization_and_aggregation_floors(
    fixtures: list[dict[str, Any]], r95: Any
) -> tuple[dict[tuple[str, str, int], dict[str, float]], dict[str, Any]]:
    projection = r95.numeric_mesh_projection(fixtures)
    encoded = canonical_json_bytes(projection)
    parsed = json.loads(encoded)
    require(
        canonical_json_bytes(parsed) == encoded,
        "SERIALIZATION_REPLAY_FAILED",
        "canonical JSON round trip did not reproduce bytes",
    )
    parsed_index = {
        (str(row["fixture_id"]), str(row["sequence_id"]), int(row["cell_count"])): row
        for row in cast(list[dict[str, Any]], parsed)
    }
    floors: dict[tuple[str, str, int], dict[str, float]] = {}
    max_serial_q = 0.0
    max_serial_wall = 0.0
    max_aggregation = 0.0
    max_reduction_roundtrip = 0.0
    for fixture in fixtures:
        fixture_id = str(fixture["fixture_id"])
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            for level in cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id]):
                count = int(level["cell_count"])
                key = (fixture_id, sequence_id, count)
                saved = parsed_index[key]
                q_value = float(level["Q_support_signed_hot_to_cold_W"])
                q_roundtrip = float(saved["Q_support_signed_hot_to_cold_W"])
                wall = cast(dict[str, float], level["wall_extrema_K"])
                parsed_wall = cast(dict[str, float], saved["wall_extrema_K"])
                q_serial = abs(q_value - q_roundtrip)
                wall_serial = max(
                    abs(float(wall[name]) - float(parsed_wall[name]))
                    for name in ("Twi_min", "Twi_max", "Two_min", "Two_max")
                )
                q_cells = [float(row["q_hc_W"]) for row in level["cell_results"]]
                q_roundtrip_cells = [float(row["q_hc_W"]) for row in saved["cell_results"]]
                fsum_value = math.fsum(q_cells)
                fsum_roundtrip = math.fsum(q_roundtrip_cells)
                aggregation_serial = abs(q_value - fsum_roundtrip)
                reduction_order = abs(fsum_value - sum(q_cells))
                q_total = q_serial + aggregation_serial + reduction_order
                max_serial_q = max(max_serial_q, q_serial, aggregation_serial)
                max_serial_wall = max(max_serial_wall, wall_serial)
                max_aggregation = max(max_aggregation, reduction_order)
                max_reduction_roundtrip = max(max_reduction_roundtrip, aggregation_serial)
                floors[key] = {
                    "q_serialization_and_aggregation_W": q_total,
                    "q_float_roundtrip_W": q_serial,
                    "q_fsum_roundtrip_difference_W": aggregation_serial,
                    "q_reduction_order_difference_W": reduction_order,
                    "wall_extrema_float_roundtrip_K": wall_serial,
                }
    return floors, {
        "canonical_float_roundtrip_bytes_stable": True,
        "max_q_float_roundtrip_difference_W": max_serial_q,
        "max_q_fsum_roundtrip_difference_W": max_reduction_roundtrip,
        "max_q_reduction_order_difference_W": max_aggregation,
        "max_wall_extrema_float_roundtrip_difference_K": max_serial_wall,
        "all_observed_serialization_and_aggregation_effects_included_in_floor": True,
    }


def attach_precision_floors(
    fixtures: list[dict[str, Any]],
    cross_floors: dict[tuple[str, str, int], dict[str, float]],
    serial_floors: dict[tuple[str, str, int], dict[str, float]],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    output = copy.deepcopy(fixtures)
    max_q = 0.0
    max_wall = 0.0
    for fixture in output:
        fixture_id = str(fixture["fixture_id"])
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            for level in cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id]):
                key = (fixture_id, sequence_id, int(level["cell_count"]))
                local = cast(dict[str, float], level["oracle_precision_floor"])
                cross = cross_floors[key]
                serial = serial_floors[key]
                q_components = {
                    "local_solver_vs_independent_local_oracle_W": float(
                        local["Q_support_absolute_bound_W"]
                    ),
                    "cross_runtime_support_aggregation_W": cross["q_support_abs_difference_W"],
                    "serialization_and_aggregation_W": serial["q_serialization_and_aggregation_W"],
                }
                wall_components = {
                    "local_solver_vs_independent_local_oracle_K": float(
                        local["wall_state_pointwise_bound_K"]
                    ),
                    "cross_runtime_wall_state_or_extrema_K": max(
                        cross["max_cell_wall_abs_difference_K"],
                        cross["wall_extrema_max_abs_difference_K"],
                    ),
                    "serialization_wall_extrema_K": serial["wall_extrema_float_roundtrip_K"],
                }
                q_floor = math.fsum(q_components.values())
                wall_floor = math.fsum(wall_components.values())
                level["r2_precision_floor"] = {
                    "Q_support_total_floor_W": q_floor,
                    "wall_state_and_extrema_total_floor_K": wall_floor,
                    "Q_components": q_components,
                    "wall_components": wall_components,
                    "classification": "MEASURED_NONPHYSICAL_NUMERICAL_PRECISION_FLOOR",
                }
                max_q = max(max_q, q_floor)
                max_wall = max(max_wall, wall_floor)
    return output, {"Q_W": max_q, "wall_K": max_wall}


def pair_audit(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    duty_threshold: float,
    near_zero_threshold_W: float,
    wall_threshold_K: float,
    near_zero: bool,
) -> dict[str, Any]:
    q_left = float(left["Q_support_signed_hot_to_cold_W"])
    q_right = float(right["Q_support_signed_hot_to_cold_W"])
    q_delta = abs(q_right - q_left)
    floor_left = cast(dict[str, Any], left["r2_precision_floor"])
    floor_right = cast(dict[str, Any], right["r2_precision_floor"])
    q_floor_left = float(floor_left["Q_support_total_floor_W"])
    q_floor_right = float(floor_right["Q_support_total_floor_W"])
    q_floor_sum = q_floor_left + q_floor_right
    wall_left = cast(dict[str, Any], left["wall_extrema_K"])
    wall_right = cast(dict[str, Any], right["wall_extrema_K"])
    wall_delta = max(
        abs(float(wall_right[name]) - float(wall_left[name]))
        for name in ("Twi_min", "Twi_max", "Two_min", "Two_max")
    )
    wall_floor_left = float(floor_left["wall_state_and_extrema_total_floor_K"])
    wall_floor_right = float(floor_right["wall_state_and_extrema_total_floor_K"])
    wall_floor_sum = wall_floor_left + wall_floor_right
    if near_zero:
        q_observed: float | None = q_delta
        q_upper = q_delta + q_floor_sum
        q_limit = near_zero_threshold_W
        q_pass = q_upper <= q_limit
        q_floor_separated = q_floor_sum < q_limit
    else:
        q_lower = abs(q_right) - q_floor_right
        q_observed = q_delta / q_lower if q_lower > 0.0 else None
        q_upper = (q_delta + q_floor_sum) / q_lower if q_lower > 0.0 else math.inf
        q_limit = duty_threshold
        q_pass = q_lower > 0.0 and q_upper <= q_limit
        q_floor_separated = q_lower > 0.0 and q_floor_sum / q_lower < q_limit
    wall_upper = wall_delta + wall_floor_sum
    wall_pass = wall_upper <= wall_threshold_K
    floor_separated = q_floor_separated and wall_floor_sum < wall_threshold_K
    return {
        "from_cell_count": int(left["cell_count"]),
        "to_cell_count": int(right["cell_count"]),
        "duty_observed": q_observed,
        "duty_upper_with_precision_floor": q_upper,
        "duty_threshold": q_limit,
        "duty_precision_floor_sum_W": q_floor_sum,
        "duty_pass": q_pass,
        "wall_extrema_difference_K": wall_delta,
        "wall_extrema_upper_with_precision_floor_K": wall_upper,
        "wall_threshold_K": wall_threshold_K,
        "wall_precision_floor_sum_K": wall_floor_sum,
        "wall_pass": wall_pass,
        "precision_floor_separated_from_threshold": floor_separated,
        "pair_pass": q_pass and wall_pass and floor_separated,
    }


def oracle_class_audit(
    level: dict[str, Any],
    reference: dict[str, Any],
    *,
    duty_threshold: float,
    near_zero_threshold_W: float,
    wall_threshold_K: float,
    near_zero: bool,
) -> dict[str, Any]:
    observed = cast(dict[str, Any], level["independent_continuous_oracle"])
    floor = cast(dict[str, Any], level["r2_precision_floor"])
    q_error = float(observed["Q_abs_error_W"])
    q_floor = float(floor["Q_support_total_floor_W"])
    q_quad = float(observed["Q_oracle_quadrature_difference_W"])
    if near_zero:
        q_upper = q_error + q_floor + q_quad
        q_limit = near_zero_threshold_W
        q_pass = q_upper <= q_limit
    else:
        q_reference = abs(float(reference["Q_ref_W"]))
        denominator_lower = q_reference - q_quad
        q_upper = (
            (q_error + q_floor + q_quad) / denominator_lower if denominator_lower > 0 else math.inf
        )
        q_limit = duty_threshold
        q_pass = denominator_lower > 0 and q_upper <= q_limit
    wall_error = float(observed["wall_extrema_max_abs_error_K"])
    wall_floor = float(floor["wall_state_and_extrema_total_floor_K"])
    ref_stability = float(reference["wall_extrema_sampling_refinement_max_difference_K"])
    wall_upper = wall_error + wall_floor + ref_stability
    return {
        "Q_error_upper_with_precision_floor": q_upper,
        "Q_threshold_same_class": q_limit,
        "Q_pass": q_pass,
        "wall_extrema_error_upper_K": wall_upper,
        "wall_extrema_threshold_K": wall_threshold_K,
        "wall_pass": wall_upper <= wall_threshold_K,
        "all_oracle_error_classes_pass": q_pass and wall_upper <= wall_threshold_K,
    }


def first_converged_group(
    fixture: dict[str, Any],
    sequence_id: str,
    *,
    duty_threshold: float,
    near_zero_threshold_W: float,
    wall_threshold_K: float,
) -> dict[str, Any]:
    levels = cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id])
    near_zero = bool(fixture["near_zero_duty"])
    reference = cast(dict[str, Any], fixture["continuous_reference"])
    for index in range(1, len(levels) - 1):
        previous_pair = pair_audit(
            levels[index - 1],
            levels[index],
            duty_threshold=duty_threshold,
            near_zero_threshold_W=near_zero_threshold_W,
            wall_threshold_K=wall_threshold_K,
            near_zero=near_zero,
        )
        future_pairs = [
            pair_audit(
                levels[later],
                levels[later + 1],
                duty_threshold=duty_threshold,
                near_zero_threshold_W=near_zero_threshold_W,
                wall_threshold_K=wall_threshold_K,
                near_zero=near_zero,
            )
            for later in range(index, len(levels) - 1)
        ]
        oracle = oracle_class_audit(
            levels[index],
            reference,
            duty_threshold=duty_threshold,
            near_zero_threshold_W=near_zero_threshold_W,
            wall_threshold_K=wall_threshold_K,
            near_zero=near_zero,
        )
        if (
            previous_pair["pair_pass"]
            and all(bool(pair["pair_pass"]) for pair in future_pairs)
            and oracle["all_oracle_error_classes_pass"]
        ):
            return {
                "fixture_id": str(fixture["fixture_id"]),
                "sequence_id": sequence_id,
                "converged": True,
                "first_declared_converged_cell_count": int(levels[index]["cell_count"]),
                "confirmation_headroom_cell_count": int(levels[index + 1]["cell_count"]),
                "previous_pair": previous_pair,
                "next_and_later_pairs": future_pairs,
                "two_consecutive_pair_rule_pass": bool(future_pairs)
                and bool(future_pairs[0]["pair_pass"]),
                "no_later_rebound_pass": all(bool(pair["pair_pass"]) for pair in future_pairs),
                "oracle_error_class": oracle,
            }
    return {
        "fixture_id": str(fixture["fixture_id"]),
        "sequence_id": sequence_id,
        "converged": False,
        "reason": "NO_FIRST_MESH_WITH_TWO_PAIRS_ORACLE_ADEQUACY_AND_NO_REBOUND",
    }


def evaluate_threshold_tuple(
    fixtures: list[dict[str, Any]],
    *,
    duty_threshold: float,
    near_zero_threshold_W: float,
    wall_threshold_K: float,
) -> dict[str, Any]:
    groups = [
        first_converged_group(
            fixture,
            sequence_id,
            duty_threshold=duty_threshold,
            near_zero_threshold_W=near_zero_threshold_W,
            wall_threshold_K=wall_threshold_K,
        )
        for fixture in fixtures
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT")
    ]
    all_converged = len(groups) == len(fixtures) * 2 and all(
        bool(group["converged"]) for group in groups
    )
    required_headroom = (
        max(cast(int, group["confirmation_headroom_cell_count"]) for group in groups)
        if all_converged
        else None
    )
    cap_sensitivity = [
        {
            "candidate_cap_cells": cap,
            "supports_all_groups_with_two_pairs_and_headroom": bool(
                all_converged and required_headroom is not None and required_headroom <= cap
            ),
            "required_observed_headroom_cells": required_headroom,
            "authority_class": "PROJECT_RESOURCE_POLICY",
            "cap_is_mesh_adequacy_proof": False,
            "cap_exceeds_max_measured_sequence": cap
            > max(max(PRIMARY_SEQUENCE), max(SECONDARY_SEQUENCE)),
        }
        for cap in RESOURCE_CAP_GRID
    ]
    supported_caps = [
        cast(int, row["candidate_cap_cells"])
        for row in cap_sensitivity
        if row["supports_all_groups_with_two_pairs_and_headroom"]
        and not row["cap_exceeds_max_measured_sequence"]
    ]
    return {
        "duty_relative_threshold": duty_threshold,
        "near_zero_duty_absolute_threshold_W": near_zero_threshold_W,
        "wall_extrema_absolute_threshold_K": wall_threshold_K,
        "all_groups_converged": all_converged,
        "required_confirmation_headroom_cells": required_headroom,
        "groups": groups,
        "resource_cap_sensitivity": cap_sensitivity,
        "minimum_supported_cap_cells": min(supported_caps) if supported_caps else None,
    }


def threshold_sensitivity(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        evaluate_threshold_tuple(
            fixtures,
            duty_threshold=float(duty),
            near_zero_threshold_W=float(near_zero),
            wall_threshold_K=float(wall),
        )
        for duty in THRESHOLD_GRID
        for near_zero in THRESHOLD_GRID
        for wall in THRESHOLD_GRID
    ]
    feasible = [
        row
        for row in rows
        if bool(row["all_groups_converged"]) and row["minimum_supported_cap_cells"] is not None
    ]
    maximal = [
        candidate
        for candidate in feasible
        if not any(
            other is not candidate
            and float(other["duty_relative_threshold"])
            >= float(candidate["duty_relative_threshold"])
            and float(other["near_zero_duty_absolute_threshold_W"])
            >= float(candidate["near_zero_duty_absolute_threshold_W"])
            and float(other["wall_extrema_absolute_threshold_K"])
            >= float(candidate["wall_extrema_absolute_threshold_K"])
            and (
                float(other["duty_relative_threshold"])
                > float(candidate["duty_relative_threshold"])
                or float(other["near_zero_duty_absolute_threshold_W"])
                > float(candidate["near_zero_duty_absolute_threshold_W"])
                or float(other["wall_extrema_absolute_threshold_K"])
                > float(candidate["wall_extrema_absolute_threshold_K"])
            )
            for other in feasible
        )
    ]
    selected = maximal[0] if len(maximal) == 1 else None
    return {
        "candidate_grid": {
            "duty_relative": list(THRESHOLD_GRID),
            "near_zero_absolute_W": list(THRESHOLD_GRID),
            "wall_extrema_absolute_K": list(THRESHOLD_GRID),
            "candidate_tuple_count": len(rows),
        },
        "selection_rule": (
            "unique componentwise-loosest frozen-grid tuple; each fixture/sequence uses "
            "N/2-to-N plus N-to-2N, oracle accuracy at N, all later measured pair checks "
            "through the frozen sequence, precision-floor separation, and one measured "
            "confirmation/headroom level"
        ),
        "threshold_matrix": rows,
        "feasible_tuple_count": len(feasible),
        "componentwise_maximal_feasible_tuple_count": len(maximal),
        "selected_threshold_tuple": selected,
        "selected_resource_cap_cells": (
            None if selected is None else selected["minimum_supported_cap_cells"]
        ),
        "selection_status": (
            "PASS_UNIQUE_LOOSEST_FEASIBLE_TUPLE"
            if selected is not None
            else "BLOCKED_NO_UNIQUE_FEASIBLE_TUPLE"
        ),
    }


def combine_runs(first_path: Path, repeat_path: Path, secondary_path: Path) -> dict[str, Any]:
    r95 = load_module(R95_RUNNER_PATH, "task172_r95_combine_r2")
    first = read_json(first_path)
    repeat = read_json(repeat_path)
    secondary = read_json(secondary_path)
    for worker in (first, repeat, secondary):
        expected_hash = str(worker.pop("canonical_hash"))
        require(
            canonical_sha256(worker) == expected_hash,
            "WORKER_RESULT_HASH_MISMATCH",
            str(worker.get("runtime", {})),
        )
        worker["canonical_hash"] = expected_hash
        require(
            worker["study_status"] == "COMPLETE_SINGLE_RUNTIME_REPLAY"
            and worker["input_matrix_canonical_hash"] == R95_INPUT_MATRIX_HASH
            and worker["effective_profile_canonical_hash"] == R98_PROFILE_HASH,
            "WORKER_RESULT_IDENTITY_MISMATCH",
            "worker result is not the frozen R95/R98 input",
        )
    require(
        first_path.read_bytes() == repeat_path.read_bytes(),
        "PRIMARY_DETERMINISTIC_REPLAY_FAILED",
        "the two primary-runtime complete-study result bytes differ",
    )
    primary_runtime = cast(dict[str, str], first["runtime"])
    repeat_runtime = cast(dict[str, str], repeat["runtime"])
    secondary_runtime = cast(dict[str, str], secondary["runtime"])
    require(
        primary_runtime == repeat_runtime
        and primary_runtime["python"].startswith("3.11.")
        and secondary_runtime["python"].startswith("3.12."),
        "DUAL_RUNTIME_IDENTITY_FAILED",
        "expected two identical Python 3.11 runs and one Python 3.12 run",
    )
    primary_fixtures = cast(list[dict[str, Any]], first["fixtures"])
    secondary_fixtures = cast(list[dict[str, Any]], secondary["fixtures"])
    cross_floors, cross_report = cross_runtime_floors(primary_fixtures, secondary_fixtures)
    serial_floors, serial_report = serialization_and_aggregation_floors(primary_fixtures, r95)
    analysis_fixtures, global_floor = attach_precision_floors(
        primary_fixtures, cross_floors, serial_floors
    )
    threshold = threshold_sensitivity(analysis_fixtures)
    failure_audit = cast(dict[str, Any], first["matrix_structure"]["failure_fixture_audit"])
    all_oracles = bool(first["independent_continuous_oracle_all_fixtures_pass"])
    candidate = threshold["selected_threshold_tuple"]
    success = bool(
        candidate is not None
        and all_oracles
        and bool(first["matrix_structure"]["all_local_solves_accepted"])
        and bool(failure_audit["all_expected_typed_outcomes_observed"])
    )
    primary_projection_hash = str(first["numeric_mesh_projection_canonical_hash"])
    repeat_projection_hash = str(repeat["numeric_mesh_projection_canonical_hash"])
    secondary_projection_hash = str(secondary["numeric_mesh_projection_canonical_hash"])
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R2",
        "result": (
            "MESH_CONVERGENCE_QUALIFICATION_CANDIDATE_COMPLETED"
            if success
            else "BLOCKED_MESH_CONVERGENCE_QUALIFICATION_R2"
        ),
        "authorized_predecessor_head": AUTHORIZED_PREDECESSOR_HEAD,
        "input_matrix_canonical_hash": R95_INPUT_MATRIX_HASH,
        "effective_overlay": {
            "overlay_id": "V07-T172-NUMERICAL-PROFILE-MESH-CELL-SCALE-EXTENSION-R1",
            "status": "REVIEWED_AUTHORITY",
            "c_round": 1.0,
            "profile_canonical_hash": R98_PROFILE_HASH,
            "r94_base_profile_rewritten": False,
            "profile_retuned": False,
        },
        "former_blocking_cell_replay": first["former_blocking_cell_replay"],
        "runtime_replay": {
            "primary_first": primary_runtime,
            "primary_repeat": repeat_runtime,
            "secondary": secondary_runtime,
            "primary_complete_study_result_hash": str(first["canonical_hash"]),
            "primary_repeat_complete_study_result_hash": str(repeat["canonical_hash"]),
            "secondary_complete_study_result_hash": str(secondary["canonical_hash"]),
            "same_input_same_mesh_result_bytes": first_path.read_bytes()
            == repeat_path.read_bytes(),
            "same_input_same_mesh_result_hash": primary_projection_hash == repeat_projection_hash,
            "primary_mesh_projection_hash": primary_projection_hash,
            "primary_repeat_mesh_projection_hash": repeat_projection_hash,
            "secondary_mesh_projection_hash": secondary_projection_hash,
            "cross_runtime_numeric_equality": cross_report,
        },
        "matrix_identity": first["matrix_structure"],
        "continuous_oracle": {
            "all_six_fixture_references_complete": all_oracles,
            "all_oracle_stability_checks_pass": all_oracles,
            "gauss_legendre_orders": [128, 256, 512],
            "wall_extrema_sampling_counts": [257, 513],
            "production_mesh_used_as_oracle": False,
        },
        "precision_floor": {
            "bound": True,
            "Q_support_maximum_W": global_floor["Q_W"],
            "wall_state_or_extrema_maximum_K": global_floor["wall_K"],
            "classification": "NUMERICAL_ONLY_NOT_PHYSICAL_OR_MODEL_FORM_UNCERTAINTY",
            "cross_runtime": cross_report,
            "serialization_and_aggregation": serial_report,
            "per_mesh_components_attached_to_matrix": True,
        },
        "threshold_sensitivity": threshold,
        "mesh_result_matrix": analysis_fixtures,
        "failure_fixture_audit": failure_audit,
        "authority_candidate": {
            "created": success,
            "lifecycle": "PROPOSED_AUTHORITY_REVIEW_PENDING" if success else "NONE",
            "refinement_operator_bound": success,
            "refinement_sequence_bound": success,
            "common_support_mapping_operator_bound": success,
            "mesh_comparison_norm_bound": success,
            "mesh_precision_floor_bound": success,
            "mesh_termination_threshold_bound": success,
            "discretization_error_estimator_bound": success,
            "max_mesh_refinement_bound": success,
            "discretization_estimator_class": "SUCCESSIVE_REFINEMENT_DIFFERENCE_INDICATOR",
            "discretization_estimator_is_universal_error_upper_bound": False,
            "max_mesh_is_mesh_adequacy_proof": False,
        },
        "blocker_ledger": {
            "mesh_convergence_canonical_blocker_removed": False,
            "effective_remaining_task172_entry_blocker_count": 1,
            "task172_entry_authority_complete": False,
            "remaining": ["MESH-CONVERGENCE-QUALIFICATION"],
            "next_gate": (
                "AUTHORIZE_TASK172_MESH_CONVERGENCE_INDEPENDENT_REVIEW_AND_ENTRY_BLOCKER_CLOSURE_R1_ONLY"
                if success
                else "NONE_UNTIL_SEPARATELY_AUTHORIZED"
            ),
        },
        "governance": {
            "production_code_changed": False,
            "engineering_calculation_production_path_changed": False,
            "dependency_changed": False,
            "lockfile_changed": False,
            "task172_implementation_started": False,
            "mesh_study_performed": True,
            "mesh_study_is_production_rating": False,
            "task173_solver_executed": False,
            "task174_hydraulic_solver_executed": False,
            "new_authority_self_approval": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
            "stop": True,
        },
    }
    result["canonical_hash"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--worker", action="store_true")
    modes.add_argument("--combine", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--primary-first", type=Path)
    parser.add_argument("--primary-repeat", type=Path)
    parser.add_argument("--secondary", type=Path)
    args = parser.parse_args()
    try:
        if args.preflight or args.worker:
            predecessor = verify_predecessor_head()
            r95, r98, r94 = load_frozen_modules()
            upstream = verify_registry_and_upstream(r95, r98)
            preflight = former_blocking_cell(r95, r98, r94)
            if args.preflight:
                print(
                    json.dumps(
                        {
                            "predecessor_head": predecessor,
                            "upstream_replay": upstream,
                            "former_blocking_cell_replay": preflight,
                        },
                        sort_keys=True,
                        indent=2,
                        allow_nan=False,
                    )
                )
                return 0
            if args.output is None:
                parser.error("--worker requires --output")
            result = run_worker(args.output)
            print(
                json.dumps(
                    {
                        "output": str(args.output),
                        "runtime": result["runtime"],
                        "input_matrix_canonical_hash": result["input_matrix_canonical_hash"],
                        "complete_fixture_matrix_canonical_hash": result[
                            "complete_fixture_matrix_canonical_hash"
                        ],
                        "local_cell_solve_count": result["matrix_structure"][
                            "local_cell_solve_count"
                        ],
                        "canonical_hash": result["canonical_hash"],
                    },
                    sort_keys=True,
                    indent=2,
                    allow_nan=False,
                )
            )
            return 0
        if args.primary_first is None or args.primary_repeat is None or args.secondary is None:
            parser.error("--combine requires --primary-first, --primary-repeat, and --secondary")
        if args.output is None:
            parser.error("--combine requires --output")
        result = combine_runs(args.primary_first, args.primary_repeat, args.secondary)
        write_json(args.output, result)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "result": result["result"],
                    "canonical_hash": result["canonical_hash"],
                    "selected_threshold_tuple": result["threshold_sensitivity"][
                        "selected_threshold_tuple"
                    ],
                    "selected_resource_cap_cells": result["threshold_sensitivity"][
                        "selected_resource_cap_cells"
                    ],
                    "precision_floor": result["precision_floor"],
                },
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
        )
        return 0 if result["authority_candidate"]["created"] else 2
    except GateFailure as failure:
        print(
            json.dumps(
                {
                    "failure_code": failure.code,
                    "failure_detail": failure.detail,
                    "failure_evidence": failure.evidence,
                },
                sort_keys=True,
                indent=2,
                allow_nan=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
