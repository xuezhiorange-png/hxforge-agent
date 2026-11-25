"""V08_LAYERED_ENGINEERING_ACCEPTANCE_V1 — Decision C experimental contract (non-production)."""

# ruff: noqa: E501

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Callable
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _terminal_tolerance_pass,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    ENERGY_ACCEPTANCE_FLOOR_W,
    CandidateRatingBindings,
    ProductionCulpReport,
    assess_production_culp_rating,
    final_trajectory_task172_holes,
    run_candidate_mesh_closeout,
)
from prototypes.v08_thermal_rating.engineering_error_budget_v08 import (
    frozen_engineering_error_budgets,
)
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    enthalpy_audit_precision_threshold_j_kg,
    tp_ph_reconstruction_audit,
    tp_ph_reconstruction_summary,
)
from prototypes.v08_thermal_rating.mesh_level_diagnostics_v08 import IsolatedMeshLevelDiagnostic
from prototypes.v08_thermal_rating.shadow_layered_acceptance import ORIGINAL_PRODUCTION_ACCEPTANCE
from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    evaluate_v08_04_candidate_hydraulics,
)

CONTRACT_ID = "V08_LAYERED_ENGINEERING_ACCEPTANCE_V1"
LAYER_MODE = "DECISION_C_LAYERED_V1"

LayerStatus = Literal["PASS", "BLOCKED", "NOT_EVALUATED", "INFORMATIVE_ONLY", "PARTIAL"]
AcceptanceStatus = Literal["PASS", "BLOCKED", "NOT_RUN"]


@dataclass(frozen=True)
class IndependentErrorBudgetEvidence:
    independently_derived: bool
    task172_culp_ceiling: float
    terminal_temperature_contract_k: str
    terminal_enthalpy_formula: str
    property_tp_ph_max_delta_h_j_kg: float | None
    property_tp_ph_max_delta_t_k: float | None
    float_ulp_water_300k_h_j_kg: float
    mesh_discretization_note: str
    derivation_sources: tuple[str, ...]
    back_solved_from_failure_residual: Literal[False] = False


@dataclass(frozen=True)
class LayerEvidence:
    layer: Literal["L1", "L2", "L3", "L4"]
    status: LayerStatus
    metrics: dict[str, Any]


@dataclass(frozen=True)
class DualContractVerdict:
    contract_id: str
    original_production_acceptance: AcceptanceStatus
    original_detail: dict[str, Any]
    experimental_engineering_acceptance: AcceptanceStatus
    experimental_detail: dict[str, Any]
    layers: tuple[LayerEvidence, ...]
    error_budget: IndependentErrorBudgetEvidence
    geometry_projection_hash: str
    candidate_id: str
    rating_request_hash: str
    normalized_input_hash: str


def derive_independent_error_budget(
    provider: PropertyProvider,
    bindings: CandidateRatingBindings,
) -> IndependentErrorBudgetEvidence:
    """Budget from frozen production contract refs + inlet TP→PH roundtrip (not failure residuals)."""
    frozen = frozen_engineering_error_budgets()
    tp_sum = tp_ph_reconstruction_summary(provider, bindings)
    tp = tp_ph_reconstruction_audit(provider, bindings)
    h_ref = float(tp.h_tp_j_kg or "0")
    ulp_h = math.ulp(h_ref) if h_ref != 0.0 else math.ulp(1.0)
    return IndependentErrorBudgetEvidence(
        independently_derived=True,
        task172_culp_ceiling=frozen.task172.culp_ratio_ceiling,
        terminal_temperature_contract_k=frozen.task173_terminal.terminal_temperature_tolerance_k,
        terminal_enthalpy_formula=frozen.task173_terminal.enthalpy_tolerance_formula,
        property_tp_ph_max_delta_h_j_kg=tp_sum.max_delta_h_j_kg,
        property_tp_ph_max_delta_t_k=tp_sum.max_delta_t_k,
        float_ulp_water_300k_h_j_kg=ulp_h,
        mesh_discretization_note=frozen.mesh_discretization_note,
        derivation_sources=(
            "engineering_error_budget_v08.frozen_engineering_error_budgets",
            "enthalpy_audit_context_v08.tp_ph_reconstruction_audit",
            "models.TERMINAL_TOLERANCE_K",
        ),
    )


