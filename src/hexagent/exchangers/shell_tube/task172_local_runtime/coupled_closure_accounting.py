"""Accounting counters for coupled Task172 closure (isolation / audit only)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CoupledClosureAccounting:
    eval_trial_2d_flux: int = 0
    eval_trial_q_ts_search: int = 0
    eval_trial_accept: int = 0
    eval_trial_total: int = 0
    least_squares_reported_nfev: int = 0
    q_ts_lattice_points: int = 0
    q_ts_brent_iterations: int = 0
    q_ts_ulp_neighbors: int = 0
    q_ts_branch_precheck: int = 0
    property_evaluations_estimated: int = 0
    wall_seconds: float = 0.0
    max_residual_ratio: float | None = None
    accepted: bool = False
    failure_code: str | None = None
    solver_status: str | None = None
    callback_cap: int = 0
    callback_used: int = 0
    extras: dict[str, str] = field(default_factory=dict)

    def record_eval(self, phase: str) -> None:
        self.eval_trial_total += 1
        if phase == "2d_flux":
            self.eval_trial_2d_flux += 1
        elif phase == "q_ts":
            self.eval_trial_q_ts_search += 1
        elif phase == "accept":
            self.eval_trial_accept += 1
