"""Engineering acceptance decision package — layers decoupled from auto contract-change."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prototypes.v08_thermal_rating.engineering_error_budget_v08 import (
    EngineeringErrorBudgetBundle,
    frozen_engineering_error_budgets,
    quantify_local_residual_budget,
    quantify_terminal_budget,
)
from prototypes.v08_thermal_rating.engineering_physical_evaluator_v08 import (
    EngineeringPhysicalAssessment,
    Frozen330Evidence,
    NegativeControlResult,
)

ProductionNumericalStatus = Literal["PASS", "BLOCKED", "NOT_RUN"]
ContractReviewEligibility = Literal["ELIGIBLE", "INSUFFICIENT"]
EngineeringAcceptance = Literal["BLOCKED"]  # this task: never approve full engineering sign-off


@dataclass(frozen=True)
class EngineeringAcceptanceDecisionPackage:
    production_numerical_status: ProductionNumericalStatus
    production_numerical_detail: str
    engineering_physical_evidence: str
    contract_review_eligibility: ContractReviewEligibility
    engineering_acceptance: EngineeringAcceptance
    engineering_error_budget: str
    local_residual_error_budget: str
    mesh_convergence_evidence: str
    negative_control_tests: Literal["PASS", "BLOCKED"]
    recommended_contract_change: str
    migration_proposal_ref: str
    production_task172: str
    production_task173: str
    rationale: tuple[str, ...]


def build_engineering_acceptance_decision(
    *,
    ev: Frozen330Evidence,
    physical: EngineeringPhysicalAssessment,
    negative: NegativeControlResult,
    task172_gate: str,
    task173_gate: str,
    budgets: EngineeringErrorBudgetBundle | None = None,
) -> EngineeringAcceptanceDecisionPackage:
    budgets = budgets or frozen_engineering_error_budgets()

    prod_num: ProductionNumericalStatus
    if task173_gate == "NOT_ATTEMPTED":
        prod_num = "NOT_RUN"
        prod_detail = "production_rating_not_attempted"
    elif task173_gate in ("BLOCKED", "VALIDATED"):
        prod_num = "PASS" if task173_gate == "VALIDATED" else "BLOCKED"
        prod_detail = f"task172={task172_gate};task173={task173_gate};n4={ev.shooting_n4}"
    else:
        prod_num = "BLOCKED"
        prod_detail = f"task173_status={task173_gate}"

    phys_evidence = physical.grade
    mesh_ev = physical.mesh_convergence_evidence

    term_q = quantify_terminal_budget(
        residual_h=ev.terminal_residual_j_kg,
        allowed_h=ev.terminal_allowed_j_kg,
        residual_k=ev.terminal_residual_k,
    )
    eng_budget = (
        f"{budgets.task173_terminal.contract_id}: {term_q}; "
        f"{budgets.property_interface_note}"
    )
    local_budget = (
        f"{budgets.task172.contract_id}: {budgets.task172.acceptance_rule}; "
        f"{quantify_local_residual_budget(max_ratio_observed=None)}"
    )

    eligible: ContractReviewEligibility = "INSUFFICIENT"
    rec_change = "none"
    notes: list[str] = []

    negatives_ok = negative.status == "PASS"
    propagation_not_causal = physical.propagation_subdominant_to_terminal
    production_blocked = prod_num == "BLOCKED"
    physical_sufficient = physical.grade == "SUFFICIENT"

    if (
        negatives_ok
        and production_blocked
        and physical_sufficient
        and propagation_not_causal
        and physical.terminal_h_exceeds_contract_margin
    ):
        eligible = "ELIGIBLE"
        rec_change = (
            "Draft dual-layer acceptance RFC only: (1) keep Task172 C-ULP and Task173 terminal "
            "production gates unchanged until sign-off; (2) add documented engineering error "
            "budget fields for property ULP, mesh band, and outer-shooting plateau evidence. "
            "No numeric tolerance values in this commit."
        )
        notes.append("production_blocked_with_sufficient_physical_evidence_and_negative_controls")
    else:
        if not negatives_ok:
            notes.append("negative_control_failed")
        if not physical_sufficient:
            notes.append(f"physical_evidence_{physical.grade}")
        if not propagation_not_causal:
            notes.append("propagation_may_be_causal_insufficient_analysis")

    return EngineeringAcceptanceDecisionPackage(
        production_numerical_status=prod_num,
        production_numerical_detail=prod_detail,
        engineering_physical_evidence=phys_evidence,
        contract_review_eligibility=eligible,
        engineering_acceptance="BLOCKED",
        engineering_error_budget=eng_budget,
        local_residual_error_budget=local_budget,
        mesh_convergence_evidence=mesh_ev,
        negative_control_tests=negative.status,
        recommended_contract_change=rec_change,
        migration_proposal_ref="docs/decisions/V08_03_ENGINEERING_ACCEPTANCE_MIGRATION_PROPOSAL.md",
        production_task172=task172_gate,
        production_task173=task173_gate,
        rationale=tuple(notes),
    )


__all__ = [
    "EngineeringAcceptanceDecisionPackage",
    "build_engineering_acceptance_decision",
]
