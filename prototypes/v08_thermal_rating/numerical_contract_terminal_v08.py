"""Production Task173 terminal gate audit (no tolerance overrides)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _MeshRun,
    _terminal_tolerance_pass,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_inlet_temperature_k,
)


@dataclass(frozen=True)
class ProductionTerminalGateAudit:
    terminal_residual_k: str
    terminal_residual_j_kg: str
    terminal_allowed_k: str
    terminal_allowed_j_kg: str
    terminal_temperature_gate: Literal["PASS", "BLOCKED"]
    terminal_enthalpy_gate: Literal["PASS", "BLOCKED"]
    production_terminal_pass: bool
    cp_j_kg_k: str
    binary64_enthalpy_ulp: str
    binary64_temperature_ulp: str


def production_terminal_gate_audit(run: _MeshRun) -> ProductionTerminalGateAudit:
    """Mirror production ``_terminal_tolerance_pass`` thresholds and split T/H gates."""
    residual_t = run.observables.terminal_boundary_residual_k
    residual_h = run.observables.terminal_boundary_residual_j_kg
    cp = Decimal(run.faces_shell[-1].property_snapshot.cp_j_kg_k)
    cold_h = effective_shell_cold_inlet_enthalpy_j_kg()
    h_floor = Decimal(str(math.ulp(float(cold_h))))
    shell_inlet_t = effective_shell_inlet_temperature_k()
    t_floor = Decimal(str(math.ulp(float(shell_inlet_t + residual_t))))
    allowed_t = TERMINAL_TOLERANCE_K + t_floor
    allowed_h = cp * TERMINAL_TOLERANCE_K + h_floor
    t_ok = Decimal(0) <= residual_t <= allowed_t
    h_ok = Decimal(0) <= residual_h <= allowed_h
    return ProductionTerminalGateAudit(
        terminal_residual_k=str(residual_t),
        terminal_residual_j_kg=str(residual_h),
        terminal_allowed_k=str(allowed_t),
        terminal_allowed_j_kg=str(allowed_h),
        terminal_temperature_gate="PASS" if t_ok else "BLOCKED",
        terminal_enthalpy_gate="PASS" if h_ok else "BLOCKED",
        production_terminal_pass=_terminal_tolerance_pass(run),
        cp_j_kg_k=str(cp),
        binary64_enthalpy_ulp=str(h_floor),
        binary64_temperature_ulp=str(t_floor),
    )


__all__ = ["ProductionTerminalGateAudit", "production_terminal_gate_audit"]
