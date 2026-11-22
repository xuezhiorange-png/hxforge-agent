"""Task173 / V08 autonomous full-path mass-flow binding boundary (experimental prescreen only)."""

from __future__ import annotations

from dataclasses import dataclass

TASK173_MASS_BINDING_ROOT_CAUSE = (
    "V08 run_autonomous_nozzle_full_path builds equipment mass from bindings.normalized "
    "(perturbed case) but hydraulic post-pass and Task174 decomposition are frozen to the "
    "Task168 enumeration bundle (Task026/Task029 at nominal 12/20 kg/s). "
    "Mass-flow sensitivity sweeps raise ValueError/ValidationError in the R27 full-path "
    "bridge when equipment totals diverge from admitted structural hydraulic templates. "
    "Temperature-only sweeps retain nominal mass and may compute high-K prescreen dp."
)

TASK173_EXPERIMENTAL_REPLAY_PROPOSAL = (
    "Wire R19A-style live_thermal_state_hydraulic_postpass with rebinding Task026 to "
    "equipment mass per scenario, or extend CandidateRatingBindings with a fresh Task026 "
    "result before post-pass — requires explicit experimental authority; not permitted "
    "inside production Task173 integrated rating contract or numerical acceptance "
    "tolerances in this task."
)


@dataclass(frozen=True)
class Task173MassBindingBoundaryReport:
    root_cause: str
    experimental_replay_feasible: bool
    production_contract_change_required: bool
    proposal: str
    blocked_scenario_classes: tuple[str, ...]


def task173_mass_binding_boundary_report() -> Task173MassBindingBoundaryReport:
    return Task173MassBindingBoundaryReport(
        root_cause=TASK173_MASS_BINDING_ROOT_CAUSE,
        experimental_replay_feasible=False,
        production_contract_change_required=True,
        proposal=TASK173_EXPERIMENTAL_REPLAY_PROPOSAL,
        blocked_scenario_classes=(
            "tube_mdot_minus_1pct",
            "tube_mdot_minus_3pct",
            "tube_mdot_plus_3pct",
            "shell_mdot_minus_3pct",
            "shell_mdot_plus_3pct",
        ),
    )
