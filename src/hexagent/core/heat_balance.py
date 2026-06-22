"""Single-phase sensible heat-balance and specification-closure kernel.

v0.1 scope: single-phase sensible heat only.  Phase change, two-phase,
and mixed-phase transitions are explicitly rejected.

Energy convention
-----------------
- Duty *Q* is positive from hot stream to cold stream.
- ``Q_hot = m_hot × (h_hot,in − h_hot,out)``  (hot-side enthalpy decrease)
- ``Q_cold = m_cold × (h_cold,out − h_cold,in)``  (cold-side enthalpy increase)
- Residual ``R = Q_hot − Q_cold``.
- Relative imbalance ``|R| / max(|Q_hot|, |Q_cold|)`` when
  ``max(|Q_hot|, |Q_cold|) > absolute_duty_threshold``;
  otherwise ``|R|`` (absolute).

Structured failure contract
---------------------------
``solve_heat_balance()`` ALWAYS returns a ``HeatBalanceResult``.  It never
raises for domain errors.  The ``status`` field indicates the outcome:

- ``SUCCEEDED``: solver converged AND energy balance accepted.
- ``BLOCKED``: a structural precondition failed (under/over-specification,
  property failure, phase rejection, temperature infeasibility, energy
  imbalance above tolerance).
- ``FAILED``: the root-finding solver did not converge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, model_validator
from scipy.optimize import brentq

from hexagent.core.canonical import sha256_digest
from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
    RunFailure,
)
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    FluidStateModel,
    PhaseRegion,
    PropertyProvider,
    ReferenceStatePolicy,
)
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

_SOFTWARE_VERSION: str = "0.1.0"

# Module-level UUID5 namespace for deterministic provenance node IDs.
_PROVENANCE_NAMESPACE: UUID = uuid5(
    UUID("00000000-0000-0000-0000-000000000000"),
    "hexagent:heat_balance:provenance",
)

# Absolute duty threshold in watts.  When max(|q_hot|, |q_cold|) is
# below this value, relative imbalance is computed as an absolute
# quantity (no division by near-zero denominator).
_ABSOLUTE_DUTY_THRESHOLD: float = 1.0


# ---------------------------------------------------------------------------
# Phase families
# ---------------------------------------------------------------------------

_LIQUID_FAMILY: frozenset[PhaseRegion] = frozenset(
    {
        PhaseRegion.LIQUID,
        PhaseRegion.SATURATED_LIQUID,
    }
)

_GAS_FAMILY: frozenset[PhaseRegion] = frozenset(
    {
        PhaseRegion.GAS,
        PhaseRegion.SATURATED_VAPOR,
    }
)

_SUPERCRITICAL_FAMILY: frozenset[PhaseRegion] = frozenset(
    {
        PhaseRegion.SUPERCRITICAL,
        PhaseRegion.SUPERCRITICAL_GAS,
        PhaseRegion.SUPERCRITICAL_LIQUID,
    }
)

_SINGLE_PHASE_FAMILIES: frozenset[frozenset[PhaseRegion]] = frozenset(
    {
        _LIQUID_FAMILY,
        _GAS_FAMILY,
        _SUPERCRITICAL_FAMILY,
    }
)


def _phase_family(phase: PhaseRegion) -> frozenset[PhaseRegion] | None:
    """Return the phase family for *phase*, or None if unknown/non-single-phase."""
    for family in _SINGLE_PHASE_FAMILIES:
        if phase in family:
            return family
    return None


def _is_single_phase_strict(phase: PhaseRegion) -> bool:
    """Return True if *phase* belongs to a single-phase family.

    SATURATED_LIQUID and SATURATED_VAPOR are in their respective families
    but are rejected by the v0.1 single-phase contract (they indicate a
    phase boundary, not a single-phase state).
    """
    if phase in _SUPERCRITICAL_FAMILY:
        return True
    if phase == PhaseRegion.LIQUID:
        return True
    return phase == PhaseRegion.GAS


# ---------------------------------------------------------------------------
# Specification modes
# ---------------------------------------------------------------------------


class SpecificationMode(StrEnum):
    """Explicit enumeration of supported specification combinations.

    The classifier returns one of these modes; under/over-specified
    combinations produce structured blockers rather than raising.
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
# Flow arrangement
# ---------------------------------------------------------------------------


class FlowArrangement(StrEnum):
    """Heat-exchanger flow arrangement.

    v0.1 supports COUNTERFLOW only.  PARALLEL is declared for forward
    compatibility but rejected with an ``UNSUPPORTED_SERVICE`` blocker.
    """

    COUNTERFLOW = "counterflow"
    PARALLEL = "parallel"


# ---------------------------------------------------------------------------
# Heat balance result status
# ---------------------------------------------------------------------------


class HeatBalanceStatus(StrEnum):
    """Outcome of a heat-balance calculation."""

    SUCCEEDED = "SUCCEEDED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Solver parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverParams:
    """Control parameters for the bounded root-finding solver.

    ``temperature_tolerance``: absolute temperature tolerance in K for
    convergence and near-equality checks.

    ``energy_tolerance``: maximum allowed relative energy imbalance
    (dimensionless).  Results above this threshold produce a BLOCKED
    status with a ``CALCULATION_NOT_CONVERGED`` blocker.

    ``max_iterations``: maximum number of Brent root-finding iterations
    (not bracket evaluations).

    ``bracket_step_k``: temperature step in K for probing outward from
    the inlet to find a valid root bracket.

    ``max_bracket_span_k``: maximum total bracket search range in K from
    the inlet temperature.
    """

    temperature_tolerance: float = 1e-4
    energy_tolerance: float = 1e-3
    max_iterations: int = 100
    bracket_step_k: float = 10.0
    max_bracket_span_k: float = 300.0

    def __post_init__(self) -> None:  # noqa: D105
        if not math.isfinite(self.temperature_tolerance) or self.temperature_tolerance <= 0:
            raise ValueError(
                f"temperature_tolerance must be finite and > 0, got {self.temperature_tolerance}"
            )
        if not math.isfinite(self.energy_tolerance) or self.energy_tolerance <= 0:
            raise ValueError(
                f"energy_tolerance must be finite and > 0, got {self.energy_tolerance}"
            )
        if not isinstance(self.max_iterations, int) or self.max_iterations < 1:
            raise ValueError(f"max_iterations must be an integer >= 1, got {self.max_iterations}")
        if not math.isfinite(self.bracket_step_k) or self.bracket_step_k <= 0:
            raise ValueError(f"bracket_step_k must be finite and > 0, got {self.bracket_step_k}")
        if not math.isfinite(self.max_bracket_span_k) or self.max_bracket_span_k <= 0:
            raise ValueError(
                f"max_bracket_span_k must be finite and > 0, got {self.max_bracket_span_k}"
            )


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

    def __post_init__(self) -> None:  # noqa: D105
        if not math.isfinite(self.mass_flow_kg_s) or self.mass_flow_kg_s <= 0:
            raise ValueError(f"Mass flow must be finite and > 0, got {self.mass_flow_kg_s}")
        if not math.isfinite(self.inlet_temperature_k) or self.inlet_temperature_k <= 0:
            raise ValueError(
                f"Inlet temperature must be finite and > 0 K, got {self.inlet_temperature_k}"
            )
        if not math.isfinite(self.inlet_pressure_pa) or self.inlet_pressure_pa <= 0:
            raise ValueError(
                f"Inlet pressure must be finite and > 0 Pa, got {self.inlet_pressure_pa}"
            )
        if self.outlet_temperature_k is not None and (
            not math.isfinite(self.outlet_temperature_k) or self.outlet_temperature_k <= 0
        ):
            raise ValueError(
                f"Outlet temperature must be finite and > 0 K, got {self.outlet_temperature_k}"
            )


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
    reference_state_policy: str
    result_temperature_k: float | None = None
    result_pressure_pa: float | None = None
    result_enthalpy_j_kg: float | None = None
    result_phase: str | None = None
    success: bool = True
    error_code: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Heat-balance input
# ---------------------------------------------------------------------------


def _assert_finite(value: float, name: str) -> None:
    """Raise ValueError if *value* is not finite."""
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


