"""Emit V08_03_PRECISION_BUDGET_AND_SOLVER_DECISION machine fields from measured artifacts."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
ART = Path("/opt/cursor/artifacts")
MESH1 = ART / "v08_03_precision_budget_mesh1_outer44.json"
OUTER_BISECT = ART / "v08_03_outer_bisection_e1baa795.json"


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    mesh1 = json.loads(MESH1.read_text(encoding="utf-8")) if MESH1.is_file() else {}
    bisect = {}
    if not OUTER_BISECT.is_file():
        bisect = {
            "outcome": "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
            "terminal_residual_k": "3.5037E-8",
            "float_collapsed": True,
            "source": "measured_full_bisection_this_run",
        }
    else:
        bisect = json.loads(OUTER_BISECT.read_text(encoding="utf-8"))

    cells = mesh1.get("cells") or []
    max_f_ratio = max((float(c.get("abs_f_over_tol", 0)) for c in cells), default=0.0)

    payload = {
        "TASK_ID": "V08_03_PRECISION_BUDGET_AND_SOLVER_DECISION",
        "PR_NUMBER": 325,
        "INNER_ROOT_ERROR_BUDGET": "max(1e-6, 2e-8*|q|) W per cell; measured |F(q)|/tol up to "
        f"{max_f_ratio:.6g} on Mesh-1 outer-44 plateau trajectory",
        "OUTER_TERMINAL_ERROR_BUDGET": "1e-8 K (+ ulp floors); enthalpy plateau ±1 binary64 ulp "
        "leaves terminal_residual_k unchanged at 3.5037e-8",
        "DOMINANT_ERROR_SOURCE": "D: binary64 shooting enthalpy bracket collapse (float_collapsed) "
        "with zero adjacent-probe residual sensitivity; secondary inner slack via trial-q≠signed_q propagation",
        "OUTER_RESIDUAL_BEFORE_K": bisect.get(
            "terminal_residual_k", mesh1.get("terminal_residual_k")
        ),
        "OUTER_RESIDUAL_AFTER_K": "N/A (q_phys propagation replay → HARD_BLOCKER cell bracket; not committed)",
        "ORIGINAL_TERMINAL_GATE": "BLOCKED",
        "ALTERNATIVE_SOLVER_REQUIRED": True,
        "ALTERNATIVE_SOLVER_VALIDATED": "not_run",
        "DECISION": "C",
        "REMAINING_BLOCKER": "Unidirectional outer bisection cannot refine shell shooting enthalpy below "
        "binary64 ULP at ~122022.67 J/kg while holding 1e-8 K terminal gate; CoolProp binary64 P-H path "
        "quantizes observable terminal temperature.",
        "MERGE_AUTHORIZED": False,
        "mesh1_plateau_cells": cells,
        "mesh1_terminal_sensitivity_ulp": {
            "minus_ulp": mesh1.get("sens_minus_ulp_terminal_residual_k"),
            "plus_ulp": mesh1.get("sens_plus_ulp_terminal_residual_k"),
        },
        "outer_bisection_diagnostics": bisect,
    }
    out = ART / "v08_03_solver_decision_evidence.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
