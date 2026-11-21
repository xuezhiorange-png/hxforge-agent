"""Task172 / Task173 error budgets from production contracts (read-only, no edits)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K


@dataclass(frozen=True)
class Task172ErrorBudget:
    """C-ULP local gate: each |r_i| / bound_i <= 1.0 (production eval_trial_residual_gate)."""

    contract_id: str
    residual_dimensions: tuple[str, ...]
    acceptance_rule: str
    culp_ratio_ceiling: float
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Task173TerminalErrorBudget:
    """Terminal dual gate: T/H vs TERMINAL_TOLERANCE_K and cp-scaled enthalpy floor."""

    contract_id: str
    terminal_temperature_tolerance_k: str
    enthalpy_tolerance_formula: str
    binary64_ulp_enthalpy_floor: str
    binary64_ulp_temperature_floor: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class EngineeringErrorBudgetBundle:
    task172: Task172ErrorBudget
    task173_terminal: Task173TerminalErrorBudget
    property_interface_note: str
    mesh_discretization_note: str


@dataclass(frozen=True)
class EngineeringErrorBudgetReport:
    status: Literal["COMPLETE", "INCOMPLETE"]
    task172_local_residuals: str
    task173_terminal_temperature: str
    task173_terminal_enthalpy: str
    property_computation_error: str
    cell_enthalpy_propagation_j_kg: str
    mesh_discretization: str
    correlation_model_uncertainty: str
    summary: tuple[str, ...]


def frozen_engineering_error_budgets() -> EngineeringErrorBudgetBundle:
    """Authoritative contract references for review package (not tuned to current failures)."""
    return EngineeringErrorBudgetBundle(
        task172=Task172ErrorBudget(
            contract_id="TASK172_CULP_LOCAL_RESIDUAL_GATE",
            residual_dimensions=("r1", "r2", "r3"),
            acceptance_rule="max(abs(residual_i) / acceptance_bound_i) <= 1.0",
            culp_ratio_ceiling=1.0,
            notes=(
                "Source: task172_local_runtime.service.eval_trial_residual_gate",
                "Independent of whole-exchanger energy balance pass.",
            ),
        ),
        task173_terminal=Task173TerminalErrorBudget(
            contract_id="TASK173_TERMINAL_TOLERANCE_V1",
            terminal_temperature_tolerance_k=str(TERMINAL_TOLERANCE_K),
            enthalpy_tolerance_formula=(
                "allowed_h = cp_shell_inlet * TERMINAL_TOLERANCE_K + ulp(h_cold_inlet); "
                "0 <= residual_h <= allowed_h; "
                "0 <= residual_T <= TERMINAL_TOLERANCE_K + ulp(T_ref)"
            ),
            binary64_ulp_enthalpy_floor="math.ulp(float(h_cold_inlet))",
            binary64_ulp_temperature_floor="math.ulp(float(shell_inlet_T + residual_T))",
            notes=(
                "Source: task173_integrated_rating.service._terminal_tolerance_pass",
                "TERMINAL_TOLERANCE_K is 1e-8 K; enthalpy scale follows cp at inlet.",
            ),
        ),
        property_interface_note=(
            "CoolProp binary64 at fixed P; mapping PURE_ORDINARY_WATER→Water for properties only."
        ),
        mesh_discretization_note=(
            "N1/N2/N4 coarse-to-fine; convergence is separate from local C-ULP and terminal gates."
        ),
    )


def build_engineering_error_budget_report(
    *, frozen: dict[str, Any]
) -> EngineeringErrorBudgetReport:
    prop = frozen.get("tp_ph_query_status", "UNAVAILABLE")
    if prop == "PASS":
        property_line = (
            f"inlet_TP_PH_delta_h_J_kg={frozen.get('tp_ph_delta_h_j_kg', 'UNAVAILABLE')}; "
            f"delta_t_K={frozen.get('tp_ph_delta_t_k', 'UNAVAILABLE')}"
        )
    else:
        property_line = "UNAVAILABLE"

    t_res = frozen.get("terminal_residual_k", "UNAVAILABLE")
    t_allow = frozen.get("terminal_allowed_k", "UNAVAILABLE")
    h_res = frozen.get("terminal_residual_j_kg", "UNAVAILABLE")
    h_allow = frozen.get("terminal_allowed_j_kg", "UNAVAILABLE")
    h_over = "UNAVAILABLE"
    if h_res != "UNAVAILABLE" and h_allow != "UNAVAILABLE":
        hres, hall = Decimal(str(h_res)), Decimal(str(h_allow))
        if hall > 0:
            h_over = f"{((hres - hall) / hall * 100):.2f}% over production allowed_h"

    task172 = (
        "task172_r1_r2_r3_actual:UNAVAILABLE; task172_acceptance_bound:1.0 C-ULP ratio; "
        f"production_gate={frozen.get('production_task172_gate', 'BLOCKED')}"
    )
    task173_t = f"residual_K={t_res} allowed_K={t_allow} contract_K={TERMINAL_TOLERANCE_K}"
    task173_h = f"residual_J_kg={h_res} allowed_J_kg={h_allow} exceedance={h_over}"

    cell_prop = frozen.get("cell_enthalpy_propagation_error_j_kg", "UNAVAILABLE")
    mesh = (
        f"N1={frozen.get('shooting_n1', '?')};N2={frozen.get('shooting_n2', '?')};"
        f"N4={frozen.get('shooting_n4', '?')}"
    )
    corr = "UNAVAILABLE (no licensed correlation uncertainty envelope in frozen bundle)"

    summary = (
        f"terminal_enthalpy_exceedance:{h_over}",
        f"cell_propagation:{cell_prop}",
        "task172_measured_residuals:UNAVAILABLE",
    )

    return EngineeringErrorBudgetReport(
        status="INCOMPLETE",
        task172_local_residuals=task172,
        task173_terminal_temperature=task173_t,
        task173_terminal_enthalpy=task173_h,
        property_computation_error=property_line,
        cell_enthalpy_propagation_j_kg=str(cell_prop),
        mesh_discretization=mesh,
        correlation_model_uncertainty=corr,
        summary=summary,
    )


def quantify_local_residual_budget(*, max_ratio_observed: float | None) -> str:
    if max_ratio_observed is None:
        return "unobserved:frozen_mesh_task172_holes>0"
    return f"culp_max_ratio_observed={max_ratio_observed:.6g} ceiling=1.0"


def quantify_terminal_budget(
    *, residual_h: Decimal, allowed_h: Decimal, residual_k: Decimal
) -> str:
    margin_h = allowed_h - residual_h
    return (
        f"terminal_h_residual={residual_h} allowed_h={allowed_h} margin_h={margin_h}; "
        f"terminal_k_residual={residual_k} contract_k={TERMINAL_TOLERANCE_K}"
    )


__all__ = [
    "EngineeringErrorBudgetBundle",
    "EngineeringErrorBudgetReport",
    "Task172ErrorBudget",
    "Task173TerminalErrorBudget",
    "build_engineering_error_budget_report",
    "frozen_engineering_error_budgets",
    "quantify_local_residual_budget",
    "quantify_terminal_budget",
]