@dataclass(frozen=True)
class HeatBalanceInput:
    """Complete input specification for the heat-balance kernel.

    Exactly one of ``known_duty_w`` or an outlet temperature must be
    provided.  Under/over-specified combinations are detected by the
    classifier and returned as structured blockers.
    """

    hot: StreamState
    cold: StreamState
    known_duty_w: float | None = None
    solver_params: SolverParams = field(default_factory=SolverParams)
    flow_arrangement: FlowArrangement = FlowArrangement.COUNTERFLOW

    def __post_init__(self) -> None:  # noqa: D105
        if self.known_duty_w is not None:
            _assert_finite(self.known_duty_w, "known_duty_w")
            if self.known_duty_w < 0:
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

    status: HeatBalanceStatus
    specification_mode: SpecificationMode
    flow_arrangement: FlowArrangement
    duty_w: float | None
    hot_inlet_state: FluidStateModel
    hot_outlet_state: FluidStateModel
    cold_inlet_state: FluidStateModel
    cold_outlet_state: FluidStateModel
    q_hot_w: float
    q_cold_w: float
    residual_w: float
    relative_imbalance: float
    energy_balance_accepted: bool
    solver_iterations: int
    bracket_evaluations: int
    solver_converged: bool
    property_calls: tuple[PropertyCallRecord, ...]
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None = None
    result_hash: str
    provenance_graph: ProvenanceGraph

    @model_validator(mode="after")
    def _validate_no_nan_inf(self) -> HeatBalanceResult:
        """Reject NaN and Infinity in all float fields."""
        for name in (
            "residual_w",
            "relative_imbalance",
            "q_hot_w",
            "q_cold_w",
        ):
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        if self.duty_w is not None and not math.isfinite(self.duty_w):
            raise ValueError(f"duty_w must be finite, got {self.duty_w!r}")
        return self

    @model_validator(mode="after")
    def _validate_status_contract(self) -> HeatBalanceResult:
        """Ensure status is consistent with blockers/failure."""
        if self.status == HeatBalanceStatus.BLOCKED and not self.blockers:
            raise ValueError("BLOCKED result must have at least one blocker")
        if self.status == HeatBalanceStatus.FAILED and self.failure is None:
            raise ValueError("FAILED result must have a failure record")
        if self.status == HeatBalanceStatus.SUCCEEDED and self.blockers:
            raise ValueError("SUCCEEDED result must not have any blockers")
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

    Returns the appropriate ``SpecificationMode`` value.
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

    # One outlet + duty known: verify duty consistency.
    if hot_outlet_known and duty_known:
        return SpecificationMode.KNOWN_HOT_OUTLET

    if cold_outlet_known and duty_known:
        return SpecificationMode.KNOWN_COLD_OUTLET

    # Should never reach here.
    return SpecificationMode.UNDER_SPECIFIED


# ---------------------------------------------------------------------------
# Phase checks
# ---------------------------------------------------------------------------


def _check_single_phase(state: FluidState, label: str) -> EngineeringMessage | None:
    """Return a blocker if the state is not strictly single-phase."""
    if state.phase == PhaseRegion.UNKNOWN:
        return EngineeringMessage(
            code=ErrorCode.UNSUPPORTED_SERVICE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"{label} state has UNKNOWN phase region; "
                "phase-change heat balance is not implemented in v0.1."
            ),
            source_module="heat_balance",
        )
    if state.phase in (PhaseRegion.SATURATED_LIQUID, PhaseRegion.SATURATED_VAPOR):
        return EngineeringMessage(
            code=ErrorCode.UNSUPPORTED_SERVICE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"{label} state is in phase region '{state.phase.value}'; "
                "saturated states are not single-phase for v0.1."
            ),
            source_module="heat_balance",
        )
    if not _is_single_phase_strict(state.phase):
        return EngineeringMessage(
            code=ErrorCode.UNSUPPORTED_SERVICE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(f"{label} state is in unsupported phase region '{state.phase.value}'."),
            source_module="heat_balance",
        )
    return None


def _check_phase_family_match(
    inlet_phase: PhaseRegion,
    outlet_phase: PhaseRegion,
    label: str,
) -> EngineeringMessage | None:
    """Return a blocker if inlet and outlet are in different phase families."""
    inlet_family = _phase_family(inlet_phase)
    outlet_family = _phase_family(outlet_phase)
    if inlet_family is None or outlet_family is None:
        return EngineeringMessage(
            code=ErrorCode.UNSUPPORTED_SERVICE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"{label}: cannot determine phase family for "
                f"inlet='{inlet_phase.value}' / outlet='{outlet_phase.value}'."
            ),
            source_module="heat_balance",
        )
    if inlet_family is not outlet_family:
        return EngineeringMessage(
            code=ErrorCode.UNSUPPORTED_SERVICE,
            severity=EngineeringMessageSeverity.BLOCKER,
            message=(
                f"{label}: phase transition from '{inlet_phase.value}' to "
                f"'{outlet_phase.value}' is not supported in v0.1."
            ),
            source_module="heat_balance",
        )
    return None


# ---------------------------------------------------------------------------
# Temperature feasibility checks (counterflow)
# ---------------------------------------------------------------------------


