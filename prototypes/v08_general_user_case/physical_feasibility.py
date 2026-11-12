"""Property-backed physical feasibility checks for normalized V08 user cases."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hexagent.properties.base import FluidIdentifier, PhaseRegion, PropertyProvider
from hexagent.properties.errors import PropertyServiceError
from prototypes.v07_general_rating_sizing_mvp.engineering_input import FluidSideSpec
from prototypes.v08_general_user_case.envelope import (
    V08_INLET_PRESSURE_MAX_PA,
    V08_INLET_PRESSURE_MIN_PA,
    V08_INLET_TEMPERATURE_MAX_K,
    V08_INLET_TEMPERATURE_MIN_K,
    V08_SUPPORTED_EXCHANGER,
    V08_SUPPORTED_FLUID,
    V08_THERMAL_BINDING_PRESSURE_MAX_PA,
    V08_THERMAL_BINDING_PRESSURE_MIN_PA,
    V08_THERMAL_BINDING_TEMPERATURE_MAX_K,
    V08_THERMAL_BINDING_TEMPERATURE_MIN_K,
)
from prototypes.v08_general_user_case.errors import V08ValidationCode, V08ValidationIssue
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase

# Rated duty at or above target / THERMODYNAMIC_DUTY_TOLERANCE counts as meeting target (same envelope as feasibility).
THERMODYNAMIC_DUTY_TOLERANCE = Decimal("1.0001")


@dataclass(frozen=True)
class SidePropertyEvidence:
    side_label: str
    temperature_k: Decimal
    pressure_pa: Decimal
    enthalpy_j_kg: Decimal
    phase: str
    cp_j_kg_k: Decimal | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "side_label": self.side_label,
            "temperature_k": str(self.temperature_k),
            "pressure_pa": str(self.pressure_pa),
            "enthalpy_j_kg": str(self.enthalpy_j_kg),
            "phase": self.phase,
            "cp_j_kg_k": None if self.cp_j_kg_k is None else str(self.cp_j_kg_k),
        }


@dataclass(frozen=True)
class PhysicalFeasibilityReport:
    issues: tuple[V08ValidationIssue, ...]
    tube_side: SidePropertyEvidence | None
    shell_side: SidePropertyEvidence | None
    thermodynamic_max_duty_w: Decimal | None
    thermal_binding_ready: bool

    @property
    def ok(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.as_dict() for issue in self.issues],
            "tube_side": None if self.tube_side is None else self.tube_side.as_dict(),
            "shell_side": None if self.shell_side is None else self.shell_side.as_dict(),
            "thermodynamic_max_duty_w": (
                None
                if self.thermodynamic_max_duty_w is None
                else str(self.thermodynamic_max_duty_w)
            ),
            "thermal_binding_ready": self.thermal_binding_ready,
        }


def _issue(
    code: V08ValidationCode,
    field: str,
    message: str,
    **context: Any,
) -> V08ValidationIssue:
    return V08ValidationIssue(code=code, field=field, message=message, context=context)


def _side_in_input_envelope(side: FluidSideSpec, *, label: str) -> V08ValidationIssue | None:
    if side.fluid != V08_SUPPORTED_FLUID:
        return _issue(
            V08ValidationCode.OUT_OF_ENVELOPE,
            f"{label}.fluid",
            f"fluid {side.fluid!r} outside V08 water/water scope",
            fluid=str(side.fluid),
        )
    if (
        side.inlet_temperature_k < V08_INLET_TEMPERATURE_MIN_K
        or side.inlet_temperature_k > V08_INLET_TEMPERATURE_MAX_K
    ):
        return _issue(
            V08ValidationCode.OUT_OF_ENVELOPE,
            f"{label}.inlet_temperature_k",
            "inlet temperature outside declared V08 input envelope",
            temperature_k=str(side.inlet_temperature_k),
            min_k=str(V08_INLET_TEMPERATURE_MIN_K),
            max_k=str(V08_INLET_TEMPERATURE_MAX_K),
        )
    if (
        side.inlet_pressure_pa < V08_INLET_PRESSURE_MIN_PA
        or side.inlet_pressure_pa > V08_INLET_PRESSURE_MAX_PA
    ):
        return _issue(
            V08ValidationCode.OUT_OF_ENVELOPE,
            f"{label}.inlet_pressure_pa",
            "inlet pressure outside declared V08 input envelope",
            pressure_pa=str(side.inlet_pressure_pa),
            min_pa=str(V08_INLET_PRESSURE_MIN_PA),
            max_pa=str(V08_INLET_PRESSURE_MAX_PA),
        )
    if not side.mass_flow_kg_s.is_finite() or side.mass_flow_kg_s <= 0:
        return _issue(
            V08ValidationCode.INVALID_INPUT,
            f"{label}.mass_flow_kg_s",
            "mass flow must be positive and finite",
            mass_flow_kg_s=str(side.mass_flow_kg_s),
        )
    return None


def _evaluate_side(
    provider: PropertyProvider,
    side: FluidSideSpec,
    *,
    label: str,
) -> tuple[SidePropertyEvidence | None, V08ValidationIssue | None]:
    try:
        state = provider.state_tp(
            FluidIdentifier(name="Water"),
            temperature_k=float(side.inlet_temperature_k),
            pressure_pa=float(side.inlet_pressure_pa),
        )
    except PropertyServiceError as exc:
        return None, _issue(
            V08ValidationCode.PROPERTY_UNAVAILABLE,
            f"{label}.inlet_state",
            str(exc),
            provider=getattr(provider, "name", type(provider).__name__),
        )
    if state.phase not in (PhaseRegion.LIQUID, PhaseRegion.SUPERCRITICAL_LIQUID):
        return None, _issue(
            V08ValidationCode.OUT_OF_ENVELOPE,
            f"{label}.phase",
            f"inlet phase {state.phase.value} is not single-phase liquid water",
            phase=state.phase.value,
        )
    cp = Decimal(str(state.cp_j_kg_k))
    evidence = SidePropertyEvidence(
        side_label=label,
        temperature_k=side.inlet_temperature_k,
        pressure_pa=side.inlet_pressure_pa,
        enthalpy_j_kg=Decimal(str(state.enthalpy_j_kg)),
        phase=state.phase.value,
        cp_j_kg_k=cp,
    )
    return evidence, None


def assess_physical_feasibility(
    case: NormalizedUserDesignCase,
    provider: PropertyProvider,
) -> PhysicalFeasibilityReport:
    issues: list[V08ValidationIssue] = []
    if case.exchanger_type != V08_SUPPORTED_EXCHANGER:
        issues.append(
            _issue(
                V08ValidationCode.OUT_OF_ENVELOPE,
                "exchanger_type",
                f"unsupported exchanger_type {case.exchanger_type!r}",
            )
        )
    if case.tube_side.inlet_temperature_k <= case.shell_side.inlet_temperature_k:
        issues.append(
            _issue(
                V08ValidationCode.THERMODYNAMICALLY_INFEASIBLE,
                "tube_side.inlet_temperature_k",
                "hot tube inlet must exceed cold shell inlet",
            )
        )
    for label, side in (("tube_side", case.tube_side), ("shell_side", case.shell_side)):
        envelope_issue = _side_in_input_envelope(side, label=label)
        if envelope_issue is not None:
            issues.append(envelope_issue)

    tube_evidence: SidePropertyEvidence | None = None
    shell_evidence: SidePropertyEvidence | None = None
    if not issues:
        tube_evidence, tube_issue = _evaluate_side(provider, case.tube_side, label="tube_side")
        if tube_issue is not None:
            issues.append(tube_issue)
        shell_evidence, shell_issue = _evaluate_side(provider, case.shell_side, label="shell_side")
        if shell_issue is not None:
            issues.append(shell_issue)

    thermo_max: Decimal | None = None
    if tube_evidence is not None and shell_evidence is not None and not issues:
        try:
            h_hot_out = Decimal(
                str(
                    provider.state_tp(
                        FluidIdentifier(name="Water"),
                        temperature_k=float(shell_evidence.temperature_k),
                        pressure_pa=float(tube_evidence.pressure_pa),
                    ).enthalpy_j_kg
                )
            )
            h_cold_out = Decimal(
                str(
                    provider.state_tp(
                        FluidIdentifier(name="Water"),
                        temperature_k=float(tube_evidence.temperature_k),
                        pressure_pa=float(shell_evidence.pressure_pa),
                    ).enthalpy_j_kg
                )
            )
        except PropertyServiceError as exc:
            issues.append(
                _issue(
                    V08ValidationCode.PROPERTY_UNAVAILABLE,
                    "thermodynamic_max_duty_w",
                    f"crossover enthalpy evaluation failed: {exc}",
                )
            )
        else:
            q_hot = case.tube_side.mass_flow_kg_s * (tube_evidence.enthalpy_j_kg - h_hot_out)
            q_cold = case.shell_side.mass_flow_kg_s * (h_cold_out - shell_evidence.enthalpy_j_kg)
            thermo_max = min(q_hot, q_cold)
            if thermo_max <= 0:
                issues.append(
                    _issue(
                        V08ValidationCode.THERMODYNAMICALLY_INFEASIBLE,
                        "thermodynamic_max_duty_w",
                        "no positive heat-transfer driving force at inlets",
                        thermodynamic_max_duty_w=str(thermo_max),
                    )
                )
            elif case.target_duty_w > thermo_max * THERMODYNAMIC_DUTY_TOLERANCE:
                issues.append(
                    _issue(
                        V08ValidationCode.THERMODYNAMICALLY_INFEASIBLE,
                        "target_duty_w",
                        "target duty exceeds property-backed thermodynamic maximum",
                        target_duty_w=str(case.target_duty_w),
                        thermodynamic_max_duty_w=str(thermo_max),
                    )
                )

    thermal_binding_ready = _thermal_binding_ready(case)
    return PhysicalFeasibilityReport(
        issues=tuple(issues),
        tube_side=tube_evidence,
        shell_side=shell_evidence,
        thermodynamic_max_duty_w=thermo_max,
        thermal_binding_ready=thermal_binding_ready,
    )


def _thermal_binding_ready(case: NormalizedUserDesignCase) -> bool:
    for side in (case.tube_side, case.shell_side):
        if (
            side.inlet_temperature_k < V08_THERMAL_BINDING_TEMPERATURE_MIN_K
            or side.inlet_temperature_k > V08_THERMAL_BINDING_TEMPERATURE_MAX_K
        ):
            return False
        if (
            side.inlet_pressure_pa < V08_THERMAL_BINDING_PRESSURE_MIN_PA
            or side.inlet_pressure_pa > V08_THERMAL_BINDING_PRESSURE_MAX_PA
        ):
            return False
    return case.tube_side.inlet_temperature_k > case.shell_side.inlet_temperature_k
