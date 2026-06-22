"""Single-phase sensible heat-balance and specification-closure kernel.

v0.1 scope: single-phase sensible heat only.  Phase change, two-phase,
and mixed-phase transitions are explicitly rejected.

Energy convention
-----------------
- Duty *Q* is positive from hot stream to cold stream.
- ``Q_hot = m_hot × (h_hot,in − h_hot,out)``  (hot-side enthalpy decrease)
- ``Q_cold = m_cold × (h_cold,out − h_cold,in)``  (cold-side enthalpy increase)
- Residual ``R = Q_hot − Q_cold``.
- Relative imbalance ``|R| / max(Q_hot, Q_cold)`` when Q > 0;
  zero-duty cases are handled separately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, model_validator
from scipy.optimize import brentq

from hexagent.core.canonical import sha256_digest
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    PhaseRegion,
    PropertyProvider,
)
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# ---------------------------------------------------------------------------
# Specification modes
# ---------------------------------------------------------------------------


class SpecificationMode(StrEnum):
    """Explicit enumeration of supported specification combinations.

    The classifier returns one of these modes; under/over-specified
    combinations produce structured errors rather than being silently
    inferred.
    """

    KNOWN_DUTY = "known_duty"
    """Duty known; both outlet temperatures solved independently."""

    KNOWN_HOT_OUTLET = "known_hot_outlet"
    """Hot-side outlet temperature known; duty and cold outlet solved."""

    KNOWN_COLD_OUTLET = "known_cold_outlet"
    """Cold-side outlet temperature known; duty and hot outlet solved."""

    BOTH_OUTLETS_KNOWN = "both_outlets_known"
    """Both outlet temperatures known; energy balance verified."""

    UNDER_SPECIFIED = "under_specified"
    """Insufficient information to solve."""

    OVER_SPECIFIED = "over_specified"
    """Conflicting or redundant specification."""


# ---------------------------------------------------------------------------
# Solver parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverParams:
    """Control parameters for the bounded root-finding solver.

    ``temperature_tolerance``: absolute temperature tolerance in K for
    convergence and near-equality checks.

    ``energy_tolerance``: maximum allowed relative energy imbalance
    (dimensionless).  Results above this threshold are flagged.

    ``max_iterations``: maximum number of function evaluations per
    root-finding call.
    """

    temperature_tolerance: float = 1e-4
    energy_tolerance: float = 1e-3
    max_iterations: int = 100


# ---------------------------------------------------------------------------
# Stream state (input to the kernel)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamState:
    """Minimal stream state for the heat-balance kernel.

    Only the fields needed for energy balance are included.  The full
    ``FluidState`` objects are obtained from the property provider.
    """

    fluid_identifier: FluidIdentifier
    mass_flow_kg_s: float
    inlet_temperature_k: float
    inlet_pressure_pa: float
    outlet_temperature_k: float | None = None

    def __post_init__(self) -> None:
        if self.mass_flow_kg_s <= 0:
            raise ValueError(f"Mass flow must be > 0, got {self.mass_flow_kg_s}")
        if self.inlet_temperature_k <= 0:
            raise ValueError(f"Inlet temperature must be > 0 K, got {self.inlet_temperature_k}")
        if self.inlet_pressure_pa <= 0:
            raise ValueError(f"Inlet pressure must be > 0 Pa, got {self.inlet_pressure_pa}")
        if self.outlet_temperature_k is not None and self.outlet_temperature_k <= 0:
            raise ValueError(f"Outlet temperature must be > 0 K, got {self.outlet_temperature_k}")


# ---------------------------------------------------------------------------
# Property call record (for provenance)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyCallRecord:
    """Traceable record of a single property-provider call."""

    fluid: str
    query_type: str
    inputs: tuple[tuple[str, float], ...]
    backend_name: str
    backend_version: str
    result_temperature_k: float | None = None
    result_pressure_pa: float | None = None


# ---------------------------------------------------------------------------
# Heat-balance input
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeatBalanceInput:
    """Complete input specification for the heat-balance kernel.

    Exactly one of ``known_duty_w`` or an outlet temperature must be
    provided.  Under/over-specified combinations are detected by the
    classifier and returned as structured errors.
    """

    hot: StreamState
    cold: StreamState
    known_duty_w: float | None = None
    solver_params: SolverParams = field(default_factory=SolverParams)

    def __post_init__(self) -> None:
        if self.known_duty_w is not None and self.known_duty_w < 0:
            raise ValueError(f"Duty must be >= 0, got {self.known_duty_w}")


# ---------------------------------------------------------------------------
# Heat-balance result (immutable, hashable)
# ---------------------------------------------------------------------------


class HeatBalanceResult(BaseModel):
    """Immutable result of a heat-balance calculation.

    Contains solved states, energy residual, solver diagnostics,
    property call trace, warnings, blockers, deterministic hash, and
    provenance graph.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    specification_mode: SpecificationMode
    duty_w: float
    hot_inlet_state: dict[str, Any]
    hot_outlet_state: dict[str, Any]
    cold_inlet_state: dict[str, Any]
    cold_outlet_state: dict[str, Any]
    residual_w: float
    relative_imbalance: float
    solver_iterations: int
    solver_converged: bool
    property_calls: tuple[dict[str, Any], ...]
    warnings: tuple[dict[str, Any], ...]
    blockers: tuple[dict[str, Any], ...]
    result_hash: str
    provenance_graph: ProvenanceGraph

    @model_validator(mode="after")
    def _validate_no_nan_inf(self) -> HeatBalanceResult:
        """Reject NaN and Infinity in all float fields."""
        for name in ("duty_w", "residual_w", "relative_imbalance"):
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        return self

    @model_validator(mode="after")
    def _validate_result_hash(self) -> HeatBalanceResult:
        """Verify result_hash starts with sha256: and is 71 chars."""
        if not self.result_hash.startswith("sha256:"):
            raise ValueError(f"result_hash must start with 'sha256:', got {self.result_hash!r}")
        hex_part = self.result_hash[7:]
        if len(hex_part) != 64:
            raise ValueError(f"result_hash hex must be 64 chars, got {len(hex_part)}")
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError(f"result_hash contains invalid hex: {self.result_hash!r}") from None
        return self