def _check_temperature_feasibility(
    hot_inlet_k: float,
    hot_outlet_k: float,
    cold_inlet_k: float,
    cold_outlet_k: float,
    duty_w: float,
    tol: float,
) -> list[EngineeringMessage]:
    """Check temperature feasibility for counterflow arrangement.

    Terminal approaches:
      hot_end = T_hot_in - T_cold_out
      cold_end = T_hot_out - T_cold_in

    Returns a list of warning or blocker messages.  Messages with
    ``severity=BLOCKER`` MUST be placed in the blockers tuple, not
    warnings.
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

    # Counterflow terminal approaches
    hot_end_approach = hot_inlet_k - cold_outlet_k
    cold_end_approach = hot_outlet_k - cold_inlet_k

    # Non-positive terminal approach → BLOCKER
    if hot_end_approach <= tol:
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.BLOCKER,
                message=(
                    f"Non-positive hot-end approach temperature: "
                    f"{hot_end_approach:.4f} K (T_hot_in={hot_inlet_k:.4f}, "
                    f"T_cold_out={cold_outlet_k:.4f})."
                ),
                source_module="heat_balance",
            )
        )
    elif hot_end_approach <= SolverParams().temperature_tolerance * 10:
        # Near-zero positive approach → WARNING (use a small multiple of default tol)
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message=(f"Hot-end approach temperature is near zero: {hot_end_approach:.6f} K."),
                source_module="heat_balance",
            )
        )

    if cold_end_approach <= tol:
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.BLOCKER,
                message=(
                    f"Non-positive cold-end approach temperature: "
                    f"{cold_end_approach:.4f} K (T_hot_out={hot_outlet_k:.4f}, "
                    f"T_cold_in={cold_inlet_k:.4f})."
                ),
                source_module="heat_balance",
            )
        )
    elif cold_end_approach <= SolverParams().temperature_tolerance * 10:
        messages.append(
            EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message=(f"Cold-end approach temperature is near zero: {cold_end_approach:.6f} K."),
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


def _compute_energy_balance(
    q_hot_w: float,
    q_cold_w: float,
    energy_tolerance: float,
) -> tuple[float, float, bool]:
    """Compute residual, relative imbalance, and acceptance flag.

    Returns (residual_w, relative_imbalance, energy_balance_accepted).
    """
    residual_w = q_hot_w - q_cold_w
    max_q = max(abs(q_hot_w), abs(q_cold_w))
    if max_q > _ABSOLUTE_DUTY_THRESHOLD:
        relative_imbalance = abs(residual_w) / max_q
    else:
        relative_imbalance = abs(residual_w)
    energy_balance_accepted = (
        relative_imbalance < energy_tolerance and max_q > _ABSOLUTE_DUTY_THRESHOLD
    )
    return residual_w, relative_imbalance, energy_balance_accepted


# ---------------------------------------------------------------------------
# Root-finding for unknown outlet temperature
# ---------------------------------------------------------------------------


class _BracketExhausted(Exception):
    """Raised internally when the bracket search fails."""


class _SolverNotConverged(Exception):
    """Raised internally when Brent fails to converge."""


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
    expected_phase_family: frozenset[PhaseRegion],
) -> tuple[FluidState, int, int]:
    """Solve for the unknown outlet temperature using Brent's method.

    Phase-safe: only expands the bracket to temperatures where the
    property call succeeds AND returns a state in the expected phase
    family.  Property failures during bracket probing are recorded and
    skipped.

    Returns ``(outlet_state, brent_iterations, bracket_evaluations)``.

    Raises ``_BracketExhausted`` if no valid bracket can be found, or
    ``_SolverNotConverged`` if Brent does not converge.
    """
    target_h: float
    if is_hot_side:
        target_h = inlet_state.enthalpy_j_kg - known_duty_w / mass_flow
    else:
        target_h = inlet_state.enthalpy_j_kg + known_duty_w / mass_flow

    pressure_pa = inlet_state.pressure_pa
    t_inlet = inlet_state.temperature_k

    brent_iterations = [0]
    bracket_evaluations = [0]

    def _safe_eval_tp(t: float) -> FluidState | None:
        """Evaluate state at (t, P).  Returns None on property failure."""
        bracket_evaluations[0] += 1
        try:
            state = provider.state_tp(fluid, t, pressure_pa)
        except PropertyServiceError:
            return None
        return state

    def _is_valid_bracket_state(state: FluidState) -> bool:
        """Check if state is finite and in the expected phase family."""
        if not math.isfinite(state.enthalpy_j_kg):
            return False
        family = _phase_family(state.phase)
        if family is None:
            return False
        return family is expected_phase_family

    def residual(t: float) -> float:
        """Residual function for brentq.  Only called within a valid bracket."""
        brent_iterations[0] += 1
        if brent_iterations[0] > solver_params.max_iterations:
            raise _SolverNotConverged(
                f"Solver exceeded max iterations ({solver_params.max_iterations})"
            )
        state = _safe_eval_tp(t)
        if state is None or not _is_valid_bracket_state(state):
            # Return a sign-guiding value; Brent should not call this
            # outside a validated bracket, but as a safety net:
            return 1e6 if is_hot_side else -1e6
        return state.enthalpy_j_kg - target_h

    # --- Build bracket by probing outward from inlet ---
    step = solver_params.bracket_step_k
    max_span = solver_params.max_bracket_span_k
    max_steps = int(max_span / step)

    t_upper: float
    t_lower: float
    f_upper: float | None = None
    f_lower: float | None = None

    if is_hot_side:
        # Upper bound is just below inlet (where h > target_h for positive Q)
        t_upper = t_inlet - solver_params.temperature_tolerance
        # Probe downward to find lower bound
        t_lower = t_inlet - step

        upper_state = _safe_eval_tp(t_upper)
        if upper_state is not None and _is_valid_bracket_state(upper_state):
            f_upper = upper_state.enthalpy_j_kg - target_h

        for _ in range(max_steps):
            probe_state = _safe_eval_tp(t_lower)
            if probe_state is not None and _is_valid_bracket_state(probe_state):
                f_lower = probe_state.enthalpy_j_kg - target_h
                if f_upper is not None and f_lower is not None and f_upper * f_lower <= 0:
                    break
                # Same sign: advance upper to this lower
                t_upper = t_lower
                f_upper = f_lower
            # Skip invalid temperature — continue probing
            t_lower -= step
        else:
            # Exhausted bracket search
            raise _BracketExhausted(
                f"Could not find valid bracket for {'hot' if is_hot_side else 'cold'}-side "
                f"outlet. Target enthalpy={target_h:.2f} J/kg, inlet T={t_inlet:.2f} K."
            )

    else:
        # Lower bound is just above inlet (where h < target_h for positive Q)
        t_lower = t_inlet + solver_params.temperature_tolerance
        # Probe upward to find upper bound
        t_upper = t_inlet + step

        lower_state = _safe_eval_tp(t_lower)
        if lower_state is not None and _is_valid_bracket_state(lower_state):
            f_lower = lower_state.enthalpy_j_kg - target_h

        for _ in range(max_steps):
            probe_state = _safe_eval_tp(t_upper)
            if probe_state is not None and _is_valid_bracket_state(probe_state):
                f_upper = probe_state.enthalpy_j_kg - target_h
                if f_lower is not None and f_upper is not None and f_lower * f_upper <= 0:
                    break
                # Same sign: advance lower to this upper
                t_lower = t_upper
                f_lower = f_upper
            # Skip invalid temperature — continue probing
            t_upper += step
        else:
            raise _BracketExhausted(
                f"Could not find valid bracket for {'hot' if is_hot_side else 'cold'}-side "
                f"outlet. Target enthalpy={target_h:.2f} J/kg, inlet T={t_inlet:.2f} K."
            )

    # --- Solve with brentq ---
    # We know f_upper and f_lower have opposite signs from the bracket search.
    def _brent_residual(t: float) -> float:
        """Wrapper for brentq that counts iterations."""
        brent_iterations[0] += 1
        if brent_iterations[0] > solver_params.max_iterations:
            raise _SolverNotConverged(
                f"Solver exceeded max iterations ({solver_params.max_iterations})"
            )
        state = _safe_eval_tp(t)
        if state is None or not _is_valid_bracket_state(state):
            return 1e6 if is_hot_side else -1e6
        return state.enthalpy_j_kg - target_h

    try:
        t_solution = brentq(
            _brent_residual,
            t_lower,
            t_upper,
            xtol=solver_params.temperature_tolerance,
            maxiter=solver_params.max_iterations,
        )
    except (_SolverNotConverged, ValueError) as exc:
        raise _SolverNotConverged(
            f"Root-finding failed: {exc}. Target enthalpy={target_h:.2f} J/kg, "
            f"bracket=[{t_lower:.2f}, {t_upper:.2f}] K."
        ) from exc

    # Get the final state at the solved temperature
    outlet_state = _safe_eval_tp(t_solution)
    if outlet_state is None:
        raise _SolverNotConverged(
            f"Final state evaluation failed at solved temperature {t_solution:.4f} K."
        )

    property_calls_temp: list[PropertyCallRecord] = []
    _record_property_call(
        property_calls_temp,
        fluid,
        "TP",
        (("temperature_k", t_solution), ("pressure_pa", pressure_pa)),
        provider,
        outlet_state,
        success=True,
    )
    property_calls.extend(property_calls_temp)

    return outlet_state, brent_iterations[0], bracket_evaluations[0]


# ---------------------------------------------------------------------------
# Property call recording
# ---------------------------------------------------------------------------


def _record_property_call(
    records: list[PropertyCallRecord],
    fluid: FluidIdentifier,
    query_type: str,
    inputs: tuple[tuple[str, float], ...],
    provider: PropertyProvider,
    state: FluidState | None = None,
    *,
    success: bool = True,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Append a PropertyCallRecord to *records*."""
    records.append(
        PropertyCallRecord(
            fluid=str(fluid),
            query_type=query_type,
            inputs=inputs,
            backend_name=provider.name,
            backend_version=provider.version,
            reference_state_policy=provider.reference_state_policy.value,
            result_temperature_k=state.temperature_k if state is not None else None,
            result_pressure_pa=state.pressure_pa if state is not None else None,
            result_enthalpy_j_kg=state.enthalpy_j_kg if state is not None else None,
            result_phase=state.phase.value if state is not None else None,
            success=success,
            error_code=error_code,
            error_message=error_message,
        )
    )


def _record_failed_property_call(
    records: list[PropertyCallRecord],
    fluid: FluidIdentifier,
    query_type: str,
    inputs: tuple[tuple[str, float], ...],
    provider: PropertyProvider,
    exc: PropertyServiceError,
) -> None:
    """Record a failed property call."""
    _record_property_call(
        records,
        fluid,
        query_type,
        inputs,
        provider,
        state=None,
        success=False,
        error_code=exc.code.value,
        error_message=str(exc),
    )


# ---------------------------------------------------------------------------
# Canonical serialization for hashing
# ---------------------------------------------------------------------------


def _fluid_state_model_to_dict(state: FluidStateModel) -> dict[str, Any]:
    """Convert FluidStateModel to a canonical dict for hashing."""
    prov = state.provenance
    return {
        "temperature_k": state.temperature_k,
        "pressure_pa": state.pressure_pa,
        "density_kg_m3": state.density_kg_m3,
        "cp_j_kg_k": state.cp_j_kg_k,
        "enthalpy_j_kg": state.enthalpy_j_kg,
        "entropy_j_kg_k": state.entropy_j_kg_k,
        "phase": state.phase.value,
        "backend_name": prov.backend_name,
        "backend_version": prov.backend_version,
        "reference_state_policy": prov.reference_state_policy.value,
    }


def _property_call_record_to_dict(pc: PropertyCallRecord) -> dict[str, Any]:
    """Convert PropertyCallRecord to a canonical dict for hashing."""
    return {
        "fluid": pc.fluid,
        "query_type": pc.query_type,
        "inputs": dict(pc.inputs),
        "backend_name": pc.backend_name,
        "backend_version": pc.backend_version,
        "reference_state_policy": pc.reference_state_policy,
        "result_temperature_k": pc.result_temperature_k,
        "result_pressure_pa": pc.result_pressure_pa,
        "result_enthalpy_j_kg": pc.result_enthalpy_j_kg,
        "result_phase": pc.result_phase,
        "success": pc.success,
        "error_code": pc.error_code,
        "error_message": pc.error_message,
    }


def _message_to_dict(msg: EngineeringMessage) -> dict[str, Any]:
    """Convert EngineeringMessage to a canonical dict for hashing."""
    return {
        "code": msg.code.value,
        "severity": msg.severity.value,
        "message": msg.message,
        "source_module": msg.source_module,
    }