def _mesh_run_holes(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    diag: IsolatedMeshLevelDiagnostic | None,
) -> int | None:
    if diag is None or diag.N_SHOOTING_ENTHALPY_J_KG is None:
        return None
    return final_trajectory_task172_holes(
        bindings,
        provider,
        subdivisions=diag.subdivisions,
        shooting_enthalpy_j_kg=diag.N_SHOOTING_ENTHALPY_J_KG,
    )


def _layer_l1(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    n4: IsolatedMeshLevelDiagnostic | None,
) -> LayerEvidence:
    holes = _mesh_run_holes(bindings, provider, n4)
    if holes is None:
        return LayerEvidence(
            "L1",
            "NOT_EVALUATED",
            {"reason": "no_n4_shooting_enthalpy", "task172_holes": None},
        )
    status: LayerStatus = "PASS" if holes == 0 else "BLOCKED"
    return LayerEvidence(
        "L1",
        status,
        {
            "task172_numerical_holes": holes,
            "gate": "production_culp_ceil_1.0_per_cell",
            "mode": LAYER_MODE,
            "note": "L1 requires zero Task172 holes on N4 trajectory (production C-ULP).",
        },
    )


def _layer_l2(
    provider: PropertyProvider,
    bindings: CandidateRatingBindings,
    budget: IndependentErrorBudgetEvidence,
) -> LayerEvidence:
    tp = tp_ph_reconstruction_audit(provider, bindings)
    tp_sum = tp_ph_reconstruction_summary(provider, bindings)
    ulp_gate = max(
        enthalpy_audit_precision_threshold_j_kg(),
        budget.float_ulp_water_300k_h_j_kg * 8,
    )
    dh = tp_sum.max_delta_h_j_kg
    consistent = tp.query_status == "PASS" and not math.isnan(dh) and dh <= ulp_gate
    status: LayerStatus = "PASS" if consistent else "BLOCKED"
    return LayerEvidence(
        "L2",
        status,
        {
            "tp_ph_status": tp.query_status,
            "max_delta_h_j_kg": dh,
            "max_delta_t_k": tp_sum.max_delta_t_k,
            "ulp_gate_j_kg": ulp_gate,
            "property_uncertainty_budget": "UNRESOLVED",
            "mode": LAYER_MODE,
        },
    )


def _layer_l3(
    bindings: CandidateRatingBindings,
    n1: IsolatedMeshLevelDiagnostic | None,
    n2: IsolatedMeshLevelDiagnostic | None,
    n4: IsolatedMeshLevelDiagnostic | None,
) -> LayerEvidence:
    gates = {
        "N1": n1.gate if n1 else "not_run",
        "N2": n2.gate if n2 else "not_run",
        "N4": n4.gate if n4 else "not_run",
    }
    run = None
    for d in (n4, n2, n1):
        if d is not None and d.outer_result.best_valid_run is not None:
            run = d.outer_result.best_valid_run
            break
        if d is not None and d.outer_result.accepted_run is not None:
            run = d.outer_result.accepted_run
            break
    energy_ok = False
    term_ok = False
    duty_w: str | None = None
    energy_res: str | None = None
    if run is not None:
        obs = run.observables
        duty_w = str(obs.total_duty_w)
        energy_res = str(obs.energy_balance_residual_w)
        tol = max(float(ENERGY_ACCEPTANCE_FLOOR_W), float(obs.duty_roundoff_floor_w))
        energy_ok = float(obs.energy_balance_residual_w) <= tol
        term_ok = _terminal_tolerance_pass(run)
    mesh_ok = all(g == "ACCEPTED" for g in gates.values())
    if not mesh_ok:
        status: LayerStatus = "BLOCKED"
    elif run is None:
        status = "NOT_EVALUATED"
    else:
        status = "PASS" if energy_ok and term_ok else "BLOCKED"
    return LayerEvidence(
        "L3",
        status,
        {
            "mesh_gates": gates,
            "mesh_convergence_all_accepted": mesh_ok,
            "energy_balance_pass": energy_ok,
            "terminal_tolerance_pass": term_ok,
            "total_duty_w": duty_w,
            "energy_balance_residual_w": energy_res,
            "terminal_residual_k": gates and (n4.N_TERMINAL_RESIDUAL_K if n4 else None),
            "terminal_residual_j_kg": n4.N_TERMINAL_RESIDUAL_J_KG if n4 else None,
            "mode": LAYER_MODE,
        },
    )