# ---------------------------------------------------------------------------
# Specification classifier
# ---------------------------------------------------------------------------


def classify_specification(inp: HeatBalanceInput) -> SpecificationMode:
    """Classify the specification mode from the input.

    Returns the appropriate ``SpecificationMode`` or raises a structured
    error for under/over-specified cases.
    """
    hot_outlet_known = inp.hot.outlet_temperature_k is not None
    cold_outlet_known = inp.cold.outlet_temperature_k is not None
    duty_known = inp.known_duty_w is not None

    if hot_outlet_known and cold_outlet_known and duty_known:
        return SpecificationMode.OVER_SPECIFIED

    if not hot_outlet_known and not cold_outlet_known and not duty_known:
        return SpecificationMode.UNDER_SPECIFIED

    if duty_known and not hot_outlet_known and not cold_outlet_known:
        return SpecificationMode.KNOWN_DUTY

    if hot_outlet_known and not cold_outlet_known and not duty_known:
        return SpecificationMode.KNOWN_HOT_OUTLET

    if not hot_outlet_known and cold_outlet_known and not duty_known:
        return SpecificationMode.KNOWN_COLD_OUTLET

    if hot_outlet_known and cold_outlet_known and not duty_known:
        return SpecificationMode.BOTH_OUTLETS_KNOWN

    # One outlet + duty known → ONE_SIDE_FULLY_KNOWN
    # We handle this by computing duty from the known outlet and solving
    # the other.  But first we must verify consistency.
    if hot_outlet_known and duty_known:
        return SpecificationMode.KNOWN_HOT_OUTLET  # will verify duty consistency

    if cold_outlet_known and duty_known:
        return SpecificationMode.KNOWN_COLD_OUTLET  # will verify duty consistency

    # Should never reach here
    return SpecificationMode.UNDER_SPECIFIED


# ---------------------------------------------------------------------------
# Phase-change detection
# ---------------------------------------------------------------------------


def _check_single_phase(state: FluidState, label: str) -> EngineeringMessage | None:
    """Return a blocker if the state is not single-phase."""
    two_phase = {
        PhaseRegion.SATURATED_LIQUID,
        PhaseRegion.SATURATED_VAPOR,
        PhaseRegion.UNKNOWN,
    }
    if state.phase in two_phase:
        return EngineeringMessage(
            code=ErrorCode.UNSUPPORTED_SERVICE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"{label} state is in phase region '{state.phase.value}'; "
                "phase-change heat balance is not implemented in v0.1."
            ),
            source_module="heat_balance",
        )
    return None


# ---------------------------------------------------------------------------
# Temperature feasibility checks
# ---------------------------------------------------------------------------


def _check_temperature_feasibility(
    hot_inlet_k: float,
    hot_outlet_k: float,
    cold_inlet_k: float,
    cold_outlet_k: float,
    duty_w: float,
    tol: float,
) -> list[EngineeringMessage]:
    """Check temperature feasibility rules.

    Returns a list of warning or blocker messages.
    """
    messages: list[EngineeringMessage] = []

    if duty_w > 0:
        # Hot outlet must not exceed hot inlet
        if hot_outlet_k > hot_inlet_k + tol:
            messages.append(
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Hot outlet temperature ({hot_outlet_k:.4f} K) exceeds "
                        f"hot inlet ({hot_inlet_k:.4f} K) for positive duty."
                    ),
                    source_module="heat_balance",
                )
            )
        # Cold outlet must not be below cold inlet
        if cold_outlet_k < cold_inlet_k - tol:
            messages.append(
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Cold outlet temperature ({cold_outlet_k:.4f} K) is below "
                        f"cold inlet ({cold_inlet_k:.4f} K) for positive duty."
                    ),
                    source_module="heat_balance",
                )
            )

    # Temperature cross check: hot outlet should be above cold outlet
    # for a valid counter/parallel flow arrangement
    if hot_outlet_k < cold_outlet_k - tol:
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message=(
                    f"Temperature cross detected: hot outlet ({hot_outlet_k:.4f} K) "
                    f"< cold outlet ({cold_outlet_k:.4f} K)."
                ),
                source_module="heat_balance",
            )
        )

    # Terminal approach (minimum approach temperature)
    # For counterflow: min approach = min(T_hot_in - T_cold_out, T_hot_out - T_cold_in)
    min_approach = min(
        hot_inlet_k - cold_outlet_k,
        hot_outlet_k - cold_inlet_k,
    )
    if min_approach < -tol:
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message=(f"Non-positive minimum approach temperature: {min_approach:.4f} K."),
                source_module="heat_balance",
            )
        )
    elif abs(min_approach) < tol:
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message=(f"Minimum approach temperature is near zero: {min_approach:.6f} K."),
                source_module="heat_balance",
            )
        )

    return messages