def _compute_result_hash(
    specification_mode: SpecificationMode,
    flow_arrangement: FlowArrangement,
    hot_inlet: FluidStateModel,
    hot_outlet: FluidStateModel,
    cold_inlet: FluidStateModel,
    cold_outlet: FluidStateModel,
    hot: StreamState,
    cold: StreamState,
    known_duty_w: float | None,
    solver_params: SolverParams,
    provider: PropertyProvider,
    property_calls: tuple[PropertyCallRecord, ...],
    warnings: tuple[EngineeringMessage, ...],
    blockers: tuple[EngineeringMessage, ...],
    q_hot_w: float,
    q_cold_w: float,
    residual_w: float,
    relative_imbalance: float,
    energy_balance_accepted: bool,
    software_version: str,
) -> str:
    """Compute deterministic SHA-256 hash of the result.

    Includes all inputs, outputs, solver params, provider identity,
    property call results, messages, and energy balance fields.
    """
    payload: dict[str, Any] = {
        "specification_mode": specification_mode.value,
        "flow_arrangement": flow_arrangement.value,
        # Fluid identifiers
        "hot_fluid_name": hot.fluid_identifier.name,
        "hot_fluid_backend": hot.fluid_identifier.equation_of_state_backend,
        "hot_fluid_components": hot.fluid_identifier.components,
        "cold_fluid_name": cold.fluid_identifier.name,
        "cold_fluid_backend": cold.fluid_identifier.equation_of_state_backend,
        "cold_fluid_components": cold.fluid_identifier.components,
        # Mass flows, pressures, inlet temperatures
        "hot_mass_flow_kg_s": hot.mass_flow_kg_s,
        "cold_mass_flow_kg_s": cold.mass_flow_kg_s,
        "hot_inlet_pressure_pa": hot.inlet_pressure_pa,
        "cold_inlet_pressure_pa": cold.inlet_pressure_pa,
        "hot_inlet_temperature_k": hot.inlet_temperature_k,
        "cold_inlet_temperature_k": cold.inlet_temperature_k,
        # Supplied outlet temperatures (None sentinel for unsupplied)
        "hot_outlet_temperature_k": hot.outlet_temperature_k,
        "cold_outlet_temperature_k": cold.outlet_temperature_k,
        # Supplied duty (None sentinel)
        "known_duty_w": known_duty_w,
        # Solver params
        "solver_temperature_tolerance": solver_params.temperature_tolerance,
        "solver_energy_tolerance": solver_params.energy_tolerance,
        "solver_max_iterations": solver_params.max_iterations,
        "solver_bracket_step_k": solver_params.bracket_step_k,
        "solver_max_bracket_span_k": solver_params.max_bracket_span_k,
        # Provider identity
        "provider_name": provider.name,
        "provider_version": provider.version,
        "provider_reference_state_policy": provider.reference_state_policy.value,
        # Solved states
        "hot_inlet": _fluid_state_model_to_dict(hot_inlet),
        "hot_outlet": _fluid_state_model_to_dict(hot_outlet),
        "cold_inlet": _fluid_state_model_to_dict(cold_inlet),
        "cold_outlet": _fluid_state_model_to_dict(cold_outlet),
        # Property call results (complete)
        "property_calls": [_property_call_record_to_dict(pc) for pc in property_calls],
        # Messages (complete)
        "warnings": [_message_to_dict(m) for m in warnings],
        "blockers": [_message_to_dict(m) for m in blockers],
        # Energy balance fields
        "q_hot_w": q_hot_w,
        "q_cold_w": q_cold_w,
        "residual_w": residual_w,
        "relative_imbalance": relative_imbalance,
        "energy_balance_accepted": energy_balance_accepted,
        # Software version
        "software_version": software_version,
    }
    return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Provenance graph construction
# ---------------------------------------------------------------------------


def _deterministic_uuid5(payload: dict[str, Any]) -> UUID:
    """Compute a deterministic UUID5 from a canonical payload dict."""
    canonical = sha256_digest(payload)
    return uuid5(_PROVENANCE_NAMESPACE, canonical)


