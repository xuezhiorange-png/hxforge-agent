"""Double-pipe heat-exchanger package."""

from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingRequestIdentity, RatingResult, RatingStatus
from hexagent.exchangers.double_pipe.solver import SolverParams, SolverResult, SolverTermination
from hexagent.exchangers.double_pipe.thermal import (
    FlowArrangement,
    ThermalResistanceBreakdown,
    build_thermal_resistance,
    effectiveness_counterflow,
    effectiveness_parallel,
    lmtd_counterflow,
    lmtd_parallel,
)

__all__ = [
    "DoublePipeGeometry",
    "FlowArrangement",
    "RatingRequestIdentity",
    "RatingResult",
    "RatingStatus",
    "SolverParams",
    "SolverResult",
    "SolverTermination",
    "ThermalResistanceBreakdown",
    "build_thermal_resistance",
    "effectiveness_counterflow",
    "effectiveness_parallel",
    "lmtd_counterflow",
    "lmtd_parallel",
    "rate_double_pipe",
]
