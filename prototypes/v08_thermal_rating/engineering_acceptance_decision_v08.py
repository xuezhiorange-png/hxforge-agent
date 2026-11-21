"""Engineering acceptance decision package — layers decoupled from auto contract-change."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prototypes.v08_thermal_rating.engineering_error_budget_v08 import (
    EngineeringErrorBudgetReport,
    build_engineering_error_budget_report,
    quantify_local_residual_budget,
    quantify_terminal_budget,
)
from prototypes.v08_thermal_rating.engineering_physical_evaluator_v08 import (
    EngineeringPhysicalAssessment,
    Frozen330Evidence,
    NegativeControlResult,
)

ProductionNumericalStatus = Literal["PASS", "BLOCKED", "NOT_RUN"]
ContractReviewStatus = Literal["ELIGIBLE_FOR_DISCUSSION", "NOT_ELIGIBLE"]
ContractChangeEvidence = Literal["INSUFFICIENT", "SUFFICIENT"]
EngineeringAcceptance = Literal["BLOCKED"]


@dataclass(frozen=True)
class EngineeringAcceptanceDecisionPackage:
    production_numerical_status: ProductionNumericalStatus
    production_numerical_detail: str
    duty_screen: str
    hydraulic_screen: str
    energy_balance: str
    local_heat_transfer: str
    mesh_convergence: str
    engineering_physical_evidence: str
    contract_review_status: ContractReviewStatus
    contract_change_evidence: ContractChangeEvidence
    production_tolerance_change_approved: bool
    engineering_acceptance: EngineeringAcceptance
    engineering_error_budget_status: Literal["COMPLETE", "INCOMPLETE"]
    engineering_error_budget: str
    local_residual_error_budget: str
    mesh_convergence_evidence: str
    negative_control_tests: Literal["PASS", "BLOCKED"]
    recommended_contract_change: str
    migration_proposal_ref: str
    production_task172: str
    production_task173: str
    merge_authorized: bool
    production_contract_change_authorized: bool
    rationale: tuple[str, ...]


def build_engineering_acceptance_decision(
    *,
    ev: Frozen330Evidence,
    physical: EngineeringPhysicalAssessment,
    negative: NegativeControlResult,
    task172_gate: str,
    task173_gate: str,
    error_budget: EngineeringErrorBudgetReport | None = None,
) -> EngineeringAcceptanceDecisionPackage:
    error_budget = error_budget or build_engineering_error_budget_report(frozen=ev.raw)

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

    screens = physical.screens
    phys_evidence = screens.engineering_physical_evidence
    mesh_ev = str(screens.mesh_convergence)

    terminal_q = quantify_terminal_budget(
        residual_h=ev.terminal_residual_j_kg,
        allowed_h=ev.terminal_allowed_j_kg,
        residual_k=ev.terminal_residual_k,
    )
    eng_budget = (
        f"{error_budget.task173_terminal_enthalpy}; {error_budget.property_computation_error}; "
        f"{terminal_q}"
    )
    local_budget = (
        f"{error_budget.task172_local_residuals}; "
        f"{quantify_local_residual_budget(max_ratio_observed=None)}"
    )

    notes: list[str] = []
    negatives_ok = negative.status == "PASS"
    production_blocked = prod_num == "BLOCKED"

    contract_review: ContractReviewStatus = (
        "ELIGIBLE_FOR_DISCUSSION"
        if production_blocked and negatives_ok and phys_evidence == "PARTIAL"
        else "NOT_ELIGIBLE"
    )
    contract_change: ContractChangeEvidence = "INSUFFICIENT"
    rec_change = (
        "Discussion-only: document Task172 hole residuals and Task173 terminal exceedance; "
        "no production tolerance edit authorized from this package."
        if contract_review == "ELIGIBLE_FOR_DISCUSSION"
        else "none"
    )

    if phys_evidence == "SUFFICIENT":
        notes.append("incorrect_sufficient_blocked_by_policy")
    if screens.energy_balance == "not_evaluated":
        notes.append("energy_balance_not_evaluated_independent_of_duty_screen")
    if screens.local_heat_transfer == "BLOCKED":
        notes.append("local_heat_transfer_blocked_n4_or_task172")
    if not negatives_ok:
        notes.append("negative_control_failed")

    return EngineeringAcceptanceDecisionPackage(
        production_numerical_status=prod_num,
        production_numerical_detail=prod_detail,
        duty_screen=screens.duty_screen,
        hydraulic_screen=screens.hydraulic_screen,
        energy_balance=screens.energy_balance,
        local_heat_transfer=screens.local_heat_transfer,
        mesh_convergence=screens.mesh_convergence,
        engineering_physical_evidence=phys_evidence,
        contract_review_status=contract_review,
        contract_change_evidence=contract_change,
        production_tolerance_change_approved=False,
        engineering_acceptance="BLOCKED",
        engineering_error_budget_status=error_budget.status,
        engineering_error_budget=eng_budget,
        local_residual_error_budget=local_budget,
        mesh_convergence_evidence=mesh_ev,
        negative_control_tests=negative.status,
        recommended_contract_change=rec_change,
        migration_proposal_ref="docs/decisions/V08_03_ENGINEERING_ACCEPTANCE_MIGRATION_PROPOSAL.md",
        production_task172=task172_gate,
        production_task173=task173_gate,
        merge_authorized=False,
        production_contract_change_authorized=False,
        rationale=tuple(notes),
    )


__all__ = [
    "ContractChangeEvidence",
    "ContractReviewStatus",
    "EngineeringAcceptanceDecisionPackage",
    "build_engineering_acceptance_decision",
]
