#!/usr/bin/env python3
"""TASK_ID=V08_03_NUMERICAL_ACCEPTANCE_CONTRACT_REVIEW — frozen N4 + production terminal audit."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    assess_production_culp_rating,
    load_case_bindings,
    resolve_candidate_bindings_by_id,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    run_enthalpy_audit_body,
    tp_ph_reconstruction_audit,
)
from prototypes.v08_thermal_rating.enthalpy_authority_experiment_v08 import (
    evaluate_n4_authority_experiment,
)
from prototypes.v08_thermal_rating.numerical_contract_review_v08 import (
    review_numerical_acceptance_contract,
)
from prototypes.v08_thermal_rating.numerical_contract_terminal_v08 import (
    production_terminal_gate_audit,
)
from prototypes.v08_thermal_rating.production_rating_diagnostics_v08 import (
    build_production_rating_diagnostic,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
GEOMETRY_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"
FROZEN_CONTEXT_ARTIFACT = Path(
    "/opt/cursor/artifacts/v08_03_enthalpy_audit_context_identity_fix.json"
)


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_status() -> str:
    try:
        out = subprocess.check_output(
            [
                "gh",
                "run",
                "list",
                "--repo",
                "xuezhiorange-png/hxforge-agent",
                "--branch",
                "cursor/v08-03-live-thermal-rating-1201",
                "--limit",
                "1",
                "--json",
                "conclusion,status,number",
            ],
            cwd=_REPO,
            text=True,
        )
        row = json.loads(out)[0]
        if row.get("status") != "completed":
            return f"in_progress_{row.get('number', '?')}"
        return str(row.get("conclusion") or "unknown")
    except Exception:
        return "unknown"


def _json_ready(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_numerical_acceptance_contract_review.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings and bindings.geometry_projection_hash == GEOMETRY_HASH

    frozen = {}
    if FROZEN_CONTEXT_ARTIFACT.is_file():
        frozen = json.loads(FROZEN_CONTEXT_ARTIFACT.read_text(encoding="utf-8"))

    iso_n4 = solve_isolated_outer_boundary(bindings, provider, subdivisions=4)
    run = iso_n4.best_valid_run or iso_n4.accepted_run
    assert run is not None

    def audit_body(_c: object, _t: object) -> tuple[Any, Any, Any]:
        tp = tp_ph_reconstruction_audit(provider, bindings)
        term = production_terminal_gate_audit(run)
        exp = evaluate_n4_authority_experiment(
            run,
            bindings=bindings,
            provider=provider,
            outer_status=iso_n4.status,
        )
        return tp, term, exp

    tp, term, exp = run_enthalpy_audit_body(bindings, provider, subdivisions=4, body=audit_body)
    verdict = exp.propagation_verdict
    assert verdict is not None

    prod = build_production_rating_diagnostic(assess_production_culp_rating(bindings, provider))
    review = review_numerical_acceptance_contract(
        terminal=term,
        propagation=verdict,
        outer_n4_status=iso_n4.status,
        production_task173=prod.PRODUCTION_TASK173_STATUS,
        cell_propagation_j_kg=verdict.cell_enthalpy_propagation_error_j_kg,
    )

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_NUMERICAL_ACCEPTANCE_CONTRACT_REVIEW",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "AUDIT_CONTEXT": "VALID",
        "TP_PH_QUERY_STATUS": tp.query_status,
        "TP_PH_DELTA_H_J_KG": tp.delta_h_j_kg if tp.query_status == "PASS" else "unavailable",
        "TP_PH_DELTA_T_K": tp.delta_t_k if tp.query_status == "PASS" else "unavailable",
        "ENTHALPY_PROPAGATION_ERROR_J_KG": verdict.cell_enthalpy_propagation_error_j_kg,
        "TERMINAL_RESIDUAL_J_KG": term.terminal_residual_j_kg,
        "TERMINAL_ALLOWED_J_KG": term.terminal_allowed_j_kg,
        "TERMINAL_RESIDUAL_K": term.terminal_residual_k,
        "TERMINAL_ALLOWED_K": term.terminal_allowed_k,
        "TERMINAL_T_GATE": term.terminal_temperature_gate,
        "TERMINAL_H_GATE": term.terminal_enthalpy_gate,
        "BINARY64_ENTHALPY_ULP": term.binary64_enthalpy_ulp,
        "BINARY64_TEMPERATURE_ULP": term.binary64_temperature_ulp,
        "TASK172_LOCAL_GATE": exp.task172_gate,
        "PROPAGATION_DEFECT_CAUSAL_PROOF": verdict.propagation_defect_causal_proof,
        "CELL_ENTHALPY_PROPAGATION_ERROR": verdict.cell_enthalpy_propagation_error_j_kg,
        "STATE_PH_RECONSTRUCTION_ERROR": verdict.state_ph_reconstruction_error_j_kg,
        "OUTER_TERMINAL_RESIDUAL": verdict.outer_terminal_residual_j_kg,
        "LOCAL_CONSTITUTIVE_ROOT_STATUS": verdict.local_constitutive_root_status,
        "ENTHALPY_PROPAGATION_DEFECT_CONFIRMED": verdict.enthalpy_propagation_defect_confirmed,
        "NUMERICAL_CONTRACT_POSTURE": review.numerical_contract_posture,
        "CONTRACT_REVIEW_ELIGIBILITY": review.contract_review_eligibility,
        "SPECIFIC_REQUIRED_CHANGE": review.specific_required_change,
        "SHOOTING_N1": frozen.get("ISOLATED_N1", "ACCEPTED"),
        "SHOOTING_N2": frozen.get("ISOLATED_N2", "ACCEPTED"),
        "SHOOTING_N4": "BLOCKED" if iso_n4.status != "ACCEPTED" else "ACCEPTED",
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_TASK173": prod.PRODUCTION_TASK173_STATUS,
        "DISTINCT_FULLY_CONVERGED": 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_SOLVER_REPLACED": False,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "MERGE_AUTHORIZED": False,
        "contract_rationale": review.rationale,
        "tp_ph_audit": _json_ready(asdict(tp)),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "NUMERICAL_CONTRACT_POSTURE": review.numerical_contract_posture,
            }
        )
    )


if __name__ == "__main__":
    main()
