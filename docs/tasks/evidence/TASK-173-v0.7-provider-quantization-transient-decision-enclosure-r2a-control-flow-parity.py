"""Mechanically verify R2A qualification delegates outer control flow to production."""

from __future__ import annotations

import ast
import runpy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as rating

ROOT = Path.cwd()
SERVICE_PATH = ROOT / "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py"
QUALIFICATION_PATH = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a-qualification.py"
)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"FUNCTION_NOT_UNIQUE:{name}:{len(matches)}")
    return matches[0]


def _runtime_control_flow_parity() -> dict[str, Any]:
    service_tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
    qualification_tree = ast.parse(QUALIFICATION_PATH.read_text(encoding="utf-8"))
    production_delegate = _function(service_tree, "_solve_outer_boundary")
    shared_helper = _function(service_tree, "_solve_outer_boundary_from_trial")
    qualification_case = _function(qualification_tree, "_qualify_case")
    production_calls = [
        node
        for node in ast.walk(production_delegate)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_solve_outer_boundary_from_trial"
    ]
    qualification_calls = [
        node
        for node in ast.walk(qualification_case)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_solve_outer_boundary_from_trial"
    ]
    loops = [node for node in ast.walk(qualification_tree) if isinstance(node, ast.While)]
    required_runtime_tokens = {
        "MAX_OUTER_BISECTION_ITERATIONS",
        "_terminal_tolerance_pass",
        "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
        "OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
        "BLOCKED_OUTER_BOUNDARY_RESOURCE_EXHAUSTION",
        "BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID",
        "BLOCKED_VALID_TRAJECTORY_NEGATIVE_RESIDUAL",
    }
    helper_names = {node.id for node in ast.walk(shared_helper) if isinstance(node, ast.Name)}
    helper_names.update(
        node.value
        for node in ast.walk(shared_helper)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    qualification_constants = {
        node.id for node in ast.walk(qualification_tree) if isinstance(node, ast.Name)
    }
    if len(production_calls) != 1 or len(qualification_calls) != 1:
        raise AssertionError("SHARED_OUTER_HELPER_CALL_MISSING_OR_DUPLICATED")
    if loops:
        raise AssertionError("QUALIFICATION_CONTAINS_INDEPENDENT_WHILE_LOOP")
    if not required_runtime_tokens.issubset(helper_names):
        missing = required_runtime_tokens - helper_names
        raise AssertionError(f"PRODUCTION_HELPER_BRANCHES_MISSING:{missing}")
    if "MAX_OUTER_BISECTION_ITERATIONS" in qualification_constants:
        raise AssertionError("QUALIFICATION_RECONSTRUCTS_OUTER_RESOURCE_LOOP")
    return {
        "production_delegate_calls_shared_helper": True,
        "qualification_calls_shared_helper": True,
        "qualification_independent_while_loop_count": 0,
        "production_failure_branches_bound": sorted(required_runtime_tokens),
    }


def _midpoint_precision_straddle_fails_closed() -> None:
    qualification = runpy.run_path(str(QUALIFICATION_PATH), run_name="task173_r2a_parity_test")

    def run(residual_k: str) -> Any:
        return SimpleNamespace(
            observables=SimpleNamespace(
                terminal_boundary_residual_k=Decimal(residual_k),
                terminal_boundary_residual_j_kg=Decimal("0.0001"),
            ),
            faces_shell=(SimpleNamespace(property_snapshot=SimpleNamespace(cp_j_kg_k="4181.0")),),
        )

    left_run = run("2e-8")
    right_run = run("1.00000000001e-8")
    left = {
        "classification": "VALID_TRAJECTORY",
        "mesh_run": left_run,
        "terminal_tolerance_pass": rating._terminal_tolerance_pass(left_run),
    }
    right = {
        "classification": "VALID_TRAJECTORY",
        "mesh_run": right_run,
        "terminal_tolerance_pass": rating._terminal_tolerance_pass(right_run),
    }
    if (
        left["terminal_tolerance_pass"] is not False
        or right["terminal_tolerance_pass"] is not False
    ):
        raise AssertionError("MIDPOINT_NEGATIVE_CONTROL_TERMINAL_PRECONDITION")
    try:
        qualification["_check_branch_invariance"](left, right)
    except rating._Stage3Failure as exc:
        if exc.code != "BLOCKED_TRANSIENT_OUTER_PRECISION_FLOOR_DECISION_QUANTIZATION_STRADDLE":
            raise AssertionError(f"WRONG_MIDPOINT_STRADDLE_FAILURE:{exc.code}") from exc
    else:
        raise AssertionError("MIDPOINT_PRECISION_FLOOR_STRADDLE_ACCEPTED")


def main() -> None:
    parity = _runtime_control_flow_parity()
    _midpoint_precision_straddle_fails_closed()
    print("QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_SOURCE=SHARED_PRODUCTION_HELPER")
    print("QUALIFICATION_OUTER_SOLVER_CONTROL_FLOW_PARITY=PASS")
    print("MIDPOINT_COLLAPSE_STRADDLE_NEGATIVE_TEST=PASS")
    print(f"CONTROL_FLOW_AUDIT={parity}")


if __name__ == "__main__":
    main()