# ---------------------------------------------------------------------------
# Energy balance evaluation
# ---------------------------------------------------------------------------


def _compute_duty_from_hot(
    hot_inlet: FluidState,
    hot_outlet: FluidState,
    mass_flow_hot: float,
) -> float:
    """Q_hot = m_hot * (h_hot_in - h_hot_out)."""
    return mass_flow_hot * (hot_inlet.enthalpy_j_kg - hot_outlet.enthalpy_j_kg)


def _compute_duty_from_cold(
    cold_inlet: FluidState,
    cold_outlet: FluidState,
    mass_flow_cold: float,
) -> float:
    """Q_cold = m_cold * (h_cold_out - h_cold_in)."""
    return mass_flow_cold * (cold_outlet.enthalpy_j_kg - cold_inlet.enthalpy_j_kg)


# ---------------------------------------------------------------------------
# Root-finding for unknown outlet temperature
# ---------------------------------------------------------------------------


def _solve_outlet_temperature(
    provider: PropertyProvider,
    fluid: FluidIdentifier,
    inlet_state: FluidState,
    mass_flow: float,
    known_duty_w: float,
    *,
    is_hot_side: bool,
    solver_params: SolverParams,
    property_calls: list[PropertyCallRecord],
) -> tuple[FluidState, int]:
    """Solve for the unknown outlet temperature using Brent's method.

    For the hot side: Q = m * (h_in - h_out) → h_out = h_in - Q/m
    For the cold side: Q = m * (h_out - h_in) → h_out = h_in + Q/m

    We search for T such that h(T, P) = target_h.

    The search bracket is built dynamically starting from the inlet
    temperature and probing outward in 10 K steps until a sign change
    is found.  This avoids hard-coded bounds that may fall outside the
    fluid's valid property range.

    Returns (outlet_state, iterations_used).
    """
    target_h: float
    if is_hot_side:
        target_h = inlet_state.enthalpy_j_kg - known_duty_w / mass_flow
    else:
        target_h = inlet_state.enthalpy_j_kg + known_duty_w / mass_flow

    pressure_pa = inlet_state.pressure_pa
    t_inlet = inlet_state.temperature_k

    iterations = [0]
    call_records: list[PropertyCallRecord] = []

    def _eval_tp(t: float) -> FluidState:
        state = provider.state_tp(fluid, t, pressure_pa)
        call_records.append(
            PropertyCallRecord(
                fluid=str(fluid),
                query_type="TP",
                inputs=(("temperature_k", t), ("pressure_pa", pressure_pa)),
                backend_name=provider.name,
                backend_version=provider.version,
                result_temperature_k=t,
                result_pressure_pa=pressure_pa,
            )
        )
        return state

    def residual(t: float) -> float:
        iterations[0] += 1
        if iterations[0] > solver_params.max_iterations * 3:
            raise RuntimeError(
                f"Solver exceeded max iterations ({solver_params.max_iterations * 3})"
            )
        try:
            state = _eval_tp(t)
        except PropertyServiceError:
            # Return a large value to guide brentq away from invalid regions
            if is_hot_side:
                return 1e12  # "h is too high" → go lower
            else:
                return -1e12  # "h is too low" → go higher
        return state.enthalpy_j_kg - target_h

    # --- Build bracket by probing outward from inlet ---
    # For hot side: T_out < T_inlet → probe downward
    # For cold side: T_out > T_inlet → probe upward
    step = 10.0  # K per probe step
    max_steps = 30  # up to 300 K from inlet

    if is_hot_side:
        # Upper bound is just below inlet (where h > target_h for positive Q)
        t_upper = t_inlet - solver_params.temperature_tolerance
        # Probe downward to find lower bound (where h < target_h)
        t_lower = t_inlet - step
        f_upper = None
        f_lower = None
        for _ in range(max_steps):
            try:
                f_upper = residual(t_upper)
            except (PropertyServiceError, RuntimeError):
                t_upper -= step
                continue
            try:
                f_lower = residual(t_lower)
            except (PropertyServiceError, RuntimeError):
                t_lower -= step
                continue
            if f_upper * f_lower <= 0:
                break
            # Both same sign — keep probing down
            t_upper = t_lower
            t_lower -= step
        else:
            raise RuntimeError(
                f"Could not find valid bracket for hot-side outlet. "
                f"Target enthalpy={target_h:.2f} J/kg, "
                f"inlet T={t_inlet:.2f} K."
            )
    else:
        # Lower bound is just above inlet (where h < target_h for positive Q)
        t_lower = t_inlet + solver_params.temperature_tolerance
        # Probe upward to find upper bound (where h > target_h)
        t_upper = t_inlet + step
        f_lower = None
        f_upper = None
        for _ in range(max_steps):
            try:
                f_lower = residual(t_lower)
            except (PropertyServiceError, RuntimeError):
                t_lower += step
                continue
            try:
                f_upper = residual(t_upper)
            except (PropertyServiceError, RuntimeError):
                t_upper += step
                continue
            if f_lower * f_upper <= 0:
                break
            # Both same sign — keep probing up
            t_lower = t_upper
            t_upper += step
        else:
            raise RuntimeError(
                f"Could not find valid bracket for cold-side outlet. "
                f"Target enthalpy={target_h:.2f} J/kg, "
                f"inlet T={t_inlet:.2f} K."
            )

    # --- Solve with brentq ---
    try:
        t_solution = brentq(
            residual,
            t_lower,
            t_upper,
            xtol=solver_params.temperature_tolerance,
            maxiter=solver_params.max_iterations,
        )
    except ValueError as exc:
        raise RuntimeError(
            f"Root-finding failed: {exc}. Target enthalpy={target_h:.2f} J/kg, "
            f"bracket=[{t_lower:.2f}, {t_upper:.2f}] K."
        ) from exc

    # Get the final state at the solved temperature
    outlet_state = _eval_tp(t_solution)

    property_calls.extend(call_records)
    return outlet_state, iterations[0]


