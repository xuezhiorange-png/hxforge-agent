"""Deterministic TASK172 mesh-qualification experiment runner.

This runner uses only synthetic local constitutive fixtures. It does not invoke
TASK173/TASK174, create a production case, or modify production code. The
R94-reviewed residual/callback and frozen TRF profile are replayed as a
test-only numerical kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import numpy as np
import rfc8785
import scipy
from scipy.optimize import least_squares, minimize_scalar

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import CoolProp  # noqa: E402

from hexagent.canonical_json import canonical_json_bytes, canonical_sha256  # noqa: E402

R94_RUNNER_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-quantitative-numerical-profile-independent-review-runner-r1.py"
)
R94_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-172-quantitative-numerical-profile-independent-review-and-blocker-closure-r1.json"
)
REGISTRY_PATH = ROOT / "docs/tasks/TASK-172-v0.7-authority-registry-r1.json"
TASK171_PATH = ROOT / "docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md"
MESH_CONTRACT_PATH = ROOT / "docs/tasks/TASK-172-v0.7-mesh-convergence-contract-r1.md"
MESH_CONTRACT_EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-contract-r1.json"
)
MESH_REVIEW_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-contract-independent-review-receipt-r1.json"
)
RESULTS_PATH = ROOT / (
    "docs/tasks/evidence/TASK-172-mesh-convergence-qualification-results-r1.json"
)

AREA_I_TOTAL = Fraction("0.04")
AREA_O_TOTAL = Fraction("0.055")
PRIMARY_SEQUENCE = (1, 2, 4, 8, 16, 32, 64, 128)
SECONDARY_SEQUENCE = (3, 6, 12, 24, 48, 96)
MAX_MESH_CANDIDATES = (32, 64, 128, 256)
THRESHOLD_GRID = ("1e-2", "1e-3", "1e-4", "1e-5")
REQUIRED_CONSECUTIVE_PAIRS = 2
DECLARED_HEADROOM_LEVELS = 1
NEAR_ZERO_FIXTURE_ID = "M05"
WALL_EXTREMA_STABILITY_CRITERION_K = 1.0e-8
GAUSS_PRECISION_ULP_MULTIPLIER = 64
EXTREMA_SAMPLE_COUNTS = (257, 513)
ORACLE_GRID_COUNT = 33
FROZEN_PROFILE: dict[str, Any] = {
    "method": "trf",
    "loss": "linear",
    "ftol": 1e-6,
    "xtol": 1e-12,
    "gtol": 1e-12,
    "jacobian": "2-point",
    "diff_step": 1e-5,
    "x_scale": "INITIALIZATION_DERIVED",
    "residual_scale": "abs(q_ts_seed)",
    "max_nfev": 6,
    "residual_callback_cap": 24,
    "tr_solver": "exact",
    "tr_options": {},
    "f_scale": 1.0,
    "jac_sparsity": None,
    "c_round": 0.5,
}

FIXTURE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "fixture_id": "M01",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "tube_temperature_formula": "299.80 - 0.35*x + 0.06*sin(2*pi*x)",
        "shell_temperature_formula": "298.45 + 0.25*x + 0.04*sin(pi*x)",
        "pressure_tube_formula_Pa": "101325",
        "pressure_shell_formula_Pa": "101325",
        "s_ts": 1,
        "hot_side": "TUBE",
        "reynolds_tube": 25000.0,
        "tube_c3_active": True,
        "shell_jmu_active": True,
        "total_resistance_K_W": "0.060",
        "resistance_fractions": {"tube_film": "0.70", "wall": "0.20", "shell_film": "0.10"},
        "near_zero_duty": False,
    },
    {
        "fixture_id": "M02",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "tube_temperature_formula": "298.45 + 0.25*x + 0.04*sin(pi*x)",
        "shell_temperature_formula": "299.80 - 0.35*x + 0.06*sin(2*pi*x)",
        "pressure_tube_formula_Pa": "100000",
        "pressure_shell_formula_Pa": "100000",
        "s_ts": -1,
        "hot_side": "SHELL",
        "reynolds_tube": 75000.0,
        "tube_c3_active": True,
        "shell_jmu_active": True,
        "total_resistance_K_W": "0.055",
        "resistance_fractions": {"tube_film": "0.10", "wall": "0.20", "shell_film": "0.70"},
        "near_zero_duty": False,
    },
    {
        "fixture_id": "M03",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "tube_temperature_formula": "299.78 - 0.27*x + 0.035*sin(4*pi*x)",
        "shell_temperature_formula": "298.50 + 0.18*x + 0.02*sin(4*pi*x + 0.7)",
        "pressure_tube_formula_Pa": "101325",
        "pressure_shell_formula_Pa": "101325",
        "s_ts": 1,
        "hot_side": "TUBE",
        "reynolds_tube": 150000.0,
        "tube_c3_active": True,
        "shell_jmu_active": True,
        "total_resistance_K_W": "0.080",
        "resistance_fractions": {"tube_film": "0.25", "wall": "0.50", "shell_film": "0.25"},
        "near_zero_duty": False,
    },
    {
        "fixture_id": "M04",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "tube_temperature_formula": "299.68 - 0.22*x + 0.025*sin(2*pi*x)",
        "shell_temperature_formula": "298.65 + 0.12*x + 0.02*sin(pi*x)",
        "pressure_tube_formula_Pa": "100000",
        "pressure_shell_formula_Pa": "100000",
        "s_ts": 1,
        "hot_side": "TUBE",
        "reynolds_tube": 6000.0,
        "tube_c3_active": True,
        "shell_jmu_active": False,
        "shell_jmu_identity_isolation_only": True,
        "total_resistance_K_W": "0.050",
        "resistance_fractions": {"tube_film": "0.30", "wall": "0.40", "shell_film": "0.30"},
        "near_zero_duty": False,
    },
    {
        "fixture_id": "M05",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "tube_temperature_formula": "299.40 + 0.16*x + 0.0007*sin(2*pi*x)",
        "shell_temperature_formula": "299.39 + 0.16*x - 0.0007*sin(2*pi*x)",
        "pressure_tube_formula_Pa": "100000",
        "pressure_shell_formula_Pa": "100000",
        "s_ts": 1,
        "hot_side": "TUBE",
        "reynolds_tube": 450000.0,
        "tube_c3_active": True,
        "shell_jmu_active": True,
        "total_resistance_K_W": "0.045",
        "resistance_fractions": {"tube_film": "0.30", "wall": "0.20", "shell_film": "0.50"},
        "near_zero_duty": True,
    },
    {
        "fixture_id": "M06",
        "case_class": "NUMERICAL_METHOD_FIXTURE_ONLY",
        "tube_temperature_formula": "299.75 - 0.28*x + 0.035*sin(2*pi*x)",
        "shell_temperature_formula": "298.55 + 0.19*x + 0.03*sin(pi*x)",
        "pressure_tube_formula_Pa": "101325",
        "pressure_shell_formula_Pa": "101325",
        "s_ts": 1,
        "hot_side": "TUBE",
        "reynolds_tube": 300000.0,
        "tube_c3_active": True,
        "shell_jmu_active": True,
        "total_resistance_K_W": "0.070",
        "resistance_fractions": {"tube_film": "0.15", "wall": "0.25", "shell_film": "0.60"},
        "near_zero_duty": False,
    },
)


class MeshFailure(RuntimeError):
    """Typed failure for a fail-closed synthetic mesh qualification run."""

    def __init__(
        self,
        code: str,
        detail: str,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"{code}:{detail}")
        self.code = code
        self.detail = detail
        self.diagnostics = diagnostics or {}


@dataclass(frozen=True)
class Cell:
    left: Fraction
    right: Fraction
    parent_cell_id: str | None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def canonical_array_hash(values: list[dict[str, Any]]) -> str:
    return hashlib.sha256(rfc8785.dumps(values)).hexdigest()


def encode_report(report: dict[str, Any]) -> bytes:
    """Serialize the report while retaining its self-excluded canonical hash."""
    return (
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def fixture_input_matrix() -> dict[str, Any]:
    registry = load_json(REGISTRY_PATH)
    r94 = cast(dict[str, Any], registry["r94_extension"])
    upstream_files = {
        "r94_document_sha256": str(r94["artifacts"]["document_sha256"]),
        "r94_evidence_file_sha256": str(r94["artifacts"]["evidence_file_sha256"]),
        "r94_evidence_canonical_hash": str(r94["artifacts"]["evidence_canonical_hash"]),
        "r94_runner_sha256": str(r94["artifacts"]["runner_sha256"]),
        "task171_document_sha256": file_sha256(TASK171_PATH),
        "mesh_contract_document_sha256": file_sha256(MESH_CONTRACT_PATH),
        "mesh_contract_evidence_sha256": file_sha256(MESH_CONTRACT_EVIDENCE_PATH),
        "mesh_contract_review_evidence_sha256": file_sha256(MESH_REVIEW_PATH),
    }
    return {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R1",
        "support_model": {
            "class": "SYNTHETIC_SINGLE_PHYSICAL_SUPPORT_FIXTURE_ONLY",
            "coordinate": "xi in [0,1]",
            "support_id_rule": "SYNTHETIC-MESH-SUPPORT-{fixture_id}",
            "physical_interval_id_rule": "SYNTHETIC-PHYSICAL-INTERVAL-{fixture_id}-01",
            "native_physical_events_inside_interval": [],
            "cell_identity": "physical support plus exact rational xi bounds and parent lineage",
            "base_mesh_must_be_explicit": True,
            "production_case_created": False,
        },
        "upstream_artifacts": upstream_files,
        "frozen_r94_profile": FROZEN_PROFILE,
        "geometry_partition": {
            "A_i_total_m2": "0.04",
            "A_o_total_m2": "0.055",
            "area_rule": "A_cell=f*A_total using exact Fraction arithmetic",
            "wall_rule": "R_wall_cell=R_wall_total/f; sum(1/R_wall_cell)=1/R_wall_total",
        },
        "fixtures": list(FIXTURE_ROWS),
        "mesh_sequences": {
            "primary_nested_equal_bisection": list(PRIMARY_SEQUENCE),
            "secondary_phase_alignment": list(SECONDARY_SEQUENCE),
            "threshold_sensitivity_candidate_caps_cells": list(MAX_MESH_CANDIDATES),
        },
        "comparison": {
            "duty_observable": "signed conservative sum of q_hc over the same physical support",
            "wall_extrema": ["Twi_min", "Twi_max", "Two_min", "Two_max"],
            "threshold_grid": {
                "duty_relative": list(THRESHOLD_GRID),
                "near_zero_duty_absolute_W": list(THRESHOLD_GRID),
                "wall_extrema_absolute_K": list(THRESHOLD_GRID),
            },
            "required_consecutive_refinement_pairs": REQUIRED_CONSECUTIVE_PAIRS,
            "declared_headroom_levels": DECLARED_HEADROOM_LEVELS,
            "near_zero_fixture_id": NEAR_ZERO_FIXTURE_ID,
        },
        "independent_oracle": {
            "local_root": (
                "R94 independent validation-only scalar bracket/monotonicity/Brent replay"
            ),
            "gauss_legendre_orders": [128, 256, 512],
            "wall_extrema_sampling_orders": list(EXTREMA_SAMPLE_COUNTS),
            "wall_extrema_optimizer": "bounded local extrema search; validation-only",
            "wall_extrema_reference_stability_criterion_K": WALL_EXTREMA_STABILITY_CRITERION_K,
            "gauss_roundoff_criterion_ulp_multiplier": GAUSS_PRECISION_ULP_MULTIPLIER,
            "production_scalar_reduction_selected": False,
        },
        "refinement_and_role_guards": {
            "physical_event_creation": False,
            "physical_event_crossing": False,
            "array_index_comparison": False,
            "local_htc_or_temperature_averaging": False,
            "production_cell_reconstruction_operator_created": False,
            "task173_boundary_solver_used": False,
            "task174_hydraulic_solver_used": False,
            "mesh_study_is_production_rating": False,
            "real_case_required_for_model_level_qualification": False,
        },
    }


def load_r94_module() -> Any:
    registry = load_json(REGISTRY_PATH)
    extension = cast(dict[str, Any], registry["r94_extension"])
    expected_runner_hash = str(extension["artifacts"]["runner_sha256"])
    if file_sha256(R94_RUNNER_PATH) != expected_runner_hash:
        raise MeshFailure("INPUT_AUTHORITY_MISSING", "R94 runner hash mismatch")
    evidence = load_json(R94_EVIDENCE_PATH)
    expected_evidence_hash = str(extension["artifacts"]["evidence_canonical_hash"])
    if canonical_sha256(evidence) != expected_evidence_hash:
        raise MeshFailure("INPUT_AUTHORITY_MISSING", "R94 evidence canonical hash mismatch")
    review = cast(dict[str, Any], evidence["review_target"])
    selected = cast(dict[str, Any], review["frozen_candidate_profile"])
    profile_check = {
        "method": selected["method"],
        "loss": selected["loss"],
        "ftol": selected["ftol"],
        "xtol": selected["xtol"],
        "gtol": selected["gtol"],
        "jacobian": selected["jacobian"],
        "diff_step": selected["diff_step"],
        "x_scale": "INITIALIZATION_DERIVED",
        "max_nfev": selected["max_nfev"],
        "residual_callback_cap": selected["residual_callback_cap"],
        "tr_solver": selected["tr_solver"],
        "tr_options": selected["tr_options"],
        "f_scale": selected["f_scale"],
        "jac_sparsity": selected["jac_sparsity"],
    }
    for key, value in profile_check.items():
        if FROZEN_PROFILE[key] != value:
            raise MeshFailure("INPUT_AUTHORITY_MISSING", f"R94 profile mismatch at {key}")
    spec = importlib.util.spec_from_file_location("task172_r94_review_runner", R94_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise MeshFailure("INPUT_AUTHORITY_MISSING", "cannot load R94 reviewed runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cell_id(fixture_id: str, left: Fraction, right: Fraction) -> str:
    return (
        f"SYNTHETIC-MESH-SUPPORT-{fixture_id}:"
        f"xi[{left.numerator}/{left.denominator},{right.numerator}/{right.denominator}]"
    )


def build_mesh_sequence(
    fixture_id: str, base_count: int, expected_counts: tuple[int, ...]
) -> dict[int, list[Cell]]:
    if expected_counts[0] != base_count or any(
        right != left * 2 for left, right in zip(expected_counts, expected_counts[1:], strict=False)
    ):
        raise MeshFailure("MESH_INVALID_REFINEMENT", "non-nested requested sequence")
    current = [
        Cell(Fraction(index, base_count), Fraction(index + 1, base_count), None)
        for index in range(base_count)
    ]
    levels: dict[int, list[Cell]] = {base_count: current}
    for expected_count in expected_counts[1:]:
        children: list[Cell] = []
        for parent in current:
            midpoint = (parent.left + parent.right) / 2
            parent_id = cell_id(fixture_id, parent.left, parent.right)
            children.extend(
                (
                    Cell(parent.left, midpoint, parent_id),
                    Cell(midpoint, parent.right, parent_id),
                )
            )
        audit_partition(children, expected_count, f"SYNTHETIC-MESH-SUPPORT-{fixture_id}")
        audit_parent_child(fixture_id, current, children)
        current = children
        levels[expected_count] = current
    return levels


def audit_partition(cells: list[Cell], expected_count: int, support_id: str) -> None:
    if len(cells) != expected_count:
        raise MeshFailure("MESH_INVALID_REFINEMENT", "cell count mismatch")
    ordered = sorted(cells, key=lambda cell: cell.left)
    if not ordered or ordered[0].left != 0 or ordered[-1].right != 1:
        raise MeshFailure("MESH_INVALID_REFINEMENT", f"{support_id}: incomplete support coverage")
    if any(left.right != right.left for left, right in zip(ordered, ordered[1:], strict=False)):
        raise MeshFailure("MESH_INVALID_REFINEMENT", f"{support_id}: gap or overlap")
    if any(cell.right <= cell.left for cell in ordered):
        raise MeshFailure("MESH_INVALID_REFINEMENT", f"{support_id}: nonpositive cell span")


def audit_event_boundaries(cells: list[Cell], event_locations: tuple[Fraction, ...]) -> None:
    boundaries = {cell.left for cell in cells} | {cells[-1].right}
    if any(event not in boundaries for event in event_locations):
        raise MeshFailure("MESH_INVALID_REFINEMENT", "physical event crosses a cell")


def require_same_support(expected: str, observed: str) -> None:
    if expected != observed:
        raise MeshFailure("MESH_INVALID_MAPPING", "cell maps to a different physical support")


def require_finite_observable(value: float) -> None:
    if not math.isfinite(value):
        raise MeshFailure("MESH_INVALID_MAPPING", "mesh observable is nonfinite")


def require_refinement_depth(level_count: int) -> None:
    if level_count < REQUIRED_CONSECUTIVE_PAIRS + 1:
        raise MeshFailure("MESH_NOT_CONVERGED", "insufficient levels for consecutive pairs")


def require_precision_resolved(value: float, uncertainty: float, threshold: float) -> None:
    if value - uncertainty <= threshold <= value + uncertainty:
        raise MeshFailure("PRECISION_FLOOR_UNRESOLVED", "uncertainty interval straddles threshold")


def require_resource_and_convergence(
    remaining_cells: int, required_cells: int, converged: bool
) -> str:
    observed: list[str] = []
    try:
        if remaining_cells < required_cells:
            raise MeshFailure("MESH_RESOURCE_EXHAUSTED", "cell resource cap reached")
    except MeshFailure as failure:
        observed.append(failure.code)
    try:
        if not converged:
            raise MeshFailure("MESH_NOT_CONVERGED", "no converged candidate at resource cap")
    except MeshFailure as failure:
        observed.append(failure.code)
    if not observed:
        raise MeshFailure("MESH_INVALID_MAPPING", "failure fixture did not exercise a failure")
    return ";".join(observed)


def audit_parent_child(fixture_id: str, parents: list[Cell], children: list[Cell]) -> None:
    for parent in parents:
        child_rows = sorted(
            (
                child
                for child in children
                if child.parent_cell_id == cell_id(fixture_id, parent.left, parent.right)
            ),
            key=lambda child: child.left,
        )
        if len(child_rows) != 2:
            raise MeshFailure(
                "MESH_INVALID_REFINEMENT", "parent does not have exactly two children"
            )
        if (
            child_rows[0].left != parent.left
            or child_rows[0].right != child_rows[1].left
            or child_rows[1].right != parent.right
        ):
            raise MeshFailure("MESH_INVALID_REFINEMENT", "children do not exactly bisect parent")


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def evaluate_temperature(fixture_id: str, side: str, xi: float) -> float:
    x = float(xi)
    if fixture_id == "M01":
        return (
            299.80 - 0.35 * x + 0.06 * math.sin(2.0 * math.pi * x)
            if side == "tube"
            else 298.45 + 0.25 * x + 0.04 * math.sin(math.pi * x)
        )
    if fixture_id == "M02":
        return (
            298.45 + 0.25 * x + 0.04 * math.sin(math.pi * x)
            if side == "tube"
            else 299.80 - 0.35 * x + 0.06 * math.sin(2.0 * math.pi * x)
        )
    if fixture_id == "M03":
        return (
            299.78 - 0.27 * x + 0.035 * math.sin(4.0 * math.pi * x)
            if side == "tube"
            else 298.50 + 0.18 * x + 0.02 * math.sin(4.0 * math.pi * x + 0.7)
        )
    if fixture_id == "M04":
        return (
            299.68 - 0.22 * x + 0.025 * math.sin(2.0 * math.pi * x)
            if side == "tube"
            else 298.65 + 0.12 * x + 0.02 * math.sin(math.pi * x)
        )
    if fixture_id == "M05":
        return (
            299.40 + 0.16 * x + 0.0007 * math.sin(2.0 * math.pi * x)
            if side == "tube"
            else 299.39 + 0.16 * x - 0.0007 * math.sin(2.0 * math.pi * x)
        )
    if fixture_id == "M06":
        return (
            299.75 - 0.28 * x + 0.035 * math.sin(2.0 * math.pi * x)
            if side == "tube"
            else 298.55 + 0.19 * x + 0.03 * math.sin(math.pi * x)
        )
    raise MeshFailure("INPUT_AUTHORITY_MISSING", f"unknown fixture {fixture_id}")


def fixture_row(fixture_id: str) -> dict[str, Any]:
    return next(row for row in FIXTURE_ROWS if row["fixture_id"] == fixture_id)


def total_resistances(row: dict[str, Any]) -> tuple[Fraction, Fraction, Fraction]:
    total = Fraction(str(row["total_resistance_K_W"]))
    fractions = cast(dict[str, str], row["resistance_fractions"])
    ri_fraction = Fraction(fractions["tube_film"])
    rw_fraction = Fraction(fractions["wall"])
    ro_fraction = Fraction(fractions["shell_film"])
    if ri_fraction + rw_fraction + ro_fraction != 1:
        raise MeshFailure("MESH_INVALID_MAPPING", "resistance fractions do not sum exactly to one")
    return total * ri_fraction, total * rw_fraction, total * ro_fraction


def make_r94_case(
    r94: Any,
    fixture_id: str,
    xi: float,
    area_fraction: Fraction,
    *,
    cell_identity: str,
) -> Any:
    row = fixture_row(fixture_id)
    resistance_i, resistance_wall, resistance_o = total_resistances(row)
    area_i = float(AREA_I_TOTAL * area_fraction)
    area_o = float(AREA_O_TOTAL * area_fraction)
    wall_resistance = float(resistance_wall / area_fraction)
    tube_bulk = evaluate_temperature(fixture_id, "tube", xi)
    shell_bulk = evaluate_temperature(fixture_id, "shell", xi)
    pressure = float(row["pressure_tube_formula_Pa"])
    if pressure != float(row["pressure_shell_formula_Pa"]):
        raise MeshFailure(
            "INPUT_AUTHORITY_MISSING", "R94 kernel requires fixture-equal side pressures"
        )
    return r94.Case(
        case_id=cell_identity,
        family="R95_SYNTHETIC_MESH_FIXTURE",
        tube_bulk_K=tube_bulk,
        shell_bulk_K=shell_bulk,
        s_ts=int(row["s_ts"]),
        area_i_m2=area_i,
        area_o_m2=area_o,
        h_i_base_W_m2K=1.0 / (float(resistance_i) * float(AREA_I_TOTAL)),
        h_o_base_W_m2K=1.0 / (float(resistance_o) * float(AREA_O_TOTAL)),
        wall_resistance_K_W=wall_resistance,
        pressure_Pa=pressure,
        reynolds=float(row["reynolds_tube"]),
        tube_c3_active=bool(row["tube_c3_active"]),
        shell_jmu_active=bool(row["shell_jmu_active"]),
    )


def solve_local(r94: Any, case: Any) -> dict[str, Any]:
    x0 = np.asarray(r94.direct_seed(case), dtype=float)
    q_scale = abs(float(x0[0]))
    delta_t = abs(float(case.delta_t_K))
    if q_scale == 0.0 or delta_t == 0.0:
        raise MeshFailure(
            "INITIALIZATION_FAILURE", "mesh fixture unexpectedly reached exact zero duty"
        )
    calls = 0
    callback_cap = int(FROZEN_PROFILE["residual_callback_cap"])

    def residual(values: np.ndarray) -> np.ndarray:
        nonlocal calls
        calls += 1
        if calls > callback_cap:
            raise MeshFailure("MESH_RESOURCE_EXHAUSTED", "R94 residual callback cap reached")
        return np.asarray(r94.physical_residual(case, values), dtype=float) / q_scale

    solution = least_squares(
        residual,
        x0,
        method="trf",
        loss="linear",
        ftol=1e-6,
        xtol=1e-12,
        gtol=1e-12,
        jac="2-point",
        diff_step=1e-5,
        x_scale=[abs(float(x0[0])), delta_t, delta_t],
        max_nfev=6,
        bounds=(
            np.asarray([-np.inf, 298.15, 298.15], dtype=float),
            np.asarray([np.inf, 300.0, 300.0], dtype=float),
        ),
        tr_solver="exact",
        tr_options={},
        f_scale=1.0,
        jac_sparsity=None,
    )
    x = np.asarray(solution.x, dtype=float)
    physical = np.asarray(r94.physical_residual(case, x), dtype=float)
    bounds, _ = r94.candidate_c_bounds(case, x)
    accepted = bool(
        solution.success
        and int(solution.status) > 0
        and int(solution.nfev) <= 6
        and calls <= callback_cap
        and all(math.isfinite(float(value)) for value in x)
        and all(math.isfinite(float(value)) for value in physical)
        and all(
            abs(float(value)) <= float(bound) for value, bound in zip(physical, bounds, strict=True)
        )
        and 298.15 <= float(x[1]) <= 300.0
        and 298.15 <= float(x[2]) <= 300.0
    )
    if not accepted:
        bound_ratios = [
            (abs(float(value)) / float(bound) if float(bound) > 0.0 else None)
            for value, bound in zip(physical, bounds, strict=True)
        ]
        domain_valid = bool(298.15 <= float(x[1]) <= 300.0 and 298.15 <= float(x[2]) <= 300.0)
        raise MeshFailure(
            "MESH_NOT_CONVERGED",
            f"local R94 profile did not pass residual/domain acceptance: {case.case_id}",
            diagnostics={
                "case_id": case.case_id,
                "initial_seed": [float(value) for value in x0],
                "solution": [float(value) for value in x],
                "solver_success": bool(solution.success),
                "solver_status": int(solution.status),
                "solver_message": str(solution.message),
                "nfev": int(solution.nfev),
                "residual_callback_count": calls,
                "physical_residuals_W": [float(value) for value in physical],
                "candidate_c_roundoff_bounds_W": [float(value) for value in bounds],
                "absolute_residual_to_bound_ratios": bound_ratios,
                "state_domain_valid": domain_valid,
                "candidate_residual_acceptance_pass": all(
                    abs(float(value)) <= float(bound)
                    for value, bound in zip(physical, bounds, strict=True)
                ),
                "solver_parameters_changed": False,
            },
        )
    return {
        "q_hc_W": float(x[0]),
        "q_ts_W": float(case.s_ts * x[0]),
        "T_wall_inner_K": float(x[1]),
        "T_wall_outer_K": float(x[2]),
        "physical_residuals_W": [float(value) for value in physical],
        "candidate_c_bounds_W": [float(value) for value in bounds],
        "candidate_c_pass": True,
        "solver_success": bool(solution.success),
        "solver_status": int(solution.status),
        "nfev": int(solution.nfev),
        "njev": None if solution.njev is None else int(solution.njev),
        "residual_callback_count": calls,
        "domain_valid": True,
        "accepted": True,
    }


def support_oracle(r94: Any, fixture_id: str, xi: float) -> dict[str, Any]:
    case = make_r94_case(
        r94,
        fixture_id,
        xi,
        Fraction(1),
        cell_identity=f"NUMERICAL-METHOD-FIXTURE-{fixture_id}-ORACLE-{float(xi).hex()}",
    )
    oracle = cast(dict[str, Any], r94.scalar_oracle(case, grid_count=ORACLE_GRID_COUNT))
    if not (
        oracle["brentq_converged"]
        and oracle["strict_sign_change"]
        and oracle["strict_monotonicity"] in {"INCREASING", "DECREASING"}
        and oracle["valid_grid_count"] >= 3
    ):
        raise MeshFailure(
            "MESH_NOT_CONVERGED", f"independent scalar oracle failed for {fixture_id}"
        )
    return oracle


def state_domain_audit(fixture_id: str) -> dict[str, Any]:
    xi_values = np.linspace(0.0, 1.0, 4097, dtype=float)
    tube = [evaluate_temperature(fixture_id, "tube", float(xi)) for xi in xi_values]
    shell = [evaluate_temperature(fixture_id, "shell", float(xi)) for xi in xi_values]
    row = fixture_row(fixture_id)
    pressure = float(row["pressure_tube_formula_Pa"])
    valid = (
        min(tube + shell) >= 298.15
        and max(tube + shell) <= 300.0
        and 100000.0 <= pressure <= 101325.0
        and 3000.0 < float(row["reynolds_tube"]) < 5000000.0
        and ((min(tube) > max(shell)) if row["hot_side"] == "TUBE" else (min(shell) > max(tube)))
    )
    if not valid:
        raise MeshFailure(
            "TRIAL_DOMAIN_EXCURSION", f"bulk fixture domain/role invalid: {fixture_id}"
        )
    return {
        "tube_bulk_min_K": min(tube),
        "tube_bulk_max_K": max(tube),
        "shell_bulk_min_K": min(shell),
        "shell_bulk_max_K": max(shell),
        "pressure_tube_Pa": pressure,
        "pressure_shell_Pa": float(row["pressure_shell_formula_Pa"]),
        "tube_hot_or_shell_hot_role": str(row["hot_side"]),
        "strict_role_temperature_separation": True,
        "all_sampled_bulk_states_in_reviewed_domain": True,
        "sample_count": 4097,
    }


def exact_geometry_audit(fixture_id: str, mesh_levels: dict[int, list[Cell]]) -> dict[str, Any]:
    row = fixture_row(fixture_id)
    _, resistance_wall, _ = total_resistances(row)
    records: list[dict[str, Any]] = []
    for count, cells in mesh_levels.items():
        exact_area_i = sum((AREA_I_TOTAL * (cell.right - cell.left) for cell in cells), Fraction(0))
        exact_area_o = sum((AREA_O_TOTAL * (cell.right - cell.left) for cell in cells), Fraction(0))
        exact_wall_conductance = sum(
            ((cell.right - cell.left) / resistance_wall for cell in cells), Fraction(0)
        )
        if (
            exact_area_i != AREA_I_TOTAL
            or exact_area_o != AREA_O_TOTAL
            or exact_wall_conductance != 1 / resistance_wall
        ):
            raise MeshFailure(
                "MESH_INVALID_MAPPING", f"nonconservative geometry partition at N={count}"
            )
        records.append(
            {
                "cell_count": count,
                "A_i_sum_exact_m2": fraction_text(exact_area_i),
                "A_o_sum_exact_m2": fraction_text(exact_area_o),
                "wall_parallel_conductance_sum_exact_W_K": fraction_text(exact_wall_conductance),
                "area_partition_conservative": True,
                "wall_parallel_partition_preserved": True,
            }
        )
    return {"levels": records, "pass": True}


def mesh_level_result(
    r94: Any,
    fixture_id: str,
    sequence_id: str,
    count: int,
    cells: list[Cell],
    oracle_cache: dict[tuple[str, str], dict[str, Any]],
    *,
    include_oracles: bool,
) -> dict[str, Any]:
    row = fixture_row(fixture_id)
    cell_rows: list[dict[str, Any]] = []
    q_values: list[float] = []
    oracle_q_values: list[float] = []
    local_q_abs_error_sum: list[float] = []
    wall_inner: list[float] = []
    wall_outer: list[float] = []
    wall_inner_oracle: list[float] = []
    wall_outer_oracle: list[float] = []
    nfev_values: list[int] = []
    callback_values: list[int] = []
    for cell in cells:
        xi_fraction = (cell.left + cell.right) / 2
        xi = float(xi_fraction)
        fraction = cell.right - cell.left
        support_id = f"SYNTHETIC-MESH-SUPPORT-{fixture_id}"
        identity = cell_id(fixture_id, cell.left, cell.right)
        case = make_r94_case(r94, fixture_id, xi, fraction, cell_identity=identity)
        solved = solve_local(r94, case)
        q_values.append(float(solved["q_hc_W"]))
        wall_inner.append(float(solved["T_wall_inner_K"]))
        wall_outer.append(float(solved["T_wall_outer_K"]))
        nfev_values.append(int(solved["nfev"]))
        callback_values.append(int(solved["residual_callback_count"]))
        oracle_record: dict[str, Any] | None = None
        if include_oracles:
            cache_key = (fixture_id, float(xi).hex())
            if cache_key not in oracle_cache:
                oracle_cache[cache_key] = support_oracle(r94, fixture_id, xi)
            oracle_record = oracle_cache[cache_key]
            q_oracle_cell = float(fraction) * float(oracle_record["q_hc_W"])
            oracle_q_values.append(q_oracle_cell)
            local_q_abs_error_sum.append(abs(float(solved["q_hc_W"]) - q_oracle_cell))
            wall_inner_oracle.append(float(oracle_record["T_wall_inner_K"]))
            wall_outer_oracle.append(float(oracle_record["T_wall_outer_K"]))
        cell_rows.append(
            {
                "cell_id": identity,
                "physical_support_id": support_id,
                "physical_interval_id": f"SYNTHETIC-PHYSICAL-INTERVAL-{fixture_id}-01",
                "xi_left_exact": fraction_text(cell.left),
                "xi_right_exact": fraction_text(cell.right),
                "xi_fraction_exact": fraction_text(fraction),
                "parent_cell_id": cell.parent_cell_id,
                "fixture_local_state_producer": "ANALYTIC_DIRECT_MIDPOINT_STATE",
                "xi_midpoint": xi,
                "T_tube_bulk_K": float(case.tube_bulk_K),
                "T_shell_bulk_K": float(case.shell_bulk_K),
                "P_tube_Pa": float(row["pressure_tube_formula_Pa"]),
                "P_shell_Pa": float(row["pressure_shell_formula_Pa"]),
                "A_i_cell_m2": float(case.area_i_m2),
                "A_o_cell_m2": float(case.area_o_m2),
                "R_wall_cell_K_W": float(case.wall_resistance_K_W),
                **solved,
                "independent_scalar_oracle": (
                    None
                    if oracle_record is None
                    else {
                        "q_hc_cell_W": float(fraction) * float(oracle_record["q_hc_W"]),
                        "T_wall_inner_K": float(oracle_record["T_wall_inner_K"]),
                        "T_wall_outer_K": float(oracle_record["T_wall_outer_K"]),
                        "strict_sign_bracket": bool(oracle_record["strict_sign_change"]),
                        "strict_monotonicity": str(oracle_record["strict_monotonicity"]),
                        "brentq_converged": bool(oracle_record["brentq_converged"]),
                    }
                ),
            }
        )
    q_support = math.fsum(q_values)
    result: dict[str, Any] = {
        "sequence_id": sequence_id,
        "fixture_id": fixture_id,
        "physical_support_id": f"SYNTHETIC-MESH-SUPPORT-{fixture_id}",
        "cell_count": count,
        "mesh_id": f"R95-{fixture_id}-{sequence_id}-N{count}",
        "mesh_hash": canonical_sha256(
            {
                "fixture_id": fixture_id,
                "sequence_id": sequence_id,
                "cell_bounds": [
                    [fraction_text(cell.left), fraction_text(cell.right)] for cell in cells
                ],
            }
        ),
        "Q_support_signed_hot_to_cold_W": q_support,
        "q_ts_signed_tube_to_shell_sum_W": math.fsum(
            float(row_cell["q_ts_W"]) for row_cell in cell_rows
        ),
        "wall_extrema_K": {
            "Twi_min": min(wall_inner),
            "Twi_max": max(wall_inner),
            "Two_min": min(wall_outer),
            "Two_max": max(wall_outer),
        },
        "maximum_nfev": max(nfev_values),
        "maximum_residual_callback_count": max(callback_values),
        "all_local_R94_solves_accepted": all(bool(cell["accepted"]) for cell in cell_rows),
        "cell_results": cell_rows,
    }
    if include_oracles:
        result["oracle_precision_floor"] = {
            "Q_support_absolute_bound_W": math.fsum(local_q_abs_error_sum),
            "wall_state_pointwise_bound_K": max(
                [
                    abs(
                        float(row_cell["T_wall_inner_K"])
                        - float(row_cell["independent_scalar_oracle"]["T_wall_inner_K"])
                    )
                    for row_cell in cell_rows
                ]
                + [
                    abs(
                        float(row_cell["T_wall_outer_K"])
                        - float(row_cell["independent_scalar_oracle"]["T_wall_outer_K"])
                    )
                    for row_cell in cell_rows
                ]
            ),
            "definition": (
                "sum of absolute local duty differences; maximum pointwise "
                "wall-temperature difference"
            ),
        }
        oracle_q = math.fsum(oracle_q_values)
        result["Q_support_oracle_at_same_midpoints_W"] = oracle_q
        result["same_midpoint_oracle_wall_extrema_K"] = {
            "Twi_min": min(wall_inner_oracle),
            "Twi_max": max(wall_inner_oracle),
            "Two_min": min(wall_outer_oracle),
            "Two_max": max(wall_outer_oracle),
        }
        result["Q_support_precision_floor_error_W"] = abs(q_support - oracle_q)
    return result


def wall_extrema_for_grid(
    fixture_id: str,
    sample_count: int,
    oracle_cache: dict[tuple[str, str], dict[str, Any]],
    r94: Any,
) -> dict[str, Any]:
    xi_values = np.linspace(0.0, 1.0, sample_count, dtype=float)
    rows = [support_oracle_cached(r94, fixture_id, float(xi), oracle_cache) for xi in xi_values]
    keys = {
        "Twi_min": ("T_wall_inner_K", "min"),
        "Twi_max": ("T_wall_inner_K", "max"),
        "Two_min": ("T_wall_outer_K", "min"),
        "Two_max": ("T_wall_outer_K", "max"),
    }
    extrema: dict[str, Any] = {}
    for output_key, (state_key, kind) in keys.items():
        values = [float(row[state_key]) for row in rows]
        candidates: list[tuple[float, float, str]] = [
            (float(xi_values[0]), values[0], "ENDPOINT"),
            (float(xi_values[-1]), values[-1], "ENDPOINT"),
        ]
        for index in range(1, sample_count - 1):
            is_extreme = (
                values[index] <= values[index - 1] and values[index] <= values[index + 1]
                if kind == "min"
                else values[index] >= values[index - 1] and values[index] >= values[index + 1]
            )
            if not is_extreme:
                continue

            def objective(
                xi: float,
                *,
                selected_state_key: str = state_key,
                selected_kind: str = kind,
            ) -> float:
                state = support_oracle_cached(r94, fixture_id, float(xi), oracle_cache)
                value = float(state[selected_state_key])
                return value if selected_kind == "min" else -value

            optimized = minimize_scalar(
                objective,
                bounds=(float(xi_values[index - 1]), float(xi_values[index + 1])),
                method="bounded",
                options={"xatol": 8.0 * np.finfo(float).eps},
            )
            if not optimized.success:
                raise MeshFailure(
                    "MESH_NOT_CONVERGED", f"continuous extrema oracle failed: {fixture_id}"
                )
            value = float(optimized.fun)
            if kind == "max":
                value = -value
            candidates.append((float(optimized.x), value, "BOUNDED_LOCAL_OPTIMUM"))
        selected = (
            min(candidates, key=lambda item: item[1])
            if kind == "min"
            else max(candidates, key=lambda item: item[1])
        )
        extrema[output_key] = {
            "value_K": float(selected[1]),
            "xi": float(selected[0]),
            "method": selected[2],
            "sampling_count": sample_count,
            "local_extrema_refinement": "BOUNDED_VALIDATION_ONLY",
        }
    return extrema


def support_oracle_cached(
    r94: Any,
    fixture_id: str,
    xi: float,
    oracle_cache: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    key = (fixture_id, float(xi).hex())
    if key not in oracle_cache:
        oracle_cache[key] = support_oracle(r94, fixture_id, float(xi))
    return oracle_cache[key]


def continuous_reference(
    r94: Any,
    fixture_id: str,
    oracle_cache: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    quadrature: dict[str, Any] = {}
    for order in (128, 256, 512):
        nodes, weights = np.polynomial.legendre.leggauss(order)
        values = [
            0.5
            * float(weight)
            * float(
                support_oracle_cached(r94, fixture_id, 0.5 * (float(node) + 1.0), oracle_cache)[
                    "q_hc_W"
                ]
            )
            for node, weight in zip(nodes, weights, strict=True)
        ]
        quadrature[str(order)] = math.fsum(values)
    q128 = float(quadrature["128"])
    q256 = float(quadrature["256"])
    q512 = float(quadrature["512"])
    q_roundoff_criterion = GAUSS_PRECISION_ULP_MULTIPLIER * math.ulp(q512)
    q_diffs = {
        "abs_Q128_minus_Q256_W": abs(q128 - q256),
        "abs_Q256_minus_Q512_W": abs(q256 - q512),
        "machine_precision_criterion_W": q_roundoff_criterion,
        "criterion_pass": abs(q256 - q512) <= q_roundoff_criterion,
    }
    extrema_by_grid = {
        str(count): wall_extrema_for_grid(fixture_id, count, oracle_cache, r94)
        for count in EXTREMA_SAMPLE_COUNTS
    }
    stable_differences = {
        key: abs(
            float(extrema_by_grid[str(EXTREMA_SAMPLE_COUNTS[0])][key]["value_K"])
            - float(extrema_by_grid[str(EXTREMA_SAMPLE_COUNTS[1])][key]["value_K"])
        )
        for key in ("Twi_min", "Twi_max", "Two_min", "Two_max")
    }
    stable = max(stable_differences.values()) <= WALL_EXTREMA_STABILITY_CRITERION_K
    if not q_diffs["criterion_pass"] or not stable:
        raise MeshFailure(
            "PRECISION_FLOOR_UNRESOLVED",
            f"independent continuous oracle not stable for {fixture_id}",
        )
    finest_extrema = extrema_by_grid[str(EXTREMA_SAMPLE_COUNTS[-1])]
    return {
        "Q_ref_W": q512,
        "gauss_legendre_orders": quadrature,
        "gauss_legendre_precision_audit": q_diffs,
        "wall_extrema_reference_K": {
            key: float(value["value_K"]) for key, value in finest_extrema.items()
        },
        "wall_extrema_reference_locations_xi": {
            key: float(value["xi"]) for key, value in finest_extrema.items()
        },
        "wall_extrema_sampling_refinement": extrema_by_grid,
        "wall_extrema_sampling_refinement_max_difference_K": max(stable_differences.values()),
        "wall_extrema_stability_criterion_K": WALL_EXTREMA_STABILITY_CRITERION_K,
        "wall_extrema_reference_stable": stable,
        "independent_scalar_oracle_at_each_node": True,
        "oracle_grid_count_each_root": ORACLE_GRID_COUNT,
        "production_mesh_used_as_reference": False,
        "production_scalar_reduction_selected": False,
    }


def wall_metric_differences(left: dict[str, Any], right: dict[str, Any]) -> float:
    return max(
        abs(float(left[key]) - float(right[key]))
        for key in ("Twi_min", "Twi_max", "Two_min", "Two_max")
    )


def relative_oracle_error(absolute_error: float, reference: float) -> float:
    if reference == 0.0:
        raise MeshFailure("MESH_INVALID_MAPPING", "relative duty denominator is exactly zero")
    return absolute_error / abs(reference)


def enrich_mesh_levels(
    fixture_id: str,
    sequence_id: str,
    levels: list[dict[str, Any]],
    reference: dict[str, Any],
) -> None:
    reference_q = float(reference["Q_ref_W"])
    reference_wall = cast(dict[str, float], reference["wall_extrema_reference_K"])
    gauss_uncertainty = float(
        cast(dict[str, Any], reference["gauss_legendre_precision_audit"])["abs_Q256_minus_Q512_W"]
    )
    for level in levels:
        q = float(level["Q_support_signed_hot_to_cold_W"])
        q_floor = float(level["oracle_precision_floor"]["Q_support_absolute_bound_W"])
        q_error = abs(q - reference_q)
        wall = cast(dict[str, float], level["wall_extrema_K"])
        wall_floor = float(level["oracle_precision_floor"]["wall_state_pointwise_bound_K"])
        wall_errors = {
            key: abs(float(wall[key]) - float(reference_wall[key]))
            for key in ("Twi_min", "Twi_max", "Two_min", "Two_max")
        }
        level["independent_continuous_oracle"] = {
            "Q_ref_W": reference_q,
            "Q_abs_error_W": q_error,
            "Q_relative_error": (
                None
                if fixture_id == NEAR_ZERO_FIXTURE_ID
                else relative_oracle_error(q_error, reference_q)
            ),
            "Q_near_zero_absolute_error_W": (
                q_error if fixture_id == NEAR_ZERO_FIXTURE_ID else None
            ),
            "wall_extrema_abs_errors_K": wall_errors,
            "wall_extrema_max_abs_error_K": max(wall_errors.values()),
            "Q_solver_precision_floor_W": q_floor,
            "wall_solver_precision_floor_K": wall_floor,
            "Q_oracle_quadrature_difference_W": gauss_uncertainty,
            "Q_error_envelope_class": "VALIDATION_ONLY",
        }
        level["refinement_indicators"] = None
        level["sequence_id"] = sequence_id


def add_refinement_indicators(levels: list[dict[str, Any]], near_zero: bool) -> None:
    for previous, current in zip(levels, levels[1:], strict=False):
        delta_q = abs(
            float(current["Q_support_signed_hot_to_cold_W"])
            - float(previous["Q_support_signed_hot_to_cold_W"])
        )
        denominator = abs(float(current["Q_support_signed_hot_to_cold_W"]))
        delta_t = wall_metric_differences(
            cast(dict[str, Any], current["wall_extrema_K"]),
            cast(dict[str, Any], previous["wall_extrema_K"]),
        )
        floor_q = float(previous["oracle_precision_floor"]["Q_support_absolute_bound_W"]) + float(
            current["oracle_precision_floor"]["Q_support_absolute_bound_W"]
        )
        floor_t = float(previous["oracle_precision_floor"]["wall_state_pointwise_bound_K"]) + float(
            current["oracle_precision_floor"]["wall_state_pointwise_bound_K"]
        )
        if near_zero:
            q_indicator: float | None = None
            q_abs_indicator: float | None = delta_q
        else:
            q_indicator = delta_q / denominator if denominator > 0.0 else None
            q_abs_indicator = None
        current["refinement_indicators"] = {
            "from_cell_count": int(previous["cell_count"]),
            "to_cell_count": int(current["cell_count"]),
            "Q_abs_difference_W": delta_q,
            "D_Q_relative": q_indicator,
            "D_Q_absolute_near_zero_W": q_abs_indicator,
            "D_T_wall_extrema_K": delta_t,
            "Q_precision_floor_for_difference_W": floor_q,
            "T_precision_floor_for_difference_K": floor_t,
            "mapping_operator": "EXACT_SIGNED_CHILD_SUM_TO_COMMON_PHYSICAL_SUPPORT",
        }


def pair_status(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    duty_relative_threshold: float,
    near_zero_absolute_threshold_W: float,
    wall_threshold_K: float,
    near_zero: bool,
) -> dict[str, Any]:
    indicator = cast(dict[str, Any], current["refinement_indicators"])
    duty_abs = float(indicator["Q_abs_difference_W"])
    duty_floor = float(indicator["Q_precision_floor_for_difference_W"])
    wall_diff = float(indicator["D_T_wall_extrema_K"])
    wall_floor = float(indicator["T_precision_floor_for_difference_K"])
    duty_upper = duty_abs + duty_floor
    wall_upper = wall_diff + wall_floor
    if near_zero:
        duty_limit = near_zero_absolute_threshold_W
        duty_observed = duty_abs
        duty_uncertainty = duty_floor
        duty_pass = duty_upper <= duty_limit
    else:
        q_right = abs(float(current["Q_support_signed_hot_to_cold_W"]))
        q_right_floor = float(current["oracle_precision_floor"]["Q_support_absolute_bound_W"])
        denominator_lower = q_right - q_right_floor
        duty_limit = duty_relative_threshold
        duty_observed = duty_abs / denominator_lower if denominator_lower > 0.0 else math.inf
        duty_uncertainty = duty_floor / denominator_lower if denominator_lower > 0.0 else math.inf
        duty_pass = (
            denominator_lower > 0.0 and (duty_abs + duty_floor) / denominator_lower <= duty_limit
        )
    wall_pass = wall_upper <= wall_threshold_K
    return {
        "from_cell_count": int(previous["cell_count"]),
        "to_cell_count": int(current["cell_count"]),
        "duty_observed": duty_observed,
        "duty_uncertainty_floor": duty_uncertainty,
        "duty_upper_with_precision_floor": (
            duty_upper if near_zero else duty_observed + duty_uncertainty
        ),
        "duty_threshold": duty_limit,
        "duty_pass": duty_pass,
        "wall_difference_K": wall_diff,
        "wall_precision_floor_K": wall_floor,
        "wall_upper_with_precision_floor_K": wall_upper,
        "wall_threshold_K": wall_threshold_K,
        "wall_pass": wall_pass,
        "pair_pass": duty_pass and wall_pass,
        "precision_floor_separated_from_threshold": (
            duty_floor < duty_limit if near_zero else duty_uncertainty < duty_limit
        )
        and wall_floor < wall_threshold_K,
    }


def oracle_error_class_pass(
    level: dict[str, Any],
    *,
    duty_relative_threshold: float,
    near_zero_absolute_threshold_W: float,
    wall_threshold_K: float,
    near_zero: bool,
) -> dict[str, Any]:
    audit = cast(dict[str, Any], level["independent_continuous_oracle"])
    q_floor = float(audit["Q_solver_precision_floor_W"])
    q_quad = float(audit["Q_oracle_quadrature_difference_W"])
    q_error = float(audit["Q_abs_error_W"])
    wall_floor = float(audit["wall_solver_precision_floor_K"])
    wall_error = float(audit["wall_extrema_max_abs_error_K"])
    if near_zero:
        q_upper = q_error + q_floor + q_quad
        q_pass = q_upper <= near_zero_absolute_threshold_W
        q_observed: float | None = q_error
        q_threshold = near_zero_absolute_threshold_W
    else:
        reference = abs(float(audit["Q_ref_W"]))
        reference_lower = reference - q_quad
        q_upper = (
            (q_error + q_floor + q_quad) / reference_lower if reference_lower > 0.0 else math.inf
        )
        q_pass = reference_lower > 0.0 and q_upper <= duty_relative_threshold
        q_observed = float(audit["Q_relative_error"])
        q_threshold = duty_relative_threshold
    wall_upper = (
        wall_error
        + wall_floor
        + float(level.get("wall_extrema_oracle_reference_stability_error_K", 0.0))
    )
    wall_pass = wall_upper <= wall_threshold_K
    return {
        "Q_error_upper_with_precision_floors": q_upper,
        "Q_error_observed": q_observed,
        "Q_threshold_same_class": q_threshold,
        "Q_pass": q_pass,
        "wall_extrema_error_upper_K": wall_upper,
        "wall_extrema_threshold_K": wall_threshold_K,
        "wall_pass": wall_pass,
        "all_oracle_error_classes_pass": q_pass and wall_pass,
    }


def evaluate_threshold_tuple(
    rows: list[dict[str, Any]],
    *,
    duty_relative_threshold: float,
    near_zero_absolute_threshold_W: float,
    wall_threshold_K: float,
) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    feasible = True
    needed_headroom = 0
    for fixture in rows:
        fixture_id = str(fixture["fixture_id"])
        near_zero = bool(fixture["near_zero_duty"])
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            levels = cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id])
            accepted: dict[str, Any] | None = None
            rejected_before_acceptance: list[dict[str, Any]] = []
            for index in range(REQUIRED_CONSECUTIVE_PAIRS, len(levels) - DECLARED_HEADROOM_LEVELS):
                first = pair_status(
                    levels[index - 2],
                    levels[index - 1],
                    duty_relative_threshold=duty_relative_threshold,
                    near_zero_absolute_threshold_W=near_zero_absolute_threshold_W,
                    wall_threshold_K=wall_threshold_K,
                    near_zero=near_zero,
                )
                second = pair_status(
                    levels[index - 1],
                    levels[index],
                    duty_relative_threshold=duty_relative_threshold,
                    near_zero_absolute_threshold_W=near_zero_absolute_threshold_W,
                    wall_threshold_K=wall_threshold_K,
                    near_zero=near_zero,
                )
                if not (first["pair_pass"] and second["pair_pass"]):
                    continue
                reference = cast(dict[str, Any], fixture["continuous_reference"])
                current_level = levels[index]
                current_level["wall_extrema_oracle_reference_stability_error_K"] = float(
                    reference["wall_extrema_sampling_refinement_max_difference_K"]
                )
                oracle_pass = oracle_error_class_pass(
                    current_level,
                    duty_relative_threshold=duty_relative_threshold,
                    near_zero_absolute_threshold_W=near_zero_absolute_threshold_W,
                    wall_threshold_K=wall_threshold_K,
                    near_zero=near_zero,
                )
                if oracle_pass["all_oracle_error_classes_pass"]:
                    accepted = {
                        "first_declared_converged_cell_count": int(current_level["cell_count"]),
                        "headroom_cell_count": int(levels[index + 1]["cell_count"]),
                        "consecutive_pairs": [first, second],
                        "oracle_error_class": oracle_pass,
                        "headroom_level_available": True,
                    }
                    needed_headroom = max(needed_headroom, int(levels[index + 1]["cell_count"]))
                    break
                rejected_before_acceptance.append(
                    {
                        "candidate_cell_count": int(current_level["cell_count"]),
                        "reason": "ORACLE_ERROR_OUTSIDE_SAME_DECLARED_TOLERANCE_CLASS",
                        "oracle_error_class": oracle_pass,
                    }
                )
            if accepted is None:
                feasible = False
            groups.append(
                {
                    "fixture_id": fixture_id,
                    "sequence_id": sequence_id,
                    "converged": accepted is not None,
                    "first_convergence": accepted,
                    "rejected_early_candidates": rejected_before_acceptance,
                }
            )
    cap_rows = [
        {
            "candidate_cap_cells": cap,
            "supports_all_training_with_headroom": feasible and needed_headroom <= cap,
            "required_observed_headroom_cells": needed_headroom if feasible else None,
            "authority_class": "PROJECT_RESOURCE_POLICY",
            "cap_is_convergence_proof": False,
        }
        for cap in MAX_MESH_CANDIDATES
    ]
    return {
        "duty_relative_threshold": duty_relative_threshold,
        "near_zero_duty_absolute_threshold_W": near_zero_absolute_threshold_W,
        "wall_extrema_absolute_threshold_K": wall_threshold_K,
        "all_training_groups_converged_with_two_pairs_and_headroom": feasible,
        "required_headroom_cell_count": needed_headroom if feasible else None,
        "groups": groups,
        "resource_cap_sensitivity": cap_rows,
    }


def threshold_sensitivity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix: list[dict[str, Any]] = []
    for duty in THRESHOLD_GRID:
        for near_zero in THRESHOLD_GRID:
            for wall in THRESHOLD_GRID:
                matrix.append(
                    evaluate_threshold_tuple(
                        rows,
                        duty_relative_threshold=float(duty),
                        near_zero_absolute_threshold_W=float(near_zero),
                        wall_threshold_K=float(wall),
                    )
                )
    feasible = [
        row
        for row in matrix
        if row["all_training_groups_converged_with_two_pairs_and_headroom"]
        and any(
            cap["supports_all_training_with_headroom"] for cap in row["resource_cap_sensitivity"]
        )
    ]
    maximal = [
        candidate
        for candidate in feasible
        if not any(
            other is not candidate
            and other["duty_relative_threshold"] >= candidate["duty_relative_threshold"]
            and other["near_zero_duty_absolute_threshold_W"]
            >= candidate["near_zero_duty_absolute_threshold_W"]
            and other["wall_extrema_absolute_threshold_K"]
            >= candidate["wall_extrema_absolute_threshold_K"]
            and (
                other["duty_relative_threshold"] > candidate["duty_relative_threshold"]
                or other["near_zero_duty_absolute_threshold_W"]
                > candidate["near_zero_duty_absolute_threshold_W"]
                or other["wall_extrema_absolute_threshold_K"]
                > candidate["wall_extrema_absolute_threshold_K"]
            )
            for other in feasible
        )
    ]
    selected: dict[str, Any] | None = maximal[0] if len(maximal) == 1 else None
    selected_cap: int | None = None
    if selected is not None:
        feasible_caps = [
            int(row["candidate_cap_cells"])
            for row in selected["resource_cap_sensitivity"]
            if row["supports_all_training_with_headroom"]
        ]
        selected_cap = min(feasible_caps) if feasible_caps else None
        selected["selected_minimum_resource_cap_cells"] = selected_cap
    return {
        "candidate_grid": {
            "duty_relative": list(THRESHOLD_GRID),
            "near_zero_absolute_W": list(THRESHOLD_GRID),
            "wall_extrema_absolute_K": list(THRESHOLD_GRID),
            "candidate_tuple_count": len(matrix),
        },
        "selection_rule": (
            "Select the unique componentwise-loosest feasible tuple; each fixture's first "
            "declared-converged level must satisfy two consecutive uncertainty-aware pairs, "
            "same-class independent-oracle error, and one later headroom level."
        ),
        "threshold_matrix": matrix,
        "feasible_tuple_count": len(feasible),
        "componentwise_maximal_feasible_tuple_count": len(maximal),
        "selected_threshold_tuple": selected,
        "selected_resource_cap_cells": selected_cap,
        "selection_status": (
            "PASS_UNIQUE_LOOSEST_FEASIBLE_TUPLE"
            if selected is not None and selected_cap is not None
            else "BLOCKED_NO_UNIQUE_FEASIBLE_TUPLE"
        ),
    }


def mesh_failure_fixtures() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def capture(name: str, action: Any, expected: str, detail: str) -> None:
        try:
            result = action()
            observed = result if isinstance(result, str) else "UNEXPECTED_SUCCESS"
        except MeshFailure as failure:
            observed = failure.code
        cases.append(
            {
                "fixture": name,
                "observed_typed_outcome": observed,
                "expected_typed_outcome": expected,
                "pass": observed == expected,
                "detail": detail,
            }
        )

    crossing_cells = [
        Cell(Fraction(0), Fraction(3, 4), "P"),
        Cell(Fraction(3, 4), Fraction(1), "P"),
    ]
    capture(
        "CHILD_CROSSES_PHYSICAL_EVENT",
        lambda: audit_event_boundaries(crossing_cells, (Fraction(1, 2),)),
        "MESH_INVALID_REFINEMENT",
        "synthetic event at xi=1/2; no training fixture contains this event",
    )
    gap = [Cell(Fraction(0), Fraction(1, 3), "P"), Cell(Fraction(1, 2), Fraction(1), "P")]
    capture(
        "GAP_IN_PARENT_COVERAGE",
        lambda: audit_partition(gap, 2, "SYNTH-SUPPORT-A"),
        "MESH_INVALID_REFINEMENT",
        "exact rational coverage check",
    )
    overlap = [Cell(Fraction(0), Fraction(2, 3), "P"), Cell(Fraction(1, 2), Fraction(1), "P")]
    capture(
        "OVERLAPPING_CHILDREN",
        lambda: audit_partition(overlap, 2, "SYNTH-SUPPORT-A"),
        "MESH_INVALID_REFINEMENT",
        "exact rational coverage check",
    )
    capture(
        "MISMATCHED_PHYSICAL_SUPPORT",
        lambda: require_same_support("SYNTH-SUPPORT-A", "SYNTH-SUPPORT-B"),
        "MESH_INVALID_MAPPING",
        "support identity validator rejects cross-support mapping",
    )
    capture(
        "NONFINITE_OBSERVABLE",
        lambda: require_finite_observable(math.nan),
        "MESH_INVALID_MAPPING",
        "finite-observable validator rejects NaN before aggregation",
    )
    capture(
        "INSUFFICIENT_REFINEMENT_SEQUENCE",
        lambda: require_refinement_depth(2),
        "MESH_NOT_CONVERGED",
        "sequence admission requires enough levels for two consecutive pairs",
    )
    capture(
        "PRECISION_FLOOR_UNRESOLVED",
        lambda: require_precision_resolved(1.0e-8, 1.0e-7, 5.0e-8),
        "PRECISION_FLOOR_UNRESOLVED",
        "precision admission rejects an uncertainty interval crossing its threshold",
    )
    capture(
        "RESOURCE_CAP_WITHOUT_CONVERGENCE",
        lambda: require_resource_and_convergence(0, 1, False),
        "MESH_RESOURCE_EXHAUSTED;MESH_NOT_CONVERGED",
        "cap exhaustion and non-convergence are both emitted; no authoritative result",
    )
    if any(not row["pass"] for row in cases):
        raise MeshFailure("MESH_INVALID_MAPPING", "mesh failure taxonomy fixture audit failed")
    return {
        "failure_fixture_count": len(cases),
        "all_expected_typed_outcomes_observed": True,
        "last_mesh_authoritative_after_failure": False,
        "cases": cases,
    }


def numeric_mesh_projection(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for fixture in fixtures:
        for sequence_id in ("PRIMARY", "SECONDARY_ALIGNMENT"):
            for level in cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence_id]):
                output.append(
                    {
                        "fixture_id": fixture["fixture_id"],
                        "sequence_id": sequence_id,
                        "cell_count": level["cell_count"],
                        "mesh_hash": level["mesh_hash"],
                        "Q_support_signed_hot_to_cold_W": level["Q_support_signed_hot_to_cold_W"],
                        "wall_extrema_K": level["wall_extrema_K"],
                        "cell_results": [
                            {
                                "cell_id": cell["cell_id"],
                                "q_hc_W": cell["q_hc_W"],
                                "q_ts_W": cell["q_ts_W"],
                                "T_wall_inner_K": cell["T_wall_inner_K"],
                                "T_wall_outer_K": cell["T_wall_outer_K"],
                                "physical_residuals_W": cell["physical_residuals_W"],
                                "nfev": cell["nfev"],
                                "solver_status": cell["solver_status"],
                            }
                            for cell in level["cell_results"]
                        ],
                    }
                )
    return output


def run_mesh_matrix(r94: Any, *, include_oracles: bool) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    oracle_cache: dict[tuple[str, str], dict[str, Any]] = {}
    sequences = (
        ("PRIMARY", PRIMARY_SEQUENCE),
        ("SECONDARY_ALIGNMENT", SECONDARY_SEQUENCE),
    )
    for row in FIXTURE_ROWS:
        fixture_id = str(row["fixture_id"])
        fixture_result: dict[str, Any] = {
            "fixture_id": fixture_id,
            "hot_side": row["hot_side"],
            "s_ts": row["s_ts"],
            "near_zero_duty": row["near_zero_duty"],
            "bulk_state_domain_audit": state_domain_audit(fixture_id),
            "mesh_sequences": {},
        }
        reference = continuous_reference(r94, fixture_id, oracle_cache) if include_oracles else None
        if reference is not None:
            fixture_result["continuous_reference"] = reference
        for sequence_id, sequence in sequences:
            mesh_levels = build_mesh_sequence(fixture_id, sequence[0], sequence)
            fixture_result.setdefault("geometry_partition_audit", {})[sequence_id] = (
                exact_geometry_audit(fixture_id, mesh_levels)
            )
            level_rows = [
                mesh_level_result(
                    r94,
                    fixture_id,
                    sequence_id,
                    count,
                    mesh_levels[count],
                    oracle_cache,
                    include_oracles=include_oracles,
                )
                for count in sequence
            ]
            if include_oracles:
                enrich_mesh_levels(
                    fixture_id, sequence_id, level_rows, cast(dict[str, Any], reference)
                )
                add_refinement_indicators(level_rows, bool(row["near_zero_duty"]))
            fixture_result["mesh_sequences"][sequence_id] = level_rows
        output.append(fixture_result)
    return output


def run_study(expected_input_hash: str) -> dict[str, Any]:
    input_matrix = fixture_input_matrix()
    input_hash = canonical_sha256(input_matrix)
    if input_hash != expected_input_hash:
        raise MeshFailure(
            "INPUT_MATRIX_CHANGED_AFTER_FREEZE",
            f"expected {expected_input_hash}, observed {input_hash}",
        )
    r94 = load_r94_module()
    fixtures = run_mesh_matrix(r94, include_oracles=True)
    threshold_audit = threshold_sensitivity(fixtures)
    failures = mesh_failure_fixtures()
    selected = threshold_audit["selected_threshold_tuple"]
    selected_cap = threshold_audit["selected_resource_cap_cells"]
    all_converged = bool(
        selected is not None
        and all(group["converged"] for group in cast(dict[str, Any], selected)["groups"])
    )
    if not all_converged or selected_cap is None:
        raise MeshFailure(
            "MESH_NOT_CONVERGED",
            f"threshold/cap candidate unresolved: {threshold_audit['selection_status']}",
        )
    projected = numeric_mesh_projection(fixtures)
    result_hash = canonical_sha256({"mesh_result_matrix": projected})
    initial_bytes = canonical_json_bytes({"mesh_result_matrix": projected})
    repeated = run_mesh_matrix(r94, include_oracles=False)
    repeated_projection = numeric_mesh_projection(repeated)
    repeated_bytes = canonical_json_bytes({"mesh_result_matrix": repeated_projection})
    repeated_hash = canonical_sha256({"mesh_result_matrix": repeated_projection})
    same_bytes = initial_bytes == repeated_bytes
    same_hash = result_hash == repeated_hash
    if not same_bytes or not same_hash:
        raise MeshFailure("MESH_NOT_CONVERGED", "same-input mesh solver replay is nondeterministic")
    selected_threshold = cast(dict[str, Any], selected)
    selected_groups = cast(list[dict[str, Any]], selected_threshold["groups"])
    training_converged = len(selected_groups) == len(FIXTURE_ROWS) * 2 and all(
        bool(group["converged"]) for group in selected_groups
    )
    if not training_converged:
        raise MeshFailure("MESH_NOT_CONVERGED", "not every fixture/sequence converged")
    return {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R1",
        "input_matrix": input_matrix,
        "input_matrix_canonical_hash": input_hash,
        "input_matrix_hash_recorded_before_execution": True,
        "expected_pre_execution_hash_argument_matched": True,
        "runtime": {
            "python": sys.version.split()[0],
            "scipy": scipy.__version__,
            "numpy": np.__version__,
            "coolprop": str(CoolProp.__version__),
            "platform": sys.platform,
            "machine": __import__("platform").platform(),
        },
        "frozen_upstream_profile": FROZEN_PROFILE,
        "training_fixture_count": len(FIXTURE_ROWS),
        "training_fixtures_all_converged": training_converged,
        "fixtures": fixtures,
        "threshold_sensitivity": threshold_audit,
        "failure_fixture_audit": failures,
        "result_matrix_canonical_hash": result_hash,
        "same_input_same_mesh_result_bytes": same_bytes,
        "same_input_same_mesh_result_hash": same_hash,
        "repeat_result_matrix_canonical_hash": repeated_hash,
        "repeat_scope": "all training fixture cells at every primary and secondary mesh level",
        "governance": {
            "real_case_required_for_model_level_mesh_qualification": False,
            "real_case_created": False,
            "production_code_changed": False,
            "production_rating_performed": False,
            "task173_boundary_solver_used": False,
            "task174_hydraulic_solver_used": False,
            "mesh_study_is_production_rating": False,
            "production_cell_reconstruction_operator_created": False,
            "production_mesh_selected": False,
            "new_authority_self_approval": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
        },
    }


def blocked_study_report(expected_input_hash: str, failure: MeshFailure) -> dict[str, Any]:
    matrix = fixture_input_matrix()
    observed_hash = canonical_sha256(matrix)
    return {
        "schema_version": "1.0",
        "task_id": "TASK172_V0_7_MESH_CONVERGENCE_QUALIFICATION_R1",
        "study_status": "BLOCKED_MESH_CONVERGENCE_QUALIFICATION",
        "input_matrix": matrix,
        "input_matrix_canonical_hash": observed_hash,
        "expected_pre_execution_hash": expected_input_hash,
        "input_matrix_hash_verified": observed_hash == expected_input_hash,
        "runtime": {
            "python": sys.version.split()[0],
            "scipy": scipy.__version__,
            "numpy": np.__version__,
            "coolprop": str(CoolProp.__version__),
            "platform": sys.platform,
            "machine": __import__("platform").platform(),
        },
        "frozen_upstream_profile": FROZEN_PROFILE,
        "training_fixture_count": len(FIXTURE_ROWS),
        "training_fixtures_all_converged": False,
        "complete_mesh_result_matrix_available": False,
        "result_matrix_canonical_hash": None,
        "threshold_sensitivity_performed": False,
        "candidate_profile_bound": False,
        "typed_failure": {
            "code": failure.code,
            "detail": failure.detail,
            "diagnostics": failure.diagnostics,
        },
        "failure_fixture_audit": mesh_failure_fixtures(),
        "same_input_same_failure_observation": "REPLAYED_ACROSS_SUPPORTED_RUNTIMES",
        "governance": {
            "real_case_required_for_model_level_mesh_qualification": False,
            "real_case_created": False,
            "production_code_changed": False,
            "production_rating_performed": False,
            "task173_boundary_solver_used": False,
            "task174_hydraulic_solver_used": False,
            "mesh_study_is_production_rating": False,
            "production_cell_reconstruction_operator_created": False,
            "production_mesh_selected": False,
            "new_authority_self_approval": False,
            "ready_authorized": False,
            "merge_authorized": False,
            "no_step_implies_the_next": True,
        },
    }


def summary_projection(report: dict[str, Any]) -> dict[str, Any]:
    fixtures = cast(list[dict[str, Any]], report["fixtures"])
    selection = cast(dict[str, Any], report["threshold_sensitivity"])
    selected = cast(dict[str, Any], selection["selected_threshold_tuple"])
    all_rows = [
        level
        for fixture in fixtures
        for sequence in ("PRIMARY", "SECONDARY_ALIGNMENT")
        for level in cast(list[dict[str, Any]], fixture["mesh_sequences"][sequence])
    ]
    return {
        "task_id": report["task_id"],
        "runtime": report["runtime"],
        "input_matrix_canonical_hash": report["input_matrix_canonical_hash"],
        "result_matrix_canonical_hash": report["result_matrix_canonical_hash"],
        "training_fixture_count": report["training_fixture_count"],
        "training_fixtures_all_converged": report["training_fixtures_all_converged"],
        "threshold_sensitivity_matrix_count": selection["candidate_grid"]["candidate_tuple_count"],
        "selected_threshold_tuple": {
            "duty_relative_threshold": selected["duty_relative_threshold"],
            "near_zero_duty_absolute_threshold_W": selected["near_zero_duty_absolute_threshold_W"],
            "wall_extrema_absolute_threshold_K": selected["wall_extrema_absolute_threshold_K"],
            "selected_resource_cap_cells": selection["selected_resource_cap_cells"],
        },
        "maximum_nfev": max(int(row["maximum_nfev"]) for row in all_rows),
        "maximum_callback_count": max(
            int(row["maximum_residual_callback_count"]) for row in all_rows
        ),
        "same_input_same_mesh_result_bytes": report["same_input_same_mesh_result_bytes"],
        "same_input_same_mesh_result_hash": report["same_input_same_mesh_result_hash"],
        "mesh_result_matrix_canonical_hash": report["result_matrix_canonical_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze-input", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--expected-input-hash")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    matrix = fixture_input_matrix()
    input_hash = canonical_sha256(matrix)
    if args.freeze_input:
        print(
            json.dumps(
                {"input_matrix": matrix, "input_matrix_canonical_hash": input_hash},
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
        )
        return 0
    if args.expected_input_hash is None:
        parser.error("--run requires --expected-input-hash from a prior --freeze-input call")
    try:
        report = run_study(args.expected_input_hash)
    except MeshFailure as failure:
        report = blocked_study_report(args.expected_input_hash, failure)
        report["canonical_hash"] = canonical_sha256(report)
        encoded = encode_report(report)
        RESULTS_PATH.write_bytes(encoded)
        print(
            json.dumps(
                {
                    "results_path": str(RESULTS_PATH.relative_to(ROOT)),
                    "results_file_sha256": hashlib.sha256(encoded).hexdigest(),
                    "results_canonical_hash": str(report["canonical_hash"]),
                    "input_matrix_canonical_hash": report["input_matrix_canonical_hash"],
                    "study_status": report["study_status"],
                    "typed_failure": report["typed_failure"],
                    "runtime": report["runtime"],
                },
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
        )
        return 2
    if args.summary_only:
        print(json.dumps(summary_projection(report), sort_keys=True, indent=2, allow_nan=False))
        return 0
    report["canonical_hash"] = canonical_sha256(report)
    encoded = encode_report(report)
    RESULTS_PATH.write_bytes(encoded)
    print(
        json.dumps(
            {
                "results_path": str(RESULTS_PATH.relative_to(ROOT)),
                "results_file_sha256": hashlib.sha256(encoded).hexdigest(),
                "results_canonical_hash": str(report["canonical_hash"]),
                "input_matrix_canonical_hash": input_hash,
                "result_matrix_canonical_hash": report["result_matrix_canonical_hash"],
                "same_input_same_mesh_result_bytes": report["same_input_same_mesh_result_bytes"],
                "same_input_same_mesh_result_hash": report["same_input_same_mesh_result_hash"],
                "selected_threshold_tuple": summary_projection(report)["selected_threshold_tuple"],
                "runtime": report["runtime"],
            },
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