def _layer_l4(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    l3: LayerEvidence,
) -> LayerEvidence:
    try:
        hyd = evaluate_v08_04_candidate_hydraulics(bindings, provider=provider)
    except (ValueError, TypeError) as exc:
        return LayerEvidence(
            "L4",
            "NOT_EVALUATED",
            {"hydraulic_eval_error": type(exc).__name__},
        )
    g = hyd.hard_gate
    hyd_ok = (
        g.tube_full_path == "PASS"
        and g.shell_full_path == "PASS"
        and g.four_nozzle_velocity == "PASS"
        and g.geometry_legal == "PASS"
        and g.model_applicability == "PASS"
    )
    target = bindings.target_duty_w
    duty_ok = False
    duty_w = l3.metrics.get("total_duty_w")
    if duty_w is not None:
        duty_ok = Decimal(str(duty_w)) >= target
    status: LayerStatus = "PASS" if hyd_ok and duty_ok else "BLOCKED"
    return LayerEvidence(
        "L4",
        status,
        {
            "hard_gate": {
                "tube_full_path": g.tube_full_path,
                "shell_full_path": g.shell_full_path,
                "four_nozzle_velocity": g.four_nozzle_velocity,
            },
            "target_duty_w": str(target),
            "achieved_duty_w": duty_w,
            "duty_at_or_above_target": duty_ok,
            "result_hash": hyd.result_hash,
            "mode": LAYER_MODE,
        },
    )


def _original_production_verdict(production: ProductionCulpReport | None) -> tuple[AcceptanceStatus, dict[str, Any]]:
    if production is None:
        return "NOT_RUN", {"mode": ORIGINAL_PRODUCTION_ACCEPTANCE}
    status: AcceptanceStatus = "PASS" if production.outcome == "RATING_SUCCESS" else "BLOCKED"
    row = production.row
    detail = {
        "mode": ORIGINAL_PRODUCTION_ACCEPTANCE,
        "rating_outcome": production.outcome,
        "failure_code": production.failure_code,
        "mesh_n1": production.mesh_n1_status,
        "mesh_n2": production.mesh_n2_status,
        "mesh_n4": production.mesh_n4_status,
        "energy_balance_status": row.energy_balance_status if row else None,
        "mesh_convergence": row.mesh_convergence_n1_n2_n4 if row else None,
    }
    return status, detail


def _experimental_verdict(layers: tuple[LayerEvidence, ...]) -> tuple[AcceptanceStatus, dict[str, Any]]:
    status_map = {layer.layer: layer.status for layer in layers}
    required = ("L1", "L2", "L3", "L4")
    if any(status_map.get(k) == "NOT_EVALUATED" for k in required):
        return "BLOCKED", {"reason": "incomplete_layers", "status_map": status_map}
    if all(status_map[k] == "PASS" for k in required):
        return "PASS", {"contract_id": CONTRACT_ID, "status_map": status_map}
    return "BLOCKED", {"contract_id": CONTRACT_ID, "status_map": status_map}