# ---------------------------------------------------------------------------
# Canonical serialization for hashing
# ---------------------------------------------------------------------------


def _state_to_dict(state: FluidState) -> dict[str, Any]:
    """Convert FluidState to a canonical dict for hashing."""
    return {
        "temperature_k": state.temperature_k,
        "pressure_pa": state.pressure_pa,
        "density_kg_m3": state.density_kg_m3,
        "cp_j_kg_k": state.cp_j_kg_k,
        "enthalpy_j_kg": state.enthalpy_j_kg,
        "entropy_j_kg_k": state.entropy_j_kg_k,
        "phase": state.phase.value,
    }


def _compute_result_hash(
    specification_mode: SpecificationMode,
    hot_inlet: FluidState,
    hot_outlet: FluidState,
    cold_inlet: FluidState,
    cold_outlet: FluidState,
    duty_w: float,
    residual_w: float,
    relative_imbalance: float,
    software_version: str,
) -> str:
    """Compute deterministic SHA-256 hash of the result."""
    payload = {
        "specification_mode": specification_mode.value,
        "hot_inlet": _state_to_dict(hot_inlet),
        "hot_outlet": _state_to_dict(hot_outlet),
        "cold_inlet": _state_to_dict(cold_inlet),
        "cold_outlet": _state_to_dict(cold_outlet),
        "duty_w": duty_w,
        "residual_w": residual_w,
        "relative_imbalance": relative_imbalance,
        "software_version": software_version,
    }
    return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Provenance graph construction
# ---------------------------------------------------------------------------

_SOFTWARE_VERSION = "0.1.0"