def _build_provenance(
    specification_mode: SpecificationMode,
    flow_arrangement: FlowArrangement,
    hot: StreamState,
    cold: StreamState,
    known_duty_w: float | None,
    solver_params: SolverParams,
    property_calls: list[PropertyCallRecord],
    solver_iterations: int,
    bracket_evaluations: int,
    solver_converged: bool,
    warnings: list[EngineeringMessage],
    blockers: list[EngineeringMessage],
    result_hash: str,
    *,
    case_revision_id: UUID | None = None,
) -> ProvenanceGraph:
    """Build a deterministic provenance graph for the heat-balance calculation.

    If *case_revision_id* is None, the CASE_REVISION and
    CALCULATION_RUN nodes are omitted (no invented identities).
    """
    nodes: list[ProvenanceNode] = []
    edges: list[ProvenanceEdge] = []

    # --- Root node (either CASE_REVISION or a standalone CALCULATION_RUN) ---
    calc_run_id: UUID

    if case_revision_id is not None:
        # Case revision node with deterministic ID
        case_rev_payload = {"revision_id": str(case_revision_id)}
        case_rev_id = _deterministic_uuid5(case_rev_payload)
        nodes.append(
            ProvenanceNode(
                node_id=case_rev_id,
                node_type=ProvenanceNodeType.CASE_REVISION,
                label="case_revision",
                metadata=(("revision_id", str(case_revision_id)),),
                payload_hash=sha256_digest(case_rev_payload),
            )
        )

        # Calculation run node
        calc_payload: dict[str, Any] = {
            "specification_mode": specification_mode.value,
            "flow_arrangement": flow_arrangement.value,
            "solver_iterations": solver_iterations,
            "bracket_evaluations": bracket_evaluations,
            "solver_converged": solver_converged,
            "software_version": _SOFTWARE_VERSION,
        }
        calc_run_id = _deterministic_uuid5(calc_payload)
        nodes.append(
            ProvenanceNode(
                node_id=calc_run_id,
                node_type=ProvenanceNodeType.CALCULATION_RUN,
                label="heat_balance_run",
                metadata=(
                    ("specification_mode", specification_mode.value),
                    ("flow_arrangement", flow_arrangement.value),
                    ("solver_iterations", solver_iterations),
                    ("bracket_evaluations", bracket_evaluations),
                    ("solver_converged", solver_converged),
                    ("software_version", _SOFTWARE_VERSION),
                ),
                payload_hash=sha256_digest(calc_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=case_rev_id,
                target_id=calc_run_id,
                relation="triggers",
            )
        )
    else:
        # No real case revision — use deterministic synthetic ID
        # (ProvenanceGraph requires CASE_REVISION node)
        synthetic_rev_payload = {
            "synthetic": True,
            "specification_mode": specification_mode.value,
            "flow_arrangement": flow_arrangement.value,
        }
        case_rev_id = _deterministic_uuid5(synthetic_rev_payload)
        nodes.append(
            ProvenanceNode(
                node_id=case_rev_id,
                node_type=ProvenanceNodeType.CASE_REVISION,
                label="synthetic_case_revision",
                metadata=(("synthetic", True),),
                payload_hash=sha256_digest(synthetic_rev_payload),
            )
        )

        calc_payload = {
            "specification_mode": specification_mode.value,
            "flow_arrangement": flow_arrangement.value,
            "solver_iterations": solver_iterations,
            "bracket_evaluations": bracket_evaluations,
            "solver_converged": solver_converged,
            "software_version": _SOFTWARE_VERSION,
        }
        calc_run_id = _deterministic_uuid5(calc_payload)
        nodes.append(
            ProvenanceNode(
                node_id=calc_run_id,
                node_type=ProvenanceNodeType.CALCULATION_RUN,
                label="heat_balance_run",
                metadata=(
                    ("specification_mode", specification_mode.value),
                    ("flow_arrangement", flow_arrangement.value),
                    ("solver_iterations", solver_iterations),
                    ("bracket_evaluations", bracket_evaluations),
                    ("solver_converged", solver_converged),
                    ("software_version", _SOFTWARE_VERSION),
                ),
                payload_hash=sha256_digest(calc_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=case_rev_id,
                target_id=calc_run_id,
                relation="triggers",
            )
        )

    # --- Property call nodes ---
    for pc in property_calls:
        prop_payload: dict[str, Any] = {
            "fluid": pc.fluid,
            "query_type": pc.query_type,
            "inputs": dict(pc.inputs),
            "backend_name": pc.backend_name,
            "backend_version": pc.backend_version,
            "reference_state_policy": pc.reference_state_policy,
            "result_temperature_k": pc.result_temperature_k,
            "result_pressure_pa": pc.result_pressure_pa,
            "result_enthalpy_j_kg": pc.result_enthalpy_j_kg,
            "result_phase": pc.result_phase,
            "success": pc.success,
            "error_code": pc.error_code,
            "error_message": pc.error_message,
        }
        prop_id = _deterministic_uuid5(prop_payload)
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
                    ("reference_state_policy", pc.reference_state_policy),
                    ("success", pc.success),
                    ("error_code", pc.error_code),
                ),
                payload_hash=sha256_digest(prop_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_run_id,
                target_id=prop_id,
                relation="calls",
            )
        )

    # --- Result node ---
    result_payload = {"result_hash": result_hash}
    result_id = _deterministic_uuid5(result_payload)
    nodes.append(
        ProvenanceNode(
            node_id=result_id,
            node_type=ProvenanceNodeType.RESULT,
            label="heat_balance_result",
            metadata=(("result_hash", result_hash),),
            payload_hash=sha256_digest(result_payload),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=calc_run_id,
            target_id=result_id,
            relation="produces",
        )
    )

    # --- Warning nodes ---
    for w in warnings:
        warn_payload: dict[str, Any] = {
            "code": w.code.value,
            "severity": w.severity.value,
            "message": w.message,
            "source_module": w.source_module,
            "context": dict(w.context) if w.context else {},
        }
        warn_id = _deterministic_uuid5(warn_payload)
        nodes.append(
            ProvenanceNode(
                node_id=warn_id,
                node_type=ProvenanceNodeType.WARNING,
                label=f"warning_{w.code.value}",
                metadata=(
                    ("code", w.code.value),
                    ("severity", w.severity.value),
                    ("message", w.message),
                    ("source_module", w.source_module),
                ),
                payload_hash=sha256_digest(warn_payload),
            )
        )
        edges.append(
            ProvenanceEdge(
                source_id=calc_run_id,
                target_id=warn_id,
                relation="emits",
            )
        )

    # --- Blocker nodes ---
    for b in blockers:
        block_payload: dict[str, Any] = {
            "code": b.code.value,
            "severity": b.severity.value,
            "message": b.message,
            "source_module": b.source_module,
            "context": dict(b.context) if b.context else {},
        }
        block_id = _deterministic_uuid5(block_payload)
        nodes.append(
            ProvenanceNode(
                node_id=block_id,
                node_type=ProvenanceNodeType.BLOCKER,
                label=f"blocker_{b.code.value}",
                metadata=(
                    ("code", b.code.value),
                    ("severity", b.severity.value),
                    ("message", b.message),
                    ("source_module", b.source_module),
                ),
                payload_hash=sha256_digest(block_payload),
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

    When Q = 0:
    - If outlets are supplied, they must match inlets within tolerance.
    - If no outlets are supplied, outlets = inlets (no property calls).
    - Do NOT fabricate property-call records for reused states.
    """
    property_calls: list[PropertyCallRecord] = []
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []
    tol = inp.solver_params.temperature_tolerance

    # Record the inlet property calls (these were already evaluated)
    _record_property_call(
        property_calls,
        inp.hot.fluid_identifier,
        "TP",
        (
            ("temperature_k", inp.hot.inlet_temperature_k),
            ("pressure_pa", inp.hot.inlet_pressure_pa),
        ),
        provider,
        hot_inlet_state,
        success=True,
    )
    _record_property_call(
        property_calls,
        inp.cold.fluid_identifier,
        "TP",
        (
            ("temperature_k", inp.cold.inlet_temperature_k),
            ("pressure_pa", inp.cold.inlet_pressure_pa),
        ),
        provider,
        cold_inlet_state,
        success=True,
    )

    # Determine outlet states

    # Validate supplied outlets against inlets
    if inp.hot.outlet_temperature_k is not None:
        if abs(inp.hot.outlet_temperature_k - hot_inlet_state.temperature_k) >= tol:
            blockers.append(
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Zero duty with hot outlet ({inp.hot.outlet_temperature_k:.4f} K) "
                        f"does not match hot inlet ({hot_inlet_state.temperature_k:.4f} K)."
                    ),
                    source_module="heat_balance",
                )
            )
        # The outlet is supplied but equals inlet — it IS the same state,
        # so we record the call for the supplied outlet (even though the
        # state is reused, the caller did provide a distinct specification).
        _record_property_call(
            property_calls,
            inp.hot.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.hot.outlet_temperature_k),
                ("pressure_pa", inp.hot.inlet_pressure_pa),
            ),
            provider,
            hot_inlet_state,
            success=True,
        )

    if inp.cold.outlet_temperature_k is not None:
        if abs(inp.cold.outlet_temperature_k - cold_inlet_state.temperature_k) >= tol:
            blockers.append(
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Zero duty with cold outlet ({inp.cold.outlet_temperature_k:.4f} K) "
                        f"does not match cold inlet ({cold_inlet_state.temperature_k:.4f} K)."
                    ),
                    source_module="heat_balance",
                )
            )
        _record_property_call(
            property_calls,
            inp.cold.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.cold.outlet_temperature_k),
                ("pressure_pa", inp.cold.inlet_pressure_pa),
            ),
            provider,
            cold_inlet_state,
            success=True,
        )

    # Phase checks on final states
    for label, state in (
        ("Hot-side inlet", hot_inlet_state),
        ("Cold-side inlet", cold_inlet_state),
    ):
        phase_msg = _check_single_phase(state, label)
        if phase_msg is not None:
            blockers.append(phase_msg)

    # Energy balance: q_hot = 0, q_cold = 0, residual = 0
    q_hot_w = 0.0
    q_cold_w = 0.0
    residual_w = 0.0
    relative_imbalance = 0.0
    energy_balance_accepted = True

    # Determine status
    status = HeatBalanceStatus.BLOCKED if blockers else HeatBalanceStatus.SUCCEEDED

    # Compute hash
    hot_model = hot_inlet_state.to_model()
    cold_model = cold_inlet_state.to_model()

    result_hash = _compute_result_hash(
        SpecificationMode.KNOWN_DUTY,
        inp.flow_arrangement,
        hot_model,
        hot_model,
        cold_model,
        cold_model,
        inp.hot,
        inp.cold,
        0.0,
        inp.solver_params,
        provider,
        tuple(property_calls),
        tuple(warnings),
        tuple(blockers),
        q_hot_w,
        q_cold_w,
        residual_w,
        relative_imbalance,
        energy_balance_accepted,
        _SOFTWARE_VERSION,
    )

    provenance = _build_provenance(
        specification_mode=SpecificationMode.KNOWN_DUTY,
        flow_arrangement=inp.flow_arrangement,
        hot=inp.hot,
        cold=inp.cold,
        known_duty_w=0.0,
        solver_params=inp.solver_params,
        property_calls=property_calls,
        solver_iterations=0,
        bracket_evaluations=0,
        solver_converged=True,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
    )

    return HeatBalanceResult(
        status=status,
        specification_mode=SpecificationMode.KNOWN_DUTY,
        flow_arrangement=inp.flow_arrangement,
        duty_w=0.0,
        hot_inlet_state=hot_model,
        hot_outlet_state=hot_model,
        cold_inlet_state=cold_model,
        cold_outlet_state=cold_model,
        q_hot_w=q_hot_w,
        q_cold_w=q_cold_w,
        residual_w=residual_w,
        relative_imbalance=relative_imbalance,
        energy_balance_accepted=energy_balance_accepted,
        solver_iterations=0,
        bracket_evaluations=0,
        solver_converged=True,
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        result_hash=result_hash,
        provenance_graph=provenance,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _property_error_to_code(exc: PropertyServiceError) -> ErrorCode:
    """Map PropertyServiceError codes to EngineeringMessage error codes."""
    mapping: dict[PropertyErrorCode, ErrorCode] = {
        PropertyErrorCode.BACKEND_FAILURE: ErrorCode.PROPERTY_UNAVAILABLE,
        PropertyErrorCode.STATE_OUT_OF_RANGE: ErrorCode.PROPERTY_OUT_OF_RANGE,
        PropertyErrorCode.INVALID_FLUID: ErrorCode.INPUT_MISSING,
        PropertyErrorCode.INVALID_INPUT: ErrorCode.INPUT_INCONSISTENT,
        PropertyErrorCode.UNSUPPORTED_BACKEND: ErrorCode.UNSUPPORTED_SERVICE,
        PropertyErrorCode.TWO_PHASE_STATE: ErrorCode.UNSUPPORTED_SERVICE,
    }
    return mapping.get(exc.code, ErrorCode.CALCULATION_BLOCKED)


def _make_blocked_result(
    inp: HeatBalanceInput,
    provider: PropertyProvider,
    specification_mode: SpecificationMode,
    hot_inlet_state: FluidState | None,
    cold_inlet_state: FluidState | None,
    property_calls: list[PropertyCallRecord],
    warnings: list[EngineeringMessage],
    blockers: list[EngineeringMessage],
) -> HeatBalanceResult:
    """Build a BLOCKED HeatBalanceResult from the current state.

    Used for early-exit paths (under/over-specified, property failure,
    phase rejection, etc.).
    """
    hot_model = (
        hot_inlet_state.to_model() if hot_inlet_state is not None else _placeholder_state_model()
    )
    cold_model = (
        cold_inlet_state.to_model() if cold_inlet_state is not None else _placeholder_state_model()
    )

    # Use placeholder outlet models (same as inlet when unknown)
    hot_outlet_model = hot_model
    cold_outlet_model = cold_model

    q_hot_w = 0.0
    q_cold_w = 0.0
    residual_w = 0.0
    relative_imbalance = 0.0
    energy_balance_accepted = False

    result_hash = _compute_result_hash(
        specification_mode,
        inp.flow_arrangement,
        hot_model,
        hot_outlet_model,
        cold_model,
        cold_outlet_model,
        inp.hot,
        inp.cold,
        inp.known_duty_w,
        inp.solver_params,
        provider,
        tuple(property_calls),
        tuple(warnings),
        tuple(blockers),
        q_hot_w,
        q_cold_w,
        residual_w,
        relative_imbalance,
        energy_balance_accepted,
        _SOFTWARE_VERSION,
    )

    provenance = _build_provenance(
        specification_mode=specification_mode,
        flow_arrangement=inp.flow_arrangement,
        hot=inp.hot,
        cold=inp.cold,
        known_duty_w=inp.known_duty_w,
        solver_params=inp.solver_params,
        property_calls=property_calls,
        solver_iterations=0,
        bracket_evaluations=0,
        solver_converged=False,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
    )

    return HeatBalanceResult(
        status=HeatBalanceStatus.BLOCKED,
        specification_mode=specification_mode,
        flow_arrangement=inp.flow_arrangement,
        duty_w=None,
        hot_inlet_state=hot_model,
        hot_outlet_state=hot_outlet_model,
        cold_inlet_state=cold_model,
        cold_outlet_state=cold_outlet_model,
        q_hot_w=q_hot_w,
        q_cold_w=q_cold_w,
        residual_w=residual_w,
        relative_imbalance=relative_imbalance,
        energy_balance_accepted=energy_balance_accepted,
        solver_iterations=0,
        bracket_evaluations=0,
        solver_converged=False,
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        result_hash=result_hash,
        provenance_graph=provenance,
    )


def _placeholder_state_model() -> FluidStateModel:
    """Create a placeholder FluidStateModel for blocked/incomplete results."""
    from hexagent.properties.base import (  # noqa: F811
        FluidValidationLevel,
        PropertyProvenanceModel,
        PropertyQueryType,
    )

    return FluidStateModel(
        temperature_k=0.0,
        pressure_pa=0.0,
        density_kg_m3=0.0,
        cp_j_kg_k=0.0,
        viscosity_pa_s=0.0,
        conductivity_w_m_k=0.0,
        enthalpy_j_kg=0.0,
        entropy_j_kg_k=0.0,
        phase=PhaseRegion.UNKNOWN,
        provenance=PropertyProvenanceModel(
            backend_name="",
            backend_version="",
            backend_git_revision="",
            fluid_identifier="",
            validation_level=FluidValidationLevel.UNVALIDATED,
            query_type=PropertyQueryType.TP,
            inputs={},
            cache_policy_version="",
            reference_state_policy=ReferenceStatePolicy.DEF,
            configuration_fingerprint="",
        ),
    )


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------


def solve_heat_balance(inp: HeatBalanceInput, provider: PropertyProvider) -> HeatBalanceResult:
    """Solve the single-phase sensible heat balance.

    This is the main entry point for the heat-balance kernel.  It:

    1. Validates inputs.
    2. Classifies the specification mode.
    3. Evaluates inlet states via the property provider.
    4. Checks for phase change (rejects two-phase / cross-family).
    5. Solves for unknowns using bounded root-finding.
    6. Checks temperature feasibility (terminal approaches).
    7. Computes energy residual and relative imbalance.
    8. Builds provenance graph and deterministic result hash.

    The function ALWAYS returns a ``HeatBalanceResult`` and never raises
    for domain errors.  Property-provider exceptions during inlet
    evaluation are caught and converted to BLOCKED results.

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
    """
    # --- Input validation ---
    if inp.hot.mass_flow_kg_s <= 0:
        raise ValueError(f"Hot-side mass flow must be > 0, got {inp.hot.mass_flow_kg_s}")
    if inp.cold.mass_flow_kg_s <= 0:
        raise ValueError(f"Cold-side mass flow must be > 0, got {inp.cold.mass_flow_kg_s}")

    # --- Flow arrangement check ---
    if inp.flow_arrangement != FlowArrangement.COUNTERFLOW:
        return _make_blocked_result(
            inp,
            provider,
            SpecificationMode.UNDER_SPECIFIED,
            None,
            None,
            [],
            [],
            [
                EngineeringMessage(
                    code=ErrorCode.UNSUPPORTED_SERVICE,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Flow arrangement '{inp.flow_arrangement.value}' is not supported "
                        "in v0.1. Only counterflow is implemented."
                    ),
                    source_module="heat_balance",
                )
            ],
        )

    # --- Classify specification ---
    mode = classify_specification(inp)

    if mode == SpecificationMode.UNDER_SPECIFIED:
        return _make_blocked_result(
            inp,
            provider,
            mode,
            None,
            None,
            [],
            [],
            [
                EngineeringMessage(
                    code=ErrorCode.INPUT_MISSING,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message="Under-specified: provide duty or at least one outlet temperature.",
                    source_module="heat_balance",
                )
            ],
        )

    if mode == SpecificationMode.OVER_SPECIFIED:
        return _make_blocked_result(
            inp,
            provider,
            mode,
            None,
            None,
            [],
            [],
            [
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message="Over-specified: duty and both outlets cannot all be provided.",
                    source_module="heat_balance",
                )
            ],
        )

    # --- Evaluate inlet states ---
    property_calls: list[PropertyCallRecord] = []
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []

    hot_inlet_state: FluidState
    try:
        hot_inlet_state = provider.state_tp(
            inp.hot.fluid_identifier,
            inp.hot.inlet_temperature_k,
            inp.hot.inlet_pressure_pa,
        )
    except PropertyServiceError as exc:
        _record_failed_property_call(
            property_calls,
            inp.hot.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.hot.inlet_temperature_k),
                ("pressure_pa", inp.hot.inlet_pressure_pa),
            ),
            provider,
            exc,
        )
        blockers.append(
            EngineeringMessage(
                code=_property_error_to_code(exc),
                severity=EngineeringMessageSeverity.BLOCKER,
                message=f"Hot-side inlet property evaluation failed: {exc}",
                source_module="heat_balance",
                context=((("error", str(exc)),)),
            )
        )
        return _make_blocked_result(
            inp, provider, mode, None, None, property_calls, warnings, blockers
        )

    _record_property_call(
        property_calls,
        inp.hot.fluid_identifier,
        "TP",
        (
            ("temperature_k", inp.hot.inlet_temperature_k),
            ("pressure_pa", inp.hot.inlet_pressure_pa),
        ),
        provider,
        hot_inlet_state,
        success=True,
    )

    cold_inlet_state: FluidState
    try:
        cold_inlet_state = provider.state_tp(
            inp.cold.fluid_identifier,
            inp.cold.inlet_temperature_k,
            inp.cold.inlet_pressure_pa,
        )
    except PropertyServiceError as exc:
        _record_failed_property_call(
            property_calls,
            inp.cold.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.cold.inlet_temperature_k),
                ("pressure_pa", inp.cold.inlet_pressure_pa),
            ),
            provider,
            exc,
        )
        blockers.append(
            EngineeringMessage(
                code=_property_error_to_code(exc),
                severity=EngineeringMessageSeverity.BLOCKER,
                message=f"Cold-side inlet property evaluation failed: {exc}",
                source_module="heat_balance",
                context=((("error", str(exc)),)),
            )
        )
        return _make_blocked_result(
            inp, provider, mode, hot_inlet_state, None, property_calls, warnings, blockers
        )

    _record_property_call(
        property_calls,
        inp.cold.fluid_identifier,
        "TP",
        (
            ("temperature_k", inp.cold.inlet_temperature_k),
            ("pressure_pa", inp.cold.inlet_pressure_pa),
        ),
        provider,
        cold_inlet_state,
        success=True,
    )

    # --- Phase check on inlets ---
    phase_msg = _check_single_phase(hot_inlet_state, "Hot-side inlet")
    if phase_msg is not None:
        blockers.append(phase_msg)
        return _make_blocked_result(
            inp,
            provider,
            mode,
            hot_inlet_state,
            cold_inlet_state,
            property_calls,
            warnings,
            blockers,
        )

    phase_msg = _check_single_phase(cold_inlet_state, "Cold-side inlet")
    if phase_msg is not None:
        blockers.append(phase_msg)
        return _make_blocked_result(
            inp,
            provider,
            mode,
            hot_inlet_state,
            cold_inlet_state,
            property_calls,
            warnings,
            blockers,
        )

    # Determine expected phase families from inlets
    hot_phase_family = _phase_family(hot_inlet_state.phase)
    cold_phase_family = _phase_family(cold_inlet_state.phase)
    assert hot_phase_family is not None  # guaranteed by _check_single_phase
    assert cold_phase_family is not None  # guaranteed by _check_single_phase

    # --- Handle zero duty ---
    if inp.known_duty_w is not None and inp.known_duty_w == 0.0:
        return _handle_zero_duty(inp, provider, hot_inlet_state, cold_inlet_state)

    # --- Solve based on specification mode ---
    total_brent_iterations = 0
    total_bracket_evaluations = 0
    hot_outlet_state: FluidState
    cold_outlet_state: FluidState
    duty_w: float

    if mode == SpecificationMode.KNOWN_DUTY:
        assert inp.known_duty_w is not None
        # Solve both outlets independently
        hot_outlet_state, iters_hot, be_hot = _solve_outlet_temperature(
            provider,
            inp.hot.fluid_identifier,
            hot_inlet_state,
            inp.hot.mass_flow_kg_s,
            inp.known_duty_w,
            is_hot_side=True,
            solver_params=inp.solver_params,
            property_calls=property_calls,
            expected_phase_family=hot_phase_family,
        )
        cold_outlet_state, iters_cold, be_cold = _solve_outlet_temperature(
            provider,
            inp.cold.fluid_identifier,
            cold_inlet_state,
            inp.cold.mass_flow_kg_s,
            inp.known_duty_w,
            is_hot_side=False,
            solver_params=inp.solver_params,
            property_calls=property_calls,
            expected_phase_family=cold_phase_family,
        )
        total_brent_iterations = iters_hot + iters_cold
        total_bracket_evaluations = be_hot + be_cold
        duty_w = inp.known_duty_w

    elif mode == SpecificationMode.KNOWN_HOT_OUTLET:
        assert inp.hot.outlet_temperature_k is not None
        # Hot outlet known → compute duty from hot side
        try:
            hot_outlet_state = provider.state_tp(
                inp.hot.fluid_identifier,
                inp.hot.outlet_temperature_k,
                inp.hot.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            _record_failed_property_call(
                property_calls,
                inp.hot.fluid_identifier,
                "TP",
                (
                    ("temperature_k", inp.hot.outlet_temperature_k),
                    ("pressure_pa", inp.hot.inlet_pressure_pa),
                ),
                provider,
                exc,
            )
            blockers.append(
                EngineeringMessage(
                    code=_property_error_to_code(exc),
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=f"Hot-side outlet property evaluation failed: {exc}",
                    source_module="heat_balance",
                    context=((("error", str(exc)),)),
                )
            )
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        _record_property_call(
            property_calls,
            inp.hot.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.hot.outlet_temperature_k),
                ("pressure_pa", inp.hot.inlet_pressure_pa),
            ),
            provider,
            hot_outlet_state,
            success=True,
        )

        phase_msg = _check_single_phase(hot_outlet_state, "Hot-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        # Phase family match check
        family_msg = _check_phase_family_match(
            hot_inlet_state.phase, hot_outlet_state.phase, "Hot-side"
        )
        if family_msg is not None:
            blockers.append(family_msg)
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        duty_w = _compute_duty_from_hot(hot_inlet_state, hot_outlet_state, inp.hot.mass_flow_kg_s)

        if duty_w < 0:
            blockers.append(
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Computed duty is negative ({duty_w:.2f} W): hot outlet "
                        f"temperature ({inp.hot.outlet_temperature_k} K) is above "
                        f"hot inlet ({inp.hot.inlet_temperature_k} K)."
                    ),
                    source_module="heat_balance",
                )
            )
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        # Verify duty if also provided
        if inp.known_duty_w is not None:
            duty_diff = abs(duty_w - inp.known_duty_w)
            duty_tol = inp.solver_params.energy_tolerance * max(
                abs(duty_w), _ABSOLUTE_DUTY_THRESHOLD
            )
            if duty_diff > duty_tol:
                blockers.append(
                    EngineeringMessage(
                        code=ErrorCode.INPUT_INCONSISTENT,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message=(
                            f"Over-specified: provided duty ({inp.known_duty_w:.2f} W) "
                            f"inconsistent with computed duty ({duty_w:.2f} W)."
                        ),
                        source_module="heat_balance",
                    )
                )
                return _make_blocked_result(
                    inp,
                    provider,
                    mode,
                    hot_inlet_state,
                    cold_inlet_state,
                    property_calls,
                    warnings,
                    blockers,
                )

        # Solve cold outlet
        cold_outlet_state, iters_cold, be_cold = _solve_outlet_temperature(
            provider,
            inp.cold.fluid_identifier,
            cold_inlet_state,
            inp.cold.mass_flow_kg_s,
            duty_w,
            is_hot_side=False,
            solver_params=inp.solver_params,
            property_calls=property_calls,
            expected_phase_family=cold_phase_family,
        )
        total_brent_iterations = iters_cold
        total_bracket_evaluations = be_cold

    elif mode == SpecificationMode.KNOWN_COLD_OUTLET:
        assert inp.cold.outlet_temperature_k is not None
        # Cold outlet known → compute duty from cold side
        try:
            cold_outlet_state = provider.state_tp(
                inp.cold.fluid_identifier,
                inp.cold.outlet_temperature_k,
                inp.cold.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            _record_failed_property_call(
                property_calls,
                inp.cold.fluid_identifier,
                "TP",
                (
                    ("temperature_k", inp.cold.outlet_temperature_k),
                    ("pressure_pa", inp.cold.inlet_pressure_pa),
                ),
                provider,
                exc,
            )
            blockers.append(
                EngineeringMessage(
                    code=_property_error_to_code(exc),
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=f"Cold-side outlet property evaluation failed: {exc}",
                    source_module="heat_balance",
                    context=((("error", str(exc)),)),
                )
            )
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        _record_property_call(
            property_calls,
            inp.cold.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.cold.outlet_temperature_k),
                ("pressure_pa", inp.cold.inlet_pressure_pa),
            ),
            provider,
            cold_outlet_state,
            success=True,
        )

        phase_msg = _check_single_phase(cold_outlet_state, "Cold-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        # Phase family match check
        family_msg = _check_phase_family_match(
            cold_inlet_state.phase, cold_outlet_state.phase, "Cold-side"
        )
        if family_msg is not None:
            blockers.append(family_msg)
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        duty_w = _compute_duty_from_cold(
            cold_inlet_state, cold_outlet_state, inp.cold.mass_flow_kg_s
        )

        if duty_w < 0:
            blockers.append(
                EngineeringMessage(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=(
                        f"Computed duty is negative ({duty_w:.2f} W): cold outlet "
                        f"temperature ({inp.cold.outlet_temperature_k} K) is below "
                        f"cold inlet ({inp.cold.inlet_temperature_k} K)."
                    ),
                    source_module="heat_balance",
                )
            )
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        # Verify duty if also provided
        if inp.known_duty_w is not None:
            duty_diff = abs(duty_w - inp.known_duty_w)
            duty_tol = inp.solver_params.energy_tolerance * max(
                abs(duty_w), _ABSOLUTE_DUTY_THRESHOLD
            )
            if duty_diff > duty_tol:
                blockers.append(
                    EngineeringMessage(
                        code=ErrorCode.INPUT_INCONSISTENT,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message=(
                            f"Over-specified: provided duty ({inp.known_duty_w:.2f} W) "
                            f"inconsistent with computed duty ({duty_w:.2f} W)."
                        ),
                        source_module="heat_balance",
                    )
                )
                return _make_blocked_result(
                    inp,
                    provider,
                    mode,
                    hot_inlet_state,
                    cold_inlet_state,
                    property_calls,
                    warnings,
                    blockers,
                )

        # Solve hot outlet
        hot_outlet_state, iters_hot, be_hot = _solve_outlet_temperature(
            provider,
            inp.hot.fluid_identifier,
            hot_inlet_state,
            inp.hot.mass_flow_kg_s,
            duty_w,
            is_hot_side=True,
            solver_params=inp.solver_params,
            property_calls=property_calls,
            expected_phase_family=hot_phase_family,
        )
        total_brent_iterations = iters_hot
        total_bracket_evaluations = be_hot

    elif mode == SpecificationMode.BOTH_OUTLETS_KNOWN:
        # Both outlets known → verify energy balance
        assert inp.hot.outlet_temperature_k is not None
        assert inp.cold.outlet_temperature_k is not None

        try:
            hot_outlet_state = provider.state_tp(
                inp.hot.fluid_identifier,
                inp.hot.outlet_temperature_k,
                inp.hot.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            _record_failed_property_call(
                property_calls,
                inp.hot.fluid_identifier,
                "TP",
                (
                    ("temperature_k", inp.hot.outlet_temperature_k),
                    ("pressure_pa", inp.hot.inlet_pressure_pa),
                ),
                provider,
                exc,
            )
            blockers.append(
                EngineeringMessage(
                    code=_property_error_to_code(exc),
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=f"Hot-side outlet property evaluation failed: {exc}",
                    source_module="heat_balance",
                    context=((("error", str(exc)),)),
                )
            )
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        _record_property_call(
            property_calls,
            inp.hot.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.hot.outlet_temperature_k),
                ("pressure_pa", inp.hot.inlet_pressure_pa),
            ),
            provider,
            hot_outlet_state,
            success=True,
        )

        phase_msg = _check_single_phase(hot_outlet_state, "Hot-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        try:
            cold_outlet_state = provider.state_tp(
                inp.cold.fluid_identifier,
                inp.cold.outlet_temperature_k,
                inp.cold.inlet_pressure_pa,
            )
        except PropertyServiceError as exc:
            _record_failed_property_call(
                property_calls,
                inp.cold.fluid_identifier,
                "TP",
                (
                    ("temperature_k", inp.cold.outlet_temperature_k),
                    ("pressure_pa", inp.cold.inlet_pressure_pa),
                ),
                provider,
                exc,
            )
            blockers.append(
                EngineeringMessage(
                    code=_property_error_to_code(exc),
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=f"Cold-side outlet property evaluation failed: {exc}",
                    source_module="heat_balance",
                    context=((("error", str(exc)),)),
                )
            )
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        _record_property_call(
            property_calls,
            inp.cold.fluid_identifier,
            "TP",
            (
                ("temperature_k", inp.cold.outlet_temperature_k),
                ("pressure_pa", inp.cold.inlet_pressure_pa),
            ),
            provider,
            cold_outlet_state,
            success=True,
        )

        phase_msg = _check_single_phase(cold_outlet_state, "Cold-side outlet")
        if phase_msg is not None:
            blockers.append(phase_msg)
            return _make_blocked_result(
                inp,
                provider,
                mode,
                hot_inlet_state,
                cold_inlet_state,
                property_calls,
                warnings,
                blockers,
            )

        # Phase family match checks
        for label, i_state, o_state in (
            ("Hot-side", hot_inlet_state, hot_outlet_state),
            ("Cold-side", cold_inlet_state, cold_outlet_state),
        ):
            family_msg = _check_phase_family_match(i_state.phase, o_state.phase, label)
            if family_msg is not None:
                blockers.append(family_msg)
                return _make_blocked_result(
                    inp,
                    provider,
                    mode,
                    hot_inlet_state,
                    cold_inlet_state,
                    property_calls,
                    warnings,
                    blockers,
                )

        q_hot = _compute_duty_from_hot(hot_inlet_state, hot_outlet_state, inp.hot.mass_flow_kg_s)
        q_cold = _compute_duty_from_cold(
            cold_inlet_state, cold_outlet_state, inp.cold.mass_flow_kg_s
        )
        # Do NOT average into duty — report both separately
        duty_w = (q_hot + q_cold) / 2.0

    else:
        raise ValueError(f"Unhandled specification mode: {mode}")

    # --- Compute energy residual ---
    q_hot = _compute_duty_from_hot(hot_inlet_state, hot_outlet_state, inp.hot.mass_flow_kg_s)
    q_cold = _compute_duty_from_cold(cold_inlet_state, cold_outlet_state, inp.cold.mass_flow_kg_s)
    residual_w, relative_imbalance, energy_balance_accepted = _compute_energy_balance(
        q_hot, q_cold, inp.solver_params.energy_tolerance
    )

    solver_converged = True  # Brent found a root (we wouldn't be here otherwise)

    # --- Temperature feasibility checks (counterflow) ---
    tol = inp.solver_params.temperature_tolerance
    feas_msgs = _check_temperature_feasibility(
        hot_inlet_state.temperature_k,
        hot_outlet_state.temperature_k,
        cold_inlet_state.temperature_k,
        cold_outlet_state.temperature_k,
        duty_w,
        tol,
    )

    # Route messages by severity into warnings vs blockers
    for msg in feas_msgs:
        if msg.severity == EngineeringMessageSeverity.BLOCKER:
            blockers.append(msg)
        else:
            warnings.append(msg)

    # --- Energy balance gate ---
    if not energy_balance_accepted:
        blockers.append(
            EngineeringMessage(
                code=ErrorCode.CALCULATION_NOT_CONVERGED,
                severity=EngineeringMessageSeverity.BLOCKER,
                message=(
                    f"Energy imbalance {relative_imbalance:.6f} exceeds tolerance "
                    f"{inp.solver_params.energy_tolerance}. "
                    f"q_hot={q_hot:.2f} W, q_cold={q_cold:.2f} W."
                ),
                source_module="heat_balance",
            )
        )

    # --- Phase checks on final solved outlets ---
    for label, state in (
        ("Hot-side outlet", hot_outlet_state),
        ("Cold-side outlet", cold_outlet_state),
    ):
        phase_msg = _check_single_phase(state, label)
        if phase_msg is not None:
            blockers.append(phase_msg)

    # Phase family match for solved outlets
    for label, i_state, o_state in (
        ("Hot-side", hot_inlet_state, hot_outlet_state),
        ("Cold-side", cold_inlet_state, cold_outlet_state),
    ):
        family_msg = _check_phase_family_match(i_state.phase, o_state.phase, label)
        if family_msg is not None:
            blockers.append(family_msg)

    # --- Determine final status ---
    if blockers:
        status = HeatBalanceStatus.BLOCKED
        # Provide duty only when energy balance is accepted AND no blockers
        final_duty_w: float | None = None
    elif not solver_converged:
        status = HeatBalanceStatus.FAILED
        final_duty_w = None
    else:
        status = HeatBalanceStatus.SUCCEEDED
        final_duty_w = duty_w

    # --- Build provenance and hash ---
    hot_model = hot_inlet_state.to_model()
    hot_outlet_model = hot_outlet_state.to_model()
    cold_model = cold_inlet_state.to_model()
    cold_outlet_model = cold_outlet_state.to_model()

    result_hash = _compute_result_hash(
        mode,
        inp.flow_arrangement,
        hot_model,
        hot_outlet_model,
        cold_model,
        cold_outlet_model,
        inp.hot,
        inp.cold,
        inp.known_duty_w,
        inp.solver_params,
        provider,
        tuple(property_calls),
        tuple(warnings),
        tuple(blockers),
        q_hot,
        q_cold,
        residual_w,
        relative_imbalance,
        energy_balance_accepted,
        _SOFTWARE_VERSION,
    )

    provenance = _build_provenance(
        specification_mode=mode,
        flow_arrangement=inp.flow_arrangement,
        hot=inp.hot,
        cold=inp.cold,
        known_duty_w=inp.known_duty_w,
        solver_params=inp.solver_params,
        property_calls=property_calls,
        solver_iterations=total_brent_iterations,
        bracket_evaluations=total_bracket_evaluations,
        solver_converged=solver_converged,
        warnings=warnings,
        blockers=blockers,
        result_hash=result_hash,
    )

    # Build failure record if FAILED
    failure: RunFailure | None = None
    if status == HeatBalanceStatus.FAILED:
        failure = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Root-finding solver did not converge.",
            context=(
                ("solver_iterations", total_brent_iterations),
                ("bracket_evaluations", total_bracket_evaluations),
            ),
        )

    return HeatBalanceResult(
        status=status,
        specification_mode=mode,
        flow_arrangement=inp.flow_arrangement,
        duty_w=final_duty_w,
        hot_inlet_state=hot_model,
        hot_outlet_state=hot_outlet_model,
        cold_inlet_state=cold_model,
        cold_outlet_state=cold_outlet_model,
        q_hot_w=q_hot,
        q_cold_w=q_cold,
        residual_w=residual_w,
        relative_imbalance=relative_imbalance,
        energy_balance_accepted=energy_balance_accepted,
        solver_iterations=total_brent_iterations,
        bracket_evaluations=total_bracket_evaluations,
        solver_converged=solver_converged,
        property_calls=tuple(property_calls),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        failure=failure,
        result_hash=result_hash,
        provenance_graph=provenance,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "FlowArrangement",
    "HeatBalanceInput",
    "HeatBalanceResult",
    "HeatBalanceStatus",
    "PropertyCallRecord",
    "SolverParams",
    "SpecificationMode",
    "StreamState",
    "classify_specification",
    "solve_heat_balance",
]