def evaluate_dual_contract(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    production: ProductionCulpReport | None = None,
    run_production_rating: bool = False,
) -> DualContractVerdict:
    budget = derive_independent_error_budget(provider, bindings)
    if run_production_rating and production is None:
        production = assess_production_culp_rating(bindings, provider)
    closeout = run_candidate_mesh_closeout(bindings, provider, run_production_gate=False)
    l1 = _layer_l1(bindings, provider, closeout.n4_diagnostic)
    l2 = _layer_l2(provider, bindings, budget)
    l3 = _layer_l3(
        bindings,
        closeout.n1_diagnostic,
        closeout.n2_diagnostic,
        closeout.n4_diagnostic,
    )
    l4 = _layer_l4(bindings, provider, l3)
    layers = (l1, l2, l3, l4)
    orig, orig_d = _original_production_verdict(production)
    exp, exp_d = _experimental_verdict(layers)
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    return DualContractVerdict(
        contract_id=CONTRACT_ID,
        original_production_acceptance=orig,
        original_detail=orig_d,
        experimental_engineering_acceptance=exp,
        experimental_detail=exp_d,
        layers=layers,
        error_budget=budget,
        geometry_projection_hash=bindings.geometry_projection_hash,
        candidate_id=bindings.rating_request.candidate_id,
        rating_request_hash=candidate_rating_request_hash(bindings.rating_request),
        normalized_input_hash=bindings.handoff.normalized_input_hash,
    )


@dataclass(frozen=True)
class LayeredNegativeControlRow:
    scenario: str
    expected_block: str
    experimental_blocked: bool


@dataclass(frozen=True)
class LayeredNegativeControlResult:
    status: Literal["PASS", "BLOCKED"]
    false_acceptance_count: int
    rows: tuple[LayeredNegativeControlRow, ...]


def run_layered_negative_controls(
    template: DualContractVerdict,
) -> LayeredNegativeControlResult:
    """Synthetic perturbations on layered verdict — not independent acceptance cases."""
    rows: list[LayeredNegativeControlRow] = []

    def _blocked_if_energy_forced() -> bool:
        l3 = next(x for x in template.layers if x.layer == "L3")
        forged = LayerEvidence(
            "L3",
            "PASS" if l3.metrics.get("energy_balance_pass") else "BLOCKED",
            {**l3.metrics, "energy_balance_pass": False},
        )
        layers = tuple(x if x.layer != "L3" else forged for x in template.layers)
        return _experimental_verdict(layers)[0] == "BLOCKED"

    scenarios: list[tuple[str, str, Callable[[], bool]]] = [
        ("force_energy_imbalance", "L3", _blocked_if_energy_forced),
        (
            "force_l1_holes",
            "L1",
            lambda: _experimental_verdict(
                tuple(
                    LayerEvidence(
                        "L1",
                        "BLOCKED",
                        {"task172_numerical_holes": 3},
                    )
                    if x.layer == "L1"
                    else x
                    for x in template.layers
                )
            )[0]
            == "BLOCKED",
        ),
        (
            "force_l2_property_fail",
            "L2",
            lambda: _experimental_verdict(
                tuple(
                    LayerEvidence("L2", "BLOCKED", {"tp_ph_status": "BLOCKED"})
                    if x.layer == "L2"
                    else x
                    for x in template.layers
                )
            )[0]
            == "BLOCKED",
        ),
        (
            "force_l4_hydraulic_fail",
            "L4",
            lambda: _experimental_verdict(
                tuple(
                    LayerEvidence(
                        "L4",
                        "BLOCKED",
                        {"duty_at_or_above_target": False},
                    )
                    if x.layer == "L4"
                    else x
                    for x in template.layers
                )
            )[0]
            == "BLOCKED",
        ),
    ]
    false = 0
    for name, layer, fn in scenarios:
        blocked = fn()
        if not blocked:
            false += 1
        rows.append(
            LayeredNegativeControlRow(
                scenario=name,
                expected_block=layer,
                experimental_blocked=blocked,
            )
        )
    status: Literal["PASS", "BLOCKED"] = "PASS" if false == 0 else "BLOCKED"
    return LayeredNegativeControlResult(status=status, false_acceptance_count=false, rows=tuple(rows))