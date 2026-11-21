"""330 kW Task173 enthalpy audit — thermal boundary context invariants (prototype)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    active_experimental_thermal_boundary,
    matches_frozen_reference_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _MeshRun,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_inlet_temperature_k,
    effective_shell_mass_flow_kg_s,
    effective_tube_inlet_temperature_k,
    effective_tube_mass_flow_kg_s,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    _run_with_rating_context,
)
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID

AUDIT_CASE_ID = CASE_330KW_ID
AUDIT_TUBE_INLET_K = Decimal("310")
AUDIT_SHELL_INLET_K = Decimal("295")
AUDIT_TUBE_MDOT = Decimal("12")
AUDIT_SHELL_MDOT = Decimal("20")

ContextStatus = Literal["VALID", "AUDIT_CONTEXT_MISSING", "AUDIT_CONTEXT_INVALID"]


@dataclass(frozen=True)
class AuditContextSnapshot:
    status: ContextStatus
    audit_case_id: str | None
    audit_tube_inlet_k: str | None
    audit_shell_inlet_k: str | None
    audit_tube_mdot: str | None
    audit_shell_mdot: str | None
    authority_shell_inlet_h_j_kg: str | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class InletTerminalInvariant:
    shell_inlet_face_h_j_kg: str
    authority_shell_inlet_h_j_kg: str
    inlet_face_minus_authority_j_kg: str
    production_terminal_residual_j_kg: str
    invariant_match: Literal["PASS", "BLOCKED"]


@dataclass(frozen=True)
class TpPhReconstructionSummary:
    max_delta_h_j_kg: float
    max_delta_t_k: float
    inlet_delta_h_j_kg: str | None
    inlet_delta_t_k: str | None


def verify_audit_thermal_context(
    bindings: CandidateRatingBindings,
) -> AuditContextSnapshot:
    """Invariant A — active experimental boundary must match normalized 330 kW case."""
    binding = active_experimental_thermal_boundary()
    notes: list[str] = []
    if binding is None:
        return AuditContextSnapshot(
            status="AUDIT_CONTEXT_MISSING",
            audit_case_id=None,
            audit_tube_inlet_k=None,
            audit_shell_inlet_k=None,
            audit_tube_mdot=None,
            audit_shell_mdot=None,
            authority_shell_inlet_h_j_kg=None,
            notes=("no_active_experimental_thermal_boundary",),
        )

    n = bindings.normalized
    expected_case = n.engineering_case_id
    if expected_case != AUDIT_CASE_ID:
        invalid = True
        notes.append(f"unexpected_engineering_case_id={expected_case}")

    def _mismatch(label: str, got: Decimal, want: Decimal) -> bool:
        if got != want:
            notes.append(f"{label}:got={got}:want={want}")
            return True
        return False

    invalid = False
    invalid |= _mismatch(
        "tube_inlet_k", binding.tube_inlet_temperature_k, n.tube_side.inlet_temperature_k
    )
    invalid |= _mismatch(
        "shell_inlet_k", binding.shell_inlet_temperature_k, n.shell_side.inlet_temperature_k
    )
    invalid |= _mismatch("tube_mdot", binding.tube_mass_flow_kg_s, n.tube_side.mass_flow_kg_s)
    invalid |= _mismatch("shell_mdot", binding.shell_mass_flow_kg_s, n.shell_side.mass_flow_kg_s)

    if expected_case == AUDIT_CASE_ID:
        invalid |= _mismatch(
            "audit_tube_inlet_k", binding.tube_inlet_temperature_k, AUDIT_TUBE_INLET_K
        )
        invalid |= _mismatch(
            "audit_shell_inlet_k", binding.shell_inlet_temperature_k, AUDIT_SHELL_INLET_K
        )
        if matches_frozen_reference_boundary(binding):
            invalid = True
            notes.append("frozen_default_boundary_300_29815_active_on_330kw_case")

    status: ContextStatus = "AUDIT_CONTEXT_INVALID" if invalid or notes else "VALID"

    try:
        h_auth = str(effective_shell_cold_inlet_enthalpy_j_kg())
    except Exception:
        h_auth = None

    return AuditContextSnapshot(
        status=status,
        audit_case_id=expected_case,
        audit_tube_inlet_k=str(binding.tube_inlet_temperature_k),
        audit_shell_inlet_k=str(binding.shell_inlet_temperature_k),
        audit_tube_mdot=str(binding.tube_mass_flow_kg_s),
        audit_shell_mdot=str(binding.shell_mass_flow_kg_s),
        authority_shell_inlet_h_j_kg=h_auth,
        notes=tuple(notes) if notes else (),
    )


def inlet_terminal_invariant(run: _MeshRun) -> InletTerminalInvariant:
    """Invariant B — audited inlet enthalpy delta equals production terminal residual."""
    face_h = run.faces_shell[-1].enthalpy_j_kg
    auth_h = effective_shell_cold_inlet_enthalpy_j_kg()
    audited = face_h - auth_h
    prod = run.observables.terminal_boundary_residual_j_kg
    match = "PASS" if audited == prod else "BLOCKED"
    return InletTerminalInvariant(
        shell_inlet_face_h_j_kg=str(face_h),
        authority_shell_inlet_h_j_kg=str(auth_h),
        inlet_face_minus_authority_j_kg=str(audited),
        production_terminal_residual_j_kg=str(prod),
        invariant_match=match,
    )


def tp_ph_reconstruction_summary(
    provider: PropertyProvider,
    bindings: CandidateRatingBindings,
) -> TpPhReconstructionSummary:
    """Invariant C — TP(inlet) then PH(P,H_TP); record real ΔT and ΔH (must be in context)."""
    from hexagent.properties.base import FluidIdentifier, ReferenceStatePolicy

    fluid = FluidIdentifier(name=str(bindings.normalized.shell_side.fluid))
    p_pa = float(bindings.normalized.shell_side.inlet_pressure_pa)
    t_in = float(effective_shell_inlet_temperature_k())
    ref = getattr(provider, "reference_state_policy", ReferenceStatePolicy.DEF)
    if not isinstance(ref, ReferenceStatePolicy):
        ref = ReferenceStatePolicy.DEF
    max_dh = 0.0
    max_dt = 0.0
    inlet_dh: str | None = None
    inlet_dt: str | None = None
    try:
        tp = provider.state_tp(fluid, t_in, p_pa)
        h_tp = float(tp.enthalpy_j_kg)
        ph = provider.state_ph(fluid, p_pa, h_tp, reference_state=ref)
        dt = float(ph.temperature_k) - t_in
        dh = float(ph.enthalpy_j_kg) - h_tp
        max_dt = abs(dt)
        max_dh = abs(dh)
        inlet_dt = str(dt)
        inlet_dh = str(dh)
    except Exception:
        pass
    return TpPhReconstructionSummary(
        max_delta_h_j_kg=max_dh,
        max_delta_t_k=max_dt,
        inlet_delta_h_j_kg=inlet_dh,
        inlet_delta_t_k=inlet_dt,
    )


def enthalpy_audit_precision_threshold_j_kg() -> float:
    """Per-cell / PH loss tracking — must not mask O(1e-9)–O(1e-6) propagation errors."""
    return max(1.0e-12, float(Decimal("1e-9")))


def run_enthalpy_audit_body(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
    body: Any,
) -> Any:
    """Run audit callbacks under the same binding lifecycle as isolated shooting."""
    return _run_with_rating_context(bindings, provider, subdivisions=subdivisions, body=body)


def read_effective_audit_invariants() -> dict[str, str]:
    """Expose effective getters for regression tests (requires active context)."""
    return {
        "AUDIT_TUBE_INLET_K": str(effective_tube_inlet_temperature_k()),
        "AUDIT_SHELL_INLET_K": str(effective_shell_inlet_temperature_k()),
        "AUDIT_TUBE_MDOT": str(effective_tube_mass_flow_kg_s()),
        "AUDIT_SHELL_MDOT": str(effective_shell_mass_flow_kg_s()),
    }


__all__ = [
    "AUDIT_CASE_ID",
    "AUDIT_SHELL_INLET_K",
    "AUDIT_SHELL_MDOT",
    "AUDIT_TUBE_INLET_K",
    "AUDIT_TUBE_MDOT",
    "AuditContextSnapshot",
    "ContextStatus",
    "InletTerminalInvariant",
    "TpPhReconstructionSummary",
    "enthalpy_audit_precision_threshold_j_kg",
    "inlet_terminal_invariant",
    "read_effective_audit_invariants",
    "run_enthalpy_audit_body",
    "tp_ph_reconstruction_summary",
    "verify_audit_thermal_context",
]