def _build_provenance(
    case_revision_id: UUID,
    specification_mode: SpecificationMode,
    property_calls: list[PropertyCallRecord],
    solver_iterations: int,
    solver_converged: bool,
    warnings: list[EngineeringMessage],
    blockers: list[EngineeringMessage],
    result_hash: str,
) -> ProvenanceGraph:
    """Build a provenance graph for the heat-balance calculation."""
    nodes: list[ProvenanceNode] = []
    edges: list[ProvenanceEdge] = []

    # Case revision node
    case_rev_id = uuid4()
    nodes.append(
        ProvenanceNode(
            node_id=case_rev_id,
            node_type=ProvenanceNodeType.CASE_REVISION,
            label="case_revision",
            metadata=(("revision_id", str(case_revision_id)),),
            payload_hash=sha256_digest({"revision_id": str(case_revision_id)}),
        )
    )

    # Calculation run node
    calc_run_id = uuid4()
    nodes.append(
        ProvenanceNode(
            node_id=calc_run_id,
            node_type=ProvenanceNodeType.CALCULATION_RUN,
            label="heat_balance_run",
            metadata=(
                ("specification_mode", specification_mode.value),
                ("solver_iterations", solver_iterations),
                ("solver_converged", solver_converged),
                ("software_version", _SOFTWARE_VERSION),
            ),
            payload_hash=sha256_digest(
                {
                    "specification_mode": specification_mode.value,
                    "solver_iterations": solver_iterations,
                    "solver_converged": solver_converged,
                }
            ),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=case_rev_id,
            target_id=calc_run_id,
            relation="triggers",
        )
    )

    # Property call nodes
    for pc in property_calls:
        prop_id = uuid4()
        nodes.append(
            ProvenanceNode(
                node_id=prop_id,
                node_type=ProvenanceNodeType.PROPERTY_CALL,
                label=f"property_{pc.fluid}_{pc.query_type}",
                metadata=(
                    ("fluid", pc.fluid),
                    ("query_type", pc.query_type),
                    ("backend_name", pc.backend_name),
                    ("backend_version", pc.backend_version),
                ),
                payload_hash=sha256_digest(
                    {
                        "fluid": pc.fluid,
                        "query_type": pc.query_type,
                        "inputs": dict(pc.inputs),
                    }
                ),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_run_id,
                target_id=prop_id,
                relation="calls",
            )
        )

    # Result node
    result_id = uuid4()
    nodes.append(
        ProvenanceNode(
            node_id=result_id,
            node_type=ProvenanceNodeType.RESULT,
            label="heat_balance_result",
            metadata=(("result_hash", result_hash),),
            payload_hash=sha256_digest({"result_hash": result_hash}),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=calc_run_id,
            target_id=result_id,
            relation="produces",
        )
    )

    # Warning nodes
    for w in warnings:
        warn_id = uuid4()
        nodes.append(
            ProvenanceNode(
                node_id=warn_id,
                node_type=ProvenanceNodeType.WARNING,
                label=f"warning_{w.code.value}",
                metadata=(
                    ("code", w.code.value),
                    ("severity", w.severity.value),
                    ("message", w.message),
                ),
                payload_hash=sha256_digest(
                    {
                        "code": w.code.value,
                        "message": w.message,
                    }
                ),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_run_id,
                target_id=warn_id,
                relation="emits",
            )
        )

    # Blocker nodes
    for b in blockers:
        block_id = uuid4()
        nodes.append(
            ProvenanceNode(
                node_id=block_id,
                node_type=ProvenanceNodeType.BLOCKER,
                label=f"blocker_{b.code.value}",
                metadata=(
                    ("code", b.code.value),
                    ("severity", b.severity.value),
                    ("message", b.message),
                ),
                payload_hash=sha256_digest(
                    {
                        "code": b.code.value,
                        "message": b.message,
                    }
                ),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_run_id,
                target_id=block_id,
                relation="emits",
            )
        )

    return ProvenanceGraph(
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


# ---------------------------------------------------------------------------
# Zero-duty handling
# ---------------------------------------------------------------------------


def _handle_zero_duty(
    inp: HeatBalanceInput,
    provider: PropertyProvider,
    hot_inlet_state: FluidState,
    cold_inlet_state: FluidState,
) -> HeatBalanceResult:
    """Handle the zero-duty case explicitly.

    When Q = 0, outlet temperatures must equal inlet temperatures
    (no heat transfer).
    """
    property_calls: list[PropertyCallRecord] = []
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []

    # Record the inlet property calls
    property_calls.append(
        PropertyCallRecord(
            fluid=str(inp.hot.fluid_identifier),
            query_type="TP",
            inputs=(
                ("temperature_k", inp.hot.inlet_temperature_k),
                ("pressure_pa", inp.hot.inlet_pressure_pa),
            ),
            backend_name=provider.name,
            backend_version=provider.version,
            result_temperature_k=inp.hot.inlet_temperature_k,
            result_pressure_pa=inp.hot.inlet_pressure_pa,
        )
    )
    property_calls.append(
        PropertyCallRecord(
            fluid=str(inp.cold.fluid_identifier),
            query_type="TP",
            inputs=(
                ("temperature_k", inp.cold.inlet_temperature_k),
                ("pressure_pa", inp.cold.inlet_pressure_pa),
            ),
            backend_name=provider.name,
            backend_version=provider.version,
            result_temperature_k=inp.cold.inlet_temperature_k,
            result_pressure_pa=inp.cold.inlet_pressure_pa,
        )
    )

    # For zero duty, outlet = inlet
    hot_outlet_state = hot_inlet_state
    cold_outlet_state = cold_inlet_state

    property_calls.append(
        PropertyCallRecord(
            fluid=str(inp.hot.fluid_identifier),
            query_type="TP",
            inputs=(
                ("temperature_k", hot_outlet_state.temperature_k),
                ("pressure_pa", hot_outlet_state.pressure_pa),
            ),
            backend_name=provider.name,
            backend_version=provider.version,
            result_temperature_k=hot_outlet_state.temperature_k,
            result_pressure_pa=hot_outlet_state.pressure_pa,
        )
    )
    property_calls.append(
        PropertyCallRecord(
            fluid=str(inp.cold.fluid_identifier),
            query_type="TP",
            inputs=(
                ("temperature_k", cold_outlet_state.temperature_k),
                ("pressure_pa", cold_outlet_state.pressure_pa),
            ),
            backend_name=provider.name,
            backend_version=provider.version,
            result_temperature_k=cold_outlet_state.temperature_k,
            result_pressure_pa=cold_outlet_state.pressure_pa,
        )
    )

    residual_w = 0.0
    relative_imbalance = 0.0

    result_hash = _compute_result_hash(
        SpecificationMode.KNOWN_DUTY,
        hot_inlet_state,
        hot_outlet_state,
        cold_inlet_state,
        cold_outlet_state,
        0.0,
        residual_w,
        relative_imbalance,
        _SOFTWARE_VERSION,
    )

    provenance = _build_provenance(
        case_revision_id=uuid4(),
        specification_mode=SpecificationMode.KNOWN_DUTY,
        property_calls=property_calls,
        solver_iterations=0,
        solver_converged=True,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
    )

    return HeatBalanceResult(
        specification_mode=SpecificationMode.KNOWN_DUTY,
        duty_w=0.0,
        hot_inlet_state=_state_to_dict(hot_inlet_state),
        hot_outlet_state=_state_to_dict(hot_outlet_state),
        cold_inlet_state=_state_to_dict(cold_inlet_state),
        cold_outlet_state=_state_to_dict(cold_outlet_state),
        residual_w=residual_w,
        relative_imbalance=relative_imbalance,
        solver_iterations=0,
        solver_converged=True,
        property_calls=tuple(_pc_to_dict(pc) for pc in property_calls),
        warnings=tuple(_msg_to_dict(m) for m in warnings),
        blockers=tuple(_msg_to_dict(m) for m in blockers),
        result_hash=result_hash,
        provenance_graph=provenance,
    )


def _pc_to_dict(pc: PropertyCallRecord) -> dict[str, Any]:
    return {
        "fluid": pc.fluid,
        "query_type": pc.query_type,
        "inputs": dict(pc.inputs),
        "backend_name": pc.backend_name,
        "backend_version": pc.backend_version,
        "result_temperature_k": pc.result_temperature_k,
        "result_pressure_pa": pc.result_pressure_pa,
    }


def _msg_to_dict(msg: EngineeringMessage) -> dict[str, Any]:
    return {
        "code": msg.code.value,
        "severity": msg.severity.value,
        "message": msg.message,
        "source_module": msg.source_module,
    }


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------


def solve_heat_balance(inp: HeatBalanceInput, provider: PropertyProvider) -> HeatBalanceResult:
    """Solve the single-phase sensible heat balance.

    This is the main entry point for the heat-balance kernel.  It:
    1. Validates inputs (zero/negative flow, zero duty).
    2. Classifies the specification mode.
    3. Evaluates inlet states via the property provider.
    4. Checks for phase change (rejects two-phase).
    5. Solves for unknowns using bounded root-finding.
    6. Checks temperature feasibility.
    7. Computes energy residual and relative imbalance.
    8. Builds provenance graph and deterministic result hash.

    Parameters
    ----------
    inp : HeatBalanceInput
        Complete input specification.
    provider : PropertyProvider
        Property provider for thermodynamic state evaluation.

    Returns
    -------
    HeatBalanceResult
        Immutable result with solved states, diagnostics, and provenance.

    Raises
    ------
    ValueError
        For under/over-specified inputs, zero/negative flow, or
        property-provider failures.
    """
    # --- Input validation ---
    if inp.hot.mass_flow_kg_s <= 0:
        raise ValueError(f"Hot-side mass flow must be > 0, got {inp.hot.mass_flow_kg_s}")
    if inp.cold.mass_flow_kg_s <= 0:
        raise ValueError(f"Cold-side mass flow must be > 0, got {inp.cold.mass_flow_kg_s}")

    # --- Classify specification ---
    mode = classify_specification(inp)

    if mode == SpecificationMode.UNDER_SPECIFIED:
        raise ValueError("Under-specified: provide duty or at least one outlet temperature.")
    if mode == SpecificationMode.OVER_SPECIFIED:
        raise ValueError("Over-specified: duty and both outlets cannot all be provided.")

    # --- Evaluate inlet states ---
    property_calls: list[PropertyCallRecord] = []
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []

    try:
        hot_inlet_state = provider.state_tp(
            inp.hot.fluid_identifier,
            inp.hot.inlet_temperature_k,
            inp.hot.inlet_pressure_pa,
        )
    except PropertyServiceError as exc:
        blockers.append(
            EngineeringMessage(
                code=_property_error_to_code(exc),
                severity=EngineeringMessageSeverity.BLOCKER,
                message=f"Hot-side inlet property evaluation failed: {exc}",
                source_module="heat_balance",
                context=(("error", str(exc)),),
            )
        )
        raise ValueError(str(exc)) from exc

    property_calls.append(
        PropertyCallRecord(
            fluid=str(inp.hot.fluid_identifier),
            query_type="TP",
            inputs=(
                ("temperature_k", inp.hot.inlet_temperature_k),
                ("pressure_pa", inp.hot.inlet_pressure_pa),
            ),
            backend_name=provider.name,
            backend_version=provider.version,
            result_temperature_k=hot_inlet_state.temperature_k,
            result_pressure_pa=hot_inlet_state.pressure_pa,
        )
    )

    try:
        cold_inlet_state = provider.state_tp(
            inp.cold.fluid_identifier,
            inp.cold.inlet_temperature_k,
            inp.cold.inlet_pressure_pa,
        )
    except PropertyServiceError as exc:
        blockers.append(
            EngineeringMessage(
                code=_property_error_to_code(exc),
                severity=EngineeringMessageSeverity.BLOCKER,
                message=f"Cold-side inlet property evaluation failed: {exc}",
                source_module="heat_balance",
                context=(("error", str(exc)),),
            )
        )
        raise ValueError(str(exc)) from exc

    property_calls.append(
        PropertyCallRecord(
            fluid=str(inp.cold.fluid_identifier),
            query_type="TP",
            inputs=(
                ("temperature_k", inp.cold.inlet_temperature_k),
                ("pressure_pa", inp.cold.inlet_pressure_pa),
            ),
            backend_name=provider.name,
            backend_version=provider.version,
            result_temperature_k=cold_inlet_state.temperature_k,
            result_pressure_pa=cold_inlet_state.pressure_pa,
        )
    )

    # --- Phase check on inlets ---
    phase_msg = _check_single_phase(hot_inlet_state, "Hot-side inlet")
    if phase_msg is not None:
        blockers.append(phase_msg)
        raise ValueError(phase_msg.message)

    phase_msg = _check_single_phase(cold_inlet_state, "Cold-side inlet")
    if phase_msg is not None:
        blockers.append(phase_msg)
        raise ValueError(phase_msg.message)

    # --- Handle zero duty ---
    if inp.known_duty_w is not None and inp.known_duty_w == 0.0:
        return _handle_zero_duty(inp, provider, hot_inlet_state, cold_inlet_state)

    # --- Solve based on specification mode ---
    total_iterations = 0

    if mode == SpecificationMode.KNOWN_DUTY:
        # Solve both outlets independently
        hot_outlet_state, iters_hot = _solve_outlet_temperature(
            provider,
            inp.hot.fluid_identifier,
            hot_inlet_state,
            inp.hot.mass_flow_kg_s,
            inp.known_duty_w,  # type: ignore[arg-type]
            is_hot_side=True,
            solver_params=inp.solver_params,
            property_calls=property_calls,
        )
        cold_outlet_state, iters_cold = _solve_outlet_temperature(
            provider,
            inp.cold.fluid_identifier,
            cold_inlet_state,
            inp.cold.mass_flow_kg_s,
            inp.known_duty_w,  # type: ignore[arg-type]
            is_hot_side=False,
            solver_params=inp.solver_params,
            property_calls=property_calls,
        )
        total_iterations = iters_hot + iters_cold
        assert inp.known_duty_w is not None
        duty_w = inp.known_duty_w
    elif mode == SpecificationMode.KNOWN_HOT_OUTLET:
        # Hot outlet known → compute duty from hot side
        try:
            hot_outlet_state = provider.state_tp(
                inp.hot.fluid_identifier,
                inp.hot.outlet_temperature_k,  # type: ignore[arg-type]
                inp.hot.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            raise ValueError(str(exc)) from exc

        property_calls.append(
            PropertyCallRecord(
                fluid=str(inp.hot.fluid_identifier),
                query_type="TP",
                inputs=(
                    ("temperature_k", inp.hot.outlet_temperature_k),  # type: ignore[arg-type]
                    ("pressure_pa", inp.hot.inlet_pressure_pa),
                ),
                backend_name=provider.name,
                backend_version=provider.version,
                result_temperature_k=hot_outlet_state.temperature_k,
                result_pressure_pa=hot_outlet_state.pressure_pa,
            )
        )

        phase_msg = _check_single_phase(hot_outlet_state, "Hot-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            raise ValueError(phase_msg.message)

        duty_w = _compute_duty_from_hot(hot_inlet_state, hot_outlet_state, inp.hot.mass_flow_kg_s)

        if duty_w < 0:
            raise ValueError(
                f"Computed duty is negative ({duty_w:.2f} W): hot outlet "
                f"temperature ({inp.hot.outlet_temperature_k} K) is above "
                f"hot inlet ({inp.hot.inlet_temperature_k} K)."
            )

        # Verify duty if also provided
        if inp.known_duty_w is not None:
            duty_diff = abs(duty_w - inp.known_duty_w)
            duty_tol = inp.solver_params.energy_tolerance * max(abs(duty_w), 1.0)
            if duty_diff > duty_tol:
                raise ValueError(
                    f"Over-specified: provided duty ({inp.known_duty_w:.2f} W) "
                    f"inconsistent with computed duty ({duty_w:.2f} W)."
                )

        # Solve cold outlet
        cold_outlet_state, iters_cold = _solve_outlet_temperature(
            provider,
            inp.cold.fluid_identifier,
            cold_inlet_state,
            inp.cold.mass_flow_kg_s,
            duty_w,
            is_hot_side=False,
            solver_params=inp.solver_params,
            property_calls=property_calls,
        )
        total_iterations = iters_cold

    elif mode == SpecificationMode.KNOWN_COLD_OUTLET:
        # Cold outlet known → compute duty from cold side
        try:
            cold_outlet_state = provider.state_tp(
                inp.cold.fluid_identifier,
                inp.cold.outlet_temperature_k,  # type: ignore[arg-type]
                inp.cold.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            raise ValueError(str(exc)) from exc

        property_calls.append(
            PropertyCallRecord(
                fluid=str(inp.cold.fluid_identifier),
                query_type="TP",
                inputs=(
                    ("temperature_k", inp.cold.outlet_temperature_k),  # type: ignore[arg-type]
                    ("pressure_pa", inp.cold.inlet_pressure_pa),
                ),
                backend_name=provider.name,
                backend_version=provider.version,
                result_temperature_k=cold_outlet_state.temperature_k,
                result_pressure_pa=cold_outlet_state.pressure_pa,
            )
        )

        phase_msg = _check_single_phase(cold_outlet_state, "Cold-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            raise ValueError(phase_msg.message)

        duty_w = _compute_duty_from_cold(
            cold_inlet_state, cold_outlet_state, inp.cold.mass_flow_kg_s
        )

        if duty_w < 0:
            raise ValueError(
                f"Computed duty is negative ({duty_w:.2f} W): cold outlet "
                f"temperature ({inp.cold.outlet_temperature_k} K) is below "
                f"cold inlet ({inp.cold.inlet_temperature_k} K)."
            )

        # Verify duty if also provided
        if inp.known_duty_w is not None:
            duty_diff = abs(duty_w - inp.known_duty_w)
            duty_tol = inp.solver_params.energy_tolerance * max(abs(duty_w), 1.0)
            if duty_diff > duty_tol:
                raise ValueError(
                    f"Over-specified: provided duty ({inp.known_duty_w:.2f} W) "
                    f"inconsistent with computed duty ({duty_w:.2f} W)."
                )

        # Solve hot outlet
        hot_outlet_state, iters_hot = _solve_outlet_temperature(
            provider,
            inp.hot.fluid_identifier,
            hot_inlet_state,
            inp.hot.mass_flow_kg_s,
            duty_w,
            is_hot_side=True,
            solver_params=inp.solver_params,
            property_calls=property_calls,
        )
        total_iterations = iters_hot

    elif mode == SpecificationMode.BOTH_OUTLETS_KNOWN:
        # Both outlets known → verify energy balance
        try:
            hot_outlet_state = provider.state_tp(
                inp.hot.fluid_identifier,
                inp.hot.outlet_temperature_k,  # type: ignore[arg-type]
                inp.hot.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            raise ValueError(str(exc)) from exc

        property_calls.append(
            PropertyCallRecord(
                fluid=str(inp.hot.fluid_identifier),
                query_type="TP",
                inputs=(
                    ("temperature_k", inp.hot.outlet_temperature_k),  # type: ignore[arg-type]
                    ("pressure_pa", inp.hot.inlet_pressure_pa),
                ),
                backend_name=provider.name,
                backend_version=provider.version,
                result_temperature_k=hot_outlet_state.temperature_k,
                result_pressure_pa=hot_outlet_state.pressure_pa,
            )
        )

        phase_msg = _check_single_phase(hot_outlet_state, "Hot-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            raise ValueError(phase_msg.message)

        try:
            cold_outlet_state = provider.state_tp(
                inp.cold.fluid_identifier,
                inp.cold.outlet_temperature_k,  # type: ignore[arg-type]
                inp.cold.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            raise ValueError(str(exc)) from exc

        property_calls.append(
            PropertyCallRecord(
                fluid=str(inp.cold.fluid_identifier),
                query_type="TP",
                inputs=(
                    ("temperature_k", inp.cold.outlet_temperature_k),  # type: ignore[arg-type]
                    ("pressure_pa", inp.cold.inlet_pressure_pa),
                ),
                backend_name=provider.name,
                backend_version=provider.version,
                result_temperature_k=cold_outlet_state.temperature_k,
                result_pressure_pa=cold_outlet_state.pressure_pa,
            )
        )

        phase_msg = _check_single_phase(cold_outlet_state, "Cold-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            raise ValueError(phase_msg.message)

        q_hot = _compute_duty_from_hot(hot_inlet_state, hot_outlet_state, inp.hot.mass_flow_kg_s)
        q_cold = _compute_duty_from_cold(
            cold_inlet_state, cold_outlet_state, inp.cold.mass_flow_kg_s
        )
        duty_w = (q_hot + q_cold) / 2.0

    else:
        raise ValueError(f"Unhandled specification mode: {mode}")

    # --- Compute energy residual ---
    q_hot = _compute_duty_from_hot(hot_inlet_state, hot_outlet_state, inp.hot.mass_flow_kg_s)
    q_cold = _compute_duty_from_cold(cold_inlet_state, cold_outlet_state, inp.cold.mass_flow_kg_s)
    residual_w = q_hot - q_cold

    max_q = max(abs(q_hot), abs(q_cold))
    relative_imbalance = abs(residual_w) / max_q if max_q > 0 else 0.0

    solver_converged = relative_imbalance < inp.solver_params.energy_tolerance

    # --- Temperature feasibility checks ---
    tol = inp.solver_params.temperature_tolerance
    feas_msgs = _check_temperature_feasibility(
        hot_inlet_state.temperature_k,
        hot_outlet_state.temperature_k,
        cold_inlet_state.temperature_k,
        cold_outlet_state.temperature_k,
        duty_w,
        tol,
    )
    warnings.extend(feas_msgs)

    # --- Build provenance and hash ---
    result_hash = _compute_result_hash(
        mode,
        hot_inlet_state,
        hot_outlet_state,
        cold_inlet_state,
        cold_outlet_state,
        duty_w,
        residual_w,
        relative_imbalance,
        _SOFTWARE_VERSION,
    )

    provenance = _build_provenance(
        case_revision_id=uuid4(),
        specification_mode=mode,
        property_calls=property_calls,
        solver_iterations=total_iterations,
        solver_converged=solver_converged,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
    )

    return HeatBalanceResult(
        specification_mode=mode,
        duty_w=duty_w,
        hot_inlet_state=_state_to_dict(hot_inlet_state),
        hot_outlet_state=_state_to_dict(hot_outlet_state),
        cold_inlet_state=_state_to_dict(cold_inlet_state),
        cold_outlet_state=_state_to_dict(cold_outlet_state),
        residual_w=residual_w,
        relative_imbalance=relative_imbalance,
        solver_iterations=total_iterations,
        solver_converged=solver_converged,
        property_calls=tuple(_pc_to_dict(pc) for pc in property_calls),
        warnings=tuple(_msg_to_dict(m) for m in warnings),
        blockers=tuple(_msg_to_dict(m) for m in blockers),
        result_hash=result_hash,
        provenance_graph=provenance,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _property_error_to_code(exc: PropertyServiceError) -> ErrorCode:
    """Map PropertyServiceError codes to EngineeringMessage error codes."""
    mapping = {
        PropertyErrorCode.BACKEND_FAILURE: ErrorCode.PROPERTY_UNAVAILABLE,
        PropertyErrorCode.STATE_OUT_OF_RANGE: ErrorCode.PROPERTY_OUT_OF_RANGE,
        PropertyErrorCode.INVALID_FLUID: ErrorCode.INPUT_MISSING,
        PropertyErrorCode.INVALID_INPUT: ErrorCode.INPUT_INCONSISTENT,
        PropertyErrorCode.UNSUPPORTED_BACKEND: ErrorCode.UNSUPPORTED_SERVICE,
        PropertyErrorCode.TWO_PHASE_STATE: ErrorCode.UNSUPPORTED_SERVICE,
    }
    return mapping.get(exc.code, ErrorCode.CALCULATION_BLOCKED)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "HeatBalanceInput",
    "HeatBalanceResult",
    "PropertyCallRecord",
    "SolverParams",
    "SpecificationMode",
    "StreamState",
    "classify_specification",
    "solve_heat_balance",
]
